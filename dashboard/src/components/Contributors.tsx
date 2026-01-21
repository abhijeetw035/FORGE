'use client';

import { ContributorData } from '@/lib/api';
import { Users, Code, Zap, Award, TrendingUp, GitCommit } from 'lucide-react';

interface ContributorsProps {
  data: ContributorData[];
}

export default function Contributors({ data }: ContributorsProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-gray-500">
        No contributor data available
      </div>
    );
  }

  const totalCommits = data.reduce((sum, c) => sum + c.total_commits, 0);
  const totalFunctions = data.reduce((sum, c) => sum + c.functions_added, 0);
  const totalLOC = data.reduce((sum, c) => sum + c.total_loc, 0);

  const getEntropyColor = (score: number, maxScore: number) => {
    const ratio = score / maxScore;
    if (ratio > 0.7) return 'text-red-600 dark:text-red-400';
    if (ratio > 0.4) return 'text-orange-600 dark:text-orange-400';
    return 'text-green-600 dark:text-green-400';
  };

  const getEntropyBg = (score: number, maxScore: number) => {
    const ratio = score / maxScore;
    if (ratio > 0.7) return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
    if (ratio > 0.4) return 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800';
    return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
  };

  const maxEntropy = Math.max(...data.map(c => c.entropy_score));
  const topContributor = data[0];

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            Team Entropy Metrics
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Understanding code complexity contributions across the team
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <div className="text-2xl">ℹ️</div>
          <div className="text-sm text-blue-900 dark:text-blue-300">
            <p className="font-semibold mb-1">Important Context</p>
            <p className="text-xs text-blue-700 dark:text-blue-400">
              Higher entropy isn't "bad" - it often means tackling complex features or refactoring legacy code. 
              Use these metrics to identify where code reviews might need extra attention, not to judge performance.
              Complex code requires complex solutions. 🧠
            </p>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <p className="text-xs font-semibold text-purple-900 dark:text-purple-300">Contributors</p>
          </div>
          <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{data.length}</p>
        </div>

        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-2">
            <GitCommit className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <p className="text-xs font-semibold text-blue-900 dark:text-blue-300">Total Commits</p>
          </div>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalCommits.toLocaleString()}</p>
        </div>

        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2 mb-2">
            <Code className="w-5 h-5 text-green-600 dark:text-green-400" />
            <p className="text-xs font-semibold text-green-900 dark:text-green-300">Functions</p>
          </div>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{totalFunctions.toLocaleString()}</p>
        </div>

        <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4 border border-orange-200 dark:border-orange-800">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            <p className="text-xs font-semibold text-orange-900 dark:text-orange-300">Lines of Code</p>
          </div>
          <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">{totalLOC.toLocaleString()}</p>
        </div>
      </div>

      {/* Top Contributor Highlight */}
      <div className={`rounded-lg p-6 border ${getEntropyBg(topContributor.entropy_score, maxEntropy)}`}>
        <div className="flex items-center gap-3 mb-4">
          <Award className="w-8 h-8 text-yellow-600 dark:text-yellow-400" />
          <div>
            <h4 className="text-lg font-bold text-gray-900 dark:text-white">
              Highest Entropy Contributor
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Most complex code contributions
            </p>
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <p className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{topContributor.author}</p>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600 dark:text-gray-400">Entropy Score</p>
              <p className="text-xl font-bold text-orange-600 dark:text-orange-400">{topContributor.entropy_score}</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Avg Complexity</p>
              <p className="text-xl font-bold text-blue-600 dark:text-blue-400">{topContributor.avg_complexity}</p>
            </div>
            <div>
              <p className="text-gray-600 dark:text-gray-400">Functions</p>
              <p className="text-xl font-bold text-green-600 dark:text-green-400">{topContributor.functions_added}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Contributors Table */}
      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
          Detailed Contributor Breakdown
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-300 dark:border-gray-600">
                <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">Author</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                  <div className="flex items-center justify-end gap-1">
                    <Zap className="w-3 h-3" />
                    Entropy
                  </div>
                </th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                  <div className="flex items-center justify-end gap-1">
                    <GitCommit className="w-3 h-3" />
                    Commits
                  </div>
                </th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                  <div className="flex items-center justify-end gap-1">
                    <Code className="w-3 h-3" />
                    Functions
                  </div>
                </th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">Avg Complexity</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">Total LOC</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">Impact %</th>
              </tr>
            </thead>
            <tbody>
              {data.map((contributor, index) => {
                const impactPercent = (contributor.functions_added / totalFunctions * 100).toFixed(1);
                return (
                  <tr 
                    key={contributor.author} 
                    className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-gray-500 dark:text-gray-400">#{index + 1}</span>
                        <span className="font-medium text-gray-900 dark:text-white">{contributor.author}</span>
                      </div>
                    </td>
                    <td className={`py-3 px-4 text-right font-bold ${getEntropyColor(contributor.entropy_score, maxEntropy)}`}>
                      {contributor.entropy_score}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">
                      {contributor.total_commits}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">
                      {contributor.functions_added.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">
                      {contributor.avg_complexity}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">
                      {contributor.total_loc.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-purple-600 dark:bg-purple-400 h-2 rounded-full"
                            style={{ width: `${impactPercent}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-medium text-gray-600 dark:text-gray-400 w-10 text-right">
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
      </div>

      {/* Interpretation Guide */}
      <div className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-yellow-900 dark:text-yellow-300 mb-2">
          📊 How to Read These Metrics
        </h4>
        <div className="space-y-2 text-xs text-yellow-800 dark:text-yellow-400">
          <p><strong>Entropy Score:</strong> Avg Complexity × Functions Added - indicates overall complexity contribution</p>
          <p><strong>High entropy isn't bad:</strong> Could mean working on algorithms, parsers, or refactoring legacy systems</p>
          <p><strong>Low entropy isn't bad:</strong> Could mean working on APIs, configs, or simple utilities</p>
          <p><strong>Best use:</strong> Identify files/features that might benefit from pair programming or extra review</p>
        </div>
      </div>
    </div>
  );
}
