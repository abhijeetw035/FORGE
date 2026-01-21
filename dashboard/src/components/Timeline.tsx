'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { TimelineData } from '@/lib/api';
import { TrendingUp, GitCommit, Code } from 'lucide-react';

interface TimelineProps {
  data: TimelineData[];
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-gray-900 text-white p-4 rounded-lg shadow-xl border border-gray-700 max-w-sm">
        <div className="flex items-center gap-2 mb-2">
          <GitCommit className="w-4 h-4 text-blue-400" />
          <p className="font-semibold text-sm">{data.sha}</p>
        </div>
        <p className="text-xs text-gray-300 mb-3 line-clamp-2">{data.message}</p>
        <div className="space-y-1 text-xs">
          <p className="text-gray-300">Date: {new Date(data.date).toLocaleDateString()}</p>
          <p className="text-blue-300">Functions: {data.function_count.toLocaleString()}</p>
          <p className="text-orange-300">Avg Complexity: {data.avg_complexity}</p>
          <p className="text-green-300">Total LOC: {data.total_loc.toLocaleString()}</p>
        </div>
      </div>
    );
  }
  return null;
};

export default function Timeline({ data }: TimelineProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-gray-500">
        No timeline data available
      </div>
    );
  }

  const maxComplexity = Math.max(...data.map(d => d.avg_complexity));
  const maxFunctions = Math.max(...data.map(d => d.function_count));

  const chartData = data.map((item, index) => ({
    ...item,
    index,
    dateLabel: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  }));

  const findSpikes = () => {
    const spikes = [];
    for (let i = 1; i < data.length - 1; i++) {
      const prev = data[i - 1].avg_complexity;
      const curr = data[i].avg_complexity;
      const next = data[i + 1].avg_complexity;
      
      if (curr > prev * 1.5 && curr > next) {
        spikes.push({
          index: i,
          commit: data[i],
          increase: ((curr - prev) / prev * 100).toFixed(1)
        });
      }
    }
    return spikes;
  };

  const spikes = findSpikes();

  return (
    <div className="w-full space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Code Evolution Timeline
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Complexity and function count over {data.length} commits
          </p>
        </div>
        {spikes.length > 0 && (
          <div className="bg-orange-50 dark:bg-orange-900/20 px-4 py-2 rounded-lg border border-orange-200 dark:border-orange-800">
            <p className="text-xs font-semibold text-orange-800 dark:text-orange-300">
              {spikes.length} Complexity Spike{spikes.length > 1 ? 's' : ''} Detected
            </p>
          </div>
        )}
      </div>

      {spikes.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-yellow-900 dark:text-yellow-300 mb-2 flex items-center gap-2">
            ⚠️ Complexity Spikes Detected
          </h4>
          <div className="space-y-2">
            {spikes.map((spike, idx) => (
              <div key={idx} className="text-xs bg-white dark:bg-gray-800 rounded p-2 border border-yellow-200 dark:border-yellow-800">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-blue-600 dark:text-blue-400">{spike.commit.sha}</span>
                  <span className="text-orange-600 dark:text-orange-400 font-semibold">+{spike.increase}% complexity</span>
                </div>
                <p className="text-gray-600 dark:text-gray-400 line-clamp-1">{spike.commit.message}</p>
                <p className="text-gray-500 dark:text-gray-500 mt-1">
                  {new Date(spike.commit.date).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Average Complexity Trend</h4>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="complexityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="dateLabel" 
                stroke="#6b7280"
                fontSize={11}
                interval="preserveStartEnd"
              />
              <YAxis 
                stroke="#6b7280"
                fontSize={11}
                label={{ value: 'Complexity', angle: -90, position: 'insideLeft', style: { fill: '#6b7280', fontSize: 11 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="avg_complexity" 
                stroke="#f59e0b" 
                strokeWidth={2}
                fill="url(#complexityGradient)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Function Count Growth</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="dateLabel" 
                stroke="#6b7280"
                fontSize={11}
                interval="preserveStartEnd"
              />
              <YAxis 
                stroke="#6b7280"
                fontSize={11}
                label={{ value: 'Functions', angle: -90, position: 'insideLeft', style: { fill: '#6b7280', fontSize: 11 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="function_count" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 5 }}
                name="Functions"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-2">
            <Code className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <p className="text-xs font-semibold text-blue-900 dark:text-blue-300">Peak Complexity</p>
          </div>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{maxComplexity.toFixed(2)}</p>
        </div>

        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
            <p className="text-xs font-semibold text-green-900 dark:text-green-300">Max Functions</p>
          </div>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{maxFunctions.toLocaleString()}</p>
        </div>

        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 border border-purple-200 dark:border-purple-800">
          <div className="flex items-center gap-2 mb-2">
            <GitCommit className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <p className="text-xs font-semibold text-purple-900 dark:text-purple-300">Total Commits</p>
          </div>
          <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{data.length}</p>
        </div>
      </div>
    </div>
  );
}
