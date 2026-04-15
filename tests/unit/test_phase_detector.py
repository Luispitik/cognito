"""
test_phase_detector.py — Tests funcionales del hook phase-detector.sh.

Simula inputs variados y valida que:
- Detecta señales de cambio de fase correctamente.
- No sugiere cambio si ya estamos en la fase sugerida.
- Detecta anclas cognitivas.
- Degrada silenciosamente si la config falta.
"""
import json

import pytest


class TestPhaseDetectorBasic:
    """Tests básicos de detección."""

    def test_detects_execution_signal(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "vamos a ejecutar el plan"},
            isolated_cognito_env,
        )
        assert rc == 0, f"Hook falló: {stderr}"
        assert "execution" in stdout.lower(), \
            f"Esperado sugerencia a execution. Stdout:\n{stdout}"

    def test_detects_review_signal(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "¿qué aprendimos de esto?"},
            isolated_cognito_env,
        )
        assert rc == 0
        assert "review" in stdout.lower(), f"Esperado sugerencia a review. Stdout:\n{stdout}"

    def test_detects_shipping_signal(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "ship it"},
            isolated_cognito_env,
        )
        assert rc == 0
        assert "shipping" in stdout.lower() or "Ship" in stdout, \
            f"Esperado sugerencia a shipping. Stdout:\n{stdout}"

    def test_no_signal_no_output(self, run_hook_fn, isolated_cognito_env):
        """Prompt sin señal no debe generar systemMessage."""
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "hola, dime la hora"},
            isolated_cognito_env,
        )
        assert rc == 0
        # Sin señal, stdout debe estar vacío o no contener systemMessage
        assert "systemMessage" not in stdout or stdout.strip() == ""


class TestPhaseDetectorSameFase:
    """Si el prompt sugiere la fase actual, no debe generar sugerencia."""

    def test_discovery_signal_when_already_discovery(self, run_hook_fn, isolated_cognito_env):
        # Estado por defecto es discovery
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "exploremos alternativas"},
            isolated_cognito_env,
        )
        assert rc == 0
        # El hook detecta "exploremos" → sugiere discovery, pero estamos en discovery
        # Debe NO sugerir (salida sin systemMessage o vacía)
        assert "systemMessage" not in stdout or "discovery" not in stdout, \
            "Detector no debería sugerir cambio a la fase actual"


class TestPhaseDetectorAnchor:
    """Detección de ancla cognitiva."""

    def test_detects_anchor_phrase(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "ya tengo decidido hacer X"},
            isolated_cognito_env,
        )
        assert rc == 0
        # Debe sugerir modo Divergente
        assert "divergente" in stdout.lower() or "ancla" in stdout.lower(), \
            f"Esperado sugerencia de divergente ante ancla. Stdout:\n{stdout}"


class TestPhaseDetectorRobustness:
    """Robustez ante inputs problemáticos."""

    def test_empty_prompt(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": ""},
            isolated_cognito_env,
        )
        assert rc == 0, f"Empty prompt debería salir limpio. Stderr: {stderr}"

    def test_missing_prompt_key(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "phase-detector.sh",
            {},
            isolated_cognito_env,
        )
        assert rc == 0, f"Sin prompt key debería salir limpio. Stderr: {stderr}"

    def test_invalid_json_stdin(self, hooks_dir, isolated_cognito_env):
        """Si stdin no es JSON, no debe crashear."""
        import subprocess
        import os
        env = os.environ.copy()
        env["COGNITO_DIR"] = isolated_cognito_env.as_posix()
        result = subprocess.run(
            ["bash", "phase-detector.sh"],
            cwd=str(isolated_cognito_env / "hooks"),
            input="not json at all",
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        # No crashear (exit 0) aunque no haya detectado nada
        assert result.returncode == 0


class TestPhaseDetectorLogging:
    """El hook debe escribir logs."""

    def test_log_file_created(self, run_hook_fn, isolated_cognito_env):
        run_hook_fn(
            "phase-detector.sh",
            {"prompt": "vamos a ejecutar"},
            isolated_cognito_env,
        )
        log_file = isolated_cognito_env / "logs" / "phase-detector.log"
        assert log_file.exists(), "Log file debería crearse"
        content = log_file.read_text()
        assert len(content) > 0, "Log file debería tener contenido"
