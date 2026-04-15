"""
test_hooks_syntax.py — Validación sintáctica de los 4 hooks bash.
"""
import subprocess
import pytest


HOOKS = [
    "phase-detector.sh",
    "mode-injector.sh",
    "gate-validator.sh",
    "session-closer.sh",
]


@pytest.mark.parametrize("hook", HOOKS)
def test_hook_exists(hooks_dir, hook):
    assert (hooks_dir / hook).exists(), f"{hook} no existe"


@pytest.mark.parametrize("hook", HOOKS)
def test_hook_bash_syntax(hooks_dir, hook):
    """`bash -n` no debe encontrar errores de sintaxis.

    Usa cwd para evitar problemas con paths Windows en Git Bash.
    """
    result = subprocess.run(
        ["bash", "-n", hook],
        cwd=str(hooks_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, f"Syntax error en {hook}:\n{result.stderr}"


@pytest.mark.parametrize("hook", HOOKS)
def test_hook_has_shebang(hooks_dir, hook):
    with open(hooks_dir / hook, encoding="utf-8") as f:
        first_line = f.readline().strip()
    assert first_line.startswith("#!"), f"{hook} no tiene shebang"
    assert "bash" in first_line or "sh" in first_line, f"{hook} shebang no apunta a bash/sh"


@pytest.mark.parametrize("hook", HOOKS)
def test_hook_has_safety_flags(hooks_dir, hook):
    """Cada hook debe tener `set -e` o equivalente para fallar rápido."""
    with open(hooks_dir / hook, encoding="utf-8") as f:
        content = f.read()
    assert "set -" in content, f"{hook} no tiene `set -e/-u/-o pipefail`"


@pytest.mark.parametrize("hook", HOOKS)
def test_hook_has_version_comment(hooks_dir, hook):
    """Cada hook debe tener una línea con 'Versión:' en la cabecera."""
    with open(hooks_dir / hook, encoding="utf-8") as f:
        content = f.read(800)  # primeros ~800 chars
    assert "Versión:" in content or "Version:" in content, \
        f"{hook} no tiene comentario de versión en cabecera"
