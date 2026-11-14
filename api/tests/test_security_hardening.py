"""SSRF allowlist on POST /repositories, fail-fast SECRET_KEY, and CORS."""
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError

from main import app
from models import User
from dependencies import get_current_user
from schemas import RepositoryCreate

API_DIR = Path(__file__).resolve().parents[1]
client = TestClient(app)


# ── SSRF: repository URL allowlist ───────────────────────────────────────────

BAD_URLS = [
    "file:///etc/passwd",
    "http://github.com/a/b",
    "https://169.254.169.254/latest",
    "https://user:pw@github.com/a/b",
    "https://evil.com/a/b",
    "https://github.com:8443/a/b",
]


@pytest.fixture
def authed():
    app.dependency_overrides[get_current_user] = lambda: User(id=1, email="t@example.com", password_hash="x")
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize("url", BAD_URLS)
def test_bad_repository_urls_return_422(authed, url):
    r = client.post("/repositories/", json={"url": url})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("url", BAD_URLS)
def test_schema_rejects_bad_urls(url):
    with pytest.raises(ValidationError):
        RepositoryCreate(url=url)


def test_good_url_is_accepted_and_normalised():
    assert RepositoryCreate(url="https://github.com/fastapi/fastapi").url == "https://github.com/fastapi/fastapi"
    assert RepositoryCreate(url="https://GitHub.com/a/b.git/").url == "https://github.com/a/b"


def test_api_and_miner_validators_are_identical():
    """The miner re-validates with a mirrored copy; they must never drift apart."""
    api = (API_DIR / "utils" / "url_validation.py").read_text()
    miner = (API_DIR.parent / "miner" / "services" / "url_validation.py").read_text()
    assert api == miner


# ── SECRET_KEY: fail fast ────────────────────────────────────────────────────

def _import_security(env_overrides):
    env = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"}
    env.update(env_overrides)
    return subprocess.run([sys.executable, "-c", "import utils.security"],
                          cwd=API_DIR, env=env, capture_output=True, text=True)


@pytest.mark.parametrize("env", [
    {},                                                                  # not set
    {"SECRET_KEY": ""},
    {"SECRET_KEY": "your-secret-key-change-this-in-production"},          # the old public default
    {"SECRET_KEY": "short"},
    {"SECRET_KEY": "CHANGE_ME" + "x" * 40},
])
def test_app_refuses_to_start_without_a_strong_secret_key(env):
    r = _import_security(env)
    assert r.returncode != 0
    assert "SECRET_KEY must be set" in r.stderr


def test_strong_key_is_accepted():
    assert _import_security({"SECRET_KEY": "a" * 32}).returncode == 0


def test_token_signed_with_the_old_default_key_is_rejected():
    forged = jwt.encode(
        {"sub": "admin@example.com", "exp": datetime.utcnow() + timedelta(days=1)},
        "your-secret-key-change-this-in-production", algorithm="HS256")
    r = client.get("/repositories/", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


# ── CORS ─────────────────────────────────────────────────────────────────────

def _preflight(origin):
    return client.options("/repositories/", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })


def test_preflight_from_unlisted_origin_gets_no_allow_origin_header():
    r = _preflight("http://evil.com")
    assert "access-control-allow-origin" not in r.headers


def test_preflight_from_configured_origin_is_allowed():
    r = _preflight("http://localhost:3000")
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r.headers["access-control-allow-credentials"] == "true"


def test_only_needed_headers_are_allowed():
    r = _preflight("http://localhost:3000")
    allowed = r.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed and "content-type" in allowed and "*" not in allowed
