import Link from 'next/link';
import { ArrowLeft, GitBranch, Activity } from 'lucide-react';
import { getRepository } from '@/lib/api';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function RepositoryPage({ params }: PageProps) {
  const { id } = await params;
  const repository = await getRepository(id);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'analyzing':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'queued':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-black">
      <div className="container mx-auto px-4 py-12">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-8 mb-8">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-3">
              <GitBranch className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  {repository.owner}/{repository.name}
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  {repository.url}
                </p>
              </div>
            </div>
            <span
              className={`px-4 py-2 rounded-full text-sm font-medium ${getStatusColor(
                repository.status
              )}`}
            >
              {repository.status.toUpperCase()}
            </span>
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
              <Activity className="w-5 h-5" />
              <span>Created: {new Date(repository.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-12">
          <div className="text-center">
            <Activity className="w-16 h-16 mx-auto mb-4 text-blue-600 dark:text-blue-400 animate-pulse" />
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
              Entropy Heatmap Coming Soon...
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Visualizing {repository.owner}/{repository.name} analysis data
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
