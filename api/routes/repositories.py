from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import redis
import json

from database import get_db
from models import Repository, User, Commit, Function, FileMetrics
from schemas import RepositoryCreate, RepositoryResponse, RepositoryDetail
from dependencies import get_current_user

router = APIRouter(prefix="/repositories", tags=["repositories"])

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# ── Redis Stream constants ────────────────────────────────────────────────────
STREAM_NAME    = 'forge:tasks'
CONSUMER_GROUP = 'miner-workers'

def _publish_task(task: dict) -> None:
    """
    Publish a task to the Redis Stream.

    Redis Streams give at-least-once delivery: the message stays in the stream
    until a consumer explicitly ACKs it.  If the worker crashes after reading
    but before ACKing, the message is reclaimed on the next XAUTOCLAIM call.

    Falls back to the legacy RPUSH list so existing workers keep working during
    a rolling deploy.
    """
    try:
        redis_client.xadd(STREAM_NAME, {'payload': json.dumps(task)})
    except Exception:
        # Fallback to legacy list (e.g. Redis < 5.0)
        redis_client.rpush('task_queue', json.dumps(task))

@router.post("/", response_model=RepositoryResponse)
async def create_repository(
    repo: RepositoryCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Repository).filter(Repository.url == repo.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="Repository already exists")
    
    parts = repo.url.rstrip('/').split('/')
    owner = parts[-2]
    name = parts[-1].replace('.git', '')
    
    db_repo = Repository(
        url=repo.url,
        name=name,
        owner=owner,
        owner_id=current_user.id,  # Assign to current user
        status="queued"
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    
    task = {
        "type": "clone_and_analyze",
        "repository_id": db_repo.id,
        "url": repo.url
    }
    _publish_task(task)
    
    return db_repo

@router.get("/", response_model=List[RepositoryResponse])
async def list_repositories(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Filter repositories by current user
    repos = db.query(Repository).filter(
        Repository.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return repos

@router.get("/{repo_id}", response_model=RepositoryDetail)
async def get_repository(
    repo_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id  # Ensure user owns this repo
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

@router.delete("/{repo_id}")
async def delete_repository(
    repo_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id  # Ensure user owns this repo
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    db.delete(repo)
    db.commit()
    return {"message": "Repository deleted"}


@router.post("/{repo_id}/reanalyze")
async def reanalyze_repository(
    repo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Wipe all derived data (Function rows, Commit rows, FileMetrics) for this
    repository and re-queue a full fresh analysis.

    This is needed when new miner features (function-identity hashes, richer
    file metrics) were introduced after the original analysis was run.
    """
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.owner_id == current_user.id
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    if repo.status in ("cloning", "analyzing"):
        raise HTTPException(status_code=409, detail="Repository is already being analysed")

    # Delete Function rows via their Commit FK
    commit_ids = [c.id for c in db.query(Commit.id).filter(Commit.repository_id == repo_id)]
    if commit_ids:
        db.query(Function).filter(Function.commit_id.in_(commit_ids)).delete(synchronize_session=False)

    db.query(Commit).filter(Commit.repository_id == repo_id).delete(synchronize_session=False)
    db.query(FileMetrics).filter(FileMetrics.repository_id == repo_id).delete(synchronize_session=False)

    # Clear the incremental checkpoint so worker does a full walk
    repo.last_indexed_sha = None
    repo.status = "queued"
    db.commit()

    task = {
        "type": "clone_and_analyze",
        "repository_id": repo.id,
        "url": repo.url,
    }
    _publish_task(task)

    return {"message": "Re-analysis queued", "repository_id": repo_id}
