import Link from 'next/link';
import { BarChart3, TrendingUp, Users, Brain } from 'lucide-react';
import Navbar from '@/components/Navbar';
import BackgroundEffects from '@/components/BackgroundEffects';
import HeroButton from '@/components/HeroButton';

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Background Effects - Particles and Orbs */}
      <BackgroundEffects />

      {/* Scanner Beam Animation */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <div 
          className="h-[1px] w-full bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent"
          
        />
      </div>

      {/* Spotlight Effect */}
      <div 
        className="fixed inset-0 z-0 pointer-events-none"
        style={{
          background: 'radial-gradient(circle 800px at 50% 30%, rgba(34, 211, 238, 0.08), transparent)',
          animation: 'pulse-slow 4s ease-in-out infinite',
        }}
      />

      {/* Smart Navbar */}
      <Navbar />

      <main className="relative z-10 pt-32">
        <section className="container mx-auto px-4 py-20">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-6xl md:text-8xl font-bold tracking-tight text-black dark:text-white mb-8 leading-[1.1]">
              Analyze Code
              <br />
              Entropy.
            </h1>
            <p className="text-xl md:text-2xl text-zinc-400 mb-12 max-w-2xl mx-auto">
              Industrial-grade complexity analysis for engineering teams.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <HeroButton />
            </div>
          </div>
        </section>

        <section className="container mx-auto px-4 py-20">
          <div className="max-w-5xl mx-auto grid md:grid-cols-4 gap-6">
            <div className="p-6 border border-zinc-800 bg-zinc-950/40 backdrop-blur-md rounded-md hover:border-zinc-700 transition-all duration-300">
              <BarChart3 className="w-6 h-6 text-primary mb-4" />
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">
                Heatmaps
              </h3>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Visualize code churn with treemap heatmaps. Identify files with highest modification frequency.
              </p>
            </div>

            <div className="p-6 border border-zinc-800 bg-zinc-950/40 backdrop-blur-md rounded-md hover:border-zinc-700 transition-all duration-300">
              <TrendingUp className="w-6 h-6 text-primary mb-4" />
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">
                Temporal Evolution
              </h3>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Track complexity evolution. See when entropy spiked during refactors or feature additions.
              </p>
            </div>

            <div className="p-6 border border-zinc-800 bg-zinc-950/40 backdrop-blur-md rounded-md hover:border-zinc-700 transition-all duration-300">
              <Users className="w-6 h-6 text-primary mb-4" />
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">
                Team Metrics
              </h3>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Understand contributor impact with context-aware metrics. Identify opportunities for code reviews.
              </p>
            </div>

            <div className="p-6 border border-zinc-800 bg-zinc-950/40 backdrop-blur-md rounded-md hover:border-zinc-700 transition-all duration-300">
              <Brain className="w-6 h-6 text-primary mb-4" />
              <h3 className="text-lg font-semibold text-zinc-100 mb-2">
                AI Risk Prediction
              </h3>
              <p className="text-sm text-zinc-400 leading-relaxed">
                Machine learning forecasts which files will break. "The Oracle" predicts future maintenance issues.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-zinc-800 py-8 mt-20">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-zinc-400">
              © 2026 FORGE. Built with Next.js & FastAPI.
            </p>
            <div className="flex items-center gap-6">
              <Link
                href="/about"
                className="text-sm text-zinc-400 hover:text-zinc-100 transition"
              >
                About
              </Link>
              <a
                href="https://github.com/abhijeetw035/FORGE"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-zinc-400 hover:text-zinc-100 transition"
              >
                GitHub
              </a>
              <Link
                href="/dashboard"
                className="text-sm text-zinc-400 hover:text-zinc-100 transition"
              >
                Dashboard
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
