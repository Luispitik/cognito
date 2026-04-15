#!/usr/bin/env bash
# =============================================================================
# Cognito Dashboard — servidor local
# =============================================================================
# Regenera data.json y sirve el dashboard en http://localhost:8765
#
# Uso:
#   bash dashboard/serve.sh
#   bash dashboard/serve.sh --port 8080
#   bash dashboard/serve.sh --cognito-dir ~/.claude/cognito
# =============================================================================

set -euo pipefail

PORT=8765
COGNITO_DIR_ARG=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            PORT="$2"
            shift 2
            ;;
        --cognito-dir)
            COGNITO_DIR_ARG="--cognito-dir $2"
            shift 2
            ;;
        *)
            echo "Uso: $0 [--port N] [--cognito-dir PATH]"
            exit 1
            ;;
    esac
done

echo "→ Regenerando data.json..."
python3 "$SCRIPT_DIR/api/build_data.py" $COGNITO_DIR_ARG

echo ""
echo "→ Sirviendo dashboard en http://localhost:$PORT"
echo "  (Ctrl+C para parar)"
echo ""

cd "$SCRIPT_DIR"
python3 -m http.server "$PORT"
