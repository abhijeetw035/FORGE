import os
import shutil
import tempfile
import pytest
import git
from services.ast_parser import ASTParser
from services.identity import match_functions, FunctionIdentityTracker
from database import SessionLocal
from models import Repository, Commit, Function
from worker import process_commit_ast
from datetime import datetime


@pytest.fixture
def parser():
    p = ASTParser()
    p.setup_language('python')
    p.setup_language('javascript')
    return p


# ============================================================================
# Unit tests with matcher directly
# ============================================================================

def test_match_new_function():
    """Completely new function gets a new UUID canonical_id and change_type 'new'."""
    new_funcs = [{
        'name': 'foo',
        'qualified_name': 'foo',
        'file_path': 'test.py',
        'body_hash': 'hash1',
        'body_tokens': ['return', '1'],
    }]
    prev_funcs = []
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 1
    assert matched[0]['change_type'] == 'new'
    assert matched[0]['canonical_id'] is not None
    assert len(matched[0]['canonical_id']) == 16
    assert len(deleted) == 0


def test_match_unchanged_function():
    """Same (file_path, qualified_name) and same body_hash -> 'unchanged'."""
    prev_funcs = [{
        'canonical_id': 'id_foo',
        'name': 'foo',
        'qualified_name': 'foo',
        'file_path': 'test.py',
        'body_hash': 'hash1',
        'body_tokens': ['return', '1'],
    }]
    new_funcs = [{
        'name': 'foo',
        'qualified_name': 'foo',
        'file_path': 'test.py',
        'body_hash': 'hash1',
        'body_tokens': ['return', '1'],
    }]
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 1
    assert matched[0]['canonical_id'] == 'id_foo'
    assert matched[0]['change_type'] == 'unchanged'
    assert matched[0]['similarity'] == 1.0
    assert len(deleted) == 0


def test_match_edit_body():
    """Same (file_path, qualified_name) and different body_hash -> 'edit'."""
    prev_funcs = [{
        'canonical_id': 'id_foo',
        'name': 'foo',
        'qualified_name': 'foo',
        'file_path': 'test.py',
        'body_hash': 'hash_old',
        'body_tokens': ['return', '1'],
    }]
    new_funcs = [{
        'name': 'foo',
        'qualified_name': 'foo',
        'file_path': 'test.py',
        'body_hash': 'hash_new',
        'body_tokens': ['return', '2'],
    }]
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 1
    assert matched[0]['canonical_id'] == 'id_foo'
    assert matched[0]['change_type'] == 'edit'
    assert len(deleted) == 0


def test_match_move_file():
    """Identical body_hash across different file_path -> 'move'."""
    prev_funcs = [{
        'canonical_id': 'id_moved',
        'name': 'helper',
        'qualified_name': 'helper',
        'file_path': 'utils.py',
        'body_hash': 'hash_helper',
        'body_tokens': ['x', '=', '1', 'return', 'x'],
    }]
    new_funcs = [{
        'name': 'helper',
        'qualified_name': 'helper',
        'file_path': 'common/utils.py',
        'body_hash': 'hash_helper',
        'body_tokens': ['x', '=', '1', 'return', 'x'],
    }]
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 1
    assert matched[0]['canonical_id'] == 'id_moved'
    assert matched[0]['change_type'] == 'move'
    assert len(deleted) == 0


def test_match_rename_identical_body():
    """Identical body_hash with different qualified_name -> 'rename'."""
    prev_funcs = [{
        'canonical_id': 'id_rename',
        'name': 'old_name',
        'qualified_name': 'old_name',
        'file_path': 'service.py',
        'body_hash': 'hash_exact',
        'body_tokens': ['a', '=', '1', 'b', '=', '2', 'return', 'a', '+', 'b'],
    }]
    new_funcs = [{
        'name': 'new_name',
        'qualified_name': 'new_name',
        'file_path': 'service.py',
        'body_hash': 'hash_exact',
        'body_tokens': ['a', '=', '1', 'b', '=', '2', 'return', 'a', '+', 'b'],
    }]
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 1
    assert matched[0]['canonical_id'] == 'id_rename'
    assert matched[0]['change_type'] == 'rename'
    assert len(deleted) == 0


def test_match_rename_with_small_edit():
    """Renamed function with small edit (similarity >= 0.8) -> 'rename'."""
    # 10 tokens, 1 token changed (ratio >= 0.8)
    prev_tokens = ['x', '=', '1', 'y', '=', '2', 'z', '=', '3', 'return', 'x']
    new_tokens  = ['x', '=', '1', 'y', '=', '2', 'z', '=', '4', 'return', 'x']
    prev_funcs = [{
        'canonical_id': 'id_sim',
        'name': 'calculate_old',
        'qualified_name': 'calculate_old',
        'file_path': 'calc.py',
        'body_hash': 'hash_prev',
        'body_tokens': prev_tokens,
    }]
    new_funcs = [{
        'name': 'calculate_new',
        'qualified_name': 'calculate_new',
        'file_path': 'calc.py',
        'body_hash': 'hash_next',
        'body_tokens': new_tokens,
    }]
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 1
    assert matched[0]['canonical_id'] == 'id_sim'
    assert matched[0]['change_type'] == 'rename'
    assert matched[0]['similarity'] >= 0.8
    assert len(deleted) == 0


def test_parameter_added_same_body():
    """Adding a parameter while keeping the body identical produces same canonical_id and change_type 'edit'."""
    prev_funcs = [{
        'canonical_id': 'id_param',
        'name': 'foo',
        'qualified_name': 'foo',
        'file_path': 'test.py',
        'body_hash': 'body_hash_identical',
        'signature_hash': 'sig_hash_v1',
        'body_tokens': ['return', '1'],
    }]
    new_funcs = [{
        'name': 'foo',
        'qualified_name': 'foo',
        'file_path': 'test.py',
        'body_hash': 'body_hash_identical',
        'signature_hash': 'sig_hash_v2',  # new parameter -> different signature_hash
        'body_tokens': ['return', '1'],
    }]
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 1
    assert matched[0]['canonical_id'] == 'id_param'
    assert matched[0]['change_type'] == 'edit'
    assert len(deleted) == 0


def test_deleted_function():
    """Previous function not matched in this commit is recorded as 'deleted'."""
    prev_funcs = [{
        'canonical_id': 'id_dead',
        'name': 'deprecated',
        'qualified_name': 'deprecated',
        'file_path': 'old.py',
        'body_hash': 'hash_dead',
        'body_tokens': ['pass'],
    }]
    new_funcs = []
    matched, deleted = match_functions(new_funcs, prev_funcs)
    assert len(matched) == 0
    assert len(deleted) == 1
    assert deleted[0]['canonical_id'] == 'id_dead'
    assert deleted[0]['change_type'] == 'deleted'


# ============================================================================
# Git repository integration tests
# ============================================================================

def test_git_repo_function_lifecycle(parser):
    """
    Test lifecycle across multiple commits in a real Git repository:
    1. Initial commit with 2 methods in different classes (__init__) and a helper
    2. Comment-only edit -> 'unchanged', same canonical_id
    3. Body edit -> 'edit', same canonical_id
    4. Function move to another file -> 'move', same canonical_id
    5. Function rename -> 'rename', same canonical_id
    """
    repo_dir = tempfile.mkdtemp()
    try:
        repo = git.Repo.init(repo_dir)
        # Configure user for commits
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Commit 1: Initial commit
        code_v1 = """
class First:
    def __init__(self):
        self.val = 1

class Second:
    def __init__(self):
        self.val = 2

def helper():
    return 42
"""
        fpath = os.path.join(repo_dir, "main.py")
        with open(fpath, "w") as f:
            f.write(code_v1)
        repo.index.add(["main.py"])
        c1 = repo.index.commit("Initial commit")

        tree1 = parser.parse_file(code_v1, "main.py")
        funcs1 = parser.extract_functions(tree1, code_v1, "python")
        for fn in funcs1:
            fn['file_path'] = 'main.py'

        matched1, del1 = match_functions(funcs1, [])
        assert len(matched1) == 3
        cids = {fn['qualified_name']: fn['canonical_id'] for fn in matched1}
        # Two __init__ in different classes must have different canonical_id
        assert cids['First.__init__'] != cids['Second.__init__']
        for fn in matched1:
            assert fn['change_type'] == 'new'

        # Commit 2: Comment-only change in main.py
        code_v2 = """
class First:
    def __init__(self):
        # added a comment here
        self.val = 1

class Second:
    def __init__(self):
        self.val = 2

def helper():
    return 42
"""
        with open(fpath, "w") as f:
            f.write(code_v2)
        repo.index.add(["main.py"])
        c2 = repo.index.commit("Comment only")

        tree2 = parser.parse_file(code_v2, "main.py")
        funcs2 = parser.extract_functions(tree2, code_v2, "python")
        for fn in funcs2:
            fn['file_path'] = 'main.py'

        matched2, del2 = match_functions(funcs2, matched1)
        cids2 = {fn['qualified_name']: fn['canonical_id'] for fn in matched2}
        assert cids2['First.__init__'] == cids['First.__init__']
        # Comment-only change must be 'unchanged'
        types2 = {fn['qualified_name']: fn['change_type'] for fn in matched2}
        assert types2['First.__init__'] == 'unchanged'
        assert types2['Second.__init__'] == 'unchanged'
        assert types2['helper'] == 'unchanged'

        # Commit 3: Edit body of helper
        code_v3 = """
class First:
    def __init__(self):
        self.val = 1

class Second:
    def __init__(self):
        self.val = 2

def helper():
    return 100 + 42
"""
        with open(fpath, "w") as f:
            f.write(code_v3)
        repo.index.add(["main.py"])
        c3 = repo.index.commit("Edit helper")

        tree3 = parser.parse_file(code_v3, "main.py")
        funcs3 = parser.extract_functions(tree3, code_v3, "python")
        for fn in funcs3:
            fn['file_path'] = 'main.py'

        matched3, del3 = match_functions(funcs3, matched2)
        types3 = {fn['qualified_name']: fn['change_type'] for fn in matched3}
        cids3 = {fn['qualified_name']: fn['canonical_id'] for fn in matched3}
        assert cids3['helper'] == cids['helper']
        assert types3['helper'] == 'edit'

        # Commit 4: Move helper to utils.py
        code_main_v4 = """
class First:
    def __init__(self):
        self.val = 1

class Second:
    def __init__(self):
        self.val = 2
"""
        code_utils_v4 = """
def helper():
    return 100 + 42
"""
        with open(fpath, "w") as f:
            f.write(code_main_v4)
        utils_path = os.path.join(repo_dir, "utils.py")
        with open(utils_path, "w") as f:
            f.write(code_utils_v4)
        repo.index.add(["main.py", "utils.py"])
        c4 = repo.index.commit("Move helper to utils.py")

        funcs4 = []
        tree_m4 = parser.parse_file(code_main_v4, "main.py")
        for fn in parser.extract_functions(tree_m4, code_main_v4, "python"):
            fn['file_path'] = 'main.py'
            funcs4.append(fn)

        tree_u4 = parser.parse_file(code_utils_v4, "utils.py")
        for fn in parser.extract_functions(tree_u4, code_utils_v4, "python"):
            fn['file_path'] = 'utils.py'
            funcs4.append(fn)

        matched4, del4 = match_functions(funcs4, matched3)
        helper_fn = next(fn for fn in matched4 if fn['name'] == 'helper')
        assert helper_fn['canonical_id'] == cids['helper']
        assert helper_fn['change_type'] == 'move'
        assert helper_fn['file_path'] == 'utils.py'

        # Commit 5: Rename helper to run_helper in utils.py
        code_utils_v5 = """
def run_helper():
    return 100 + 42
"""
        with open(utils_path, "w") as f:
            f.write(code_utils_v5)
        repo.index.add(["utils.py"])
        c5 = repo.index.commit("Rename helper to run_helper")

        tree_u5 = parser.parse_file(code_utils_v5, "utils.py")
        funcs5 = parser.extract_functions(tree_u5, code_utils_v5, "python")
        for fn in funcs5:
            fn['file_path'] = 'utils.py'

        # Prev funcs relevant to utils.py from commit 4
        prev_utils = [fn for fn in matched4 if fn['file_path'] == 'utils.py']
        matched5, del5 = match_functions(funcs5, prev_utils)
        assert len(matched5) == 1
        assert matched5[0]['name'] == 'run_helper'
        assert matched5[0]['canonical_id'] == cids['helper']
        assert matched5[0]['change_type'] == 'rename'

    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)


def test_incremental_seeding_and_rename_with_edit(parser):
    """
    Test incremental run:
    1. Commit 1 adds a function. Stored in DB.
    2. Tracker is created anew and seeded from DB (since_sha set) -> body_tokens is None.
    3. Commit 2 in Git renames the function and makes a small edit.
    4. Worker processes Commit 2: tracker re-parses Commit 1 to restore body_tokens on demand.
    5. Step 3 matches the function via similarity (>= 0.8) -> same canonical_id, change_type 'rename'.
    """
    db = SessionLocal()
    repo_dir = tempfile.mkdtemp()
    try:
        test_repo = Repository(
            url=f"file://{repo_dir}_incr",
            name="test-incr-repo",
            owner="test",
            status="analyzing"
        )
        db.add(test_repo)
        db.commit()
        db.refresh(test_repo)

        repo = git.Repo.init(repo_dir)
        repo.config_writer().set_value("user", "name", "Incr Tester").release()
        repo.config_writer().set_value("user", "email", "incr@example.com").release()

        # Commit 1: function process_data
        code_v1 = """
def process_data(data):
    a = 1
    b = 2
    c = 3
    d = 4
    return data + a + b + c + d
"""
        fpath = os.path.join(repo_dir, "data.py")
        with open(fpath, "w") as f:
            f.write(code_v1)
        repo.index.add(["data.py"])
        gc1 = repo.index.commit("Initial data processor")

        c1 = Commit(
            repository_id=test_repo.id,
            sha=gc1.hexsha,
            author="Incr Tester",
            message=gc1.message,
            timestamp=datetime.utcnow()
        )
        db.add(c1)
        db.flush()

        initial_tracker = FunctionIdentityTracker(test_repo.id, db, repo_path=repo_dir)
        process_commit_ast(c1, repo_dir, db, changed_files=["data.py"], identity_tracker=initial_tracker)
        db.commit()

        # Verify initial function in DB
        fn1 = db.query(Function).filter(Function.commit_id == c1.id).first()
        assert fn1 is not None
        canonical_id = fn1.canonical_id
        assert fn1.name == "process_data"
        assert fn1.change_type == "new"

        # Now simulate incremental run:
        # A new tracker is initialized and seeded from DB
        seeded_tracker = FunctionIdentityTracker(test_repo.id, db, repo_path=repo_dir)
        seeded_tracker.seed_from_db(since_sha=c1.sha)
        key = ("data.py", "process_data")
        assert key in seeded_tracker.latest
        assert seeded_tracker.latest[key]["body_tokens"] is None  # seeded without tokens

        # Commit 2: Rename to transform_data with a small edit (1 token changed out of many)
        code_v2 = """
def transform_data(data):
    a = 1
    b = 2
    c = 3
    d = 5
    return data + a + b + c + d
"""
        with open(fpath, "w") as f:
            f.write(code_v2)
        repo.index.add(["data.py"])
        gc2 = repo.index.commit("Rename and small edit")

        c2 = Commit(
            repository_id=test_repo.id,
            sha=gc2.hexsha,
            author="Incr Tester",
            message=gc2.message,
            timestamp=datetime.utcnow()
        )
        db.add(c2)
        db.flush()

        # Process commit 2 using seeded_tracker
        process_commit_ast(c2, repo_dir, db, changed_files=["data.py"], identity_tracker=seeded_tracker)
        db.commit()

        # Verify function in Commit 2
        fn2 = db.query(Function).filter(Function.commit_id == c2.id, Function.change_type != "deleted").first()
        assert fn2 is not None
        assert fn2.name == "transform_data"
        # Must reuse the same canonical_id!
        assert fn2.canonical_id == canonical_id
        # Change type must be 'rename'
        assert fn2.change_type == "rename"
        # Similarity must be >= 0.8
        assert fn2.similarity is not None
        assert fn2.similarity >= 0.8

    finally:
        db.query(Function).filter(
            Function.commit_id.in_(
                db.query(Commit.id).filter(Commit.repository_id == test_repo.id)
            )
        ).delete(synchronize_session=False)
        db.query(Commit).filter(Commit.repository_id == test_repo.id).delete(synchronize_session=False)
        db.query(Repository).filter(Repository.id == test_repo.id).delete(synchronize_session=False)
        db.commit()
        db.close()
        shutil.rmtree(repo_dir, ignore_errors=True)


