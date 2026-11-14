"""
Repository URL allowlist (SSRF protection).

Anything a user submits ends up in `git clone`, so only https URLs of the form
https://<allowed host>/<owner>/<repo> are accepted. This is an ALLOWLIST on
purpose: blocking private IPs is fragile (DNS rebinding, IPv6 forms, decimal
IPs, redirects). The same module is mirrored in miner/services/url_validation.py
and re-checked right before cloning. Keep the two files identical.
"""
import os
import re
from typing import Iterable, Optional
from urllib.parse import urlparse

DEFAULT_ALLOWED_HOSTS = "github.com,gitlab.com"
# owner/repo: letters, digits, _ . - only; optional .git; optional trailing slash
PATH_RE = re.compile(r"^/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?(\.git)?/?$")


def allowed_hosts() -> set:
    raw = os.getenv("ALLOWED_GIT_HOSTS", DEFAULT_ALLOWED_HOSTS)
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def validate_repo_url(value: str, hosts: Optional[Iterable[str]] = None) -> str:
    """Return the normalised URL or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError("URL must be a string")
    v = value.strip()
    if any(ord(c) <= 32 or ord(c) == 127 for c in v):
        raise ValueError("URL must not contain spaces or control characters")

    u = urlparse(v)
    if u.scheme != "https":
        raise ValueError("Only https URLs are allowed")
    try:
        port = u.port
    except ValueError:
        raise ValueError("Invalid port in URL")
    if u.username or u.password or port is not None:
        raise ValueError("Credentials and ports are not allowed in the URL")

    allowed = {h.lower() for h in hosts} if hosts is not None else allowed_hosts()
    if (u.hostname or "").lower() not in allowed:
        raise ValueError("Host not allowed")

    if not PATH_RE.match(u.path) or u.query or u.fragment or u.params:
        raise ValueError("URL must look like https://github.com/owner/repo")
    if any(seg in (".", "..") for seg in u.path.split("/")):
        raise ValueError("URL must look like https://github.com/owner/repo")

    path = u.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]          # x and x.git are the same repository
    return f"https://{u.hostname.lower()}{path}"
