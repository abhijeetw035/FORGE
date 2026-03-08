'use client';

import { useState } from 'react';
import { ContributorData } from '@/lib/api';
import { Users, Code, Zap, Award, TrendingUp, GitCommit, ChevronLeft, ChevronRight } from 'lucide-react';

interface ContributorsProps {
  data: ContributorData[];
}

const ITEMS_PER_PAGE = 10;

export default function Contributors({ data }: ContributorsProps) {
  const [currentPage, setCurrentPage] = useState(1);

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-zinc-500">
        No contributor data available
      </div>
    );
  }

  const totalCommits = data.reduce((sum, c) => sum + c.total_commits, 0);
  const totalFunctions = data.reduce((sum, c) => sum + c.functions_added, 0);
  const totalLOC = data.reduce((sum, c) => sum + c.total_loc, 0);

  const getEntropyColor = (score: number, maxScore: number) => {
    const ratio = score / maxScore;
    if (ratio > 0.7) return 'text-red-400';
    if (ratio > 0.4) return 'text-orange-400';
    return 'text-green-400';
  };

  const maxEntropy = Math.max(...data.map(c => c.entropy_score));
  const topContributor = data[0];

  const getInitials = (name: string) =>
    name.split(/\s+/).map(n => n[0]).slice(0, 2).join('').toUpperCase();

  const avatarBg = (i: number) => {
    const classes = ['bg-zinc-700', 'bg-zinc-600', 'bg-zinc-700', 'bg-zinc-600'];
    return classes[i % classes.length];
  };

  // pagination
  const totalPages = Math.ceil(data.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const pageData = data.slice(startIndex, startIndex + ITEMS_PER_PAGE);

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
            <Users className="w-5 h-5 text-zinc-100" />
            Team Entropy Metrics
          </h3>
          <p className="text-sm text-zinc-500 mt-1">
            Understanding code complexity contributions across the team
          </p>
        </div>
      </div>

      {/* Disclaimer — no emojis */}
      <div className="glass-card p-4">
        <div className="flex items-start gap-3">
          <div>
            <p className="font-semibold mb-1 text-zinc-100">Important Context</p>
            <p className="text-xs text-zinc-400">
              Higher entropy isn't "bad" — it often means tackling complex features or refactoring legacy code.
              Use these metrics to identify where code reviews might need extra attention, not to judge performance.
              Complex code requires complex solutions.
            </p>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-card p-4 border-l-2 border-zinc-700">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-5 h-5 text-zinc-300" />
            <p className="text-xs font-semibold text-zinc-400">Contributors</p>
          </div>
          <p className="text-2xl font-bold text-zinc-50">{data.length}</p>
        </div>
        <div className="glass-card p-4 border-l-2 border-zinc-700">
          <div className="flex items-center gap-2 mb-2">
            <GitCommit className="w-5 h-5 text-zinc-300" />
            <p className="text-xs font-semibold text-zinc-400">Total Commits</p>
          </div>
          <p className="text-2xl font-bold text-zinc-50">{totalCommits.toLocaleString()}</p>
        </div>
        <div className="glass-card p-4 border-l-2 border-zinc-700">
          <div className="flex items-center gap-2 mb-2">
            <Code className="w-5 h-5 text-zinc-300" />
            <p className="text-xs font-semibold text-zinc-400">Functions</p>
          </div>
          <p className="text-2xl font-bold text-zinc-50">{totalFunctions.toLocaleString()}</p>
        </div>
        <div className="glass-card p-4 border-l-2 border-zinc-700">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-zinc-300" />
            <p className="text-xs font-semibold text-zinc-400">Lines of Code</p>
          </div>
          <p className="text-2xl font-bold text-zinc-50">{totalLOC.toLocaleString()}</p>
        </div>
      </div>

      {/* Top Contributor Highlight */}
      <div className="bg-zinc-900/50 rounded-md p-6 border border-zinc-800 border-l-4 border-l-rose-500">
        <div className="flex items-center gap-3 mb-4">
          <Award className="w-8 h-8 text-yellow-400" />
          <div>
            <h4 className="text-lg font-bold text-zinc-100">Highest Entropy Contributor</h4>
            <p className="text-sm text-zinc-400">Most complex code contributions</p>
          </div>
        </div>
        <div className="bg-zinc-900/50 rounded-md p-4 border border-zinc-800">
          <p className="text-2xl font-bold text-zinc-50 mb-2">{topContributor.author}</p>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-zinc-400">Entropy Score</p>
              <p className="text-xl font-bold text-zinc-50">{topContributor.entropy_score}</p>
            </div>
            <div>
              <p className="text-zinc-400">Avg Complexity</p>
              <p className="text-xl font-bold text-zinc-50">{topContributor.avg_complexity}</p>
            </div>
            <div>
              <p className="text-zinc-400">Functions</p>
              <p className="text-xl font-bold text-zinc-50">{topContributor.functions_added}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Contributors Table */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            Detailed Contributor Breakdown
          </h4>
          <span className="text-xs text-zinc-500">
            {data.length} contributor{data.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-zinc-950/50 text-zinc-400 border-b border-zinc-800 uppercase text-xs tracking-wider">
                <th className="text-left py-3 px-4 font-semibold">Author</th>
                <th className="text-right py-3 px-4 font-semibold">
                  <div className="flex items-center justify-end gap-1">
                    <Zap className="w-3 h-3" /> Entropy
                  </div>
                </th>
                <th className="text-right py-3 px-4 font-semibold">
                  <div className="flex items-center justify-end gap-1">
                    <GitCommit className="w-3 h-3" /> Commits
                  </div>
                </th>
                <th className="text-right py-3 px-4 font-semibold">
                  <div className="flex items-center justify-end gap-1">
                    <Code className="w-3 h-3" /> Functions
                  </div>
                </th>
                <th className="text-right py-3 px-4 font-semibold">Avg Complexity</th>
                <th className="text-right py-3 px-4 font-semibold">Total LOC</th>
                <th className="text-right py-3 px-4 font-semibold">Impact %</th>
              </tr>
            </thead>
            <tbody>
              {pageData.map((contributor, index) => {
                const globalIndex = startIndex + index;
                const impactPercent = (contributor.functions_added / totalFunctions * 100).toFixed(1);
                return (
                  <tr
                    key={contributor.author}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className={`flex items-center justify-center w-8 h-8 rounded-full text-zinc-50 ${avatarBg(globalIndex)}`}>
                          {getInitials(contributor.author)}
                        </div>
                        <div>
                          <div className="text-xs font-mono text-zinc-500">#{globalIndex + 1}</div>
                          <div className="font-medium text-zinc-100">{contributor.author}</div>
                        </div>
                      </div>
                    </td>
                    <td className={`py-3 px-4 text-right font-bold ${getEntropyColor(contributor.entropy_score, maxEntropy)}`}>
                      {contributor.entropy_score}
                    </td>
                    <td className="py-3 px-4 text-right text-zinc-300">{contributor.total_commits}</td>
                    <td className="py-3 px-4 text-right text-zinc-300">{contributor.functions_added.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right text-zinc-300">{contributor.avg_complexity}</td>
                    <td className="py-3 px-4 text-right text-zinc-300">{contributor.total_loc.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-zinc-800 rounded-full h-2">
                          <div
                            className="bg-purple-400 h-2 rounded-full"
                            style={{ width: `${impactPercent}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-zinc-400 w-10 text-right">
                          {impactPercent}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-zinc-800">
            <span className="text-xs text-zinc-500">
              Showing {startIndex + 1}–{Math.min(startIndex + ITEMS_PER_PAGE, data.length)} of {data.length} contributors
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-all
                  ${currentPage === 1
                    ? 'bg-zinc-900/50 text-zinc-600 cursor-not-allowed'
                    : 'bg-zinc-950/50 border border-zinc-800 text-white hover:bg-zinc-900 hover:border-zinc-700'}`}
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Prev
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                <button
                  key={page}
                  onClick={() => setCurrentPage(page)}
                  className={`w-8 h-8 rounded-md text-xs font-medium transition-all
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
                className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium transition-all
                  ${currentPage === totalPages
                    ? 'bg-zinc-900/50 text-zinc-600 cursor-not-allowed'
                    : 'bg-zinc-950/50 border border-zinc-800 text-white hover:bg-zinc-900 hover:border-zinc-700'}`}
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Interpretation Guide — no emojis */}
      <div className="bg-zinc-950/50 border border-zinc-800 rounded-md p-4">
        <h4 className="text-sm font-semibold text-white mb-2">How to Read These Metrics</h4>
        <div className="space-y-2 text-xs text-white">
          <p><strong>Entropy Score:</strong> Avg Complexity × Functions Added — indicates overall complexity contribution</p>
          <p><strong>High entropy:</strong> Could mean working on algorithms, parsers, or refactoring legacy systems</p>
          <p><strong>Low entropy:</strong> Could mean working on APIs, configs, or simple utilities</p>
          <p><strong>Best use:</strong> Identify files or features that might benefit from pair programming or extra review</p>
        </div>
      </div>
    </div>
  );
}
