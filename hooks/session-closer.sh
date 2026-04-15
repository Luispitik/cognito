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

mkdir -p "$COGNITO_DIR_RESOLVED/logs" "$COGNITO_DIR_RESOLVED/sessions" 2>/dev/null || true

INPUT_JSON=$(cat 2>/dev/null || echo "{}")
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

session_id = data.get("session_id") or data.get("sessionId")
if not session_id:
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

# Métricas
def count_log_lines(log_file, substring):
    if not os.path.exists(log_file):
        return 0
    try:
        with open(log_file, encoding="utf-8") as f:
            return sum(1 for line in f if substring in line)
    except IOError:
        return 0

gates_triggered = count_log_lines(os.path.join(logs_dir, "gate-validator.log"), "Violaciones para")
mode_injections = count_log_lines(os.path.join(logs_dir, "mode-injector.log"), "Modos activos")
phase_detections = count_log_lines(os.path.join(logs_dir, "phase-detector.log"), "Detectado:")

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

# Escribir sesión
session_file = os.path.join(sessions_dir, f"{session_id}.json")
try:
    with open(session_file, "w", encoding="utf-8") as f:
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
