"""
git must never wait for a human, never hang, and never be handed attacker-controlled options.

Most tests run a STUB `git` executable, so they exercise our real subprocess handling
(env, argv, timeout, kill, error mapping) without a network. The last two tests run real
git against GitHub and are skipped when it is unreachable: they exist because a mocked
clone once hid a bug that broke every new clone.
"""
import os
import socket
import stat
import subprocess
import tempfile
import time

import pytest

import services.git_service as gs
from services.git_service import GitService, GitCommandFailed, GitTimeout


@pytest.fixture
def stub_git(tmp_path, monkeypatch):
    """Put a fake `git` first on PATH. Returns a function to set its script body."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    record = tmp_path / "record.txt"

    def install(body):
        script = bindir / "git"
        script.write_text("#!/bin/sh\n"
                          f'echo "ARGS: $*" >> "{record}"\n'
                          f'echo "PROMPT=$GIT_TERMINAL_PROMPT ASKPASS=$GIT_ASKPASS PROTO=$GIT_ALLOW_PROTOCOL" >> "{record}"\n'
                          + body + "\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
        return record
    return install


def svc(strict=True, token=None):
    return GitService(tempfile.mkdtemp(), github_token=token, strict=strict)


# ── no prompts, restricted protocols ─────────────────────────────────────────

def test_git_never_prompts_and_is_restricted_to_https(stub_git):
    record = stub_git("mkdir -p \"$(eval echo \\${$#})\"")           # pretend to clone into the last arg
    svc().clone_repository("https://github.com/a/b", 1)
    text = record.read_text()
    assert "PROMPT=0" in text
    assert "ASKPASS=" in text and "ASKPASS=\n" not in text and "/true" in text   # askpass answers instantly
    assert "PROTO=https" in text
    argv = text.splitlines()[0]
    assert "-c protocol.file.allow=never" in argv and "-c http.followRedirects=false" in argv
    assert argv.index("-c") < argv.index("clone") < argv.index("--") < argv.index("https://github.com/a/b")


def test_non_strict_mode_still_never_prompts_but_does_not_restrict_protocol(stub_git):
    record = stub_git("mkdir -p \"$(eval echo \\${$#})\"")
    svc(strict=False).clone_repository("/some/local/path", 1)
    text = record.read_text()
    assert "PROMPT=0" in text and "PROTO=\n" in text or "PROTO= " in text or text.rstrip().endswith("PROTO=")
    assert "protocol.file.allow" not in text.splitlines()[0]


# ── a hung git must end (and take its children with it) ──────────────────────

def test_hung_clone_is_killed_after_the_timeout_and_its_children_too(stub_git):
    stub_git("sleep 31")                                            # waits "for a password" forever
    s = svc()
    t = time.time()
    with pytest.raises(GitTimeout):
        s._run_git(["clone", "--", "https://github.com/a/b", os.path.join(s.storage_path, "x")], timeout=1)
    assert time.time() - t < 10
    time.sleep(0.3)
    if os.path.isdir("/proc"):                                       # Linux (the container); no pgrep needed
        alive = []
        for pid in filter(str.isdigit, os.listdir("/proc")):
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    if b"sleep\x0031" in f.read() and open(f"/proc/{pid}/stat").read().split()[2] != "Z":
                        alive.append(pid)
            except OSError:
                pass
        assert alive == [], f"child of the killed git is still running: {alive}"


def test_default_timeout_is_ten_minutes():
    assert gs.GIT_NETWORK_TIMEOUT_SEC == 600


# ── failure handling ─────────────────────────────────────────────────────────

def test_missing_repo_fails_fast_is_permanent_and_leaves_no_half_clone(stub_git):
    stub_git("echo \"fatal: could not read Password for 'https://TOKEN123@github.com': terminal prompts disabled\" >&2; exit 128")
    s = svc(token="TOKEN123")
    with pytest.raises(GitCommandFailed) as ei:
        s.clone_repository("https://github.com/a/does-not-exist-xyz", 232)
    assert "exit 128" in str(ei.value)
    assert not os.path.exists(os.path.join(s.storage_path, "repo_232"))

    worker = pytest.importorskip("worker")
    out = worker.classify_clone_error(ei.value)
    assert isinstance(out, worker.PermanentError)
    assert "TOKEN123" not in str(out)                               # secret redacted


@pytest.mark.parametrize("stderr", [
    "remote: Repository not found.\nfatal: repository 'https://github.com/a/b/' not found",
    "fatal: Authentication failed for 'https://github.com/a/b/'",
    "fatal: could not read Username for 'https://github.com': No such device or address",
    "fatal: could not read Username for 'https://github.com': terminal prompts disabled",
])
def test_not_found_and_auth_errors_are_permanent(stderr):
    worker = pytest.importorskip("worker")
    out = worker.classify_clone_error(GitCommandFailed(f"git clone failed (exit 128): {stderr}"))
    assert isinstance(out, worker.PermanentError)


def test_timeouts_and_network_errors_are_transient():
    worker = pytest.importorskip("worker")
    t = GitTimeout("git clone timed out after 600s and was killed")
    assert worker.classify_clone_error(t) is t
    n = GitCommandFailed("git clone failed (exit 128): fatal: unable to access 'https://github.com/a/b/': "
                         "Could not resolve host: github.com")
    assert worker.classify_clone_error(n) is n


def test_dead_lettered_job_keeps_the_underlying_error():
    worker = pytest.importorskip("worker")
    from database import SessionLocal
    from models import Repository
    db = SessionLocal()
    try:
        r = Repository(url=f"https://github.com/zz/dlq-{os.getpid()}-{time.time()}", name="x", owner="zz",
                       status="queued", failed_reason="Retrying after error: network is on fire")
        db.add(r); db.commit()
        worker.mark_repo_failed(r.id, "Failed after 3 attempts")
        db.expire_all()
        assert r.status == "failed"
        assert r.failed_reason == "Failed after 3 attempts. Last error: network is on fire"
    finally:
        db.query(Repository).filter(Repository.id == r.id).delete()
        db.commit(); db.close()


# ── real git, real GitHub (skipped offline) ──────────────────────────────────

def _github_reachable():
    try:
        socket.create_connection(("github.com", 443), timeout=3).close()
        return True
    except OSError:
        return False


needs_github = pytest.mark.skipif(not _github_reachable(), reason="github.com not reachable")


@needs_github
def test_real_missing_github_repo_fails_fast_instead_of_hanging():
    worker = pytest.importorskip("worker")
    s = svc()
    t = time.time()
    with pytest.raises(GitCommandFailed) as ei:
        s.clone_repository("https://github.com/forge-no-such-owner-xyz/does-not-exist-xyz", 232)
    assert time.time() - t < 60
    assert isinstance(worker.classify_clone_error(ei.value), worker.PermanentError)


@needs_github
def test_real_strict_clone_of_a_public_repo_works():
    s = svc()
    path = s.clone_repository("https://github.com/octocat/Hello-World", 1)
    assert os.path.isdir(os.path.join(path, ".git"))
    assert s.get_new_commits(path)                                   # history is readable
    s.clone_repository("https://github.com/octocat/Hello-World", 1)  # second call = fetch path, also works
