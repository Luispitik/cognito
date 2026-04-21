"""Shared utilities for Cognito hooks.

Importable both as a package (`from hooks.python import _common`) and as a
standalone script (`python3 hooks/python/phase_detector.py`) — see the
`_import_common()` helper each sibling module uses at the top of the file.

Kept deliberately small — anything that would pull a third-party dependency
lives elsewhere. These helpers used to live as duplicated 30-line blocks
inside each `.sh` heredoc; consolidating them here closes the Maintainability
gap flagged in the v1.1 ISO 25010 audit.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "read_stdin_capped",
    "parse_input_json",
    "extract_session_id",
    "resolve_cognito_dir",
    "make_logger",
    "load_json",
    "STDIN_CAP_BYTES",
]

# 1 MiB — matches the `head -c 1048576` cap the bash wrappers used to enforce.
STDIN_CAP_BYTES = 1 << 20

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_DEFAULT_INSTALL_DIR = Path.home() / ".claude" / "cognito"


def read_stdin_capped(limit: int = STDIN_CAP_BYTES) -> str:
    """Read at most `limit` bytes from stdin. Empty string if nothing or error.

    The bash wrappers set INPUT_JSON via `head -c 1048576`. When the module is
    invoked via `python3 -m hooks.python.<name>` directly, stdin is raw and we
    must cap it ourselves to avoid memory exhaustion on pathological input.
    """
    env_override = os.environ.get("INPUT_JSON")
    if env_override is not None:
        return env_override[:limit]
    try:
        data = sys.stdin.buffer.read(limit + 1)
    except (OSError, AttributeError):
        return ""
    if len(data) > limit:
        data = data[:limit]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def parse_input_json(raw: str) -> dict:
    """Parse JSON input, always returning a dict (never None / not a list)."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def extract_session_id(data: dict, fallback: str = "unknown") -> str:
    """Extract and validate session_id from hook payload.

    Accepts both `session_id` and `sessionId`. Rejects paths, shell meta and
    anything longer than 64 chars — the bash wrappers used this exact regex
    before v1.2 to prevent path traversal in session-closer.
    """
    raw = data.get("session_id") or data.get("sessionId") or ""
    if isinstance(raw, str) and _SESSION_ID_RE.match(raw):
        return raw
    return fallback


def resolve_cognito_dir() -> Path:
    """Resolve the Cognito install dir using the same precedence as the `.sh` wrappers.

    Precedence:
      1. $COGNITO_DIR_RESOLVED (set by the bash wrapper after cygpath)
      2. $COGNITO_DIR           (raw, the bash wrapper reads it first)
      3. parent of this file     (repo / source-tree dev install)
      4. ~/.claude/cognito       (default install location)
    """
    for env_key in ("COGNITO_DIR_RESOLVED", "COGNITO_DIR"):
        val = os.environ.get(env_key)
        if val:
            return Path(val)

    # hooks/python/_common.py -> parent.parent = repo root candidate.
    here = Path(__file__).resolve()
    candidate = here.parent.parent.parent
    if (candidate / "config").is_dir():
        return candidate

    return _DEFAULT_INSTALL_DIR


def make_logger(cognito_dir: Path, log_name: str, session_id: str):
    """Build a logger closure that writes `[ts] [sid] msg` to `logs/<log_name>`.

    Never raises: any IOError is swallowed so hook execution cannot be blocked
    by a full disk or a read-only mount.
    """
    log_file = cognito_dir / "logs" / log_name
    sid_tag = f"[{session_id}]"

    def log(msg: str) -> None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                f.write(f"[{ts}] {sid_tag} {msg}\n")
        except Exception:  # noqa: BLE001
            pass

    return log


def load_json(path: Path) -> Any | None:
    """Load JSON from `path`, returning None if missing or invalid."""
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def ensure_dirs(cognito_dir: Path, *subdirs: str) -> None:
    """mkdir -p the requested subdirectories under cognito_dir. Never raises."""
    for sub in subdirs:
        try:
            (cognito_dir / sub).mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            pass
