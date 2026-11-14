"""clone_repository must refresh an existing clone so incremental runs see new commits."""
import os
import shutil
import tempfile

import git
import pytest

from services.git_service import GitService


def _commit(repo, name, body):
    path = os.path.join(repo.working_tree_dir, name)
    open(path, "w").write(body)
    repo.index.add([name])
    actor = git.Actor("T", "t@x.com")
    return repo.index.commit(f"add {name}", author=actor, committer=actor)


@pytest.fixture
def remote_and_service():
    remote_dir, storage = tempfile.mkdtemp(), tempfile.mkdtemp()
    remote = git.Repo.init(remote_dir)
    _commit(remote, "a.py", "x=1\n")
    # strict=False: these tests clone local fixture repos (file paths), which the
    # production allowlist rightly refuses. URL security is tested in test_url_security.py.
    yield remote, GitService(storage, strict=False), remote_dir
    shutil.rmtree(remote_dir, ignore_errors=True)
    shutil.rmtree(storage, ignore_errors=True)


def test_existing_clone_is_updated_with_new_upstream_commits(remote_and_service):
    remote, svc, url = remote_and_service
    path = svc.clone_repository(url, 1)
    first = git.Repo(path).head.commit.hexsha

    new = _commit(remote, "b.py", "y=2\n")           # upstream moves on
    assert svc.clone_repository(url, 1) == path       # same dir, refreshed

    local = git.Repo(path)
    assert local.head.commit.hexsha == new.hexsha != first
    assert [c["sha"] for c in svc.get_new_commits(path, since_sha=first)] == [new.hexsha]
    assert os.path.exists(os.path.join(path, "b.py"))


def test_unchanged_upstream_is_a_noop(remote_and_service):
    remote, svc, url = remote_and_service
    path = svc.clone_repository(url, 1)
    sha = git.Repo(path).head.commit.hexsha
    svc.clone_repository(url, 1)
    assert git.Repo(path).head.commit.hexsha == sha


def test_force_pushed_history_is_followed(remote_and_service):
    remote, svc, url = remote_and_service
    path = svc.clone_repository(url, 1)
    _commit(remote, "b.py", "y=2\n")
    remote.git.update_environment(GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@x.com",
                                  GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@x.com")
    remote.git.commit("--amend", "-m", "rewritten")   
    svc.clone_repository(url, 1)                      # clone now holds the amended tip
    remote.git.commit("--amend", "-m", "rewritten again")   # force-push: the tip the clone holds is gone
    svc.clone_repository(url, 1)
    assert git.Repo(path).head.commit.hexsha == remote.head.commit.hexsha


def test_corrupt_or_half_cloned_directory_is_recloned(remote_and_service):
    remote, svc, url = remote_and_service
    broken = os.path.join(svc.storage_path, "repo_2")
    os.makedirs(os.path.join(broken, ".git"))          # looks like a clone, is not one
    path = svc.clone_repository(url, 2)
    assert git.Repo(path).head.commit.hexsha == remote.head.commit.hexsha
