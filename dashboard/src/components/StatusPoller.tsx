'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Repository } from '@/types';

interface StatusPollerProps {
  repositories: Repository[];
}

export default function StatusPoller({ repositories }: StatusPollerProps) {
  const router = useRouter();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Check if any repository is being analyzed or queued
    const hasActiveAnalysis = repositories.some(
      (repo) => repo.status === 'analyzing' || repo.status === 'queued'
    );

    if (hasActiveAnalysis) {
      // Start polling every 3 seconds
      console.log('🔄 Analysis in progress - Starting auto-refresh polling');
      
      intervalRef.current = setInterval(() => {
        console.log('🔄 Polling for updates...');
        router.refresh();
      }, 3000);
    } else {
      // Stop polling if all are completed or failed
      if (intervalRef.current) {
        console.log('✅ All analyses complete - Stopping polling');
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [repositories, router]);

  return null; // This component doesn't render anything
}
