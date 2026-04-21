#!/usr/bin/env bash
# =============================================================================
# Cognito - cognito-daemon.sh (v2.0)
# =============================================================================
# Manage the long-lived hook daemon introduced in v2.0.
#   start    - spawn detached, write pid/socket
#   stop     - send SIGTERM and clean runtime files
#   restart  - stop then start
#   status   - report running / stale / down
# Version: 2.0.0-rc1
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_MODULE="$(dirname "$SCRIPT_DIR")/hooks/python/_daemon.py"
RUNTIME_DIR="$COGNITO_DIR_RESOLVED/runtime"
LOG_FILE="$COGNITO_DIR_RESOLVED/logs/daemon.log"
PID_FILE="$RUNTIME_DIR/hook.pid"

cmd="${1:-status}"

usage() {
    cat <<'EOF'
Usage: cognito-daemon.sh {start|stop|restart|status}

  start     Spawn the daemon detached.
  stop      Terminate the daemon (SIGTERM, then cleanup).
  restart   stop + start.
  status    Report daemon state.

Env:
  COGNITO_DIR   Override the install directory.
EOF
}

start() {
    if [ -f "$PID_FILE" ]; then
        echo "daemon may already be running (pid file at $PID_FILE). Run 'status' first."
        return 1
    fi
    mkdir -p "$RUNTIME_DIR" "$(dirname "$LOG_FILE")"
    # Detach: nohup + background + disown
    nohup python3 "$DAEMON_MODULE" serve >>"$LOG_FILE" 2>&1 &
    local spawned_pid=$!
    disown "$spawned_pid" 2>/dev/null || true
    # Wait up to 2s for the daemon to write its pid/socket.
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
        if [ -f "$PID_FILE" ]; then
            break
        fi
        sleep 0.1
    done
    if [ -f "$PID_FILE" ]; then
        echo "started pid $(cat "$PID_FILE")"
    else
        echo "warn: daemon spawned (pid $spawned_pid) but pid file never appeared; check $LOG_FILE"
        return 2
    fi
}

stop() {
    exec python3 "$DAEMON_MODULE" stop
}

status() {
    exec python3 "$DAEMON_MODULE" status
}

case "$cmd" in
    start)   start ;;
    stop)    stop ;;
    restart) python3 "$DAEMON_MODULE" stop; start ;;
    status)  status ;;
    -h|--help|help) usage ;;
    *) usage; exit 2 ;;
esac
