"""SSRF: the miner re-validates every URL before it reaches git, and restricts git itself."""
import os
import tempfile

import pytest

from services.git_service import GitService, InvalidRepositoryURL
from services.url_validation import validate_repo_url

BAD = [
    "file:///etc/passwd",
    "http://github.com/a/b",
    "https://169.254.169.254/latest",
    "https://user:pw@github.com/a/b",
    "https://evil.com/a/b",
    "https://github.com:8443/a/b",
    "https://github.com/a/b?x=1",
    "https://github.com/a/b#frag",
    "https://github.com/a",
    "https://github.com/a/b/c",
    "https://github.com/../b",
    "https://github.com/a/..",
    "https://github.com./a/b",
    "https://github.com@evil.com/a/b",
    "https://evil.com/github.com/a/b",
    "https://github.com/a/b\nhttps://evil.com",
    "git@github.com:a/b.git",
    "ssh://git@github.com/a/b",
    "//github.com/a/b",
    "",
]


@pytest.mark.parametrize("url", BAD)
def test_bad_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_repo_url(url)


def test_good_urls_are_accepted_and_normalised():
    assert validate_repo_url("https://github.com/fastapi/fastapi") == "https://github.com/fastapi/fastapi"
    assert validate_repo_url("  https://GitHub.com/Owner/Repo.git/ ") == "https://github.com/Owner/Repo"
    assert validate_repo_url("https://gitlab.com/o/r") == "https://gitlab.com/o/r"


def test_allowlist_is_configurable(monkeypatch):
    monkeypatch.setenv("ALLOWED_GIT_HOSTS", "git.example.org")
    assert validate_repo_url("https://git.example.org/a/b") == "https://git.example.org/a/b"
    with pytest.raises(ValueError):
        validate_repo_url("https://github.com/a/b")


@pytest.mark.parametrize("url", BAD[:6])
def test_strict_clone_refuses_before_touching_git(url):
    svc = GitService(tempfile.mkdtemp())            # strict by default
    with pytest.raises(InvalidRepositoryURL):
        svc.clone_repository(url, 1)
    assert not os.path.exists(os.path.join(svc.storage_path, "repo_1"))


def test_invalid_url_is_a_permanent_failure_not_a_retry():
    worker = pytest.importorskip("worker")
    out = worker.classify_clone_error(InvalidRepositoryURL("Repository URL not allowed: Host not allowed"))
    assert isinstance(out, worker.PermanentError)


def test_redirect_failure_is_permanent():
    worker = pytest.importorskip("worker")
    err = Exception("fatal: unable to update url base from redirection: asked for ...")
    assert isinstance(worker.classify_clone_error(err), worker.PermanentError)


def test_token_is_only_sent_to_the_real_github_host(monkeypatch):
    """Substring matching ('github.com' in url) would leak the token to look-alike hosts."""
    seen = {}

    def fake_clone(url, path, **kw):
        seen["url"], seen["kw"] = url, kw

    import git
    monkeypatch.setattr(git.Repo, "clone_from", staticmethod(fake_clone))
    svc = GitService(tempfile.mkdtemp(), github_token="TOKEN123")
    svc.clone_repository("https://github.com/a/b", 7)
    assert seen["url"] == "https://TOKEN123@github.com/a/b"

    monkeypatch.setenv("ALLOWED_GIT_HOSTS", "github.com,github.com.evil.io")
    svc.clone_repository("https://github.com.evil.io/a/b", 8)
    assert "TOKEN123" not in seen["url"]


def test_clone_runs_with_restricted_git(monkeypatch):
    import git
    seen = {}
    monkeypatch.setattr(git.Repo, "clone_from",
                        staticmethod(lambda url, path, **kw: seen.update(kw)))
    GitService(tempfile.mkdtemp()).clone_repository("https://github.com/a/b", 9)
    assert seen["env"]["GIT_ALLOW_PROTOCOL"] == "https"
    assert seen["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert "-c protocol.file.allow=never" in seen["multi_options"]
    assert "-c http.followRedirects=false" in seen["multi_options"]
