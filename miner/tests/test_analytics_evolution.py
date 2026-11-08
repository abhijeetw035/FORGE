import os
import shutil
import tempfile
import pytest
import git
from datetime import datetime
from database import SessionLocal
from models import Repository, Commit, Function
from worker import process_commit_ast
from services.identity import FunctionIdentityTracker


def test_function_evolution_tracking_and_renames():
    """
    Test end-to-end:
    - One function edited across multiple commits appears as ONE function (one canonical_id)
      with multiple versions.
    - A renamed function shows was_renamed = True.
    """
    db = SessionLocal()
    repo_dir = tempfile.mkdtemp()
    try:
        # Create a test repository in DB
        test_repo = Repository(
            url=f"file://{repo_dir}",
            name="test-identity-repo",
            owner="test",
            status="analyzing"
        )
        db.add(test_repo)
        db.commit()
        db.refresh(test_repo)

        # Initialize git repo
        git_repo = git.Repo.init(repo_dir)
        git_repo.config_writer().set_value("user", "name", "Tester").release()
        git_repo.config_writer().set_value("user", "email", "tester@example.com").release()

        tracker = FunctionIdentityTracker(test_repo.id, db, repo_path=repo_dir)

        # -------------------------------------------------------------
        # Commit 1: add calculate()
        # -------------------------------------------------------------
        code_c1 = """
def calculate(a, b):
    return a + b
"""
        fpath = os.path.join(repo_dir, "calc.py")
        with open(fpath, "w") as f:
            f.write(code_c1)
        git_repo.index.add(["calc.py"])
        gc1 = git_repo.index.commit("Add calculate")

        c1 = Commit(
            repository_id=test_repo.id,
            sha=gc1.hexsha,
            author="Tester",
            message=gc1.message,
            timestamp=datetime.utcnow()
        )
        db.add(c1)
        db.flush()
        process_commit_ast(c1, repo_dir, db, changed_files=["calc.py"], identity_tracker=tracker)
        db.commit()

        # -------------------------------------------------------------
        # Commit 2: edit calculate() body
        # -------------------------------------------------------------
        code_c2 = """
def calculate(a, b):
    # added check
    if a < 0:
        return 0
    return a + b
"""
        with open(fpath, "w") as f:
            f.write(code_c2)
        git_repo.index.add(["calc.py"])
        gc2 = git_repo.index.commit("Edit calculate body")

        c2 = Commit(
            repository_id=test_repo.id,
            sha=gc2.hexsha,
            author="Tester",
            message=gc2.message,
            timestamp=datetime.utcnow()
        )
        db.add(c2)
        db.flush()
        process_commit_ast(c2, repo_dir, db, changed_files=["calc.py"], identity_tracker=tracker)
        db.commit()

        # -------------------------------------------------------------
        # Commit 3: rename calculate() to compute()
        # -------------------------------------------------------------
        code_c3 = """
def compute(a, b):
    if a < 0:
        return 0
    return a + b
"""
        with open(fpath, "w") as f:
            f.write(code_c3)
        git_repo.index.add(["calc.py"])
        gc3 = git_repo.index.commit("Rename calculate to compute")

        c3 = Commit(
            repository_id=test_repo.id,
            sha=gc3.hexsha,
            author="Tester",
            message=gc3.message,
            timestamp=datetime.utcnow()
        )
        db.add(c3)
        db.flush()
        process_commit_ast(c3, repo_dir, db, changed_files=["calc.py"], identity_tracker=tracker)
        db.commit()

        # -------------------------------------------------------------
        # Query functions and simulate analytics function evolution
        # -------------------------------------------------------------
        db_funcs = (
            db.query(Function)
            .join(Commit, Function.commit_id == Commit.id)
            .filter(Commit.repository_id == test_repo.id)
            .order_by(Commit.timestamp.asc(), Function.id.asc())
            .all()
        )

        # Check canonical IDs
        cids = {fn.canonical_id for fn in db_funcs if fn.canonical_id}
        # MUST BE EXACTLY ONE CANONICAL ID across all 3 commits
        assert len(cids) == 1, f"Expected 1 canonical_id, got: {cids}"

        canonical_id = list(cids)[0]
        funcs_for_cid = [fn for fn in db_funcs if fn.canonical_id == canonical_id]
        assert len(funcs_for_cid) == 3

        # Commit 1: new
        assert funcs_for_cid[0].name == 'calculate'
        assert funcs_for_cid[0].change_type == 'new'

        # Commit 2: edit
        assert funcs_for_cid[1].name == 'calculate'
        assert funcs_for_cid[1].change_type == 'edit'
        assert funcs_for_cid[1].complexity > funcs_for_cid[0].complexity

        # Commit 3: rename
        assert funcs_for_cid[2].name == 'compute'
        assert funcs_for_cid[2].change_type == 'rename'

        # Check evolution aggregation logic
        names = {fn.qualified_name or fn.name for fn in funcs_for_cid}
        was_renamed = len(names) > 1
        assert was_renamed is True

        paths = {fn.file_path for fn in funcs_for_cid}
        was_moved = len(paths) > 1
        assert was_moved is False

        # Complexity trend
        delta = funcs_for_cid[-1].complexity - funcs_for_cid[0].complexity
        assert delta > 0

    finally:
        # Cleanup
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

