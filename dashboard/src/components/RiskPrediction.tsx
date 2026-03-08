'use client';

import { useState } from 'react';
import {
  Brain,
  AlertTriangle,
  AlertCircle,
  Eye,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  GitCommit,
  Users,
  Clock,
  Zap,
  Package,
  TrendingUp,
  Activity,
  ExternalLink,
} from 'lucide-react';
import type { RiskPredictionData } from '@/lib/api';

interface RiskPredictionProps {
  data: RiskPredictionData[];
}

interface FeatureBarProps {
  label: string;
  value: number;
  max: number;
  unit?: string;
  icon: React.ReactNode;
  color: string; // tailwind bg class
}

function FeatureBar({ label, value, unit, icon, color, max }: FeatureBarProps) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="text-zinc-500 w-4 flex-shrink-0">{icon}</div>
      <span className="text-zinc-400 w-32 flex-shrink-0 truncate">{label}</span>
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-zinc-300 w-16 text-right flex-shrink-0">
        {typeof value === 'number' && !Number.isInteger(value)
          ? value.toFixed(2)
          : value}
        {unit ? ` ${unit}` : ''}
      </span>
    </div>
  );
}

export default function RiskPrediction({ data }: RiskPredictionProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const itemsPerPage = 5;

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-zinc-500">
        No risk predictions available
      </div>
    );
  }

  const getRiskStyle = (level: string) => {
    switch (level) {
      case 'critical':
        return {
          border: 'border-red-900/60',
          progressFill: 'bg-red-600',
          badgeBg: 'bg-red-950/60 border-red-800 text-red-400',
          icon: AlertTriangle,
          iconColor: 'text-red-400',
        };
      case 'warning':
        return {
          border: 'border-orange-900/60',
          progressFill: 'bg-orange-500',
          badgeBg: 'bg-orange-950/60 border-orange-800 text-orange-400',
          icon: AlertCircle,
          iconColor: 'text-orange-400',
        };
      default:
        return {
          border: 'border-zinc-800',
          progressFill: 'bg-zinc-500',
          badgeBg: 'bg-zinc-900/60 border-zinc-700 text-zinc-400',
          icon: Eye,
          iconColor: 'text-zinc-400',
        };
    }
  };

  const criticalCount = data.filter(d => d.risk_level === 'critical').length;
  const warningCount  = data.filter(d => d.risk_level === 'warning').length;

  const totalPages  = Math.ceil(data.length / itemsPerPage);
  const startIndex  = (currentPage - 1) * itemsPerPage;
  const currentPage_data = data.slice(startIndex, startIndex + itemsPerPage);

  const toggleExpand = (i: number) =>
    setExpandedIndex(expandedIndex === i ? null : i);

  // ── render ──────────────────────────────────────────────────────────────────
  return (
    <div className="w-full space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-cyan-400" />
            AI Risk Forecast
          </h3>
          <p className="text-sm text-zinc-500 mt-1">
            Isolation Forest anomaly detection across 9 code-health features
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1 bg-red-950/40 border border-red-900/50 rounded-md">
            <span className="text-xs font-semibold text-red-400">{criticalCount} Critical</span>
          </div>
          <div className="px-3 py-1 bg-orange-950/40 border border-orange-900/50 rounded-md">
            <span className="text-xs font-semibold text-orange-400">{warningCount} Warning</span>
          </div>
        </div>
      </div>

      {/* How it works — docs link */}
      <div className="bg-zinc-950/50 border border-zinc-800 rounded-md p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-start gap-3">
            <div className="text-xl">🔮</div>
            <div>
              <p className="font-semibold text-white">How it works</p>
              <p className="text-xs text-zinc-500 mt-0.5">
                Isolation Forest anomaly detection across 9 code-health features.
              </p>
            </div>
          </div>
          <a
            href="/docs/risk-prediction"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-zinc-700 text-xs text-zinc-300 hover:text-white hover:border-zinc-500 hover:bg-zinc-800/50 transition-all flex-shrink-0"
          >
            View Docs
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Risk cards */}
      <div className="space-y-3">
        {currentPage_data.map((file, index) => {
          const style    = getRiskStyle(file.risk_level);
          const Icon     = style.icon;
          const fileName = file.file_path.split('/').pop() || file.file_path;
          const isOpen   = expandedIndex === index;

          return (
            <div
              key={index}
              className={`bg-zinc-950/50 border ${style.border} rounded-md overflow-hidden transition-all duration-200`}
            >
              {/* Card header (always visible) */}
              <div className="p-4">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <Icon className={`w-5 h-5 ${style.iconColor} flex-shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white truncate" title={file.file_path}>
                        {fileName}
                      </p>
                      <p className="text-xs text-zinc-500 truncate mt-0.5">
                        {file.file_path}
                      </p>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-2xl font-bold text-white">
                      {Math.round(file.risk_score)}%
                    </p>
                    <span className={`text-xs px-2 py-0.5 rounded border font-semibold uppercase tracking-wider ${style.badgeBg}`}>
                      {file.risk_level}
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden mb-3">
                  <div
                    className={`h-full ${style.progressFill} transition-all duration-500`}
                    style={{ width: `${file.risk_score}%` }}
                  />
                </div>

                {/* Quick stats + reason + expand toggle */}
                <div className="flex items-center justify-between text-xs gap-2 flex-wrap">
                  {/* top-3 quick stats always visible */}
                  <div className="flex items-center gap-3 text-zinc-400 flex-wrap">
                    <span className="flex items-center gap-1">
                      <GitCommit className="w-3 h-3" /> {file.churn ?? 0} commits
                    </span>
                    <span className="flex items-center gap-1">
                      <Activity className="w-3 h-3" /> {(file.complexity ?? 0).toFixed(1)} complexity
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" /> {file.author_count ?? 0} authors
                    </span>
                    {(file.recent_churn ?? 0) > 0 && (
                      <span className="flex items-center gap-1 text-yellow-500">
                        <TrendingUp className="w-3 h-3" /> {file.recent_churn} recent
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => toggleExpand(index)}
                    className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 transition-colors ml-auto flex-shrink-0"
                  >
                    {isOpen ? (
                      <><ChevronUp className="w-3.5 h-3.5" /> Less</>
                    ) : (
                      <><ChevronDown className="w-3.5 h-3.5" /> Details</>
                    )}
                  </button>
                </div>

                {/* Reason tag */}
                {file.reason && (
                  <p className="mt-2 text-xs text-zinc-400 italic">
                    ⚠️ {file.reason}
                  </p>
                )}
              </div>

              {/* Expandable feature breakdown */}
              {isOpen && (
                <div className="border-t border-zinc-800 bg-zinc-900/30 px-4 py-4 space-y-2.5">
                  <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
                    Feature Breakdown
                  </p>

                  {/* Commit history group */}
                  <p className="text-xs text-zinc-600 uppercase tracking-widest">Commit History</p>
                  <FeatureBar
                    label="Total Churn"
                    value={file.churn ?? 0}
                    max={100}
                    icon={<GitCommit className="w-3 h-3" />}
                    color="bg-blue-500"
                  />
                  <FeatureBar
                    label="Lines Added"
                    value={file.lines_added ?? 0}
                    max={5000}
                    icon={<TrendingUp className="w-3 h-3" />}
                    color="bg-green-500"
                  />
                  <FeatureBar
                    label="Lines Deleted"
                    value={file.lines_deleted ?? 0}
                    max={5000}
                    icon={<TrendingUp className="w-3 h-3 rotate-180" />}
                    color="bg-red-500"
                  />
                  <FeatureBar
                    label="File Age"
                    value={file.file_age_days ?? 0}
                    max={1095}
                    unit="days"
                    icon={<Clock className="w-3 h-3" />}
                    color="bg-purple-500"
                  />
                  <FeatureBar
                    label="Commit Freq"
                    value={file.commit_frequency ?? 0}
                    max={2}
                    unit="/day"
                    icon={<Zap className="w-3 h-3" />}
                    color="bg-yellow-500"
                  />
                  <FeatureBar
                    label="Recent Churn"
                    value={file.recent_churn ?? 0}
                    max={30}
                    unit="(90d)"
                    icon={<Activity className="w-3 h-3" />}
                    color="bg-orange-500"
                  />

                  {/* Authorship group */}
                  <p className="text-xs text-zinc-600 uppercase tracking-widest pt-1">Authorship</p>
                  <FeatureBar
                    label="Author Count"
                    value={file.author_count ?? 0}
                    max={20}
                    icon={<Users className="w-3 h-3" />}
                    color="bg-cyan-500"
                  />
                  <FeatureBar
                    label="Ownership Entropy"
                    value={file.ownership_entropy ?? 0}
                    max={5}
                    unit="bits"
                    icon={<Users className="w-3 h-3" />}
                    color="bg-pink-500"
                  />

                  {/* Coupling + complexity group */}
                  <p className="text-xs text-zinc-600 uppercase tracking-widest pt-1">Coupling &amp; Complexity</p>
                  <FeatureBar
                    label="Dependencies"
                    value={file.dependency_count ?? 0}
                    max={50}
                    icon={<Package className="w-3 h-3" />}
                    color="bg-indigo-500"
                  />
                  <FeatureBar
                    label="Avg Complexity"
                    value={file.complexity ?? 0}
                    max={30}
                    icon={<Activity className="w-3 h-3" />}
                    color="bg-rose-500"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      {data.length > itemsPerPage && (
        <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
          <div className="text-sm text-zinc-400">
            Showing {startIndex + 1}–{Math.min(startIndex + itemsPerPage, data.length)} of {data.length} files
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
              disabled={currentPage === 1}
              className={`flex items-center gap-1 px-3 py-2 rounded-md text-sm font-medium transition-all
                ${currentPage === 1
                  ? 'bg-zinc-900/50 text-zinc-600 cursor-not-allowed'
                  : 'bg-zinc-950/50 border border-zinc-800 text-white hover:bg-zinc-900 hover:border-zinc-700'}`}
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`w-10 h-10 rounded-md text-sm font-medium transition-all
                  ${currentPage === page
                    ? 'bg-blue-500 text-white'
                    : 'bg-zinc-950/50 border border-zinc-800 text-zinc-400 hover:bg-zinc-900 hover:border-zinc-700 hover:text-white'}`}
              >
                {page}
              </button>
            ))}
            <button
              onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
              disabled={currentPage === totalPages}
              className={`flex items-center gap-1 px-3 py-2 rounded-md text-sm font-medium transition-all
                ${currentPage === totalPages
                  ? 'bg-zinc-900/50 text-zinc-600 cursor-not-allowed'
                  : 'bg-zinc-950/50 border border-zinc-800 text-white hover:bg-zinc-900 hover:border-zinc-700'}`}
            >
              Next <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Interpretation guide */}
      <div className="glass-card p-4">
        <h4 className="text-sm font-semibold text-white mb-3">💡 Interpretation Guide</h4>
        <div className="space-y-1.5 text-xs text-zinc-400">
          <p><strong className="text-red-400">Critical (80-100%):</strong> Immediate attention required — statistically extreme combination of signals.</p>
          <p><strong className="text-orange-400">Warning (50-79%):</strong> Monitor closely; consider refactoring or additional test coverage.</p>
          <p><strong className="text-zinc-400">Watchlist (&lt;50%):</strong> Unusual in at least one dimension — keep an eye on it.</p>
        </div>
        <div className="mt-3 pt-3 border-t border-zinc-800 grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-zinc-500">
          <p><span className="text-zinc-300">Ownership Entropy</span> — low = knowledge silo; high = diffuse ownership</p>
          <p><span className="text-zinc-300">Commit Frequency</span> — burst changes indicate instability</p>
          <p><span className="text-zinc-300">Recent Churn</span> — commits in last 90 days</p>
          <p><span className="text-zinc-300">Dependencies</span> — import count proxies coupling risk</p>
        </div>
      </div>
    </div>
  );
}
