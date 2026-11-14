import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import User, Repository, Commit, Function, FileMetrics
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
    # Also remove any extra repositories a test created for this user, and their metrics
    extra_ids = [r.id for r in db_session.query(Repository.id).filter(Repository.owner_id == user.id)]
    db_session.query(FileMetrics).filter(FileMetrics.repository_id.in_(extra_ids)).delete(synchronize_session=False)
    db_session.query(Repository).filter(Repository.owner_id == user.id).delete(synchronize_session=False)
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

    # 1. Test Heatmap: reads file_metrics, NOT function rows. The file has 3 function
    #    rows but was touched by only 2 commits and has 40 real lines.
    db.add(FileMetrics(repository_id=repo.id, file_path="service.py", churn=2, loc=40))
    db.commit()
    resp_heat = client.get(f"/analytics/repositories/{repo.id}/heatmap")
    assert resp_heat.status_code == 200
    heat_data = resp_heat.json()
    assert len(heat_data) == 1
    assert heat_data[0] == {"name": "service.py", "size": 40, "score": 2}  # NOT 3 function rows

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


def test_snapshot_timeline_small_file_does_not_skew_average(test_setup):
    """
    Item 1 test: a commit that touches one tiny file must not move the
    repo-wide average complexity by an unreasonable amount.

    Setup:
      Commit 1 → large.py  : 50 functions, each complexity 2.0  → avg 2.0
      Commit 2 → small.py  :  1 function,  complexity 15.0      → avg 2.25
      Repo-wide delta: (50*2.0 + 1*15.0)/51 ≈ 2.25 — well under 0.5 swing
    """
    db = test_setup["db"]
    repo = test_setup["repo"]
    client = TestClient(app)

    # --- Commit 1: 50 functions in large.py, all complexity 2.0 ---
    c1 = Commit(
        repository_id=repo.id,
        sha="cc11111111111111111111111111111111111111",
        author="Alice",
        message="Add large.py with 50 functions",
        timestamp=datetime(2026, 2, 1, 10, 0, 0),
    )
    db.add(c1)
    db.flush()

    for i in range(50):
        db.add(Function(
            commit_id=c1.id,
            name=f"fn_{i}",
            qualified_name=f"fn_{i}",
            file_path="large.py",
            start_line=i * 5 + 1,
            end_line=i * 5 + 5,
            complexity=2,
            lines_of_code=5,
            canonical_id=f"canon_large_{i}",
            change_type="new",
        ))

    # --- Commit 2: 1 function in small.py, complexity 15 ---
    c2 = Commit(
        repository_id=repo.id,
        sha="cc22222222222222222222222222222222222222",
        author="Alice",
        message="Add small.py with one complex function",
        timestamp=datetime(2026, 2, 2, 10, 0, 0),
    )
    db.add(c2)
    db.flush()

    db.add(Function(
        commit_id=c2.id,
        name="complex_fn",
        qualified_name="complex_fn",
        file_path="small.py",
        start_line=1,
        end_line=20,
        complexity=15,
        lines_of_code=20,
        canonical_id="canon_small_0",
        change_type="new",
    ))
    db.commit()

    resp = client.get(f"/analytics/repositories/{repo.id}/timeline")
    assert resp.status_code == 200, resp.text
    time_data = resp.json()

    # Must have exactly 2 data points (one per commit that has function data)
    assert len(time_data) == 2, f"Expected 2 timeline points, got {len(time_data)}: {time_data}"

    c1_stat = next(t for t in time_data if t["sha"] == "cc11111")
    c2_stat = next(t for t in time_data if t["sha"] == "cc22222")

    # Commit 1: 50 functions, avg 2.0
    assert c1_stat["function_count"] == 50
    assert abs(c1_stat["avg_complexity"] - 2.0) < 0.05, f"c1 avg_complexity {c1_stat['avg_complexity']} != 2.0"

    # Commit 2: 51 functions (snapshot: large.py still there + small.py), avg ≈ 2.25
    assert c2_stat["function_count"] == 51, f"Expected 51 total functions, got {c2_stat['function_count']}"
    expected_avg = round((50 * 2.0 + 1 * 15.0) / 51, 2)  # ≈ 2.25
    assert abs(c2_stat["avg_complexity"] - expected_avg) < 0.05, (
        f"c2 avg_complexity {c2_stat['avg_complexity']} != expected {expected_avg}"
    )

    # The key assertion: one small file must NOT move the average by more than 0.5
    delta = abs(c2_stat["avg_complexity"] - c1_stat["avg_complexity"])
    assert delta < 0.5, (
        f"Adding one small file moved avg complexity by {delta:.2f} — too much! "
        f"(was {c1_stat['avg_complexity']}, now {c2_stat['avg_complexity']})"
    )


def test_heatmap_uses_real_churn_and_loc_ordered_and_filtered(test_setup):
    """score = commits touching the file, size = real LOC; empty/deleted files excluded."""
    db, repo = test_setup["db"], test_setup["repo"]
    client = TestClient(app)

    # Many function rows must NOT inflate churn/size.
    c = Commit(repository_id=repo.id, sha="dd" * 20, author="A", message="m",
               timestamp=datetime(2026, 3, 1))
    db.add(c)
    db.flush()
    for i in range(104):
        db.add(Function(commit_id=c.id, name=f"f{i}", qualified_name=f"f{i}", file_path="gateway.go",
                        start_line=1, end_line=500, complexity=1, canonical_id=f"g{i}", change_type="new"))
    db.add_all([
        FileMetrics(repository_id=repo.id, file_path="gateway.go", churn=8, loc=762),
        FileMetrics(repository_id=repo.id, file_path="busy.py", churn=30, loc=120),
        FileMetrics(repository_id=repo.id, file_path="empty.txt", churn=99, loc=0),   # no lines -> hidden
    ])
    db.commit()

    data = client.get(f"/analytics/repositories/{repo.id}/heatmap").json()
    assert [d["name"] for d in data] == ["busy.py", "gateway.go"]            # churn desc, loc=0 dropped
    gw = next(d for d in data if d["name"] == "gateway.go")
    assert (gw["score"], gw["size"]) == (8, 762)                              # not 104 / summed spans


def test_heatmap_does_not_leak_other_repositories(test_setup):
    db, repo = test_setup["db"], test_setup["repo"]
    other = Repository(url="https://github.com/o/other", name="other", owner="o",
                       owner_id=repo.owner_id, status="completed")
    db.add(other)
    db.commit()
    db.add_all([FileMetrics(repository_id=other.id, file_path="x.py", churn=5, loc=10),
                FileMetrics(repository_id=repo.id, file_path="mine.py", churn=1, loc=3)])
    db.commit()
    data = TestClient(app).get(f"/analytics/repositories/{repo.id}/heatmap").json()
    assert [d["name"] for d in data] == ["mine.py"]


def test_function_evolution_limit_is_applied_in_sql_not_after_loading_everything(test_setup):
    """
    20 functions with 1..20 versions each. limit=3 must return the 3 most-changed
    (in order) AND must not even load rows for the other 17 (this used to load
    every row of a large repo into Python and got the API OOM-killed).
    """
    from sqlalchemy import event
    from database import engine

    db, repo = test_setup["db"], test_setup["repo"]
    client = TestClient(app)

    commits = []
    for i in range(20):
        c = Commit(repository_id=repo.id, sha=f"{i:040x}", author="A", message=f"c{i}",
                   timestamp=datetime(2026, 1, 1 + i))
        db.add(c)
        commits.append(c)
    db.flush()
    for fn_idx in range(20):                       # fn_idx 19 has 20 versions, fn_idx 0 has 1
        for v in range(fn_idx + 1):
            db.add(Function(commit_id=commits[v].id, name=f"fn{fn_idx}", qualified_name=f"fn{fn_idx}",
                            file_path="f.py", start_line=1, end_line=3, complexity=v + 1,
                            canonical_id=f"canon{fn_idx:02d}", change_type="edit", body_hash=f"b{fn_idx}_{v}"))
    db.commit()

    fetched = {"rows": 0}

    @event.listens_for(engine, "after_cursor_execute")
    def count_rows(conn, cursor, statement, parameters, context, executemany):
        if "FROM functions" in statement and "JOIN commits" in statement and "GROUP BY" not in statement:
            fetched["rows"] += cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

    try:
        r = client.get(f"/analytics/repositories/{repo.id}/function-evolution?limit=3")
    finally:
        event.remove(engine, "after_cursor_execute", count_rows)

    assert r.status_code == 200
    data = r.json()
    assert [d["canonical_id"] for d in data] == ["canon19", "canon18", "canon17"]
    assert [d["commit_count"] for d in data] == [20, 19, 18]
    assert fetched["rows"] == 20 + 19 + 18         # only the top 3 functions' rows were loaded (not 210)


@pytest.mark.parametrize("limit", [0, -1, 201, 100000])
def test_function_evolution_limit_is_bounded(test_setup, limit):
    r = TestClient(app).get(f"/analytics/repositories/{test_setup['repo'].id}/function-evolution?limit={limit}")
    assert r.status_code == 422
