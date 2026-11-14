"""
Queue reliability tests: DLQ + retry cap, permanent errors, per-repo lock,
heartbeat.  The Redis tests use an in-memory fake that models just enough of
Streams (PEL idle time, delivery counts, XCLAIM JUSTID) to run anywhere; the
lock test uses the real Postgres and is skipped if it is unreachable.
"""
import json
import threading
import time

import pytest

import queue_utils
from queue_utils import PermanentError, handle_message, start_heartbeat, delivery_count


class FakeRedis:
    """Minimal Redis Streams PEL model."""

    def __init__(self):
        self.pending = {}      # msg_id -> {"consumer", "last_delivery", "times_delivered"}
        self.acked = []
        self.streams = {}      # stream -> [fields]
        self.claims = []

    def add_pending(self, msg_id, consumer="c1", times_delivered=1):
        self.pending[msg_id] = {"consumer": consumer, "last_delivery": time.monotonic(),
                                "times_delivered": times_delivered}

    def idle_ms(self, msg_id):
        return (time.monotonic() - self.pending[msg_id]["last_delivery"]) * 1000

    # redis-py compatible surface -------------------------------------------
    def xpending_range(self, stream, group, min, max, count):
        e = self.pending.get(min)
        return [{"message_id": min, "times_delivered": e["times_delivered"]}] if e else []

    def xadd(self, stream, fields):
        self.streams.setdefault(stream, []).append(fields)

    def xack(self, stream, group, msg_id):
        self.acked.append(msg_id)
        self.pending.pop(msg_id, None)

    def xclaim(self, stream, group, consumer, min_idle_time, message_ids, justid=False, **kw):
        self.claims.append((consumer, tuple(message_ids), justid))
        for mid in message_ids:
            e = self.pending.get(mid)
            if e and self.idle_ms(mid) >= min_idle_time:
                e["last_delivery"] = time.monotonic()      # idle time reset
                e["consumer"] = consumer
                if not justid:
                    e["times_delivered"] += 1               # JUSTID must NOT count a delivery
        return list(message_ids)


def _fields(repo_id=1):
    return {"payload": json.dumps({"type": "clone_and_analyze", "repository_id": repo_id, "url": "u"})}


def test_over_max_deliveries_goes_to_dlq_marks_failed_and_acks():
    r = FakeRedis()
    r.add_pending("1-0", times_delivered=queue_utils.MAX_DELIVERIES + 1)
    processed, failed = [], []

    out = handle_message(r, "1-0", _fields(7), "c1",
                         process_fn=processed.append,
                         mark_failed=lambda rid, why: failed.append((rid, why)))

    assert out == 'dlq'
    assert processed == []                                   # never run again
    assert failed == [(7, "Failed after 3 attempts")]
    assert "1-0" in r.acked
    assert r.streams[queue_utils.DLQ_STREAM][0]["reason"] == "max_deliveries"


def test_third_delivery_is_still_processed():
    r = FakeRedis()
    r.add_pending("1-0", times_delivered=queue_utils.MAX_DELIVERIES)
    processed = []
    out = handle_message(r, "1-0", _fields(), "c1", process_fn=processed.append,
                         mark_failed=lambda *a: None)
    assert out == 'done' and len(processed) == 1 and "1-0" in r.acked


def test_permanent_error_fails_immediately_and_acks():
    r = FakeRedis()
    r.add_pending("1-0", times_delivered=1)
    failed = []

    def boom(task):
        raise PermanentError("Could not clone repository: repository not found")

    out = handle_message(r, "1-0", _fields(9), "c1", process_fn=boom,
                         mark_failed=lambda rid, why: failed.append((rid, why)))

    assert out == 'permanent'
    assert failed == [(9, "Could not clone repository: repository not found")]
    assert "1-0" in r.acked                                  # no retries


def test_transient_error_is_not_acked():
    r = FakeRedis()
    r.add_pending("1-0", times_delivered=1)
    hooked = []

    def boom(task):
        raise RuntimeError("network blip")

    out = handle_message(r, "1-0", _fields(), "c1", process_fn=boom,
                         mark_failed=lambda *a: pytest.fail("must not fail yet"),
                         on_transient_error=lambda t, e: hooked.append(str(e)))

    assert out == 'retry'
    assert "1-0" not in r.acked and "1-0" in r.pending       # stays in PEL for retry
    assert hooked == ["network blip"]


def test_unreadable_payload_is_dead_lettered_and_acked():
    r = FakeRedis()
    r.add_pending("1-0")
    out = handle_message(r, "1-0", {"payload": "{not json"}, "c1",
                         process_fn=lambda t: pytest.fail("no"), mark_failed=lambda *a: None)
    assert out == 'permanent' and "1-0" in r.acked
    assert r.streams[queue_utils.DLQ_STREAM][0]["reason"] == "bad_payload"


def test_heartbeat_keeps_idle_time_below_threshold_without_counting_deliveries():
    r = FakeRedis()
    r.add_pending("1-0", consumer="c1", times_delivered=1)
    threshold_ms = 200                                       # stand-in for CLAIM_IDLE_MS
    max_idle_seen = 0.0

    def slow_job(task):
        nonlocal max_idle_seen
        for _ in range(12):                                  # ~0.6 s >> threshold
            time.sleep(0.05)
            max_idle_seen = max(max_idle_seen, r.idle_ms("1-0"))

    out = handle_message(r, "1-0", _fields(), "c1", process_fn=slow_job,
                         mark_failed=lambda *a: None, heartbeat_sec=0.05)

    assert out == 'done'
    assert max_idle_seen < threshold_ms, f"idle reached {max_idle_seen:.0f}ms; heartbeat not working"
    assert r.claims and all(c[0] == "c1" and c[2] is True for c in r.claims)   # same consumer, JUSTID
    assert delivery_count(r, "1-0") == 1 or "1-0" not in r.pending            # no extra deliveries


def test_heartbeat_thread_stops():
    r = FakeRedis()
    r.add_pending("1-0")
    stop = threading.Event()
    t = start_heartbeat(r, "1-0", "c1", stop, interval=0.01)
    stop.set()
    t.join(timeout=1)
    assert not t.is_alive()


# ── per-repo lock ────────────────────────────────────────────────────────────

def test_process_repository_skips_when_lock_is_held(monkeypatch):
    """Lock not acquired -> pipeline never runs (so nothing is written)."""
    worker = pytest.importorskip("worker")
    from contextlib import contextmanager

    @contextmanager
    def never_acquired(engine, repo_id):
        yield False

    monkeypatch.setattr(worker, "repo_lock", never_acquired)
    monkeypatch.setattr(worker, "_run_pipeline",
                        lambda *a, **k: pytest.fail("pipeline must not run without the lock"))

    assert worker.process_repository({"repository_id": 1, "url": "u"}, db=None) is False


def test_real_advisory_lock_is_exclusive_and_released():
    from sqlalchemy import text
    from database import engine
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Postgres not reachable")

    repo_id = 987654
    with queue_utils.repo_lock(engine, repo_id) as first:
        assert first is True
        with queue_utils.repo_lock(engine, repo_id) as second:
            assert second is False                           # second worker is locked out
        with queue_utils.repo_lock(engine, repo_id + 1) as other:
            assert other is True                             # other repos unaffected
    with queue_utils.repo_lock(engine, repo_id) as again:
        assert again is True                                 # released after the job


# ── secrets + error classification ───────────────────────────────────────────

def test_redact_secrets_strips_url_credentials_and_tokens():
    msg = ("fatal: could not read Password for "
           "'https://ghp_abcdefghijklmnopqrstuvwxyz0123456789@github.com': No such device")
    out = queue_utils.redact_secrets(msg)
    assert "ghp_" not in out and "https://***@github.com" in out
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in queue_utils.redact_secrets(
        "token ghp_abcdefghijklmnopqrstuvwxyz0123456789 leaked")


def test_missing_repo_with_token_is_permanent_and_redacted():
    worker = pytest.importorskip("worker")
    err = Exception("Cmd('git') failed: fatal: could not read Password for "
                    "'https://ghp_abcdefghijklmnopqrstuvwxyz0123456789@github.com': No such device or address")
    out = worker.classify_clone_error(err)
    assert isinstance(out, PermanentError)
    assert "ghp_" not in str(out)


def test_network_errors_stay_transient():
    worker = pytest.importorskip("worker")
    err = Exception("fatal: unable to access 'https://github.com/x/y/': Could not resolve host: github.com")
    assert worker.classify_clone_error(err) is err
