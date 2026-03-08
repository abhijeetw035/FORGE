import time
import redis
import logging
import json
import os
import socket
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

        # ── incremental indexing ──────────────────────────────────────────
        # If this repo was analysed before, last_indexed_sha holds the HEAD
        # SHA from that run.  We ask git for ONLY the commits that arrived
        # since then (git log <sha>..HEAD).  On first run since_sha is None
        # so we fall back to the full history walk.
        since_sha = repo.last_indexed_sha
        commits_data = git_service.get_new_commits(repo_path, since_sha=since_sha)

        if since_sha:
            logger.info(f"Incremental run: {len(commits_data)} new commits since {since_sha[:7]}")
        else:
            logger.info(f"First run: {len(commits_data)} commits to index")
        
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
                
                # Only parse the files that actually changed in this commit
                process_commit_ast(commit, repo_path, db,
                                   changed_files=commit_data.get('changed_files'))

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
            logger.warning(f"File-metrics computation failed (non-fatal): {metric_err}")

        repo.status = "completed"
        db.commit()
        
        logger.info(f"Repository {repo_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing repository {repo_id}: {e}")
        repo.status = "failed"
        db.commit()

def process_commit_ast(commit: Commit, repo_path: str, db: Session,
                       changed_files: list = None):
    """
    Parse functions from a single commit.

    ``changed_files`` — list of file paths that were actually modified in
    this commit (from git diff-tree).  When supplied we only parse those
    files, which is O(changed files) instead of O(all files in tree).
    Falls back to full tree traversal when None (legacy path / root commit).
    """
    try:
        import git as gitpython
        repo = gitpython.Repo(repo_path)
        commit_obj = repo.commit(commit.sha)

        # Build the set of files to parse
        PARSEABLE_EXTS = {'.py', '.js', '.java', '.go'}

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

        for file_path, blob in blobs:
            try:
                source_code = blob.data_stream.read().decode('utf-8')
                tree = ast_parser.parse_file(source_code, file_path)
                
                if tree:
                    _, ext = os.path.splitext(file_path)
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


def compute_and_store_file_metrics(repo_id: int, repo_path: str, db: Session,
                                   since_sha: str = None):
    """
    Compute rich per-file metrics via GitService and store/update FileMetrics rows.

    When ``since_sha`` is provided (incremental run) only the new commits are
    walked and their deltas are ADDED to existing FileMetrics rows.  On a
    first run (since_sha=None) a full walk is done and rows are created fresh.
    """
    from sqlalchemy import func as sqlfunc

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
        .filter(Commit.repository_id == repo_id)
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


def main():
    logger.info("Miner worker starting...")

    r = redis.Redis(host='redis', port=6379, decode_responses=True)

    # ── Redis Stream constants ────────────────────────────────────────────
    STREAM_NAME    = 'forge:tasks'
    CONSUMER_GROUP = 'miner-workers'
    # Each container gets a unique consumer name so multiple workers can run
    CONSUMER_NAME  = f'worker-{socket.gethostname()}'
    # Messages idle for longer than this are reclaimed from crashed workers (ms)
    CLAIM_IDLE_MS  = 60_000   # 60 seconds
    BLOCK_MS       = 5_000    # block up to 5 s waiting for new messages

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
        """Deserialise and process one stream message, then ACK it."""
        try:
            task_data = json.loads(fields['payload'])
            logger.info(f"Processing task (stream id={msg_id}): {task_data}")

            db = SessionLocal()
            try:
                if task_data['type'] == 'clone_and_analyze':
                    process_repository(task_data, db)
            finally:
                db.close()

            # ACK only after successful processing — message stays in the
            # PEL (Pending Entries List) until this line runs.
            r.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
            logger.debug(f"ACKed message {msg_id}")

        except Exception as e:
            logger.error(f"Error processing message {msg_id}: {e}")
            # Do NOT ack — message stays in PEL and will be reclaimed after
            # CLAIM_IDLE_MS by the next XAUTOCLAIM call.

    while True:
        try:
            # ── 1. Reclaim messages from crashed workers ──────────────────
            # XAUTOCLAIM transfers any PEL messages idle > CLAIM_IDLE_MS to
            # this worker.  This is the crash-safety guarantee: if a previous
            # worker popped a job and died before ACKing, we pick it up here.
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
                    logger.warning(f"Reclaiming orphaned message {msg_id} from crashed worker")
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
                legacy = r.blpop('task_queue', timeout=1)
                if legacy:
                    try:
                        task_data = json.loads(legacy[1])
                        logger.info(f"Processing legacy list task: {task_data}")
                        db = SessionLocal()
                        try:
                            if task_data['type'] == 'clone_and_analyze':
                                process_repository(task_data, db)
                        finally:
                            db.close()
                    except Exception as e:
                        logger.error(f"Error processing legacy task: {e}")
                else:
                    logger.debug("No tasks — waiting...")

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
