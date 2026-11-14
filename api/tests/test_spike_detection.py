import pytest

MIN_RELATIVE_INCREASE = 0.5  # >= 50%
MIN_ABSOLUTE_INCREASE = 1.0  # >= 1.0
MIN_BASELINE_COMPLEXITY = 1.0  # Tiny baselines (e.g. 0.5 -> 4.0) must NOT count


def detect_spikes(data, min_relative=MIN_RELATIVE_INCREASE, min_absolute=MIN_ABSOLUTE_INCREASE, min_baseline=MIN_BASELINE_COMPLEXITY):
    """Python implementation of the spike detection rule for automated verification."""
    if not data or len(data) < 2:
        return []

    spikes = []
    for i in range(1, len(data)):
        prev = float(data[i - 1].get("avg_complexity", 0))
        curr = float(data[i].get("avg_complexity", 0))

        if prev < min_baseline:
            continue

        delta = round(curr - prev, 2)
        relative = (curr - prev) / prev if prev > 0 else 0

        if relative >= min_relative and delta >= min_absolute:
            raw_ratio = curr / prev if prev > 0 else 1.0
            ratio = round(raw_ratio, 1) if raw_ratio % 1 != 0 else int(raw_ratio)
            spikes.append({
                "index": i,
                "commit": data[i],
                "before": prev,
                "after": curr,
                "delta": delta,
                "ratio": ratio,
            })
    return spikes


def test_tiny_baseline_does_not_count():
    data = [
        {"sha": "c1", "avg_complexity": 0.5},
        {"sha": "c2", "avg_complexity": 4.0},
    ]
    spikes = detect_spikes(data)
    assert len(spikes) == 0, "0.5 -> 4.0 is a tiny baseline and must NOT count as a spike"


def test_real_jump_counts():
    data = [
        {"sha": "c1", "avg_complexity": 2.1},
        {"sha": "c2", "avg_complexity": 6.3},
    ]
    spikes = detect_spikes(data)
    assert len(spikes) == 1
    assert spikes[0]["before"] == 2.1
    assert spikes[0]["after"] == 6.3
    assert spikes[0]["delta"] == 4.2
    assert spikes[0]["ratio"] == 3


def test_small_absolute_increase_rejected():
    data = [
        {"sha": "c1", "avg_complexity": 3.0},
        {"sha": "c2", "avg_complexity": 3.5},
    ]
    spikes = detect_spikes(data)
    assert len(spikes) == 0


def test_small_relative_increase_rejected():
    data = [
        {"sha": "c1", "avg_complexity": 10.0},
        {"sha": "c2", "avg_complexity": 12.0},
    ]
    spikes = detect_spikes(data)
    assert len(spikes) == 0


def test_multiple_spikes():
    data = [
        {"sha": "c1", "avg_complexity": 0.5},
        {"sha": "c2", "avg_complexity": 4.0},  # rejected (tiny baseline)
        {"sha": "c3", "avg_complexity": 4.2},  # rejected (small delta)
        {"sha": "c4", "avg_complexity": 8.4},  # spike: 4.2 -> 8.4
        {"sha": "c5", "avg_complexity": 8.6},  # rejected (small delta)
        {"sha": "c6", "avg_complexity": 17.2}, # spike: 8.6 -> 17.2
    ]
    spikes = detect_spikes(data)
    assert len(spikes) == 2
    assert spikes[0]["commit"]["sha"] == "c4"
    assert spikes[1]["commit"]["sha"] == "c6"

