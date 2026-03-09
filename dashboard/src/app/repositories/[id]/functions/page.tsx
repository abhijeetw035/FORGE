'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  ChevronDown,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRightLeft,
  Pencil,
  GitCommit,
  GitBranch,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as ReTooltip,
  ResponsiveContainer,
  ReferenceDot,
} from 'recharts';
import { getRepositoryFunctionEvolution, getRepository } from '@/lib/api';
import type { FunctionEvolutionData, FunctionVersionData } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import type { Repository } from '@/types';

// ── Complexity Trend chart ────────────────────────────────────────────────────
function ComplexityChart({ versions }: { versions: FunctionVersionData[] }) {
  const points = [...versions]
    .sort((a, b) => new Date(a.timestamp ?? 0).getTime() - new Date(b.timestamp ?? 0).getTime())
    .map(v => ({
      date: v.timestamp
        ? new Date(v.timestamp).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
        : '—',
      complexity: v.complexity,
    }));

  if (points.length < 2)
    return <p className="text-xs text-zinc-500 py-4 text-center">Not enough data for a trend</p>;

  const last = points[points.length - 1];

  return (
    <div className="mt-4 bg-zinc-900 border border-zinc-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-zinc-200 mb-4">Complexity Trend</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={points} margin={{ top: 12, right: 40, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="cxGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} width={26} />
          <ReTooltip
            contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#e4e4e7' }}
            itemStyle={{ color: '#60a5fa' }}
          />
          <Area
            type="monotone"
            dataKey="complexity"
            stroke="#3b82f6"
            strokeWidth={2.5}
            fill="url(#cxGrad)"
            dot={{ r: 4, fill: '#3b82f6', stroke: '#1d4ed8', strokeWidth: 1.5 }}
            activeDot={{ r: 5 }}
          />
          <ReferenceDot
            x={last.date}
            y={last.complexity}
            r={0}
            label={{
              value: last.complexity.toFixed(1),
              position: 'right',
              fontSize: 12,
              fill: '#fff',
              fontWeight: 700,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Function Timeline (right panel) ─────────────────────────────────────────
function FunctionTimeline({ entry, repoUrl }: { entry: FunctionEvolutionData | null; repoUrl: string }) {
  const [dropSearch, setDropSearch] = useState('');
  // entry is controlled by parent; this component only renders the timeline list
  if (!entry) return (
    <div className="flex flex-col items-center justify-center h-40 text-zinc-500 text-sm gap-2">
      <GitBranch className="w-7 h-7 opacity-30" />
      <span>Select a function to see its timeline</span>
    </div>
  );

  const sorted = [...entry.versions].sort(
    (a, b) => new Date(b.timestamp ?? 0).getTime() - new Date(a.timestamp ?? 0).getTime()
  );
  const fmtLong = (ts: string | null) =>
    ts ? new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';

  // Build a GitHub commit link from the repo url + sha
  const commitUrl = (sha: string) => {
    const base = repoUrl.replace(/\.git$/, '');
    return `${base}/commit/${sha}`;
  };

  return (
    <div className="overflow-y-auto max-h-[560px] pr-1">
      <ol className="relative border-l-2 border-zinc-700 ml-2">
        {sorted.map((v, i) => (
          <li key={`${v.commit_sha}-${i}`} className="relative mb-6 pl-6">
            <span className="absolute left-[-9px] top-1 w-4 h-4 rounded-full bg-blue-500 ring-4 ring-zinc-900 flex-shrink-0" />
            <p className="text-xs text-zinc-500 mb-0.5">{fmtLong(v.timestamp)}</p>
            <p className="text-sm text-zinc-100 font-medium leading-snug line-clamp-2">
              {v.commit_message || 'No message'}
            </p>
            <div className="flex flex-wrap gap-3 mt-1 text-xs">
              <a
                href={commitUrl(v.commit_sha)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="font-mono text-blue-400 hover:text-blue-300 hover:underline transition-colors"
                title={`Open commit ${v.commit_sha} on GitHub`}
              >
                {v.commit_sha.slice(0, 7)}
              </a>
              <span className="text-green-400">+{v.start_line}</span>
              <span className="text-red-400">-{v.end_line}</span>
              <span className="text-zinc-400">~{v.complexity.toFixed(1)} cplx</span>
            </div>
          </li>
        ))}
        {/* Created marker */}
        <li className="relative pl-6">
          <span className="absolute left-[-9px] top-1 w-4 h-4 rounded-full bg-zinc-600 ring-4 ring-zinc-900 flex-shrink-0" />
          <p className="text-xs text-zinc-500">
            {fmtLong(entry.first_seen_ts)} · Created
          </p>
        </li>
      </ol>

      <div className="mt-4 pt-3 border-t border-zinc-800">
        <span className="text-xs text-blue-400 font-semibold">Complexity </span>
        <span className="text-xs text-zinc-400">
          {entry.versions[0]?.complexity ?? '—'} &nbsp;·&nbsp; {entry.commit_count} commits
        </span>
      </div>
    </div>
  );
}

interface PageProps {
  params: Promise<{ id: string }>;
}

const ITEMS_PER_PAGE = 10;

function TrendIcon({ trend }: { trend: 'increasing' | 'decreasing' | 'stable' }) {
  if (trend === 'increasing')
    return <TrendingUp className="w-4 h-4 text-red-400" />;
  if (trend === 'decreasing')
    return <TrendingDown className="w-4 h-4 text-green-400" />;
  return <Minus className="w-4 h-4 text-zinc-500" />;
}

function VersionRow({ v, index }: { v: FunctionVersionData; index: number }) {
  const date = v.timestamp ? new Date(v.timestamp).toLocaleDateString() : '—';
  return (
    <tr className={index % 2 === 0 ? 'bg-zinc-900/40' : 'bg-zinc-900/20'}>
      <td className="px-4 py-2 font-mono text-xs text-zinc-400">{v.commit_sha}</td>
      <td className="px-4 py-2 text-xs text-zinc-300">{date}</td>
      <td className="px-4 py-2 text-xs text-zinc-400 max-w-xs truncate">{v.commit_author}</td>
      <td className="px-4 py-2 text-xs text-zinc-400 max-w-sm truncate">{v.commit_message}</td>
      <td className="px-4 py-2 text-xs font-mono text-zinc-500 truncate max-w-xs">{v.file_path.split('/').slice(-2).join('/')}</td>
      <td className="px-4 py-2 text-xs text-center">
        <span
          className={`font-semibold ${
            v.complexity > 10 ? 'text-red-400' : v.complexity > 5 ? 'text-orange-400' : 'text-green-400'
          }`}
        >
          {v.complexity}
        </span>
      </td>
    </tr>
  );
}

function FunctionRow({ entry, isSelected = false, onSelect }: {
  entry: FunctionEvolutionData;
  isSelected?: boolean;
  onSelect?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const fileName = entry.file_path.split('/').pop() ?? entry.file_path;
  const firstDate = entry.first_seen_ts
    ? new Date(entry.first_seen_ts).toLocaleDateString()
    : '—';
  const lastDate = entry.last_seen_ts
    ? new Date(entry.last_seen_ts).toLocaleDateString()
    : '—';

  return (
    <>
      <tr
        className={`border-b border-zinc-800 cursor-pointer transition-colors ${
          isSelected
            ? 'bg-blue-500/10 border-l-2 border-l-blue-500'
            : 'hover:bg-zinc-800/40'
        }`}
        onClick={() => { setExpanded(e => !e); onSelect?.(); }}
      >
        {/* expand toggle */}
        <td className="px-4 py-3 w-8 text-zinc-500">
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </td>

        {/* function name */}
        <td className="px-4 py-3">
          <span className="font-mono text-sm text-white">{entry.name}</span>
        </td>

        {/* file */}
        <td className="px-4 py-3 text-sm text-zinc-400 truncate max-w-[220px]" title={entry.file_path}>
          {fileName}
        </td>

        {/* badges */}
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            {entry.was_moved && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/30">
                <ArrowRightLeft className="w-3 h-3" /> moved
              </span>
            )}
            {entry.was_renamed && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-yellow-500/15 text-yellow-400 border border-yellow-500/30">
                <Pencil className="w-3 h-3" /> renamed
              </span>
            )}
          </div>
        </td>

        {/* commit count */}
        <td className="px-4 py-3 text-center">
          <span className="flex items-center justify-center gap-1 text-sm text-zinc-300">
            <GitCommit className="w-3.5 h-3.5 text-zinc-500" />
            {entry.commit_count}
          </span>
        </td>

        {/* complexity trend */}
        <td className="px-4 py-3">
          <div className="flex items-center gap-1.5">
            <TrendIcon trend={entry.complexity_trend} />
            <span className="text-sm text-zinc-400">
              {entry.complexity_trend}
              {entry.complexity_delta !== 0 && (
                <span className={entry.complexity_delta > 0 ? 'text-red-400 ml-1' : 'text-green-400 ml-1'}>
                  ({entry.complexity_delta > 0 ? '+' : ''}{entry.complexity_delta})
                </span>
              )}
            </span>
          </div>
        </td>

        {/* lifespan */}
        <td className="px-4 py-3 text-xs text-zinc-500 whitespace-nowrap">
          {firstDate} → {lastDate}
        </td>
      </tr>

      {/* expanded version history */}
      {expanded && (
        <tr>
          <td colSpan={7} className="px-0 py-0">
            <div className="bg-zinc-950 border-b border-zinc-800 px-8 py-4">
              <p className="text-xs text-zinc-500 mb-3 uppercase tracking-wider font-semibold">
                Version History — {entry.versions.length} commit{entry.versions.length !== 1 ? 's' : ''}
              </p>
              <div className="overflow-x-auto rounded-lg border border-zinc-800">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-zinc-700 bg-zinc-900">
                      <th className="px-4 py-2 text-xs text-zinc-500 font-medium">SHA</th>
                      <th className="px-4 py-2 text-xs text-zinc-500 font-medium">Date</th>
                      <th className="px-4 py-2 text-xs text-zinc-500 font-medium">Author</th>
                      <th className="px-4 py-2 text-xs text-zinc-500 font-medium">Message</th>
                      <th className="px-4 py-2 text-xs text-zinc-500 font-medium">File</th>
                      <th className="px-4 py-2 text-xs text-zinc-500 font-medium text-center">Complexity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entry.versions.map((v, i) => (
                      <VersionRow key={`${v.commit_sha}-${i}`} v={v} index={i} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function FunctionsPage({ params }: PageProps) {
  const [id, setId] = useState<string>('');
  const [data, setData] = useState<FunctionEvolutionData[]>([]);
  const [repo, setRepo] = useState<Repository | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<'all' | 'moved' | 'renamed' | 'increasing'>('all');
  const [selected, setSelected] = useState<FunctionEvolutionData | null>(null);
  const [timelineDropSearch, setTimelineDropSearch] = useState('');
  const [showTimelineDrop, setShowTimelineDrop] = useState(false);
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  useEffect(() => {
    params.then(p => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) { router.push('/login'); return; }
    if (!id) return;

    getRepositoryFunctionEvolution(id)
      .then(d => { setData(d); if (d.length > 0) setSelected(d[0]); })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setIsLoading(false));

    getRepository(id).then(setRepo).catch(() => {});
  }, [id, isAuthenticated, authLoading, router]);

  const filtered = data.filter(e => {
    if (filter === 'moved')     return e.was_moved;
    if (filter === 'renamed')   return e.was_renamed;
    if (filter === 'increasing') return e.complexity_trend === 'increasing';
    return true;
  });

  const dropOptions = useMemo(() => {
    const q = timelineDropSearch.toLowerCase();
    return data.filter(e => e.name.toLowerCase().includes(q)).slice(0, 40);
  }, [data, timelineDropSearch]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const pageData   = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const filterBtn = (value: typeof filter, label: string) => (
    <button
      onClick={() => { setFilter(value); setPage(1); }}
      className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
        filter === value
          ? 'bg-blue-500/20 text-blue-400 border-blue-500/40'
          : 'text-zinc-400 border-zinc-700 hover:border-zinc-500 hover:text-white'
      }`}
    >
      {label}
    </button>
  );

  if (isLoading || authLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-zinc-400">Loading function evolution…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-1">Function Evolution</h1>
        <p className="text-zinc-400 text-sm">
          Track how each function evolves across commits — moves, renames, and complexity drift.
          Identity is computed from AST content hashes, not line numbers.
        </p>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Tracked Functions', value: data.length },
          { label: 'Moved', value: data.filter(e => e.was_moved).length },
          { label: 'Renamed', value: data.filter(e => e.was_renamed).length },
          { label: 'Growing Complexity', value: data.filter(e => e.complexity_trend === 'increasing').length },
        ].map(({ label, value }) => (
          <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <p className="text-xs text-zinc-500 mb-1">{label}</p>
            <p className="text-2xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4">
        {filterBtn('all', 'All')}
        {filterBtn('moved', 'Moved')}
        {filterBtn('renamed', 'Renamed')}
        {filterBtn('increasing', 'Growing Complexity')}
        <span className="ml-auto text-xs text-zinc-500">
          {filtered.length} function{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* ── Two-column layout: table+chart LEFT, timeline RIGHT ── */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-5 items-start">

        {/* LEFT: table + chart */}
        <div className="min-w-0">
          {/* Table */}
          {filtered.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
              <p className="text-zinc-500 text-sm">
                {data.length === 0
                  ? 'No functions with identity hashes yet. Re-queue the repository for analysis.'
                  : 'No functions match this filter.'}
              </p>
            </div>
          ) : (
            <>
              <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="px-4 py-3 w-8" />
                      <th className="px-4 py-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Function</th>
                      <th className="px-4 py-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">File</th>
                      <th className="px-4 py-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Tags</th>
                      <th className="px-4 py-3 text-xs text-zinc-500 font-medium uppercase tracking-wider text-center">Commits</th>
                      <th className="px-4 py-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Complexity</th>
                      <th className="px-4 py-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Lifespan</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageData.map(entry => (
                      <FunctionRow
                        key={entry.canonical_id}
                        entry={entry}
                        isSelected={selected?.canonical_id === entry.canonical_id}
                        onSelect={() => setSelected(entry)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <span className="text-xs text-zinc-500">
                    Showing {(page - 1) * ITEMS_PER_PAGE + 1}–{Math.min(page * ITEMS_PER_PAGE, filtered.length)} of {filtered.length}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1.5 text-sm rounded-lg border border-zinc-700 text-zinc-400 hover:text-white hover:border-zinc-500 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Prev
                    </button>
                    {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(n => (
                      <button
                        key={n}
                        onClick={() => setPage(n)}
                        className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                          n === page
                            ? 'bg-blue-500/20 text-blue-400 border-blue-500/40'
                            : 'border-zinc-700 text-zinc-400 hover:text-white hover:border-zinc-500'
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="px-3 py-1.5 text-sm rounded-lg border border-zinc-700 text-zinc-400 hover:text-white hover:border-zinc-500 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Complexity Trend chart — below table */}
          {selected ? (
            <ComplexityChart versions={selected.versions} />
          ) : (
            <div className="mt-4 bg-zinc-900 border border-zinc-800 rounded-xl p-5 text-center text-zinc-600 text-sm">
              Click any function row to see its Complexity Trend
            </div>
          )}
        </div>

        {/* RIGHT: Function Timeline */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-zinc-800">
            <h2 className="font-semibold text-zinc-100 mb-3">Function Timeline</h2>

            {/* Dropdown picker */}
            <div className="relative">
              <button
                onClick={() => setShowTimelineDrop(v => !v)}
                className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg border border-zinc-700 bg-zinc-800 text-sm text-zinc-200 hover:border-zinc-500 transition-colors"
              >
                <span className="truncate">{selected?.name ?? 'Select function…'}</span>
                <ChevronDown className="w-4 h-4 text-zinc-400 shrink-0" />
              </button>
              {showTimelineDrop && (
                <div className="absolute left-0 right-0 mt-1 z-30 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl max-h-56 flex flex-col">
                  <div className="p-2 border-b border-zinc-800">
                    <input
                      autoFocus
                      className="w-full bg-zinc-800 text-sm text-zinc-200 placeholder-zinc-500 outline-none px-2 py-1 rounded"
                      placeholder="Search…"
                      value={timelineDropSearch}
                      onChange={e => setTimelineDropSearch(e.target.value)}
                    />
                  </div>
                  <div className="overflow-y-auto flex-1">
                    {dropOptions.map(e => (
                      <button
                        key={e.canonical_id}
                        onClick={() => { setSelected(e); setShowTimelineDrop(false); setTimelineDropSearch(''); }}
                        className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                          selected?.canonical_id === e.canonical_id
                            ? 'bg-blue-500/10 text-blue-400'
                            : 'text-zinc-300 hover:bg-zinc-800'
                        }`}
                      >
                        {e.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="px-5 py-4 flex-1">
            <h3 className="text-sm font-semibold text-zinc-200 mb-4">Function Timeline</h3>
            <FunctionTimeline entry={selected} repoUrl={repo?.url ?? ''} />
          </div>
        </div>

      </div>
    </div>
  );
}
