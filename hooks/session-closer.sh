#!/usr/bin/env bash
# =============================================================================
# Cognito - session-closer.sh (v1.2 wrapper)
# =============================================================================
# Hook: Stop
# Version: 1.2.0
# Delegates to hooks/python/session_closer.py.
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

INPUT_JSON=$(head -c 1048576 2>/dev/null || echo "{}")
export INPUT_JSON

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/python/_daemon.py" ]; then
    python3 "$SCRIPT_DIR/python/_daemon.py" client session-closer
    _rc=$?
    if [ "$_rc" != "127" ]; then
        exit "$_rc"
    fi
fi

if [ -f "$SCRIPT_DIR/python/session_closer.py" ]; then
    exec python3 "$SCRIPT_DIR/python/session_closer.py"
else
    exec python3 -m hooks.python.session_closer
fi
