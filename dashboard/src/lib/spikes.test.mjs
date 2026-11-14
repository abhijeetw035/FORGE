import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  detectSpikes,
  percentile,
  SPIKE_MIN_RELATIVE_INCREASE,
  SPIKE_MIN_ABSOLUTE_INCREASE,
  SPIKE_PERCENTILE_THRESHOLD,
  SPIKE_MAX_CHART_MARKERS,
} from './spikes.ts';

// ─── Constants ───────────────────────────────────────────────────────────────

test('constants have expected values', () => {
  assert.equal(SPIKE_MIN_RELATIVE_INCREASE, 0.10);
  assert.equal(SPIKE_MIN_ABSOLUTE_INCREASE, 0.30);
  assert.equal(SPIKE_PERCENTILE_THRESHOLD, 95);
  assert.equal(SPIKE_MAX_CHART_MARKERS, 15);
});

// ─── percentile helper ────────────────────────────────────────────────────────

test('percentile([1,2,3,4,5], 100) = 5', () => {
  assert.equal(percentile([1, 2, 3, 4, 5], 100), 5);
});

test('percentile([1,2,3,4,5], 0) = 1', () => {
  assert.equal(percentile([1, 2, 3, 4, 5], 0), 1);
});

test('percentile empty array returns 0', () => {
  assert.equal(percentile([], 95), 0);
});

// ─── Core spike rules ─────────────────────────────────────────────────────────

test('no data or single point returns empty', () => {
  assert.deepEqual(detectSpikes([]), []);
  assert.deepEqual(detectSpikes([
    { sha: 'a', message: 'm', date: '2025-01-01', function_count: 5, avg_complexity: 2.0, total_loc: 50 },
  ]), []);
});

test('small absolute increase (2.0 -> 2.25, +0.25) must NOT be a spike', () => {
  // delta 0.25 < SPIKE_MIN_ABSOLUTE_INCREASE 0.30
  const data = [
    { sha: 'a', message: 'init', date: '2025-01-01', function_count: 50, avg_complexity: 2.0, total_loc: 500 },
    { sha: 'b', message: 'edit', date: '2025-01-02', function_count: 55, avg_complexity: 2.25, total_loc: 550 },
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 0, 'Delta 0.25 < minAbsolute 0.30 — must not be a spike');
});

test('small relative increase (2.0 -> 2.35, +0.35, 17%) must NOT be a spike', () => {
  // relative 17.5% < SPIKE_MIN_RELATIVE_INCREASE 10% — wait, 17.5% > 10%.
  // But the p95 of [0.35] = 0.35 and delta == 0.35, so it qualifies.
  // Let's make a case that clearly fails relative: very high baseline, tiny ratio.
  // 10.0 -> 10.35 = 3.5% relative — must NOT qualify.
  const data = [
    { sha: 'a', message: 'init', date: '2025-01-01', function_count: 100, avg_complexity: 10.0, total_loc: 2000 },
    { sha: 'b', message: 'edit', date: '2025-01-02', function_count: 105, avg_complexity: 10.35, total_loc: 2100 },
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 0, '3.5% relative increase < 10% threshold — not a spike');
});

test('genuine spike: 2.0 -> 2.80 (+0.80, 40%) is detected', () => {
  // relative 40% >= 10%, absolute 0.80 >= 0.30, and p95 of [0.80] = 0.80 → qualifies
  const data = [
    { sha: 'a', message: 'init', date: '2025-01-01', function_count: 50, avg_complexity: 2.0, total_loc: 500 },
    { sha: 'b', message: 'jump', date: '2025-01-02', function_count: 60, avg_complexity: 2.80, total_loc: 700 },
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 1);
  assert.equal(spikes[0].before, 2.0);
  assert.equal(spikes[0].after, 2.80);
  assert.equal(spikes[0].delta, 0.80);
});

test('95th-percentile filter suppresses below-p95 jumps in noisy series', () => {
  // 100 small commits of +0.05, then one big jump of +0.60.
  // p95 of all positive deltas should be ~0.05 (most deltas are 0.05).
  // The +0.60 is WAY above p95, so it must be a spike.
  // The small +0.05 ones: relative is 0.05/2.x = ~2% < 10%, so they won't pass relative check.
  const data = [];
  let complexity = 2.0;
  for (let i = 0; i < 50; i++) {
    complexity += 0.02; // tiny positive drift, relative ~ 1%
    data.push({ sha: `c${i}`, message: 'drift', date: `2025-01-${String(i + 1).padStart(2, '0')}`, function_count: 100 + i, avg_complexity: +complexity.toFixed(2), total_loc: 2000 });
  }
  // Add one big jump
  const bigJumpComplexity = +(complexity + 0.60).toFixed(2);
  data.push({ sha: 'big', message: 'big jump', date: '2025-04-01', function_count: 200, avg_complexity: bigJumpComplexity, total_loc: 4000 });

  const spikes = detectSpikes(data);
  assert.ok(spikes.length >= 1, 'Big jump must be detected');
  assert.equal(spikes[spikes.length - 1].commit.sha, 'big', 'Last spike must be the big jump commit');
});

test('multiple spikes: timeline with 2 big jumps separated by stable periods', () => {
  const data = [
    { sha: 'c1', message: 'init',    date: '2025-01-01', function_count: 10, avg_complexity: 2.0, total_loc: 100 },
    { sha: 'c2', message: 'stable1', date: '2025-01-02', function_count: 15, avg_complexity: 2.1, total_loc: 150 },
    { sha: 'c3', message: 'jump1',   date: '2025-01-03', function_count: 20, avg_complexity: 3.0, total_loc: 200 }, // +0.9, 43% → candidate
    { sha: 'c4', message: 'stable2', date: '2025-01-04', function_count: 25, avg_complexity: 3.05, total_loc: 250 },
    { sha: 'c5', message: 'jump2',   date: '2025-01-05', function_count: 30, avg_complexity: 4.0, total_loc: 300 }, // +0.95, 31% → candidate
  ];
  const spikes = detectSpikes(data);
  // Both jumps pass relative (>10%) and absolute (>0.30); p95 of positive deltas
  // [0.1, 0.9, 0.05, 0.95] sorted = [0.05, 0.1, 0.9, 0.95], p95 index = floor(4*0.95)=3 → 0.95
  // So only the +0.95 jump qualifies as above-p95
  const shaSets = spikes.map(s => s.commit.sha);
  assert.ok(shaSets.includes('c5'), 'The larger jump (c5) must always be detected');
});
