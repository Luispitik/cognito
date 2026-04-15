"""
test_gate_validator.py — Tests funcionales del hook gate-validator.sh.

Casos:
- Detecta y bloquea commitear .env.
- Bloquea hardcode de PII.
- Avisa (no bloquea) ante n8n.
- Avisa ante migraciones sin RLS.
- No dispara con contenido limpio.
- Respeta gates deshabilitados.
"""
import json

import pytest


def make_write_input(file_path: str, content: str) -> dict:
    """Construye input JSON que simula PreToolUse de Write."""
    return {
        "tool_input": {
            "file_path": file_path,
            "content": content,
        }
    }


class TestGateValidatorBlocking:
    """Gates configurados como 'block' retornan exit code != 0."""

    def test_blocks_env_commit(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            make_write_input(".env", "SECRET_KEY=xxx"),
            isolated_cognito_env,
        )
        # .env debe ser bloqueado
        assert rc != 0, f"Gate no bloqueó .env. Stdout: {stdout}, Stderr: {stderr}"

    def test_blocks_pii_hardcode(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            make_write_input("src/config.ts", 'const email = "user@example.com";'),
            isolated_cognito_env,
        )
        assert rc != 0, f"Gate no bloqueó PII hardcode. Stdout: {stdout}, Stderr: {stderr}"


class TestGateValidatorWarning:
    """Gates configurados como 'warn' retornan exit 0 pero con mensaje."""

    def _enable_gate(self, isolated_cognito_env, gate_id):
        """Helper: activa un gate opt-in en _operator-config.json."""
        import json
        op_path = isolated_cognito_env / "config" / "_operator-config.json"
        with open(op_path) as f:
            config = json.load(f)
        if gate_id not in config["gates"]["enabled"]:
            config["gates"]["enabled"].append(gate_id)
        with open(op_path, "w") as f:
            json.dump(config, f)

    def test_warns_about_n8n(self, run_hook_fn, isolated_cognito_env):
        """n8n-retired es opt-in (operator profile). Activarlo debe disparar warning."""
        self._enable_gate(isolated_cognito_env, "n8n-retired")
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            make_write_input("workflow.json", '{"name": "n8n workflow"}'),
            isolated_cognito_env,
        )
        assert rc == 0, "n8n es warn-and-confirm, no block → exit 0"
        assert "n8n" in stdout.lower() or "systemMessage" in stdout, \
            f"Warning de n8n no emitido. Stdout: {stdout}"

    def test_n8n_not_in_default_enabled(self, operator_config):
        """Regresión para A2: los defaults son neutros (solo gates universales)."""
        enabled = operator_config["gates"]["enabled"]
        # Defaults solo incluye universales
        assert "n8n-retired" not in enabled, "n8n-retired no debe ser default (es opt-in)"
        assert "operator-pricing-check" not in enabled, "operator-pricing-check no debe ser default"
        assert "no-commit-env" in enabled, "no-commit-env es universal, debe estar"
        assert "no-hardcode-pii" in enabled, "no-hardcode-pii es universal, debe estar"


class TestGateValidatorClean:
    """Contenido limpio no debe disparar ningún gate."""

    def test_clean_content_passes(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            make_write_input("README.md", "# Mi proyecto\n\nHola mundo"),
            isolated_cognito_env,
        )
        assert rc == 0
        # Sin violaciones, stdout vacío o sin systemMessage
        assert "systemMessage" not in stdout


class TestGateValidatorRobustness:
    """Robustez ante inputs problemáticos."""

    def test_no_file_path(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            {"tool_input": {}},
            isolated_cognito_env,
        )
        # Sin file_path no debe crashear
        assert rc == 0

    def test_empty_content(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            make_write_input("archivo.ts", ""),
            isolated_cognito_env,
        )
        assert rc == 0


class TestGateValidatorDisabled:
    """Gates deshabilitados en operator-config no deben disparar."""

    def test_disabled_gate_does_not_fire(self, isolated_cognito_env, run_hook_fn):
        import json
        # Deshabilitar el gate n8n-retired
        op_config_path = isolated_cognito_env / "config" / "_operator-config.json"
        with open(op_config_path) as f:
            config = json.load(f)
        config["gates"]["enabled"] = [g for g in config["gates"]["enabled"] if g != "n8n-retired"]
        config["gates"]["disabled"] = ["n8n-retired"]
        with open(op_config_path, "w") as f:
            json.dump(config, f)

        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            make_write_input("workflow.json", '{"type": "n8n-workflow"}'),
            isolated_cognito_env,
        )
        assert rc == 0
        # No debe haber warning de n8n
        assert "n8n" not in stdout.lower() or "systemMessage" not in stdout
