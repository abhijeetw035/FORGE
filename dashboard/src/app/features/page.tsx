'use client';

import Link from 'next/link';
import { Activity, TrendingUp, Users, BrainCircuit, AlertTriangle, BarChart3, ArrowRight } from 'lucide-react';
import Navbar from '@/components/Navbar';
import BackgroundEffects from '@/components/BackgroundEffects';

export default function FeaturesPage() {
  return (
    <div className="min-h-screen">
      <BackgroundEffects />
      <Navbar />

      <main className="relative z-10 pt-32 pb-20">
        <div className="container mx-auto px-4 max-w-6xl">
          <header className="text-center mb-16">
            <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
              Features & How to Use
            </h1>
            <p className="text-xl text-zinc-400 max-w-3xl mx-auto">
              Comprehensive guide to FORGE's analysis tools and how to interpret the data
            </p>
          </header>

          <div className="space-y-16">
            <section className="glass-card p-8">
              <div className="flex items-start gap-4 mb-6">
                <div className="p-3 bg-blue-500/10 rounded-lg">
                  <Activity className="w-8 h-8 text-blue-400" />
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-white mb-2">Entropy Heatmap</h2>
                  <p className="text-zinc-400">Visual representation of code churn across your entire codebase</p>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">📊 How to Read It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm">
                    <p className="text-zinc-300"><strong className="text-white">Box Size:</strong> Represents lines of code (LOC). Larger boxes = larger files.</p>
                    <p className="text-zinc-300"><strong className="text-white">Color Intensity:</strong> Shows modification frequency (churn).</p>
                    <div className="ml-4 space-y-1 text-zinc-400">
                      <p>• <span className="text-slate-400">Dark Slate</span> = Low risk, stable files</p>
                      <p>• <span className="text-blue-400">Deep Blue</span> = Medium risk, moderate changes</p>
                      <p>• <span className="text-red-400">Deep Red</span> = High risk, frequent modifications</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">🎯 How to Use It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm text-zinc-300">
                    <p>• <strong className="text-white">Identify Hotspots:</strong> Large red boxes are high-churn, high-impact files</p>
                    <p>• <strong className="text-white">Prioritize Reviews:</strong> Focus code reviews on red/blue areas</p>
                    <p>• <strong className="text-white">Refactor Planning:</strong> Large red boxes are prime candidates for splitting</p>
                    <p>• <strong className="text-white">Stability Check:</strong> Gray/slate areas are your stable foundation</p>
                  </div>
                </div>

                <div className="pt-4">
                  <Link 
                    href="/repositories"
                    className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View in your repositories <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            </section>

            <section className="glass-card p-8">
              <div className="flex items-start gap-4 mb-6">
                <div className="p-3 bg-orange-500/10 rounded-lg">
                  <TrendingUp className="w-8 h-8 text-orange-400" />
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-white mb-2">Evolution Timeline</h2>
                  <p className="text-zinc-400">Track how complexity and function count evolve over time</p>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">📊 How to Read It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm">
                    <p className="text-zinc-300"><strong className="text-white">Blue Line:</strong> Average cyclomatic complexity across all functions</p>
                    <p className="text-zinc-300"><strong className="text-white">Orange Dots:</strong> Commits with significant complexity changes</p>
                    <p className="text-zinc-300"><strong className="text-white">Timeline:</strong> Each point = a commit with function/complexity metrics</p>
                    <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                      <div className="bg-orange-500/10 border border-orange-800 rounded p-2">
                        <p className="text-orange-400 font-semibold mb-1">Peak Complexity</p>
                        <p className="text-zinc-400">Highest complexity reached</p>
                      </div>
                      <div className="bg-blue-500/10 border border-blue-800 rounded p-2">
                        <p className="text-blue-400 font-semibold mb-1">Max Functions</p>
                        <p className="text-zinc-400">Most functions in a commit</p>
                      </div>
                      <div className="bg-teal-500/10 border border-teal-800 rounded p-2">
                        <p className="text-teal-400 font-semibold mb-1">Total Commits</p>
                        <p className="text-zinc-400">Repository history depth</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">🎯 How to Use It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm text-zinc-300">
                    <p>• <strong className="text-white">Spot Spikes:</strong> Sudden increases indicate refactors or complex features</p>
                    <p>• <strong className="text-white">Trend Analysis:</strong> Is complexity growing or shrinking over time?</p>
                    <p>• <strong className="text-white">Correlate Events:</strong> Match spikes to feature releases or team changes</p>
                    <p>• <strong className="text-white">Set Baselines:</strong> Understand what "normal" complexity looks like</p>
                  </div>
                </div>
              </div>
            </section>

            <section className="glass-card p-8">
              <div className="flex items-start gap-4 mb-6">
                <div className="p-3 bg-purple-500/10 rounded-lg">
                  <Users className="w-8 h-8 text-purple-400" />
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-white mb-2">Team Stats</h2>
                  <p className="text-zinc-400">Contributor metrics and entropy analysis by author</p>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">📊 How to Read It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm">
                    <p className="text-zinc-300"><strong className="text-white">Entropy Score:</strong> Avg Complexity × Functions Added</p>
                    <p className="text-zinc-300"><strong className="text-white">Commits:</strong> Total number of commits by contributor</p>
                    <p className="text-zinc-300"><strong className="text-white">Functions Added:</strong> New functions introduced</p>
                    <p className="text-zinc-300"><strong className="text-white">Avg Complexity:</strong> Average cyclomatic complexity of their code</p>
                    <p className="text-zinc-300"><strong className="text-white">Impact %:</strong> Percentage of total functions contributed</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">🎯 How to Use It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm text-zinc-300">
                    <p>• <strong className="text-white">Context, Not Judgment:</strong> High entropy ≠ bad developer</p>
                    <p>• <strong className="text-white">Pair Programming:</strong> High-entropy contributors benefit from pairing</p>
                    <p>• <strong className="text-white">Code Review Focus:</strong> Prioritize reviews for high-entropy changes</p>
                    <p>• <strong className="text-white">Workload Balance:</strong> Ensure complex work is distributed</p>
                    <p>• <strong className="text-white">Onboarding:</strong> New devs should start in low-entropy areas</p>
                  </div>
                </div>

                <div className="bg-yellow-500/10 border border-yellow-800 rounded-lg p-4">
                  <p className="text-sm text-zinc-300">
                    <strong className="text-yellow-400">⚠️ Important:</strong> High entropy often means working on algorithms, parsers, or refactoring legacy systems. 
                    Use this data to identify where support is needed, not to rank performance.
                  </p>
                </div>
              </div>
            </section>

            <section className="glass-card p-8">
              <div className="flex items-start gap-4 mb-6">
                <div className="p-3 bg-red-500/10 rounded-lg">
                  <BrainCircuit className="w-8 h-8 text-red-400" />
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-white mb-2">Risk Forecast (The Oracle)</h2>
                  <p className="text-zinc-400">AI-powered predictions for files at risk of bugs or maintenance issues</p>
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">📊 How to Read It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm">
                    <p className="text-zinc-300"><strong className="text-white">Risk Score (%):</strong> Likelihood of future maintenance issues</p>
                    <p className="text-zinc-300"><strong className="text-white">Risk Levels:</strong></p>
                    <div className="ml-4 space-y-1 text-zinc-400">
                      <p>• <span className="text-red-400">Critical (80-100%)</span> = Immediate attention required</p>
                      <p>• <span className="text-orange-400">Warning (50-79%)</span> = Monitor closely, plan refactor</p>
                      <p>• <span className="text-zinc-400">Watchlist (&lt;50%)</span> = Keep an eye on these</p>
                    </div>
                    <p className="text-zinc-300 mt-3"><strong className="text-white">Progress Bar:</strong> Visual indicator of risk level (red/orange/gray)</p>
                    <p className="text-zinc-300"><strong className="text-white">Metrics:</strong> Churn, Complexity, and Author Count drive the prediction</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">🎯 How to Use It</h3>
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4 space-y-2 text-sm text-zinc-300">
                    <p>• <strong className="text-white">Proactive Refactoring:</strong> Address critical files before they break</p>
                    <p>• <strong className="text-white">Test Coverage:</strong> Prioritize tests for high-risk files</p>
                    <p>• <strong className="text-white">Sprint Planning:</strong> Budget time to reduce technical debt</p>
                    <p>• <strong className="text-white">Architecture Review:</strong> High risk might indicate design issues</p>
                    <p>• <strong className="text-white">Documentation:</strong> High-risk files need better docs</p>
                  </div>
                </div>

                <div className="bg-blue-500/10 border border-blue-800 rounded-lg p-4">
                  <p className="text-sm text-zinc-300">
                    <strong className="text-blue-400">🔮 The Algorithm:</strong> Uses Isolation Forest (unsupervised ML) to detect statistical anomalies 
                    in complexity, churn, and authorship patterns. Files that deviate significantly from the norm are flagged as high-risk.
                  </p>
                </div>
              </div>
            </section>
          </div>

          <div className="mt-16 text-center">
            <Link 
              href="/about"
              className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-900/50 border border-zinc-700 rounded-lg text-white hover:bg-zinc-900 hover:border-zinc-600 transition-all"
            >
              Learn more about Code Entropy Concepts <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </main>

      <footer className="relative z-10 border-t border-zinc-800 py-8">
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
