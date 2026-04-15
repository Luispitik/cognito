#!/usr/bin/env bats
# =============================================================================
# Cognito — Tests bats de hooks
# =============================================================================
# Complementan los tests pytest con verificaciones específicas del entorno
# bash: cross-shell, paths con espacios, permisos, encoding UTF-8.
#
# Se ejecutan en CI (Ubuntu/macOS). En Windows, corrér vía WSL o Git Bash
# con bats-core instalado (`brew install bats-core` / `npm i -g bats`).
# =============================================================================

setup() {
    # Directorio temporal aislado para cada test
    export COGNITO_TEST_DIR=$(mktemp -d)
    export ORIGINAL_DIR=$(pwd)

    # Copiar estructura mínima de Cognito al dir de test
    mkdir -p "$COGNITO_TEST_DIR"/{config,hooks,logs,sessions,integrations,modes}

    # Copiar hooks desde el proyecto real
    PROJECT_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    cp "$PROJECT_ROOT/hooks/"*.sh "$COGNITO_TEST_DIR/hooks/"
    cp "$PROJECT_ROOT/config/"*.json "$COGNITO_TEST_DIR/config/"
    cp "$PROJECT_ROOT/config/_phase-state.default.json" "$COGNITO_TEST_DIR/config/_phase-state.json"
    cp "$PROJECT_ROOT/integrations/sinapsis_bridge.py" "$COGNITO_TEST_DIR/integrations/" 2>/dev/null || true

    chmod +x "$COGNITO_TEST_DIR/hooks/"*.sh

    cd "$COGNITO_TEST_DIR/hooks"
    export COGNITO_DIR="$COGNITO_TEST_DIR"
}

# Helper: activa un gate opt-in (defaults son neutros post A2 audit)
enable_gate() {
    local gate_id="$1"
    python3 -c "
import json
p = '$COGNITO_TEST_DIR/config/_operator-config.json'
with open(p) as f: c = json.load(f)
if '$gate_id' not in c['gates']['enabled']:
    c['gates']['enabled'].append('$gate_id')
with open(p, 'w') as f: json.dump(c, f)
"
}

teardown() {
    cd "$ORIGINAL_DIR"
    rm -rf "$COGNITO_TEST_DIR"
}

# --------------------------------------------------------------------
# Syntax y shebang
# --------------------------------------------------------------------

@test "phase-detector.sh tiene sintaxis válida" {
    run bash -n phase-detector.sh
    [ "$status" -eq 0 ]
}

@test "mode-injector.sh tiene sintaxis válida" {
    run bash -n mode-injector.sh
    [ "$status" -eq 0 ]
}

@test "gate-validator.sh tiene sintaxis válida" {
    run bash -n gate-validator.sh
    [ "$status" -eq 0 ]
}

@test "session-closer.sh tiene sintaxis válida" {
    run bash -n session-closer.sh
    [ "$status" -eq 0 ]
}

@test "todos los hooks son ejecutables" {
    for hook in *.sh; do
        [ -x "$hook" ] || { echo "No ejecutable: $hook"; return 1; }
    done
}

# --------------------------------------------------------------------
# Funcionamiento básico
# --------------------------------------------------------------------

@test "phase-detector detecta señal 'vamos a ejecutar'" {
    run bash -c 'echo "{\"prompt\":\"vamos a ejecutar\"}" | bash phase-detector.sh'
    [ "$status" -eq 0 ]
    [[ "$output" == *"execution"* ]]
}

@test "phase-detector no produce output con prompt neutro" {
    run bash -c 'echo "{\"prompt\":\"hola que tal\"}" | bash phase-detector.sh'
    [ "$status" -eq 0 ]
    [ -z "$output" ] || [[ "$output" != *"systemMessage"* ]]
}

@test "phase-detector sobrevive stdin corrupto" {
    run bash -c 'echo "not json" | bash phase-detector.sh'
    [ "$status" -eq 0 ]
}

@test "phase-detector sobrevive stdin vacío" {
    run bash -c 'echo "" | bash phase-detector.sh'
    [ "$status" -eq 0 ]
}

# --------------------------------------------------------------------
# gate-validator
# --------------------------------------------------------------------

@test "gate-validator bloquea .env (exit != 0)" {
    payload='{"tool_input":{"file_path":".env","content":"SECRET=xxx"}}'
    run bash -c "echo '$payload' | bash gate-validator.sh"
    [ "$status" -ne 0 ]
}

@test "gate-validator permite Write limpio (exit 0)" {
    payload='{"tool_input":{"file_path":"README.md","content":"# Hello"}}'
    run bash -c "echo '$payload' | bash gate-validator.sh"
    [ "$status" -eq 0 ]
    # Sin systemMessage en stdout si no hay violación
    [[ "$output" != *"systemMessage"* ]] || [[ "$output" != *"[BLOCK]"* ]]
}

@test "gate-validator avisa n8n cuando esta activado (warn, exit 0)" {
    enable_gate "n8n-retired"
    payload='{"tool_input":{"file_path":"workflow.json","content":"{\"type\":\"n8n-workflow\"}"}}'
    run bash -c "echo '$payload' | bash gate-validator.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"n8n"* ]] || [[ "$output" == *"systemMessage"* ]]
}

@test "gate-validator no dispara n8n por default (A2 audit: gates opt-in)" {
    payload='{"tool_input":{"file_path":"workflow.json","content":"{\"type\":\"n8n-workflow\"}"}}'
    run bash -c "echo '$payload' | bash gate-validator.sh"
    [ "$status" -eq 0 ]
    [[ "$output" != *"n8n"* ]]
}

# --------------------------------------------------------------------
# mode-injector
# --------------------------------------------------------------------

@test "mode-injector no rompe con payload mínimo" {
    payload='{"tool":"Read"}'
    run bash -c "echo '$payload' | bash mode-injector.sh"
    [ "$status" -eq 0 ]
}

@test "mode-injector escribe log" {
    payload='{"tool":"Read"}'
    run bash -c "echo '$payload' | bash mode-injector.sh"
    [ -f "$COGNITO_TEST_DIR/logs/mode-injector.log" ]
}

# --------------------------------------------------------------------
# session-closer
# --------------------------------------------------------------------

@test "session-closer crea session file con id provisto" {
    payload='{"session_id":"bats-test-001"}'
    run bash -c "echo '$payload' | bash session-closer.sh"
    [ "$status" -eq 0 ]
    [ -f "$COGNITO_TEST_DIR/sessions/bats-test-001.json" ]
}

@test "session-closer genera id auto cuando falta" {
    run bash -c 'echo "{}" | bash session-closer.sh'
    [ "$status" -eq 0 ]
    # Debe haber al menos un archivo session-*.json
    shopt -s nullglob
    files=("$COGNITO_TEST_DIR"/sessions/session-*.json)
    [ ${#files[@]} -gt 0 ]
}

# --------------------------------------------------------------------
# Robustez cross-shell
# --------------------------------------------------------------------

@test "hooks toleran path con espacios en COGNITO_DIR" {
    SPACE_DIR="$COGNITO_TEST_DIR/with space"
    mkdir -p "$SPACE_DIR"/{config,hooks,logs,sessions,integrations}
    cp -r "$COGNITO_TEST_DIR/config/"* "$SPACE_DIR/config/"
    cp -r "$COGNITO_TEST_DIR/hooks/"* "$SPACE_DIR/hooks/"
    cp -r "$COGNITO_TEST_DIR/integrations/"* "$SPACE_DIR/integrations/" 2>/dev/null || true
    chmod +x "$SPACE_DIR/hooks/"*.sh

    COGNITO_DIR="$SPACE_DIR" run bash -c \
        "echo '{\"prompt\":\"vamos a ejecutar\"}' | bash '$SPACE_DIR/hooks/phase-detector.sh'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"execution"* ]] || [ -z "$output" ]
}

@test "hooks escriben logs en UTF-8 sin romper" {
    # Prompt con acentos y emojis
    run bash -c 'echo "{\"prompt\":\"vamos a ejecutar mañana 🚀\"}" | bash phase-detector.sh'
    [ "$status" -eq 0 ]
    [ -f "$COGNITO_TEST_DIR/logs/phase-detector.log" ]
}

@test "session-closer actualiza phase-state con sessionId" {
    payload='{"session_id":"state-update-test"}'
    run bash -c "echo '$payload' | bash session-closer.sh"
    [ "$status" -eq 0 ]
    # Verificar con python (grep puede fallar por encoding)
    run python3 -c "
import json
with open('$COGNITO_TEST_DIR/config/_phase-state.json') as f:
    s = json.load(f)
assert s.get('sessionId') == 'state-update-test', f'Got: {s.get(\"sessionId\")}'
"
    [ "$status" -eq 0 ]
}

# --------------------------------------------------------------------
# Fallback sin COGNITO_DIR
# --------------------------------------------------------------------

@test "phase-detector encuentra su dir si COGNITO_DIR no está definido" {
    # Desestablece COGNITO_DIR y depende del fallback (parent del script)
    unset COGNITO_DIR
    run bash -c 'echo "{\"prompt\":\"vamos a ejecutar\"}" | bash phase-detector.sh'
    [ "$status" -eq 0 ]
    # Debe haber encontrado config y producido output (o silencio si no matchea)
}

@test "gate-validator con config ausente degrada limpio" {
    # Borrar config para simular instalación rota
    rm -f "$COGNITO_TEST_DIR/config/_passive-triggers.json"
    payload='{"tool_input":{"file_path":"test.ts","content":"const x = 1;"}}'
    run bash -c "echo '$payload' | bash gate-validator.sh"
    [ "$status" -eq 0 ]  # No debe bloquear, no debe crashear
}
