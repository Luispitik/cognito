"""Direct unit tests for hooks.python.* modules.

v1.2 extracted the heredocs from `hooks/*.sh` into importable Python modules
under `hooks/python/`. This file exercises them directly (not via subprocess)
so pytest-cov can actually track branch coverage — the subprocess invocation
used by `test_phase_detector.py`, `test_gate_validator.py` etc. never shows
up in the coverage report because the child process doesn't install the
coverage hooks.

Together with the existing subprocess-based tests, we get:
- Functional contract coverage (subprocess, same behavior Claude sees)
- Branch coverage metrics (these tests, imported modules)
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from hooks.python import (  # noqa: E402
    _common,
    gate_validator,
    mode_injector,
    phase_detector,
    session_closer,
)


# --------------------------------------------------------------------------- #
# Fixture: isolated cognito dir whose hooks run against a pristine config.
# --------------------------------------------------------------------------- #
@pytest.fixture
def iso_cognito(tmp_path, monkeypatch):
    root = tmp_path / "cognito"
    shutil.copytree(
        PROJECT_ROOT,
        root,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "tests", ".git", "node_modules"),
    )
    default = root / "config" / "_phase-state.default.json"
    state = root / "config" / "_phase-state.json"
    if default.is_file():
        shutil.copy(default, state)
    monkeypatch.setenv("COGNITO_DIR_RESOLVED", str(root))
    monkeypatch.setenv("COGNITO_DIR", str(root))
    return root


def _run_main(module, stdin_str: str, monkeypatch, capsys) -> tuple[int, str, str]:
    """Invoke module.main() after pushing stdin_str into INPUT_JSON."""
    monkeypatch.setenv("INPUT_JSON", stdin_str)
    rc = module.main()
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


# --------------------------------------------------------------------------- #
# _common
# --------------------------------------------------------------------------- #
class TestCommon:
    def test_extract_session_id_valid(self):
        assert _common.extract_session_id({"session_id": "abc-123"}) == "abc-123"

    def test_extract_session_id_camelcase(self):
        assert _common.extract_session_id({"sessionId": "abc"}) == "abc"

    def test_extract_session_id_rejects_path_traversal(self):
        assert _common.extract_session_id({"session_id": "../etc/passwd"}) == "unknown"

    def test_extract_session_id_rejects_too_long(self):
        assert _common.extract_session_id({"session_id": "a" * 65}) == "unknown"

    def test_extract_session_id_custom_fallback(self):
        assert _common.extract_session_id({}, fallback="FB") == "FB"

    def test_parse_input_json_handles_garbage(self):
        assert _common.parse_input_json("not json at all") == {}

    def test_parse_input_json_rejects_list(self):
        assert _common.parse_input_json("[1,2,3]") == {}

    def test_parse_input_json_accepts_dict(self):
        assert _common.parse_input_json('{"a":1}') == {"a": 1}

    def test_read_stdin_capped_uses_env_override(self, monkeypatch):
        monkeypatch.setenv("INPUT_JSON", "hello")
        assert _common.read_stdin_capped() == "hello"

    def test_read_stdin_capped_respects_limit(self, monkeypatch):
        monkeypatch.setenv("INPUT_JSON", "x" * 100)
        assert _common.read_stdin_capped(limit=50) == "x" * 50

    def test_make_logger_writes_with_session_tag(self, tmp_path):
        log = _common.make_logger(tmp_path, "t.log", "sess-42")
        log("hello")
        content = (tmp_path / "logs" / "t.log").read_text(encoding="utf-8")
        assert "[sess-42]" in content
        assert "hello" in content

    def test_make_logger_never_raises_on_bad_dir(self):
        # Nonexistent parent with unusable permissions should not raise.
        log = _common.make_logger(Path("/definitely/does/not/exist"), "x.log", "sid")
        log("payload")  # must not raise

    def test_load_json_missing_returns_none(self, tmp_path):
        assert _common.load_json(tmp_path / "nope.json") is None

    def test_load_json_invalid_returns_none(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not-json")
        assert _common.load_json(f) is None

    def test_resolve_cognito_dir_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("COGNITO_DIR_RESOLVED", str(tmp_path))
        assert _common.resolve_cognito_dir() == tmp_path


# --------------------------------------------------------------------------- #
# phase_detector
# --------------------------------------------------------------------------- #
class TestPhaseDetectorDirect:
    def test_empty_prompt_exits_clean(self, iso_cognito, monkeypatch, capsys):
        rc, out, _ = _run_main(phase_detector, json.dumps({"prompt": ""}), monkeypatch, capsys)
        assert rc == 0
        assert out == ""

    def test_missing_prompt_exits_clean(self, iso_cognito, monkeypatch, capsys):
        rc, out, _ = _run_main(phase_detector, json.dumps({}), monkeypatch, capsys)
        assert rc == 0
        assert out == ""

    def test_high_confidence_signal_triggers_suggestion(self, iso_cognito, monkeypatch, capsys):
        rc, out, _ = _run_main(
            phase_detector,
            json.dumps({"prompt": "vamos a ejecutar esto ya"}),
            monkeypatch, capsys,
        )
        assert rc == 0
        assert "execution" in out.lower()
        assert "systemMessage" in out

    def test_anchor_pattern_triggers_divergente(self, iso_cognito, monkeypatch, capsys):
        rc, out, _ = _run_main(
            phase_detector,
            json.dumps({"prompt": "ya tengo decidido hacer X"}),
            monkeypatch, capsys,
        )
        assert rc == 0
        assert "divergente" in out.lower() or "ancla" in out.lower()

    def test_word_boundary_rejects_substring_inside_word(self, iso_cognito, monkeypatch, capsys):
        # "ejecutarlo" contains "ejecutar" as substring but should NOT trigger
        # (word boundary: `\bejecutar\b` does not match in `ejecutarlo`).
        rc, out, _ = _run_main(
            phase_detector,
            json.dumps({"prompt": "esto no es ejecutarlotodo"}),
            monkeypatch, capsys,
        )
        assert rc == 0
        assert "execution" not in out.lower() or out.strip() == ""

    def test_signal_already_in_current_phase_no_suggestion(self, iso_cognito, monkeypatch, capsys):
        # Default phase is discovery. A discovery-suggesting signal must NOT
        # emit a change suggestion.
        rc, out, _ = _run_main(
            phase_detector,
            json.dumps({"prompt": "exploremos las alternativas"}),
            monkeypatch, capsys,
        )
        assert rc == 0
        # May emit anchor detection but should not suggest the current phase.
        if "systemMessage" in out:
            # If anything was emitted, it must be an anchor, not a phase suggestion.
            assert "pasar de fase" not in out


# --------------------------------------------------------------------------- #
# gate_validator
# --------------------------------------------------------------------------- #
class TestGateValidatorDirect:
    def test_empty_input_exits_clean(self, iso_cognito, monkeypatch, capsys):
        rc, _, _ = _run_main(gate_validator, "{}", monkeypatch, capsys)
        assert rc == 0

    def test_env_file_blocked(self, iso_cognito, monkeypatch, capsys):
        # no-commit-env is in the default operator gates list.
        rc, _, err = _run_main(
            gate_validator,
            json.dumps({
                "session_id": "t",
                "tool_input": {"file_path": ".env", "content": "SECRET=shh"},
            }),
            monkeypatch, capsys,
        )
        assert rc == 1
        assert "BLOCK" in err or "Gate" in err

    def test_benign_file_passes(self, iso_cognito, monkeypatch, capsys):
        rc, _, _ = _run_main(
            gate_validator,
            json.dumps({
                "session_id": "t",
                "tool_input": {"file_path": "src/foo.ts", "content": "export const x = 1;"},
            }),
            monkeypatch, capsys,
        )
        assert rc == 0

    def test_malformed_pattern_is_tolerated(self, iso_cognito, monkeypatch, capsys):
        # Force a malformed regex into triggers — gate_validator must skip it
        # without raising.
        triggers_file = iso_cognito / "config" / "_passive-triggers.json"
        data = json.loads(triggers_file.read_text(encoding="utf-8"))
        data.setdefault("gates", {}).setdefault("rules", []).append({
            "id": "broken-gate",
            "pattern": "(unclosed",
            "filesAffected": ["*"],
            "action": "warn",
            "message": "should not fire",
        })
        op_file = iso_cognito / "config" / "_operator-config.json"
        op = json.loads(op_file.read_text(encoding="utf-8"))
        op.setdefault("gates", {}).setdefault("enabled", []).append("broken-gate")
        triggers_file.write_text(json.dumps(data), encoding="utf-8")
        op_file.write_text(json.dumps(op), encoding="utf-8")

        rc, _, _ = _run_main(
            gate_validator,
            json.dumps({
                "session_id": "t",
                "tool_input": {"file_path": "src/foo.ts", "content": "anything"},
            }),
            monkeypatch, capsys,
        )
        assert rc == 0


# --------------------------------------------------------------------------- #
# mode_injector
# --------------------------------------------------------------------------- #
class TestModeInjectorDirect:
    def test_smart_truncate_short_text_unchanged(self):
        assert mode_injector._smart_truncate("short", 100) == "short"

    def test_smart_truncate_cuts_at_section_boundary(self):
        text = "intro\n\n## Section 1\nlong" + ("x" * 500) + "\n\n## Section 2\nmore"
        truncated = mode_injector._smart_truncate(text, 80)
        assert len(truncated) <= 120  # smart cut + [truncated] marker
        assert "[truncated]" in truncated

    def test_smart_truncate_fallback_hard_cut(self):
        # No `---`, `##`, or `#` markers — must still cap somewhere.
        text = "x" * 1000
        truncated = mode_injector._smart_truncate(text, 100)
        assert len(truncated) <= 150
        assert "[truncated]" in truncated

    def test_injects_system_message_when_modes_active(self, iso_cognito, monkeypatch, capsys):
        rc, out, _ = _run_main(mode_injector, "{}", monkeypatch, capsys)
        assert rc == 0
        # Default phase is discovery -> divergente + estratega active
        if out.strip():
            payload = json.loads(out)
            assert "systemMessage" in payload


# --------------------------------------------------------------------------- #
# session_closer
# --------------------------------------------------------------------------- #
class TestSessionCloserDirect:
    def test_creates_session_file(self, iso_cognito, monkeypatch, capsys):
        rc, _, _ = _run_main(
            session_closer,
            json.dumps({"session_id": "direct-test-1"}),
            monkeypatch, capsys,
        )
        assert rc == 0
        session_file = iso_cognito / "sessions" / "direct-test-1.json"
        assert session_file.is_file()
        rec = json.loads(session_file.read_text(encoding="utf-8"))
        assert rec["sessionId"] == "direct-test-1"
        assert "metrics" in rec

    def test_invalid_session_id_gets_fallback(self, iso_cognito, monkeypatch, capsys):
        rc, _, _ = _run_main(
            session_closer,
            json.dumps({"session_id": "../escape"}),
            monkeypatch, capsys,
        )
        assert rc == 0
        # No file named "../escape" can exist in sessions/; the fallback is
        # something like session-YYYYMMDD-HHMMSS.
        sessions = list((iso_cognito / "sessions").glob("session-*.json"))
        assert sessions, "fallback session file not created"

    def test_partitions_gate_log_by_session(self, iso_cognito, monkeypatch, capsys):
        # Seed gate log with two lines: one for session A, one unknown.
        logs_dir = iso_cognito / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        gate_log = logs_dir / "gate-validator.log"
        gate_log.write_text(
            "[2026-04-19T10:00:00Z] [session-A] Violaciones para .env: ['x']\n"
            "[2026-04-19T10:01:00Z] [session-B] Violaciones para other: ['y']\n",
            encoding="utf-8",
        )
        rc, _, _ = _run_main(
            session_closer,
            json.dumps({"session_id": "session-A"}),
            monkeypatch, capsys,
        )
        assert rc == 0
        rec = json.loads((iso_cognito / "sessions" / "session-A.json").read_text(encoding="utf-8"))
        assert rec["metrics"]["gatesTriggered"] == 1
        # session-B's line must remain in the live log.
        remaining = gate_log.read_text(encoding="utf-8") if gate_log.is_file() else ""
        assert "session-B" in remaining
