"""
The CI PR bot must authenticate, use the real risk forecast, and FAIL LOUDLY.
The script runs against a fake FORGE server (no network, no database).
"""
import importlib.util
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "scripts" / "forge_pr_check.py"
WORKFLOW = ROOT / ".github" / "workflows" / "forge-analysis.yml"

spec = importlib.util.spec_from_file_location("forge_pr_check", SCRIPT)
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

TOKEN = "tok_abcdef123456"
RISK = [
    {"file_path": "internal/gateway/gateway.go", "risk_score": 100.0, "risk_level": "critical",
     "reason": "changes very frequently (12 edits)\nand has 4 authors", "churn": 12, "loc": 640,
     "complexity": 9.5, "author_count": 4},
    {"file_path": "src/util.py", "risk_score": 62.0, "risk_level": "warning", "reason": "complex", "churn": 5,
     "loc": 90, "complexity": 6.0, "author_count": 2},
    {"file_path": "src/ok.py", "risk_score": 12.0, "risk_level": "watchlist", "reason": "", "churn": 1,
     "loc": 20, "complexity": 1.0, "author_count": 1},
]


@pytest.fixture
def forge():
    """Fake FORGE API. `state` lets a test change behaviour."""
    state = {"password": "right-pw", "risk_status": 200, "seen_auth": []}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/auth/login" and body.get("password") == state["password"]:
                self._send(200, {"access_token": TOKEN, "token_type": "bearer"})
            else:
                self._send(401, {"detail": "Incorrect email or password"})

        def do_GET(self):
            auth = self.headers.get("Authorization")
            state["seen_auth"].append((self.path, auth))
            if auth != f"Bearer {TOKEN}":
                return self._send(401, {"detail": "Not authenticated"})   # what the bot used to hit
            if self.path == "/repositories/7":
                return self._send(200, {"id": 7, "status": state.get("repo_status", "completed")})
            if self.path == "/analytics/repositories/7/risk-prediction":
                return self._send(state["risk_status"], RISK if state["risk_status"] == 200 else {"detail": "boom"})
            self._send(404, {"detail": "nope"})

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{srv.server_port}"
    yield state
    srv.shutdown()


@pytest.fixture
def env(tmp_path, forge):
    changed = tmp_path / "changed.txt"
    changed.write_text("internal/gateway/gateway.go\nsrc/new_file.py\n")
    return {
        "FORGE_API_URL": forge["url"], "FORGE_EMAIL": "ci@example.com", "FORGE_PASSWORD": "right-pw",
        "FORGE_REPO_ID": "7", "CHANGED_FILES": str(changed), "COMMENT_FILE": str(tmp_path / "comment.md"),
    }


def run_cli(env):
    """Run the script exactly like the workflow does; returns the CompletedProcess."""
    import os
    return subprocess.run([sys.executable, str(SCRIPT)], env={**os.environ, **env},
                          capture_output=True, text=True, timeout=60)


# ── success: authenticated, real risk forecast ───────────────────────────────

def test_authenticates_and_posts_the_risk_for_changed_files(env, forge):
    r = run_cli(env)
    assert r.returncode == 0, r.stdout + r.stderr
    body = Path(env["COMMENT_FILE"]).read_text()
    assert "gateway.go" in body and "Critical (100)" in body and "🔴" in body
    assert "| 12 | 640 |" in body                                  # real churn + real LOC
    assert "src/util.py" not in body and "src/new_file.py" not in body   # not changed in the PR
    assert bot.MARKER in body
    # every FORGE call after login carried the bearer token
    assert forge["seen_auth"] and all(a == f"Bearer {TOKEN}" for _, a in forge["seen_auth"])
    assert f"::add-mask::{TOKEN}" in r.stdout                      # token is masked in CI logs
    assert TOKEN not in body


# ── fail loudly ──────────────────────────────────────────────────────────────

def test_wrong_password_fails_the_workflow_visibly(env, forge):
    r = run_cli({**env, "FORGE_PASSWORD": "wrong"})
    assert r.returncode == 1
    assert "::error" in r.stdout and "HTTP 401" in r.stdout
    assert not Path(env["COMMENT_FILE"]).exists()                  # no misleading "all clear" comment


def test_server_error_fails_the_workflow(env, forge):
    forge["risk_status"] = 500
    r = run_cli(env)
    assert r.returncode == 1 and "HTTP 500" in r.stdout
    assert not Path(env["COMMENT_FILE"]).exists()


def test_unreachable_server_fails_and_explains_localhost(env):
    r = run_cli({**env, "FORGE_API_URL": "http://127.0.0.1:1"})
    assert r.returncode == 1
    assert "unreachable" in r.stdout and "reachable from the CI runner" in r.stdout


@pytest.mark.parametrize("missing", ["FORGE_API_URL", "FORGE_EMAIL", "FORGE_PASSWORD", "FORGE_REPO_ID"])
def test_missing_secret_fails_naming_it(env, missing):
    r = run_cli({**env, missing: ""})
    assert r.returncode == 1 and missing in r.stdout and "Missing configuration" in r.stdout


def test_repo_id_must_be_numeric(env):
    r = run_cli({**env, "FORGE_REPO_ID": "7; rm -rf /"})
    assert r.returncode == 1 and "FORGE_REPO_ID must be a number" in r.stdout


# ── comment content ──────────────────────────────────────────────────────────

def test_no_risky_changed_files_says_so():
    c = bot.build_comment({"status": "completed"}, RISK, ["docs/readme.py"])
    assert "✅ None of the changed files" in c and "🔴" not in c


def test_watchlist_only_is_not_flagged():
    c = bot.build_comment({"status": "completed"}, RISK, ["src/ok.py"])
    assert "No changed file is critical or warning" in c and "🟡" in c


def test_empty_forecast_is_reported_not_hidden():
    c = bot.build_comment({"status": "completed"}, [], ["a.py"])
    assert "no risk data" in c


def test_in_progress_analysis_is_flagged():
    c = bot.build_comment({"status": "analyzing"}, RISK, ["src/util.py"])
    assert "still analysing" in c and "analyzing" in c


def test_hostile_file_names_and_reasons_cannot_break_the_markdown_table():
    import re
    risk = [{"file_path": "x`|.py", "risk_score": 90, "risk_level": "critical",
             "reason": "a | b\n\n# heading", "churn": 1, "loc": 1, "complexity": 1, "author_count": 1}]
    c = bot.build_comment({}, risk, ["x`|.py"])
    row = next(l for l in c.splitlines() if l.startswith("| 🔴"))
    assert len(re.findall(r"(?<!\\)\|", row)) == 8              # 7 cells; the file name's | is escaped
    assert "x'\\|.py" in row                                      # backtick neutralised, pipe escaped
    reason = next(l for l in c.splitlines() if l.startswith("- "))
    assert reason.endswith("a / b # heading")                      # newlines collapsed, no heading injected


# ── workflow file: the old silent patterns must not come back ────────────────

def test_workflow_has_no_silent_curl_placeholder_url_or_injection():
    wf = WORKFLOW.read_text()
    assert "curl -s " not in wf and "curl -s\n" not in wf
    assert "your-forge-instance" not in wf                          # no placeholder fallback URL
    assert "tj-actions" not in wf                                   # no third-party changed-files action
    assert "steps.changed-files.outputs" not in wf                  # file names never interpolated into scripts
    for secret in ("FORGE_API_URL", "FORGE_EMAIL", "FORGE_PASSWORD", "FORGE_REPO_ID"):
        assert f"secrets.{secret}" in wf
    assert "forge_pr_check.py" in wf and "pull_request_target" not in wf
