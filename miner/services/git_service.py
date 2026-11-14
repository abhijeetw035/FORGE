import os
import shutil
import signal
import subprocess
import math
import re
import logging
from collections import defaultdict, Counter
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

import git
from urllib.parse import urlparse

from services.url_validation import validate_repo_url

logger = logging.getLogger(__name__)

# git's well-known empty tree: lets us diff a root commit like any other
EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


class InvalidRepositoryURL(ValueError):
    """The URL failed the allowlist; retrying cannot help."""


# git itself is restricted too (strict mode): https only, never follow redirects
# (an allowed host could otherwise bounce git to an internal address), never read
# local paths via the file protocol, no credential helpers.
_STRICT_GIT_ENV = {"GIT_ALLOW_PROTOCOL": "https"}
_STRICT_GIT_CONFIG = ["-c", "protocol.file.allow=never",
                      "-c", "http.followRedirects=false",
                      "-c", "credential.helper="]

# Applied in EVERY mode: git must never wait for a human. GitHub answers
# "who are you?" for repositories that do not exist; without these, git blocks
# on a username prompt forever and the heartbeat keeps the dead job alive.
_NO_PROMPT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": shutil.which("true") or "/bin/true",   # prints nothing -> instant auth failure
    "SSH_ASKPASS": shutil.which("true") or "/bin/true",
    "GCM_INTERACTIVE": "never",
}

# A hung clone/fetch must end. Default 10 minutes.
GIT_NETWORK_TIMEOUT_SEC = int(os.getenv("GIT_NETWORK_TIMEOUT_SEC", "600"))


class GitCommandFailed(Exception):
    """git exited non-zero; the message carries its stderr (the worker redacts secrets)."""


class GitTimeout(Exception):
    """git did not finish within the timeout and was killed."""


class GitService:
    def __init__(self, storage_path: str, github_token: Optional[str] = None, strict: bool = True):
        """
        ``strict`` (default) enforces the URL allowlist and https-only git.
        It exists to be switched off ONLY by tests that clone local fixture repos.
        """
        self.storage_path = storage_path
        self.github_token = github_token
        self.strict = strict
        os.makedirs(storage_path, exist_ok=True)

    def clone_repository(self, url: str, repo_id: int) -> str:
        """
        Return a local, up-to-date working copy of the repo.

        First run: clone. Re-analysis: fetch the remote's HEAD and move to it,
        so incremental runs actually see new upstream commits. A corrupt or
        half-cloned directory is removed and cloned again.

        The URL is validated again here (the API already did): this is the last
        line of defence before user input reaches git.
        """
        if self.strict:
            try:
                url = validate_repo_url(url)
            except ValueError as e:
                raise InvalidRepositoryURL(f"Repository URL not allowed: {e}")

        repo_dir = os.path.join(self.storage_path, f"repo_{repo_id}")

        clone_url = url
        if self.github_token and (urlparse(url).hostname or "").lower() == 'github.com':
            clone_url = url.replace('https://', f'https://{self.github_token}@', 1)

        if os.path.exists(repo_dir):
            try:
                repo = git.Repo(repo_dir)
                repo.head.commit  # raises on an empty/half-cloned repo
            except (git.InvalidGitRepositoryError, git.NoSuchPathError, ValueError):
                logger.warning(f"Clone at {repo_dir} is unusable; removing and re-cloning")
                shutil.rmtree(repo_dir, ignore_errors=True)
            else:
                # Keep the remote URL current (token may have changed), then
                # fast-forward to the remote HEAD. reset --hard also handles
                # force-pushes; the clone is ours, nothing local to preserve.
                repo.remotes.origin.set_url(clone_url)
                self._run_git(["fetch", "origin", "HEAD"], cwd=repo_dir)
                repo.git.reset('--hard', 'FETCH_HEAD')
                return repo_dir

        try:
            self._run_git(["clone", "--quiet", "--", clone_url, repo_dir])
        except Exception:
            shutil.rmtree(repo_dir, ignore_errors=True)    # never leave a half-clone behind
            raise
        return repo_dir

    def _run_git(self, args: List[str], cwd: Optional[str] = None,
                 timeout: Optional[int] = None) -> str:
        """
        Run git with no prompts, restricted protocols (strict mode) and a hard
        timeout. A timed-out git (and any helper processes it started) is killed.
        """
        timeout = timeout or GIT_NETWORK_TIMEOUT_SEC
        env = {**os.environ, **_NO_PROMPT_ENV}
        cmd = ["git"]
        if self.strict:
            env.update(_STRICT_GIT_ENV)
            cmd += _STRICT_GIT_CONFIG
        cmd += args

        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, errors="replace",
                                start_new_session=True)       # own process group -> killable as a unit
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
            raise GitTimeout(f"git {args[0]} timed out after {timeout}s and was killed")
        if proc.returncode != 0:
            raise GitCommandFailed(f"git {args[0]} failed (exit {proc.returncode}): {err.strip()[-600:]}")
        return out

    def get_commits(self, repo_path: str):
        repo = git.Repo(repo_path)
        commits = []

        for commit in repo.iter_commits():
            commits.append({
                'sha': commit.hexsha,
                'author': str(commit.author),
                'message': commit.message.strip(),
                'timestamp': commit.committed_datetime
            })

        return commits

    # ── per-commit facts ─────────────────────────────────────────────────

    @staticmethod
    def parse_numstat(raw: str) -> List[Dict[str, Any]]:
        """Parse ``git diff --numstat -z`` output into [{file_path, lines_added, lines_deleted}]."""
        rows = []
        for entry in raw.split('\0'):
            if not entry.strip():
                continue
            parts = entry.lstrip('\n').split('\t', 2)
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            rows.append({
                'file_path': path,
                # binary files report "-"
                'lines_added': int(added) if added.isdigit() else 0,
                'lines_deleted': int(deleted) if deleted.isdigit() else 0,
            })
        return rows

    def _canonical_email(self, repo, name: str, email: str, cache: dict) -> str:
        """Lowercased author email resolved through .mailmap, so one person = one author."""
        key = (name, email)
        if key in cache:
            return cache[key]
        resolved = email or ''
        try:
            out = repo.git.check_mailmap(f"{name} <{email}>")
            m = re.search(r'<([^>]*)>', out)
            if m:
                resolved = m.group(1)
        except Exception:
            pass
        resolved = resolved.strip().lower() or (name or 'unknown').strip().lower()
        cache[key] = resolved
        return resolved

    def _commit_info(self, repo, commit, mailmap_cache: dict) -> Dict[str, Any]:
        """
        Everything we record about one commit, from a SINGLE git call
        (diff vs first parent, or vs the empty tree for a root commit).

        ``file_changes`` is empty for merge commits: their changes are already
        counted on the merged branch's own commits, so counting the merge too
        would double-count churn and lines.
        """
        parent = commit.parents[0].hexsha if commit.parents else EMPTY_TREE
        rows = self.parse_numstat(
            repo.git.diff('--numstat', '--no-renames', '-z', parent, commit.hexsha)
        )
        is_merge = len(commit.parents) > 1
        committed = commit.committed_datetime
        committed_utc = committed.astimezone(timezone.utc).replace(tzinfo=None)
        return {
            'sha':           commit.hexsha,
            'author':        str(commit.author),
            'author_email':  self._canonical_email(
                                 repo, commit.author.name or '', commit.author.email or '', mailmap_cache),
            'message':       commit.message.strip(),
            'timestamp':     committed,
            'committed_at':  committed_utc,
            'changed_files': [r['file_path'] for r in rows],
            'file_changes':  [] if is_merge else rows,
        }

    def get_commit_changes(self, repo_path: str, sha: str) -> Dict[str, Any]:
        """Facts for one existing commit (used to backfill commits indexed before file_changes existed)."""
        repo = git.Repo(repo_path)
        return self._commit_info(repo, repo.commit(sha), {})

    def get_new_commits(self, repo_path: str, since_sha: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return only commits that have NOT been indexed yet, oldest first.

        If ``since_sha`` is provided (the last fully-indexed commit SHA), we
        ask git for the range  ``<since_sha>..HEAD``.  If it is None
        (first-time clone) we walk the full history.

        Each dict carries ``changed_files`` (paths touched, for AST parsing),
        ``file_changes`` (per-file line stats, stored in file_changes),
        ``author_email`` (lowercased, .mailmap-resolved) and ``committed_at`` (UTC).
        """
        repo = git.Repo(repo_path)

        if since_sha:
            try:
                # Only commits reachable from HEAD that are NOT ancestors of since_sha
                commit_iter = repo.iter_commits(f'{since_sha}..HEAD')
            except git.BadName:
                # since_sha no longer in history (e.g. force-push) — full walk
                logger.warning(
                    f"since_sha {since_sha!r} not found in history; falling back to full walk"
                )
                commit_iter = repo.iter_commits()
        else:
            commit_iter = repo.iter_commits()

        cache: dict = {}
        commits = [self._commit_info(repo, c, cache) for c in commit_iter]

        # Chronological order (oldest first) so last_indexed_sha checkpoints correctly.
        return list(reversed(commits))

    def get_head_files(self, repo_path: str) -> Dict[str, Dict[str, int]]:
        """
        {path: {"dependency_count": n, "loc": n}} for every file that exists
        at HEAD. Files not in this map were deleted and must not be risk-scored.
        ``loc`` is the number of non-blank lines (0 for binary files).
        """
        repo = git.Repo(repo_path)
        files: Dict[str, Dict[str, int]] = {}
        for item in repo.head.commit.tree.traverse():
            if item.type != 'blob':
                continue
            try:
                raw = item.data_stream.read()
                source = raw.decode('utf-8', errors='ignore')
                files[item.path] = {
                    'dependency_count': self._count_dependencies(source, item.path),
                    'loc': self.count_loc(raw),
                }
            except Exception:
                files[item.path] = {'dependency_count': 0, 'loc': 0}
        return files

    @staticmethod
    def count_loc(raw: bytes) -> int:
        """Non-blank lines (same as ``grep -cv '^\\s*$'``); 0 for binary content."""
        if b'\0' in raw[:8192]:
            return 0
        return sum(1 for line in raw.splitlines() if line.strip())

    def get_file_at_commit(self, repo_path: str, commit_sha: str, file_path: str) -> Optional[str]:
        try:
            repo = git.Repo(repo_path)
            commit = repo.commit(commit_sha)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode('utf-8')
        except Exception:
            return None

    # Helpers
    @staticmethod
    def _shannon_entropy(probabilities: List[float]) -> float:
        """Shannon entropy H = -sum(p * log2(p))."""
        return -sum(p * math.log2(p) for p in probabilities if p > 0)

    @staticmethod
    def _count_dependencies(source: str, file_path: str) -> int:
        """Rough import/dependency count heuristic across languages."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.py':
            pattern = r'^\s*(import |from .+ import )'
        elif ext in ('.js', '.ts', '.jsx', '.tsx'):
            pattern = r'^\s*(import |require\s*\()'
        elif ext in ('.java', '.kt'):
            pattern = r'^\s*import '
        elif ext == '.go':
            pattern = r'^\s*import '
        elif ext in ('.c', '.cpp', '.h', '.hpp'):
            pattern = r'^\s*#include '
        elif ext in ('.rs',):
            pattern = r'^\s*use '
        elif ext == '.rb':
            pattern = r'^\s*(require|require_relative) '
        else:
            return 0
        return len(re.findall(pattern, source, re.MULTILINE))


