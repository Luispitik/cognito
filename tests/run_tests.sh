#!/usr/bin/env bash
# =============================================================================
# Cognito — Runner de tests
# =============================================================================
# Ejecuta toda la suite de tests y genera reporte.
# Uso:
#   bash tests/run_tests.sh              # todos
#   bash tests/run_tests.sh unit         # solo unitarios
#   bash tests/run_tests.sh integration  # solo integración
# =============================================================================

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR" || exit 1

TARGET="${1:-all}"

echo "════════════════════════════════════════════"
echo "Cognito — Suite de tests"
echo "════════════════════════════════════════════"
echo "Proyecto: $PROJECT_DIR"
echo "Target: $TARGET"
echo ""

# --- Verificar pytest ---
if ! command -v pytest >/dev/null 2>&1; then
    echo "❌ pytest no instalado. Instala con: pip install -r requirements-test.txt"
    exit 1
fi

# --- Verificar que existe la estructura ---
for dir in config hooks modes phases commands templates profiles; do
    if [ ! -d "$PROJECT_DIR/$dir" ]; then
        echo "❌ Falta directorio: $dir"
        exit 1
    fi
done

echo "✓ Estructura verificada"
echo ""

# --- Ejecutar según target ---
EXIT_CODE=0

case "$TARGET" in
    unit)
        pytest tests/unit/ -v --tb=short
        EXIT_CODE=$?
        ;;
    integration)
        pytest tests/integration/ -v --tb=short
        EXIT_CODE=$?
        ;;
    all|*)
        pytest tests/ -v --tb=short
        EXIT_CODE=$?
        ;;
esac

echo ""
echo "════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Todos los tests pasaron"
else
    echo "❌ Algunos tests fallaron (exit code: $EXIT_CODE)"
fi
echo "════════════════════════════════════════════"

exit $EXIT_CODE
