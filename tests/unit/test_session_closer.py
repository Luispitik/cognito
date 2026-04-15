"""
test_session_closer.py — Tests del hook session-closer.sh.

Verifica:
- Crea registro de sesión en sessions/.
- Actualiza phase-state con sessionId.
- Incluye métricas básicas.
- Robustez sin archivos previos.
"""
import json

import pytest


class TestSessionCloserBasic:
    """Funcionamiento normal."""

    def test_creates_session_file(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "session-closer.sh",
            {"session_id": "test-session-001"},
            isolated_cognito_env,
        )
        assert rc == 0, f"Hook falló: {stderr}"

        session_file = isolated_cognito_env / "sessions" / "test-session-001.json"
        assert session_file.exists(), f"Session file no creado: {session_file}"

    def test_session_file_has_required_fields(self, run_hook_fn, isolated_cognito_env):
        run_hook_fn(
            "session-closer.sh",
            {"session_id": "test-fields"},
            isolated_cognito_env,
        )
        session_file = isolated_cognito_env / "sessions" / "test-fields.json"
        with open(session_file) as f:
            data = json.load(f)

        assert "sessionId" in data
        assert "closedAt" in data
        assert "phaseAtClose" in data
        assert "metrics" in data

    def test_metrics_are_present(self, run_hook_fn, isolated_cognito_env):
        run_hook_fn(
            "session-closer.sh",
            {"session_id": "test-metrics"},
            isolated_cognito_env,
        )
        session_file = isolated_cognito_env / "sessions" / "test-metrics.json"
        with open(session_file) as f:
            data = json.load(f)

        metrics = data["metrics"]
        assert "gatesTriggered" in metrics
        assert "modeInjections" in metrics
        assert "phaseDetections" in metrics
        # Los valores son ints (o convertibles)
        assert isinstance(metrics["gatesTriggered"], int)


class TestSessionCloserPhaseState:
    """Actualiza phase-state con session info."""

    def test_updates_phase_state_session_id(self, run_hook_fn, isolated_cognito_env):
        run_hook_fn(
            "session-closer.sh",
            {"session_id": "test-phase-state"},
            isolated_cognito_env,
        )

        state_file = isolated_cognito_env / "config" / "_phase-state.json"
        with open(state_file) as f:
            state = json.load(f)

        assert state.get("sessionId") == "test-phase-state"
        assert state.get("lastUpdatedBy") == "session-closer"


class TestSessionCloserRobustness:
    """Robustez."""

    def test_no_session_id_provided(self, run_hook_fn, isolated_cognito_env):
        """Si no hay session_id, el hook genera uno automáticamente."""
        stdout, stderr, rc = run_hook_fn(
            "session-closer.sh",
            {},
            isolated_cognito_env,
        )
        assert rc == 0

        # Debe haber un archivo en sessions/
        sessions_dir = isolated_cognito_env / "sessions"
        files = list(sessions_dir.glob("session-*.json"))
        assert len(files) > 0, "Debería haber creado session-YYYYMMDD-HHMMSS.json"

    def test_missing_phase_state(self, run_hook_fn, isolated_cognito_env):
        """Si falta phase-state, el hook no debe crashear."""
        state_path = isolated_cognito_env / "config" / "_phase-state.json"
        state_path.unlink()

        stdout, stderr, rc = run_hook_fn(
            "session-closer.sh",
            {"session_id": "test-no-state"},
            isolated_cognito_env,
        )
        assert rc == 0
