import type { TimelineData } from './api';

// Configurable constants for spike detection
export const MIN_RELATIVE_INCREASE = 0.5; // >= 50% increase
export const MIN_ABSOLUTE_INCREASE = 1.0;  // Absolute delta >= 1.0
export const MIN_BASELINE_COMPLEXITY = 1.0; // Baselines below 1.0 (e.g. 0.5 -> 4.0) must NOT count

export interface Spike {
  index: number;
  commit: TimelineData;
  before: number;
  after: number;
  delta: number;
  ratio: number;
}

export interface SpikeDetectionOptions {
  minRelative?: number;
  minAbsolute?: number;
  minBaseline?: number;
  requireAboveMedian?: boolean;
}

export function calculateMedianComplexity(data: TimelineData[]): number {
  if (!data || data.length === 0) return 0;
  const sorted = data.map(d => Number(d.avg_complexity) || 0).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Detect significant complexity spikes across commit timeline.
 * A commit counts as a spike ONLY when:
 * 1. Relative increase >= minRelative (default 50%)
 * 2. Absolute increase >= minAbsolute (default 1.0)
 * 3. Baseline is not tiny (before >= minBaseline, default 1.0)
 * 4. (Optional) after >= median repo complexity
 */
export function detectSpikes(
  data: TimelineData[],
  options?: SpikeDetectionOptions
): Spike[] {
  if (!data || data.length < 2) return [];

  const minRelative = options?.minRelative ?? MIN_RELATIVE_INCREASE;
  const minAbsolute = options?.minAbsolute ?? MIN_ABSOLUTE_INCREASE;
  const minBaseline = options?.minBaseline ?? MIN_BASELINE_COMPLEXITY;
  const median = options?.requireAboveMedian ? calculateMedianComplexity(data) : 0;

  const spikes: Spike[] = [];

  for (let i = 1; i < data.length; i++) {
    const prev = Number(data[i - 1].avg_complexity) || 0;
    const curr = Number(data[i].avg_complexity) || 0;

    // Filter out tiny baselines (e.g., 0.5 -> 4.0 must NOT count)
    if (prev < minBaseline) {
      continue;
    }

    const delta = +(curr - prev).toFixed(2);
    const relative = prev > 0 ? (curr - prev) / prev : 0;

    const meetsRelative = relative >= minRelative;
    const meetsAbsolute = delta >= minAbsolute;
    const meetsMedian = !options?.requireAboveMedian || curr >= median;

    if (meetsRelative && meetsAbsolute && meetsMedian) {
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

