#!/usr/bin/env bash
# =============================================================================
# Cognito — gate-validator.sh
# =============================================================================
# Hook: PreToolUse (matcher: Write, Edit)
# Función: Valida anti-patrones. Bloquea (exit 1) o avisa (exit 0 + mensaje).
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

mkdir -p "$COGNITO_DIR_RESOLVED/logs" 2>/dev/null || true

INPUT_JSON=$(cat 2>/dev/null || echo "{}")
export INPUT_JSON

python3 <<'PYEOF'
import fnmatch
import json
import os
import re
import sys
from datetime import datetime, timezone

cognito_dir = os.environ.get("COGNITO_DIR_RESOLVED", "")
triggers_file = os.path.join(cognito_dir, "config", "_passive-triggers.json")
operator_file = os.path.join(cognito_dir, "config", "_operator-config.json")
log_file = os.path.join(cognito_dir, "logs", "gate-validator.log")

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
    if not isinstance(data, dict):
        data = {}
except (json.JSONDecodeError, TypeError):
    data = {}

tool_input = data.get("tool_input", data.get("input", {}))
if not isinstance(tool_input, dict):
    tool_input = {}

file_path = tool_input.get("file_path", "")
content = tool_input.get("content", tool_input.get("new_string", ""))

if not file_path:
    log("Sin file_path. Salgo.")
    sys.exit(0)

# Config
for f in (triggers_file, operator_file):
    if not os.path.exists(f):
        log(f"Config ausente: {f}. Salgo sin validar.")
        sys.exit(0)

try:
    with open(triggers_file, encoding="utf-8") as f:
        triggers = json.load(f)
    with open(operator_file, encoding="utf-8") as f:
        operator = json.load(f)
except (json.JSONDecodeError, IOError) as e:
    log(f"Config ilegible: {e}")
    sys.exit(0)

enabled_gates = set(operator.get("gates", {}).get("enabled", []))
disabled_gates = set(operator.get("gates", {}).get("disabled", []))

violations = []
file_basename = os.path.basename(file_path)

for rule in triggers.get("gates", {}).get("rules", []):
    gate_id = rule.get("id", "")
    if gate_id not in enabled_gates or gate_id in disabled_gates:
        continue

    files_affected = rule.get("filesAffected", ["*"])
    matches_file = any(
        fnmatch.fnmatch(file_path, pat) or fnmatch.fnmatch(file_basename, pat)
        for pat in files_affected
    )
    if not matches_file:
        continue

    pattern = rule.get("pattern", "")
    try:
        if re.search(pattern, content, re.IGNORECASE):
            violations.append({
                "id": gate_id,
                "action": rule.get("action", "warn"),
                "message": rule.get("message", ""),
                "override": rule.get("override"),
            })
    except re.error:
        continue

if not violations:
    log(f"Sin violaciones para {file_path}")
    sys.exit(0)

ids = [v["id"] for v in violations]
log(f"Violaciones para {file_path}: {ids}")

has_block = any(v.get("action") == "block" for v in violations)

parts = []
for v in violations:
    emoji = "[BLOCK]" if v["action"] == "block" else "[WARN]"
    line = f"{emoji} Gate [{v['id']}]: {v['message']}"
    if v.get("override"):
        line += f" Override: {v['override']}"
    parts.append(line)
message = "\n".join(parts)

if has_block:
    print(message, file=sys.stderr)
    sys.exit(1)
else:
    print(json.dumps({"systemMessage": message}))
    sys.exit(0)
PYEOF

exit $?
