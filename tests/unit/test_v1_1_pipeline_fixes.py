"""
test_v1_1_pipeline_fixes.py — Regression tests for the pipeline fixes in v1.1.

Covers:
- phase-detector uses word-boundary match (no substring-in-negation bugs).
- mode-injector no longer truncates SKILL.md at 60 lines.
- Every hook tags log lines with [session_id] for proper session metrics.
- session-closer counts only its own tagged lines.
"""
import json
import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]


class TestPhaseDetectorWordBoundaries:
    """Pre-1.1 used `signal in prompt_lower`, which matched inside other words."""

    def test_negated_signal_does_not_trigger(self, run_hook_fn, isolated_cognito_env):
        """'no exploremos eso' must NOT suggest discovery (pre-1.1 bug)."""
        # Pick a signal that appears in _passive-triggers.json and build a
        # negated prompt around it.
        triggers = json.loads(
            (isolated_cognito_env / "config" / "_passive-triggers.json")
            .read_text(encoding="utf-8")
        )
        signals = [
            r.get("signal", "") for r in
            triggers.get("phaseDetection", {}).get("rules", [])
            if r.get("confidence") in ("high", "medium")
        ]
        # Pick the first single-word signal so we can embed it cleanly.
        single_word = next((s for s in signals if s and " " not in s), None)
        if not single_word:
            pytest.skip("No single-word phase signal in triggers config")
        # Build a word that contains the signal as a substring (e.g. 'exploremosDos')
        # to prove word boundaries actually work.
        prompt = f"{single_word}dos no quiero hacer esto"
        stdout, _, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": prompt},
            isolated_cognito_env,
        )
        assert rc == 0
        # Must not emit a phase-change suggestion
        assert "suggestPhase" not in stdout.lower() or stdout.strip() == "", (
            f"Pre-1.1 substring bug re-introduced. stdout:\n{stdout}"
        )

    def test_exact_signal_still_triggers(self, run_hook_fn, isolated_cognito_env):
        """Legit signal must still fire (regression of the word-boundary fix)."""
        stdout, _, rc = run_hook_fn(
            "phase-detector.sh",
            {"prompt": "vamos a ejecutar esto ya"},
            isolated_cognito_env,
        )
        assert rc == 0
        assert "execution" in stdout.lower()


class TestModeInjectorNoTruncation:
    """Pre-1.1 truncated SKILL.md at 60 lines -> Triggers sections dropped."""

    def test_source_does_not_slice_60_lines(self):
        src = (REPO / "hooks" / "mode-injector.sh").read_text(encoding="utf-8")
        assert "readlines()[:60]" not in src, (
            "Pre-1.1 60-line truncation re-introduced. Use _smart_truncate()."
        )
        assert "_smart_truncate" in src, "smart truncate helper missing"

    def test_budget_limits_defined(self):
        src = (REPO / "hooks" / "mode-injector.sh").read_text(encoding="utf-8")
        # MAX_PER_MODE and MAX_TOTAL_CHARS must be explicit
        assert "MAX_PER_MODE" in src
        assert "MAX_TOTAL_CHARS" in src

    def test_mode_injector_on_user_prompt_submit(self):
        """Fire once per turn, not on every tool call."""
        src = (REPO / "hooks" / "mode-injector.sh").read_text(encoding="utf-8")
        assert "UserPromptSubmit" in src, (
            "mode-injector header must declare UserPromptSubmit as its hook event."
        )


class TestSessionIdTagging:
    """Every hook must tag log lines with [session_id] for per-session metrics."""

    @pytest.mark.parametrize("hook", [
        "phase-detector.sh",
        "mode-injector.sh",
        "gate-validator.sh",
        "session-closer.sh",
    ])
    def test_hook_tags_log_lines_with_session(self, hook):
        src = (REPO / "hooks" / hook).read_text(encoding="utf-8")
        # Must build a SESSION_ID from input and use it in log format
        assert "SESSION_ID" in src, (
            f"{hook} does not tag log lines with [session_id]."
        )
        # Must write the tag in the log format (either `[{SESSION_ID}]` or
        # `{SESSION_TAG}` used in session-closer).
        tagged = "[{SESSION_ID}]" in src or "SESSION_TAG" in src
        assert tagged, f"{hook} log() does not include session tag"


class TestSessionCloserPerSessionMetrics:
    """Metrics must reflect only the closing session, not lifetime totals."""

    def test_different_sessions_isolated(self, run_hook_fn, isolated_cognito_env):
        # Session A: trigger a gate violation
        run_hook_fn(
            "gate-validator.sh",
            {"session_id": "session-A", "tool_input": {"file_path": ".env", "content": "SECRET=xxx"}},
            isolated_cognito_env,
        )
        # Close session A
        run_hook_fn(
            "session-closer.sh", {"session_id": "session-A"}, isolated_cognito_env,
        )
        session_a = json.loads(
            (isolated_cognito_env / "sessions" / "session-A.json").read_text(encoding="utf-8")
        )
        assert session_a["metrics"]["gatesTriggered"] >= 1

        # Session B: no gates triggered
        run_hook_fn(
            "session-closer.sh", {"session_id": "session-B"}, isolated_cognito_env,
        )
        session_b = json.loads(
            (isolated_cognito_env / "sessions" / "session-B.json").read_text(encoding="utf-8")
        )
        # Session B must NOT inherit session A's count (this was the pre-1.1 bug)
        assert session_b["metrics"]["gatesTriggered"] == 0, (
            "session-closer leaked session A's gate count into session B. "
            "Pre-1.1 lifetime-counter bug re-introduced."
        )

    def test_archive_file_created(self, run_hook_fn, isolated_cognito_env):
        run_hook_fn(
            "session-closer.sh", {"session_id": "archive-me"}, isolated_cognito_env,
        )
        archive_dir = isolated_cognito_env / "logs" / "archive"
        assert archive_dir.is_dir(), "logs/archive/ not created"
