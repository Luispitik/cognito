#!/usr/bin/env bash
# =============================================================================
# Cognito — uninstall script (v1.1.0)
# =============================================================================
# Removes everything installed by scripts/install.sh, including the cognito-*
# entries inside ~/.claude/settings.json (via jq when available).
#
# Usage:
#   bash scripts/uninstall.sh
#   bash scripts/uninstall.sh --target=/tmp/cognito-test
#   bash scripts/uninstall.sh --yes                 # non-interactive
#   bash scripts/uninstall.sh --keep-settings       # skip settings.json cleanup
# =============================================================================

set -euo pipefail

TARGET_DIR="${HOME}/.claude/cognito"
SETTINGS_FILE="${HOME}/.claude/settings.json"
ASSUME_YES=0
KEEP_SETTINGS=0

for arg in "$@"; do
    case "$arg" in
        --target=*)         TARGET_DIR="${arg#*=}"    ;;
        --settings=*)       SETTINGS_FILE="${arg#*=}" ;;
        --yes|-y)           ASSUME_YES=1              ;;
        --keep-settings)    KEEP_SETTINGS=1           ;;
        --help|-h)
            cat <<'EOF'
Cognito uninstaller

Usage: bash scripts/uninstall.sh [options]

Options:
  --target=PATH       Install dir to remove (default: ~/.claude/cognito)
  --settings=PATH     settings.json to clean (default: ~/.claude/settings.json)
  --yes, -y           Skip confirmation prompt
  --keep-settings     Do not touch settings.json
EOF
            exit 0
            ;;
    esac
done

echo "Cognito uninstall"
echo "  target   : $TARGET_DIR"
echo "  settings : $([ $KEEP_SETTINGS = 1 ] && echo 'skipped' || echo $SETTINGS_FILE)"
echo

if [ "$ASSUME_YES" != "1" ]; then
    read -p "Remove the install and clean settings.json hooks? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Cancelled."
        exit 0
    fi
fi

# --- Remove install tree --------------------------------------------------
if [ -d "$TARGET_DIR" ]; then
    rm -rf "$TARGET_DIR"
    echo "ok  removed $TARGET_DIR"
fi

# --- Remove Cognito commands ---------------------------------------------
for cmd in fase modo cognition-status cognition-gate divergir verificar devils-advocate consolidar ejecutar estratega auditar; do
    f="$HOME/.claude/commands/${cmd}.md"
    [ -f "$f" ] && rm "$f"
done
echo "ok  commands removed"

# --- Remove Cognito skills (modes) ---------------------------------------
for mode in divergente verificador devils-advocate consolidador ejecutor estratega auditor; do
    d="$HOME/.claude/skills/$mode"
    [ -d "$d" ] && rm -rf "$d"
done
echo "ok  mode skills removed"

# --- Clean settings.json hooks -------------------------------------------
if [ "$KEEP_SETTINGS" = "1" ]; then
    echo "skip settings.json (--keep-settings)"
elif [ ! -f "$SETTINGS_FILE" ]; then
    echo "skip settings.json (file not found)"
elif ! command -v jq >/dev/null 2>&1; then
    cat <<EOF
warn jq not installed — manual cleanup required.
     Edit $SETTINGS_FILE and remove any hook entry whose "name" starts with "cognito-".
EOF
else
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.cognito.bak" 2>/dev/null || true
    jq '
      if .hooks == null then .
      else
        .hooks = (
          .hooks
          | with_entries(
              .value = (
                (.value // [])
                | map(select(
                    (.name // "") | startswith("cognito-") | not
                  ))
              )
            )
          | with_entries(select(.value != []))
        )
      end
    ' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    echo "ok  settings.json cleaned (backup at ${SETTINGS_FILE}.cognito.bak)"
fi

echo
echo "Done."
