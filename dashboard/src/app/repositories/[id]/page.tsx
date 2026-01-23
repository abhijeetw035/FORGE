'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { GitBranch } from 'lucide-react';
import { getRepository, getRepositoryHeatmap, getRepositoryTimeline, getRepositoryContributors, getRepositoryRiskPrediction } from '@/lib/api';
import Heatmap from '@/components/Heatmap';
import Timeline from '@/components/Timeline';
import Contributors from '@/components/Contributors';
import RiskPrediction from '@/components/RiskPrediction';
import StatusPoller from '@/components/StatusPoller';
import { Repository } from '@/types';
import type { HeatmapData, TimelineData, ContributorData, RiskPredictionData } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function RepositoryPage({ params }: PageProps) {
  const [id, setId] = useState<string>('');
  const [repository, setRepository] = useState<Repository | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapData[]>([]);
  const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
  const [contributorsData, setContributorsData] = useState<ContributorData[]>([]);
  const [riskData, setRiskData] = useState<RiskPredictionData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  useEffect(() => {
    params.then(p => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (!id) return;

    const fetchData = async () => {
      try {
        const [repo, heatmap, timeline, contributors, risks] = await Promise.all([
          getRepository(id),
          getRepositoryHeatmap(id),
          getRepositoryTimeline(id),
          getRepositoryContributors(id),
          getRepositoryRiskPrediction(id),
        ]);
        
        setRepository(repo);
        setHeatmapData(heatmap);
        setTimelineData(timeline);
        setContributorsData(contributors);
        setRiskData(risks);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load repository');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [id, router, isAuthenticated, authLoading]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-zinc-100 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-400">Loading repository...</p>
        </div>
      </div>
    );
  }

  if (error || !repository) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'Repository not found'}</p>
          <Link
            href="/dashboard"
            className="px-6 py-2 bg-zinc-100 text-black rounded-md hover:bg-zinc-300 transition"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-950/50 text-green-400 border border-green-800';
      case 'analyzing':
        return 'bg-yellow-950/50 text-yellow-400 border border-yellow-800';
      case 'queued':
        return 'bg-blue-950/50 text-blue-400 border border-blue-800';
      case 'failed':
        return 'bg-red-950/50 text-red-400 border border-red-800';
      default:
        return 'bg-zinc-900/50 text-zinc-400 border border-zinc-800';
    }
  };

  return (
    <div className="min-h-screen">
      <StatusPoller repositories={[repository]} />
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        <header className="mb-8 pb-6 border-b border-zinc-800 animate-in fade-in slide-in-from-top-4 duration-700">
          <nav className="text-sm text-zinc-400 mb-4">
            <Link href="/dashboard" className="text-zinc-400 hover:text-zinc-100">
              Dashboard
            </Link>
            <span className="mx-2 text-zinc-600">/</span>
            <span className="text-zinc-400">{repository.owner}</span>
            <span className="mx-2 text-zinc-600">/</span>
            <span className="text-zinc-100 font-medium">{repository.name}</span>
          </nav>

          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <GitBranch className="w-8 h-8 text-zinc-100" />
              <div>
                <h1 className="text-3xl font-bold text-zinc-100">
                  {repository.owner}/{repository.name}
                </h1>
                <p className="text-zinc-500 mt-1">{repository.url}</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <span className={`px-3 py-1 rounded-md text-sm font-medium ${getStatusColor(
                repository.status
              )}`}>
                {repository.status.toUpperCase()}
              </span>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-4">
            <div className="glass-card p-6">
              <RiskPrediction data={riskData} />
            </div>
          </div>

          <div className="col-span-12 md:col-span-8">
            <div className="glass-card p-6">
              <Heatmap data={heatmapData} />
            </div>
          </div>

          <div className="col-span-12">
            <div className="glass-card p-6">
              <Timeline data={timelineData} />
            </div>
          </div>

          <div className="col-span-12">
            <div className="glass-card p-6">
              <Contributors data={contributorsData} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
