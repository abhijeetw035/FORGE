'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Zap, LogOut } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-zinc-800 bg-black/80 backdrop-blur-md">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <Zap className="w-5 h-5 text-zinc-100 group-hover:text-cyan-400 transition-colors" />
            <span className="text-xl font-semibold tracking-tight text-zinc-100">
              FORGE
            </span>
          </Link>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            <Link
              href="/features"
              className="text-sm text-zinc-400 hover:text-zinc-100 transition"
            >
              Features
            </Link>
            <Link
              href="/about"
              className="text-sm text-zinc-400 hover:text-zinc-100 transition"
            >
              About
            </Link>
            <ThemeToggle />
            
            {!isAuthenticated ? (
              <>
                <Link
                  href="/login"
                  className="text-sm text-zinc-400 hover:text-zinc-100 transition"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="px-6 py-2 bg-zinc-100 hover:bg-zinc-300 text-black font-medium rounded-md transition"
                >
                  Get Started
                </Link>
              </>
            ) : (
              <>
                <span className="text-sm text-zinc-400">
                  {user?.email || 'User'}
                </span>
                <Link
                  href="/dashboard"
                  className="px-6 py-2 bg-zinc-100 hover:bg-zinc-300 text-black font-medium rounded-md transition"
                >
                  Dashboard
                </Link>
                <button
                  onClick={handleLogout}
                  className="p-2 text-zinc-400 hover:text-zinc-100 border border-zinc-800 hover:border-zinc-700 rounded-md transition"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
