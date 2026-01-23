'use client';

import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { HeatmapData } from '@/lib/api';

interface HeatmapProps {
  data: HeatmapData[];
}

const getColorByScore = (score: number, maxScore: number) => {
  const ratio = score / maxScore;

  if (ratio > 0.7) {
    return { fill: '#b91c1c', stroke: '#ef4444' };
  }
  if (ratio > 0.4) {
    return { fill: '#0f4c75', stroke: '#3282b8' };
  }
  
  return { fill: '#1e293b', stroke: '#334155' };
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
        fill={color.fill}
        stroke={color.stroke}
        strokeWidth={1}
        rx={4}
      />
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="none"
        stroke="#0b1220"
        strokeWidth={1}
        rx={4}
      />
      {showText && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - 8}
            textAnchor="middle"
            fill="#ffffff"
            fontSize={12}
            fontWeight="bold"
          >
            {name.split('/').pop()}
          </text>
          <text
            x={x + width / 2}
            y={y + height / 2 + 10}
            textAnchor="middle"
            fill="#ffffff"
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
      <div className="bg-zinc-950 border border-zinc-800 text-zinc-200 p-4 rounded-md shadow-xl">
        <p className="font-semibold mb-2 text-sm">{data.name}</p>
        <p className="text-xs">Size: {data.size.toLocaleString()} LOC</p>
        <p className="text-xs">Churn: {data.score.toLocaleString()} modifications</p>
      </div>
    );
  }
  return null;
};

export default function Heatmap({ data }: HeatmapProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-20 text-zinc-500">
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
    <div className="w-full min-h-[600px]">
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-zinc-100">
            Code Churn Heatmap
          </h3>
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <span>Low Risk</span>
            <div className="flex gap-1">
              <div className="w-6 h-4 rounded" style={{ background: '#1e293b', border: '1px solid #334155' }}></div>
              <div className="w-6 h-4 rounded" style={{ background: '#0f4c75', border: '1px solid #3282b8' }}></div>
              <div className="w-6 h-4 rounded" style={{ background: '#b91c1c', border: '1px solid #ef4444' }}></div>
            </div>
            <span>High Risk</span>
          </div>
        </div>
        <p className="text-sm text-zinc-500">
          Box size = Lines of Code | Color = Modification frequency
        </p>
      </div>
      
      <ResponsiveContainer width="100%" height={600}>
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
