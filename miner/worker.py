import time
import redis
import logging
import json
import os
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Repository, Commit, Function, FileMetrics
from services.git_service import GitService
from services.ast_parser import ASTParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

storage_path = os.getenv('STORAGE_PATH', '/storage')
github_token = os.getenv('GITHUB_TOKEN')
git_service = GitService(storage_path, github_token)
ast_parser = ASTParser()

if github_token:
    logger.info("GitHub token detected - private repository access enabled")
else:
    logger.info("No GitHub token - only public repositories can be cloned")

try:
    ast_parser.setup_python()
    logger.info("Tree-sitter Python parser initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Tree-sitter: {e}")

def process_repository(task_data: dict, db: Session):
    repo_id = task_data['repository_id']
    url = task_data['url']
    
    logger.info(f"Processing repository {repo_id}: {url}")
    
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        logger.error(f"Repository {repo_id} not found")
        return
    
    try:
        repo.status = "cloning"
        db.commit()
        
        repo_path = git_service.clone_repository(url, repo_id)
        repo.clone_path = repo_path
        repo.status = "analyzing"
        db.commit()
        
        commits_data = git_service.get_commits(repo_path)
        logger.info(f"Found {len(commits_data)} commits")
        
        for commit_data in commits_data:
            existing_commit = db.query(Commit).filter(
                Commit.repository_id == repo_id,
                Commit.sha == commit_data['sha']
            ).first()
            
            if not existing_commit:
                commit = Commit(
                    repository_id=repo_id,
                    sha=commit_data['sha'],
                    author=commit_data['author'],
                    message=commit_data['message'],
                    timestamp=commit_data['timestamp']
                )
                db.add(commit)
                db.flush()
                
                process_commit_ast(commit, repo_path, db)
        
        db.commit()

        logger.info(f"Computing rich file metrics for repo {repo_id}...")
        try:
            compute_and_store_file_metrics(repo_id, repo_path, db)
        except Exception as metric_err:
            logger.warning(f"File-metrics computation failed (non-fatal): {metric_err}")

        repo.status = "completed"
        db.commit()
        
        logger.info(f"Repository {repo_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing repository {repo_id}: {e}")
        repo.status = "failed"
        db.commit()

def process_commit_ast(commit: Commit, repo_path: str, db: Session):
    try:
        import git as gitpython
        repo = gitpython.Repo(repo_path)
        commit_obj = repo.commit(commit.sha)
        
        for item in commit_obj.tree.traverse():
            if item.type == 'blob':
                file_path = item.path
                _, ext = os.path.splitext(file_path)
                
                if ext in ['.py', '.js', '.java', '.go']:
                    try:
                        source_code = item.data_stream.read().decode('utf-8')
                        tree = ast_parser.parse_file(source_code, file_path)
                        
                        if tree:
                            parser, language = ast_parser.get_parser(ext)
                            functions = ast_parser.extract_functions(tree, source_code, language)
                            
                            for func_data in functions:
                                function = Function(
                                    commit_id=commit.id,
                                    name=func_data['name'],
                                    file_path=file_path,
                                    start_line=func_data['start_line'],
                                    end_line=func_data['end_line'],
                                    complexity=func_data['complexity'],
                                    lines_of_code=func_data['lines_of_code'],
                                    parameters=func_data['parameters'],
                                    # stable cross-commit identity hashes
                                    body_hash=func_data.get('body_hash'),
                                    signature_hash=func_data.get('signature_hash'),
                                    canonical_id=func_data.get('canonical_id'),
                                )
                                db.add(function)
                    except Exception as e:
                        logger.debug(f"Could not parse {file_path}: {e}")
                        continue
        
        commit.processed = True
        
    except Exception as e:
        logger.error(f"Error processing AST for commit {commit.sha}: {e}")


def compute_and_store_file_metrics(repo_id: int, repo_path: str, db: Session):
    """
    Compute rich per-file metrics via GitService and store/update FileMetrics rows.
    Also merges avg_complexity from the already-stored Function records.
    """
    from sqlalchemy import func as sqlfunc

    # 1. Get git-history metrics for every file
    metrics_list = git_service.get_file_metrics(repo_path)

    # 2. Compute avg_complexity per file from stored Function records
    complexity_rows = (
        db.query(
            Function.file_path,
            sqlfunc.avg(Function.complexity).label('avg_complexity')
        )
        .join(Commit, Function.commit_id == Commit.id)
        .filter(Commit.repository_id == repo_id)
        .group_by(Function.file_path)
        .all()
    )
    complexity_map = {row.file_path: float(row.avg_complexity or 0) for row in complexity_rows}

    for m in metrics_list:
        path = m['file_path']
        # upsert: update existing row or insert new one
        existing = (
            db.query(FileMetrics)
            .filter(FileMetrics.repository_id == repo_id, FileMetrics.file_path == path)
            .first()
        )
        if existing:
            row = existing
        else:
            row = FileMetrics(repository_id=repo_id, file_path=path)
            db.add(row)

        row.churn             = m['churn']
        row.lines_added       = m['lines_added']
        row.lines_deleted     = m['lines_deleted']
        row.file_age_days     = m['file_age_days']
        row.commit_frequency  = m['commit_frequency']
        row.recent_churn      = m['recent_churn']
        row.author_count      = m['author_count']
        row.ownership_entropy = m['ownership_entropy']
        row.dependency_count  = m['dependency_count']
        row.avg_complexity    = complexity_map.get(path, 0.0)

    db.commit()
    logger.info(f"Stored FileMetrics for {len(metrics_list)} files in repo {repo_id}")


def main():
    logger.info("Miner worker starting...")
    
    r = redis.Redis(host='redis', port=6379, decode_responses=True)
    
    while True:
        try:
            task = r.blpop('task_queue', timeout=5)
            if task:
                task_data = json.loads(task[1])
                logger.info(f"Processing task: {task_data}")
                
                db = SessionLocal()
                try:
                    if task_data['type'] == 'clone_and_analyze':
                        process_repository(task_data, db)
                finally:
                    db.close()
            else:
                logger.debug("No tasks in queue")
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
