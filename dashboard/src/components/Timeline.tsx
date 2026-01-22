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
      <div className="bg-zinc-950 border border-zinc-800 text-zinc-200 p-4 rounded-md shadow-xl max-w-sm">
        <div className="flex items-center gap-2 mb-2">
          <GitCommit className="w-4 h-4 text-zinc-400" />
          <p className="font-semibold text-sm">{data.sha}</p>
        </div>
        <p className="text-xs mb-3 line-clamp-2">{data.message}</p>
        <div className="space-y-1 text-xs">
          <p>Date: {new Date(data.date).toLocaleDateString()}</p>
          <p className="text-blue-400">Functions: {data.function_count.toLocaleString()}</p>
          <p className="text-orange-400">Avg Complexity: {data.avg_complexity}</p>
          <p className="text-green-400">Total LOC: {data.total_loc.toLocaleString()}</p>
        </div>
      </div>
    );
  }
  return null;
};

export default function Timeline({ data }: TimelineProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-zinc-500">
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
          <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-zinc-100" />
            Code Evolution Timeline
          </h3>
          <p className="text-sm text-zinc-500 mt-1">
            Complexity and function count over {data.length} commits
          </p>
        </div>
        {spikes.length > 0 && (
          <div className="bg-orange-950/50 px-4 py-2 rounded-md border border-orange-800">
            <p className="text-xs font-semibold text-orange-400">
              {spikes.length} Complexity Spike{spikes.length > 1 ? 's' : ''} Detected
            </p>
          </div>
        )}
      </div>

      {spikes.length > 0 && (
        <div className="bg-yellow-950/30 border border-yellow-800 rounded-md p-4">
          <h4 className="text-sm font-semibold text-yellow-400 mb-2 flex items-center gap-2">
            ⚠️ Complexity Spikes Detected
          </h4>
          <div className="space-y-2">
            {spikes.map((spike, idx) => (
              <div key={idx} className="text-xs bg-zinc-900/50 rounded p-2 border border-yellow-800">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-zinc-300">{spike.commit.sha}</span>
                  <span className="text-orange-400 font-semibold">+{spike.increase}% complexity</span>
                </div>
                <p className="text-zinc-400 line-clamp-1">{spike.commit.message}</p>
                <p className="text-zinc-500 mt-1">
                  {new Date(spike.commit.date).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="glass-card p-4">
        <div className="mb-4">
          <h4 className="text-sm font-medium text-zinc-300 mb-2">Average Complexity Trend</h4>
          <ResponsiveContainer width="100%" height={250} style={{ background: 'transparent' }}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="complexityGradient" x1="0" y1="0" x2="0" y2="1">
                  {/* Professional Blue gradient fade to transparent */}
                  <stop offset="5%" stopColor="rgb(59, 130, 246)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="rgb(59, 130, 246)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" opacity={0.5} />
              <XAxis 
                dataKey="dateLabel" 
                stroke="#71717a"
                fontSize={11}
                interval="preserveStartEnd"
              />
              <YAxis 
                stroke="#71717a"
                fontSize={11}
                label={{ value: 'Complexity', angle: -90, position: 'insideLeft', style: { fill: '#71717a', fontSize: 11 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="avg_complexity" 
                stroke="rgb(96, 165, 250)"
                strokeWidth={2}
                fill="url(#complexityGradient)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div>
          <h4 className="text-sm font-medium text-zinc-300 mb-2">Function Count Growth</h4>
          <ResponsiveContainer width="100%" height={250} style={{ background: 'transparent' }}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" opacity={0.5} />
              <XAxis 
                dataKey="dateLabel" 
                stroke="#71717a"
                fontSize={11}
                interval="preserveStartEnd"
              />
              <YAxis 
                stroke="#71717a"
                fontSize={11}
                label={{ value: 'Functions', angle: -90, position: 'insideLeft', style: { fill: '#71717a', fontSize: 11 } }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="function_count" 
                stroke="rgb(96, 165, 250)"
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 5, fill: 'rgb(249, 115, 22)' }}
                name="Functions"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Code className="w-5 h-5 text-orange-400" />
            <p className="text-xs font-semibold text-zinc-300">Peak Complexity</p>
          </div>
          <p className="text-2xl font-bold text-orange-400">{maxComplexity.toFixed(2)}</p>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            <p className="text-xs font-semibold text-zinc-300">Max Functions</p>
          </div>
          <p className="text-2xl font-bold text-blue-400">{maxFunctions.toLocaleString()}</p>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <GitCommit className="w-5 h-5 text-teal-400" />
            <p className="text-xs font-semibold text-zinc-300">Total Commits</p>
          </div>
          <p className="text-2xl font-bold text-teal-400">{data.length}</p>
        </div>
      </div>
    </div>
  );
}
