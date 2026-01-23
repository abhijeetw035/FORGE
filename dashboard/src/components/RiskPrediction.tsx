'use client';

import { Brain, AlertTriangle, AlertCircle, Eye } from 'lucide-react';
import type { RiskPredictionData } from '@/lib/api';

interface RiskPredictionProps {
  data: RiskPredictionData[];
}

export default function RiskPrediction({ data }: RiskPredictionProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-zinc-500">
        No risk predictions available
      </div>
    );
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical':
        return {
          bg: 'bg-zinc-950/50',
          border: 'border-zinc-800',
          text: 'text-white',
          progressBg: 'bg-zinc-900',
          progressFill: 'bg-red-600',
          icon: AlertTriangle
        };
      case 'warning':
        return {
          bg: 'bg-zinc-950/50',
          border: 'border-zinc-800',
          text: 'text-white',
          progressBg: 'bg-zinc-900',
          progressFill: 'bg-orange-500',
          icon: AlertCircle
        };
      default:
        return {
          bg: 'bg-zinc-950/50',
          border: 'border-zinc-800',
          text: 'text-zinc-400',
          progressBg: 'bg-zinc-900',
          progressFill: 'bg-zinc-600',
          icon: Eye
        };
    }
  };

  const topRisks = data.slice(0, 5);
  const criticalCount = data.filter(d => d.risk_level === 'critical').length;
  const warningCount = data.filter(d => d.risk_level === 'warning').length;

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-cyan-400" />
            AI Risk Forecast
          </h3>
          <p className="text-sm text-zinc-500 mt-1">
            Machine learning predictions for files at risk
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1 bg-zinc-950/50 border border-zinc-800 rounded-md">
            <span className="text-xs font-semibold text-white">{criticalCount} Critical</span>
          </div>
          <div className="px-3 py-1 bg-zinc-950/50 border border-zinc-800 rounded-md">
            <span className="text-xs font-semibold text-white">{warningCount} Warning</span>
          </div>
        </div>
      </div>

      <div className="bg-zinc-950/50 border border-zinc-800 rounded-md p-4">
        <div className="flex items-start gap-3">
          <div className="text-2xl">🔮</div>
          <div>
            <p className="font-semibold mb-1 text-white">How it works</p>
            <p className="text-xs text-zinc-400">
              Using Isolation Forest algorithm to detect statistical anomalies in code complexity, 
              change frequency, and authorship patterns. Files that deviate significantly from the 
              norm are flagged as high-risk.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {topRisks.map((file, index) => {
          const colors = getRiskColor(file.risk_level);
          const Icon = colors.icon;
          const fileName = file.file_path.split('/').pop() || file.file_path;
          
          return (
            <div
              key={index}
              className={`${colors.bg} border ${colors.border} rounded-md p-4 hover:border-opacity-100 transition-all duration-200`}
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <Icon className={`w-5 h-5 ${colors.text} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate" title={file.file_path}>
                      {fileName}
                    </p>
                    <p className="text-xs text-zinc-400 truncate mt-0.5">
                      {file.file_path}
                    </p>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className={`text-2xl font-bold text-white`}>
                    {Math.round(file.risk_score)}%
                  </p>
                  <p className="text-xs text-zinc-400 uppercase tracking-wider">
                    {file.risk_level}
                  </p>
                </div>
              </div>

              <div className="mb-3">
                <div className={`w-full h-2 ${colors.progressBg} rounded-full overflow-hidden`}>
                  <div
                    className={`h-full ${colors.progressFill} transition-all duration-500`}
                    style={{ width: `${file.risk_score}%` }}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-4 text-zinc-400">
                  <span>Churn: {file.churn}</span>
                  <span>Complexity: {file.complexity}</span>
                  <span>Authors: {file.author_count}</span>
                </div>
                <span className={`font-medium text-zinc-400`}>
                  {file.reason}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {data.length > 5 && (
        <div className="text-center pt-2">
          <p className="text-sm text-zinc-500">
            Showing top 5 of {data.length} analyzed files
          </p>
        </div>
      )}

      <div className="glass-card p-4">
        <h4 className="text-sm font-semibold text-white mb-2">
          💡 Interpretation Guide
        </h4>
        <div className="space-y-1 text-xs text-zinc-400">
          <p><strong className="text-white">Critical (80-100%):</strong> Immediate attention required. High chance of bugs or maintenance issues.</p>
          <p><strong className="text-white">Warning (50-79%):</strong> Monitor closely. Consider refactoring or additional testing.</p>
          <p><strong className="text-white">Watchlist (&lt;50%):</strong> Keep an eye on these. May become problematic over time.</p>
        </div>
      </div>
    </div>
  );
}
