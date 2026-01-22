'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createRepository } from '@/lib/api';
import { X, GitBranch, Loader2, AlertCircle } from 'lucide-react';

interface AddRepositoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void | Promise<void>;
}

export default function AddRepositoryModal({ isOpen, onClose, onSuccess }: AddRepositoryModalProps) {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await createRepository(url);
      setUrl('');
      onClose();
      
      // Call the success callback to refresh the parent
      if (onSuccess) {
        await onSuccess();
      }
      
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add repository');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md"
      onClick={handleOverlayClick}
    >
      <div className="relative w-full max-w-md mx-4 bg-zinc-950/40 backdrop-blur-md rounded-lg shadow-2xl border border-zinc-800/50 overflow-hidden">
        {/* Subtle glow effect */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-32 bg-cyan-500/5 blur-3xl" />
        
        {/* Header */}
        <div className="relative flex items-center justify-between p-6 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-zinc-900/60 border border-zinc-800 rounded-md">
              <GitBranch className="w-5 h-5 text-cyan-400" />
            </div>
            <h2 className="text-xl font-bold text-zinc-100">
              Add Repository
            </h2>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 rounded-md transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="relative p-6 space-y-4">
          <div>
            <label
              htmlFor="repo-url"
              className="block text-sm font-medium text-zinc-300 mb-2"
            >
              GitHub Repository URL
            </label>
            <input
              id="repo-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              required
              disabled={isLoading}
              className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-md text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <p className="mt-2 text-xs text-zinc-500">
              Enter the full GitHub URL of the repository you want to analyze
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-950/30 border border-red-800 rounded-md">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !url.trim()}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-black rounded-md font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-cyan-500/30"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <span>Analyze</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
