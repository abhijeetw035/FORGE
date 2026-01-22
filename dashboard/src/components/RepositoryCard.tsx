'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Repository } from '@/types';
import { deleteRepository } from '@/lib/api';
import { GitBranch, Clock, GitCommit, Trash2, TrendingUp, Loader2 } from 'lucide-react';

interface RepositoryCardProps {
  repository: Repository;
}

export default function RepositoryCard({ repository }: RepositoryCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const router = useRouter();

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          color: 'bg-green-500',
          text: 'text-green-400',
          border: 'border-green-500/30',
          glow: 'shadow-green-500/20',
          label: 'Completed'
        };
      case 'analyzing':
        return {
          color: 'bg-yellow-500',
          text: 'text-yellow-400',
          border: 'border-yellow-500/30',
          glow: 'shadow-yellow-500/20',
          label: 'Analyzing'
        };
      case 'queued':
        return {
          color: 'bg-blue-500',
          text: 'text-blue-400',
          border: 'border-blue-500/30',
          glow: 'shadow-blue-500/20',
          label: 'Queued'
        };
      case 'failed':
        return {
          color: 'bg-red-500',
          text: 'text-red-400',
          border: 'border-red-500/30',
          glow: 'shadow-red-500/20',
          label: 'Failed'
        };
      default:
        return {
          color: 'bg-gray-500',
          text: 'text-gray-400',
          border: 'border-gray-500/30',
          glow: 'shadow-gray-500/20',
          label: 'Unknown'
        };
    }
  };

  const statusConfig = getStatusConfig(repository.status);

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!window.confirm(`Are you sure you want to delete "${repository.owner}/${repository.name}"?\n\nThis will permanently remove all analysis data.`)) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteRepository(repository.id);
      router.refresh();
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to delete repository');
      setIsDeleting(false);
    }
  };

  return (
    <div className="group relative bg-zinc-950/40 backdrop-blur-md border border-zinc-800/50 hover:border-zinc-700/80 rounded-md transition-all duration-300 shadow-2xl hover:shadow-zinc-900/50 overflow-hidden hover:-translate-y-1">
      
      <button
        onClick={handleDelete}
        disabled={isDeleting}
        className="absolute top-4 right-4 z-10 p-2 bg-zinc-950/80 backdrop-blur-sm border border-zinc-800 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-950/50 hover:border-red-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        title="Delete repository"
      >
        {isDeleting ? (
          <Loader2 className="w-4 h-4 text-red-400 animate-spin" />
        ) : (
          <Trash2 className="w-4 h-4 text-red-400" />
        )}
      </button>

      <div className="relative p-6">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-zinc-950 border border-zinc-800 rounded-md">
              <GitBranch className="w-5 h-5 text-zinc-50" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-xl font-bold text-zinc-50 truncate">
                {repository.name}
              </h3>
              <p className="text-sm text-zinc-400 truncate">
                {repository.owner}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className={`relative flex items-center gap-2 px-3 py-1.5 ${statusConfig.border} border rounded-md`}>
              <div className="relative">
                <div className={`w-2 h-2 ${statusConfig.color} rounded-full`} />
                {(repository.status === 'analyzing' || repository.status === 'queued') && (
                  <div className={`absolute inset-0 w-2 h-2 ${statusConfig.color} rounded-full animate-ping`} />
                )}
              </div>
              <span className={`text-xs font-semibold ${statusConfig.text}`}>
                {statusConfig.label}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6 pb-6 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-zinc-950 rounded-md">
              <GitCommit className="w-4 h-4 text-zinc-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500">Repository</p>
              <p className="text-sm font-semibold text-zinc-300">Tracked</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-zinc-950 rounded-md">
              <Clock className="w-4 h-4 text-zinc-400" />
            </div>
            <div>
              <p className="text-xs text-zinc-500">Added</p>
              <p className="text-sm font-semibold text-zinc-300">
                {new Date(repository.created_at).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric' 
                })}
              </p>
            </div>
          </div>
        </div>

        <Link
          href={`/repositories/${repository.id}`}
          className="block w-full"
        >
          <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-zinc-100 hover:bg-zinc-300 text-black font-semibold rounded-md transition-all">
            <TrendingUp className="w-4 h-4" />
            View Dashboard
          </button>
        </Link>
      </div>
    </div>
  );
}
