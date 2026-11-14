from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, case
from database import get_db
from models import Function, Commit, Repository, User, FileMetrics
from dependencies import get_current_user
from services.predictor import RiskPredictor
from collections import defaultdict
from datetime import datetime

router = APIRouter(prefix='/analytics', tags=['analytics'])

@router.get("/repositories/{repo_id}/heatmap")
def get_repository_heatmap(
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
        
        # Real per-file numbers from file_metrics (same source as the risk page):
        #   score = commits that touched the file (churn)
        #   size  = non-blank lines of the file at HEAD (loc)
        rows = (
            db.query(
                FileMetrics.file_path.label('name'),
                FileMetrics.loc.label('size'),
                FileMetrics.churn.label('score'),
            )
            .filter(FileMetrics.repository_id == repo_id, FileMetrics.loc > 0)
            .order_by(FileMetrics.churn.desc(), FileMetrics.file_path.asc())
            .limit(100)
            .all()
        )

        return [
            {"name": r.name, "size": int(r.size or 0), "score": int(r.score or 0)}
            for r in rows
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repositories/{repo_id}/timeline")
def get_repository_timeline(
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
        
        # --- Snapshot algorithm: running file_map ---
        # We need repo-wide totals after EACH commit, not just per-commit diffs.
        # Strategy:
        #   1. Fetch all commits in chronological order.
        #   2. Fetch (commit_id, file_path) aggregates for active/deleted rows.
        #   3. Walk commits in order, maintaining file_map = { file_path: {count, complexity_sum, loc_sum} }.
        #      On each commit, update changed files; then snapshot repo-wide sums.

        commits = (
            db.query(Commit.id, Commit.timestamp, Commit.sha, Commit.message)
            .filter(Commit.repository_id == repo_id)
            .order_by(Commit.timestamp.asc())
            .all()
        )

        # Aggregate per (commit_id, file_path): count active, sum complexity & loc
        func_rows = (
            db.query(
                Function.commit_id,
                Function.file_path,
                func.sum(
                    case((or_(Function.change_type.is_(None), Function.change_type != 'deleted'), 1), else_=0)
                ).label('active_count'),
                func.sum(
                    case((or_(Function.change_type.is_(None), Function.change_type != 'deleted'), Function.complexity), else_=0.0)
                ).label('complexity_sum'),
                func.sum(
                    case((or_(Function.change_type.is_(None), Function.change_type != 'deleted'), Function.end_line - Function.start_line), else_=0)
                ).label('loc_sum'),
            )
            .join(Commit, Function.commit_id == Commit.id)
            .filter(Commit.repository_id == repo_id)
            .group_by(Function.commit_id, Function.file_path)
            .all()
        )

        # Index by commit_id
        commit_file_updates: dict = defaultdict(list)
        for r in func_rows:
            commit_file_updates[r.commit_id].append(r)

        # Walk commits, maintain running snapshot
        file_map: dict = {}  # file_path -> {count, complexity_sum, loc_sum}
        result = []
        for c in commits:
            updates = commit_file_updates.get(c.id, [])
            if not updates and not file_map:
                # No data yet — skip
                continue
            for u in updates:
                active_count = int(u.active_count or 0)
                if active_count > 0:
                    file_map[u.file_path] = {
                        'count': active_count,
                        'complexity_sum': float(u.complexity_sum or 0.0),
                        'loc_sum': int(u.loc_sum or 0),
                    }
                else:
                    # All functions in this file were deleted this commit
                    file_map.pop(u.file_path, None)

            if not file_map and not updates:
                continue

            total_funcs = sum(f['count'] for f in file_map.values())
            total_complexity = sum(f['complexity_sum'] for f in file_map.values())
            total_loc = sum(f['loc_sum'] for f in file_map.values())
            avg_complexity = round(total_complexity / total_funcs, 2) if total_funcs > 0 else 0.0

            if total_funcs > 0 or updates:
                result.append({
                    "date": c.timestamp.isoformat() if c.timestamp else None,
                    "sha": c.sha[:7],
                    "message": c.message.split('\n')[0][:100] if c.message else "",
                    "function_count": total_funcs,
                    "avg_complexity": avg_complexity,
                    "total_loc": total_loc,
                })

        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repositories/{repo_id}/contributors")
def get_repository_contributors(
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
            .filter(
                Commit.repository_id == repo_id,
                Commit.author.isnot(None),
                or_(Function.change_type.is_(None), Function.change_type != 'deleted')
            )
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
def get_risk_prediction(
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
                    'loc':               row.loc               or 0,
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
                .filter(
                    Commit.repository_id == repo_id,
                    or_(Function.change_type.is_(None), Function.change_type != 'deleted')
                )
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
def get_function_evolution(
    repo_id: int,
    limit: int = Query(50, ge=1, le=200),
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

        # Memory-safe: pick the `limit` most-changed functions IN SQL first, then load
        # rows for only those. (Loading every row of a large repo into Python
        # dicts, then slicing, used to get the API process OOM-killed.)
        top_ids = [
            r.canonical_id
            for r in (
                db.query(Function.canonical_id, func.count(Function.id).label('n'))
                .join(Commit, Function.commit_id == Commit.id)
                .filter(Commit.repository_id == repo_id, Function.canonical_id.isnot(None))
                .group_by(Function.canonical_id)
                .order_by(func.count(Function.id).desc(), Function.canonical_id.asc())
                .limit(limit)
                .all()
            )
        ]
        if not top_ids:
            return []

        rows = (
            db.query(
                Function.canonical_id,
                Function.signature_hash,
                Function.body_hash,
                Function.name,
                Function.qualified_name,
                Function.change_type,
                Function.similarity,
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
                Function.canonical_id.in_(top_ids),
            )
            .order_by(Commit.timestamp.asc(), Function.id.asc())
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
                'qualified_name':   r.qualified_name or r.name,
                'change_type':      r.change_type,
                'similarity':       r.similarity,
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

        # ── inline get_function_evolution logic ──────
        by_cid: dict = defaultdict(list)
        for fn in db_functions:
            cid = fn.get('canonical_id')
            if cid:
                by_cid[cid].append(fn)

        evolution = []
        for cid, all_rows in by_cid.items():
            all_sorted = sorted(
                all_rows,
                key=lambda f: f.get('commit_timestamp') or datetime.min
            )
            first_row = all_sorted[0]
            last_row  = all_sorted[-1]

            # Detect moves: more than one distinct file_path
            paths = {v['file_path'] for v in all_sorted}
            was_moved = len(paths) > 1

            # Detect renames: more than one distinct qualified_name (fall back to name)
            names = {v.get('qualified_name') or v.get('name') for v in all_sorted if (v.get('qualified_name') or v.get('name'))}
            was_renamed = len(names) > 1

            # A version = a row where body_hash OR signature_hash differs from previous row, or lifecycle change (move/rename/deleted)
            versions = []
            prev_body_hash = None
            prev_sig_hash = None
            for idx, r in enumerate(all_sorted):
                curr_body_hash = r.get('body_hash')
                curr_sig_hash = r.get('signature_hash')
                ctype = r.get('change_type')
                if (idx == 0 or
                    curr_body_hash != prev_body_hash or
                    curr_sig_hash != prev_sig_hash or
                    ctype in ['move', 'rename', 'deleted']):
                    versions.append(r)
                    prev_body_hash = curr_body_hash
                    prev_sig_hash = curr_sig_hash

            if not versions:
                versions = [last_row]

            # Complexity trend across versions
            delta = versions[-1]['complexity'] - versions[0]['complexity']
            trend = 'increasing' if delta > 0 else ('decreasing' if delta < 0 else 'stable')

            evolution.append({
                'canonical_id':     cid,
                'name':             last_row.get('name', ''),
                'qualified_name':   last_row.get('qualified_name', ''),
                'file_path':        last_row.get('file_path', ''),
                'first_seen_sha':   first_row.get('commit_sha', ''),
                'last_seen_sha':    last_row.get('commit_sha', ''),
                'first_seen_ts':    first_row.get('commit_timestamp'),
                'last_seen_ts':     last_row.get('commit_timestamp'),
                'commit_count':     len(all_sorted),
                'was_moved':        was_moved,
                'was_renamed':      was_renamed,
                'complexity_trend': trend,
                'complexity_delta': delta,
                'versions':         versions,
            })

        evolution.sort(key=lambda r: (-r['commit_count'], r['canonical_id']))

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
                    'qualified_name': v.get('qualified_name', ''),
                    'change_type':    v.get('change_type'),
                    'similarity':     v.get('similarity'),
                    'complexity':     v.get('complexity', 0),
                    'start_line':     v.get('start_line', 0),
                    'end_line':       v.get('end_line', 0),
                })

            first_ts = entry.get('first_seen_ts')
            last_ts  = entry.get('last_seen_ts')
            return {
                'canonical_id':     entry['canonical_id'],
                'name':             entry['name'],
                'qualified_name':   entry.get('qualified_name'),
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
