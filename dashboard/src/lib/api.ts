import { Repository } from '@/types';

export interface HeatmapData {
  name: string;
  size: number;
  score: number;
}

export interface TimelineData {
  date: string;
  sha: string;
  message: string;
  function_count: number;
  avg_complexity: number;
  total_loc: number;
}

export interface ContributorData {
  author: string;
  total_commits: number;
  functions_added: number;
  total_complexity: number;
  avg_complexity: number;
  total_loc: number;
  entropy_score: number;
}

const getApiUrl = () => {
  if (typeof window === 'undefined') {
    return process.env.API_URL || 'http://api:8000';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

export const API_URL = getApiUrl();

export async function getRepositories(): Promise<Repository[]> {
  const response = await fetch(`${API_URL}/repositories/`, {
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch repositories');
  }
  
  return response.json();
}

export async function getRepository(id: string): Promise<Repository> {
  const response = await fetch(`${API_URL}/repositories/${id}`, {
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch repository');
  }
  
  return response.json();
}

export async function getRepositoryHeatmap(id: string): Promise<HeatmapData[]> {
  const response = await fetch(`${API_URL}/analytics/repositories/${id}/heatmap`, {
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch heatmap data');
  }
  
  return response.json();
}

export async function getRepositoryTimeline(id: string): Promise<TimelineData[]> {
  const response = await fetch(`${API_URL}/analytics/repositories/${id}/timeline`, {
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch timeline data');
  }
  
  return response.json();
}

export async function getRepositoryContributors(id: string): Promise<ContributorData[]> {
  const response = await fetch(`${API_URL}/analytics/repositories/${id}/contributors`, {
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch contributors data');
  }
  
  return response.json();
}
