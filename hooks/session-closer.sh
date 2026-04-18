#!/usr/bin/env bash
# =============================================================================
# Cognito — session-closer.sh
# =============================================================================
# Hook: Stop
# Función: Registra métricas de la sesión al cerrarla.
# Versión: 1.0.0
# =============================================================================

set -uo pipefail

if [ -n "${COGNITO_DIR:-}" ]; then
    COGNITO_DIR_RESOLVED="$COGNITO_DIR"
else
    _SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    _PARENT_DIR="$(dirname "$_SCRIPT_DIR")"
    if [ -d "$_PARENT_DIR/config" ]; then
        COGNITO_DIR_RESOLVED="$_PARENT_DIR"
    else
        COGNITO_DIR_RESOLVED="$HOME/.claude/cognito"
    fi
fi

if command -v cygpath >/dev/null 2>&1; then
    COGNITO_DIR_RESOLVED=$(cygpath -m "$COGNITO_DIR_RESOLVED" 2>/dev/null || echo "$COGNITO_DIR_RESOLVED")
fi

export COGNITO_DIR_RESOLVED

mkdir -p "$COGNITO_DIR_RESOLVED/logs" "$COGNITO_DIR_RESOLVED/sessions" "$COGNITO_DIR_RESOLVED/logs/archive" 2>/dev/null || true

# Stdin size cap (1 MiB) to prevent memory exhaustion on malformed payloads.
INPUT_JSON=$(head -c 1048576 2>/dev/null || echo "{}")
export INPUT_JSON

python3 <<'PYEOF'
import json
import os
import sys
from datetime import datetime, timezone

cognito_dir = os.environ.get("COGNITO_DIR_RESOLVED", "")
state_file = os.path.join(cognito_dir, "config", "_phase-state.json")
logs_dir = os.path.join(cognito_dir, "logs")
sessions_dir = os.path.join(cognito_dir, "sessions")
session_log = os.path.join(logs_dir, "session-closer.log")

def log(msg):
    try:
        with open(session_log, "a", encoding="utf-8") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

# Parse input
input_json = os.environ.get("INPUT_JSON", "{}")
try:
    data = json.loads(input_json)
    if not isinstance(data, dict):
        data = {}
except (json.JSONDecodeError, TypeError):
    data = {}

import re as _re
_SESSION_ID_RE = _re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
raw_session_id = data.get("session_id") or data.get("sessionId")
if isinstance(raw_session_id, str) and _SESSION_ID_RE.match(raw_session_id):
    session_id = raw_session_id
    # When the harness provides session_id only at close time (but not to
    # the other hooks during the session), log lines will carry "unknown".
    # partition_and_count() treats those as ours too — see below.
else:
    if raw_session_id:
        log(f"session_id invalido (descartado): {raw_session_id!r}")
    now = datetime.now(timezone.utc)
    session_id = f"session-{now.strftime('%Y%m%d-%H%M%S')}"

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Fase actual
current_phase = "unknown"
state = None
if os.path.exists(state_file):
    try:
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
        current_phase = state.get("current", "unknown")
    except (json.JSONDecodeError, IOError):
        pass

# Métricas scoped to THIS session_id. v1.1.0 fix: pre-1.1 counted lifetime
# log lines (never rotated) so every session reported accumulated totals.
# Now we:
#   1. Tag every log line with [session_id] (in each hook).
#   2. Count only lines carrying this session's id, plus any "[unknown]"
#      lines (hooks fall back to that tag when the harness does not pass
#      session_id — treating them as ours is safer than leaking stale state
#      across sessions).
#   3. After counting, move those lines to logs/archive/{session_id}.log
#      so the live log file does not grow unbounded.
SESSION_TAG = f"[{session_id}]"
UNKNOWN_TAG = "[unknown]"

def _is_mine(line: str) -> bool:
    return SESSION_TAG in line or UNKNOWN_TAG in line

def partition_and_count(log_file: str, substring: str) -> int:
    """Return count of matches for this session, rewrite log file to drop
    those lines, and append them to the per-session archive."""
    if not os.path.exists(log_file):
        return 0
    try:
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
    except IOError:
        return 0

    mine_all = [ln for ln in lines if _is_mine(ln)]
    others = [ln for ln in lines if not _is_mine(ln)]
    count = sum(1 for ln in mine_all if substring in ln)

    archive_file = os.path.join(logs_dir, "archive", f"{session_id}.log")
    try:
        if mine_all:
            with open(archive_file, "a", encoding="utf-8") as f:
                f.write(f"# --- from {os.path.basename(log_file)} ---\n")
                f.writelines(mine_all)
        # Rewrite live log with only other-session lines. Keeps parallel
        # sessions intact; atomically replaces via temp file.
        tmp = log_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(others)
        os.replace(tmp, log_file)
    except IOError as e:
        log(f"No se pudo rotar {log_file}: {e}")

    return count

gates_triggered = partition_and_count(os.path.join(logs_dir, "gate-validator.log"), "Violaciones para")
mode_injections = partition_and_count(os.path.join(logs_dir, "mode-injector.log"), "Modos activos")
phase_detections = partition_and_count(os.path.join(logs_dir, "phase-detector.log"), "Detectado:")

record = {
    "sessionId": session_id,
    "closedAt": timestamp,
    "phaseAtClose": current_phase,
    "metrics": {
        "gatesTriggered": gates_triggered,
        "modeInjections": mode_injections,
        "phaseDetections": phase_detections,
    },
}

# Escribir sesion (defensa en profundidad: realpath + prefix check)
session_file = os.path.join(sessions_dir, f"{session_id}.json")
try:
    sessions_dir_real = os.path.realpath(sessions_dir)
    session_file_real = os.path.realpath(session_file)
    if not session_file_real.startswith(sessions_dir_real + os.sep):
        log(f"Path escape detectado: {session_file_real} fuera de {sessions_dir_real}")
        sys.exit(0)
    with open(session_file_real, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
except IOError as e:
    log(f"Error escribiendo session file: {e}")
    sys.exit(0)

log(
    f"Sesion {session_id} cerrada. Fase: {current_phase}. "
    f"Gates: {gates_triggered}. Injections: {mode_injections}. Detections: {phase_detections}."
)

# Actualizar state con sessionId
if state is not None:
    state["sessionId"] = session_id
    state["lastUpdatedBy"] = "session-closer"
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        log(f"Error actualizando state: {e}")

sys.exit(0)
PYEOF

exit $?
