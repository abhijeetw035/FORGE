"""
Queue reliability helpers for the miner worker.

Four mechanisms work together (see docs in worker.py):

1. Heartbeat           - keep resetting a message's idle time while it is being
                         worked on, so a healthy long job is never reclaimed.
2. Retry cap + DLQ     - a job delivered more than MAX_DELIVERIES times goes to
                         a dead-letter stream and the repo is marked failed.
3. Per-repo lock       - a Postgres advisory lock so two workers can never
                         process the same repo at once.
4. Idempotent writes   - unique constraints + ON CONFLICT DO NOTHING (worker.py,
                         migration 007).

Delivery is still at-least-once; "exactly-once effect" comes from (3) + (4).
"""
import json
import logging
import os
import re
import threading
from contextlib import contextmanager
from typing import Callable, Optional

logger = logging.getLogger(__name__)

STREAM_NAME = 'forge:tasks'
CONSUMER_GROUP = 'miner-workers'
DLQ_STREAM = 'forge:tasks:dlq'

# Reclaim a message only if NO heartbeat was seen for this long (crashed worker).
CLAIM_IDLE_MS = 5 * 60_000
# Heartbeat interval; must be far below CLAIM_IDLE_MS.
HEARTBEAT_SEC = 30
# A job may be delivered at most this many times before it is dead-lettered.
MAX_DELIVERIES = 3

# First int of the two-int advisory-lock key (second int = repository id), so
# our locks cannot collide with advisory locks used for anything else.
REPO_LOCK_NAMESPACE = 0x46524745  # "FRGE"


# ── Secret redaction ─────────────────────────────────────────────────────────
# git error messages embed the clone URL, which contains the GitHub token.
# Never let that reach the DB (failed_reason is shown in the UI) or the logs.
_URL_CREDS = re.compile(r'(://)[^/@\s]+@')
_TOKEN_LIKE = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b')


def redact_secrets(text) -> str:
    text = _URL_CREDS.sub(r'\1***@', str(text))
    text = _TOKEN_LIKE.sub('***', text)
    token = os.getenv('GITHUB_TOKEN')
    if token:
        text = text.replace(token, '***')
    return text


class _RedactingFormatter(logging.Formatter):
    def format(self, record):
        return redact_secrets(super().format(record))   # includes tracebacks


def install_log_redaction() -> None:
    """Wrap every root handler's formatter so no log line can leak credentials."""
    for h in logging.getLogger().handlers:
        fmt = h.formatter or logging.Formatter(logging.BASIC_FORMAT)
        h.setFormatter(_RedactingFormatter(fmt._fmt, fmt.datefmt))


class PermanentError(Exception):
    """A failure retrying cannot fix (bad URL, repo not found, auth failure)."""


# ── 1. Heartbeat ─────────────────────────────────────────────────────────────

def start_heartbeat(r, msg_id: str, consumer: str, stop: threading.Event,
                    interval: float = HEARTBEAT_SEC,
                    stream: str = STREAM_NAME, group: str = CONSUMER_GROUP) -> threading.Thread:
    """
    Periodically XCLAIM the message back to the SAME consumer with JUSTID.
    That resets its idle time without incrementing the delivery counter.
    If the process dies the thread dies with it, so crash recovery still works.
    """
    def beat():
        while not stop.wait(interval):
            try:
                r.xclaim(stream, group, consumer, min_idle_time=0,
                         message_ids=[msg_id], justid=True)
            except Exception as e:  # never let a Redis blip kill the job
                logger.warning(f"Heartbeat for {msg_id} failed: {e}")

    t = threading.Thread(target=beat, name=f"heartbeat-{msg_id}", daemon=True)
    t.start()
    return t


# ── 2. Retry cap / DLQ ───────────────────────────────────────────────────────

def delivery_count(r, msg_id: str, stream: str = STREAM_NAME, group: str = CONSUMER_GROUP) -> int:
    info = r.xpending_range(stream, group, min=msg_id, max=msg_id, count=1)
    return int(info[0]["times_delivered"]) if info else 1


def handle_message(
    r,
    msg_id: str,
    fields: dict,
    consumer: str,
    process_fn: Callable[[dict], None],
    mark_failed: Callable[[Optional[int], str], None],
    on_transient_error: Optional[Callable[[dict, Exception], None]] = None,
    heartbeat_sec: float = HEARTBEAT_SEC,
    max_deliveries: int = MAX_DELIVERIES,
) -> str:
    """
    Process one stream message. Returns one of:
      'done'       processed (or skipped as duplicate) and ACKed
      'dlq'        exceeded max deliveries -> dead-lettered, repo failed, ACKed
      'permanent'  PermanentError / bad payload -> repo failed, ACKed
      'retry'      transient error -> NOT ACKed, will be reclaimed after idle
    """
    try:
        task = json.loads(fields['payload'])
    except Exception as e:
        logger.error(f"Message {msg_id} has an unreadable payload: {e}")
        r.xadd(DLQ_STREAM, {"payload": str(fields.get('payload', '')), "reason": "bad_payload"})
        r.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
        return 'permanent'

    repo_id = task.get("repository_id")

    if delivery_count(r, msg_id) > max_deliveries:
        logger.error(f"Task {msg_id} (repo {repo_id}) exceeded {max_deliveries} deliveries; dead-lettering")
        r.xadd(DLQ_STREAM, {"payload": json.dumps(task), "reason": "max_deliveries"})
        mark_failed(repo_id, f"Failed after {max_deliveries} attempts")
        r.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
        return 'dlq'

    stop = threading.Event()
    start_heartbeat(r, msg_id, consumer, stop, interval=heartbeat_sec)
    try:
        logger.info(f"Processing task (stream id={msg_id}): {task}")
        process_fn(task)
        r.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
        return 'done'
    except PermanentError as e:
        logger.error(f"Permanent failure for repo {repo_id}: {e}")
        mark_failed(repo_id, redact_secrets(e))
        r.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)  # retrying won't help
        return 'permanent'
    except Exception as e:
        logger.exception(f"Transient failure for repo {repo_id}; will retry")
        if on_transient_error:
            try:
                on_transient_error(task, e)
            except Exception:
                logger.exception("on_transient_error hook failed")
        return 'retry'  # no ACK -> reclaimed after CLAIM_IDLE_MS, counted as a delivery
    finally:
        stop.set()


# ── 3. Per-repo lock ─────────────────────────────────────────────────────────

@contextmanager
def repo_lock(engine, repo_id: int):
    """
    Postgres session-level advisory lock on a DEDICATED connection.

    It must not be the work Session's connection: a Session returns its
    connection to the pool on every commit(), which would silently move or
    leak the lock. This connection is held, idle, for the whole job; if the
    worker dies the connection closes and Postgres releases the lock itself.

    Yields True if acquired, False if another worker holds it.
    """
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    acquired = False
    try:
        acquired = bool(conn.exec_driver_sql(
            "SELECT pg_try_advisory_lock(%s, %s)", (REPO_LOCK_NAMESPACE, int(repo_id))
        ).scalar())
        yield acquired
    finally:
        try:
            if acquired:
                conn.exec_driver_sql(
                    "SELECT pg_advisory_unlock(%s, %s)", (REPO_LOCK_NAMESPACE, int(repo_id))
                )
        finally:
            conn.close()
