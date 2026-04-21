#!/usr/bin/env bash
# =============================================================================
# Cognito - phase-detector.sh (v1.2 wrapper)
# =============================================================================
# Hook: UserPromptSubmit
# Version: 1.2.0
# Delegates to hooks/python/phase_detector.py. Heredocs were extracted in v1.2
# to close the Maintainability gap (see docs/QUALITY-ISO25010-2026-04-18.md).
#
# Fast-path: if the prompt field is empty or whitespace-only, short-circuit in
# bash without paying the ~200 ms Python cold-start. Typical prompts still hit
# Python because they carry content; this only skips the cases that would
# return 0 anyway.
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

# Fast-path: empty / whitespace-only prompts cannot match any signal. Saves
# the ~200 ms Python cold start on e.g. slash-commands with no body.
if ! printf '%s' "$INPUT_JSON" | grep -q '"prompt"[[:space:]]*:[[:space:]]*"[^"]'; then
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# v2.0: try the persistent daemon first. `_daemon.py client` returns 127 when
# no daemon is reachable so we can transparently fall back to the cold-start
# Python invocation that v1.2 ships.
if [ -f "$SCRIPT_DIR/python/_daemon.py" ]; then
    python3 "$SCRIPT_DIR/python/_daemon.py" client phase-detector
    _rc=$?
    if [ "$_rc" != "127" ]; then
        exit "$_rc"
    fi
fi

if [ -f "$SCRIPT_DIR/python/phase_detector.py" ]; then
    exec python3 "$SCRIPT_DIR/python/phase_detector.py"
else
    exec python3 -m hooks.python.phase_detector
fi
