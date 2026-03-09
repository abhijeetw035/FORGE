'use client';

import { useState, useMemo } from 'react';
import { ContributorData } from '@/lib/api';
import { Users, GitCommit, Code, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  PieChart, Pie, Cell, Tooltip as ReTooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';

interface ContributorsProps {
  data: ContributorData[];
}

const ITEMS_PER_PAGE = 10;

const COLORS = [
  '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444',
  '#10b981', '#f97316', '#06b6d4', '#ec4899',
];

function getInitials(name: string) {
  return name.split(/\s+/).map(n => n[0]).slice(0, 2).join('').toUpperCase();
}

function avatarBg(i: number) {
  const classes = [
    'bg-blue-700', 'bg-amber-600', 'bg-purple-700', 'bg-red-700',
    'bg-emerald-700', 'bg-orange-700', 'bg-cyan-700', 'bg-pink-700',
  ];
  return classes[i % classes.length];
}

export default function Contributors({ data }: ContributorsProps) {
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-zinc-500">
        No contributor data available
      </div>
    );
  }

  const totalCommits = data.reduce((s, c) => s + c.total_commits, 0);
  const totalFunctions = data.reduce((s, c) => s + c.functions_added, 0);
  const maxEntropy = Math.max(...data.map(c => c.entropy_score));

  // Donut chart data — top 5 + Others
  const top5 = data.slice(0, 5);
  const othersCount = data.slice(5).reduce((s, c) => s + c.functions_added, 0);
  const pieData = [
    ...top5.map(c => ({ name: c.author, value: c.functions_added })),
    ...(othersCount > 0 ? [{ name: 'Others', value: othersCount }] : []),
  ];
  const totalForPct = pieData.reduce((s, d) => s + d.value, 0);

  // Team entropy score (avg)
  const avgEntropy = data.reduce((s, c) => s + c.entropy_score, 0) / data.length;
  const entropyRatio = Math.min(avgEntropy / (maxEntropy || 1), 1);

  // Filtered + paginated
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return q ? data.filter(c => c.author.toLowerCase().includes(q)) : data;
  }, [data, search]);

  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const pageData = filtered.slice(startIndex, startIndex + ITEMS_PER_PAGE);

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Contributors</h1>
        <div className="flex items-center gap-1.5 text-sm text-zinc-500">
          <Users className="w-3.5 h-3.5" />
          <span>Contributors</span>
        </div>
      </div>

      {/* Filter */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <input
          type="text"
          placeholder="Filter commits..."
          value={search}
          onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </div>

      {/* Top row: Donut + Entropy panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5">

        {/* Contributor Impact */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h2 className="font-semibold text-zinc-100 mb-4">Contributor Impact</h2>
          <div className="flex gap-6 items-center">

            {/* Donut */}
            <div className="relative shrink-0" style={{ width: 200, height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={62}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <ReTooltip
                    contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={(v: any, name: any) => v !== undefined ? [`${((v / totalForPct) * 100).toFixed(1)}%`, name ?? ''] : ['-', '']}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* Center label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-xl font-bold text-zinc-100">{data.length} / 100%</span>
                <span className="text-xs text-zinc-500">Total Functions</span>
              </div>
            </div>

            {/* Legend */}
            <div className="flex-1 space-y-2">
              <div className="text-sm font-semibold text-zinc-300 mb-3">Contributors</div>
              {pieData.map((d, i) => (
                <div key={d.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="text-blue-400 font-medium">{d.name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-zinc-400">
                    <span>{d.value.toLocaleString()}</span>
                    <span className="font-semibold text-zinc-200">{((d.value / totalForPct) * 100).toFixed(1)}%</span>
                    {i < top5.length && <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />}
                  </div>
                </div>
              ))}

              {/* Legend color row */}
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 pt-2 border-t border-zinc-800">
                {pieData.map((d, i) => (
                  <div key={d.name} className="flex items-center gap-1 text-xs text-zinc-500">
                    <span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                    {d.name} {((d.value / totalForPct) * 100).toFixed(1)}%
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Team Entropy */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col gap-4">
          <h2 className="font-semibold text-zinc-100">Team Entropy</h2>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-zinc-400">Entropy Score:</span>
              <span className="font-bold text-zinc-100">{avgEntropy.toFixed(2)}</span>
            </div>
            {/* Gradient bar */}
            <div className="relative h-4 rounded-full overflow-hidden" style={{
              background: 'linear-gradient(to right, #3b82f6, #06b6d4, #10b981, #eab308, #f97316, #ef4444)',
            }}>
              <div
                className="absolute top-0 h-full w-3 bg-white rounded-full shadow-lg transition-all duration-500"
                style={{ left: `calc(${entropyRatio * 100}% - 6px)` }}
              />
            </div>
            <div className="flex justify-between text-xs text-zinc-500 mt-1">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>

          <div className="bg-zinc-950/60 border border-zinc-800 rounded-lg p-4">
            <div className="text-sm font-semibold text-zinc-200 mb-1">Entropy Score: {avgEntropy.toFixed(2)}</div>
            <p className="text-xs text-zinc-500 leading-relaxed">
              The entropy score measures authorship distribution across the codebase.
              Higher entropy means code is spread out among more contributors.
            </p>
          </div>
        </div>
      </div>

      {/* Commits per Author chart */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h2 className="font-semibold text-zinc-100 mb-4 flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-blue-400" /> Commits by Author
        </h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={data.slice(0, 12).map((c, i) => ({
              name: c.author.split(/\s+/)[0],   // first name only to keep labels short
              commits: c.total_commits,
              loc: c.total_loc,
              fill: COLORS[i % COLORS.length],
            }))}
            margin={{ top: 4, right: 16, left: 0, bottom: 32 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: '#a1a1aa', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              angle={-30}
              textAnchor="end"
            />
            <YAxis
              tick={{ fill: '#a1a1aa', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={36}
            />
            <ReTooltip
              contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(v: any, name: any) => [v?.toLocaleString?.() ?? v, name === 'commits' ? 'Total Commits' : name ?? '']}
              cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            />
            <Bar dataKey="commits" radius={[4, 4, 0, 0]} maxBarSize={40}>
              {data.slice(0, 12).map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Contributors table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <h2 className="font-semibold text-zinc-100 flex items-center gap-2">
            <Users className="w-4 h-4" /> Contributors
          </h2>
          <span className="text-xs text-zinc-500">
            {filtered.length} contributor{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-zinc-950/60 border-b border-zinc-800 text-xs text-zinc-400 uppercase tracking-wide">
                <th className="text-left py-3 px-4 font-semibold">Author</th>
                <th className="text-right py-3 px-4 font-semibold flex items-center justify-end gap-1">
                  <GitCommit className="w-3 h-3" /> Total Commits
                </th>
                <th className="text-right py-3 px-4 font-semibold">
                  <div className="flex items-center justify-end gap-1">
                    <Code className="w-3 h-3" /> Functions Added
                  </div>
                </th>
                <th className="text-right py-3 px-4 font-semibold">Total LOC</th>
                <th className="text-right py-3 px-4 font-semibold">Entropy Score</th>
                <th className="text-right py-3 px-4 font-semibold">Impact %</th>
              </tr>
            </thead>
            <tbody>
              {pageData.map((contributor, index) => {
                const globalIndex = startIndex + index;
                const impactPercent = totalFunctions > 0
                  ? (contributor.functions_added / totalFunctions * 100).toFixed(1)
                  : '0.0';
                return (
                  <tr
                    key={contributor.author}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className={`flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-bold shrink-0 ${avatarBg(globalIndex)}`}>
                          {getInitials(contributor.author)}
                        </div>
                        <span className="font-medium text-zinc-100">{contributor.author}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right text-zinc-300">{contributor.total_commits.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right text-zinc-300">{contributor.functions_added.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right text-zinc-300">{contributor.total_loc.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 bg-zinc-800 rounded-full h-1.5">
                          <div
                            className="bg-blue-500 h-1.5 rounded-full"
                            style={{ width: `${Math.min((contributor.entropy_score / maxEntropy) * 100, 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-zinc-200 w-10 text-right">{contributor.entropy_score.toFixed(2)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right text-zinc-300 font-medium">{impactPercent}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800 text-xs text-zinc-500">
          <span>
            {filtered.length === 0 ? '0' : `${startIndex + 1}–${Math.min(startIndex + ITEMS_PER_PAGE, filtered.length)}`} of {filtered.length}
          </span>
          <div className="flex items-center gap-1.5">
            <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}
              className="p-1 rounded border border-zinc-700 disabled:opacity-30 hover:bg-zinc-800 text-zinc-300">
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(n => (
              <button key={n} onClick={() => setCurrentPage(n)}
                className={`w-7 h-7 rounded border text-xs font-medium transition-colors ${currentPage === n ? 'bg-blue-600 border-blue-600 text-white' : 'border-zinc-700 text-zinc-400 hover:bg-zinc-800'}`}>
                {n}
              </button>
            ))}
            <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages || totalPages === 0}
              className="p-1 rounded border border-zinc-700 disabled:opacity-30 hover:bg-zinc-800 text-zinc-300">
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}