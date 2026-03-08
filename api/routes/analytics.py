from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Function, Commit, Repository, User, FileMetrics
from dependencies import get_current_user
from services.predictor import RiskPredictor

router = APIRouter(prefix='/analytics', tags=['analytics'])

@router.get("/repositories/{repo_id}/heatmap")
async def get_repository_heatmap(
    repo_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Verify user owns this repository
        repo = db.query(Repository).filter(
            Repository.id == repo_id,
            Repository.owner_id == current_user.id
        ).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        heatmap_data = (
            db.query(
                Function.file_path.label('name'),
                func.sum(Function.end_line - Function.start_line).label('size'),
                func.count(Function.id).label('score')
            )
            .join(Commit, Function.commit_id == Commit.id)
            .filter(Commit.repository_id == repo_id)
            .group_by(Function.file_path)
            .order_by(func.count(Function.id).desc())
            .limit(100)
            .all()
        )
        
        result = [
            {
                "name": row.name,
                "size": int(row.size) if row.size else 0,
                "score": int(row.score) if row.score else 0
            }
            for row in heatmap_data
        ]
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repositories/{repo_id}/timeline")
async def get_repository_timeline(
    repo_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Verify user owns this repository
        repo = db.query(Repository).filter(
            Repository.id == repo_id,
            Repository.owner_id == current_user.id
        ).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        timeline_data = (
            db.query(
                Commit.timestamp.label('date'),
                Commit.sha.label('sha'),
                Commit.message.label('message'),
                func.count(Function.id).label('function_count'),
                func.avg(Function.complexity).label('avg_complexity'),
                func.sum(Function.end_line - Function.start_line).label('total_loc')
            )
            .join(Function, Commit.id == Function.commit_id)
            .filter(Commit.repository_id == repo_id)
            .group_by(Commit.id, Commit.timestamp, Commit.sha, Commit.message)
            .order_by(Commit.timestamp.asc())
            .all()
        )
        
        result = [
            {
                "date": row.date.isoformat() if row.date else None,
                "sha": row.sha[:7],
                "message": row.message.split('\n')[0][:100],
                "function_count": int(row.function_count) if row.function_count else 0,
                "avg_complexity": round(float(row.avg_complexity), 2) if row.avg_complexity else 0,
                "total_loc": int(row.total_loc) if row.total_loc else 0
            }
            for row in timeline_data
        ]
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repositories/{repo_id}/contributors")
async def get_repository_contributors(
    repo_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze contributor impact: who adds the most complexity?
    
    Metrics:
    - total_commits: Number of commits by this author
    - functions_added: Total functions authored
    - total_complexity: Sum of complexity across all their functions
    - avg_complexity: Average complexity of their functions
    - total_loc: Total lines of code contributed
    - entropy_score: Weighted score (complexity * functions)
    """
    try:
        # Verify user owns this repository
        repo = db.query(Repository).filter(
            Repository.id == repo_id,
            Repository.owner_id == current_user.id
        ).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        entropy_score_col = (func.avg(Function.complexity) * func.count(Function.id)).label('entropy_score')
        
        contributor_data = (
            db.query(
                Commit.author.label('author'),
                func.count(func.distinct(Commit.id)).label('total_commits'),
                func.count(Function.id).label('functions_added'),
                func.sum(Function.complexity).label('total_complexity'),
                func.avg(Function.complexity).label('avg_complexity'),
                func.sum(Function.end_line - Function.start_line).label('total_loc'),
                entropy_score_col
            )
            .join(Function, Commit.id == Function.commit_id)
            .filter(Commit.repository_id == repo_id)
            .filter(Commit.author.isnot(None))
            .group_by(Commit.author)
            .order_by(entropy_score_col.desc())
            .all()
        )
        
        result = [
            {
                "author": row.author,
                "total_commits": int(row.total_commits) if row.total_commits else 0,
                "functions_added": int(row.functions_added) if row.functions_added else 0,
                "total_complexity": round(float(row.total_complexity), 2) if row.total_complexity else 0,
                "avg_complexity": round(float(row.avg_complexity), 2) if row.avg_complexity else 0,
                "total_loc": int(row.total_loc) if row.total_loc else 0,
                "entropy_score": round(float(row.entropy_score), 2) if row.entropy_score else 0
            }
            for row in contributor_data
        ]
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repositories/{repo_id}/risk-prediction")
async def get_risk_prediction(
    repo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Verify user owns this repository
        repo = db.query(Repository).filter(
            Repository.id == repo_id,
            Repository.owner_id == current_user.id
        ).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Query FileMetrics rows (populated by the miner).
        fm_rows = (
            db.query(FileMetrics)
            .filter(FileMetrics.repository_id == repo_id)
            .all()
        )

        if fm_rows:
            data = [
                {
                    'file_path':         row.file_path,
                    'churn':             row.churn             or 0,
                    'lines_added':       row.lines_added       or 0,
                    'lines_deleted':     row.lines_deleted     or 0,
                    'file_age_days':     row.file_age_days     or 0.0,
                    'commit_frequency':  row.commit_frequency  or 0.0,
                    'recent_churn':      row.recent_churn      or 0,
                    'author_count':      row.author_count      or 1,
                    'ownership_entropy': row.ownership_entropy or 0.0,
                    'dependency_count':  row.dependency_count  or 0,
                    'complexity':        row.avg_complexity    or 0.0,
                }
                for row in fm_rows
            ]
        else:
            # Legacy fallback: derive minimal features from Function/Commit tables
            file_stats = (
                db.query(
                    Function.file_path,
                    func.count(Function.id).label('churn'),
                    func.avg(Function.complexity).label('complexity'),
                    func.count(func.distinct(Commit.author)).label('author_count')
                )
                .join(Commit, Function.commit_id == Commit.id)
                .filter(Commit.repository_id == repo_id)
                .group_by(Function.file_path)
                .all()
            )
            if not file_stats:
                return []
            data = [
                {
                    'file_path':         row.file_path,
                    'churn':             int(row.churn)             if row.churn       else 0,
                    'lines_added':       0,
                    'lines_deleted':     0,
                    'file_age_days':     0.0,
                    'commit_frequency':  0.0,
                    'recent_churn':      0,
                    'author_count':      int(row.author_count)      if row.author_count else 1,
                    'ownership_entropy': 0.0,
                    'dependency_count':  0,
                    'complexity':        round(float(row.complexity), 2) if row.complexity else 0.0,
                }
                for row in file_stats
            ]

        if not data:
            return []

        # Run AI prediction with all features
        predictor = RiskPredictor(contamination=0.1)
        predictions = predictor.predict_risk(data)

        # Return top 20 at-risk files
        return predictions[:20]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
