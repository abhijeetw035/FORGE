'use client';

import { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Search,
  CheckCircle2,
  GitCommit,
  Activity,
  Users,
  TrendingUp,
  GitPullRequest,
  Clock,
  Layers,
  ArrowDownUp,
  FileCode2,
} from 'lucide-react';
import type { RiskPredictionData } from '@/lib/api';

interface RiskPredictionProps {
  data: RiskPredictionData[];
}

// Standardized churn thresholds matching api/services/predictor.py
export const CHURN_VERY_HIGH_THRESHOLD = 20;
export const CHURN_HIGH_THRESHOLD = 10;

export function getChurnLevel(churn: number): 'High' | 'Med' | 'Low' {
  if (churn > CHURN_VERY_HIGH_THRESHOLD) return 'High';
  if (churn > CHURN_HIGH_THRESHOLD) return 'Med';
  return 'Low';
}

/**
 * Generate a natural, single-sentence plain-English explanation
 * from the top 2-3 risk factors for this file.
 */
export function explainRisk(file: RiskPredictionData): string {
  const phrases: string[] = [];

  // 1. Complexity + untouched vs pure complexity
  if ((file.complexity ?? 0) > 10 && (file.recent_churn ?? 0) === 0) {
    phrases.push("it's complex and rarely touched, so few people remember how it works");
  } else if ((file.complexity ?? 0) > 10) {
    phrases.push("the code is hard to read (high complexity)");
  }

  // 2. Many authors / high ownership entropy
  if ((file.author_count ?? 0) > 4 || (file.ownership_entropy ?? 0) > 1.2) {
    const authors = file.author_count ?? 1;
    phrases.push(`${authors} different people have edited this file, so nobody clearly owns it`);
  }

  // 3. High dependencies
  if ((file.dependency_count ?? 0) > 8) {
    phrases.push(`${file.dependency_count} other files rely on it, so a change here can break things elsewhere`);
  }

  // 4. High churn
  if ((file.churn ?? 0) > CHURN_VERY_HIGH_THRESHOLD) {
    phrases.push(`it changes very frequently (${file.churn} edits)`);
  }

  // 5. High lines added/deleted
  if ((file.lines_added ?? 0) > 3000 || (file.lines_deleted ?? 0) > 2000) {
    phrases.push("lots of code keeps being added and removed");
  }

  // Fallback if none matched
  if (phrases.length === 0) {
    if (file.reason) {
      const parts = file.reason.split(' · ');
      return parts.slice(0, 2).join(' and ') + '.';
    }
    return "This file exhibits anomalous patterns across recent churn and structural health signals.";
  }

  const selected = phrases.slice(0, 3);
  let sentence = "";
  if (selected.length === 1) {
    sentence = selected[0];
  } else if (selected.length === 2) {
    sentence = `${selected[0]}, and ${selected[1]}`;
  } else {
    sentence = `${selected[0]}, ${selected[1]}, and ${selected[2]}`;
  }

  return sentence.charAt(0).toUpperCase() + sentence.slice(1) + '.';
}

function getNextSteps(file: RiskPredictionData): string[] {
  const steps: string[] = [];

  if ((file.ownership_entropy ?? 0) > 1.2 || (file.author_count ?? 0) > 4) {
    steps.push("Assign one or two code owners for this file.");
  }
  if ((file.dependency_count ?? 0) > 8) {
    steps.push("Add tests before the next change, since many files depend on it.");
  }
  if ((file.complexity ?? 0) > 10 && (file.recent_churn ?? 0) === 0) {
    steps.push("Document how it works while someone still remembers.");
  } else if ((file.complexity ?? 0) > 10) {
    steps.push("Consider splitting it into smaller, focused modules.");
  }
  if ((file.churn ?? 0) > CHURN_VERY_HIGH_THRESHOLD) {
    steps.push("Review why this file changes so often to reduce instability.");
  }

  if (steps.length === 0) {
    steps.push("Add unit test coverage around the main execution paths.");
    steps.push("Keep upcoming changes small and focused during code review.");
  }

  return steps.slice(0, 3);
}

function splitFilePath(path: string) {
  const parts = path.split('/');
  const fileName = parts.pop() || path;
  const folder = parts.length > 0 ? parts.join('/') + '/' : '';
  return { fileName, folder };
}

interface FeatureBarProps {
  label: string;
  value: number;
  max: number;
  unit?: string;
  icon: React.ReactNode;
  color: string;
}

function FeatureBar({ label, value, unit, icon, color, max }: FeatureBarProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  return (
    <div className="flex items-center gap-2 text-xs py-1">
      <div className="text-[#A1A1AA] w-4 flex-shrink-0">{icon}</div>
      <span className="text-[#A1A1AA] w-36 flex-shrink-0 truncate">{label}</span>
      <div className="flex-1 h-1.5 bg-[#0B0B0D] rounded-full overflow-hidden border border-[#2A2A30]">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[#F4F4F5] font-mono w-20 text-right flex-shrink-0">
        {typeof value === 'number' && !Number.isInteger(value) ? value.toFixed(2) : value}
        {unit ? ` ${unit}` : ''}
      </span>
    </div>
  );
}

export default function RiskPrediction({ data }: RiskPredictionProps) {
  const [filter, setFilter] = useState<'all' | 'fix_soon' | 'keep_eye'>('all');
  const [search, setSearch] = useState('');
  const [visibleCount, setVisibleCount] = useState(5);
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({});
  const [techBreakdownOpen, setTechBreakdownOpen] = useState<Record<string, boolean>>({});

  const fixSoonCount = useMemo(
    () => data.filter(d => (d.risk_score ?? 0) >= 80).length,
    [data]
  );
  const keepEyeCount = useMemo(
    () => data.filter(d => (d.risk_score ?? 0) >= 50 && (d.risk_score ?? 0) < 80).length,
    [data]
  );

  // Most common problem across flagged files (risk_score >= 50)
  const mostCommonProblem = useMemo(() => {
    const flagged = data.filter(d => (d.risk_score ?? 0) >= 50);
    if (flagged.length === 0) return { label: 'None detected', count: 0 };

    const counts: Record<string, number> = {
      'No clear owner': 0,
      'High complexity': 0,
      'Heavy dependencies': 0,
      'Frequent changes': 0,
      'Untouched legacy code': 0,
    };

    flagged.forEach(f => {
      if ((f.ownership_entropy ?? 0) > 1.2 || (f.author_count ?? 0) > 4) counts['No clear owner']++;
      if ((f.complexity ?? 0) > 10) counts['High complexity']++;
      if ((f.dependency_count ?? 0) > 8) counts['Heavy dependencies']++;
      if ((f.churn ?? 0) > CHURN_VERY_HIGH_THRESHOLD) counts['Frequent changes']++;
      if ((f.complexity ?? 0) > 10 && (f.recent_churn ?? 0) === 0) counts['Untouched legacy code']++;
    });

    let topLabel = 'No clear owner';
    let max = -1;
    for (const [k, v] of Object.entries(counts)) {
      if (v > max) {
        max = v;
        topLabel = k;
      }
    }
    return { label: topLabel, count: max };
  }, [data]);

  // Filtered and searched data
  const filtered = useMemo(() => {
    let list = data;
    if (filter === 'fix_soon') {
      list = list.filter(d => (d.risk_score ?? 0) >= 80);
    } else if (filter === 'keep_eye') {
      list = list.filter(d => (d.risk_score ?? 0) >= 50 && (d.risk_score ?? 0) < 80);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(d => d.file_path.toLowerCase().includes(q));
    }
    return list;
  }, [data, filter, search]);

  const visibleFiles = useMemo(
    () => filtered.slice(0, visibleCount),
    [filtered, visibleCount]
  );

  const toggleExpand = (filePath: string) => {
    setExpandedFiles(prev => ({
      ...prev,
      [filePath]: !prev[filePath],
    }));
  };

  const toggleTech = (filePath: string) => {
    setTechBreakdownOpen(prev => ({
      ...prev,
      [filePath]: !prev[filePath],
    }));
  };

  const scrollToHow = () => {
    const el = document.getElementById('how');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-24 text-[#A1A1AA] bg-[#141417] border border-[#2A2A30] rounded-2xl">
        <FileCode2 className="w-10 h-10 text-[#71717A] mx-auto mb-3" />
        <p className="text-lg font-semibold text-[#F4F4F5]">No risk predictions available</p>
        <p className="text-sm text-[#A1A1AA] mt-1">
          Analyze this repository to generate AI-powered risk forecasts.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6 text-[#F4F4F5]">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#2A2A30]">
        <div>
          <h1 className="text-3xl font-bold text-[#F4F4F5] tracking-tight">Risk Forecast</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">
            Files most likely to cause bugs next — and what to do about them.
          </p>
        </div>
        <button
          type="button"
          onClick={scrollToHow}
          aria-label="Scroll to how risk is calculated"
          className="min-h-[44px] px-4 py-2.5 rounded-xl border border-[#2A2A30] bg-[#141417] text-sm font-medium text-[#A1A1AA] hover:text-[#F4F4F5] hover:border-[#3F3F46] hover:bg-[#1C1C21] transition-all flex items-center justify-center gap-2 shrink-0 self-start sm:self-auto cursor-pointer"
        >
          <HelpCircle className="w-4 h-4 text-[#A1A1AA]" />
          <span>How is this calculated?</span>
        </button>
      </div>

      {/* 2. Summary row (3 cards, responsive grid, stacks on mobile) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Fix soon */}
        <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F87171]" />
              <span className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                Fix soon
              </span>
            </div>
            <p className="text-3xl font-bold text-[#F4F4F5] mt-2">
              {fixSoonCount}
            </p>
          </div>
          <p className="text-xs text-[#A1A1AA] mt-3">
            Very likely to break. Look at these first.
          </p>
        </div>

        {/* Keep an eye on */}
        <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FBBF24]" />
              <span className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                Keep an eye on
              </span>
            </div>
            <p className="text-3xl font-bold text-[#F4F4F5] mt-2">
              {keepEyeCount}
            </p>
          </div>
          <p className="text-xs text-[#A1A1AA] mt-3">
            Some warning signs. Add tests when you touch them.
          </p>
        </div>

        {/* Most common problem */}
        <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
              <span className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                Most common problem
              </span>
            </div>
            <p className="text-2xl font-bold text-[#F4F4F5] mt-2 truncate">
              {mostCommonProblem.label}
            </p>
          </div>
          <p className="text-xs text-[#A1A1AA] mt-3">
            {mostCommonProblem.count > 0
              ? `Top recurring issue across flagged files.`
              : 'No recurring anomalies detected.'}
          </p>
        </div>
      </div>

      {/* 3. Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
        {/* Segmented control tabs */}
        <div className="inline-flex items-center bg-[#141417] border border-[#2A2A30] p-1 rounded-xl gap-1">
          <button
            type="button"
            onClick={() => { setFilter('all'); setVisibleCount(5); }}
            aria-label="Show all files"
            className={`min-h-[44px] px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer ${
              filter === 'all'
                ? 'bg-[#2A2A30] text-[#F4F4F5]'
                : 'text-[#A1A1AA] hover:text-[#F4F4F5] hover:bg-[#1A1A1F]'
            }`}
          >
            All ({data.length})
          </button>
          <button
            type="button"
            onClick={() => { setFilter('fix_soon'); setVisibleCount(5); }}
            aria-label="Filter by Fix soon"
            className={`min-h-[44px] px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer flex items-center gap-2 ${
              filter === 'fix_soon'
                ? 'bg-[#2A2A30] text-[#F4F4F5]'
                : 'text-[#A1A1AA] hover:text-[#F4F4F5] hover:bg-[#1A1A1F]'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-[#F87171]" />
            Fix soon ({fixSoonCount})
          </button>
          <button
            type="button"
            onClick={() => { setFilter('keep_eye'); setVisibleCount(5); }}
            aria-label="Filter by Keep an eye on"
            className={`min-h-[44px] px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer flex items-center gap-2 ${
              filter === 'keep_eye'
                ? 'bg-[#2A2A30] text-[#F4F4F5]'
                : 'text-[#A1A1AA] hover:text-[#F4F4F5] hover:bg-[#1A1A1F]'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-[#FBBF24]" />
            Keep an eye on ({keepEyeCount})
          </button>
        </div>

        {/* Search input */}
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#71717A]" />
          <input
            type="text"
            placeholder="Search by file name or path..."
            value={search}
            onChange={e => { setSearch(e.target.value); setVisibleCount(5); }}
            aria-label="Search files by name or path"
            className="w-full min-h-[44px] bg-[#141417] border border-[#2A2A30] rounded-xl pl-10 pr-4 text-sm text-[#F4F4F5] placeholder-[#71717A] focus:outline-none focus:border-[#52525B] transition-colors"
          />
        </div>
      </div>

      {/* 4. File list */}
      <div className="space-y-3 pt-1">
        {visibleFiles.length === 0 ? (
          <div className="bg-[#141417] border border-[#2A2A30] rounded-2xl p-8 text-center text-[#A1A1AA]">
            No files match the selected filter or search criteria.
          </div>
        ) : (
          visibleFiles.map(file => {
            const isFixSoon = (file.risk_score ?? 0) >= 80;
            const isOpen = !!expandedFiles[file.file_path];
            const isTechOpen = !!techBreakdownOpen[file.file_path];
            const { fileName, folder } = splitFilePath(file.file_path);

            return (
              <div
                key={file.file_path}
                className={`bg-[#141417] border rounded-2xl transition-all duration-200 py-[22px] px-[24px] ${
                  isOpen && isFixSoon
                    ? 'border-red-900/60 shadow-sm shadow-red-950/40'
                    : isOpen
                    ? 'border-[#3F3F46]'
                    : 'border-[#2A2A30] hover:border-[#3F3F46]'
                }`}
              >
                {/* Collapsed top row */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {/* Status pill + file name + folder */}
                    <div className="flex items-center gap-2.5 flex-wrap">
                      {isFixSoon ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-950/40 text-[#F87171] border border-red-900/50">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#F87171]" />
                          Fix soon
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950/40 text-[#FBBF24] border border-amber-900/50">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#FBBF24]" />
                          Keep an eye on
                        </span>
                      )}

                      <span className="font-bold text-base text-[#F4F4F5] truncate">
                        {fileName}
                      </span>
                      {folder && (
                        <span className="text-sm text-[#A1A1AA] font-mono truncate" title={file.file_path}>
                          {folder}
                        </span>
                      )}
                    </div>

                    {/* Single plain-English explanation */}
                    <p className="text-sm text-[#A1A1AA] mt-2.5 leading-relaxed">
                      {explainRisk(file)}
                    </p>
                  </div>

                  {/* Details toggle button */}
                  <button
                    type="button"
                    onClick={() => toggleExpand(file.file_path)}
                    aria-expanded={isOpen}
                    aria-label={isOpen ? `Hide details for ${fileName}` : `Show details for ${fileName}`}
                    className="min-h-[44px] min-w-[100px] px-3.5 py-2 rounded-xl border border-[#2A2A30] bg-[#0B0B0D] hover:bg-[#1C1C21] hover:border-[#3F3F46] text-sm font-medium text-[#F4F4F5] flex items-center justify-center gap-1.5 transition-all self-end sm:self-center shrink-0 cursor-pointer"
                  >
                    <span>Details</span>
                    {isOpen ? (
                      <ChevronUp className="w-4 h-4 text-[#A1A1AA]" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-[#A1A1AA]" />
                    )}
                  </button>
                </div>

                {/* 5. Expanded details */}
                {isOpen && (
                  <div className="mt-5 pt-5 border-t border-[#2A2A30] space-y-5">
                    {/* 4 Stat Boxes Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {/* 1. Who works on it */}
                      <div className="bg-[#0B0B0D] border border-[#2A2A30] rounded-xl p-4">
                        <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                          Who works on it
                        </p>
                        <p className="text-xl font-bold text-[#F4F4F5] mt-1.5">
                          {file.author_count ?? 1} people
                        </p>
                        <p className="text-xs font-medium mt-1">
                          {(file.ownership_entropy ?? 0) > 1.5 ? (
                            <span className="text-[#F87171]">No clear owner</span>
                          ) : (file.ownership_entropy ?? 0) >= 0.8 ? (
                            <span className="text-[#FBBF24]">Shared</span>
                          ) : (
                            <span className="text-emerald-400">Clear owner</span>
                          )}
                        </p>
                      </div>

                      {/* 2. How connected it is */}
                      <div className="bg-[#0B0B0D] border border-[#2A2A30] rounded-xl p-4">
                        <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                          How connected it is
                        </p>
                        <p className="text-xl font-bold text-[#F4F4F5] mt-1.5">
                          {file.dependency_count ?? 0} imports
                        </p>
                        <p className="text-xs font-medium mt-1">
                          {(file.dependency_count ?? 0) > 15 ? (
                            <span className="text-[#F87171]">Highly connected</span>
                          ) : (file.dependency_count ?? 0) > 3 ? (
                            <span className="text-[#FBBF24]">Some connections</span>
                          ) : (
                            <span className="text-[#A1A1AA]">Isolated</span>
                          )}
                        </p>
                      </div>

                      {/* 3. How hard to read */}
                      <div className="bg-[#0B0B0D] border border-[#2A2A30] rounded-xl p-4">
                        <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                          How hard to read
                        </p>
                        <p className="text-xl font-bold mt-1.5">
                          {(file.complexity ?? 0) > 12 ? (
                            <span className="text-[#F87171]">High</span>
                          ) : (file.complexity ?? 0) > 6 ? (
                            <span className="text-[#FBBF24]">Medium</span>
                          ) : (
                            <span className="text-emerald-400">Low</span>
                          )}
                        </p>
                        <p className="text-xs text-[#A1A1AA] mt-1">
                          Complexity {(file.complexity ?? 0).toFixed(1)}
                        </p>
                      </div>

                      {/* 4. Recent activity */}
                      <div className="bg-[#0B0B0D] border border-[#2A2A30] rounded-xl p-4">
                        <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider">
                          Recent activity
                        </p>
                        <p className="text-xl font-bold mt-1.5">
                          {(file.recent_churn ?? 0) > 0 ? (
                            <span className="text-[#FBBF24]">Active</span>
                          ) : (
                            <span className="text-[#A1A1AA]">Quiet</span>
                          )}
                        </p>
                        <p className="text-xs text-[#A1A1AA] mt-1">
                          {file.recent_churn ?? 0} changes in 90 days
                        </p>
                      </div>
                    </div>

                    {/* Suggested next steps */}
                    <div className="bg-[#0B0B0D] border border-[#2A2A30] rounded-xl p-4">
                      <p className="text-xs font-semibold text-[#A1A1AA] uppercase tracking-wider mb-2.5">
                        Suggested next steps
                      </p>
                      <ul className="space-y-2">
                        {getNextSteps(file).map((step, idx) => (
                          <li key={idx} className="flex items-start gap-2.5 text-sm text-[#F4F4F5]">
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            <span>{step}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Toggle full technical breakdown */}
                    <div>
                      <button
                        type="button"
                        onClick={() => toggleTech(file.file_path)}
                        aria-expanded={isTechOpen}
                        className="min-h-[44px] text-xs font-medium text-blue-400 hover:text-blue-300 underline underline-offset-4 flex items-center gap-1.5 cursor-pointer"
                      >
                        {isTechOpen ? "Hide technical breakdown" : "Show full technical breakdown (9 signals)"}
                      </button>

                      {isTechOpen && (
                        <div className="mt-3 bg-[#0B0B0D] border border-[#2A2A30] rounded-xl p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-[#2A2A30] text-xs">
                            <span className="text-[#A1A1AA]">
                              Raw Risk Score: <strong className="text-[#F4F4F5]">{file.risk_score.toFixed(2)}%</strong>
                            </span>
                            <span className="text-[#71717A] font-mono">
                              Model: Isolation Forest
                            </span>
                          </div>

                          <div className="space-y-1">
                            <FeatureBar
                              label="Total Churn"
                              value={file.churn ?? 0}
                              max={100}
                              icon={<GitCommit className="w-3 h-3" />}
                              color="bg-blue-500"
                              unit="commits"
                            />
                            <FeatureBar
                              label="Complexity"
                              value={file.complexity ?? 0}
                              max={30}
                              icon={<Activity className="w-3 h-3" />}
                              color="bg-purple-500"
                            />
                            <FeatureBar
                              label="Distinct Authors"
                              value={file.author_count ?? 1}
                              max={20}
                              icon={<Users className="w-3 h-3" />}
                              color="bg-indigo-500"
                              unit="authors"
                            />
                            <FeatureBar
                              label="Lines Added"
                              value={file.lines_added ?? 0}
                              max={10000}
                              icon={<TrendingUp className="w-3 h-3" />}
                              color="bg-green-500"
                              unit="lines"
                            />
                            <FeatureBar
                              label="Lines Deleted"
                              value={file.lines_deleted ?? 0}
                              max={5000}
                              icon={<ArrowDownUp className="w-3 h-3" />}
                              color="bg-rose-500"
                              unit="lines"
                            />
                            <FeatureBar
                              label="Commit Frequency"
                              value={file.commit_frequency ?? 0}
                              max={5}
                              icon={<Clock className="w-3 h-3" />}
                              color="bg-yellow-500"
                              unit="/ day"
                            />
                            <FeatureBar
                              label="Recent Churn (90d)"
                              value={file.recent_churn ?? 0}
                              max={50}
                              icon={<GitPullRequest className="w-3 h-3" />}
                              color="bg-orange-500"
                              unit="commits"
                            />
                            <FeatureBar
                              label="Ownership Entropy"
                              value={file.ownership_entropy ?? 0}
                              max={3}
                              icon={<Layers className="w-3 h-3" />}
                              color="bg-pink-500"
                              unit="bits"
                            />
                            <FeatureBar
                              label="Dependencies"
                              value={file.dependency_count ?? 0}
                              max={30}
                              icon={<Layers className="w-3 h-3" />}
                              color="bg-cyan-500"
                              unit="imports"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* 6. Pagination */}
      <div className="flex items-center justify-between pt-2">
        <p className="text-sm text-[#A1A1AA]">
          Showing {Math.min(visibleCount, filtered.length)} of {filtered.length} files
        </p>

        {visibleCount < filtered.length && (
          <button
            type="button"
            onClick={() => setVisibleCount(c => c + 5)}
            aria-label="Show 5 more files"
            className="min-h-[44px] px-5 py-2 rounded-xl bg-[#141417] border border-[#2A2A30] hover:border-[#3F3F46] hover:bg-[#1C1C21] text-sm font-medium text-[#F4F4F5] transition-all cursor-pointer"
          >
            Show more
          </button>
        )}
      </div>

      {/* 7. Explainer section at the bottom (id="how") */}
      <div id="how" className="mt-12 bg-[#141417] border border-[#2A2A30] rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-bold text-[#F4F4F5]">How to read this</h2>
        </div>
        <p className="text-sm text-[#A1A1AA] leading-relaxed">
          We compare every file's history — how often it changes, how many people edit it, how many files depend on it, and how complex it is. Files that look unusual on several of these at once are flagged.
        </p>

        {/* Legend */}
        <div className="pt-2 border-t border-[#2A2A30] flex flex-wrap gap-6 text-xs text-[#A1A1AA]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F87171]" />
            <span><strong className="text-[#F4F4F5]">Fix soon</strong> — act this sprint</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FBBF24]" />
            <span><strong className="text-[#F4F4F5]">Keep an eye on</strong> — add tests when touched</span>
          </div>
        </div>
      </div>
    </div>
  );
}
