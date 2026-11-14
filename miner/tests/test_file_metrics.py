"""
File-metrics correctness: raw facts per commit (file_changes) + exact SQL recompute.

Needs the real Postgres (run inside the miner container); skipped otherwise.
"""
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta

import git
import pytest
from sqlalchemy import text

from database import SessionLocal, engine
from models import Repository, Commit, Function, FileMetrics, FileChange
from services.git_service import GitService

worker = pytest.importorskip("worker")


@pytest.fixture
def db():
    try:
        s = SessionLocal()
        s.execute(text("SELECT 1 FROM file_changes LIMIT 1"))
        s.rollback()
    except Exception:
        pytest.skip("Postgres with migration 008 not reachable")
    created = []
    s.new_repo = lambda url=None: _new_repo(s, created, url)
    yield s
    s.rollback()
    for rid in created:
        s.execute(text("DELETE FROM file_changes WHERE repository_id=:r"), {"r": rid})
        s.execute(text("DELETE FROM functions WHERE commit_id IN (SELECT id FROM commits WHERE repository_id=:r)"), {"r": rid})
        s.execute(text("DELETE FROM commits WHERE repository_id=:r"), {"r": rid})
        s.execute(text("DELETE FROM file_metrics WHERE repository_id=:r"), {"r": rid})
        s.execute(text("DELETE FROM repositories WHERE id=:r"), {"r": rid})
        shutil.rmtree(os.path.join(os.getenv('STORAGE_PATH', '/storage'), f"repo_{rid}"), ignore_errors=True)
    s.commit()
    s.close()


def _new_repo(s, created, url=None):
    r = Repository(url=url or f"test://{uuid.uuid4()}", name="t", owner="t", status="queued")
    s.add(r)
    s.commit()
    created.append(r.id)
    return r


_seq = [0]


def add_change(db, repo, path, author, when=None, added=1, deleted=0):
    """One commit touching one file, authored by `author` (email)."""
    _seq[0] += 1
    c = Commit(repository_id=repo.id, sha=f"{_seq[0]:040x}", author=author,
               message="m", timestamp=when or datetime(2025, 1, 1), changes_recorded=True)
    db.add(c)
    db.flush()
    db.add(FileChange(repository_id=repo.id, commit_id=c.id, file_path=path,
                      author_email=author, committed_at=when or datetime(2025, 1, 1),
                      lines_added=added, lines_deleted=deleted))
    db.commit()
    return c


def metrics(db, repo):
    db.expire_all()
    return {m.file_path: m for m in db.query(FileMetrics).filter(FileMetrics.repository_id == repo.id)}


# ── pure parsing ─────────────────────────────────────────────────────────────

def test_parse_numstat_handles_binary_and_paths_with_spaces():
    raw = "3\t1\tsrc/a.py\x00-\t-\timg/logo.png\x0010\t0\tdir with space/b.go\x00"
    rows = GitService.parse_numstat(raw)
    assert rows == [
        {"file_path": "src/a.py", "lines_added": 3, "lines_deleted": 1},
        {"file_path": "img/logo.png", "lines_added": 0, "lines_deleted": 0},
        {"file_path": "dir with space/b.go", "lines_added": 10, "lines_deleted": 0},
    ]


# ── entropy ──────────────────────────────────────────────────────────────────

def test_entropy_is_0_1_2_bits_for_1_2_4_equal_authors(db):
    repo = db.new_repo()
    for _ in range(3):
        add_change(db, repo, "one.py", "a@x.com")
    for who in ("a@x.com", "b@x.com") * 2:
        add_change(db, repo, "two.py", who)
    for who in ("a@x.com", "b@x.com", "c@x.com", "d@x.com"):
        add_change(db, repo, "four.py", who)

    worker.recompute_file_metrics(db, repo.id, {"one.py": 0, "two.py": 0, "four.py": 0})
    m = metrics(db, repo)

    assert m["one.py"].ownership_entropy == 0 and m["one.py"].author_count == 1
    assert m["two.py"].ownership_entropy == pytest.approx(1.0, abs=1e-3) and m["two.py"].author_count == 2
    assert m["four.py"].ownership_entropy == pytest.approx(2.0, abs=1e-3) and m["four.py"].author_count == 4


def test_incremental_run_gives_full_history_entropy_not_max(db):
    repo = db.new_repo()
    for _ in range(50):
        add_change(db, repo, "f.py", "a@x.com")
    worker.recompute_file_metrics(db, repo.id, {"f.py": 0})
    assert metrics(db, repo)["f.py"].ownership_entropy == 0

    add_change(db, repo, "f.py", "b@x.com")              # author B, 1 commit, "incremental run"
    worker.recompute_file_metrics(db, repo.id, {"f.py": 0})

    m = metrics(db, repo)["f.py"]
    assert m.ownership_entropy == pytest.approx(0.139, abs=2e-3)   # H(50/51, 1/51); max() would say ~0
    assert m.churn == 51 and m.author_count == 2


# ── other metric rules ───────────────────────────────────────────────────────

def test_lines_age_recent_and_frequency(db):
    repo = db.new_repo()
    now = datetime.utcnow()
    add_change(db, repo, "f.py", "a@x.com", when=now - timedelta(days=200), added=10, deleted=2)
    add_change(db, repo, "f.py", "a@x.com", when=now - timedelta(days=10), added=5, deleted=1)
    worker.recompute_file_metrics(db, repo.id, {"f.py": 4})
    m = metrics(db, repo)["f.py"]
    assert (m.lines_added, m.lines_deleted) == (15, 3)
    assert m.file_age_days == pytest.approx(190, abs=0.1)
    assert m.recent_churn == 1 and m.churn == 2
    assert m.commit_frequency == pytest.approx(2 / 190, abs=1e-3)
    assert m.dependency_count == 4


def test_files_deleted_at_head_are_excluded_and_stale_rows_removed(db):
    repo = db.new_repo()
    add_change(db, repo, "kept.py", "a@x.com")
    add_change(db, repo, "gone.py", "a@x.com")
    worker.recompute_file_metrics(db, repo.id, {"kept.py": 0, "gone.py": 0})
    assert set(metrics(db, repo)) == {"kept.py", "gone.py"}
    worker.recompute_file_metrics(db, repo.id, {"kept.py": 0})      # gone.py deleted at HEAD
    assert set(metrics(db, repo)) == {"kept.py"}


def test_avg_complexity_uses_only_current_function_versions(db):
    repo = db.new_repo()
    c1 = add_change(db, repo, "f.py", "a@x.com", when=datetime(2025, 1, 1))
    c2 = add_change(db, repo, "f.py", "a@x.com", when=datetime(2025, 2, 1))
    c3 = add_change(db, repo, "f.py", "a@x.com", when=datetime(2025, 3, 1))

    def fn(commit, cid, cx, change="edit"):
        db.add(Function(commit_id=commit.id, name=cid, qualified_name=cid, file_path="f.py",
                        start_line=1, end_line=2, complexity=cx, canonical_id=cid, change_type=change,
                        body_hash=uuid.uuid4().hex[:16]))

    fn(c1, "keep", 2, "new"); fn(c2, "keep", 10)          # history 2 -> 10: only 10 counts
    fn(c1, "gone", 40, "new"); fn(c3, "gone", 40, "deleted")   # deleted: excluded entirely
    db.commit()

    worker.recompute_file_metrics(db, repo.id, {"f.py": 0})
    assert metrics(db, repo)["f.py"].avg_complexity == pytest.approx(10.0)   # old code: (2+10+40+40)/4


# ── git-backed: authors, mailmap, merges ─────────────────────────────────────

def _git_repo(commits, mailmap=None):
    """commits: list of (name, email, {path: content}). Returns repo dir."""
    d = tempfile.mkdtemp()
    r = git.Repo.init(d)
    if mailmap:
        open(os.path.join(d, ".mailmap"), "w").write(mailmap)
        r.index.add([".mailmap"])
    for i, (name, email, files) in enumerate(commits):
        for p, body in files.items():
            os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True)
            open(os.path.join(d, p), "w").write(body)
            r.index.add([p])
        actor = git.Actor(name, email)
        r.index.commit(f"c{i}", author=actor, committer=actor)
    return d


def test_mailmap_merges_one_person_with_two_identities():
    d = _git_repo(
        [("Alice", "alice@x.com", {"a.py": "x=1\n"}),
         ("Alice Work", "ALICE.WORK@y.com", {"a.py": "x=2\n"})],
        mailmap="Alice <alice@x.com> <alice.work@y.com>\n",
    )
    try:
        commits = GitService(tempfile.mkdtemp()).get_new_commits(d)
        assert {c["author_email"] for c in commits} == {"alice@x.com"}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_email_is_lowercased_without_mailmap():
    d = _git_repo([("Bob", "Bob@X.com", {"a.py": "x=1\n"})])
    try:
        assert GitService(tempfile.mkdtemp()).get_new_commits(d)[0]["author_email"] == "bob@x.com"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_file_changes_per_commit_include_root_commit_and_line_counts():
    d = _git_repo([("A", "a@x.com", {"a.py": "1\n2\n3\n"}), ("A", "a@x.com", {"a.py": "1\n2\n3\n4\n"})])
    try:
        c = GitService(tempfile.mkdtemp()).get_new_commits(d)
        assert c[0]["file_changes"] == [{"file_path": "a.py", "lines_added": 3, "lines_deleted": 0}]
        assert c[1]["file_changes"] == [{"file_path": "a.py", "lines_added": 1, "lines_deleted": 0}]
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ── crash + resume == clean run ──────────────────────────────────────────────

def _snapshot(db, repo):
    return {
        p: (m.churn, m.lines_added, m.lines_deleted, m.author_count,
            round(m.ownership_entropy, 4), m.recent_churn, m.file_age_days, round(m.avg_complexity, 4))
        for p, m in metrics(db, repo).items()
    }


def test_crash_midway_then_resume_matches_clean_run(db, monkeypatch):
    authors = [("A", "a@x.com"), ("B", "b@x.com"), ("A", "a@x.com"), ("C", "c@x.com")]
    commits = []
    for i in range(20):
        n, e = authors[i % len(authors)]
        commits.append((n, e, {f"f{i % 3}.py": "".join(f"def g{j}():\n    return {j}\n" for j in range(i + 1))}))
    d = _git_repo(commits)

    # The task's url (what gets cloned) is independent of the DB row's unique url.
    clean = db.new_repo()
    crashy = db.new_repo()

    try:
        # --- clean run ---------------------------------------------------
        worker._run_pipeline({"repository_id": clean.id, "url": d}, SessionLocal())

        # --- crash after 9 commits --------------------------------------
        real_index = worker._index_commit
        calls = {"n": 0}

        def crashing(*a, **k):
            if calls["n"] >= 9:
                raise RuntimeError("simulated worker crash")
            calls["n"] += 1
            return real_index(*a, **k)

        monkeypatch.setattr(worker, "_index_commit", crashing)
        with pytest.raises(RuntimeError):
            worker._run_pipeline({"repository_id": crashy.id, "url": d}, SessionLocal())
        monkeypatch.setattr(worker, "_index_commit", real_index)

        db.expire_all()
        assert db.query(Commit).filter(Commit.repository_id == crashy.id).count() == 9   # checkpointed atomically
        assert db.query(FileChange).filter(FileChange.repository_id == crashy.id).count() == 9

        # --- resume -------------------------------------------------------
        worker._run_pipeline({"repository_id": crashy.id, "url": d}, SessionLocal())

        assert _snapshot(db, crashy) == _snapshot(db, clean)
        assert _snapshot(db, clean), "expected metrics rows"
        assert db.query(FileChange).filter(FileChange.repository_id == crashy.id).count() == 20
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_backfill_fills_commits_recorded_before_file_changes_existed(db):
    commits = [("A", "a@x.com", {"a.py": "x=1\n"}), ("B", "b@x.com", {"a.py": "x=2\n"})]
    d = _git_repo(commits)
    try:
        repo = db.new_repo(url=d)
        # simulate an old run: commits exist, changes_recorded = false, no file_changes
        for c in GitService(tempfile.mkdtemp()).get_new_commits(d):
            db.add(Commit(repository_id=repo.id, sha=c["sha"], author=c["author"], message=c["message"],
                          timestamp=c["timestamp"], changes_recorded=False))
        db.commit()

        n = worker.backfill_file_changes(repo.id, d, db)
        assert n == 2
        assert db.query(FileChange).filter(FileChange.repository_id == repo.id).count() == 2
        assert worker.backfill_file_changes(repo.id, d, db) == 0     # idempotent

        worker.recompute_file_metrics(db, repo.id, {"a.py": 0})
        m = metrics(db, repo)["a.py"]
        assert m.churn == 2 and m.author_count == 2 and m.ownership_entropy == pytest.approx(1.0, abs=1e-3)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ── loc (non-blank lines at HEAD) ────────────────────────────────────────────

def test_count_loc_ignores_blank_and_whitespace_only_lines_and_binary():
    assert GitService.count_loc(b"a\n\n  \n\t\nb\nc") == 3
    assert GitService.count_loc(b"") == 0
    assert GitService.count_loc(b"\x89PNG\x00\x01binary\n") == 0


def test_head_files_report_loc_matching_grep_cv_blank_lines():
    d = _git_repo([("A", "a@x.com", {"gateway.go": "package x\n\nfunc a() {}\n   \nfunc b() {}\n"})])
    try:
        head = GitService(tempfile.mkdtemp()).get_head_files(d)
        assert head["gateway.go"]["loc"] == 3
        # same definition as: grep -cv '^\s*$' gateway.go
        assert head["gateway.go"]["loc"] == sum(
            1 for l in open(os.path.join(d, "gateway.go")) if l.strip())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_recompute_stores_loc_from_head_files(db):
    repo = db.new_repo()
    add_change(db, repo, "f.py", "a@x.com")
    add_change(db, repo, "f.py", "a@x.com")
    worker.recompute_file_metrics(db, repo.id, {"f.py": {"dependency_count": 2, "loc": 762}})
    m = metrics(db, repo)["f.py"]
    assert (m.loc, m.dependency_count, m.churn) == (762, 2, 2)
