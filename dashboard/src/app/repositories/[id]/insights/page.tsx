'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import {
  getRepositoryRiskPrediction, getRepositoryFunctionEvolution,
  getRepositoryContributors,
  RiskPredictionData, FunctionEvolutionData, ContributorData,
} from '@/lib/api';
import { Lightbulb, Download, ShieldAlert, Zap, Flame, Users, FileCode2 } from 'lucide-react';

function riskColor(level: string) {
  if (level === 'critical') return 'text-red-400 bg-red-500/10 border-red-500/30';
  if (level === 'warning')  return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
  return 'text-zinc-400 bg-zinc-700/20 border-zinc-600/30';
}

function riskDot(level: string) {
  if (level === 'critical') return 'bg-red-500';
  if (level === 'warning')  return 'bg-yellow-500';
  return 'bg-zinc-500';
}

function shortPath(path: string) {
  const parts = path.split('/');
  return parts.length > 3 ? `…/${parts.slice(-2).join('/')}` : path;
}

function SectionCard({ icon, title, count, children }: {
  icon: React.ReactNode;
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="font-semibold text-zinc-100 flex items-center gap-2 text-sm">
          {icon}
          {title}
        </h2>
        <span className="text-xs text-zinc-500">{count} items</span>
      </div>
      <div className="divide-y divide-zinc-800/60">{children}</div>
    </div>
  );
}

export default function InsightsPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? '';

  const [risk, setRisk]   = useState<RiskPredictionData[]>([]);
  const [funcs, setFuncs] = useState<FunctionEvolutionData[]>([]);
  const [contributors, setContributors] = useState<ContributorData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      getRepositoryRiskPrediction(id).catch(() => [] as RiskPredictionData[]),
      getRepositoryFunctionEvolution(id).catch(() => [] as FunctionEvolutionData[]),
      getRepositoryContributors(id).catch(() => [] as ContributorData[]),
    ]).then(([r, f, c]) => {
      setRisk(r);
      setFuncs(f);
      setContributors(c);
      setLoading(false);
    });
  }, [id]);

  const topRisky = useMemo(
    () => [...risk].sort((a, b) => b.risk_score - a.risk_score).slice(0, 10),
    [risk],
  );
  const topChurn = useMemo(
    () => [...risk].sort((a, b) => b.churn - a.churn).slice(0, 10),
    [risk],
  );
  const topComplex = useMemo(() => {
    const seen = new Map<string, { name: string; complexity: number; file: string }>();
    funcs.forEach(fn => {
      fn.versions.forEach(v => {
        const prev = seen.get(fn.name);
        if (!prev || v.complexity > prev.complexity) {
          seen.set(fn.name, { name: fn.name, complexity: v.complexity, file: v.file_path });
        }
      });
    });
    return [...seen.values()].sort((a, b) => b.complexity - a.complexity).slice(0, 10);
  }, [funcs]);

  const topContributors = useMemo(
    () => [...contributors].sort((a, b) => b.total_commits - a.total_commits).slice(0, 5),
    [contributors],
  );

  function exportJSON() {
    const payload = { topRisky, topChurn, topComplex, topContributors };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `insights-repo-${id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportCSV() {
    const rows: string[] = ['Type,File/Function,Score,Risk Level'];
    topRisky.forEach(f => rows.push(`Top Risky,"${f.file_path}",${f.risk_score.toFixed(3)},${f.risk_level}`));
    topChurn.forEach(f => rows.push(`High Churn,"${f.file_path}",${f.churn},${f.risk_level}`));
    topComplex.forEach(f => rows.push(`Complex Function,"${f.name} (${f.file})",${f.complexity},-`));
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `insights-repo-${id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <Lightbulb className="w-7 h-7 text-yellow-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Insights</h1>
            <p className="text-sm text-zinc-500">Loading analysis…</p>
          </div>
        </div>
        {[1,2,3,4].map(i => (
          <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl h-48 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Lightbulb className="w-7 h-7 text-yellow-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Insights</h1>
            <p className="text-sm text-zinc-500">
              Automated analysis across {risk.length} files · {funcs.length} functions
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300 hover:text-white hover:border-zinc-500 transition-colors"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
          <button
            onClick={exportJSON}
            className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white border border-blue-500 transition-colors"
          >
            <Download className="w-4 h-4" /> Export JSON
          </button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Critical Files',   value: risk.filter(r => r.risk_level === 'critical').length,  color: 'text-red-400',    icon: <ShieldAlert className="w-4 h-4" /> },
          { label: 'High Churn Files', value: topChurn.filter(f => f.churn > 20).length,             color: 'text-orange-400', icon: <Flame className="w-4 h-4" /> },
          { label: 'Complex Fns',      value: topComplex.filter(f => f.complexity > 10).length,      color: 'text-yellow-400', icon: <Zap className="w-4 h-4" /> },
          { label: 'Contributors',     value: contributors.length,                                   color: 'text-blue-400',   icon: <Users className="w-4 h-4" /> },
        ].map(({ label, value, color, icon }) => (
          <div key={label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-3">
            <span className={color}>{icon}</span>
            <div>
              <div className={`text-xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-zinc-500">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Top 10 Risky Files */}
      <SectionCard icon={<ShieldAlert className="w-4 h-4 text-red-400" />} title="Top 10 Riskiest Files" count={topRisky.length}>
        {topRisky.map((f) => (
          <div key={f.file_path} className="flex items-center justify-between px-5 py-3 hover:bg-zinc-800/40 transition-colors gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className={`w-2 h-2 rounded-full shrink-0 ${riskDot(f.risk_level)}`} />
              <span className="text-sm text-zinc-200 truncate font-mono">{shortPath(f.file_path)}</span>
            </div>
            <div className="flex items-center gap-3 shrink-0 text-xs">
              <span className="text-zinc-500">Churn {f.churn}</span>
              <span className="text-zinc-500">Cplx {f.complexity}</span>
              <span className={`px-2 py-0.5 rounded-md border font-semibold ${riskColor(f.risk_level)}`}>
                {f.risk_score.toFixed(3)}
              </span>
            </div>
          </div>
        ))}
      </SectionCard>

      {/* Top 10 High Churn Files */}
      <SectionCard icon={<Flame className="w-4 h-4 text-orange-400" />} title="Top 10 High-Churn Files" count={topChurn.length}>
        {topChurn.map((f) => (
          <div key={f.file_path} className="flex items-center justify-between px-5 py-3 hover:bg-zinc-800/40 transition-colors gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <FileCode2 className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
              <span className="text-sm text-zinc-200 truncate font-mono">{shortPath(f.file_path)}</span>
            </div>
            <div className="flex items-center gap-3 shrink-0 text-xs">
              <span className="text-zinc-500">+{f.lines_added} / -{f.lines_deleted}</span>
              <span className={`px-2 py-0.5 rounded-md border font-semibold ${riskColor(f.risk_level)}`}>
                {f.churn} churn
              </span>
            </div>
          </div>
        ))}
      </SectionCard>

      {/* Top 10 Complex Functions */}
      <SectionCard icon={<Zap className="w-4 h-4 text-yellow-400" />} title="Top 10 Most Complex Functions" count={topComplex.length}>
        {topComplex.map((fn) => (
          <div key={fn.name + fn.file} className="flex items-center justify-between px-5 py-3 hover:bg-zinc-800/40 transition-colors gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-yellow-400 font-bold text-xs w-6 text-center">{fn.complexity}</span>
              <div className="min-w-0">
                <div className="text-sm font-semibold text-zinc-100 truncate">{fn.name}</div>
                <div className="text-xs text-zinc-500 truncate font-mono">{shortPath(fn.file)}</div>
              </div>
            </div>
            {/* Complexity bar */}
            <div className="w-24 bg-zinc-800 rounded-full h-1.5 shrink-0">
              <div
                className="h-1.5 rounded-full bg-yellow-500/80"
                style={{ width: `${Math.min((fn.complexity / (topComplex[0]?.complexity || 1)) * 100, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </SectionCard>

      {/* Top Contributors */}
      <SectionCard icon={<Users className="w-4 h-4 text-blue-400" />} title="Top Contributors" count={topContributors.length}>
        {topContributors.map((c, i) => {
          const maxCommits = topContributors[0]?.total_commits || 1;
          return (
            <div key={c.author} className="flex items-center justify-between px-5 py-3 hover:bg-zinc-800/40 transition-colors gap-4">
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xs text-zinc-600 w-5 text-right shrink-0">#{i + 1}</span>
                <span className="text-sm font-medium text-zinc-100 truncate">{c.author}</span>
              </div>
              <div className="flex items-center gap-3 shrink-0 text-xs">
                <div className="w-28 bg-zinc-800 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-blue-500/80"
                    style={{ width: `${(c.total_commits / maxCommits) * 100}%` }}
                  />
                </div>
                <span className="text-zinc-300 font-medium">{c.total_commits.toLocaleString()} commits</span>
              </div>
            </div>
          );
        })}
      </SectionCard>

    </div>
  );
}
