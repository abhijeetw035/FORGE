"""
Python mirror of the TypeScript spike detection logic (spikes.ts).
Used to verify the same rules produce the same results server-side.
Constants must stay in sync with dashboard/src/lib/spikes.ts.
"""
import pytest

# ─── Constants (keep in sync with spikes.ts) ─────────────────────────────────
SPIKE_MIN_RELATIVE_INCREASE = 0.10   # >= 10 % increase
SPIKE_MIN_ABSOLUTE_INCREASE = 0.30   # absolute delta >= 0.30
SPIKE_PERCENTILE_THRESHOLD = 95      # delta must be above 95th percentile
SPIKE_MAX_CHART_MARKERS = 15


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _percentile(values: list[float], p: int) -> float:
    """Nearest-rank percentile (0-based sorted index)."""
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(p / 100 * len(s))
    return s[min(idx, len(s) - 1)]


def detect_spikes(data: list[dict]) -> list[dict]:
    """
    Python re-implementation matching the TypeScript detectSpikes() in spikes.ts.

    Rules:
      1. relative increase >= SPIKE_MIN_RELATIVE_INCREASE
      2. absolute increase >= SPIKE_MIN_ABSOLUTE_INCREASE
      3. delta >= 95th percentile of all positive commit-to-commit deltas
    """
    if not data or len(data) < 2:
        return []

    positive_deltas = []
    for i in range(1, len(data)):
        prev = float(data[i - 1].get("avg_complexity", 0))
        curr = float(data[i].get("avg_complexity", 0))
        d = curr - prev
        if d > 0:
            positive_deltas.append(d)

    p95 = _percentile(positive_deltas, SPIKE_PERCENTILE_THRESHOLD)

    spikes = []
    for i in range(1, len(data)):
        prev = float(data[i - 1].get("avg_complexity", 0))
        curr = float(data[i].get("avg_complexity", 0))
        raw_delta = curr - prev
        delta = round(raw_delta, 2)
        relative = (curr - prev) / prev if prev > 0 else 0.0

        meets_relative = relative >= SPIKE_MIN_RELATIVE_INCREASE
        meets_absolute = raw_delta >= SPIKE_MIN_ABSOLUTE_INCREASE - 1e-9
        meets_percentile = raw_delta >= p95 - 1e-9

        if meets_relative and meets_absolute and meets_percentile:
            raw_ratio = curr / prev if prev > 0 else 1.0
            ratio = int(raw_ratio) if raw_ratio % 1 == 0 else round(raw_ratio, 1)
            spikes.append({
                "index": i,
                "commit": data[i],
                "before": prev,
                "after": curr,
                "delta": delta,
                "ratio": ratio,
            })
    return spikes


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_constants_have_expected_values():
    assert SPIKE_MIN_RELATIVE_INCREASE == 0.10
    assert SPIKE_MIN_ABSOLUTE_INCREASE == 0.30
    assert SPIKE_PERCENTILE_THRESHOLD == 95
    assert SPIKE_MAX_CHART_MARKERS == 15


def test_percentile_basic():
    assert _percentile([1, 2, 3, 4, 5], 100) == 5
    assert _percentile([1, 2, 3, 4, 5], 0) == 1
    assert _percentile([], 95) == 0.0


def test_empty_and_single_returns_no_spikes():
    assert detect_spikes([]) == []
    assert detect_spikes([{"avg_complexity": 2.0}]) == []


def test_small_absolute_rejected():
    # +0.25 < SPIKE_MIN_ABSOLUTE_INCREASE 0.30
    data = [
        {"sha": "c1", "avg_complexity": 2.0},
        {"sha": "c2", "avg_complexity": 2.25},
    ]
    assert detect_spikes(data) == []


def test_small_relative_rejected():
    # 3.5% relative < 10% threshold
    data = [
        {"sha": "c1", "avg_complexity": 10.0},
        {"sha": "c2", "avg_complexity": 10.35},
    ]
    assert detect_spikes(data) == []


def test_genuine_spike_detected():
    # +0.80, 40% relative — well above all thresholds
    data = [
        {"sha": "c1", "avg_complexity": 2.0},
        {"sha": "c2", "avg_complexity": 2.80},
    ]
    spikes = detect_spikes(data)
    assert len(spikes) == 1
    assert spikes[0]["before"] == 2.0
    assert spikes[0]["after"] == 2.80
    assert spikes[0]["delta"] == 0.80


def test_p95_suppresses_small_jumps_in_noisy_series():
    """
    50 tiny drifts (+0.02 each, ~1% relative → fail relative check anyway),
    then one big jump of +0.60.  Only the big jump must be detected.
    """
    data = []
    complexity = 2.0
    for i in range(50):
        complexity = round(complexity + 0.02, 2)
        data.append({"sha": f"c{i}", "avg_complexity": complexity})
    big = round(complexity + 0.60, 2)
    data.append({"sha": "big", "avg_complexity": big})

    spikes = detect_spikes(data)
    assert len(spikes) >= 1
    assert spikes[-1]["commit"]["sha"] == "big"


def test_two_spikes_separated_by_stable_periods():
    data = [
        {"sha": "c1", "avg_complexity": 2.0},
        {"sha": "c2", "avg_complexity": 2.1},   # +0.10, 5% → not a spike
        {"sha": "c3", "avg_complexity": 3.0},   # +0.90, 43% → candidate
        {"sha": "c4", "avg_complexity": 3.05},  # +0.05, 1.7% → not a spike
        {"sha": "c5", "avg_complexity": 4.0},   # +0.95, 31% → candidate
    ]
    spikes = detect_spikes(data)
    sha_set = {s["commit"]["sha"] for s in spikes}
    # p95 of [0.10, 0.90, 0.05, 0.95] sorted=[0.05,0.10,0.90,0.95], idx=floor(4*0.95)=3 → 0.95
    # Only c5's delta of 0.95 == p95 ≥ p95, so at least c5 must be a spike
    assert "c5" in sha_set, f"c5 must be detected; got {sha_set}"
