'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getRepository, getRepositoryRiskPrediction } from '@/lib/api';
import RiskPrediction from '@/components/RiskPrediction';
import type { RiskPredictionData } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function RiskPage({ params }: PageProps) {
  const [id, setId] = useState<string>('');
  const [riskData, setRiskData] = useState<RiskPredictionData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  useEffect(() => {
    params.then(p => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    if (!id) return;

    const fetchData = async () => {
      try {
        const [repo, risks] = await Promise.all([
          getRepository(id),
          getRepositoryRiskPrediction(id),
        ]);
        
        setRiskData(risks);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [id, router, isAuthenticated, authLoading]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-zinc-100 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-400">Loading risk predictions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-200px)]">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Risk Forecast</h1>
        <p className="text-zinc-400">AI-powered predictions for files at risk of bugs or maintenance issues</p>
      </div>

      <div className="glass-card p-6">
        <RiskPrediction data={riskData} />
      </div>
    </div>
  );
}
