import os
import git
from typing import Optional

class GitService:
    def __init__(self, storage_path: str, github_token: Optional[str] = None):
        self.storage_path = storage_path
        self.github_token = github_token
        os.makedirs(storage_path, exist_ok=True)
    
    def clone_repository(self, url: str, repo_id: int) -> str:
        repo_dir = os.path.join(self.storage_path, f"repo_{repo_id}")
        
        if os.path.exists(repo_dir):
            return repo_dir
        
        clone_url = url
        if self.github_token and 'github.com' in url:
            clone_url = url.replace('https://', f'https://{self.github_token}@')
        
        git.Repo.clone_from(clone_url, repo_dir)
        return repo_dir
    
    def get_commits(self, repo_path: str):
        repo = git.Repo(repo_path)
        commits = []
        
        for commit in repo.iter_commits():
            commits.append({
                'sha': commit.hexsha,
                'author': str(commit.author),
                'message': commit.message.strip(),
                'timestamp': commit.committed_datetime
            })
        
        return commits
    
    def get_file_at_commit(self, repo_path: str, commit_sha: str, file_path: str) -> Optional[str]:
        try:
            repo = git.Repo(repo_path)
            commit = repo.commit(commit_sha)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode('utf-8')
        except:
            return None
