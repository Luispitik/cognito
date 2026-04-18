#!/usr/bin/env bash
# =============================================================================
# Cognito — mode-injector.sh
# =============================================================================
# Hook: UserPromptSubmit  (changed in v1.1.0, was PreToolUse which fired N
#                          times per turn and re-injected the same payload).
# Función: Inyecta instrucciones de los modos activos una vez por turno.
# Versión: 1.1.0
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

mkdir -p "$COGNITO_DIR_RESOLVED/logs" 2>/dev/null || true

# Stdin size cap: 1 MiB is more than enough for any Claude hook payload.
INPUT_JSON=$(head -c 1048576 2>/dev/null || echo "{}")
export INPUT_JSON

python3 <<'PYEOF'
import json
import os
import sys
from datetime import datetime, timezone

import re as _re

cognito_dir = os.environ.get("COGNITO_DIR_RESOLVED", "")
state_file = os.path.join(cognito_dir, "config", "_phase-state.json")
modes_file = os.path.join(cognito_dir, "config", "_modes.json")
phases_file = os.path.join(cognito_dir, "config", "_phases.json")
operator_file = os.path.join(cognito_dir, "config", "_operator-config.json")
log_file = os.path.join(cognito_dir, "logs", "mode-injector.log")

# Extract session_id from stdin or phase-state fallback, validated.
_SESSION_ID_RE = _re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_raw_input = os.environ.get("INPUT_JSON", "{}")
try:
    _data = json.loads(_raw_input)
    if not isinstance(_data, dict):
        _data = {}
except (json.JSONDecodeError, TypeError):
    _data = {}
_raw_sid = _data.get("session_id") or _data.get("sessionId") or ""
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

# Check requireds
for f in (state_file, modes_file, phases_file, operator_file):
    if not os.path.exists(f):
        log(f"Falta config: {f}. Salgo.")
        sys.exit(0)

try:
    with open(state_file, encoding="utf-8") as f:
        state = json.load(f)
    with open(modes_file, encoding="utf-8") as f:
        modes = json.load(f)
    with open(phases_file, encoding="utf-8") as f:
        phases = json.load(f)
    with open(operator_file, encoding="utf-8") as f:
        operator = json.load(f)
except (json.JSONDecodeError, IOError) as e:
    log(f"Config ilegible: {e}. Salgo.")
    sys.exit(0)

current_phase = state.get("current", "discovery")
override_modes = state.get("overrideModes", [])
enabled_modes = set(operator.get("modes", {}).get("enabled", []))
disabled_modes = set(operator.get("modes", {}).get("disabled", []))

phase_def = phases.get("phases", {}).get(current_phase, {})
default_modes = phase_def.get("defaultModes", [])

# Unión: defaults + overrides, filtrando enabled y disabled
active = []
for m in default_modes + override_modes:
    if m in enabled_modes and m not in disabled_modes and m not in active:
        active.append(m)

if not active:
    log("Sin modos activos.")
    sys.exit(0)

log(f"Modos activos: {','.join(active)} (fase: {current_phase})")

# Leer SKILL.md completo de cada modo (v1.1.0 quita el truncado a 60 lineas
# que cortaba secciones criticas como "Triggers de auto-activacion").
# Budget total de ~16k chars para proteger el contexto. Si se excede, cortamos
# al primer separador "---" o "\n##" del archivo; ultimo recurso: truncate.
MAX_TOTAL_CHARS = 16000
MAX_PER_MODE = 6000

def _smart_truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = text[:limit]
    # Prefer cutting at section boundaries to keep meaning intact.
    for marker in ("\n---\n", "\n## ", "\n# "):
        idx = head.rfind(marker)
        if idx > limit // 2:
            return head[:idx] + "\n\n[truncated]"
    return head + "\n\n[truncated]"

instructions_parts = []
running_total = 0
for mode in active:
    mode_def = modes.get("modes", {}).get(mode, {})
    skill_rel = mode_def.get("skillPath", "")
    if not skill_rel:
        continue
    skill_full = os.path.join(cognito_dir, skill_rel)
    if not os.path.exists(skill_full):
        log(f"SKILL.md de '{mode}' no encontrado en {skill_full}")
        continue
    try:
        with open(skill_full, encoding="utf-8") as f:
            content = f.read()
    except IOError:
        log(f"No se pudo leer {skill_full}")
        continue

    chunk = _smart_truncate(content, MAX_PER_MODE)
    header = f"\n\n---\n## Modo activo: {mode}\n\n"
    projected = running_total + len(header) + len(chunk)
    if projected > MAX_TOTAL_CHARS:
        remaining = MAX_TOTAL_CHARS - running_total - len(header)
        if remaining < 300:
            log(f"Budget agotado antes de '{mode}', omitido")
            break
        chunk = _smart_truncate(chunk, remaining)
    instructions_parts.append(header + chunk)
    running_total += len(header) + len(chunk)

# Bridge opcional a Sinapsis (auto-detect; si no hay, degrada silencioso)
try:
    bridge_script = os.path.join(cognito_dir, "integrations", "sinapsis_bridge.py")
    if os.path.exists(bridge_script):
        sys.path.insert(0, os.path.join(cognito_dir, "integrations"))
        from sinapsis_bridge import SinapsisBridge  # type: ignore
        bridge = SinapsisBridge.detect(operator_config=operator)
        modes_que_usan_instincts = {"ejecutor", "verificador", "auditor"}
        if bridge.available and any(m in modes_que_usan_instincts for m in active):
            injection = bridge.render_injection(limit=8)
            if injection:
                instructions_parts.append(injection)
                log(f"Sinapsis bridge activo (v{bridge.version or '?'}): instincts inyectados")
except Exception as e:  # noqa: BLE001 — tolerancia máxima: si rompe, degradamos
    log(f"Bridge Sinapsis no disponible (degradando a standalone): {e}")

if instructions_parts:
    full = "".join(instructions_parts)
    print(json.dumps({"systemMessage": full}))

sys.exit(0)
PYEOF

exit $?
