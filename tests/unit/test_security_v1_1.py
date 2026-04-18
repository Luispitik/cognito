"""
test_security_v1_1.py — Regression tests for the security fixes in v1.1.0.

Covers:
- session-closer sanitizes session_id (no path traversal)
- install.sh rejects unknown profile names
- install.sh fails loudly without python3 (smoke — can't easily remove python3
  inside pytest, so we test the whitelist branch instead)
- dashboard/serve.sh binds 127.0.0.1 by default (string assertion)
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]

_SKIP_ON_WINDOWS = pytest.mark.skipif(
    sys.platform == "win32",
    reason="bash install e2e validated in Linux/macOS CI; "
           "Windows Git Bash has tmp_path translation issues under AppData",
)


class TestSessionIdSanitization:
    """Regression: pre-1.1 session_id was unsanitized -> path traversal."""

    def test_path_traversal_session_id_is_rejected(self, run_hook_fn, isolated_cognito_env):
        """A crafted session_id with ../ must NOT write outside sessions/."""
        malicious = "../../config/_operator-config"
        stdout, stderr, rc = run_hook_fn(
            "session-closer.sh",
            {"session_id": malicious},
            isolated_cognito_env,
        )
        # Hook should still exit 0 (graceful degradation).
        assert rc == 0

        # No file should have been created matching the malicious name
        # under sessions/ OR outside it.
        sessions_dir = isolated_cognito_env / "sessions"
        operator_cfg = isolated_cognito_env / "config" / "_operator-config.json"

        # The config file must still be a JSON object, not overwritten with
        # a session record.
        import json
        with open(operator_cfg) as f:
            cfg = json.load(f)
        assert "profile" in cfg, "session-closer overwrote _operator-config.json"

        # The session filename should be the fallback timestamp, not the
        # crafted traversal string.
        matches = list(sessions_dir.glob("*.json"))
        for m in matches:
            assert ".." not in m.name
            assert "/" not in m.name
            assert "\\" not in m.name

    def test_invalid_chars_in_session_id_fallback(self, run_hook_fn, isolated_cognito_env):
        for bad in ["foo bar", "foo;rm -rf /", "foo/bar", "foo\x00", "a" * 200]:
            stdout, stderr, rc = run_hook_fn(
                "session-closer.sh",
                {"session_id": bad},
                isolated_cognito_env,
            )
            assert rc == 0, f"hook crashed on {bad!r}"

        # Only safe, regex-matching filenames exist under sessions/
        import re
        safe_re = re.compile(r"^[A-Za-z0-9_.-]{1,64}\.json$")
        for path in (isolated_cognito_env / "sessions").glob("*.json"):
            assert safe_re.match(path.name), f"Unsafe session filename survived: {path.name}"

    def test_clean_session_id_still_works(self, run_hook_fn, isolated_cognito_env):
        stdout, stderr, rc = run_hook_fn(
            "session-closer.sh",
            {"session_id": "integration_test_001"},
            isolated_cognito_env,
        )
        assert rc == 0
        assert (isolated_cognito_env / "sessions" / "integration_test_001.json").exists()


@_SKIP_ON_WINDOWS
class TestInstallProfileWhitelist:
    """Regression: pre-1.1 install.sh did `case` but did not exit on unknown profile."""

    def test_unknown_profile_rejected(self, tmp_path):
        target = (tmp_path / "cognito-bad").as_posix()
        result = subprocess.run(
            ["bash", "scripts/install.sh",
             "--profile=evilprofile",
             f"--target={target}",
             "--skip-settings"],
            capture_output=True, text=True, cwd=str(REPO), timeout=30,
        )
        assert result.returncode != 0, (
            "install.sh accepted unknown profile. Output:\n"
            + result.stdout + result.stderr
        )
        combined = (result.stdout + result.stderr).lower()
        for expected in ("operator", "alumno", "public", "client"):
            assert expected in combined

    def test_missing_profile_rejected(self, tmp_path):
        target = (tmp_path / "cognito-bad").as_posix()
        result = subprocess.run(
            ["bash", "scripts/install.sh",
             f"--target={target}",
             "--skip-settings"],
            capture_output=True, text=True, cwd=str(REPO), timeout=30,
        )
        assert result.returncode != 0


class TestInstallHeredocQuoting:
    """Regression: pre-1.1 <<PYEOF let bash expand $PROFILE into Python source.

    The whitelist closes the vector end-to-end, but we also verify that the
    heredoc delimiter is quoted in the source file so a future edit that
    removes the whitelist cannot re-introduce the vuln silently.
    """

    def test_heredoc_uses_quoted_delimiter(self):
        src = (REPO / "scripts" / "install.sh").read_text(encoding="utf-8")
        # All multi-line python heredocs must start with <<'PYEOF' not <<PYEOF.
        # Tolerates extra whitespace.
        import re
        unquoted = re.findall(r"<<\s*PYEOF\b", src)
        assert not unquoted, (
            f"install.sh still contains unquoted <<PYEOF delimiter "
            f"({len(unquoted)} occurrence(s)). Must be <<'PYEOF' to close "
            f"shell-injection vector."
        )


class TestDashboardServeBindsLoopback:
    """Regression: dashboard used to expose api/ dir + bind 0.0.0.0."""

    def test_serve_binds_127_0_0_1(self):
        src = (REPO / "dashboard" / "serve.sh").read_text(encoding="utf-8")
        assert 'BIND_ADDR="127.0.0.1"' in src, (
            "serve.sh must default to 127.0.0.1 to avoid LAN exposure."
        )

    def test_serve_allowlist_restricts_served_files(self):
        src = (REPO / "dashboard" / "serve.sh").read_text(encoding="utf-8")
        # Must contain the static allowlist, not serve the whole dir.
        assert "ALLOWED" in src
        assert "index.html" in src
        assert "app.js" in src
        assert "data.json" in src

        # Extract the ALLOWED set literal and prove it does not list api paths.
        import re
        m = re.search(r"ALLOWED\s*=\s*\{([^}]+)\}", src)
        assert m, "ALLOWED set literal not found"
        allowed_block = m.group(1)
        assert "/api/" not in allowed_block, (
            "ALLOWED set must not expose paths under /api/. Got:\n" + allowed_block
        )
        assert "build_data.py" not in allowed_block
        assert "seed_demo.py" not in allowed_block


class TestDashboardXssEscaping:
    """Regression: app.js used innerHTML with unsanitized data.json values."""

    def test_esc_helper_defined(self):
        src = (REPO / "dashboard" / "app.js").read_text(encoding="utf-8")
        assert "function esc(" in src, "app.js must define esc() for HTML escaping"
        assert "textContent" in src, "esc() must use textContent to escape"
