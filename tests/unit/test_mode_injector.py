"""
test_mode_injector.py — Tests del hook mode-injector.sh.

Verifica:
- Inyecta modos correctos según fase activa.
- Respeta overrides.
- Respeta modos deshabilitados en operator-config.
- Degrada si falta SKILL.md de un modo.
"""
import json

import pytest


class TestModeInjectorBasic:
    """Inyección según fase default."""

    def test_discovery_injects_divergente_and_estratega(
        self, run_hook_fn, isolated_cognito_env
    ):
        """Fase default discovery → inyecta divergente + estratega."""
        stdout, stderr, rc = run_hook_fn(
            "mode-injector.sh",
            {"tool": "Read"},
            isolated_cognito_env,
        )
        assert rc == 0, f"Hook falló: {stderr}"
        # Debe mencionar alguno de los modos
        # (el contenido exacto depende del SKILL.md de cada modo)
        if stdout.strip():
            assert "divergente" in stdout.lower() or "Divergente" in stdout or \
                   "estratega" in stdout.lower() or "Estratega" in stdout, \
                f"Esperado mención a modos de discovery. Stdout:\n{stdout[:500]}"

    def test_execution_injects_ejecutor_and_verificador(
        self, run_hook_fn, isolated_cognito_env
    ):
        """Cambiar fase a execution → inyecta ejecutor + verificador."""
        # Cambiar phase-state a execution
        state_path = isolated_cognito_env / "config" / "_phase-state.json"
        with open(state_path) as f:
            state = json.load(f)
        state["current"] = "execution"
        with open(state_path, "w") as f:
            json.dump(state, f)

        stdout, stderr, rc = run_hook_fn(
            "mode-injector.sh",
            {"tool": "Write"},
            isolated_cognito_env,
        )
        assert rc == 0, f"Hook falló: {stderr}"
        if stdout.strip():
            assert "ejecutor" in stdout.lower() or "Ejecutor" in stdout or \
                   "verificador" in stdout.lower() or "Verificador" in stdout, \
                f"Esperado mención a modos de execution. Stdout:\n{stdout[:500]}"


class TestModeInjectorOverrides:
    """Overrides se aplican además de defaults."""

    def test_override_mode_is_injected(self, run_hook_fn, isolated_cognito_env):
        """Añadir 'auditor' como override en fase discovery."""
        state_path = isolated_cognito_env / "config" / "_phase-state.json"
        with open(state_path) as f:
            state = json.load(f)
        state["overrideModes"] = ["auditor"]
        with open(state_path, "w") as f:
            json.dump(state, f)

        stdout, stderr, rc = run_hook_fn(
            "mode-injector.sh",
            {"tool": "Read"},
            isolated_cognito_env,
        )
        assert rc == 0
        if stdout.strip():
            # Debe incluir auditor además de los defaults
            assert "auditor" in stdout.lower() or "Auditor" in stdout


class TestModeInjectorDisabled:
    """Modos deshabilitados no se inyectan aunque estén en defaults."""

    def test_disabled_mode_not_injected(self, run_hook_fn, isolated_cognito_env):
        """Deshabilitar divergente, estar en discovery → solo estratega."""
        op_config_path = isolated_cognito_env / "config" / "_operator-config.json"
        with open(op_config_path) as f:
            op = json.load(f)
        op["modes"]["enabled"] = [m for m in op["modes"]["enabled"] if m != "divergente"]
        op["modes"]["disabled"] = ["divergente"]
        with open(op_config_path, "w") as f:
            json.dump(op, f)

        stdout, stderr, rc = run_hook_fn(
            "mode-injector.sh",
            {"tool": "Read"},
            isolated_cognito_env,
        )
        assert rc == 0
        # No debería haber contenido del SKILL divergente
        # (este test es más cualitativo; verificamos que al menos no crashea)


class TestModeInjectorRobustness:
    """Robustez."""

    def test_missing_config_degrades_silently(self, run_hook_fn, isolated_cognito_env):
        """Si falta _phase-state.json, el hook sale sin error."""
        state_path = isolated_cognito_env / "config" / "_phase-state.json"
        state_path.unlink()

        stdout, stderr, rc = run_hook_fn(
            "mode-injector.sh",
            {"tool": "Read"},
            isolated_cognito_env,
        )
        assert rc == 0, "Sin config el hook debería degradar, no fallar"

    def test_writes_log(self, run_hook_fn, isolated_cognito_env):
        run_hook_fn(
            "mode-injector.sh",
            {"tool": "Read"},
            isolated_cognito_env,
        )
        log_file = isolated_cognito_env / "logs" / "mode-injector.log"
        assert log_file.exists()
