#!/usr/bin/env bash
# =============================================================================
# Cognito — update script (v1.1.0+)
# =============================================================================
# Non-destructive update. Refreshes hook scripts, templates, phases, SKILL.md
# and the integrations bridge from the repo into the installed target dir,
# but preserves:
#   - config/_phase-state.json (current session state)
#   - config/_operator-config.json (user-tuned modes.enabled / gates.enabled)
#   - logs/ and sessions/
#
# Usage:
#   bash scripts/update.sh
#   bash scripts/update.sh --target=/tmp/cognito-test
#   bash scripts/update.sh --dry-run
# =============================================================================

set -euo pipefail

TARGET_DIR="${HOME}/.claude/cognito"
DRY_RUN=0

for arg in "$@"; do
    case "$arg" in
        --target=*) TARGET_DIR="${arg#*=}" ;;
        --dry-run)  DRY_RUN=1 ;;
        --help|-h)
            cat <<'EOF'
Cognito update (non-destructive)

Usage: bash scripts/update.sh [options]

Options:
  --target=PATH   Install dir (default: ~/.claude/cognito)
  --dry-run       Show what would change; do not touch files
EOF
            exit 0
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -d "$TARGET_DIR" ]; then
    echo "No install at $TARGET_DIR. Run scripts/install.sh first." >&2
    exit 1
fi

echo "Cognito update"
echo "  repo   : $REPO_DIR"
echo "  target : $TARGET_DIR"
echo "  dry-run: $([ $DRY_RUN = 1 ] && echo yes || echo no)"
echo

# Backup first
if [ "$DRY_RUN" != "1" ]; then
    BACKUP_ROOT="${HOME}/.claude/cognito-backups"
    TS=$(date -u +"%Y%m%dT%H%M%SZ")
    BACKUP_DIR="$BACKUP_ROOT/$TS-update"
    mkdir -p "$BACKUP_ROOT"
    cp -r "$TARGET_DIR" "$BACKUP_DIR"
    echo "ok  backup at $BACKUP_DIR"
fi

refresh_file() {
    local rel="$1"
    local src="$REPO_DIR/$rel"
    local dst="$TARGET_DIR/$rel"
    if [ ! -f "$src" ]; then return; fi
    if [ -f "$dst" ] && cmp -s "$src" "$dst"; then return; fi
    if [ "$DRY_RUN" = "1" ]; then
        echo "  would update: $rel"
    else
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
        echo "  updated: $rel"
    fi
}

refresh_dir() {
    local rel="$1"
    local src="$REPO_DIR/$rel"
    local dst="$TARGET_DIR/$rel"
    if [ ! -d "$src" ]; then return; fi
    if [ "$DRY_RUN" = "1" ]; then
        echo "  would sync dir: $rel"
    else
        mkdir -p "$dst"
        cp -r "$src/." "$dst/"
        echo "  synced dir: $rel"
    fi
}

echo "-> Hooks"
for h in phase-detector mode-injector gate-validator session-closer; do
    refresh_file "hooks/${h}.sh"
    [ "$DRY_RUN" = "1" ] || chmod +x "$TARGET_DIR/hooks/${h}.sh" 2>/dev/null || true
done

echo "-> Templates"
refresh_dir "templates"

echo "-> Phases"
refresh_dir "phases"

echo "-> Integrations (Sinapsis bridge)"
refresh_dir "integrations"

echo "-> SKILL.md"
refresh_file "SKILL.md"

echo "-> Config (non-destructive)"
# Only fill in config files that don't exist. Never overwrite user tuning.
for cfg in _modes.json _phases.json _passive-triggers.json _operator-config.json; do
    src="$REPO_DIR/config/$cfg"
    dst="$TARGET_DIR/config/$cfg"
    if [ ! -f "$dst" ] && [ -f "$src" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            echo "  would create: config/$cfg"
        else
            cp "$src" "$dst"
            echo "  created: config/$cfg"
        fi
    fi
done
# Always refresh the *.default.json seed (not the live _phase-state.json).
refresh_file "config/_phase-state.default.json"

echo
if [ "$DRY_RUN" = "1" ]; then
    echo "Dry run — no files changed."
else
    echo "Update complete."
    echo "Your _phase-state.json, _operator-config.json, logs/ and sessions/ were left untouched."
fi
