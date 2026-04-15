# Tests bats — cross-platform profundo

Tests complementarios en [bats-core](https://github.com/bats-core/bats-core) que validan:
- Syntax y ejecutabilidad de los 4 hooks
- Funcionamiento en bash real (no subprocess Python)
- Paths con espacios, encoding UTF-8
- Fallback cuando falta `COGNITO_DIR` env
- Degradación sin config

## Ejecutar localmente

### Instalar bats-core

```bash
# macOS
brew install bats-core

# Ubuntu/Debian
sudo apt-get install bats

# Con npm (cualquier SO)
npm install -g bats

# Windows (via WSL o Git Bash)
# 1. Abrir WSL/Git Bash
# 2. git clone https://github.com/bats-core/bats-core.git
# 3. cd bats-core && ./install.sh ~/.local
# 4. Añadir ~/.local/bin al PATH
```

### Correr los tests

```bash
# Desde raíz del proyecto
bats tests/bats/hooks.bats

# Verbose
bats --verbose-run tests/bats/hooks.bats

# Formato tap (para parsing automático)
bats --formatter tap tests/bats/hooks.bats
```

## En CI

Los tests corren automáticamente en el workflow `.github/workflows/test.yml` en Ubuntu. Ver allí para detalles.

## Añadir nuevos tests

Cada test es un bloque `@test "nombre" { ... }`. Usa:
- `run <comando>` para capturar output y status
- `[ "$status" -eq 0 ]` para chequear exit code
- `[[ "$output" == *"substring"* ]]` para regex en output
- `setup()` / `teardown()` para preparar/limpiar entorno

Mantén tests idempotentes (no modifican el proyecto real, usan `mktemp -d`).
