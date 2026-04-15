"""
test_config_jsons.py — Los 5 JSONs de config son válidos y tienen el schema esperado.
"""
import json

import pytest


class TestConfigJsonsParse:
    """Los 5 JSONs parsean sin error."""

    def test_phase_state_default_parses(self, config_dir):
        with open(config_dir / "_phase-state.default.json") as f:
            json.load(f)

    def test_phase_state_parses(self, config_dir):
        with open(config_dir / "_phase-state.json") as f:
            json.load(f)

    def test_modes_parses(self, config_dir):
        with open(config_dir / "_modes.json") as f:
            json.load(f)

    def test_phases_parses(self, config_dir):
        with open(config_dir / "_phases.json") as f:
            json.load(f)

    def test_operator_config_parses(self, config_dir):
        with open(config_dir / "_operator-config.json") as f:
            json.load(f)

    def test_triggers_parses(self, config_dir):
        with open(config_dir / "_passive-triggers.json") as f:
            json.load(f)


class TestPhaseStateSchema:
    """Schema de _phase-state.json."""

    def test_has_required_fields(self, phase_state_default):
        assert "version" in phase_state_default
        assert "current" in phase_state_default
        assert "since" in phase_state_default
        assert "previousPhases" in phase_state_default
        assert "overrideModes" in phase_state_default

    def test_current_is_valid_phase(self, phase_state_default, phases_config):
        valid_phases = list(phases_config["phases"].keys())
        assert phase_state_default["current"] in valid_phases

    def test_override_modes_is_list(self, phase_state_default):
        assert isinstance(phase_state_default["overrideModes"], list)


class TestModesSchema:
    """Schema de _modes.json."""

    EXPECTED_MODES = {
        "divergente", "verificador", "devils-advocate",
        "consolidador", "ejecutor", "estratega", "auditor"
    }

    def test_has_seven_modes(self, modes_config):
        assert set(modes_config["modes"].keys()) == self.EXPECTED_MODES

    def test_each_mode_has_required_fields(self, modes_config):
        required = ["displayName", "description", "skillPath", "determinism", "triggers", "defaultPhases"]
        for mode_id, mode in modes_config["modes"].items():
            for field in required:
                assert field in mode, f"Modo {mode_id} falta field: {field}"

    def test_determinism_valid(self, modes_config):
        valid_levels = {"low", "medium", "high"}
        for mode_id, mode in modes_config["modes"].items():
            assert mode["determinism"] in valid_levels, f"Modo {mode_id} tiene determinism inválido"

    def test_skill_path_points_to_existing_file(self, modes_config, project_root):
        for mode_id, mode in modes_config["modes"].items():
            skill_path = project_root / mode["skillPath"]
            assert skill_path.exists(), f"SKILL.md de {mode_id} no existe: {skill_path}"

    def test_triggers_has_phrases(self, modes_config):
        for mode_id, mode in modes_config["modes"].items():
            assert "phrases" in mode["triggers"], f"Modo {mode_id} sin triggers.phrases"
            assert isinstance(mode["triggers"]["phrases"], list)
            assert len(mode["triggers"]["phrases"]) > 0

    def test_default_phases_reference_valid_phases(self, modes_config, phases_config):
        valid_phases = set(phases_config["phases"].keys())
        for mode_id, mode in modes_config["modes"].items():
            for phase in mode["defaultPhases"]:
                assert phase in valid_phases, f"Modo {mode_id} referencia fase inexistente: {phase}"


class TestPhasesSchema:
    """Schema de _phases.json."""

    EXPECTED_PHASES = {"discovery", "planning", "execution", "review", "shipping"}

    def test_has_five_phases(self, phases_config):
        assert set(phases_config["phases"].keys()) == self.EXPECTED_PHASES

    def test_each_phase_has_required_fields(self, phases_config):
        required = ["displayName", "description", "defaultModes", "hookIntensity", "exitSignals", "reminder"]
        for phase_id, phase in phases_config["phases"].items():
            for field in required:
                assert field in phase, f"Fase {phase_id} falta field: {field}"

    def test_default_modes_reference_valid_modes(self, phases_config, modes_config):
        valid_modes = set(modes_config["modes"].keys())
        for phase_id, phase in phases_config["phases"].items():
            for mode in phase["defaultModes"]:
                assert mode in valid_modes, f"Fase {phase_id} referencia modo inexistente: {mode}"

    def test_hook_intensity_has_all_hooks(self, phases_config):
        required_hooks = {"phase-detector", "mode-injector", "gate-validator", "session-closer"}
        for phase_id, phase in phases_config["phases"].items():
            assert set(phase["hookIntensity"].keys()) == required_hooks, \
                f"Fase {phase_id} no tiene todos los hooks en hookIntensity"

    def test_exit_signals_is_non_empty_list(self, phases_config):
        for phase_id, phase in phases_config["phases"].items():
            assert isinstance(phase["exitSignals"], list)
            assert len(phase["exitSignals"]) > 0, f"Fase {phase_id} sin exitSignals"


class TestOperatorConfigSchema:
    """Schema de _operator-config.json."""

    def test_has_required_fields(self, operator_config):
        assert "profile" in operator_config
        assert "preferences" in operator_config
        assert "modes" in operator_config
        assert "gates" in operator_config

    def test_profile_is_valid(self, operator_config):
        valid_profiles = {"operator", "alumno", "public", "client"}
        assert operator_config["profile"] in valid_profiles

    def test_modes_has_enabled_and_disabled(self, operator_config):
        assert "enabled" in operator_config["modes"]
        assert "disabled" in operator_config["modes"]
        assert isinstance(operator_config["modes"]["enabled"], list)
        assert isinstance(operator_config["modes"]["disabled"], list)

    def test_enabled_modes_are_valid(self, operator_config, modes_config):
        valid_modes = set(modes_config["modes"].keys())
        for mode in operator_config["modes"]["enabled"]:
            assert mode in valid_modes, f"Modo enabled inválido: {mode}"

    def test_default_profile_is_public(self, operator_config):
        """Regresión para A1: el default debe ser 'public' (neutro) post-auditoría."""
        assert operator_config["profile"] == "public", (
            "Default profile debe ser 'public' para que un clone sea neutro. "
            "Ver AUDIT-PRE-DEPLOY.md → A1."
        )


class TestTriggersSchema:
    """Schema de _passive-triggers.json."""

    def test_has_phase_detection_rules(self, triggers_config):
        assert "phaseDetection" in triggers_config
        assert "rules" in triggers_config["phaseDetection"]
        assert len(triggers_config["phaseDetection"]["rules"]) > 0

    def test_phase_detection_rules_reference_valid_phases(self, triggers_config, phases_config):
        valid_phases = set(phases_config["phases"].keys())
        for rule in triggers_config["phaseDetection"]["rules"]:
            assert rule["suggestPhase"] in valid_phases, \
                f"Rule '{rule['signal']}' apunta a fase inexistente: {rule['suggestPhase']}"

    def test_phase_detection_confidence_valid(self, triggers_config):
        valid = {"low", "medium", "high"}
        for rule in triggers_config["phaseDetection"]["rules"]:
            assert rule["confidence"] in valid

    def test_gates_have_required_fields(self, triggers_config):
        required = ["id", "pattern", "filesAffected", "action", "message"]
        for gate in triggers_config["gates"]["rules"]:
            for field in required:
                assert field in gate, f"Gate {gate.get('id', '?')} falta: {field}"

    def test_gate_actions_valid(self, triggers_config):
        valid = {"block", "warn", "warn-and-confirm"}
        for gate in triggers_config["gates"]["rules"]:
            assert gate["action"] in valid, f"Gate {gate['id']} action inválida: {gate['action']}"

    def test_gate_patterns_are_valid_regex(self, triggers_config):
        import re
        for gate in triggers_config["gates"]["rules"]:
            try:
                re.compile(gate["pattern"])
            except re.error as e:
                pytest.fail(f"Gate {gate['id']} pattern inválido: {e}")

    def test_anchor_detection_rules_activate_existing_modes(self, triggers_config, modes_config):
        valid_modes = set(modes_config["modes"].keys())
        for rule in triggers_config["anchorDetection"]["rules"]:
            assert rule["activate"] in valid_modes, \
                f"Anchor rule activa modo inexistente: {rule['activate']}"


class TestCrossConsistency:
    """Coherencia cruzada entre archivos."""

    def test_every_enabled_gate_has_rule(self, operator_config, triggers_config):
        defined_gate_ids = {g["id"] for g in triggers_config["gates"]["rules"]}
        for gate_id in operator_config["gates"]["enabled"]:
            # Gates generic-best-practices y placeholder-client-gates son nombres de profiles, no gates concretos
            if gate_id in {"generic-best-practices", "placeholder-client-gates"}:
                continue
            assert gate_id in defined_gate_ids, f"Gate enabled '{gate_id}' no tiene rule definida"

    def test_available_gates_are_all_defined(self, operator_config, triggers_config):
        """Todos los gates listados como 'available' deben tener rule definida."""
        defined_gate_ids = {g["id"] for g in triggers_config["gates"]["rules"]}
        for gate_id in operator_config["gates"].get("available", []):
            assert gate_id in defined_gate_ids, f"Gate available '{gate_id}' no tiene rule definida"

    def test_phase_state_current_matches_existing_phase(self, phase_state_default, phases_config):
        assert phase_state_default["current"] in phases_config["phases"]
