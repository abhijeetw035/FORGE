import os
import uuid
import difflib
import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from models import Function, Commit

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.8


def match_functions(
    new_funcs: List[Dict[str, Any]],
    prev_funcs: List[Dict[str, Any]],
    similarity_threshold: float = SIMILARITY_THRESHOLD
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Match functions parsed from this commit's changed files against the latest
    known version of previous functions.

    Matching order:
    1. Same (file_path, qualified_name) -> reuse canonical_id.
       change_type = 'unchanged' if body_hash and signature_hash are both equal, else 'edit'.
    2. Among remaining, identical body_hash to a disappeared function -> reuse canonical_id.
       change_type = 'move' if file_path differs, 'rename' if qualified_name differs (prefer 'rename').
    3. Among remaining, body token similarity >= threshold with a disappeared function -> reuse canonical_id.
       change_type = 'rename' if qualified_name differs, else 'move'.
       (Note: 'edit' cannot happen in Step 3 because same-location functions were already handled in Step 1).
    4. Otherwise -> new canonical_id = uuid4().hex[:16], change_type = 'new'.
    5. Previous functions in those files that matched nothing -> change_type = 'deleted'.

    Returns:
        (matched_new_funcs, deleted_funcs)
    """
    unmatched_new = set(range(len(new_funcs)))
    unmatched_prev = set(range(len(prev_funcs)))

    # Step 1: Same (file_path, qualified_name)
    prev_by_location = {}
    for idx, prev in enumerate(prev_funcs):
        key = (prev['file_path'], prev['qualified_name'])
        prev_by_location[key] = idx

    for i in list(unmatched_new):
        nf = new_funcs[i]
        key = (nf['file_path'], nf['qualified_name'])
        if key in prev_by_location:
            p_idx = prev_by_location[key]
            if p_idx in unmatched_prev:
                pf = prev_funcs[p_idx]
                nf['canonical_id'] = pf['canonical_id']
                # Check both body_hash and signature_hash for unchanged vs edit
                body_equal = (nf.get('body_hash') == pf.get('body_hash'))
                sig_equal = (nf.get('signature_hash') == pf.get('signature_hash'))
                if body_equal and sig_equal:
                    nf['change_type'] = 'unchanged'
                    nf['similarity'] = 1.0
                else:
                    nf['change_type'] = 'edit'
                    nf['similarity'] = None
                unmatched_new.remove(i)
                unmatched_prev.remove(p_idx)

    # Step 2: Identical body_hash to an unmatched ('disappeared') previous function
    prev_by_body_hash = {}
    for p_idx in unmatched_prev:
        bh = prev_funcs[p_idx].get('body_hash')
        if bh:
            prev_by_body_hash.setdefault(bh, []).append(p_idx)

    for i in list(unmatched_new):
        nf = new_funcs[i]
        bh = nf.get('body_hash')
        if bh and bh in prev_by_body_hash and prev_by_body_hash[bh]:
            p_idx = prev_by_body_hash[bh].pop(0)
            if p_idx in unmatched_prev:
                pf = prev_funcs[p_idx]
                nf['canonical_id'] = pf['canonical_id']
                nf['similarity'] = 1.0

                file_differ = (nf['file_path'] != pf['file_path'])
                name_differ = (nf['qualified_name'] != pf['qualified_name'])

                # Prefer 'rename' if both differ
                if name_differ:
                    nf['change_type'] = 'rename'
                elif file_differ:
                    nf['change_type'] = 'move'
                else:
                    nf['change_type'] = 'unchanged'

                unmatched_new.remove(i)
                unmatched_prev.remove(p_idx)

    # Step 3: Body token similarity >= threshold on body tokens (without header)
    candidates = []
    for i in unmatched_new:
        tokens_a = new_funcs[i].get('body_tokens') or []
        len_a = len(tokens_a)
        if len_a == 0:
            continue

        for p_idx in unmatched_prev:
            tokens_b = prev_funcs[p_idx].get('body_tokens') or []
            len_b = len(tokens_b)
            if len_b == 0:
                continue

            # Skip pairs whose token-count ratio is more than 2x to save time
            count_ratio = max(len_a, len_b) / min(len_a, len_b)
            if count_ratio > 2.0:
                continue

            sim = difflib.SequenceMatcher(None, tokens_a, tokens_b).ratio()
            if sim >= similarity_threshold:
                candidates.append((sim, i, p_idx))

    # Pick the best matches greedily
    candidates.sort(key=lambda c: c[0], reverse=True)
    for sim, i, p_idx in candidates:
        if i in unmatched_new and p_idx in unmatched_prev:
            nf = new_funcs[i]
            pf = prev_funcs[p_idx]
            nf['canonical_id'] = pf['canonical_id']
            nf['similarity'] = round(sim, 4)

            name_differ = (nf['qualified_name'] != pf['qualified_name'])

            # If name differs -> rename. Otherwise file MUST differ (since Step 1 matched same location) -> move
            if name_differ:
                nf['change_type'] = 'rename'
            else:
                nf['change_type'] = 'move'

            unmatched_new.remove(i)
            unmatched_prev.remove(p_idx)

    # Step 4: Otherwise -> new ID
    for i in unmatched_new:
        nf = new_funcs[i]
        nf['canonical_id'] = uuid.uuid4().hex[:16]
        nf['change_type'] = 'new'
        nf['similarity'] = None

    # Step 5: Previous functions in those files that matched nothing -> deleted
    deleted_funcs = []
    for p_idx in unmatched_prev:
        pf = dict(prev_funcs[p_idx])
        pf['change_type'] = 'deleted'
        pf['similarity'] = None
        deleted_funcs.append(pf)
        logger.info(
            f"Function {pf.get('qualified_name')} ({pf.get('canonical_id')}) in {pf.get('file_path')} marked as deleted"
        )

    return new_funcs, deleted_funcs


class FunctionIdentityTracker:
    """
    Maintains cross-commit function identity state during repository mining.
    Tracks latest version per (file_path, qualified_name) in memory and seeds
    from DB on incremental runs.
    """
    def __init__(self, repo_id: int, db: Session, repo_path: Optional[str] = None):
        self.repo_id = repo_id
        self.db = db
        self.repo_path = repo_path
        # latest[(file_path, qualified_name)] = dict(function_data)
        self.latest: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def seed_from_db(self, since_sha: str):
        """
        Seed tracker state from database on incremental runs.
        Fetches the latest function row per canonical_id.
        """
        # Fetch all functions for this repo ordered by commit timestamp ascending
        rows = (
            self.db.query(Function, Commit.timestamp)
            .join(Commit, Function.commit_id == Commit.id)
            .filter(Commit.repository_id == self.repo_id)
            .order_by(Commit.timestamp.asc(), Function.id.asc())
            .all()
        )

        by_cid: Dict[str, Function] = {}
        for fn, _ in rows:
            if fn.canonical_id:
                by_cid[fn.canonical_id] = fn

        for cid, fn in by_cid.items():
            if fn.change_type == 'deleted':
                continue
            qname = fn.qualified_name or fn.name
            key = (fn.file_path, qname)
            self.latest[key] = {
                'canonical_id': fn.canonical_id,
                'name': fn.name,
                'qualified_name': qname,
                'file_path': fn.file_path,
                'body_hash': fn.body_hash,
                'signature_hash': fn.signature_hash,
                'complexity': fn.complexity,
                'start_line': fn.start_line,
                'end_line': fn.end_line,
                'lines_of_code': fn.lines_of_code,
                'parameters': fn.parameters,
                'body_tokens': None,  # lazily parsed if similarity matching is needed
            }
        logger.info(f"Seeded {len(self.latest)} active functions from DB for repo {self.repo_id}")

    def get_prev_funcs(
        self,
        changed_files: Optional[List[str]],
        ast_parser: Any = None,
        parent_sha: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Return the latest known version of functions relevant to this commit's changed files.
        If any candidate function was seeded from DB without body_tokens, re-parses the file
        at parent_sha commit in Git to restore body_tokens for similarity matching.
        """
        if changed_files is None:
            # Full tree (e.g. root commit)
            prev_list = list(self.latest.values())
        else:
            changed_set = set(changed_files)
            prev_list = [
                f for (fpath, _), f in self.latest.items()
                if fpath in changed_set
            ]

        # Ensure body_tokens exist for similarity matching on seeded entries
        if ast_parser and parent_sha and self.repo_path:
            missing_by_file = defaultdict(list)
            for pf in prev_list:
                if pf.get('body_tokens') is None:
                    missing_by_file[pf['file_path']].append(pf)

            if missing_by_file:
                try:
                    import git as gitpython
                    repo = gitpython.Repo(self.repo_path)
                    parent_commit = repo.commit(parent_sha)
                    for fpath, funcs in missing_by_file.items():
                        try:
                            blob = parent_commit.tree / fpath
                            code = blob.data_stream.read().decode('utf-8')
                            tree = ast_parser.parse_file(code, fpath)
                            if tree:
                                _, ext = os.path.splitext(fpath)
                                res = ast_parser.get_parser(ext)
                                if res:
                                    _, lang = res
                                    parsed = ast_parser.extract_functions(tree, code, lang)
                                    parsed_map = {fn['qualified_name']: fn.get('body_tokens') for fn in parsed}
                                    for pf in funcs:
                                        toks = parsed_map.get(pf['qualified_name'])
                                        pf['body_tokens'] = toks
                                        key = (fpath, pf['qualified_name'])
                                        if key in self.latest:
                                            self.latest[key]['body_tokens'] = toks
                        except Exception as file_err:
                            logger.debug(f"Could not re-parse {fpath} at {parent_sha}: {file_err}")
                except Exception as repo_err:
                    logger.warning(f"Could not load parent commit {parent_sha}: {repo_err}")

        return prev_list

    def update_state(self, matched_new: List[Dict[str, Any]], deleted_funcs: List[Dict[str, Any]]):
        """
        Update in-memory latest dictionary after processing a commit.
        """
        # 1. Remove deleted functions
        for df in deleted_funcs:
            key = (df['file_path'], df['qualified_name'])
            self.latest.pop(key, None)

        # 2. Add or update matched new functions
        for nf in matched_new:
            key = (nf['file_path'], nf['qualified_name'])
            # Check if this function moved/renamed from another key
            cid = nf.get('canonical_id')
            old_keys = [k for k, v in self.latest.items() if v.get('canonical_id') == cid and k != key]
            for ok in old_keys:
                self.latest.pop(ok, None)

            self.latest[key] = {
                'canonical_id': nf.get('canonical_id'),
                'name': nf.get('name'),
                'qualified_name': nf.get('qualified_name'),
                'file_path': nf.get('file_path'),
                'body_hash': nf.get('body_hash'),
                'signature_hash': nf.get('signature_hash'),
                'complexity': nf.get('complexity'),
                'start_line': nf.get('start_line'),
                'end_line': nf.get('end_line'),
                'lines_of_code': nf.get('lines_of_code'),
                'parameters': nf.get('parameters'),
                'body_tokens': nf.get('body_tokens'),
            }
