import { test } from 'node:test';
import assert from 'node:assert/strict';

// Import our TypeScript module compiled or replicated test
import {
  detectSpikes,
  MIN_RELATIVE_INCREASE,
  MIN_ABSOLUTE_INCREASE,
  MIN_BASELINE_COMPLEXITY,
} from './spikes.ts';

test('constants have expected values', () => {
  assert.equal(MIN_RELATIVE_INCREASE, 0.5);
  assert.equal(MIN_ABSOLUTE_INCREASE, 1.0);
  assert.equal(MIN_BASELINE_COMPLEXITY, 1.0);
});

test('tiny baseline jump (0.5 -> 4.0) must NOT count as a spike', () => {
  const data = [
    { sha: 'aaa', message: 'init', date: '2025-01-01', function_count: 5, avg_complexity: 0.5, total_loc: 50 },
    { sha: 'bbb', message: 'jump', date: '2025-01-02', function_count: 10, avg_complexity: 4.0, total_loc: 100 },
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 0, 'Tiny baseline 0.5 -> 4.0 must NOT be counted as a spike');
});

test('real jump (2.1 -> 6.3) must count as a spike with ratio 3x', () => {
  const data = [
    { sha: 'aaa', message: 'init', date: '2025-01-01', function_count: 50, avg_complexity: 2.1, total_loc: 500 },
    { sha: 'bbb', message: 'refactor', date: '2025-01-02', function_count: 60, avg_complexity: 6.3, total_loc: 700 },
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 1);
  assert.equal(spikes[0].before, 2.1);
  assert.equal(spikes[0].after, 6.3);
  assert.equal(spikes[0].delta, 4.2);
  assert.equal(spikes[0].ratio, 3);
});

test('small absolute increase (3.0 -> 3.5) must NOT count as a spike', () => {
  const data = [
    { sha: 'aaa', message: 'init', date: '2025-01-01', function_count: 50, avg_complexity: 3.0, total_loc: 500 },
    { sha: 'bbb', message: 'edit', date: '2025-01-02', function_count: 55, avg_complexity: 3.5, total_loc: 550 },
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 0, 'Delta 0.5 is less than minAbsolute 1.0');
});

test('small relative increase (10.0 -> 12.0) must NOT count as a spike', () => {
  const data = [
    { sha: 'aaa', message: 'init', date: '2025-01-01', function_count: 100, avg_complexity: 10.0, total_loc: 2000 },
    { sha: 'bbb', message: 'edit', date: '2025-01-02', function_count: 105, avg_complexity: 12.0, total_loc: 2200 },
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 0, 'Relative increase 20% is less than minRelative 50%');
});

test('multiple commits timeline detects only genuine spikes', () => {
  const data = [
    { sha: 'c1', message: 'init', date: '2025-01-01', function_count: 10, avg_complexity: 0.5, total_loc: 100 },
    { sha: 'c2', message: 'early jump', date: '2025-01-02', function_count: 15, avg_complexity: 4.0, total_loc: 200 }, // tiny baseline (0.5) -> skipped
    { sha: 'c3', message: 'stable', date: '2025-01-03', function_count: 20, avg_complexity: 4.2, total_loc: 250 },     // small delta -> skipped
    { sha: 'c4', message: 'big jump 1', date: '2025-01-04', function_count: 30, avg_complexity: 8.4, total_loc: 400 },  // 4.2 -> 8.4 (100% inc, delta 4.2) -> SPIKE 1
    { sha: 'c5', message: 'stable', date: '2025-01-05', function_count: 35, avg_complexity: 8.5, total_loc: 450 },     // small delta -> skipped
    { sha: 'c6', message: 'big jump 2', date: '2025-01-06', function_count: 40, avg_complexity: 17.0, total_loc: 600 }, // 8.5 -> 17.0 (100% inc, delta 8.5) -> SPIKE 2
  ];
  const spikes = detectSpikes(data);
  assert.equal(spikes.length, 2);
  assert.equal(spikes[0].commit.sha, 'c4');
  assert.equal(spikes[0].ratio, 2);
  assert.equal(spikes[1].commit.sha, 'c6');
  assert.equal(spikes[1].ratio, 2);
});

