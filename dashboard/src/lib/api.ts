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

export interface RiskPredictionData {
  file_path: string;
  churn: number;
  complexity: number;
  author_count: number;
  risk_score: number;
  risk_level: 'critical' | 'warning' | 'watchlist';
  reason: string;
}

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

const getApiUrl = () => {
  if (typeof window === 'undefined') {
    return process.env.API_URL || 'http://api:8000';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

export const API_URL = getApiUrl();

// Auth token management
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('auth_token', token);
}

export function clearAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('auth_token');
}

export const removeAuthToken = clearAuthToken;

// Helper function to add auth headers
function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

// Auth API calls
export async function register(email: string, password: string): Promise<User> {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }
  
  return response.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  
  const data = await response.json();
  setAuthToken(data.access_token);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: getHeaders(),
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch user');
  }
  
  return response.json();
}

export async function logout(): Promise<void> {
  clearAuthToken();
}

// Repository API calls (now with auth)
export async function getRepositories(): Promise<Repository[]> {
  const response = await fetch(`${API_URL}/repositories/`, {
    headers: getHeaders(),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch repositories');
  }
  
  return response.json();
}

export async function getRepository(id: string): Promise<Repository> {
  const response = await fetch(`${API_URL}/repositories/${id}`, {
    headers: getHeaders(),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch repository');
  }
  
  return response.json();
}

export async function getRepositoryHeatmap(id: string): Promise<HeatmapData[]> {
  const response = await fetch(`${API_URL}/analytics/repositories/${id}/heatmap`, {
    headers: getHeaders(),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch heatmap data');
  }
  
  return response.json();
}

export async function getRepositoryTimeline(id: string): Promise<TimelineData[]> {
  const response = await fetch(`${API_URL}/analytics/repositories/${id}/timeline`, {
    headers: getHeaders(),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch timeline data');
  }
  
  return response.json();
}

export async function getRepositoryContributors(id: string): Promise<ContributorData[]> {
  const response = await fetch(`${API_URL}/analytics/repositories/${id}/contributors`, {
    headers: getHeaders(),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch contributors data');
  }
  
  return response.json();
}

export async function createRepository(url: string): Promise<Repository> {
  const response = await fetch(`${API_URL}/repositories/`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ url }),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create repository' }));
    throw new Error(error.detail || 'Failed to create repository');
  }
  
  return response.json();
}

export async function deleteRepository(id: number): Promise<void> {
  const response = await fetch(`${API_URL}/repositories/${id}`, {
    method: 'DELETE',
    headers: getHeaders(),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete repository' }));
    throw new Error(error.detail || 'Failed to delete repository');
  }
}

export async function getRepositoryRiskPrediction(id: string): Promise<RiskPredictionData[]> {
  const response = await fetch(`${API_URL}/analytics/repositories/${id}/risk-prediction`, {
    headers: getHeaders(),
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch risk predictions');
  }
  
  return response.json();
}
