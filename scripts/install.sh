#!/usr/bin/env bash
# =============================================================================
# Cognito — Script de instalación
# =============================================================================
# Uso:
#   bash scripts/install.sh --profile=operator
#   bash scripts/install.sh --profile=alumno
#   bash scripts/install.sh --profile=public
#   bash scripts/install.sh --profile=client [--client-intake=./intake.json]
# =============================================================================

set -euo pipefail

# --- Parse args ---
PROFILE=""
CLIENT_INTAKE=""
TARGET_DIR="${HOME}/.claude/cognito"

for arg in "$@"; do
    case "$arg" in
        --profile=*)
            PROFILE="${arg#*=}"
            ;;
        --client-intake=*)
            CLIENT_INTAKE="${arg#*=}"
            ;;
        --target=*)
            TARGET_DIR="${arg#*=}"
            ;;
        --help|-h)
            cat <<EOF
Cognito — Instalación

Uso: bash scripts/install.sh --profile=<nombre> [opciones]

Perfiles disponibles:
  operator   Founder/consultor avanzado (default)
  alumno     Alumno de formación corporativa / formación
  public     Open source / genérico
  client     Cliente B2B (requiere --client-intake)

Opciones:
  --target=PATH         Directorio destino (default: ~/.claude/cognito)
  --client-intake=PATH  Archivo de intake JSON (solo client)

Ejemplos:
  bash scripts/install.sh --profile=operator
  bash scripts/install.sh --profile=alumno --target=/tmp/cognito-test
EOF
            exit 0
            ;;
    esac
done

if [ -z "$PROFILE" ]; then
    echo "Falta --profile. Usa --help para ver opciones." >&2
    exit 1
fi

# --- Whitelist de perfiles (defensa contra argumentos hostiles) ---
case "$PROFILE" in
    operator|alumno|public|client) ;;
    *)
        echo "Perfil invalido: '$PROFILE'. Permitidos: operator, alumno, public, client." >&2
        exit 1
        ;;
esac

# --- Validar python3 disponible (hard requirement) ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 no encontrado en PATH. Cognito requiere Python 3.10+." >&2
    echo "Windows: instala desde python.org y marca 'Add to PATH'." >&2
    exit 1
fi

# --- Validar perfil ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PROFILE_FILE="$REPO_DIR/profiles/${PROFILE}.yaml"

if [ ! -f "$PROFILE_FILE" ]; then
    echo "Perfil '$PROFILE' no encontrado en profiles/" >&2
    echo "Disponibles:" >&2
    ( cd "$REPO_DIR/profiles/" && ls *.yaml 2>/dev/null | sed 's/\.yaml//' | sed 's/^/  /' ) >&2
    exit 1
fi

echo "════════════════════════════════════════════"
echo "Cognito — Instalación"
echo "════════════════════════════════════════════"
echo "Perfil: $PROFILE"
echo "Destino: $TARGET_DIR"
echo ""

# --- Crear estructura destino ---
mkdir -p "$TARGET_DIR"/{config,hooks,logs,sessions}

# --- Copiar archivos core ---
echo "→ Copiando hooks..."
cp "$REPO_DIR/hooks/"*.sh "$TARGET_DIR/hooks/"
chmod +x "$TARGET_DIR/hooks/"*.sh

echo "→ Copiando config..."
cp "$REPO_DIR/config/"*.json "$TARGET_DIR/config/"

# Inicializar phase-state.json desde default
if [ -f "$REPO_DIR/config/_phase-state.default.json" ]; then
    cp "$REPO_DIR/config/_phase-state.default.json" "$TARGET_DIR/config/_phase-state.json"
fi

echo "→ Copiando templates..."
cp -r "$REPO_DIR/templates" "$TARGET_DIR/"

echo "→ Copiando phases..."
cp -r "$REPO_DIR/phases" "$TARGET_DIR/"

echo "→ Copiando SKILL.md raíz..."
cp "$REPO_DIR/SKILL.md" "$TARGET_DIR/"

# --- Copiar modos según perfil ---
echo "→ Instalando modos del perfil '$PROFILE'..."
# Por simplicidad, copiamos todos los modos. El _operator-config.json
# controla cuáles están habilitados según perfil.
mkdir -p "$HOME/.claude/skills"
for mode_dir in "$REPO_DIR/modes/"*/; do
    mode_name=$(basename "$mode_dir")
    cp -r "$mode_dir" "$HOME/.claude/skills/"
    echo "  ✓ modes/$mode_name"
done

# --- Copiar commands ---
echo "→ Instalando commands..."
mkdir -p "$HOME/.claude/commands"
for cmd in "$REPO_DIR/commands/"*.md; do
    cp "$cmd" "$HOME/.claude/commands/"
done

# --- Aplicar configuración de perfil ---
echo "-> Aplicando configuracion de perfil '$PROFILE'..."
# Actualizar _operator-config.json → profile
# Valores pasados por env (NO interpolacion bash) para cerrar vector de inyeccion.
export COGNITO_CONFIG_PATH="$TARGET_DIR/config/_operator-config.json"
export COGNITO_PROFILE="$PROFILE"
python3 <<'PYEOF'
import json, os, sys
config_path = os.environ["COGNITO_CONFIG_PATH"]
profile = os.environ["COGNITO_PROFILE"]
try:
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
except Exception as e:
    print(f"  Error leyendo config: {e}", file=sys.stderr)
    sys.exit(1)
if not isinstance(config, dict):
    print("  _operator-config.json debe ser un objeto JSON.", file=sys.stderr)
    sys.exit(1)
config["profile"] = profile
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)
print(f"  Perfil aplicado: {profile}")
PYEOF
unset COGNITO_CONFIG_PATH COGNITO_PROFILE

# --- Reporte final ---
echo ""
echo "════════════════════════════════════════════"
echo "✅ Instalación completada"
echo "════════════════════════════════════════════"
echo ""
echo "Próximos pasos:"
echo "1. Registrar hooks en ~/.claude/settings.json (ver INSTALL.md)"
echo "2. Abrir nueva sesión de Claude Code"
echo "3. Ejecutar: /cognition-status"
echo ""
echo "Docs: $REPO_DIR/INSTALL.md"
