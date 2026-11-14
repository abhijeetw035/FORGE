import type { TimelineData } from './api';

// ─── Spike-detection constants ──────────────────────────────────────────────
/** Repo-wide avg must increase by at least this fraction (10 %). */
export const SPIKE_MIN_RELATIVE_INCREASE = 0.10;
/** Absolute increase in avg complexity must be at least this much. */
export const SPIKE_MIN_ABSOLUTE_INCREASE = 0.30;
/** Change must be above this percentile of all positive commit-to-commit deltas. */
export const SPIKE_PERCENTILE_THRESHOLD = 95;
/** Maximum spike markers drawn on the chart; full list is still available. */
export const SPIKE_MAX_CHART_MARKERS = 15;

// ─── Types ───────────────────────────────────────────────────────────────────
export interface Spike {
  index: number;
  commit: TimelineData;
  before: number;
  after: number;
  delta: number;
  ratio: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Compute the Nth percentile of a numeric array.
 * Uses nearest-rank method (0-based sorted index).
 */
export function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.floor((p / 100) * sorted.length);
  return sorted[Math.min(idx, sorted.length - 1)];
}

// ─── Spike detection ─────────────────────────────────────────────────────────

/**
 * Detect significant complexity spikes across the commit timeline.
 *
 * A commit qualifies as a spike ONLY when ALL THREE conditions hold:
 *   1. Relative increase >= SPIKE_MIN_RELATIVE_INCREASE  (default 10 %)
 *   2. Absolute increase >= SPIKE_MIN_ABSOLUTE_INCREASE  (default 0.30)
 *   3. Delta is above the SPIKE_PERCENTILE_THRESHOLD     (default 95th percentile)
 *      of ALL positive commit-to-commit changes in the dataset.
 *
 * Returns all spikes sorted by time (ascending index).
 * Use SPIKE_MAX_CHART_MARKERS to limit chart dots; "View all" shows the full list.
 */
export function detectSpikes(data: TimelineData[]): Spike[] {
  if (!data || data.length < 2) return [];

  // --- Compute all positive deltas across the whole dataset ---
  const positiveDeltas: number[] = [];
  for (let i = 1; i < data.length; i++) {
    const prev = Number(data[i - 1].avg_complexity) || 0;
    const curr = Number(data[i].avg_complexity) || 0;
    const d = curr - prev;
    if (d > 0) positiveDeltas.push(d);
  }

  // 95th-percentile threshold (falls back to 0 when there are no positive deltas)
  const p95 = percentile(positiveDeltas, SPIKE_PERCENTILE_THRESHOLD);

  const spikes: Spike[] = [];

  for (let i = 1; i < data.length; i++) {
    const prev = Number(data[i - 1].avg_complexity) || 0;
    const curr = Number(data[i].avg_complexity) || 0;
    const rawDelta = curr - prev;
    const delta = +rawDelta.toFixed(2);
    const relative = prev > 0 ? (curr - prev) / prev : 0;

    const meetsRelative = relative >= SPIKE_MIN_RELATIVE_INCREASE;
    // Compare raw (unrounded) values against raw thresholds; epsilon guards float noise.
    const EPS = 1e-9;
    const meetsAbsolute = rawDelta >= SPIKE_MIN_ABSOLUTE_INCREASE - EPS;
    const meetsPercentile = rawDelta >= p95 - EPS;

    if (meetsRelative && meetsAbsolute && meetsPercentile) {
      const rawRatio = prev > 0 ? curr / prev : 1;
      const ratio = +(rawRatio % 1 === 0 ? rawRatio.toFixed(0) : rawRatio.toFixed(1));

      spikes.push({
        index: i,
        commit: data[i],
        before: prev,
        after: curr,
        delta,
        ratio,
      });
    }
  }

  return spikes;
}
