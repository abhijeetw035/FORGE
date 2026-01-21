import { Repository } from '@/types';

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
