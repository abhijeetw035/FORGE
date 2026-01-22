from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import redis
import json

from database import get_db
from models import Repository, User
from schemas import RepositoryCreate, RepositoryResponse, RepositoryDetail
from dependencies import get_current_user

router = APIRouter(prefix="/repositories", tags=["repositories"])

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

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
    redis_client.rpush('task_queue', json.dumps(task))
    
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
