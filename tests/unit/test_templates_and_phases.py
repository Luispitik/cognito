"""
test_templates_and_phases.py — Valida que templates y phase specs existen y tienen estructura mínima.
"""
import pytest


EXPECTED_TEMPLATES = [
    "matriz-decision.md",
    "pre-mortem.md",
    "steel-man.md",
    "checklist-deploy.md",
    "auditoria-output.md",
]

EXPECTED_PHASES = [
    "discovery.md",
    "planning.md",
    "execution.md",
    "review.md",
    "shipping.md",
]


class TestTemplatesExist:
    @pytest.mark.parametrize("tpl", EXPECTED_TEMPLATES)
    def test_template_exists(self, templates_dir, tpl):
        assert (templates_dir / tpl).exists(), f"Template {tpl} no existe"

    @pytest.mark.parametrize("tpl", EXPECTED_TEMPLATES)
    def test_template_has_content(self, templates_dir, tpl):
        content = (templates_dir / tpl).read_text(encoding="utf-8")
        assert len(content) > 200, f"Template {tpl} demasiado corto (< 200 chars)"

    @pytest.mark.parametrize("tpl", EXPECTED_TEMPLATES)
    def test_template_has_title(self, templates_dir, tpl):
        content = (templates_dir / tpl).read_text(encoding="utf-8")
        # Primera línea significativa debe ser un H1
        lines = [l for l in content.split("\n") if l.strip()]
        assert lines[0].startswith("# "), f"Template {tpl} sin H1 como primer elemento"


class TestPhasesExist:
    @pytest.mark.parametrize("phase", EXPECTED_PHASES)
    def test_phase_spec_exists(self, phases_dir, phase):
        assert (phases_dir / phase).exists(), f"Phase spec {phase} no existe"

    @pytest.mark.parametrize("phase", EXPECTED_PHASES)
    def test_phase_spec_has_required_sections(self, phases_dir, phase):
        content = (phases_dir / phase).read_text(encoding="utf-8")
        required_sections = ["## Objetivo", "## Modos activos"]
        for section in required_sections:
            assert section in content, f"{phase} falta sección: {section}"


class TestProfilesYaml:
    """Profiles YAML parsean."""

    EXPECTED_PROFILES = ["operator.yaml", "alumno.yaml", "public.yaml", "client.yaml"]

    @pytest.mark.parametrize("prof", EXPECTED_PROFILES)
    def test_profile_exists(self, profiles_dir, prof):
        assert (profiles_dir / prof).exists(), f"Profile {prof} no existe"

    @pytest.mark.parametrize("prof", EXPECTED_PROFILES)
    def test_profile_parses_yaml(self, profiles_dir, prof):
        """Valida que el YAML es parseable. Usa PyYAML si está; si no, parse simple."""
        import yaml
        path = profiles_dir / prof
        with open(path, encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"YAML inválido en {prof}: {e}")
        assert data is not None, f"{prof} parsea a None"
        assert "profile" in data, f"{prof} sin campo 'profile'"
