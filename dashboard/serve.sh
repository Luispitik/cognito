#!/usr/bin/env bash
# =============================================================================
# Cognito Dashboard — local server
# =============================================================================
# Regenerates data.json and serves the dashboard at http://127.0.0.1:8765
#
# Security-hardened: binds loopback only, serves an explicit allowlist of
# static files, never exposes Python source under api/.
#
# Usage:
#   bash dashboard/serve.sh
#   bash dashboard/serve.sh --port 8080
#   bash dashboard/serve.sh --cognito-dir ~/.claude/cognito
# =============================================================================

set -euo pipefail

PORT=8765
BIND_ADDR="127.0.0.1"
COGNITO_DIR_VALUE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            PORT="$2"
            shift 2
            ;;
        --cognito-dir)
            COGNITO_DIR_VALUE="$2"
            shift 2
            ;;
        --bind)
            BIND_ADDR="$2"
            shift 2
            ;;
        --help|-h)
            cat <<EOF
Usage: $0 [--port N] [--bind ADDR] [--cognito-dir PATH]

Defaults:
  --port        8765
  --bind        127.0.0.1   (loopback only; use --bind 0.0.0.0 to expose to LAN)
  --cognito-dir auto-detected from script location
EOF
            exit 0
            ;;
        *)
            echo "Unknown arg: $1 (try --help)" >&2
            exit 1
            ;;
    esac
done

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found in PATH (required for dashboard)." >&2
    exit 1
fi

echo "-> Regenerating data.json..."
if [ -n "$COGNITO_DIR_VALUE" ]; then
    python3 "$SCRIPT_DIR/api/build_data.py" --cognito-dir "$COGNITO_DIR_VALUE"
else
    python3 "$SCRIPT_DIR/api/build_data.py"
fi

echo ""
echo "-> Serving dashboard at http://${BIND_ADDR}:${PORT}"
echo "   (Ctrl+C to stop)"
echo ""

# Serve an explicit allowlist from $SCRIPT_DIR, binding loopback only.
# This prevents accidental exposure of api/*.py source code.
export COGNITO_DASHBOARD_DIR="$SCRIPT_DIR"
export COGNITO_DASHBOARD_BIND="$BIND_ADDR"
export COGNITO_DASHBOARD_PORT="$PORT"

python3 <<'PYEOF'
import http.server
import os
import posixpath
import socketserver
import sys
from urllib.parse import urlparse

DASHBOARD_DIR = os.environ["COGNITO_DASHBOARD_DIR"]
BIND_ADDR = os.environ["COGNITO_DASHBOARD_BIND"]
PORT = int(os.environ["COGNITO_DASHBOARD_PORT"])

ALLOWED = {
    "/",
    "/index.html",
    "/app.js",
    "/styles.css",
    "/data.json",
}

class CognitoHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Always serve from dashboard directory, never climb out.
        parsed = urlparse(path).path
        parsed = posixpath.normpath(parsed)
        if parsed == "/":
            parsed = "/index.html"
        if parsed not in ALLOWED:
            # Will trigger 404 via SimpleHTTPRequestHandler
            return os.path.join(DASHBOARD_DIR, ".__forbidden__")
        return os.path.join(DASHBOARD_DIR, parsed.lstrip("/"))

    def log_message(self, fmt, *args):
        sys.stderr.write("[dashboard] " + fmt % args + "\n")

try:
    with socketserver.TCPServer((BIND_ADDR, PORT), CognitoHandler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\nStopped.")
    sys.exit(0)
except OSError as e:
    print(f"Failed to bind {BIND_ADDR}:{PORT} — {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
