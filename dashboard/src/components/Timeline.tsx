'use client';

import { useState, useMemo } from 'react';
import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ReTooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  GitCommit,
  TrendingUp,
  Activity,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  HelpCircle,
  Layers,
  ArrowUpRight,
} from 'lucide-react';
import type { TimelineData } from '@/lib/api';
import { detectSpikes, type Spike, SPIKE_MAX_CHART_MARKERS } from '@/lib/spikes';

interface TimelineProps {
  data: TimelineData[];
  repoUrl?: string;
}

type TimeRange = '30d' | '90d' | '1y' | 'all';

/** |change| below this percent is "steady" — used by verdict, pill and tile color. */
export const STEADY_THRESHOLD_PCT = 10;

export type ChangeDirection = 'steady' | 'up' | 'down';

export function classifyChange(pctChange: number): ChangeDirection {
  if (Math.abs(pctChange) < STEADY_THRESHOLD_PCT) return 'steady';
  return pctChange > 0 ? 'up' : 'down';
}

/** "MMM 'YY", e.g. "Jan '26". */
export function formatMonthYear(timestamp: number): string {
  const d = new Date(timestamp);
  const month = d.toLocaleDateString('en-US', { month: 'short' });
  const year = String(d.getFullYear()).slice(-2);
  return `${month} '${year}`;
}

/** ~count evenly spaced timestamps between min and max (inclusive), de-duplicated by label. */
export function buildTimeTicks(min: number, max: number, count = 7): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [];
  if (max <= min) return [min];
  const ticks: number[] = [];
  const seen = new Set<string>();
  for (let i = 0; i < count; i++) {
    const t = Math.round(min + ((max - min) * i) / (count - 1));
    const label = formatMonthYear(t);
    if (seen.has(label)) continue;
    seen.add(label);
    ticks.push(t);
  }
  return ticks;
}

function formatRelativeDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays <= 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 30) return `${diffDays} days ago`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths === 1) return '1 month ago';
    if (diffMonths < 12) return `${diffMonths} months ago`;
    const diffYears = Math.floor(diffDays / 365);
    if (diffYears === 1) return '1 year ago';
    return `${diffYears} years ago`;
  } catch {
    return dateStr;
  }
}

export function summarizeEvolution(
  data: TimelineData[],
  rangeLabel: string,
  spikesCount: number
): { text: string; status: 'Steady' | 'Rising' | 'Improving'; pctChange: number } {
  if (!data || data.length === 0) {
    return { text: 'No commit evolution data in this period.', status: 'Steady', pctChange: 0 };
  }
  if (data.length === 1) {
    const fCount = data[0].function_count;
    const cVal = (Number(data[0].avg_complexity) || 0).toFixed(1);
    return {
      text: `Single commit tracked with ${fCount} functions and ${cVal} average complexity.`,
      status: 'Steady',
      pctChange: 0,
    };
  }

  const sampleSize = Math.max(1, Math.floor(data.length * 0.1));
  const firstSlice = data.slice(0, sampleSize);
  const lastSlice = data.slice(data.length - sampleSize);

  const avgStart =
    firstSlice.reduce((sum, d) => sum + (Number(d.avg_complexity) || 0), 0) / firstSlice.length;
  const avgEnd =
    lastSlice.reduce((sum, d) => sum + (Number(d.avg_complexity) || 0), 0) / lastSlice.length;

  const firstFunc = data[0].function_count;
  const lastFunc = data[data.length - 1].function_count;

  // "grew" / "shrank" / "stayed flat"
  const growthWord = lastFunc > firstFunc ? 'grew' : lastFunc < firstFunc ? 'shrank' : 'stayed flat';

  // Consistent 10 % threshold for all three states
  const pctChange = avgStart > 0 ? ((avgEnd - avgStart) / avgStart) * 100 : 0;
  const direction = classifyChange(pctChange);

  if (direction === 'steady') {
    // Steady: optionally note if no spikes
    if (rangeLabel !== 'All' && spikesCount === 0) {
      return {
        text: `Things have settled down: no big complexity jumps in the last ${rangeLabel.toLowerCase()}.`,
        status: 'Steady',
        pctChange,
      };
    }
    return {
      text: `Your codebase ${growthWord} from ${firstFunc.toLocaleString()} to ${lastFunc.toLocaleString()} functions while average complexity stayed steady (${avgStart.toFixed(1)} → ${avgEnd.toFixed(1)}).`,
      status: 'Steady',
      pctChange,
    };
  }

  if (direction === 'up') {
    const timeframe = rangeLabel === 'All' ? 'across commit history' : `in the last ${rangeLabel.toLowerCase()}`;
    return {
      text: `Complexity has been rising — up ${Math.round(pctChange)}% ${timeframe}.`,
      status: 'Rising',
      pctChange,
    };
  }

  return {
    text: `Code maintainability has been improving — average complexity decreased from ${avgStart.toFixed(1)} to ${avgEnd.toFixed(1)}.`,
    status: 'Improving',
    pctChange,
  };
}

export default function Timeline({ data, repoUrl }: TimelineProps) {
  const [range, setRange] = useState<TimeRange>('all');
  const [showFunctions, setShowFunctions] = useState(true);
  const [showComplexity, setShowComplexity] = useState(true);
  const [showAllJumps, setShowAllJumps] = useState(false);
  const [jumpsPage, setJumpsPage] = useState(1);
  const [explainerOpen, setExplainerOpen] = useState(false);

  // Filter chronologically and by selected time range
  const filteredData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Ensure sorted chronologically
    const sorted = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    if (range === 'all') return sorted;

    const maxTime = Math.max(...sorted.map(d => new Date(d.date).getTime()));
    const daysMap: Record<TimeRange, number> = {
      '30d': 30,
      '90d': 90,
      '1y': 365,
      all: 0,
    };
    const cutoff = maxTime - daysMap[range] * 24 * 60 * 60 * 1000;
    return sorted.filter(d => new Date(d.date).getTime() >= cutoff);
  }, [data, range]);

  // Detect significant spikes using standardized rules
  const spikes = useMemo(() => {
    return detectSpikes(filteredData);
  }, [filteredData]);

  // Top 5 spikes sorted by absolute increase
  const topSpikes = useMemo(() => {
    return [...spikes].sort((a, b) => b.delta - a.delta).slice(0, 5);
  }, [spikes]);

  // Only the top N spikes (by size) get a marker on the chart; the full list stays in "View all".
  const spikeShaMap = useMemo(() => {
    const map = new Map<string, Spike>();
    [...spikes]
      .sort((a, b) => b.delta - a.delta)
      .slice(0, SPIKE_MAX_CHART_MARKERS)
      .forEach(s => map.set(s.commit.sha, s));
    return map;
  }, [spikes]);

  // Downsample if more than 200 commits, but strictly preserve every spike
  const chartPoints = useMemo(() => {
    if (filteredData.length === 0) return [];

    const mapped = filteredData.map(d => {
      const ts = new Date(d.date).getTime();
      const spike = spikeShaMap.get(d.sha);
      return {
        timestamp: ts,
        date: d.date,
        sha: d.sha,
        message: d.message,
        function_count: Number(d.function_count) || 0,
        avg_complexity: Number(Number(d.avg_complexity || 0).toFixed(2)),
        total_loc: Number(d.total_loc) || 0,
        isSpike: !!spike,
        spikeInfo: spike,
      };
    });

    if (mapped.length <= 200) {
      return mapped;
    }

    // Downsample keeping every Nth item + all spikes + first and last
    const stride = Math.ceil(mapped.length / 150);
    const result = [];
    for (let i = 0; i < mapped.length; i++) {
      if (i === 0 || i === mapped.length - 1 || i % stride === 0 || mapped[i].isSpike) {
        result.push(mapped[i]);
      }
    }
    return result;
  }, [filteredData, spikeShaMap]);

  const timeTicks = useMemo(() => {
    if (chartPoints.length === 0) return [];
    return buildTimeTicks(chartPoints[0].timestamp, chartPoints[chartPoints.length - 1].timestamp, 7);
  }, [chartPoints]);

  const rangeLabel = range === '30d' ? '30 days' : range === '90d' ? '90 days' : range === '1y' ? '1 year' : 'All';
  const verdict = useMemo(() => {
    return summarizeEvolution(filteredData, rangeLabel, spikes.length);
  }, [filteredData, rangeLabel, spikes.length]);

  // Stats calculations
  const stats = useMemo(() => {
    if (filteredData.length === 0) {
      return {
        currentComplexity: 0,
        complexityDelta: 0,
        currentFunctions: 0,
        functionsDelta: 0,
        commitsCount: 0,
        dateRangeText: '—',
        maxComplexity: 0,
      };
    }
    const first = filteredData[0];
    const last = filteredData[filteredData.length - 1];

    const currentComplexity = Number(last.avg_complexity) || 0;
    const startComplexity = Number(first.avg_complexity) || 0;
    const complexityDelta = +(currentComplexity - startComplexity).toFixed(2);

    const currentFunctions = last.function_count;
    const functionsDelta = last.function_count - first.function_count;

    const firstDate = new Date(first.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    const lastDate = new Date(last.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    const dateRangeText = firstDate === lastDate ? firstDate : `${firstDate} – ${lastDate}`;

    const maxComplexity = Math.max(...filteredData.map(d => Number(d.avg_complexity) || 0));

    return {
      currentComplexity,
      complexityDelta,
      currentFunctions,
      functionsDelta,
      commitsCount: filteredData.length,
      dateRangeText,
      maxComplexity,
    };
  }, [filteredData]);

  const commitLink = (sha: string) => {
    if (!repoUrl) return null;
    const cleanUrl = repoUrl.replace(/\.git$/, '');
    return `${cleanUrl}/commit/${sha}`;
  };

  // Custom Dot for Spikes
  const renderCustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    if (!payload || !payload.isSpike) return null;
    return (
      <circle
        key={`spike-${payload.sha}-${cx}`}
        cx={cx}
        cy={cy}
        r={5}
        fill="#FBBF24"
        stroke="#0B0B0D"
        strokeWidth={2}
      />
    );
  };

  // Custom Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const pt = payload[0].payload;
    const spike = pt.spikeInfo;

    return (
      <div className="bg-[#141417] border border-[#2A2A30] rounded-xl p-3.5 shadow-xl max-w-xs text-xs space-y-2">
        <div className="flex items-center justify-between gap-2 border-b border-[#2A2A30] pb-2">
          <div className="flex items-center gap-1.5 font-mono text-[#F4F4F5]">
            <GitCommit className="w-3.5 h-3.5 text-[#A1A1AA]" />
            <span className="font-bold">{pt.sha}</span>
          </div>
          <span className="text-[#A1A1AA]">{new Date(pt.date).toLocaleDateString()}</span>
        </div>

        <p className="text-[#F4F4F5] line-clamp-2 leading-relaxed">{pt.message}</p>

        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between">
            <span className="text-[#A1A1AA]">Total Functions:</span>
            <span className="font-semibold text-[#2DD4BF] font-mono">{pt.function_count.toLocaleString()}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#A1A1AA]">Avg Complexity:</span>
            <span className="font-semibold text-[#60A5FA] font-mono">{pt.avg_complexity.toFixed(2)}</span>
          </div>

          {spike && (
            <div className="mt-2 pt-2 border-t border-[#2A2A30] bg-amber-950/20 -mx-3.5 -mb-3.5 p-3 rounded-b-xl">
              <div className="flex items-center gap-1.5 text-[#FBBF24] font-semibold">
                <span>⚠️ Complexity Spike:</span>
                <span>{spike.before.toFixed(1)} → {spike.after.toFixed(1)}</span>
              </div>
              <p className="text-[11px] text-[#A1A1AA] mt-0.5">
                {spike.ratio}× more complex (+{spike.delta.toFixed(1)} points)
              </p>
            </div>
          )}
        </div>

        <div className="text-[10px] text-[#71717A] pt-1">
          Peak complexity in range: {stats.maxComplexity.toFixed(1)}
        </div>
      </div>
    );
  };

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-[#A1A1AA] bg-[#141417] border border-[#2A2A30] rounded-2xl">
        <Activity className="w-10 h-10 text-[#71717A] mx-auto mb-3" />
        <p className="text-lg font-semibold text-[#F4F4F5]">No evolution data available</p>
        <p className="text-sm text-[#A1A1AA] mt-1">
          Analyze this repository to generate complexity and growth timeline data.
        </p>
      </div>
    );
  }

  // All spikes table pagination
  const JUMPS_PER_PAGE = 10;
  const totalJumpsPages = Math.ceil(spikes.length / JUMPS_PER_PAGE);
  const pagedJumps = spikes.slice((jumpsPage - 1) * JUMPS_PER_PAGE, jumpsPage * JUMPS_PER_PAGE);

  return (
    <div className="w-full space-y-6 text-[#F4F4F5]">
      {/* 1. Header with Time Range Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#2A2A30]">
        <div>
          <h1 className="text-3xl font-bold text-[#F4F4F5] tracking-tight">Evolution Timeline</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">
            How your codebase grew over time — and when it got harder to maintain.
          </p>
        </div>

        {/* Time-range segmented control */}
        <div className="inline-flex items-center bg-[#141417] border border-[#2A2A30] p-1 rounded-xl gap-1 shrink-0 self-start sm:self-auto">
          {(['30d', '90d', '1y', 'all'] as const).map(key => {
            const label = key === '30d' ? '30 days' : key === '90d' ? '90 days' : key === '1y' ? '1 year' : 'All';
            const isActive = range === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => { setRange(key); setJumpsPage(1); }}
                aria-label={`Filter by ${label}`}
                className={`min-h-[44px] px-3.5 py-2 text-xs sm:text-sm font-medium rounded-lg transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-[#2A2A30] text-[#F4F4F5]'
                    : 'text-[#A1A1AA] hover:text-[#F4F4F5] hover:bg-[#1A1A1F]'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Plain-language verdict card */}
      <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <p className="text-base text-[#F4F4F5] font-medium leading-relaxed">
          {verdict.text}
        </p>
        <span
          className={`self-start sm:self-center px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider shrink-0 border ${
            verdict.status === 'Rising'
              ? 'bg-amber-950/40 text-[#FBBF24] border-amber-900/50'
              : verdict.status === 'Improving'
              ? 'bg-emerald-950/40 text-emerald-400 border-emerald-900/50'
              : 'bg-[#1C1C21] text-[#A1A1AA] border-[#2A2A30]'
          }`}
        >
          {verdict.status}
        </span>
      </div>

      {/* 3. Summary tiles (4 tiles in responsive grid) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Average complexity now */}
        <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
              Average complexity now
            </p>
            <p className="text-3xl font-bold text-[#F4F4F5] mt-2 font-mono">
              {stats.currentComplexity.toFixed(1)}
            </p>
          </div>
          <p className="text-xs font-medium mt-3 flex items-center gap-1.5">
            {verdict.status === 'Rising' ? (
              <span className="text-[#FBBF24]">▲ +{stats.complexityDelta} vs. start</span>
            ) : verdict.status === 'Improving' ? (
              <span className="text-emerald-400">▼ {stats.complexityDelta} vs. start</span>
            ) : (
              <span className="text-[#A1A1AA]">
                → {stats.complexityDelta > 0 ? '+' : ''}{stats.complexityDelta} vs. start
              </span>
            )}
          </p>
        </div>

        {/* Functions now */}
        <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
              Functions now
            </p>
            <p className="text-3xl font-bold text-[#F4F4F5] mt-2 font-mono">
              {stats.currentFunctions.toLocaleString()}
            </p>
          </div>
          <p className="text-xs text-[#A1A1AA] mt-3">
            {stats.functionsDelta >= 0 ? `+${stats.functionsDelta}` : stats.functionsDelta} since start
          </p>
        </div>

        {/* Commits analyzed */}
        <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
              Commits analyzed
            </p>
            <p className="text-3xl font-bold text-[#F4F4F5] mt-2 font-mono">
              {stats.commitsCount}
            </p>
          </div>
          <p className="text-xs text-[#A1A1AA] mt-3 truncate" title={stats.dateRangeText}>
            {stats.dateRangeText}
          </p>
        </div>

        {/* Big jumps */}
        <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              {spikes.length > 0 && <span className="w-2.5 h-2.5 rounded-full bg-[#FBBF24]" />}
              <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                Big jumps
              </p>
            </div>
            <p className="text-3xl font-bold text-[#F4F4F5] mt-2 font-mono">
              {spikes.length}
            </p>
          </div>
          <p className="text-xs text-[#A1A1AA] mt-3">
            commits that made code much harder to read
          </p>
        </div>
      </div>

      {/* 4. Combined chart: Growth vs. complexity */}
      <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-[#F4F4F5]">Growth vs. complexity</h3>
            <p className="text-xs text-[#A1A1AA] mt-0.5">
              Cumulative function growth (teal) alongside average cyclomatic complexity (blue).
            </p>
          </div>

          {/* Interactive Legend with Toggles */}
          <div className="flex items-center gap-3 text-xs flex-wrap">
            <button
              type="button"
              onClick={() => setShowFunctions(!showFunctions)}
              aria-label="Toggle functions series"
              className={`min-h-[44px] px-3 py-1.5 rounded-lg border transition-all flex items-center gap-2 cursor-pointer ${
                showFunctions
                  ? 'bg-teal-950/30 border-teal-800 text-[#2DD4BF]'
                  : 'bg-[#141417] border-[#2A2A30] text-[#71717A]'
              }`}
            >
              <span className="w-2.5 h-2.5 rounded-sm bg-[#2DD4BF]" />
              <span>Functions</span>
            </button>

            <button
              type="button"
              onClick={() => setShowComplexity(!showComplexity)}
              aria-label="Toggle complexity series"
              className={`min-h-[44px] px-3 py-1.5 rounded-lg border transition-all flex items-center gap-2 cursor-pointer ${
                showComplexity
                  ? 'bg-blue-950/30 border-blue-800 text-[#60A5FA]'
                  : 'bg-[#141417] border-[#2A2A30] text-[#71717A]'
              }`}
            >
              <span className="w-2.5 h-1 bg-[#3B82F6] rounded-full" />
              <span>Complexity</span>
            </button>

            {spikes.length > 0 && (
              <span className="inline-flex items-center gap-1.5 text-xs text-[#FBBF24] ml-1">
                <span className="w-2.5 h-2.5 rounded-full bg-[#FBBF24]" />
                <span>Spike ({spikes.length})</span>
              </span>
            )}
          </div>
        </div>

        {/* Chart View */}
        <div className="w-full h-[320px]" aria-label="Code evolution chart showing functions growth and complexity trends">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartPoints} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="tealAreaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2DD4BF" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#2DD4BF" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A2A30" opacity={0.6} vertical={false} />

              {/* Real time scale X-axis */}
              <XAxis
                type="number"
                dataKey="timestamp"
                domain={['dataMin', 'dataMax']}
                scale="time"
                ticks={timeTicks}
                interval={0}
                tickFormatter={formatMonthYear}
                stroke="#71717A"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#2A2A30' }}
              />

              {/* Left Y-axis: Functions */}
              <YAxis
                yAxisId="left"
                stroke="#2DD4BF"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                domain={[0, 'auto']}
                tickFormatter={val => (val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val)}
              />

              {/* Right Y-axis: Complexity */}
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#3B82F6"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                domain={[0, (dataMax: number) => Math.ceil(Math.max((Number(dataMax) || 0) * 1.15, 4))]}
                tickFormatter={val => val.toFixed(1)}
              />

              <ReTooltip content={<CustomTooltip />} />

              {/* Functions Area */}
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="function_count"
                stroke="#2DD4BF"
                strokeWidth={2}
                fill="url(#tealAreaGrad)"
                name="Functions"
                hide={!showFunctions}
                isAnimationActive={false}
              />

              {/* Complexity Line */}
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="avg_complexity"
                stroke="#3B82F6"
                strokeWidth={2.5}
                dot={renderCustomDot}
                name="Complexity"
                connectNulls={true}
                hide={!showComplexity}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 5. "Biggest jumps" (top 5 spikes) */}
      <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 space-y-4">
        <div>
          <h3 className="text-base font-bold text-[#F4F4F5]">Biggest jumps</h3>
          <p className="text-xs text-[#A1A1AA] mt-0.5">
            Commits that produced the steepest increases in codebase complexity.
          </p>
        </div>

        {spikes.length === 0 ? (
          <div className="py-8 px-4 rounded-xl border border-[#2A2A30] bg-[#0B0B0D] flex items-center justify-center gap-2.5 text-sm text-[#A1A1AA]">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>No big complexity jumps in this period</span>
          </div>
        ) : (
          <div className="space-y-2.5">
            {topSpikes.map(spike => {
              const url = commitLink(spike.commit.sha);
              const Comp = url ? 'a' : 'div';
              return (
                <Comp
                  key={`top-spike-${spike.commit.sha}`}
                  {...(url ? { href: url, target: '_blank', rel: 'noopener noreferrer' } : {})}
                  className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 bg-[#0B0B0D] border border-[#2A2A30] hover:border-[#3F3F46] rounded-xl transition-all"
                >
                  {/* Left: Message, short hash pill, relative date */}
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#141417] text-[#A1A1AA] border border-[#2A2A30] shrink-0">
                      {spike.commit.sha}
                    </span>
                    <span className="font-semibold text-sm text-[#F4F4F5] truncate group-hover:text-blue-400 transition-colors">
                      {spike.commit.message}
                    </span>
                    <span
                      className="text-xs text-[#71717A] shrink-0 hidden md:inline-block"
                      title={new Date(spike.commit.date).toLocaleString()}
                    >
                      {formatRelativeDate(spike.commit.date)}
                    </span>
                  </div>

                  {/* Right: before -> after + ratio pill */}
                  <div className="flex items-center gap-2.5 shrink-0 self-end sm:self-auto">
                    <span className="text-xs font-mono text-[#A1A1AA]">
                      {spike.before.toFixed(1)} → <strong className="text-[#F4F4F5]">{spike.after.toFixed(1)}</strong>
                    </span>
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/40 text-[#FBBF24] border border-amber-900/50">
                      {spike.ratio}× more complex
                    </span>
                    {url && <ExternalLink className="w-3.5 h-3.5 text-[#71717A] group-hover:text-[#F4F4F5] transition-colors" />}
                  </div>
                </Comp>
              );
            })}

            {/* View all jumps button */}
            {spikes.length > 5 && (
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setShowAllJumps(!showAllJumps)}
                  aria-expanded={showAllJumps}
                  className="min-h-[44px] w-full px-4 py-2.5 rounded-xl border border-[#2A2A30] bg-[#0B0B0D] hover:bg-[#1C1C21] hover:border-[#3F3F46] text-sm font-medium text-[#F4F4F5] flex items-center justify-center gap-2 transition-all cursor-pointer"
                >
                  <span>{showAllJumps ? 'Hide all jumps' : `View all ${spikes.length} jumps`}</span>
                  {showAllJumps ? <ChevronUp className="w-4 h-4 text-[#A1A1AA]" /> : <ChevronDown className="w-4 h-4 text-[#A1A1AA]" />}
                </button>
              </div>
            )}

            {/* Expanded table of all spikes */}
            {showAllJumps && spikes.length > 0 && (
              <div className="pt-3 space-y-3">
                <div className="overflow-x-auto rounded-xl border border-[#2A2A30]">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-[#0B0B0D] border-b border-[#2A2A30] text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                        <th className="text-left py-2.5 px-3">Commit</th>
                        <th className="text-left py-2.5 px-3">Message</th>
                        <th className="text-left py-2.5 px-3">Date</th>
                        <th className="text-right py-2.5 px-3">Before</th>
                        <th className="text-right py-2.5 px-3">After</th>
                        <th className="text-right py-2.5 px-3">Change</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#2A2A30]/60 bg-[#141417]">
                      {pagedJumps.map(s => {
                        const url = commitLink(s.commit.sha);
                        return (
                          <tr key={`all-spike-${s.commit.sha}`} className="hover:bg-[#1C1C21] transition-colors">
                            <td className="py-2.5 px-3 font-mono text-xs text-blue-400">
                              {url ? (
                                <a href={url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                                  {s.commit.sha}
                                </a>
                              ) : (
                                s.commit.sha
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-[#F4F4F5] max-w-xs truncate" title={s.commit.message}>
                              {s.commit.message}
                            </td>
                            <td className="py-2.5 px-3 text-[#A1A1AA] text-xs whitespace-nowrap">
                              {new Date(s.commit.date).toLocaleDateString()}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono text-xs text-[#A1A1AA]">
                              {s.before.toFixed(1)}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono text-xs text-[#F4F4F5]">
                              {s.after.toFixed(1)}
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/40 text-[#FBBF24] border border-amber-900/50">
                                {s.ratio}× (+{s.delta.toFixed(1)})
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Table pagination */}
                {totalJumpsPages > 1 && (
                  <div className="flex items-center justify-between text-xs text-[#A1A1AA] pt-1">
                    <span>
                      Page {jumpsPage} of {totalJumpsPages}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setJumpsPage(p => Math.max(1, p - 1))}
                        disabled={jumpsPage === 1}
                        className="min-h-[44px] px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#0B0B0D] hover:bg-[#1C1C21] disabled:opacity-40 text-[#F4F4F5] cursor-pointer"
                      >
                        Previous
                      </button>
                      <button
                        type="button"
                        onClick={() => setJumpsPage(p => Math.min(totalJumpsPages, p + 1))}
                        disabled={jumpsPage === totalJumpsPages}
                        className="min-h-[44px] px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#0B0B0D] hover:bg-[#1C1C21] disabled:opacity-40 text-[#F4F4F5] cursor-pointer"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 6. Explainer section at the bottom (collapsible, closed by default) */}
      <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl overflow-hidden transition-all">
        <button
          type="button"
          onClick={() => setExplainerOpen(!explainerOpen)}
          aria-expanded={explainerOpen}
          aria-label="Toggle explanation of numbers"
          className="min-h-[44px] w-full px-6 py-4 flex items-center justify-between text-left hover:bg-[#1C1C21] transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2.5">
            <HelpCircle className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-[#F4F4F5]">What do these numbers mean?</h2>
          </div>
          {explainerOpen ? (
            <ChevronUp className="w-4 h-4 text-[#A1A1AA]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#A1A1AA]" />
          )}
        </button>

        {explainerOpen && (
          <div className="px-6 pb-5 pt-1 border-t border-[#2A2A30] space-y-3 text-xs sm:text-sm text-[#A1A1AA] leading-relaxed">
            <p>
              <strong className="text-[#F4F4F5]">Complexity:</strong> how many decision paths (if/else, loops) a function has on average. Higher = harder to read and test.
            </p>
            <p>
              <strong className="text-[#F4F4F5]">Functions:</strong> the total number of functions in the codebase at that commit.
            </p>
            <p>
              <strong className="text-[#F4F4F5]">Big jump:</strong> a single commit that made average complexity rise sharply.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
