#!/usr/bin/env bash
# =============================================================================
# Cognito — install script (v1.1.0)
# =============================================================================
# Honors the profile YAML: copies only the modes/hooks/gates/templates listed
# under installs:. Idempotent (backs up existing install before overwriting,
# preserves _phase-state.json). Auto-registers hooks in ~/.claude/settings.json
# when jq is available; otherwise prints a paste-ready snippet.
#
# Usage:
#   bash scripts/install.sh --profile=operator
#   bash scripts/install.sh --profile=alumno   --target=/tmp/cognito-test
#   bash scripts/install.sh --profile=public   --skip-settings
#   bash scripts/install.sh --profile=client   --client-intake=./intake.json
# =============================================================================

set -euo pipefail

PROFILE=""
CLIENT_INTAKE=""
TARGET_DIR="${HOME}/.claude/cognito"
SKIP_SETTINGS=0
SETTINGS_FILE="${HOME}/.claude/settings.json"

for arg in "$@"; do
    case "$arg" in
        --profile=*)        PROFILE="${arg#*=}"       ;;
        --client-intake=*)  CLIENT_INTAKE="${arg#*=}" ;;
        --target=*)         TARGET_DIR="${arg#*=}"    ;;
        --settings=*)       SETTINGS_FILE="${arg#*=}" ;;
        --skip-settings)    SKIP_SETTINGS=1           ;;
        --help|-h)
            cat <<'EOF'
Cognito installer (v1.1.0)

Usage: bash scripts/install.sh --profile=<name> [options]

Profiles (defined in profiles/*.yaml):
  operator   Founder / advanced Claude Code operator
  alumno     Learner (pedagogical MVP, 4 modes)
  public     Open source / generic
  client     B2B client (requires --client-intake)

Options:
  --target=PATH         Install directory (default: ~/.claude/cognito)
  --settings=PATH       settings.json to update (default: ~/.claude/settings.json)
  --skip-settings       Do not touch settings.json; print the snippet instead
  --client-intake=PATH  Intake JSON (only for --profile=client)
EOF
            exit 0
            ;;
    esac
done

# --- Required args ---------------------------------------------------------
if [ -z "$PROFILE" ]; then
    echo "Missing --profile. Try --help." >&2
    exit 1
fi

case "$PROFILE" in
    operator|alumno|public|client) ;;
    *)
        echo "Invalid profile '$PROFILE'. Allowed: operator, alumno, public, client." >&2
        exit 1
        ;;
esac

# --- client profile requires --client-intake -------------------------------
# Backported from the v1.0 fix (044d4c4): advertised support must actually work.
if [ "$PROFILE" = "client" ]; then
    if [ -z "$CLIENT_INTAKE" ]; then
        echo "Profile 'client' requires --client-intake=PATH." >&2
        exit 1
    fi
    if [ ! -f "$CLIENT_INTAKE" ]; then
        echo "Intake file not found: $CLIENT_INTAKE" >&2
        exit 1
    fi
fi

# --- Tooling prereqs -------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found in PATH (Cognito requires Python 3.10+)." >&2
    echo "Windows: install from python.org and check 'Add to PATH'." >&2
    exit 1
fi

HAVE_JQ=0
if command -v jq >/dev/null 2>&1; then HAVE_JQ=1; fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PROFILE_FILE="$REPO_DIR/profiles/${PROFILE}.yaml"

if [ ! -f "$PROFILE_FILE" ]; then
    echo "Profile file not found: $PROFILE_FILE" >&2
    exit 1
fi

echo "=========================================="
echo " Cognito install"
echo "=========================================="
echo " profile : $PROFILE"
echo " target  : $TARGET_DIR"
echo " jq      : $([ $HAVE_JQ = 1 ] && echo yes || echo no)"
echo "=========================================="
echo

# --- Parse profile YAML (stdlib-only subset parser) ------------------------
export COGNITO_PROFILE_YAML="$PROFILE_FILE"
INSTALL_PLAN=$(python3 <<'PYEOF'
import json
import os
import sys

path = os.environ["COGNITO_PROFILE_YAML"]
with open(path, encoding="utf-8") as f:
    raw = f.read().splitlines()

out = {"modes": [], "hooks": [], "gates": [], "templates": []}
in_installs = False
current_key = None

def _indent(s: str) -> int:
    return len(s) - len(s.lstrip(" "))

for line in raw:
    if not line.strip() or line.lstrip().startswith("#"):
        continue
    indent = _indent(line)
    stripped = line.strip()
    if indent == 0:
        in_installs = stripped.startswith("installs:")
        current_key = None
        continue
    if not in_installs:
        continue
    if indent == 2 and stripped.endswith(":"):
        key = stripped[:-1].strip()
        current_key = key if key in out else None
        continue
    if indent == 2 and ":" in stripped and not stripped.endswith(":"):
        # inline "gates: []" style
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if key in out and value == "[]":
            out[key] = []
            current_key = None
        continue
    if indent >= 4 and stripped.startswith("- ") and current_key:
        item = stripped[2:].split("#", 1)[0].strip().strip("'\"")
        if item:
            out[current_key].append(item)
json.dump(out, sys.stdout)
PYEOF
)

MODES=$(echo "$INSTALL_PLAN"     | python3 -c "import sys,json;print(' '.join(json.load(sys.stdin)['modes']))")
HOOKS=$(echo "$INSTALL_PLAN"     | python3 -c "import sys,json;print(' '.join(json.load(sys.stdin)['hooks']))")
GATES=$(echo "$INSTALL_PLAN"     | python3 -c "import sys,json;print(' '.join(json.load(sys.stdin)['gates']))")
TEMPLATES=$(echo "$INSTALL_PLAN" | python3 -c "import sys,json;print(' '.join(json.load(sys.stdin)['templates']))")

echo " Profile plan:"
echo "   modes      : ${MODES:-<none>}"
echo "   hooks      : ${HOOKS:-<none>}"
echo "   gates      : ${GATES:-<none>}"
echo "   templates  : ${TEMPLATES:-<none>}"
echo

# --- Idempotency: back up existing install --------------------------------
if [ -d "$TARGET_DIR" ]; then
    BACKUP_ROOT="${HOME}/.claude/cognito-backups"
    TS=$(date -u +"%Y%m%dT%H%M%SZ")
    BACKUP_DIR="$BACKUP_ROOT/$TS"
    mkdir -p "$BACKUP_ROOT"
    echo "-> Existing install detected. Backing up to $BACKUP_DIR"
    cp -r "$TARGET_DIR" "$BACKUP_DIR"
fi

mkdir -p "$TARGET_DIR"/{config,hooks,logs,sessions,integrations}
mkdir -p "$TARGET_DIR/logs/archive"

# --- Copy client intake (after target dir exists) --------------------------
if [ "$PROFILE" = "client" ] && [ -n "$CLIENT_INTAKE" ]; then
    cp "$CLIENT_INTAKE" "$TARGET_DIR/config/intake.json"
    echo "-> Intake copied to $TARGET_DIR/config/intake.json"
fi

# --- Copy hooks listed in the profile -------------------------------------
echo "-> Installing hooks..."
for hook in $HOOKS; do
    src="$REPO_DIR/hooks/${hook}.sh"
    if [ ! -f "$src" ]; then
        echo "   (skip) hook source missing: $src" >&2
        continue
    fi
    cp "$src" "$TARGET_DIR/hooks/"
    chmod +x "$TARGET_DIR/hooks/${hook}.sh"
    echo "   ok  hooks/${hook}.sh"
done

# --- Copy all config JSONs (runtime-filtered, not install-filtered) -------
echo "-> Installing config..."
cp "$REPO_DIR/config/"*.json "$TARGET_DIR/config/"

# Preserve existing _phase-state.json (idempotency). Otherwise seed from default.
if [ -f "$TARGET_DIR/config/_phase-state.json" ] && [ -s "$TARGET_DIR/config/_phase-state.json" ]; then
    echo "   ok  preserved _phase-state.json"
else
    cp "$REPO_DIR/config/_phase-state.default.json" "$TARGET_DIR/config/_phase-state.json"
    echo "   ok  seeded _phase-state.json from default"
fi

# --- Copy templates listed in the profile ---------------------------------
mkdir -p "$TARGET_DIR/templates"
echo "-> Installing templates..."
for tpl in $TEMPLATES; do
    src="$REPO_DIR/templates/${tpl}.md"
    if [ ! -f "$src" ]; then
        echo "   (skip) template source missing: $src" >&2
        continue
    fi
    cp "$src" "$TARGET_DIR/templates/"
    echo "   ok  templates/${tpl}.md"
done

# Phases and SKILL.md are architectural invariants (not per-profile).
cp -r "$REPO_DIR/phases" "$TARGET_DIR/"
cp "$REPO_DIR/SKILL.md" "$TARGET_DIR/"

# Sinapsis bridge (runtime detection — safe to ship always).
if [ -d "$REPO_DIR/integrations" ]; then
    cp -r "$REPO_DIR/integrations/." "$TARGET_DIR/integrations/"
fi

# --- Copy modes into ~/.claude/skills/{mode}/ -----------------------------
echo "-> Installing modes (skills)..."
mkdir -p "$HOME/.claude/skills"
for mode in $MODES; do
    src="$REPO_DIR/modes/$mode"
    if [ ! -d "$src" ]; then
        echo "   (skip) mode source missing: $src" >&2
        continue
    fi
    cp -r "$src" "$HOME/.claude/skills/"
    echo "   ok  skills/$mode"
done

# --- Copy commands: the ones tied to each enabled mode + meta commands ----
echo "-> Installing commands..."
mkdir -p "$HOME/.claude/commands"

# Map mode -> slash command filename.
# Keeps operator UX identical to v1.0 for modes that ship by default.
MODE_CMD_MAP_DIVERGENTE="divergir"
MODE_CMD_MAP_VERIFICADOR="verificar"
MODE_CMD_MAP_DEVILS_ADVOCATE="devils-advocate"
MODE_CMD_MAP_CONSOLIDADOR="consolidar"
MODE_CMD_MAP_EJECUTOR="ejecutar"
MODE_CMD_MAP_ESTRATEGA="estratega"
MODE_CMD_MAP_AUDITOR="auditar"

copy_cmd() {
    local name="$1"
    local src="$REPO_DIR/commands/${name}.md"
    if [ -f "$src" ]; then
        cp "$src" "$HOME/.claude/commands/"
        echo "   ok  commands/${name}.md"
    fi
}

# Meta commands always installed if any hook is active.
copy_cmd "fase"
copy_cmd "modo"
copy_cmd "cognition-status"
copy_cmd "cognition-gate"

for mode in $MODES; do
    case "$mode" in
        divergente)       copy_cmd "$MODE_CMD_MAP_DIVERGENTE"       ;;
        verificador)      copy_cmd "$MODE_CMD_MAP_VERIFICADOR"      ;;
        devils-advocate)  copy_cmd "$MODE_CMD_MAP_DEVILS_ADVOCATE"  ;;
        consolidador)     copy_cmd "$MODE_CMD_MAP_CONSOLIDADOR"     ;;
        ejecutor)         copy_cmd "$MODE_CMD_MAP_EJECUTOR"         ;;
        estratega)        copy_cmd "$MODE_CMD_MAP_ESTRATEGA"        ;;
        auditor)          copy_cmd "$MODE_CMD_MAP_AUDITOR"          ;;
    esac
done

# --- Apply profile-derived runtime config ---------------------------------
echo "-> Applying profile config..."
export COGNITO_CONFIG_PATH="$TARGET_DIR/config/_operator-config.json"
export COGNITO_PROFILE="$PROFILE"
export COGNITO_INSTALL_PLAN="$INSTALL_PLAN"
python3 <<'PYEOF'
import json, os, sys
path = os.environ["COGNITO_CONFIG_PATH"]
profile = os.environ["COGNITO_PROFILE"]
plan = json.loads(os.environ["COGNITO_INSTALL_PLAN"])

try:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
except Exception as e:
    print(f"  config read error: {e}", file=sys.stderr)
    sys.exit(1)
if not isinstance(cfg, dict):
    print("  _operator-config.json must be a JSON object.", file=sys.stderr)
    sys.exit(1)

cfg["profile"] = profile

# Modes: enabled = profile list, disabled = everything else minus enabled
ALL_MODES = [
    "divergente", "verificador", "devils-advocate", "consolidador",
    "ejecutor", "estratega", "auditor",
]
modes_block = cfg.setdefault("modes", {})
modes_block["enabled"] = list(plan.get("modes", []))
modes_block["disabled"] = [m for m in ALL_MODES if m not in modes_block["enabled"]]

# Gates: honor the profile gates list verbatim. Preserve any extra keys the
# user may have added (e.g. custom gates) by only overwriting "enabled".
gates_block = cfg.setdefault("gates", {})
gates_block["enabled"] = list(plan.get("gates", []))

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
print(f"  ok  profile applied: {profile}")
print(f"  ok  modes enabled  : {', '.join(modes_block['enabled']) or '<none>'}")
print(f"  ok  gates enabled  : {', '.join(gates_block['enabled']) or '<none>'}")
PYEOF
unset COGNITO_CONFIG_PATH COGNITO_PROFILE COGNITO_INSTALL_PLAN

# --- Auto-register hooks in settings.json ---------------------------------
SNIPPET_FILE="$TARGET_DIR/.settings-snippet.json"

# Build the snippet from the enabled hooks only.
export COGNITO_HOOKS_DIR="$TARGET_DIR/hooks"
export COGNITO_ENABLED_HOOKS="$HOOKS"
python3 <<'PYEOF' > "$SNIPPET_FILE"
import json, os
hooks_dir = os.environ["COGNITO_HOOKS_DIR"]
enabled = os.environ["COGNITO_ENABLED_HOOKS"].split()

HOOK_META = {
    "phase-detector":  ("UserPromptSubmit", False, None),
    "mode-injector":   ("UserPromptSubmit", False, None),
    "gate-validator":  ("PreToolUse",       True,  {"tool": ["Write", "Edit"]}),
    "session-closer":  ("Stop",             False, None),
}

out = {}
for name in enabled:
    meta = HOOK_META.get(name)
    if not meta:
        continue
    event, blocking, matchers = meta
    entry = {
        "name": f"cognito-{name}",
        "command": f"bash {hooks_dir}/{name}.sh",
        "blocking": blocking,
    }
    if matchers:
        entry["matchers"] = matchers
    out.setdefault(event, []).append(entry)
print(json.dumps({"hooks": out}, indent=2))
PYEOF
unset COGNITO_HOOKS_DIR COGNITO_ENABLED_HOOKS

if [ "$SKIP_SETTINGS" = "1" ]; then
    echo "-> --skip-settings: snippet saved at $SNIPPET_FILE. Paste the 'hooks' block into $SETTINGS_FILE manually."
elif [ "$HAVE_JQ" = "1" ]; then
    echo "-> Merging hook registrations into $SETTINGS_FILE (via jq)..."
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    if [ ! -f "$SETTINGS_FILE" ]; then echo "{}" > "$SETTINGS_FILE"; fi
    # Backup settings.json before rewrite
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.cognito.bak" 2>/dev/null || true
    # Remove any prior cognito-* entries, then append the fresh ones.
    jq --slurpfile add "$SNIPPET_FILE" '
      .hooks = (.hooks // {})
      | .hooks = (
          .hooks
          | with_entries(
              .value = (
                (.value // [])
                | map(select(
                    (.name // "") | startswith("cognito-") | not
                  ))
              )
            )
        )
      | .hooks = (
          (.hooks) as $cur
          | ($add[0].hooks) as $new
          | reduce ($new | to_entries[]) as $pair
              ($cur; .[$pair.key] = ((.[$pair.key] // []) + $pair.value))
        )
    ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    echo "   ok  hooks merged (backup at ${SETTINGS_FILE}.cognito.bak)"
else
    cat <<EOF
-> jq not installed. Paste the following "hooks" block into $SETTINGS_FILE manually:

$(cat "$SNIPPET_FILE")

To automate next time:  sudo apt install jq   |   brew install jq   |   winget install jqlang.jq
EOF
fi

echo
echo "=========================================="
echo " Install complete"
echo "=========================================="
echo " Next steps:"
echo "  1. Open a new Claude Code session"
echo "  2. Run: /cognition-status"
echo "  3. Verify with: /cognition-status --verify (v1.1+)"
echo
