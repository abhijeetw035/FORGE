import time
import redis
import logging
import json
import os
import socket
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal, engine
from models import Repository, Commit, Function, FileMetrics
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
            # Idempotent insert: unique (repository_id, sha) + ON CONFLICT DO NOTHING.
            # If the commit already exists (duplicate run), skip it.
            commit_id = db.execute(
                pg_insert(Commit)
                .values(
                    repository_id=repo_id,
                    sha=commit_data['sha'],
                    author=commit_data['author'],
                    message=commit_data['message'],
                    timestamp=commit_data['timestamp'],
                    processed=False,
                )
                .on_conflict_do_nothing(constraint='uq_commits_repository_sha')
                .returning(Commit.id)
            ).scalar()

            if commit_id is not None:
                commit = db.get(Commit, commit_id)

                # Only parse the files that actually changed in this commit
                process_commit_ast(commit, repo_path, db,
                                   changed_files=commit_data.get('changed_files'),
                                   identity_tracker=identity_tracker)

                # Checkpoint: record this SHA so a future re-queue only
                # processes commits that come after it.
                repo.last_indexed_sha = commit_data['sha']
                db.commit()

        db.commit()

        logger.info(f"Computing rich file metrics for repo {repo_id}...")
        try:
            # Pass since_sha so only the delta commits are walked for metrics
            compute_and_store_file_metrics(repo_id, repo_path, db, since_sha=since_sha)
        except Exception as metric_err:
            db.rollback()
            logger.warning(f"File-metrics computation failed (non-fatal): {metric_err}")

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


def compute_and_store_file_metrics(repo_id: int, repo_path: str, db: Session,
                                   since_sha: str = None):
    """
    Compute rich per-file metrics via GitService and store/update FileMetrics rows.

    When ``since_sha`` is provided (incremental run) only the new commits are
    walked and their deltas are ADDED to existing FileMetrics rows.  On a
    first run (since_sha=None) a full walk is done and rows are created fresh.
    """
    from sqlalchemy import func as sqlfunc, or_

    incremental = since_sha is not None

    # 1. Get git-history metrics (full or delta)
    metrics_list = git_service.get_file_metrics(repo_path, since_sha=since_sha)

    # 2. Compute avg_complexity per file from stored Function records
    complexity_rows = (
        db.query(
            Function.file_path,
            sqlfunc.avg(Function.complexity).label('avg_complexity')
        )
        .join(Commit, Function.commit_id == Commit.id)
        .filter(
            Commit.repository_id == repo_id,
            or_(Function.change_type.is_(None), Function.change_type != 'deleted')
        )
        .group_by(Function.file_path)
        .all()
    )
    complexity_map = {row.file_path: float(row.avg_complexity or 0) for row in complexity_rows}

    for m in metrics_list:
        path = m['file_path']
        existing = (
            db.query(FileMetrics)
            .filter(FileMetrics.repository_id == repo_id, FileMetrics.file_path == path)
            .first()
        )

        if existing and incremental:
            # Merge delta into existing row
            existing.churn            += m['churn']
            existing.lines_added      += m['lines_added']
            existing.lines_deleted    += m['lines_deleted']
            existing.recent_churn      = m['recent_churn']   # recalculated from HEAD
            # author_count and ownership_entropy are tricky to merge cheaply;
            # update them only if the new value is higher (conservative upper-bound)
            existing.author_count      = max(existing.author_count or 0, m['author_count'])
            existing.ownership_entropy = max(existing.ownership_entropy or 0.0, m['ownership_entropy'])
            existing.dependency_count  = m['dependency_count']   # always from HEAD
            existing.avg_complexity    = complexity_map.get(path, existing.avg_complexity or 0.0)
            # Recalculate file_age_days from stored first_ts + current time, or keep max
            existing.file_age_days     = max(existing.file_age_days or 0.0, m['file_age_days'])
            existing.commit_frequency  = round(
                existing.churn / max(existing.file_age_days, 1), 4
            )
        else:
            # Full write (first run or new file)
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
    mode = "incremental" if incremental else "full"
    logger.info(f"Stored FileMetrics ({mode}) for {len(metrics_list)} files in repo {repo_id}")


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
