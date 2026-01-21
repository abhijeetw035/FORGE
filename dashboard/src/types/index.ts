export interface Repository {
  id: number;
  name: string;
  owner: string;
  url: string;
  status: 'queued' | 'analyzing' | 'completed' | 'failed';
  created_at: string;
}

export interface Commit {
  id: number;
  repository_id: number;
  sha: string;
  author_name: string;
  author_email: string;
  commit_date: string;
  message: string;
  created_at: string;
}

export interface Function {
  id: number;
  commit_id: number;
  name: string;
  file_path: string;
  start_line: number;
  end_line: number;
  complexity: number;
  parameters: Record<string, unknown>;
  entropy: number;
  ast_data: Record<string, unknown>;
}
