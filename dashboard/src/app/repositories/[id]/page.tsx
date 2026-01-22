'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { GitBranch } from 'lucide-react';
import { getRepository, getRepositoryHeatmap, getRepositoryTimeline, getRepositoryContributors } from '@/lib/api';
import Heatmap from '@/components/Heatmap';
import Timeline from '@/components/Timeline';
import Contributors from '@/components/Contributors';
import StatusPoller from '@/components/StatusPoller';
import { Repository } from '@/types';
import type { HeatmapData, TimelineData, ContributorData } from '@/lib/api';
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
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  useEffect(() => {
    params.then(p => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (authLoading) return; // Wait for auth to load
    
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (!id) return;

    const fetchData = async () => {
      try {
        const [repo, heatmap, timeline, contributors] = await Promise.all([
          getRepository(id),
          getRepositoryHeatmap(id),
          getRepositoryTimeline(id),
          getRepositoryContributors(id),
        ]);
        
        setRepository(repo);
        setHeatmapData(heatmap);
        setTimelineData(timeline);
        setContributorsData(contributors);
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
      <div className="container mx-auto px-4 py-12">
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

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="bg-zinc-950/40 backdrop-blur-md border border-zinc-800/50 shadow-2xl rounded-lg p-6 hover:shadow-zinc-900/50 hover:border-zinc-700/80 transition-all duration-300">
              <Heatmap data={heatmapData} />
            </div>
          </div>

          <aside className="lg:col-span-1">
            <div className="bg-zinc-950/40 backdrop-blur-md border border-zinc-800/50 shadow-2xl rounded-lg p-6 hover:shadow-zinc-900/50 hover:border-zinc-700/80 transition-all duration-300">
              <div className="flex flex-col gap-4">
                <div>
                  <p className="text-sm text-zinc-300">Repository</p>
                  <p className="text-lg font-semibold text-zinc-100 mt-1">{repository.owner}/{repository.name}</p>
                </div>

                <div>
                  <p className="text-sm text-zinc-300">Created</p>
                  <p className="text-sm text-zinc-400 mt-1">{new Date(repository.created_at).toLocaleString()}</p>
                </div>

                <div>
                  <p className="text-sm text-zinc-300">Contributors</p>
                  <p className="text-sm text-zinc-400 mt-1">{contributorsData.length}</p>
                </div>

                <div>
                  <p className="text-sm text-zinc-300">Commits (visible)</p>
                  <p className="text-sm text-zinc-400 mt-1">{timelineData.length}</p>
                </div>

                <div>
                  <Link href="/dashboard" className="inline-block mt-2 text-sm text-zinc-300 hover:text-zinc-100">
                    View all repositories →
                  </Link>
                </div>
              </div>
            </div>
          </aside>

          <div className="lg:col-span-3">
            <div className="bg-zinc-950/40 backdrop-blur-md border border-zinc-800/50 shadow-2xl rounded-lg p-6 hover:shadow-zinc-900/50 hover:border-zinc-700/80 transition-all duration-300">
              <Timeline data={timelineData} />
            </div>
          </div>

          <div className="lg:col-span-3">
            <div className="bg-zinc-950/40 backdrop-blur-md border border-zinc-800/50 shadow-2xl rounded-lg p-6 hover:shadow-zinc-900/50 hover:border-zinc-700/80 transition-all duration-300">
              <Contributors data={contributorsData} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
