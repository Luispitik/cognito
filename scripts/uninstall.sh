#!/usr/bin/env bash
# Cognito — Uninstall script
# Uso: bash scripts/uninstall.sh [--target=PATH]

set -euo pipefail

TARGET_DIR="${HOME}/.claude/cognito"

for arg in "$@"; do
    case "$arg" in
        --target=*)
            TARGET_DIR="${arg#*=}"
            ;;
    esac
done

echo "Cognito — Uninstall"
echo "Target: $TARGET_DIR"
echo ""
read -p "¿Borrar toda la instalación? [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Cancelado."
    exit 0
fi

# Borrar Cognito dir
if [ -d "$TARGET_DIR" ]; then
    rm -rf "$TARGET_DIR"
    echo "✓ Borrado $TARGET_DIR"
fi

# Borrar commands
for cmd in fase modo cognition-status divergir verificar devils-advocate consolidar ejecutar estratega auditar; do
    f="$HOME/.claude/commands/${cmd}.md"
    if [ -f "$f" ]; then
        rm "$f"
    fi
done
echo "✓ Commands borrados"

# Borrar modos
for mode in divergente verificador devils-advocate consolidador ejecutor estratega auditor; do
    d="$HOME/.claude/skills/$mode"
    if [ -d "$d" ]; then
        rm -rf "$d"
    fi
done
echo "✓ Skills de modos borrados"

echo ""
echo "⚠️ No olvides quitar los hooks 'cognito-*' de ~/.claude/settings.json manualmente."
