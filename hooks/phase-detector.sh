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

# Leer stdin completo
INPUT_JSON=$(cat 2>/dev/null || echo "{}")
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

def log(msg):
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

# Parse input
input_json = os.environ.get("INPUT_JSON", "{}")
try:
    data = json.loads(input_json)
    prompt = data.get("prompt", "") if isinstance(data, dict) else ""
except (json.JSONDecodeError, TypeError):
    prompt = ""

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

# Detección de fase
best_conf = {"high": 3, "medium": 2, "low": 1}
best = None
for rule in triggers.get("phaseDetection", {}).get("rules", []):
    signal = rule.get("signal", "").lower()
    if signal and signal in prompt_lower:
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

# Detección de ancla
for rule in triggers.get("anchorDetection", {}).get("rules", []):
    pat = rule.get("pattern", "").lower().replace("[x]", ".+")
    try:
        if re.search(pat, prompt_lower):
            log(f'Ancla detectada: "{rule["pattern"]}" -> sugerir Divergente')
            msg = (
                f'Cognito detecto posible ancla cognitiva ("{rule["pattern"]}"). '
                f'Considera activar modo Divergente. Sugerencia: /modo divergente o /divergir.'
            )
            print(json.dumps({"systemMessage": msg}))
            sys.exit(0)
    except re.error:
        continue

log(f"Sin deteccion. Fase actual: {current_phase}")
sys.exit(0)
PYEOF

exit $?
