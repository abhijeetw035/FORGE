'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Plus, Zap, GitBranch, Sparkles, LogOut } from 'lucide-react';
import { Repository } from '@/types';
import AddRepositoryModal from '@/components/AddRepositoryModal';
import RepositoryCard from '@/components/RepositoryCard';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useAuth } from '@/context/AuthContext';

interface DashboardContentProps {
  initialRepositories: Repository[];
  onRepositoryAdded?: () => void | Promise<void>;
}

export default function DashboardContent({ initialRepositories, onRepositoryAdded }: DashboardContentProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const router = useRouter();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const handleRepositoryAdded = () => {
    setIsModalOpen(false);
    if (onRepositoryAdded) {
      onRepositoryAdded();
    }
  };

  return (
    <>
      <div className="min-h-screen">
        <div className="relative z-10 container mx-auto px-4 py-8 max-w-7xl">
          <header className="flex items-center justify-between mb-12 py-6 animate-in fade-in slide-in-from-top-4 duration-700">
            <Link href="/" className="flex items-center gap-4 group cursor-pointer">
              <div className="glass-card p-3">
                <Zap className="w-8 h-8 text-zinc-50 group-hover:text-primary transition-colors" />
              </div>
              <div>
                <h1 className="text-4xl font-bold text-zinc-50 tracking-tight group-hover:text-primary transition-colors">
                  FORGE
                </h1>
                <p className="text-sm text-zinc-400 mt-1">
                  Code Entropy Analysis Platform
                </p>
              </div>
            </Link>
            
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <button
                onClick={handleLogout}
                className="glass-card flex items-center gap-2 px-4 py-2 text-zinc-400 hover:text-zinc-50 hover:border-zinc-700 transition"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
              <button
                onClick={() => setIsModalOpen(true)}
                className="flex items-center gap-2 px-6 py-3 bg-zinc-100 hover:bg-zinc-300 text-black font-semibold rounded-md transition-all border border-zinc-200"
              >
                <Plus className="w-5 h-5" />
                Add Repository
              </button>
            </div>
          </header>

          {initialRepositories.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-32">
              <div className="relative mb-8">
                <div className="glass-card p-8">
                  <GitBranch className="w-20 h-20 text-zinc-400" />
                </div>
              </div>
              
              <h2 className="text-3xl font-bold text-zinc-50 mb-3">
                Ready to analyze your first codebase?
              </h2>
              <p className="text-zinc-400 mb-8 text-center max-w-md">
                Add a GitHub repository to start tracking code entropy, complexity metrics, and team contributions.
              </p>
              
              <button
                onClick={() => setIsModalOpen(true)}
                className="flex items-center gap-3 px-8 py-4 bg-zinc-100 hover:bg-zinc-300 text-black font-bold rounded-md transition-all border border-zinc-200 hover:shadow-lg"
              >
                <Sparkles className="w-5 h-5" />
                Add Your First Repository
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {initialRepositories.map((repo) => (
                <RepositoryCard key={repo.id} repository={repo} />
              ))}
            </div>
          )}
        </div>
      </div>

      <AddRepositoryModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleRepositoryAdded}
      />
    </>
  );
}
