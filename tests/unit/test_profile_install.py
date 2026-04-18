"""
test_profile_install.py — Verifies that the v1.1 install.sh honors the
profile YAML (modes/hooks/gates/templates) instead of copying everything.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]

# End-to-end install tests shell out to bash. On Windows, pytest's tmp_path
# lives under C:\Users\...\AppData\Local\Temp which Git Bash / MSYS does
# not reliably write to across the MSYS -> Win32 boundary used by bash
# during cp/mkdir. CI (Ubuntu + macOS) exercises this path correctly.
_SKIP_ON_WINDOWS = pytest.mark.skipif(
    sys.platform == "win32",
    reason="bash install e2e tests validated in Linux/macOS CI; "
           "Windows Git Bash has tmp_path translation issues under AppData",
)


def _to_bash_path(path: Path) -> str:
    """Convert a Windows absolute path to Git Bash / MSYS style.

    C:\\Users\\luis\\X  ->  /c/Users/luis/X
    Linux/macOS paths are returned unchanged.
    """
    s = path.as_posix()
    if sys.platform == "win32" and len(s) > 1 and s[1] == ":":
        drive = s[0].lower()
        rest = s[2:]
        return f"/{drive}{rest}"
    return s


@pytest.fixture
def install_into(tmp_path):
    """Factory: install a given profile into tmp_path and return (target, home, stdout).

    Runs bash with cwd=REPO and a relative script path to avoid MSYS / Git Bash
    path translation issues on Windows (absolute paths with spaces break).
    HOME and --target are converted to Git Bash /c/... form on Windows so that
    install.sh's internal mkdir/cp operate in the expected directory.

    For profile=client, a minimal intake.json is created in tmp_path and passed
    via --client-intake (required since the v1.0 fix 044d4c4).
    """
    def _install(profile: str):
        target = tmp_path / "cognito"
        home = tmp_path / "home"
        (home / ".claude").mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = _to_bash_path(home)

        args = ["bash", "scripts/install.sh",
                f"--profile={profile}",
                f"--target={_to_bash_path(target)}",
                "--skip-settings"]

        if profile == "client":
            intake = tmp_path / "intake.json"
            intake.write_text(json.dumps({
                "client_name": "Test Client",
                "client_industry": "tech",
                "client_stack": ["next.js", "supabase"],
            }), encoding="utf-8")
            args.append(f"--client-intake={_to_bash_path(intake)}")

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPO),
            timeout=60,
        )
        assert result.returncode == 0, (
            f"install failed for profile={profile}:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        return target, home, result.stdout
    return _install


@_SKIP_ON_WINDOWS
class TestProfileDifferentiation:
    """The 4 profiles must produce materially different installs."""

    def test_alumno_installs_only_4_modes(self, install_into):
        target, home, _ = install_into("alumno")
        modes = sorted([p.name for p in (home / ".claude" / "skills").iterdir() if p.is_dir()])
        expected = ["consolidador", "divergente", "ejecutor", "verificador"]
        assert modes == expected, f"alumno should get 4 modes, got {modes}"

    def test_operator_installs_all_7_modes(self, install_into):
        target, home, _ = install_into("operator")
        modes = sorted([p.name for p in (home / ".claude" / "skills").iterdir() if p.is_dir()])
        expected = sorted([
            "auditor", "consolidador", "devils-advocate", "divergente",
            "ejecutor", "estratega", "verificador",
        ])
        assert modes == expected, f"operator should get 7 modes, got {modes}"

    def test_alumno_gets_only_2_hooks(self, install_into):
        target, _, _ = install_into("alumno")
        hooks = sorted([p.name for p in (target / "hooks").glob("*.sh")])
        expected = ["gate-validator.sh", "mode-injector.sh"]
        assert hooks == expected, f"alumno hooks should be {expected}, got {hooks}"

    def test_operator_gets_all_4_hooks(self, install_into):
        target, _, _ = install_into("operator")
        hooks = sorted([p.name for p in (target / "hooks").glob("*.sh")])
        expected = sorted([
            "gate-validator.sh", "mode-injector.sh",
            "phase-detector.sh", "session-closer.sh",
        ])
        assert hooks == expected

    def test_alumno_gets_only_2_templates(self, install_into):
        target, _, _ = install_into("alumno")
        tpls = sorted([p.name for p in (target / "templates").glob("*.md")])
        expected = ["checklist-deploy.md", "matriz-decision.md"]
        assert tpls == expected

    def test_operator_gets_all_5_templates(self, install_into):
        target, _, _ = install_into("operator")
        tpls = sorted([p.name for p in (target / "templates").glob("*.md")])
        assert len(tpls) == 5

    def test_profile_string_written_to_operator_config(self, install_into):
        for profile in ["alumno", "operator", "public", "client"]:
            target, _, _ = install_into(profile)
            cfg_path = target / "config" / "_operator-config.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            assert cfg["profile"] == profile
            # modes.enabled and gates.enabled must reflect the profile YAML,
            # not the v1.0 defaults.
            assert "modes" in cfg and "enabled" in cfg["modes"]
            assert "gates" in cfg and "enabled" in cfg["gates"]


@_SKIP_ON_WINDOWS
class TestIdempotency:
    """Reinstall must back up and preserve _phase-state.json."""

    def test_reinstall_backs_up_previous_install(self, install_into, tmp_path):
        install_into("alumno")
        target = tmp_path / "cognito"
        home = tmp_path / "home"
        env = os.environ.copy()
        env["HOME"] = _to_bash_path(home)
        result = subprocess.run(
            ["bash", "scripts/install.sh",
             "--profile=alumno",
             f"--target={_to_bash_path(target)}",
             "--skip-settings"],
            capture_output=True, text=True, env=env, cwd=str(REPO), timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "Backing up" in result.stdout, result.stdout
        backups = list((home / ".claude" / "cognito-backups").iterdir())
        assert len(backups) >= 1, "reinstall did not create a backup"

    def test_reinstall_preserves_phase_state(self, install_into, tmp_path):
        target, home, _ = install_into("operator")
        ps_path = target / "config" / "_phase-state.json"
        state = json.loads(ps_path.read_text(encoding="utf-8"))
        state["current"] = "execution"
        state["customMarker"] = "should-survive-reinstall"
        ps_path.write_text(json.dumps(state), encoding="utf-8")

        env = os.environ.copy()
        env["HOME"] = _to_bash_path(home)
        result = subprocess.run(
            ["bash", "scripts/install.sh",
             "--profile=operator",
             f"--target={_to_bash_path(target)}",
             "--skip-settings"],
            capture_output=True, text=True, env=env, cwd=str(REPO), timeout=60,
        )
        assert result.returncode == 0, result.stderr

        survived = json.loads(ps_path.read_text(encoding="utf-8"))
        assert survived.get("current") == "execution"
        assert survived.get("customMarker") == "should-survive-reinstall"


@_SKIP_ON_WINDOWS
class TestProfileYamlParser:
    """The stdlib-only YAML subset parser must extract every section correctly."""

    def test_public_profile_has_empty_gates_list(self, install_into):
        target, _, _ = install_into("public")
        cfg = json.loads((target / "config" / "_operator-config.json").read_text(encoding="utf-8"))
        assert cfg["gates"]["enabled"] == [], (
            f"public profile should have no gates, got: {cfg['gates']['enabled']}"
        )

    def test_operator_gates_match_yaml(self, install_into):
        target, _, _ = install_into("operator")
        cfg = json.loads((target / "config" / "_operator-config.json").read_text(encoding="utf-8"))
        expected_gates = {
            "n8n-retired", "rls-supabase-required", "no-hardcode-pii",
            "no-commit-env", "operator-pricing-check", "eu-ai-act-sources",
        }
        assert set(cfg["gates"]["enabled"]) == expected_gates
