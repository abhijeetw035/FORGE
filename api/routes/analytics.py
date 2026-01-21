from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Function, Commit

router = APIRouter(prefix='/analytics', tags=['analytics'])

@router.get("/repositories/{repo_id}/heatmap")
async def get_repository_heatmap(repo_id: int, db: Session = Depends(get_db)):
    try:
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
