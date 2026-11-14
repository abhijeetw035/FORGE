import time
import redis
import logging
import json
import os
import socket
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal, engine
from models import Repository, Commit, Function, FileMetrics, FileChange
from services.git_service import GitService
from services.ast_parser import ASTParser
from services.identity import FunctionIdentityTracker, match_functions
from queue_utils import (
    PermanentError, repo_lock, handle_message, redact_secrets, install_log_redaction,
    STREAM_NAME, CONSUMER_GROUP, CLAIM_IDLE_MS,
)

logging.basicConfig(level=logging.INFO)
install_log_redaction()
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

_PERMANENT_CLONE_MARKERS = (
    'repository not found', 'not found', 'authentication failed',
    'could not read username', 'invalid username or password',
    'does not appear to be a git repository', 'unable to access',
    # git could not prompt for credentials (no TTY): private/nonexistent repo
    'could not read password', 'terminal prompts disabled', 'no such device or address',
    'invalid url', 'permission denied', 'returned error: 40',
)


def classify_clone_error(exc: Exception) -> Exception:
    """Return PermanentError for failures retrying cannot fix, else the original."""
    msg = str(exc).lower()
    if any(m in msg for m in _PERMANENT_CLONE_MARKERS):
        # "unable to access" also covers transient network errors; keep those retryable
        if 'unable to access' in msg and any(
            t in msg for t in ('timed out', 'timeout', 'could not resolve', 'connection reset',
                               'connection refused', 'returned error: 5')
        ):
            return exc
        return PermanentError(f"Could not clone repository: {redact_secrets(exc)}")
    return exc


def mark_repo_failed(repo_id, reason: str) -> None:
    """Mark a repository failed with a human-readable reason (own session)."""
    if repo_id is None:
        return
    db = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.status = "failed"
            repo.failed_reason = redact_secrets(reason or "")[:1000]
            db.commit()
    except Exception:
        db.rollback()
        logger.exception(f"Could not mark repo {repo_id} failed")
    finally:
        db.close()


def mark_repo_retrying(task_data: dict, exc: Exception) -> None:
    """Transient failure: show the repo as waiting for a retry, not stuck mid-analysis."""
    repo_id = task_data.get('repository_id')
    db = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.status = "queued"
            repo.failed_reason = f"Retrying after error: {redact_secrets(exc)[:500]}"
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def process_repository(task_data: dict, db: Session) -> bool:
    """
    Run the analysis for one repository under a per-repo advisory lock.

    Returns True if the work ran, False if another worker already holds the
    lock (the caller should still ACK: the message is a duplicate).
    Raises PermanentError for failures retrying cannot fix; any other
    exception is transient (the message is left un-ACKed and retried).
    """
    repo_id = task_data['repository_id']
    with repo_lock(engine, repo_id) as acquired:
        if not acquired:
            logger.info(f"Repository {repo_id} is already being processed; skipping duplicate")
            return False
        _run_pipeline(task_data, db)
        return True


def _run_pipeline(task_data: dict, db: Session) -> None:
    repo_id = task_data['repository_id']
    url = task_data['url']

    logger.info(f"Processing repository {repo_id}: {url}")

    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        if repo_id >= 999000:
            # Simulate real work for dummy benchmark tasks to measure concurrency scaling
            time.sleep(0.5)
            logger.info(f"Simulated work for dummy repo {repo_id}")
            return
        raise PermanentError(f"Repository {repo_id} not found")

    try:
        repo.status = "cloning"
        repo.failed_reason = None
        db.commit()

        try:
            repo_path = git_service.clone_repository(url, repo_id)
        except Exception as clone_err:
            raise classify_clone_error(clone_err)
        repo.clone_path = repo_path
        repo.status = "analyzing"
        db.commit()

        # ── incremental indexing ──────────────────────────────────────────
        # If this repo was analysed before, last_indexed_sha holds the HEAD
        # SHA from that run.  We ask git for ONLY the commits that arrived
        # since then (git log <sha>..HEAD).  On first run since_sha is None
        # so we fall back to the full history walk.
        since_sha = repo.last_indexed_sha
        commits_data = git_service.get_new_commits(repo_path, since_sha=since_sha)

        identity_tracker = FunctionIdentityTracker(repo_id, db, repo_path=repo_path)
        if since_sha:
            logger.info(f"Incremental run: {len(commits_data)} new commits since {since_sha[:7]}")
            identity_tracker.seed_from_db(since_sha)
        else:
            logger.info(f"First run: {len(commits_data)} commits to index")

        for commit_data in commits_data:
            _index_commit(db, repo, repo_id, repo_path, commit_data, identity_tracker)

        db.commit()

        # Commits indexed before file_changes existed (or by a run that predates
        # it) get their raw facts backfilled, so metrics are always complete.
        backfill_file_changes(repo_id, repo_path, db)

        # Exact recompute from file_changes: nothing is merged with old values,
        # so a crash/resume can never leave history missing.
        logger.info(f"Recomputing file metrics for repo {repo_id}...")
        recompute_file_metrics(db, repo_id, git_service.get_head_files(repo_path))

        repo.status = "completed"
        repo.failed_reason = None
        db.commit()

        logger.info(f"Repository {repo_id} processed successfully")

    except Exception as e:
        # Do NOT swallow: PermanentError fails fast, anything else is retried.
        # The queue handler records the final status/reason.
        logger.error(f"Error processing repository {repo_id}: {e}")
        db.rollback()
        raise

def _function_row(commit_id: int, func_data: dict, deleted: bool) -> dict:
    """Column dict for a Function insert (active or deleted)."""
    return {
        'commit_id': commit_id,
        'name': func_data['name'],
        'qualified_name': func_data.get('qualified_name'),
        'file_path': func_data['file_path'],
        'start_line': func_data.get('start_line'),
        'end_line': func_data.get('end_line'),
        'complexity': func_data.get('complexity'),
        'lines_of_code': 0 if deleted else func_data.get('lines_of_code'),
        'parameters': func_data.get('parameters'),
        'body_hash': func_data.get('body_hash'),
        'signature_hash': func_data.get('signature_hash'),
        'canonical_id': func_data.get('canonical_id'),
        'change_type': 'deleted' if deleted else func_data.get('change_type'),
        'similarity': None if deleted else func_data.get('similarity'),
    }


def process_commit_ast(commit: Commit, repo_path: str, db: Session,
                       changed_files: list = None,
                       identity_tracker: FunctionIdentityTracker = None):
    """
    Parse functions from a single commit with stable canonical_id identity matching.

    ``changed_files`` — list of file paths that were actually modified in
    this commit (from git diff-tree).  When supplied we only parse those
    files, which is O(changed files) instead of O(all files in tree).
    Falls back to full tree traversal when None (legacy path / root commit).
    """
    try:
        import git as gitpython
        repo = gitpython.Repo(repo_path)
        commit_obj = repo.commit(commit.sha)

        if identity_tracker is None:
            identity_tracker = FunctionIdentityTracker(commit.repository_id, db, repo_path=repo_path)

        # Build the set of files to parse
        PARSEABLE_EXTS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go'}

        if changed_files is not None:
            # Efficient path: only look at files that changed in this commit
            candidates = [
                p for p in changed_files
                if os.path.splitext(p)[1] in PARSEABLE_EXTS
            ]
            blobs = []
            for file_path in candidates:
                try:
                    blob = commit_obj.tree / file_path
                    blobs.append((file_path, blob))
                except KeyError:
                    # File deleted in this commit — nothing to parse
                    continue
        else:
            # Fallback: traverse entire tree (first-run root commits)
            blobs = [
                (item.path, item)
                for item in commit_obj.tree.traverse()
                if item.type == 'blob'
                and os.path.splitext(item.path)[1] in PARSEABLE_EXTS
            ]

        new_funcs = []
        for file_path, blob in blobs:
            try:
                source_code = blob.data_stream.read().decode('utf-8')
                tree = ast_parser.parse_file(source_code, file_path)
                
                if tree:
                    _, ext = os.path.splitext(file_path)
                    res = ast_parser.get_parser(ext)
                    if not res:
                        continue
                    parser, language = res
                    functions = ast_parser.extract_functions(tree, source_code, language)
                    for func_data in functions:
                        func_data['file_path'] = file_path
                        new_funcs.append(func_data)
            except Exception as e:
                logger.debug(f"Could not parse {file_path}: {e}")
                continue

        # Get previous functions for comparison (re-parsing parent commit on demand if seeded from DB)
        parent_sha = commit_obj.parents[0].hexsha if commit_obj.parents else None
        prev_funcs = identity_tracker.get_prev_funcs(
            changed_files,
            ast_parser=ast_parser,
            parent_sha=parent_sha
        )

        # Match new vs previous functions
        matched_new, deleted_funcs = match_functions(new_funcs, prev_funcs)

        # Idempotent write: unique (commit_id, file_path, qualified_name) +
        # ON CONFLICT DO NOTHING, so a duplicate run cannot create duplicate rows.
        rows = []
        for func_data in matched_new:
            rows.append(_function_row(commit.id, func_data, deleted=False))
        for func_data in deleted_funcs:
            rows.append(_function_row(commit.id, func_data, deleted=True))
        if rows:
            db.execute(
                pg_insert(Function).on_conflict_do_nothing(constraint='uq_functions_identity'),
                rows,
            )

        # Update identity tracker state for subsequent commits
        identity_tracker.update_state(matched_new, deleted_funcs)
        
        commit.processed = True
        
    except Exception as e:
        logger.error(f"Error processing AST for commit {commit.sha}: {e}")


def _index_commit(db: Session, repo: Repository, repo_id: int, repo_path: str, commit_data: dict,
                  identity_tracker: FunctionIdentityTracker) -> bool:
    """
    Index ONE commit atomically: the commit row, its functions, its file_changes
    facts and the last_indexed_sha checkpoint are saved by a single db.commit().
    Either all of it is stored or none of it, so a crash can never lose history.

    Idempotent: returns False (no-op) if the commit already exists.
    """
    commit_id = db.execute(
        pg_insert(Commit)
        .values(
            repository_id=repo_id,
            sha=commit_data['sha'],
            author=commit_data['author'],
            message=commit_data['message'],
            timestamp=commit_data['timestamp'],
            processed=False,
            changes_recorded=True,
        )
        .on_conflict_do_nothing(constraint='uq_commits_repository_sha')
        .returning(Commit.id)
    ).scalar()

    if commit_id is None:
        return False

    commit = db.get(Commit, commit_id)

    # Only parse the files that actually changed in this commit
    process_commit_ast(commit, repo_path, db,
                       changed_files=commit_data.get('changed_files'),
                       identity_tracker=identity_tracker)

    _store_file_changes(db, repo_id, commit_id, commit_data)

    # Checkpoint in the SAME transaction as everything above.
    repo.last_indexed_sha = commit_data['sha']
    db.commit()
    return True


def _store_file_changes(db: Session, repo_id: int, commit_id: int, commit_data: dict) -> None:
    rows = [
        {
            'repository_id': repo_id,
            'commit_id': commit_id,
            'file_path': fc['file_path'],
            'author_email': commit_data['author_email'],
            'committed_at': commit_data['committed_at'],
            'lines_added': fc['lines_added'],
            'lines_deleted': fc['lines_deleted'],
        }
        for fc in commit_data.get('file_changes', [])
    ]
    if rows:
        db.execute(
            pg_insert(FileChange).on_conflict_do_nothing(constraint='uq_file_changes_commit_file'),
            rows,
        )


def backfill_file_changes(repo_id: int, repo_path: str, db: Session, batch: int = 200) -> int:
    """
    Store file_changes for commits that have none recorded yet
    (commits.changes_recorded = false). Each batch commits atomically with the
    flag, so this is crash-safe and resumable too.
    """
    pending = (
        db.query(Commit.id, Commit.sha)
        .filter(Commit.repository_id == repo_id, Commit.changes_recorded.is_(False))
        .order_by(Commit.id)
        .all()
    )
    if not pending:
        return 0
    logger.info(f"Backfilling file_changes for {len(pending)} commits of repo {repo_id}")

    done = 0
    for i, (commit_id, sha) in enumerate(pending, 1):
        try:
            info = git_service.get_commit_changes(repo_path, sha)
            _store_file_changes(db, repo_id, commit_id, info)
        except Exception as e:
            # Commit no longer in git history (force-push): nothing to record.
            logger.warning(f"Could not read changes for {sha[:7]}: {redact_secrets(e)}")
        db.query(Commit).filter(Commit.id == commit_id).update(
            {Commit.changes_recorded: True}, synchronize_session=False)
        done += 1
        if i % batch == 0:
            db.commit()
    db.commit()
    return done


# Per-file features, recomputed from raw facts. Exact, not merged with old values.
_FILE_METRICS_SQL = text("""
WITH per_author AS (
  SELECT file_path, author_email, COUNT(*)::float AS n
  FROM file_changes WHERE repository_id = :repo
  GROUP BY file_path, author_email
),
totals AS (
  SELECT file_path, SUM(n) AS total, COUNT(*) AS authors
  FROM per_author GROUP BY file_path
),
entropy AS (
  SELECT a.file_path,
         GREATEST(-SUM((a.n / t.total) * (LN(a.n / t.total) / LN(2))), 0) AS ownership_entropy
  FROM per_author a JOIN totals t USING (file_path)
  GROUP BY a.file_path
),
agg AS (
  SELECT file_path,
         COUNT(DISTINCT commit_id)                              AS churn,
         COALESCE(SUM(lines_added), 0)                          AS lines_added,
         COALESCE(SUM(lines_deleted), 0)                        AS lines_deleted,
         EXTRACT(EPOCH FROM MAX(committed_at) - MIN(committed_at)) / 86400 AS file_age_days,
         COUNT(DISTINCT commit_id) FILTER (
           WHERE committed_at >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '90 days') AS recent_churn
  FROM file_changes WHERE repository_id = :repo
  GROUP BY file_path
)
SELECT agg.file_path, agg.churn, agg.lines_added, agg.lines_deleted,
       agg.file_age_days, agg.recent_churn,
       totals.authors AS author_count, entropy.ownership_entropy
FROM agg
JOIN totals  USING (file_path)
JOIN entropy USING (file_path)
""")

# Average complexity over the CURRENT functions only: the latest version of each
# function identity, dropped if that latest version is a deletion.
_CURRENT_COMPLEXITY_SQL = text("""
WITH latest AS (
  SELECT DISTINCT ON (COALESCE(f.canonical_id, f.file_path || ':' || COALESCE(f.qualified_name, f.name)))
         f.file_path, f.complexity, f.change_type
  FROM functions f JOIN commits c ON c.id = f.commit_id
  WHERE c.repository_id = :repo
  ORDER BY COALESCE(f.canonical_id, f.file_path || ':' || COALESCE(f.qualified_name, f.name)),
           c.timestamp DESC, c.id DESC, f.id DESC
)
SELECT file_path, AVG(complexity) AS avg_complexity
FROM latest
WHERE change_type IS DISTINCT FROM 'deleted'
GROUP BY file_path
""")


def recompute_file_metrics(db: Session, repo_id: int, head_files: dict) -> int:
    """
    Rebuild file_metrics for a repo from file_changes + current functions.

    ``head_files`` maps path -> dependency_count for files that exist at HEAD;
    files deleted since are excluded from risk scoring.
    """
    rows = db.execute(_FILE_METRICS_SQL, {'repo': repo_id}).mappings().all()
    complexity = {
        r.file_path: float(r.avg_complexity or 0.0)
        for r in db.execute(_CURRENT_COMPLEXITY_SQL, {'repo': repo_id}).all()
    }

    new_rows = []
    for r in rows:
        path = r['file_path']
        if path not in head_files:
            continue
        churn = int(r['churn'])
        age = max(float(r['file_age_days'] or 0.0), 0.0)
        new_rows.append({
            'repository_id':     repo_id,
            'file_path':         path,
            'churn':             churn,
            'lines_added':       int(r['lines_added']),
            'lines_deleted':     int(r['lines_deleted']),
            'file_age_days':     round(age, 1),
            'commit_frequency':  round(churn / max(age, 1), 4),
            'recent_churn':      int(r['recent_churn']),
            'author_count':      int(r['author_count']),
            'ownership_entropy': round(float(r['ownership_entropy']), 4),
            'dependency_count':  head_files.get(path, 0),
            'avg_complexity':    round(complexity.get(path, 0.0), 4),
        })

    # Replace atomically: stale rows (deleted/renamed files) disappear too.
    db.query(FileMetrics).filter(FileMetrics.repository_id == repo_id).delete(synchronize_session=False)
    if new_rows:
        db.bulk_insert_mappings(FileMetrics, new_rows)
    db.commit()
    logger.info(f"Stored FileMetrics for {len(new_rows)} files in repo {repo_id}")
    return len(new_rows)


def _handle_task(task_data: dict) -> None:
    """Run one decoded task on its own DB session."""
    if task_data.get('type') != 'clone_and_analyze':
        return
    db = SessionLocal()
    try:
        process_repository(task_data, db)  # False (duplicate) is fine: caller ACKs
    finally:
        db.close()


def main():
    logger.info("Miner worker starting...")

    r = redis.Redis(host='redis', port=6379, decode_responses=True)

    # Each container gets a unique consumer name so multiple workers can run
    CONSUMER_NAME = f'worker-{socket.gethostname()}'
    BLOCK_MS = 5_000    # block up to 5 s waiting for new messages

    # ── Ensure stream + consumer group exist ─────────────────────────────
    try:
        # MKSTREAM creates the stream if it doesn't exist yet
        r.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id='0', mkstream=True)
        logger.info(f"Created consumer group '{CONSUMER_GROUP}' on stream '{STREAM_NAME}'")
    except redis.exceptions.ResponseError as e:
        if 'BUSYGROUP' in str(e):
            logger.info(f"Consumer group '{CONSUMER_GROUP}' already exists — OK")
        else:
            raise

    def _process_message(msg_id: str, fields: dict):
        """Heartbeat + retry cap + DLQ + ACK handling live in queue_utils."""
        outcome = handle_message(
            r, msg_id, fields, CONSUMER_NAME,
            process_fn=_handle_task,
            mark_failed=mark_repo_failed,
            on_transient_error=mark_repo_retrying,
        )
        logger.info(f"Message {msg_id} outcome: {outcome}")

    while True:
        try:
            # ── 1. Reclaim messages from crashed workers ──────────────────
            # A healthy worker heartbeats its message (XCLAIM JUSTID), so only
            # a message with NO heartbeat for CLAIM_IDLE_MS (dead worker, or a
            # transient failure awaiting retry) is reclaimed here.
            try:
                claimed = r.xautoclaim(
                    STREAM_NAME, CONSUMER_GROUP, CONSUMER_NAME,
                    min_idle_time=CLAIM_IDLE_MS,
                    start_id='0-0',
                    count=10,
                )
                # xautoclaim returns (next_start_id, [(msg_id, fields), ...], [...deleted])
                reclaimed_messages = claimed[1] if claimed else []
                for msg_id, fields in reclaimed_messages:
                    if not fields:   # entry was trimmed from the stream
                        r.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
                        continue
                    logger.warning(f"Reclaiming orphaned message {msg_id} (no heartbeat for {CLAIM_IDLE_MS // 1000}s)")
                    _process_message(msg_id, fields)
            except redis.exceptions.ResponseError:
                # XAUTOCLAIM requires Redis 7.0+; silently skip on older versions
                pass

            # ── 2. Read new messages ──────────────────────────────────────
            # '>' means "give me messages nobody in this group has seen yet"
            results = r.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM_NAME: '>'},
                count=1,
                block=BLOCK_MS,
            )

            if results:
                for stream, messages in results:
                    for msg_id, fields in messages:
                        _process_message(msg_id, fields)
            else:
                # ── 3. Fallback: drain legacy task_queue list ─────────────
                # During rolling deploy the API may still push to the old list.
                # The legacy list has no PEL, so there is no retry: any failure is final.
                legacy = r.blpop('task_queue', timeout=1)
                if legacy:
                    task_data = None
                    try:
                        task_data = json.loads(legacy[1])
                        logger.info(f"Processing legacy list task: {task_data}")
                        _handle_task(task_data)
                    except Exception as e:
                        logger.error(f"Error processing legacy task: {e}")
                        if task_data:
                            mark_repo_failed(task_data.get('repository_id'), str(e))
                else:
                    logger.debug("No tasks — waiting...")

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
