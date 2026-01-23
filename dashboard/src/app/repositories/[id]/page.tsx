'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { GitBranch, GitCommit, Activity, AlertTriangle } from 'lucide-react';
import { getRepository, getRepositoryTimeline, getRepositoryRiskPrediction } from '@/lib/api';
import StatusPoller from '@/components/StatusPoller';
import { Repository } from '@/types';
import type { TimelineData, RiskPredictionData } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function RepositoryPage({ params }: PageProps) {
  const [id, setId] = useState<string>('');
  const [repository, setRepository] = useState<Repository | null>(null);
  const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
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
        const [repo, timeline, risks] = await Promise.all([
          getRepository(id),
          getRepositoryTimeline(id),
          getRepositoryRiskPrediction(id),
        ]);
        
        setRepository(repo);
        setTimelineData(timeline);
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
    <>
      <StatusPoller repositories={[repository]} />
      
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
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

        <div className="mb-6">
          <h2 className="text-2xl font-bold text-white mb-2">Overview</h2>
          <p className="text-zinc-400">High-level summary of repository metrics and health</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-blue-500/10 rounded-lg">
                <GitCommit className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-zinc-400">Total Commits</p>
                <p className="text-2xl font-bold text-white">
                  {timelineData.length.toLocaleString()}
                </p>
              </div>
            </div>
            <p className="text-xs text-zinc-500">Tracked across entire repository history</p>
          </div>

          <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-orange-500/10 rounded-lg">
                <Activity className="w-6 h-6 text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-zinc-400">Complexity Score</p>
                <p className="text-2xl font-bold text-white">
                  {timelineData.length > 0 
                    ? Math.round(timelineData[timelineData.length - 1].avg_complexity)
                    : 0}
                </p>
              </div>
            </div>
            <p className="text-xs text-zinc-500">Average cyclomatic complexity</p>
          </div>

          <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-red-500/10 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <div>
                <p className="text-sm text-zinc-400">Risk Level</p>
                <p className="text-2xl font-bold text-white">
                  {riskData.filter(d => d.risk_level === 'critical').length}
                </p>
              </div>
            </div>
            <p className="text-xs text-zinc-500">Critical files requiring attention</p>
          </div>
        </div>

        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link 
              href={`/repositories/${id}/heatmap`}
              className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg hover:border-blue-500 transition-all group"
            >
              <Activity className="w-5 h-5 text-blue-400 mb-2" />
              <h4 className="font-semibold text-white mb-1">Explore Entropy Map</h4>
              <p className="text-sm text-zinc-400">Visualize code complexity hotspots</p>
            </Link>

            <Link 
              href={`/repositories/${id}/risk`}
              className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg hover:border-blue-500 transition-all group"
            >
              <AlertTriangle className="w-5 h-5 text-red-400 mb-2" />
              <h4 className="font-semibold text-white mb-1">View Risk Forecast</h4>
              <p className="text-sm text-zinc-400">AI-powered predictions for at-risk files</p>
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
