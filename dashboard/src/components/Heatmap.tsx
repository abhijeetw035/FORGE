'use client';

import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { HeatmapData } from '@/lib/api';

interface HeatmapProps {
  data: HeatmapData[];
}

const getColorByScore = (score: number, maxScore: number) => {
  const ratio = score / maxScore;
  
  if (ratio > 0.8) return '#dc2626';
  if (ratio > 0.6) return '#ea580c';
  if (ratio > 0.4) return '#f59e0b';
  if (ratio > 0.2) return '#fbbf24';
  return '#84cc16';
};

interface CustomContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  size?: number;
  score?: number;
  maxScore?: number;
}

const CustomContent = (props: CustomContentProps) => {
  const { x = 0, y = 0, width = 0, height = 0, name = '', score = 0, maxScore = 1 } = props;
  
  if (width < 10 || height < 10) return null;
  
  const color = getColorByScore(score, maxScore);
  const showText = width > 80 && height > 40;
  
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={color}
        stroke="#fff"
        strokeWidth={2}
        rx={4}
      />
      {showText && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 8}
            textAnchor="middle"
            fill="#fff"
            fontSize={12}
            fontWeight="bold"
          >
            {name.split('/').pop()}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="#fff"
            fontSize={10}
          >
            Churn: {score.toLocaleString()}
          </text>
        </>
      )}
    </g>
  );
};

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-gray-900 text-white p-4 rounded-lg shadow-xl border border-gray-700">
        <p className="font-semibold mb-2 text-sm">{data.name}</p>
        <p className="text-xs text-gray-300">Size: {data.size.toLocaleString()} LOC</p>
        <p className="text-xs text-gray-300">Churn: {data.score.toLocaleString()} modifications</p>
      </div>
    );
  }
  return null;
};

export default function Heatmap({ data }: HeatmapProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-gray-500">
        No heatmap data available
      </div>
    );
  }

  const maxScore = Math.max(...data.map(d => d.score));
  
  const treeData = data.map(item => ({
    ...item,
    maxScore,
  }));

  return (
    <div className="w-full h-[600px] bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Code Churn Heatmap
          </h3>
          <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
            <span>Low Risk</span>
            <div className="flex gap-1">
              <div className="w-6 h-4 bg-[#84cc16] rounded"></div>
              <div className="w-6 h-4 bg-[#fbbf24] rounded"></div>
              <div className="w-6 h-4 bg-[#f59e0b] rounded"></div>
              <div className="w-6 h-4 bg-[#ea580c] rounded"></div>
              <div className="w-6 h-4 bg-[#dc2626] rounded"></div>
            </div>
            <span>High Risk</span>
          </div>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Box size = Lines of Code | Color = Modification frequency
        </p>
      </div>
      
      <ResponsiveContainer width="100%" height="90%">
        <Treemap
          data={treeData}
          dataKey="size"
          stroke="#fff"
          fill="#8884d8"
          content={<CustomContent />}
        >
          <Tooltip content={<CustomTooltip />} />
        </Treemap>
      </ResponsiveContainer>
    </div>
  );
}
