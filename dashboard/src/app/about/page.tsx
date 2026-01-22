import Link from 'next/link';
import { Brain, TrendingUp, Users, GitBranch, Zap, Target, Shield, Lightbulb } from 'lucide-react';
import Navbar from '@/components/Navbar';

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      <Navbar />

      <main className="relative z-10 pt-32 pb-20">
        <div className="container mx-auto px-4 max-w-5xl">
          {/* Hero Section */}
          <div className="text-center mb-20">
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-zinc-100 mb-6">
              What is Code Entropy?
            </h1>
            <p className="text-xl text-zinc-400 max-w-3xl mx-auto">
              Understanding complexity, churn, and technical debt through the lens of information theory
            </p>
          </div>

          {/* Introduction */}
          <div className="glass-card p-8 mb-12">
            <div className="flex items-start gap-4 mb-6">
              <Brain className="w-8 h-8 text-cyan-400 flex-shrink-0 mt-1" />
              <div>
                <h2 className="text-2xl font-bold text-zinc-100 mb-4">The Problem</h2>
                <p className="text-zinc-300 leading-relaxed mb-4">
                  As codebases grow, they accumulate <span className="text-cyan-400 font-semibold">complexity</span>. 
                  Files get modified repeatedly, functions become nested, and understanding "what changed and why" becomes harder. 
                  Traditional metrics like lines of code or commit count don't tell the full story.
                </p>
                <p className="text-zinc-300 leading-relaxed">
                  <span className="text-cyan-400 font-semibold">Code entropy</span> measures the "disorder" or "unpredictability" 
                  in your codebase. High entropy indicates areas where complexity is growing faster than clarity.
                </p>
              </div>
            </div>
          </div>

          {/* What is Entropy */}
          <div className="mb-12">
            <h2 className="text-3xl font-bold text-zinc-100 mb-8 flex items-center gap-3">
              <Zap className="w-8 h-8 text-cyan-400" />
              Entropy Explained
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div className="glass-card p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                  <GitBranch className="w-5 h-5 text-emerald-400" />
                  Code Churn
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed mb-3">
                  How often a file changes. High churn = unstable design or evolving requirements.
                </p>
                <div className="bg-zinc-900/50 border border-zinc-800 rounded p-3 text-xs font-mono text-zinc-300">
                  <span className="text-emerald-400">Low Churn:</span> Stable APIs, utilities<br/>
                  <span className="text-amber-400">Medium:</span> Business logic, features<br/>
                  <span className="text-rose-400">High Churn:</span> Hotspots, refactor candidates
                </div>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                  <Brain className="w-5 h-5 text-violet-400" />
                  Complexity Score
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed mb-3">
                  Cyclomatic complexity + function depth. High complexity = harder to test and maintain.
                </p>
                <div className="bg-zinc-900/50 border border-zinc-800 rounded p-3 text-xs font-mono text-zinc-300">
                  <span className="text-emerald-400">1-5:</span> Simple, linear code<br/>
                  <span className="text-amber-400">6-15:</span> Moderate branching<br/>
                  <span className="text-rose-400">16+:</span> Complex, needs refactoring
                </div>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-cyan-400" />
                  Entropy Score
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed mb-3">
                  Churn × Complexity. Identifies files that are both complex AND frequently changed.
                </p>
                <div className="bg-zinc-900/50 border border-zinc-800 rounded p-3 text-xs font-mono text-zinc-300">
                  Formula: <span className="text-cyan-400">Entropy = Avg Complexity × Functions Added</span>
                </div>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-3 flex items-center gap-2">
                  <Users className="w-5 h-5 text-amber-400" />
                  Team Impact
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed mb-3">
                  Which contributors are working on high-entropy code? No judgment—just context.
                </p>
                <div className="bg-zinc-900/50 border border-zinc-800 rounded p-3 text-xs font-mono text-zinc-300">
                  High entropy ≠ bad developer<br/>
                  Often = tackling hard problems
                </div>
              </div>
            </div>
          </div>

          {/* How FORGE Solves This */}
          <div className="mb-12">
            <h2 className="text-3xl font-bold text-zinc-100 mb-8 flex items-center gap-3">
              <Target className="w-8 h-8 text-cyan-400" />
              How FORGE Helps
            </h2>

            <div className="space-y-6">
              <div className="bg-gradient-to-r from-cyan-950/20 to-zinc-950/40 backdrop-blur-md border border-cyan-800/30 border-l-4 border-l-cyan-500 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-2">🎯 Visual Heatmaps</h3>
                <p className="text-zinc-400">
                  See your entire codebase at a glance. Box size = file size, color = churn intensity. 
                  Instantly identify hotspots that need attention.
                </p>
              </div>

              <div className="bg-gradient-to-r from-violet-950/20 to-zinc-950/40 backdrop-blur-md border border-violet-800/30 border-l-4 border-l-violet-500 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-2">📈 Timeline Analysis</h3>
                <p className="text-zinc-400">
                  Track complexity over time. See when entropy spiked—was it during a major refactor? 
                  A new feature? Use this to understand your team's coding patterns.
                </p>
              </div>

              <div className="bg-gradient-to-r from-amber-950/20 to-zinc-950/40 backdrop-blur-md border border-amber-800/30 border-l-4 border-l-amber-500 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-2">👥 Contributor Metrics</h3>
                <p className="text-zinc-400">
                  Understand who's working on complex code. Not for performance reviews—for <strong>context</strong>. 
                  High-entropy contributors often need extra code review support or pair programming.
                </p>
              </div>

              <div className="bg-gradient-to-r from-rose-950/20 to-zinc-950/40 backdrop-blur-md border border-rose-800/30 border-l-4 border-l-rose-500 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-zinc-100 mb-2">⚠️ Early Warning System</h3>
                <p className="text-zinc-400">
                  Get alerts when entropy spikes. Catch technical debt before it compounds. 
                  Plan refactors based on data, not gut feeling.
                </p>
              </div>
            </div>
          </div>

          {/* Use Cases */}
          <div className="mb-12">
            <h2 className="text-3xl font-bold text-zinc-100 mb-8 flex items-center gap-3">
              <Lightbulb className="w-8 h-8 text-cyan-400" />
              Real-World Use Cases
            </h2>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="glass-card p-6 hover:border-cyan-700 transition-colors">
                <Shield className="w-8 h-8 text-cyan-400 mb-4" />
                <h3 className="text-lg font-semibold text-zinc-100 mb-2">Code Reviews</h3>
                <p className="text-sm text-zinc-400">
                  Focus reviews on high-entropy files. Don't waste time on stable utilities—prioritize complex, changing code.
                </p>
              </div>

              <div className="glass-card p-6 hover:border-violet-700 transition-colors">
                <TrendingUp className="w-8 h-8 text-violet-400 mb-4" />
                <h3 className="text-lg font-semibold text-zinc-100 mb-2">Refactor Planning</h3>
                <p className="text-sm text-zinc-400">
                  Identify which modules to refactor first. Data-driven decisions instead of guesswork.
                </p>
              </div>

              <div className="glass-card p-6 hover:border-amber-700 transition-colors">
                <Users className="w-8 h-8 text-amber-400 mb-4" />
                <h3 className="text-lg font-semibold text-zinc-100 mb-2">Onboarding</h3>
                <p className="text-sm text-zinc-400">
                  Show new developers the "safe" vs "complex" areas. Help them contribute confidently.
                </p>
              </div>
            </div>
          </div>

          {/* Important Note */}
          <div className="bg-blue-950/30 border border-blue-800 rounded-lg p-6 mb-12">
            <h3 className="text-xl font-semibold text-blue-300 mb-3 flex items-center gap-2">
              ℹ️ Important Context
            </h3>
            <p className="text-zinc-300 leading-relaxed mb-3">
              <strong>High entropy isn't "bad"</strong>—it's <em>informative</em>. Someone working on a parser, 
              a game engine, or legacy refactoring will naturally have high entropy scores.
            </p>
            <p className="text-zinc-300 leading-relaxed">
              FORGE helps you <strong>understand complexity</strong>, not judge performance. Use these metrics to 
              identify where your team needs support, not to rank developers.
            </p>
          </div>

          {/* CTA */}
          <div className="text-center">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-8 py-4 bg-cyan-500 hover:bg-cyan-400 text-black font-bold rounded-md transition-all shadow-lg hover:shadow-cyan-500/50"
            >
              <Zap className="w-5 h-5" />
              Start Analyzing Your Code
            </Link>
            <p className="text-sm text-zinc-500 mt-4">
              Free for open-source projects · No credit card required
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-zinc-800 py-8 mt-20">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-zinc-400">
              © 2026 FORGE. Built with Next.js & FastAPI.
            </p>
            <div className="flex items-center gap-6">
              <Link href="/" className="text-sm text-zinc-400 hover:text-zinc-100 transition">
                Home
              </Link>
              <Link href="/about" className="text-sm text-zinc-400 hover:text-zinc-100 transition">
                About
              </Link>
              <Link href="/dashboard" className="text-sm text-zinc-400 hover:text-zinc-100 transition">
                Dashboard
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
