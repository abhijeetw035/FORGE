import os
import math
import re
import logging
from collections import defaultdict, Counter
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

import git

logger = logging.getLogger(__name__)


class GitService:
    def __init__(self, storage_path: str, github_token: Optional[str] = None):
        self.storage_path = storage_path
        self.github_token = github_token
        os.makedirs(storage_path, exist_ok=True)

    def clone_repository(self, url: str, repo_id: int) -> str:
        repo_dir = os.path.join(self.storage_path, f"repo_{repo_id}")

        if os.path.exists(repo_dir):
            return repo_dir

        clone_url = url
        if self.github_token and 'github.com' in url:
            clone_url = url.replace('https://', f'https://{self.github_token}@')

        git.Repo.clone_from(clone_url, repo_dir)
        return repo_dir

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

    def get_new_commits(self, repo_path: str, since_sha: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return only commits that have NOT been indexed yet.

        If ``since_sha`` is provided (the last fully-indexed commit SHA), we
        ask git for the range  ``<since_sha>..HEAD`` — typically a handful of
        commits even on a repo with millions of entries.

        If ``since_sha`` is None (first-time clone) we fall back to the full
        history walk exactly as before.

        Each returned dict also carries ``changed_files`` — the list of file
        paths that were actually modified in that commit (from diff-tree),
        so the caller can avoid re-parsing every file in the tree.
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

        commits = []
        for commit in commit_iter:
            # Efficient changed-files list via diff against parent(s)
            if commit.parents:
                changed = [
                    diff.b_path or diff.a_path
                    for diff in commit.diff(commit.parents[0], create_patch=False)
                    if (diff.b_path or diff.a_path)
                ]
            else:
                # Root commit — every file is "new"
                changed = [
                    item.path
                    for item in commit.tree.traverse()
                    if item.type == 'blob'
                ]

            commits.append({
                'sha':           commit.hexsha,
                'author':        str(commit.author),
                'message':       commit.message.strip(),
                'timestamp':     commit.committed_datetime,
                'changed_files': changed,
            })

        # Return in chronological order (oldest first) so we can checkpoint
        # last_indexed_sha correctly after each commit.
        return list(reversed(commits))

    def get_file_at_commit(self, repo_path: str, commit_sha: str, file_path: str) -> Optional[str]:
        try:
            repo = git.Repo(repo_path)
            commit = repo.commit(commit_sha)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode('utf-8')
        except Exception:
            return None

    def get_file_metrics(self, repo_path: str, since_sha: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Walk the commit history and compute per-file features.

        ``since_sha`` enables incremental mode: only commits in the range
        ``<since_sha>..HEAD`` are walked, so the caller can merge the returned
        deltas into existing FileMetrics rows instead of recomputing everything.

        When ``since_sha`` is None (first run) the full history is walked.

        Per-file features computed:
        - churn            : total number of commits that touched this file
        - lines_added      : cumulative lines added across all commits
        - lines_deleted    : cumulative lines deleted across all commits
        - file_age_days    : days between first and last commit touching the file
        - commit_frequency : commits per day (churn / max(file_age_days, 1))
        - recent_churn     : commits in the last 90 days
        - author_count     : number of distinct authors
        - ownership_entropy: Shannon entropy of author contribution fractions
        - dependency_count : rough count of import/require/include statements
                             in the HEAD version of the file
        """
        repo = git.Repo(repo_path)
        now = datetime.now(timezone.utc)
        ninety_days_ago = now.timestamp() - 90 * 86400

        if since_sha:
            try:
                commit_iter = repo.iter_commits(f'{since_sha}..HEAD')
                logger.info(f"Incremental file-metrics walk from {since_sha[:7]}")
            except git.BadName:
                logger.warning(f"since_sha {since_sha!r} not in history; full walk")
                commit_iter = repo.iter_commits()
        else:
            commit_iter = repo.iter_commits()

        file_churn:      Dict[str, int]             = defaultdict(int)
        file_lines_add:  Dict[str, int]             = defaultdict(int)
        file_lines_del:  Dict[str, int]             = defaultdict(int)
        file_first_ts:   Dict[str, float]           = {}
        file_last_ts:    Dict[str, float]           = {}
        file_recent:     Dict[str, int]             = defaultdict(int)
        file_authors:    Dict[str, Counter]         = defaultdict(Counter)

        for commit in commit_iter:
            ts = commit.committed_date  # unix timestamp
            author = str(commit.author)

            # diff against each parent (or root commit)
            parents = commit.parents
            if parents:
                diffs = commit.diff(parents[0], create_patch=False)
            else:
                # root commit – treat every blob as "added"
                diffs = commit.diff(git.NULL_TREE, create_patch=False)

            for diff in diffs:
                path = diff.b_path or diff.a_path
                if not path:
                    continue

                file_churn[path] += 1
                file_authors[path][author] += 1

                if path not in file_first_ts or ts < file_first_ts[path]:
                    file_first_ts[path] = ts
                if path not in file_last_ts or ts > file_last_ts[path]:
                    file_last_ts[path] = ts

                if ts >= ninety_days_ago:
                    file_recent[path] += 1

                # line stats via diff stats (available without --patch)
                try:
                    stats = commit.stats.files.get(path, {})
                    file_lines_add[path] += stats.get('insertions', 0)
                    file_lines_del[path] += stats.get('deletions', 0)
                except Exception:
                    pass

        # dependency count from HEAD tree
        file_deps: Dict[str, int] = {}
        try:
            head_commit = repo.head.commit
            for item in head_commit.tree.traverse():
                if item.type != 'blob':
                    continue
                try:
                    source = item.data_stream.read().decode('utf-8', errors='ignore')
                    file_deps[item.path] = self._count_dependencies(source, item.path)
                except Exception:
                    file_deps[item.path] = 0
        except Exception:
            pass

        # assemble results
        results = []
        for path, churn in file_churn.items():
            first_ts = file_first_ts.get(path, now.timestamp())
            last_ts  = file_last_ts.get(path, now.timestamp())
            age_days = max((last_ts - first_ts) / 86400, 0)

            author_counts = file_authors[path]
            total_touches = sum(author_counts.values())
            entropy = self._shannon_entropy(
                [c / total_touches for c in author_counts.values()]
            ) if total_touches > 0 else 0.0

            results.append({
                'file_path':         path,
                'churn':             churn,
                'lines_added':       file_lines_add.get(path, 0),
                'lines_deleted':     file_lines_del.get(path, 0),
                'file_age_days':     round(age_days, 1),
                'commit_frequency':  round(churn / max(age_days, 1), 4),
                'recent_churn':      file_recent.get(path, 0),
                'author_count':      len(author_counts),
                'ownership_entropy': round(entropy, 4),
                'dependency_count':  file_deps.get(path, 0),
            })

        return results

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

    # Cross-commit function evolution (identity-aware, no line numbers)
    def get_function_evolution(
        self,
        repo_path: str,
        db_functions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build a timeline of each unique function's life across commits using
        its ``canonical_id`` — NOT line-number ranges.

        This correctly handles:
        - Function moved to a different line / different file (same canonical_id)
        - Pure reformat / indentation change (same body_hash → same canonical_id)
        - Rename          → different signature_hash → treated as new function  ✓
        - Parameter change → different signature_hash → treated as new function ✓
        - Body rewrite    → different body_hash  → treated as new version       ✓

        Args:
            repo_path    : path to the cloned git repo (used to get commit order)
            db_functions : list of dicts from the database, each with keys:
                           canonical_id, signature_hash, body_hash,
                           name, file_path, start_line, end_line,
                           complexity, commit_sha, commit_timestamp

        Returns:
            List of function-evolution dicts, one per unique canonical_id:
            {
                canonical_id      : str,
                name              : str,          # most recent name
                file_path         : str,          # most recent file path
                first_seen_sha    : str,
                last_seen_sha     : str,
                first_seen_ts     : datetime,
                last_seen_ts      : datetime,
                commit_count      : int,          # how many commits touched it
                was_moved         : bool,         # file_path changed between commits
                was_renamed       : bool,         # signature_hash changed (name/params)
                complexity_trend  : str,          # 'increasing' | 'decreasing' | 'stable'
                complexity_delta  : int,          # last - first complexity
                versions          : list[dict],   # full chronological history
            }
        """
        if not db_functions:
            return []

        # Group all Function rows by canonical_id
        by_cid: Dict[str, List[Dict]] = defaultdict(list)
        for fn in db_functions:
            cid = fn.get('canonical_id')
            if cid:
                by_cid[cid].append(fn)

        results = []
        for cid, versions in by_cid.items():
            # Sort chronologically
            versions_sorted = sorted(
                versions,
                key=lambda f: f.get('commit_timestamp') or datetime.min
            )

            first = versions_sorted[0]
            last  = versions_sorted[-1]

            # Detect moves: file_path changed across any two consecutive versions
            paths = [v['file_path'] for v in versions_sorted]
            was_moved = len(set(paths)) > 1

            # Detect renames: signature_hash changed (name or params changed)
            sigs = [v.get('signature_hash') for v in versions_sorted if v.get('signature_hash')]
            was_renamed = len(set(sigs)) > 1

            # Complexity trend
            complexities = [v.get('complexity') or 0 for v in versions_sorted]
            if len(complexities) >= 2:
                delta = complexities[-1] - complexities[0]
                if delta > 0:
                    trend = 'increasing'
                elif delta < 0:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                delta = 0
                trend = 'stable'

            results.append({
                'canonical_id':     cid,
                'name':             last.get('name', ''),
                'file_path':        last.get('file_path', ''),
                'first_seen_sha':   first.get('commit_sha', ''),
                'last_seen_sha':    last.get('commit_sha', ''),
                'first_seen_ts':    first.get('commit_timestamp'),
                'last_seen_ts':     last.get('commit_timestamp'),
                'commit_count':     len(versions_sorted),
                'was_moved':        was_moved,
                'was_renamed':      was_renamed,
                'complexity_trend': trend,
                'complexity_delta': delta,
                'versions':         versions_sorted,
            })

        # Sort by commit_count descending (most-touched functions first)
        results.sort(key=lambda r: r['commit_count'], reverse=True)
        return results
