"""
test_skills_frontmatter.py — Valida frontmatter de cada SKILL.md (modos + meta).
"""
import re

import pytest


def parse_frontmatter(path):
    """Extrae el frontmatter YAML de un archivo markdown."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    # Parser YAML simple para cases predecibles
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line and not line.strip().startswith("-") and not line.strip().startswith("#"):
            key, *rest = line.split(":", 1)
            fm[key.strip()] = rest[0].strip() if rest else ""
    return fm


class TestMetaSkillFrontmatter:
    """SKILL.md raíz del orquestador."""

    def test_meta_skill_has_frontmatter(self, project_root):
        path = project_root / "SKILL.md"
        fm = parse_frontmatter(path)
        assert fm is not None, "Meta SKILL.md sin frontmatter"

    def test_meta_skill_required_fields(self, project_root):
        path = project_root / "SKILL.md"
        fm = parse_frontmatter(path)
        assert "name" in fm
        assert "description" in fm
        assert "version" in fm

    def test_meta_skill_name_is_cognito(self, project_root):
        fm = parse_frontmatter(project_root / "SKILL.md")
        assert fm["name"] == "cognito"


MODE_NAMES = [
    "divergente", "verificador", "devils-advocate",
    "consolidador", "ejecutor", "estratega", "auditor",
]


class TestModeSkillsFrontmatter:
    """SKILL.md de cada modo."""

    @pytest.mark.parametrize("mode", MODE_NAMES)
    def test_mode_skill_exists(self, modes_dir, mode):
        assert (modes_dir / mode / "SKILL.md").exists(), f"SKILL.md de {mode} no existe"

    @pytest.mark.parametrize("mode", MODE_NAMES)
    def test_mode_skill_has_frontmatter(self, modes_dir, mode):
        fm = parse_frontmatter(modes_dir / mode / "SKILL.md")
        assert fm is not None, f"SKILL.md de {mode} sin frontmatter"

    @pytest.mark.parametrize("mode", MODE_NAMES)
    def test_mode_skill_has_required_fields(self, modes_dir, mode):
        fm = parse_frontmatter(modes_dir / mode / "SKILL.md")
        required = ["name", "description", "version", "mode", "determinism"]
        for field in required:
            assert field in fm, f"{mode} SKILL.md falta: {field}"

    @pytest.mark.parametrize("mode", MODE_NAMES)
    def test_mode_name_matches_id(self, modes_dir, mode):
        fm = parse_frontmatter(modes_dir / mode / "SKILL.md")
        # El campo 'mode' debe matchear el directorio
        assert fm["mode"] == mode, \
            f"SKILL.md de {mode} tiene mode={fm['mode']}, debería ser {mode}"

    @pytest.mark.parametrize("mode", MODE_NAMES)
    def test_mode_determinism_valid(self, modes_dir, mode):
        fm = parse_frontmatter(modes_dir / mode / "SKILL.md")
        assert fm["determinism"] in {"low", "medium", "high"}, \
            f"{mode} determinism inválido: {fm['determinism']}"

    @pytest.mark.parametrize("mode", MODE_NAMES)
    def test_mode_name_has_cognito_prefix(self, modes_dir, mode):
        fm = parse_frontmatter(modes_dir / mode / "SKILL.md")
        assert fm["name"].startswith("cognito-"), \
            f"{mode} name debería empezar con 'cognito-': {fm['name']}"


class TestCommandsFrontmatter:
    """Commands .md tienen frontmatter con description."""

    EXPECTED_COMMANDS = [
        "fase.md", "modo.md", "cognition-status.md",
        "divergir.md", "verificar.md", "devils-advocate.md",
        "consolidar.md", "ejecutar.md", "estratega.md", "auditar.md",
    ]

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_exists(self, commands_dir, cmd):
        assert (commands_dir / cmd).exists(), f"Command {cmd} no existe"

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_has_description(self, commands_dir, cmd):
        fm = parse_frontmatter(commands_dir / cmd)
        assert fm is not None, f"{cmd} sin frontmatter"
        assert "description" in fm, f"{cmd} sin description"
        assert len(fm["description"]) > 10, f"{cmd} description demasiado corta"
