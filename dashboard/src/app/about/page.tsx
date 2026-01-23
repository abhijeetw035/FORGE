import Link from 'next/link';
import { Brain, Zap, GitBranch, Code, Users, ArrowRight, Lightbulb } from 'lucide-react';
import Navbar from '@/components/Navbar';
import BackgroundEffects from '@/components/BackgroundEffects';

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      <BackgroundEffects />
      <Navbar />

      <main className="relative z-10 pt-32 pb-20">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="text-center mb-20">
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-zinc-100 mb-6">
              Understanding Code Entropy
            </h1>
            <p className="text-xl text-zinc-400 max-w-3xl mx-auto">
              Complexity, churn, and technical debt through the lens of information theory
            </p>
          </div>

          <div className="glass-card p-8 mb-12">
            <div className="flex items-start gap-4 mb-6">
              <Brain className="w-8 h-8 text-primary flex-shrink-0 mt-1" />
              <div>
                <h2 className="text-2xl font-bold text-zinc-100 mb-4">The Problem</h2>
                <p className="text-zinc-300 leading-relaxed mb-4">
                  As codebases grow, they accumulate <span className="text-primary font-semibold">complexity</span>. 
                  Files get modified repeatedly, functions become nested, and understanding "what changed and why" becomes harder. 
                  Traditional metrics like lines of code or commit count don't tell the full story.
                </p>
                <p className="text-zinc-300 leading-relaxed">
                  <span className="text-primary font-semibold">Code entropy</span> measures the "disorder" or "unpredictability" 
                  in your codebase. High entropy indicates areas where complexity is growing faster than clarity.
                </p>
              </div>
            </div>
          </div>

          <div className="mb-12">
            <h2 className="text-3xl font-bold text-zinc-100 mb-8 flex items-center gap-3">
              <Zap className="w-8 h-8 text-primary" />
              Key Concepts
            </h2>
            
            <div className="space-y-6">
              <div className="glass-card p-6">
                <div className="flex items-start gap-4">
                  <GitBranch className="w-6 h-6 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-semibold text-zinc-100 mb-2">Code Churn</h3>
                    <p className="text-zinc-300 mb-3">
                      How often a file changes. High churn = unstable design or evolving requirements.
                    </p>
                    <div className="text-sm text-zinc-400 space-y-1">
                      <p>• <strong className="text-white">Low Churn:</strong> Stable APIs, utilities, configuration files</p>
                      <p>• <strong className="text-white">Medium:</strong> Business logic, features under active development</p>
                      <p>• <strong className="text-white">High Churn:</strong> Hotspots, refactor candidates, experimental code</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <div className="flex items-start gap-4">
                  <Code className="w-6 h-6 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-semibold text-zinc-100 mb-2">Complexity Score</h3>
                    <p className="text-zinc-300 mb-3">
                      Cyclomatic complexity + function depth. High complexity = harder to test and maintain.
                    </p>
                    <div className="text-sm text-zinc-400 space-y-1">
                      <p>• <strong className="text-white">1-5:</strong> Simple, linear code paths</p>
                      <p>• <strong className="text-white">6-15:</strong> Moderate branching, typical business logic</p>
                      <p>• <strong className="text-white">16+:</strong> Complex, needs refactoring or better decomposition</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <div className="flex items-start gap-4">
                  <Zap className="w-6 h-6 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-semibold text-zinc-100 mb-2">Entropy Score</h3>
                    <p className="text-zinc-300 mb-3">
                      Churn × Complexity. Identifies files that are both complex AND frequently changed.
                    </p>
                    <div className="bg-zinc-950/50 border border-zinc-800 rounded p-3 text-sm mb-3">
                      <p className="text-primary font-mono">Formula: Entropy = Avg Complexity × Functions Added</p>
                    </div>
                    <p className="text-sm text-zinc-400">
                      High entropy files are prime candidates for bugs and maintenance issues. They're changing frequently 
                      (unstable) AND have high complexity (hard to understand).
                    </p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <div className="flex items-start gap-4">
                  <Users className="w-6 h-6 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-semibold text-zinc-100 mb-2">Team Impact</h3>
                    <p className="text-zinc-300 mb-3">
                      Which contributors are working on high-entropy code? No judgment—just context.
                    </p>
                    <div className="bg-yellow-500/10 border border-yellow-800 rounded p-3 text-sm">
                      <p className="text-zinc-300">
                        <strong className="text-yellow-400">⚠️ Important:</strong> High entropy ≠ bad developer. 
                        Often means tackling algorithms, parsers, or refactoring legacy systems. Use this to identify 
                        where support (pair programming, extra reviews) is needed.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <div className="flex items-start gap-4">
                  <Brain className="w-6 h-6 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-xl font-semibold text-zinc-100 mb-2">AI Risk Prediction</h3>
                    <p className="text-zinc-300 mb-3">
                      Machine learning predicts which files are likely to break using Isolation Forest algorithm.
                    </p>
                    <div className="text-sm text-zinc-400 space-y-1">
                      <p>• <strong className="text-white">The Oracle:</strong> Future risk detection before problems occur</p>
                      <p>• <strong className="text-white">Method:</strong> Unsupervised anomaly detection</p>
                      <p>• <strong className="text-white">Based on:</strong> Churn × complexity × authorship patterns</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mb-12">
            <h2 className="text-3xl font-bold text-zinc-100 mb-8 flex items-center gap-3">
              <Lightbulb className="w-8 h-8 text-primary" />
              Real-World Use Cases
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-zinc-100 mb-3">Code Reviews</h3>
                <p className="text-sm text-zinc-300">
                  Focus reviews on high-entropy files. Don't waste time on stable utilities—prioritize complex, 
                  changing code that's most likely to have issues.
                </p>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-zinc-100 mb-3">Refactor Planning</h3>
                <p className="text-sm text-zinc-300">
                  Identify which modules to refactor first. Data-driven decisions instead of guesswork. 
                  High-entropy files should be prioritized for splitting or simplification.
                </p>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-zinc-100 mb-3">Onboarding</h3>
                <p className="text-sm text-zinc-300">
                  Show new developers the "safe" vs "complex" areas. Help them contribute confidently 
                  by starting in low-entropy zones.
                </p>
              </div>

              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-zinc-100 mb-3">Sprint Planning</h3>
                <p className="text-sm text-zinc-300">
                  Budget time for technical debt reduction. Use entropy trends to justify refactoring 
                  work to stakeholders with hard data.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-blue-500/10 border border-blue-800 rounded-lg p-6 mb-12">
            <h3 className="text-xl font-semibold text-blue-300 mb-3">
              💡 The Philosophy
            </h3>
            <p className="text-zinc-300 leading-relaxed mb-3">
              High entropy isn't "bad"—it's informative. Someone working on a parser, a game engine, or legacy refactoring 
              will naturally have high entropy scores.
            </p>
            <p className="text-zinc-300 leading-relaxed">
              <strong className="text-white">FORGE helps you understand complexity, not judge performance.</strong> Use these 
              metrics to identify where your team needs support, documentation, and extra attention—not to rank developers.
            </p>
          </div>

          <div className="flex gap-4 justify-center">
            <Link
              href="/features"
              className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-900/50 border border-zinc-700 rounded-lg text-white hover:bg-zinc-900 hover:border-zinc-600 transition-all"
            >
              See Features & How to Use <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-hover text-white font-semibold rounded-lg transition-all"
            >
              Start Analyzing
            </Link>
          </div>
        </div>
      </main>

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
              <Link href="/features" className="text-sm text-zinc-400 hover:text-zinc-100 transition">
                Features
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
