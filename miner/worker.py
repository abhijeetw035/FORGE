import time
import redis
import logging
import json
import os
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Repository, Commit, Function
from services.git_service import GitService
from services.ast_parser import ASTParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

storage_path = os.getenv('STORAGE_PATH', '/storage')
git_service = GitService(storage_path)
ast_parser = ASTParser()

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
        
        db.commit()
        repo.status = "completed"
        db.commit()
        
        logger.info(f"Repository {repo_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing repository {repo_id}: {e}")
        repo.status = "failed"
        db.commit()

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
