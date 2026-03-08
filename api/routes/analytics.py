from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Function, Commit, Repository, User, FileMetrics
from dependencies import get_current_user
from services.predictor import RiskPredictor
from collections import defaultdict
from datetime import datetime

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


@router.get("/repositories/{repo_id}/function-evolution")
async def get_function_evolution(
    repo_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Return per-function evolution timelines for a repository.

    Each entry represents one unique function (identified by canonical_id) and
    includes:
    - Whether it was ever moved to a different file
    - Whether it was ever renamed / had its signature changed
    - Complexity trend across commits
    - Full chronological version history
    """
    try:
        repo = db.query(Repository).filter(
            Repository.id == repo_id,
            Repository.owner_id == current_user.id
        ).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Only pull functions that have a canonical_id (hashed by the new miner)
        rows = (
            db.query(
                Function.canonical_id,
                Function.signature_hash,
                Function.body_hash,
                Function.name,
                Function.file_path,
                Function.start_line,
                Function.end_line,
                Function.complexity,
                Commit.sha.label('commit_sha'),
                Commit.timestamp.label('commit_timestamp'),
                Commit.author.label('commit_author'),
                Commit.message.label('commit_message'),
            )
            .join(Commit, Function.commit_id == Commit.id)
            .filter(
                Commit.repository_id == repo_id,
                Function.canonical_id.isnot(None),
            )
            .order_by(Commit.timestamp.asc())
            .all()
        )

        if not rows:
            return []

        db_functions = [
            {
                'canonical_id':     r.canonical_id,
                'signature_hash':   r.signature_hash,
                'body_hash':        r.body_hash,
                'name':             r.name,
                'file_path':        r.file_path,
                'start_line':       r.start_line,
                'end_line':         r.end_line,
                'complexity':       r.complexity or 0,
                'commit_sha':       r.commit_sha,
                'commit_timestamp': r.commit_timestamp,
                'commit_author':    r.commit_author,
                'commit_message':   r.commit_message,
            }
            for r in rows
        ]

        # ── inline get_function_evolution logic (no git I/O needed) ──────
        by_cid: dict = defaultdict(list)
        for fn in db_functions:
            cid = fn.get('canonical_id')
            if cid:
                by_cid[cid].append(fn)

        evolution = []
        for cid, versions in by_cid.items():
            versions_sorted = sorted(
                versions,
                key=lambda f: f.get('commit_timestamp') or datetime.min
            )
            first = versions_sorted[0]
            last  = versions_sorted[-1]

            paths = [v['file_path'] for v in versions_sorted]
            was_moved = len(set(paths)) > 1

            sigs = [v.get('signature_hash') for v in versions_sorted if v.get('signature_hash')]
            was_renamed = len(set(sigs)) > 1

            complexities = [v.get('complexity') or 0 for v in versions_sorted]
            if len(complexities) >= 2:
                delta = complexities[-1] - complexities[0]
                trend = 'increasing' if delta > 0 else ('decreasing' if delta < 0 else 'stable')
            else:
                delta, trend = 0, 'stable'

            evolution.append({
                'canonical_id':     cid,
                'name':             last.get('name', ''),
                'file_path':        last.get('file_path', ''),
                'first_seen_sha':   first.get('commit_sha', ''),
                'last_seen_sha':    last.get('commit_sha', ''),
                'first_seen_ts':    first.get('commit_timestamp'),
                'last_seen_ts':     last.get('commit_timestamp'),
                'commit_count':     len(versions_sorted),
                'was_moved':        was_moved,
                'was_renamed':      was_renamed,
                'complexity_trend': trend,
                'complexity_delta': delta,
                'versions':         versions_sorted,
            })

        evolution.sort(key=lambda r: r['commit_count'], reverse=True)

        # Serialise — datetime objects aren't JSON-serialisable by default
        def _serialise(entry: dict) -> dict:
            versions_out = []
            for v in entry.get('versions', []):
                ts = v.get('commit_timestamp')
                versions_out.append({
                    'commit_sha':     v.get('commit_sha', '')[:7],
                    'commit_author':  v.get('commit_author', ''),
                    'commit_message': (v.get('commit_message') or '')[:120],
                    'timestamp':      ts.isoformat() if ts else None,
                    'file_path':      v.get('file_path', ''),
                    'name':           v.get('name', ''),
                    'complexity':     v.get('complexity', 0),
                    'start_line':     v.get('start_line', 0),
                    'end_line':       v.get('end_line', 0),
                })

            first_ts = entry.get('first_seen_ts')
            last_ts  = entry.get('last_seen_ts')
            return {
                'canonical_id':     entry['canonical_id'],
                'name':             entry['name'],
                'file_path':        entry['file_path'],
                'first_seen_sha':   (entry.get('first_seen_sha') or '')[:7],
                'last_seen_sha':    (entry.get('last_seen_sha') or '')[:7],
                'first_seen_ts':    first_ts.isoformat() if first_ts else None,
                'last_seen_ts':     last_ts.isoformat()  if last_ts  else None,
                'commit_count':     entry['commit_count'],
                'was_moved':        entry['was_moved'],
                'was_renamed':      entry['was_renamed'],
                'complexity_trend': entry['complexity_trend'],
                'complexity_delta': entry['complexity_delta'],
                'versions':         versions_out,
            }

        return [_serialise(e) for e in evolution[:limit]]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
