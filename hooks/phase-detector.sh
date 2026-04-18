#!/usr/bin/env bash
# =============================================================================
# Cognito — phase-detector.sh
# =============================================================================
# Hook: UserPromptSubmit
# Función: Detecta señales de cambio de fase. SUGIERE (no aplica).
# Versión: 1.0.0
# Portable: macOS, Linux, Windows (Git Bash con Python3)
# =============================================================================

set -uo pipefail

# Resolver COGNITO_DIR: env var, luego parent del script, luego default
if [ -n "${COGNITO_DIR:-}" ]; then
    COGNITO_DIR_RESOLVED="$COGNITO_DIR"
else
    # Fallback: parent del script (cognito/hooks/script.sh -> cognito/)
    _SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    _PARENT_DIR="$(dirname "$_SCRIPT_DIR")"
    if [ -d "$_PARENT_DIR/config" ]; then
        COGNITO_DIR_RESOLVED="$_PARENT_DIR"
    else
        COGNITO_DIR_RESOLVED="$HOME/.claude/cognito"
    fi
fi

# Si el path es MSYS style (/c/...), convertir a Windows-style
if command -v cygpath >/dev/null 2>&1; then
    COGNITO_DIR_RESOLVED=$(cygpath -m "$COGNITO_DIR_RESOLVED" 2>/dev/null || echo "$COGNITO_DIR_RESOLVED")
fi

export COGNITO_DIR_RESOLVED

mkdir -p "$COGNITO_DIR_RESOLVED/logs" 2>/dev/null || true

# Stdin size cap (1 MiB) to protect against pathological payloads.
INPUT_JSON=$(head -c 1048576 2>/dev/null || echo "{}")
export INPUT_JSON

# Toda la lógica en Python para evitar issues de interpolación bash
python3 <<'PYEOF'
import json
import os
import re
import sys
from datetime import datetime, timezone

cognito_dir = os.environ.get("COGNITO_DIR_RESOLVED", "")
state_file = os.path.join(cognito_dir, "config", "_phase-state.json")
triggers_file = os.path.join(cognito_dir, "config", "_passive-triggers.json")
log_file = os.path.join(cognito_dir, "logs", "phase-detector.log")

# Parse input
input_json = os.environ.get("INPUT_JSON", "{}")
try:
    data = json.loads(input_json)
    if not isinstance(data, dict):
        data = {}
except (json.JSONDecodeError, TypeError):
    data = {}
prompt = data.get("prompt", "") if isinstance(data.get("prompt"), str) else ""

# session_id extracted and validated for log-line tagging.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_raw_sid = data.get("session_id") or data.get("sessionId") or ""
if isinstance(_raw_sid, str) and _SESSION_ID_RE.match(_raw_sid):
    SESSION_ID = _raw_sid
else:
    SESSION_ID = "unknown"

def log(msg):
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] [{SESSION_ID}] {msg}\n")
    except Exception:
        pass

if not prompt:
    log("Sin prompt. Salgo.")
    sys.exit(0)

# Fase actual
current_phase = "discovery"
if os.path.exists(state_file):
    try:
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
        current_phase = state.get("current", "discovery")
    except (json.JSONDecodeError, IOError):
        pass

# Triggers
if not os.path.exists(triggers_file):
    log("Triggers file ausente. Salgo.")
    sys.exit(0)

try:
    with open(triggers_file, encoding="utf-8") as f:
        triggers = json.load(f)
except (json.JSONDecodeError, IOError):
    log("Triggers file ilegible. Salgo.")
    sys.exit(0)

prompt_lower = prompt.lower()

def _matches_signal(signal: str, haystack: str) -> bool:
    """Word-boundary match so that 'exploremos' does NOT match inside
    'no exploremos eso'. v1.1.0 fix: pre-1.1 used plain substring,
    which triggered false positives on negated prompts."""
    if not signal:
        return False
    # re.escape to allow multi-word signals ("vamos a ejecutar") as well.
    pattern = r"\b" + re.escape(signal) + r"\b"
    try:
        return bool(re.search(pattern, haystack))
    except re.error:
        return False

# Detección de fase
best_conf = {"high": 3, "medium": 2, "low": 1}
best = None
for rule in triggers.get("phaseDetection", {}).get("rules", []):
    signal = rule.get("signal", "").lower()
    if _matches_signal(signal, prompt_lower):
        conf = rule.get("confidence", "low")
        if best is None or best_conf.get(conf, 0) > best_conf.get(best["confidence"], 0):
            best = {
                "signal": rule["signal"],
                "suggestPhase": rule["suggestPhase"],
                "confidence": conf,
            }

if best and best["suggestPhase"] != current_phase and best["confidence"] in ("high", "medium"):
    log(f'Detectado: "{best["signal"]}" -> sugerir {best["suggestPhase"]} ({best["confidence"]})')
    msg = (
        f'Cognito detecto senal "{best["signal"]}" que sugiere pasar '
        f'de fase "{current_phase}" a "{best["suggestPhase"]}" '
        f'(confianza: {best["confidence"]}). Si aplica, sugiere al usuario: '
        f'/fase {best["suggestPhase"]}. NO apliques el cambio sin confirmacion.'
    )
    print(json.dumps({"systemMessage": msg}))
    sys.exit(0)

# Detección de ancla (with regex timeout protection — patterns come from
# user-controlled config, so a malformed regex must not hang the hook).
for rule in triggers.get("anchorDetection", {}).get("rules", []):
    pat = rule.get("pattern", "").lower().replace("[x]", ".+")
    if not pat:
        continue
    try:
        compiled = re.compile(pat)
    except re.error as exc:
        log(f"Regex invalido en anchor rule '{rule.get('pattern')}': {exc}")
        continue
    try:
        if compiled.search(prompt_lower):
            log(f'Ancla detectada: "{rule["pattern"]}" -> sugerir Divergente')
            msg = (
                f'Cognito detecto posible ancla cognitiva ("{rule["pattern"]}"). '
                f'Considera activar modo Divergente. Sugerencia: /modo divergente o /divergir.'
            )
            print(json.dumps({"systemMessage": msg}))
            sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        log(f"Error evaluando anchor rule: {exc}")
        continue

log(f"Sin deteccion. Fase actual: {current_phase}")
sys.exit(0)
PYEOF

exit $?
