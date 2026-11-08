import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import User, Repository, Commit, Function
from dependencies import get_current_user


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_setup(db_session):
    # Create test user
    user = User(
        email=f"testuser_{datetime.utcnow().timestamp()}@example.com",
        password_hash="fakehash"
    )
    db_session.add(user)
    db_session.flush()

    repo = Repository(
        owner_id=user.id,
        url=f"https://github.com/test/repo_{user.id}",
        name="test-repo",
        owner="test",
        status="completed"
    )
    db_session.add(repo)
    db_session.flush()

    # Override current user dependency
    app.dependency_overrides[get_current_user] = lambda: user

    yield {
        "user": user,
        "repo": repo,
        "db": db_session
    }

    # Cleanup
    app.dependency_overrides.clear()
    db_session.rollback()
    db_session.query(Function).filter(
        Function.commit_id.in_(
            db_session.query(Commit.id).filter(Commit.repository_id == repo.id)
        )
    ).delete(synchronize_session=False)
    db_session.query(Commit).filter(Commit.repository_id == repo.id).delete(synchronize_session=False)
    db_session.query(Repository).filter(Repository.id == repo.id).delete(synchronize_session=False)
    db_session.query(User).filter(User.id == user.id).delete(synchronize_session=False)
    db_session.commit()


def test_real_function_evolution_endpoint(test_setup):
    db = test_setup["db"]
    repo = test_setup["repo"]
    client = TestClient(app)

    # Commit 1: function calculate(a)
    c1 = Commit(
        repository_id=repo.id,
        sha="1111111111111111111111111111111111111111",
        author="Alice",
        message="Initial calculate",
        timestamp=datetime(2026, 1, 1, 10, 0, 0)
    )
    db.add(c1)
    db.flush()

    f1 = Function(
        commit_id=c1.id,
        name="calculate",
        qualified_name="calculate",
        file_path="math.py",
        start_line=1,
        end_line=5,
        complexity=1,
        lines_of_code=5,
        body_hash="hash_v1",
        signature_hash="sig_v1",
        canonical_id="calc_canonical01",
        change_type="new",
        similarity=None
    )
    db.add(f1)

    # Commit 2: parameter added to calculate(a, b) with same body
    c2 = Commit(
        repository_id=repo.id,
        sha="2222222222222222222222222222222222222222",
        author="Alice",
        message="Add parameter to calculate",
        timestamp=datetime(2026, 1, 2, 10, 0, 0)
    )
    db.add(c2)
    db.flush()

    f2 = Function(
        commit_id=c2.id,
        name="calculate",
        qualified_name="calculate",
        file_path="math.py",
        start_line=1,
        end_line=5,
        complexity=1,
        lines_of_code=5,
        body_hash="hash_v1",       # same body
        signature_hash="sig_v2",    # signature changed!
        canonical_id="calc_canonical01",
        change_type="edit",
        similarity=None
    )
    db.add(f2)

    # Commit 3: rename calculate to compute, same body
    c3 = Commit(
        repository_id=repo.id,
        sha="3333333333333333333333333333333333333333",
        author="Bob",
        message="Rename calculate to compute",
        timestamp=datetime(2026, 1, 3, 10, 0, 0)
    )
    db.add(c3)
    db.flush()

    f3 = Function(
        commit_id=c3.id,
        name="compute",
        qualified_name="compute",
        file_path="math.py",
        start_line=1,
        end_line=5,
        complexity=2,
        lines_of_code=5,
        body_hash="hash_v2",
        signature_hash="sig_v3",
        canonical_id="calc_canonical01",
        change_type="rename",
        similarity=1.0
    )
    db.add(f3)
    db.commit()

    # Call real FastAPI endpoint
    response = client.get(f"/analytics/repositories/{repo.id}/function-evolution")
    assert response.status_code == 200, response.text
    data = response.json()

    # Must have exactly 1 function timeline with canonical_id 'calc_canonical01'
    assert len(data) == 1
    func_data = data[0]
    assert func_data["canonical_id"] == "calc_canonical01"
    assert func_data["name"] == "compute"
    assert func_data["qualified_name"] == "compute"
    assert func_data["was_renamed"] is True
    assert func_data["was_moved"] is False

    # Versions:
    # 1. Initial version
    # 2. Parameter added (signature_hash changed, same body) -> MUST BE RECORDED AS NEW VERSION
    # 3. Rename with body change
    assert len(func_data["versions"]) == 3
    versions = func_data["versions"]
    assert versions[0]["name"] == "calculate"
    assert versions[1]["name"] == "calculate"
    assert versions[1]["change_type"] == "edit"
    assert versions[2]["name"] == "compute"
    assert versions[2]["change_type"] == "rename"


def test_deleted_rows_excluded_from_analytics(test_setup):
    db = test_setup["db"]
    repo = test_setup["repo"]
    client = TestClient(app)

    # Commit 1: Add two active functions
    c1 = Commit(
        repository_id=repo.id,
        sha="aaaa111111111111111111111111111111111111",
        author="Alice",
        message="Add active functions",
        timestamp=datetime(2026, 1, 1, 10, 0, 0)
    )
    db.add(c1)
    db.flush()

    f1 = Function(
        commit_id=c1.id,
        name="active1",
        qualified_name="active1",
        file_path="service.py",
        start_line=1,
        end_line=10,
        complexity=2,
        lines_of_code=10,
        canonical_id="cid_active1",
        change_type="new"
    )
    f2 = Function(
        commit_id=c1.id,
        name="active2",
        qualified_name="active2",
        file_path="service.py",
        start_line=11,
        end_line=20,
        complexity=3,
        lines_of_code=10,
        canonical_id="cid_active2",
        change_type="new"
    )
    db.add_all([f1, f2])

    # Commit 2: active1 remains active, while active2 is deleted (tombstone)
    c2 = Commit(
        repository_id=repo.id,
        sha="bbbb222222222222222222222222222222222222",
        author="Alice",
        message="Keep active1 and delete active2",
        timestamp=datetime(2026, 1, 2, 10, 0, 0)
    )
    db.add(c2)
    db.flush()

    f1_c2 = Function(
        commit_id=c2.id,
        name="active1",
        qualified_name="active1",
        file_path="service.py",
        start_line=1,
        end_line=10,
        complexity=2,
        lines_of_code=10,
        canonical_id="cid_active1",
        change_type="unchanged"
    )
    f_del = Function(
        commit_id=c2.id,
        name="active2",
        qualified_name="active2",
        file_path="service.py",
        start_line=11,
        end_line=20,
        complexity=3,
        lines_of_code=0,
        canonical_id="cid_active2",
        change_type="deleted"
    )
    db.add_all([f1_c2, f_del])
    db.commit()

    # 1. Test Heatmap: count must be 3 active function rows across commits, NOT 4 (deleted excluded)
    resp_heat = client.get(f"/analytics/repositories/{repo.id}/heatmap")
    assert resp_heat.status_code == 200
    heat_data = resp_heat.json()
    assert len(heat_data) == 1
    assert heat_data[0]["name"] == "service.py"
    assert heat_data[0]["score"] == 3  # NOT 4

    # 2. Test Timeline: commit 2 must count 1 active function, NOT 2 (deleted excluded)
    resp_time = client.get(f"/analytics/repositories/{repo.id}/timeline")
    assert resp_time.status_code == 200
    time_data = resp_time.json()
    assert len(time_data) == 2
    # Commit 1 has 2 functions
    c1_stat = next(t for t in time_data if t["sha"] == "aaaa111")
    assert c1_stat["function_count"] == 2
    # Commit 2 has 1 active function (deleted active2 is excluded)
    c2_stat = next(t for t in time_data if t["sha"] == "bbbb222")
    assert c2_stat["function_count"] == 1  # NOT 2

    # 3. Test Contributors: Alice added 3 active function rows, NOT 4
    resp_contrib = client.get(f"/analytics/repositories/{repo.id}/contributors")
    assert resp_contrib.status_code == 200
    contrib_data = resp_contrib.json()
    assert len(contrib_data) == 1
    assert contrib_data[0]["functions_added"] == 3  # NOT 4
