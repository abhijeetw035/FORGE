'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { getRepositoryRiskPrediction, getRepositoryTimeline } from '@/lib/api';
import type { RiskPredictionData, TimelineData } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip as ReTooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts';
import {
  Search, ChevronUp, ChevronDown, FileCode2,
  TrendingUp, TrendingDown, GitCommit, Users, Activity,
} from 'lucide-react';

interface PageProps {
  params: Promise<{ id: string }>;
}

const ITEMS_PER_PAGE = 10;

function riskBadge(score: number) {
  const pct = Math.round(score * 100);
  let bg = 'bg-green-600';
  if (pct >= 80) bg = 'bg-red-600';
  else if (pct >= 65) bg = 'bg-orange-500';
  else if (pct >= 45) bg = 'bg-yellow-500';
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-white text-xs font-bold ${bg}`}>
      {pct}%
    </span>
  );
}

function shortName(path: string) {
  return path.split('/').pop() ?? path;
}

type SortKey = 'file_path' | 'complexity' | 'churn' | 'risk_score' | 'author_count' | 'dependency_count';
type SortDir = 'asc' | 'desc';

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ChevronUp className="w-3 h-3 text-zinc-600" />;
  return dir === 'asc'
    ? <ChevronUp className="w-3 h-3 text-blue-400" />
    : <ChevronDown className="w-3 h-3 text-blue-400" />;
}

function StatRow({
  label, value, icon,
}: { label: string; value: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-zinc-800 last:border-0">
      <div className="flex items-center gap-2 text-zinc-400 text-sm">{icon}{label}</div>
      <div className="text-zinc-100 font-semibold text-sm">{value}</div>
    </div>
  );
}

export default function HeatmapPage({ params }: PageProps) {
  const [id, setId] = useState('');
  const [files, setFiles] = useState<RiskPredictionData[]>([]);
  const [timeline, setTimeline] = useState<TimelineData[]>([]);
  const [selected, setSelected] = useState<RiskPredictionData | null>(null);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('risk_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  useEffect(() => { params.then(p => setId(p.id)); }, [params]);

  useEffect(() => {
    if (authLoading || !id) return;
    if (!isAuthenticated) { router.push('/login'); return; }

    Promise.all([
      getRepositoryRiskPrediction(id),
      getRepositoryTimeline(id).catch(() => [] as TimelineData[]),
    ]).then(([risk, tl]) => {
      setFiles(risk);
      setTimeline(tl);
      if (risk.length > 0) setSelected(risk[0]);
    }).catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setIsLoading(false));
  }, [id, router, isAuthenticated, authLoading]);

  const sorted = useMemo(() => {
    const q = search.toLowerCase();
    const filtered = q ? files.filter(f => f.file_path.toLowerCase().includes(q)) : files;
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] as number | string;
      const bv = b[sortKey] as number | string;
      if (typeof av === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv as string) : (bv as string).localeCompare(av);
      }
      return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
  }, [files, search, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / ITEMS_PER_PAGE);
  const pageRows = sorted.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);
  const detailRows = useMemo(() => sorted.slice(0, 6), [sorted]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
    setPage(1);
  }

  const churnChart = useMemo(() => {
    if (timeline.length === 0) return [];
    return [...timeline]
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .slice(-12)
      .map(t => ({
        month: new Date(t.date).toLocaleString('default', { month: 'short' }),
        churn: t.function_count,
      }));
  }, [timeline]);

  function Th({ label, sk }: { label: string; sk: SortKey }) {
    return (
      <th
        className="text-left py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide cursor-pointer select-none whitespace-nowrap"
        onClick={() => toggleSort(sk)}
      >
        <div className="flex items-center gap-1">
          {label}
          <SortIcon active={sortKey === sk} dir={sortDir} />
        </div>
      </th>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-zinc-700 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Loading file analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">File Analytics</h1>
        <div className="flex items-center gap-1.5 text-sm text-zinc-500">
          <Activity className="w-3.5 h-3.5" />
          <span>File Analytics</span>
        </div>
      </div>

      {/* Top filter */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <input
          type="text"
          placeholder="Filter files..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </div>

      {/* Main split layout */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-5 items-start">

        {/* LEFT */}
        <div className="space-y-5 min-w-0">

          {/* File Table */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800">
              <h2 className="font-semibold text-zinc-100">File Table</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-zinc-950/60 border-b border-zinc-800">
                    <Th label="File Path" sk="file_path" />
                    <th className="text-right py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide">Size</th>
                    <Th label="Churn ↕" sk="churn" />
                    <Th label="Complexity" sk="complexity" />
                    <Th label="Authors" sk="author_count" />
                    <Th label="Dependencies" sk="dependency_count" />
                    <Th label="Risk Score" sk="risk_score" />
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map(f => (
                    <tr
                      key={f.file_path}
                      onClick={() => setSelected(f)}
                      className={`border-b border-zinc-800/50 cursor-pointer transition-colors
                        ${selected?.file_path === f.file_path
                          ? 'bg-blue-500/10 border-l-2 border-l-blue-500'
                          : 'hover:bg-zinc-800/40'}`}
                    >
                      <td className="py-2.5 px-3 font-medium text-zinc-200 max-w-[200px] truncate">{shortName(f.file_path)}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-400">{Math.round(f.complexity * 10)}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{f.churn} edits</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{f.complexity.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{f.author_count}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{f.dependency_count}</td>
                      <td className="py-2.5 px-3 text-right">{riskBadge(f.risk_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800 text-xs text-zinc-500">
              <span>
                {sorted.length === 0 ? '0' : `${(page - 1) * ITEMS_PER_PAGE + 1}–${Math.min(page * ITEMS_PER_PAGE, sorted.length)}`} of {sorted.length}
              </span>
              <div className="flex items-center gap-1.5">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                  className="px-2 py-1 rounded border border-zinc-700 disabled:opacity-30 hover:bg-zinc-800 text-zinc-300">Prev</button>
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(n => (
                  <button key={n} onClick={() => setPage(n)}
                    className={`w-7 h-7 rounded border text-xs font-medium transition-colors ${page === n ? 'bg-blue-600 border-blue-600 text-white' : 'border-zinc-700 text-zinc-400 hover:bg-zinc-800'}`}>
                    {n}
                  </button>
                ))}
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages || totalPages === 0}
                  className="px-2 py-1 rounded border border-zinc-700 disabled:opacity-30 hover:bg-zinc-800 text-zinc-300">Next</button>
              </div>
            </div>
          </div>

          {/* File Detail View table */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800">
              <h2 className="font-semibold text-zinc-100">File Detail View</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-zinc-950/60 border-b border-zinc-800">
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide">File Path</th>
                    <th className="text-right py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide">Size ↓ LLOC</th>
                    <th className="text-right py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide">Churn</th>
                    <th className="text-right py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide">Complexity</th>
                    <th className="text-right py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide">Authors</th>
                    <th className="text-right py-2.5 px-3 text-xs font-semibold text-zinc-400 uppercase tracking-wide">Risk Score</th>
                  </tr>
                </thead>
                <tbody>
                  {detailRows.map(f => (
                    <tr
                      key={f.file_path}
                      onClick={() => setSelected(f)}
                      className={`border-b border-zinc-800/50 cursor-pointer transition-colors
                        ${selected?.file_path === f.file_path
                          ? 'bg-blue-500/10 border-l-2 border-l-blue-500'
                          : 'hover:bg-zinc-800/40'}`}
                    >
                      <td className="py-2.5 px-3 font-medium text-zinc-200 max-w-[180px] truncate">{shortName(f.file_path)}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-400">{Math.round(f.complexity * 10)}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{f.churn}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{f.complexity.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-right text-zinc-300">{f.author_count}</td>
                      <td className="py-2.5 px-3 text-right">{riskBadge(f.risk_score)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-zinc-800 text-xs text-zinc-500">
              1–{Math.min(6, detailRows.length)} of {sorted.length}
            </div>
          </div>
        </div>

        {/* RIGHT — File detail panel */}
        {selected && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden flex flex-col">

            {/* File header */}
            <div className="px-5 pt-5 pb-4 border-b border-zinc-800">
              <div className="flex items-center gap-3 mb-1">
                <FileCode2 className="w-7 h-7 text-blue-400" />
                <h3 className="text-lg font-bold text-zinc-100 truncate">{shortName(selected.file_path)}</h3>
              </div>
              <p className="text-xs text-zinc-500 truncate pl-10">{selected.file_path}</p>
              <p className="text-sm text-zinc-400 mt-1 pl-10">Total LOC: {Math.round(selected.complexity * 10)}</p>
            </div>

            {/* Stats */}
            <div className="px-5 py-4 border-b border-zinc-800">
              <StatRow
                label="Lines Added"
                icon={<TrendingUp className="w-4 h-4 text-green-400" />}
                value={<span className="text-green-400">↑ {selected.lines_added.toLocaleString()}</span>}
              />
              <StatRow
                label="Lines Deleted"
                icon={<TrendingDown className="w-4 h-4 text-red-400" />}
                value={<span className="text-red-400">−{selected.lines_deleted.toLocaleString()}</span>}
              />
              <StatRow
                label="Commit Frequency"
                icon={<GitCommit className="w-4 h-4 text-zinc-400" />}
                value={selected.commit_frequency}
              />
              <StatRow
                label="Recent Churn (30 days)"
                icon={<Activity className="w-4 h-4 text-yellow-400" />}
                value={`${selected.recent_churn} edits`}
              />
              <StatRow
                label="Ownership Entropy"
                icon={<Users className="w-4 h-4 text-purple-400" />}
                value={selected.ownership_entropy.toFixed(2)}
              />
            </div>

            {/* Churn Over Time chart */}
            <div className="px-5 py-4">
              <h4 className="text-sm font-semibold text-zinc-200 mb-3">Churn Over Time</h4>
              {churnChart.length >= 2 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={churnChart} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="churnGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis dataKey="month" tick={{ fill: '#71717a', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#71717a', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <ReTooltip
                      contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: '#a1a1aa' }}
                      itemStyle={{ color: '#60a5fa' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="churn"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fill="url(#churnGrad)"
                      dot={{ r: 3, fill: '#3b82f6', strokeWidth: 0 }}
                      activeDot={{ r: 5, fill: '#60a5fa' }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[180px] flex items-center justify-center text-zinc-600 text-sm">
                  Not enough timeline data
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
