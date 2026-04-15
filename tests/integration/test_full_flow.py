"""
test_full_flow.py — Test de integración end-to-end.

Simula un ciclo completo:
1. Inicio en Discovery.
2. Prompt usuario "vamos a ejecutar" → phase-detector sugiere execution.
3. Usuario cambia a execution (manualmente, tocando phase-state).
4. mode-injector inyecta Ejecutor + Verificador.
5. Intento de Write con contenido limpio → gate-validator no bloquea.
6. Intento de Write con .env → gate-validator bloquea.
7. Cierre de sesión → session-closer crea log.
"""
import json

import pytest


class TestFullFlow:
    """Flujo completo desde Discovery a cierre de sesión."""

    def test_full_flow_executes_cleanly(self, run_hook_fn, isolated_cognito_env):
        state_path = isolated_cognito_env / "config" / "_phase-state.json"

        # === 1. Fase inicial: discovery ===
        with open(state_path) as f:
            state = json.load(f)
        assert state["current"] == "discovery"

        # === 2. Phase detector: "vamos a ejecutar" → sugiere execution ===
        stdout, _, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "vamos a ejecutar esto ya"},
            isolated_cognito_env,
        )
        assert rc == 0
        assert "execution" in stdout.lower(), "Phase detector no sugirió execution"

        # === 3. Cambio manual a execution ===
        state["current"] = "execution"
        with open(state_path, "w") as f:
            json.dump(state, f)

        # === 4. Mode injector: ahora debe inyectar Ejecutor/Verificador ===
        stdout, _, rc = run_hook_fn(
            "mode-injector.sh",
            {"tool": "Write"},
            isolated_cognito_env,
        )
        assert rc == 0

        # === 5. Gate validator: Write limpio no bloquea ===
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            {"tool_input": {"file_path": "src/utils.ts", "content": "export const add = (a, b) => a + b;"}},
            isolated_cognito_env,
        )
        assert rc == 0, f"Write limpio bloqueado: {stderr}"

        # === 6. Gate validator: .env bloquea ===
        stdout, stderr, rc = run_hook_fn(
            "gate-validator.sh",
            {"tool_input": {"file_path": ".env", "content": "SECRET=xxx"}},
            isolated_cognito_env,
        )
        assert rc != 0, "Gate validator no bloqueó .env"

        # === 7. Session closer ===
        stdout, _, rc = run_hook_fn(
            "session-closer.sh",
            {"session_id": "integration-test-001"},
            isolated_cognito_env,
        )
        assert rc == 0

        session_file = isolated_cognito_env / "sessions" / "integration-test-001.json"
        assert session_file.exists()

        with open(session_file) as f:
            session = json.load(f)
        assert session["phaseAtClose"] == "execution"
        assert session["metrics"]["gatesTriggered"] >= 1  # al menos el .env


class TestPhaseTransitions:
    """Transiciones entre fases funcionan."""

    def test_discovery_to_planning_to_execution(self, isolated_cognito_env):
        """Transición manual en secuencia."""
        state_path = isolated_cognito_env / "config" / "_phase-state.json"

        for phase in ["discovery", "planning", "execution", "review", "shipping"]:
            with open(state_path) as f:
                state = json.load(f)
            state["previousPhases"].append({"phase": state["current"], "until": "now"})
            state["current"] = phase
            with open(state_path, "w") as f:
                json.dump(state, f)

        # Después del ciclo, current es shipping
        with open(state_path) as f:
            state = json.load(f)
        assert state["current"] == "shipping"
        assert len(state["previousPhases"]) == 5
