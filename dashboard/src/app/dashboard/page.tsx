'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getRepositories } from '@/lib/api';
import DashboardContent from '@/components/DashboardContent';
import StatusPoller from '@/components/StatusPoller';
import { Repository } from '@/types';
import { useAuth } from '@/context/AuthContext';

export default function DashboardPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [error, setError] = useState<string>('');
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  const fetchRepositories = async () => {
    try {
      const repos = await getRepositories();
      setRepositories(repos);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load repositories');
    }
  };

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }

    if (isAuthenticated) {
      fetchRepositories();
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-zinc-900 dark:border-zinc-50 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-600 dark:text-zinc-400">Loading your repositories...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <button
            onClick={() => router.push('/login')}
            className="px-6 py-2 bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 rounded-md border border-zinc-800 dark:border-zinc-200"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <StatusPoller repositories={repositories} />
      <DashboardContent 
        initialRepositories={repositories} 
        onRepositoryAdded={fetchRepositories}
      />
    </>
  );
}
