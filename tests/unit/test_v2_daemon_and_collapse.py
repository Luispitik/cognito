"""Regression tests for v2.0 features: hook daemon, collapse modes, marketplace.

These tests DO exercise real subprocess + real sockets (daemon) so they are
tagged `slow` implicitly by being in this file. They pass on all three OSs
the CI matrix targets; platform-specific branches inside the daemon itself
(AF_UNIX vs AF_INET) are exercised by the matching runner.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from hooks.python import _daemon  # noqa: E402


@pytest.fixture
def isolated_cognito(tmp_path, monkeypatch):
    """Copy the repo into tmp_path so daemon writes don't pollute the source."""
    dest = tmp_path / "cognito"
    shutil.copytree(
        REPO,
        dest,
        ignore=shutil.ignore_patterns(
            "__pycache__", ".pytest_cache", "tests", ".git", "node_modules",
            "logs", "sessions", "runtime",
        ),
    )
    # Seed a valid phase-state.
    default = dest / "config" / "_phase-state.default.json"
    state = dest / "config" / "_phase-state.json"
    if default.is_file():
        shutil.copy(default, state)
    monkeypatch.setenv("COGNITO_DIR", str(dest))
    monkeypatch.setenv("COGNITO_DIR_RESOLVED", str(dest))
    return dest


# --------------------------------------------------------------------- #
# Daemon lifecycle
# --------------------------------------------------------------------- #
class TestHookDaemon:
    def _spawn_daemon(self, cognito_dir: Path) -> subprocess.Popen:
        env = os.environ.copy()
        env["COGNITO_DIR"] = str(cognito_dir)
        env["COGNITO_DIR_RESOLVED"] = str(cognito_dir)
        proc = subprocess.Popen(
            [sys.executable, str(REPO / "hooks" / "python" / "_daemon.py"), "serve"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait up to 3s for pid file + socket/addr to appear.
        pid_file = cognito_dir / "runtime" / "hook.pid"
        for _ in range(30):
            time.sleep(0.1)
            if pid_file.is_file():
                break
        assert pid_file.is_file(), "daemon never wrote its pid file"
        return proc

    def _stop_daemon(self, proc: subprocess.Popen):
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def test_daemon_responds_to_phase_detector_via_client(self, isolated_cognito):
        proc = self._spawn_daemon(isolated_cognito)
        try:
            # Invoke via the client subcommand exactly like the .sh wrapper does.
            env = os.environ.copy()
            env["COGNITO_DIR"] = str(isolated_cognito)
            env["COGNITO_DIR_RESOLVED"] = str(isolated_cognito)
            env["INPUT_JSON"] = json.dumps({"prompt": "vamos a ejecutar ya"})
            result = subprocess.run(
                [sys.executable, str(REPO / "hooks" / "python" / "_daemon.py"),
                 "client", "phase-detector"],
                env=env, capture_output=True, text=True, timeout=5,
            )
            assert result.returncode == 0, f"rc={result.returncode} stderr={result.stderr}"
            assert "execution" in result.stdout.lower()
        finally:
            self._stop_daemon(proc)

    def test_client_returns_127_when_daemon_down(self, isolated_cognito):
        # Ensure no daemon is running for this cognito_dir
        runtime = isolated_cognito / "runtime"
        if runtime.exists():
            shutil.rmtree(runtime)
        env = os.environ.copy()
        env["COGNITO_DIR"] = str(isolated_cognito)
        env["COGNITO_DIR_RESOLVED"] = str(isolated_cognito)
        env["INPUT_JSON"] = "{}"
        result = subprocess.run(
            [sys.executable, str(REPO / "hooks" / "python" / "_daemon.py"),
             "client", "phase-detector"],
            env=env, capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 127, "client must return 127 when daemon unreachable"

    def test_daemon_handle_request_direct(self, isolated_cognito, monkeypatch):
        """Exercise the in-process request handler without touching sockets."""
        monkeypatch.setenv("COGNITO_DIR_RESOLVED", str(isolated_cognito))
        payload = json.dumps({
            "hook": "phase-detector",
            "cognito_dir": str(isolated_cognito),
            "stdin": json.dumps({"prompt": "vamos a ejecutar ya"}),
        })
        resp_line = _daemon._handle_request(payload)
        resp = json.loads(resp_line)
        assert resp["rc"] == 0
        assert "execution" in resp["stdout"].lower()

    def test_daemon_rejects_unknown_hook(self, isolated_cognito):
        payload = json.dumps({"hook": "not-a-hook", "cognito_dir": str(isolated_cognito), "stdin": "{}"})
        resp = json.loads(_daemon._handle_request(payload))
        assert resp["rc"] == 2
        assert "unknown hook" in resp["stderr"]

    def test_daemon_handles_invalid_json(self):
        resp = json.loads(_daemon._handle_request("not json"))
        assert resp["rc"] == 2


# --------------------------------------------------------------------- #
# Collapse v2 aliases
# --------------------------------------------------------------------- #
class TestCollapseV2:
    def _seed_operator_config(self, cognito_dir: Path, *, collapse: bool, modes_enabled: list[str]):
        cfg_path = cognito_dir / "config" / "_operator-config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg.setdefault("modes", {})
        cfg["modes"]["enabled"] = modes_enabled
        cfg["modes"]["disabled"] = []
        cfg["modes"]["collapseV2"] = collapse
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    def _set_phase(self, cognito_dir: Path, phase: str, override_modes: list[str] | None = None):
        state_path = cognito_dir / "config" / "_phase-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["current"] = phase
        if override_modes is not None:
            state["overrideModes"] = override_modes
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _run_injector(self, cognito_dir: Path) -> tuple[int, str]:
        env = os.environ.copy()
        env["COGNITO_DIR"] = str(cognito_dir)
        env["COGNITO_DIR_RESOLVED"] = str(cognito_dir)
        env["INPUT_JSON"] = "{}"
        result = subprocess.run(
            [sys.executable, str(REPO / "hooks" / "python" / "mode_injector.py")],
            env=env, capture_output=True, text=True, timeout=15,
        )
        return result.returncode, result.stdout

    def test_collapse_off_preserves_estratega_header(self, isolated_cognito):
        self._seed_operator_config(
            isolated_cognito, collapse=False,
            modes_enabled=["divergente", "estratega"],
        )
        self._set_phase(isolated_cognito, "discovery", override_modes=[])
        rc, out = self._run_injector(isolated_cognito)
        assert rc == 0
        if out.strip():
            msg = json.loads(out)["systemMessage"]
            assert "Modo activo: estratega" in msg
            assert "preset:" not in msg

    def test_collapse_on_rewrites_estratega_to_divergente_preset(self, isolated_cognito):
        self._seed_operator_config(
            isolated_cognito, collapse=True,
            modes_enabled=["divergente", "estratega"],
        )
        self._set_phase(isolated_cognito, "discovery", override_modes=[])
        rc, out = self._run_injector(isolated_cognito)
        assert rc == 0, out
        assert out.strip(), "injector must emit a payload when modes are active"
        msg = json.loads(out)["systemMessage"]
        assert "Modo activo: estratega" not in msg, "collapse did not suppress aliased mode"
        assert "Modo activo: divergente (preset: time-horizon)" in msg

    def test_collapse_on_rewrites_devils_advocate_to_auditor_preset(self, isolated_cognito):
        self._seed_operator_config(
            isolated_cognito, collapse=True,
            modes_enabled=["auditor", "devils-advocate"],
        )
        self._set_phase(isolated_cognito, "review", override_modes=[])
        rc, out = self._run_injector(isolated_cognito)
        assert rc == 0, out
        assert out.strip(), "injector must emit when review modes are active"
        msg = json.loads(out)["systemMessage"]
        assert "Modo activo: devils-advocate" not in msg
        assert "Modo activo: auditor (preset: pre-mortem)" in msg


# --------------------------------------------------------------------- #
# Marketplace install-mode.sh
# --------------------------------------------------------------------- #
@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="install-mode.sh uses mktemp/curl/wget which need a proper POSIX env.",
)
class TestMarketplaceInstaller:
    def _write_registry(self, tmp_path: Path, modes: dict) -> Path:
        path = tmp_path / "registry.json"
        path.write_text(json.dumps({"modes": modes}), encoding="utf-8")
        return path

    def test_install_local_mode(self, tmp_path):
        src_skill = tmp_path / "mymode-src" / "SKILL.md"
        src_skill.parent.mkdir()
        src_skill.write_text("---\nname: mymode\n---\n# My mode\n", encoding="utf-8")

        result = subprocess.run(
            ["bash", str(REPO / "scripts" / "install-mode.sh"),
             f"--local={src_skill}",
             f"--target={tmp_path}",
             "mymode"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, result.stderr
        installed = tmp_path / "modes" / "custom" / "mymode" / "SKILL.md"
        assert installed.is_file()
        assert "# My mode" in installed.read_text(encoding="utf-8")

    def test_refuses_overwrite_without_force(self, tmp_path):
        src_skill = tmp_path / "src" / "SKILL.md"
        src_skill.parent.mkdir()
        src_skill.write_text("v1", encoding="utf-8")
        base = ["bash", str(REPO / "scripts" / "install-mode.sh"),
                f"--local={src_skill}", f"--target={tmp_path}", "clash"]
        # first install: ok
        r1 = subprocess.run(base, capture_output=True, text=True, timeout=15)
        assert r1.returncode == 0
        # second without --force: must fail
        src_skill.write_text("v2", encoding="utf-8")
        r2 = subprocess.run(base, capture_output=True, text=True, timeout=15)
        assert r2.returncode == 1
        assert "already installed" in r2.stderr
        # With --force it must succeed and overwrite.
        r3 = subprocess.run(base + ["--force"], capture_output=True, text=True, timeout=15)
        assert r3.returncode == 0
        installed = tmp_path / "modes" / "custom" / "clash" / "SKILL.md"
        assert installed.read_text(encoding="utf-8") == "v2"
