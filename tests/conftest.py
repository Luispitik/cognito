"""
conftest.py — Fixtures compartidos para tests de Cognito.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Raíz del proyecto: dos niveles arriba de este archivo
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CONFIG_DIR = PROJECT_ROOT / "config"
HOOKS_DIR = PROJECT_ROOT / "hooks"
MODES_DIR = PROJECT_ROOT / "modes"
PHASES_DIR = PROJECT_ROOT / "phases"
COMMANDS_DIR = PROJECT_ROOT / "commands"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
PROFILES_DIR = PROJECT_ROOT / "profiles"


@pytest.fixture
def project_root():
    """Raíz del proyecto Cognito."""
    return PROJECT_ROOT


@pytest.fixture
def config_dir():
    return CONFIG_DIR


@pytest.fixture
def hooks_dir():
    return HOOKS_DIR


@pytest.fixture
def modes_dir():
    return MODES_DIR


@pytest.fixture
def phases_dir():
    return PHASES_DIR


@pytest.fixture
def commands_dir():
    return COMMANDS_DIR


@pytest.fixture
def templates_dir():
    return TEMPLATES_DIR


@pytest.fixture
def profiles_dir():
    return PROFILES_DIR


@pytest.fixture
def load_config():
    """Factory para cargar cualquier JSON de config."""
    def _load(name: str) -> dict:
        path = CONFIG_DIR / name
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return _load


@pytest.fixture
def modes_config(load_config):
    return load_config("_modes.json")


@pytest.fixture
def phases_config(load_config):
    return load_config("_phases.json")


@pytest.fixture
def phase_state_default(load_config):
    return load_config("_phase-state.default.json")


@pytest.fixture
def operator_config(load_config):
    return load_config("_operator-config.json")


@pytest.fixture
def triggers_config(load_config):
    return load_config("_passive-triggers.json")


@pytest.fixture
def isolated_cognito_env(tmp_path, monkeypatch):
    """
    Crea una copia aislada del proyecto Cognito en tmp_path para que los hooks
    puedan ejecutarse sin modificar el estado real.
    """
    isolated = tmp_path / "cognito"
    shutil.copytree(PROJECT_ROOT, isolated, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", "tests", ".git", "node_modules"
    ))

    # Apuntar COGNITO_DIR al entorno aislado
    monkeypatch.setenv("COGNITO_DIR", str(isolated))

    # Inicializar phase-state
    default = isolated / "config" / "_phase-state.default.json"
    target = isolated / "config" / "_phase-state.json"
    if default.exists():
        shutil.copy(default, target)

    yield isolated


def run_hook(hook_name: str, stdin_data: dict, cognito_dir: Path):
    """
    Ejecuta un hook bash con stdin JSON y retorna (stdout, stderr, exit_code).

    Usa cwd al directorio de hooks para evitar problemas con paths Windows
    en Git Bash (que no entiende `C:\\...` bien).
    """
    import subprocess
    hooks_dir = cognito_dir / "hooks"
    env = os.environ.copy()
    env["COGNITO_DIR"] = cognito_dir.as_posix()
    # Asegurar PATH incluye directorios comunes
    if "PATH" in env:
        env["PATH"] = str(cognito_dir) + os.pathsep + env["PATH"]

    result = subprocess.run(
        ["bash", hook_name],
        cwd=str(hooks_dir),
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout, result.stderr, result.returncode


@pytest.fixture
def run_hook_fn():
    return run_hook
