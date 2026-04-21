"""Regression tests for v1.2 install.sh --dry-run and cognition-verify.sh --repair."""
from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], env: dict | None = None, input_: str | None = None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(REPO),
        env=full_env,
        input=input_,
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )


@pytest.mark.skipif(
    platform.system() == "Windows" and "CI" in os.environ,
    reason="Subprocess bash on Windows GH runners needs a custom shell path.",
)
class TestInstallDryRun:
    """`install.sh --dry-run` must describe the plan without touching the FS."""

    def test_dry_run_creates_no_files(self, tmp_path):
        target = tmp_path / "fake-install"
        result = _run([
            "bash", "scripts/install.sh",
            "--profile=public",
            f"--target={target.as_posix()}",
            "--skip-settings",
            "--dry-run",
        ])
        assert result.returncode == 0, result.stderr
        assert "[dry-run]" in result.stdout, "dry-run marker missing from output"
        assert "Dry-run complete" in result.stdout, "dry-run did not print completion banner"
        assert not target.exists(), f"dry-run created {target} which it must not"

    def test_dry_run_lists_hooks(self, tmp_path):
        target = tmp_path / "fake-install-2"
        result = _run([
            "bash", "scripts/install.sh",
            "--profile=operator",
            f"--target={target.as_posix()}",
            "--skip-settings",
            "--dry-run",
        ])
        assert result.returncode == 0
        # Operator profile installs all 4 hooks.
        for hook in ("phase-detector", "mode-injector", "gate-validator", "session-closer"):
            assert hook in result.stdout, f"dry-run did not mention hook {hook}"


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason=(
        "Subprocess bash on Windows reinterprets Windows tmpdir paths through "
        "MSYS (C:/... -> /c/...), which makes `--target=C:/...` land on an "
        "MSYS-translated path invisible to Python's Path.exists(). The repair "
        "flow is verified via the standalone pytest_install_repair smoke in "
        "run_tests.sh and by the Linux/macOS matrix in .github/workflows/test.yml."
    ),
)
class TestVerifyRepair:
    """`cognition-verify.sh --repair` must fix corrupted phase-state."""

    def _install_fresh(self, target: Path):
        """Real install into tmp_path target."""
        result = _run([
            "bash", "scripts/install.sh",
            "--profile=public",
            f"--target={target.as_posix()}",
            "--skip-settings",
        ])
        assert result.returncode == 0, f"install failed: {result.stderr}"

    def test_repair_restores_corrupt_phase_state(self, tmp_path):
        target = tmp_path / "cognito-inst"
        self._install_fresh(target)

        state = target / "config" / "_phase-state.json"
        assert state.is_file(), "state file should exist after install"
        state.write_text("{{{ not json", encoding="utf-8")

        # Verify without repair: must FAIL on the corrupted state.
        result = _run([
            "bash", "scripts/cognition-verify.sh",
            f"--target={target.as_posix()}",
        ])
        assert "FAIL" in result.stdout or result.returncode != 0

        # Verify with --repair: must succeed and restore the file.
        result = _run([
            "bash", "scripts/cognition-verify.sh",
            f"--target={target.as_posix()}",
            "--repair",
        ])
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
        assert "Repaired:" in result.stdout or "repair/" in result.stdout
        # Post-repair state must be valid JSON again.
        restored = json.loads(state.read_text(encoding="utf-8"))
        assert restored.get("current") == "discovery"

        incidents = target / "logs" / "incidents.log"
        assert incidents.is_file(), "repair must append to logs/incidents.log"
        assert "phase-state repaired" in incidents.read_text(encoding="utf-8")

    def test_repair_keeps_broken_backup(self, tmp_path):
        """Broken file is kept as `_phase-state.broken.<ts>.json` for forensics."""
        target = tmp_path / "cognito-inst-b"
        self._install_fresh(target)
        state = target / "config" / "_phase-state.json"
        state.write_text("broken", encoding="utf-8")

        _run([
            "bash", "scripts/cognition-verify.sh",
            f"--target={target.as_posix()}",
            "--repair",
        ])
        backups = list((target / "config").glob("_phase-state.broken.*.json"))
        assert backups, "forensic backup of broken state missing"

    def test_repair_noop_when_state_is_clean(self, tmp_path):
        target = tmp_path / "cognito-inst-clean"
        self._install_fresh(target)
        result = _run([
            "bash", "scripts/cognition-verify.sh",
            f"--target={target.as_posix()}",
            "--repair",
        ])
        assert result.returncode == 0
        assert "Nothing to repair." in result.stdout
