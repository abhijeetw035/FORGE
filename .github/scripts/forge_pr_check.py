#!/usr/bin/env python3
"""
FORGE PR check: log in to the FORGE API, fetch the repository's risk forecast,
match it against the files changed in a pull request and write a markdown comment.

Fails LOUDLY: any HTTP error (wrong password, 401, 404, 500, unreachable server),
missing configuration or a malformed response ends in a non-zero exit and a
`::error::` annotation, so the workflow goes red instead of silently posting nothing.

Configuration (environment):
  FORGE_API_URL     base URL of a FORGE instance reachable from the runner
  FORGE_EMAIL       login of the dedicated CI user (it must OWN the repository in FORGE)
  FORGE_PASSWORD
  FORGE_REPO_ID     numeric id of the repository in FORGE
  CHANGED_FILES     path of a text file with one changed file per line
  COMMENT_FILE      where to write the markdown comment
"""
import json
import os
import sys
import urllib.error
import urllib.request

MARKER = "<!-- forge-analysis -->"
TIMEOUT = 30
LEVELS = {  # risk_level -> (emoji, label)
    "critical": ("🔴", "Critical"),
    "warning": ("🟠", "Warning"),
    "watchlist": ("🟡", "Watchlist"),
}


class CIError(Exception):
    """Something the workflow must fail on."""


# ── HTTP ─────────────────────────────────────────────────────────────────────

def _request(method, url, token=None, payload=None):
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:200]
        raise CIError(f"{method} {url} -> HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise CIError(f"{method} {url} unreachable: {e.reason}. "
                      "FORGE_API_URL must be reachable from the CI runner (localhost is not).")
    except ValueError:
        raise CIError(f"{method} {url} returned something that is not JSON")


def login(api_url, email, password):
    body = _request("POST", f"{api_url}/auth/login", payload={"email": email, "password": password})
    token = (body or {}).get("access_token")
    if not token:
        raise CIError("FORGE login returned no access_token")
    print(f"::add-mask::{token}")          # never let the token show up in logs
    return token


# ── matching + rendering ─────────────────────────────────────────────────────

def _norm(path):
    path = path.strip().replace("\\", "/")
    return path[2:] if path.startswith("./") else path


def _code(text):
    # a "|" would split a table cell even inside a code span, so it must be escaped
    return "`" + str(text).replace("`", "'").replace("\n", " ").replace("|", "\\|") + "`"


def _plain(text, limit=220):
    return " ".join(str(text).split()).replace("|", "/").replace("`", "'")[:limit]


def match_changed_files(predictions, changed_files):
    """Risk rows for the changed files, riskiest first."""
    changed = {_norm(f) for f in changed_files if f.strip()}
    rows = [p for p in predictions if _norm(p.get("file_path", "")) in changed]
    return sorted(rows, key=lambda p: p.get("risk_score", 0), reverse=True)


def build_comment(repo, predictions, changed_files):
    lines = ["## 🔥 FORGE Code Analysis", ""]
    status = (repo or {}).get("status")
    if status and status != "completed":
        lines += [f"> ⚠️ FORGE is still analysing this repository (status: **{_plain(status)}**), "
                  "so the numbers below may be out of date.", ""]

    if not predictions:
        lines += ["FORGE has no risk data for this repository yet "
                  "(it needs at least two analysed files). Nothing to report for this PR.", ""]
    else:
        hits = match_changed_files(predictions, changed_files)
        flagged = [h for h in hits if h.get("risk_level") in ("critical", "warning")]
        if not hits:
            lines += [f"✅ None of the changed files is among this repository's {len(predictions)} "
                      "highest-risk files.", ""]
        else:
            if flagged:
                lines += [f"⚠️ **{len(flagged)}** changed file(s) are critical/warning risk. "
                          "Review them carefully.", ""]
            else:
                lines += ["No changed file is critical or warning risk; some are on the watchlist.", ""]
            lines += ["| | File | Risk | Churn (commits) | LOC | Complexity | Authors |",
                      "|---|---|---|---|---|---|---|"]
            for h in hits:
                emoji, label = LEVELS.get(h.get("risk_level"), ("⚪", "Unknown"))
                lines.append(
                    f"| {emoji} | {_code(h.get('file_path'))} | {label} ({h.get('risk_score', 0):.0f}) "
                    f"| {h.get('churn', 0)} | {h.get('loc', 0)} | {h.get('complexity', 0):.1f} "
                    f"| {h.get('author_count', 0)} |")
            lines.append("")
            for h in flagged:
                if h.get("reason"):
                    lines.append(f"- {_code(h['file_path'])}: {_plain(h['reason'])}")
            if flagged:
                lines.append("")

    lines += ["---",
              "*Powered by [FORGE](https://github.com/abhijeetw035/FORGE). Risk is relative to the other "
              "files in this repository (Isolation Forest over all files; FORGE reports the 20 highest-risk), "
              "not an absolute score.*",
              MARKER]
    return "\n".join(lines) + "\n"


# ── main ─────────────────────────────────────────────────────────────────────

def main(env=os.environ):
    required = ["FORGE_API_URL", "FORGE_EMAIL", "FORGE_PASSWORD", "FORGE_REPO_ID", "CHANGED_FILES", "COMMENT_FILE"]
    missing = [k for k in required if not env.get(k, "").strip()]
    if missing:
        raise CIError("Missing configuration: " + ", ".join(missing)
                      + " (set the FORGE_* repository secrets)")

    api = env["FORGE_API_URL"].strip().rstrip("/")
    if not api.startswith(("https://", "http://")):
        raise CIError("FORGE_API_URL must start with https://")
    repo_id = env["FORGE_REPO_ID"].strip()
    if not repo_id.isdigit():
        raise CIError("FORGE_REPO_ID must be a number")

    with open(env["CHANGED_FILES"], encoding="utf-8") as f:
        changed = [line for line in f.read().splitlines() if line.strip()]

    token = login(api, env["FORGE_EMAIL"], env["FORGE_PASSWORD"])
    repo = _request("GET", f"{api}/repositories/{repo_id}", token)
    risk = _request("GET", f"{api}/analytics/repositories/{repo_id}/risk-prediction", token)
    if not isinstance(risk, list):
        raise CIError("risk-prediction returned an unexpected response")

    comment = build_comment(repo, risk, changed)
    with open(env["COMMENT_FILE"], "w", encoding="utf-8") as f:
        f.write(comment)
    hits = match_changed_files(risk, changed)
    print(f"FORGE: {len(changed)} changed file(s), {len(hits)} found in the risk forecast "
          f"({sum(h.get('risk_level') in ('critical', 'warning') for h in hits)} critical/warning).")


if __name__ == "__main__":
    try:
        main()
    except CIError as e:
        print(f"::error title=FORGE analysis failed::{e}")
        sys.exit(1)
