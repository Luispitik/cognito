"""test_effort_hint.py — Regression tests for v2.1 effort hint.

Covers:
- Every mode in _modes.json declares `recommendedEffort` ∈ allowed set.
- mode_injector emits an effort block with the correct level per mode.
- Operator override (phase-state.overrideEffort) wins over mode recommendation.
- Determinism fallback used when a mode lacks `recommendedEffort`.
- Anti-regression: no mode's SKILL.md injects deprecated Opus 4.7 params
  (`budget_tokens`, `top_p`, `top_k`, prefill) as executable instructions.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from hooks.python import mode_injector  # noqa: E402


ALLOWED = {"low", "medium", "high", "max"}


# --------------------------------------------------------------------------- #
# Fixture — copy of the repo with fresh state
# --------------------------------------------------------------------------- #
@pytest.fixture
def iso(tmp_path, monkeypatch):
    dest = tmp_path / "cognito"
    shutil.copytree(
        REPO,
        dest,
        ignore=shutil.ignore_patterns(
            "__pycache__", ".pytest_cache", "tests", ".git", "node_modules",
            "logs", "sessions", "runtime",
        ),
    )
    default = dest / "config" / "_phase-state.default.json"
    state = dest / "config" / "_phase-state.json"
    if default.is_file():
        shutil.copy(default, state)
    monkeypatch.setenv("COGNITO_DIR", str(dest))
    monkeypatch.setenv("COGNITO_DIR_RESOLVED", str(dest))
    return dest


def _enable_modes(cognito_dir: Path, modes: list[str]):
    cfg_path = cognito_dir / "config" / "_operator-config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.setdefault("modes", {})["enabled"] = modes
    cfg["modes"]["disabled"] = []
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _set_state(cognito_dir: Path, **fields):
    state_path = cognito_dir / "config" / "_phase-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update(fields)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _run_injector(cognito_dir: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["COGNITO_DIR"] = str(cognito_dir)
    env["COGNITO_DIR_RESOLVED"] = str(cognito_dir)
    env["INPUT_JSON"] = "{}"
    r = subprocess.run(
        [sys.executable, str(REPO / "hooks" / "python" / "mode_injector.py")],
        env=env, capture_output=True, text=True, timeout=15,
    )
    return r.returncode, r.stdout


# --------------------------------------------------------------------------- #
# Config integrity
# --------------------------------------------------------------------------- #
class TestModesConfig:
    def test_every_mode_has_recommended_effort(self):
        modes = json.loads((REPO / "config" / "_modes.json").read_text(encoding="utf-8"))
        missing = [m for m, md in modes["modes"].items() if "recommendedEffort" not in md]
        assert not missing, f"modes missing recommendedEffort: {missing}"

    def test_every_recommended_effort_in_allowed_set(self):
        modes = json.loads((REPO / "config" / "_modes.json").read_text(encoding="utf-8"))
        bad = {m: md["recommendedEffort"]
               for m, md in modes["modes"].items()
               if md.get("recommendedEffort") not in ALLOWED}
        assert not bad, f"modes with invalid recommendedEffort: {bad}"

    def test_verificador_and_auditor_are_max(self):
        """High-stakes modes should default to max — fact-check + lessons-learned."""
        modes = json.loads((REPO / "config" / "_modes.json").read_text(encoding="utf-8"))
        assert modes["modes"]["verificador"]["recommendedEffort"] == "max"
        assert modes["modes"]["auditor"]["recommendedEffort"] == "max"

    def test_phase_state_default_has_override_effort_field(self):
        state = json.loads((REPO / "config" / "_phase-state.default.json").read_text(encoding="utf-8"))
        assert "overrideEffort" in state
        assert state["overrideEffort"] is None


# --------------------------------------------------------------------------- #
# Mode injector behavior
# --------------------------------------------------------------------------- #
class TestInjectorEffortHint:
    def test_emits_effort_block_for_single_mode(self, iso):
        _enable_modes(iso, ["divergente"])
        _set_state(iso, current="discovery", overrideModes=[], overrideEffort=None)
        rc, out = _run_injector(iso)
        assert rc == 0
        payload = json.loads(out)
        msg = payload["systemMessage"]
        assert "effort recommendation" in msg
        # divergente has recommendedEffort=high
        assert "`high`" in msg

    def test_picks_highest_effort_when_multiple_active(self, iso):
        # divergente=high, auditor=max. Max wins.
        _enable_modes(iso, ["divergente", "auditor"])
        _set_state(iso, current="review", overrideModes=["divergente"], overrideEffort=None)
        rc, out = _run_injector(iso)
        assert rc == 0
        msg = json.loads(out)["systemMessage"]
        assert "`max`" in msg
        assert "auditor→max" in msg
        assert "divergente→high" in msg

    def test_override_wins_over_recommended(self, iso):
        _enable_modes(iso, ["divergente"])
        _set_state(iso, current="discovery", overrideModes=[], overrideEffort="low")
        rc, out = _run_injector(iso)
        assert rc == 0
        msg = json.loads(out)["systemMessage"]
        assert "`low`" in msg
        assert "forzado vía `/cognition-effort`" in msg

    def test_invalid_override_falls_back_to_recommended(self, iso):
        _enable_modes(iso, ["divergente"])
        _set_state(iso, current="discovery", overrideModes=[], overrideEffort="bogus")
        rc, out = _run_injector(iso)
        assert rc == 0
        msg = json.loads(out)["systemMessage"]
        # Should NOT say "forzado" — fell back to mode recommendation
        assert "forzado" not in msg
        assert "`high`" in msg  # divergente default

    def test_no_hint_when_no_modes_active(self, iso, monkeypatch):
        """If no modes are enabled, mode_injector exits early with no output."""
        _enable_modes(iso, [])
        _set_state(iso, current="discovery", overrideModes=[], overrideEffort=None)
        rc, out = _run_injector(iso)
        assert rc == 0
        assert out.strip() == ""

    def test_effort_block_appended_after_mode_content(self, iso):
        _enable_modes(iso, ["ejecutor"])
        _set_state(iso, current="execution", overrideModes=[], overrideEffort=None)
        rc, out = _run_injector(iso)
        assert rc == 0
        msg = json.loads(out)["systemMessage"]
        idx_mode = msg.find("## Modo activo: ejecutor")
        idx_effort = msg.find("## Cognito · effort recommendation")
        assert idx_mode != -1 and idx_effort != -1
        assert idx_effort > idx_mode, "effort block must come AFTER mode content"


# --------------------------------------------------------------------------- #
# Budget increase
# --------------------------------------------------------------------------- #
class TestBudgetV21:
    def test_max_total_chars_raised_to_48k(self):
        assert mode_injector.MAX_TOTAL_CHARS == 48_000, (
            "v2.1 triples the injection budget to 48k chars "
            "(~12k tokens, crosses Opus 4.7's 4096-token cache floor)."
        )

    def test_divergente_fits_without_truncation(self, iso):
        """With the new 48k budget, divergente's full 6.5k SKILL.md should land intact."""
        _enable_modes(iso, ["divergente"])
        _set_state(iso, current="discovery", overrideModes=[], overrideEffort=None)
        rc, out = _run_injector(iso)
        assert rc == 0
        msg = json.loads(out)["systemMessage"]
        # [truncated] marker would appear if we had cut the skill mid-sentence
        assert "[truncated]" not in msg, "divergente should fit in the v2.1 budget"


# --------------------------------------------------------------------------- #
# Anti-regression: deprecated Opus 4.7 params in SKILL.md
# --------------------------------------------------------------------------- #
class TestNoDeprecated47Params:
    """Opus 4.7 removes `budget_tokens`, `temperature`, `top_p`, `top_k` and
    rejects prefills (400). Cognito does NOT call the API — but if one of the
    SKILL.md files ever tells Claude to emit such a param, a downstream
    harness following the instruction could regress. Scan for literal usage.
    """

    DEPRECATED_RE = re.compile(
        r"\b(budget_tokens|top_p|top_k)\s*[:=]",
    )

    @pytest.mark.parametrize("mode_file", list((REPO / "modes").glob("*/SKILL.md")))
    def test_mode_skill_does_not_prescribe_deprecated_params(self, mode_file):
        src = mode_file.read_text(encoding="utf-8")
        matches = self.DEPRECATED_RE.findall(src)
        assert not matches, (
            f"{mode_file.relative_to(REPO)} contains deprecated Opus 4.7 "
            f"params: {matches}"
        )

    def test_mode_injector_itself_does_not_mention_deprecated_params_as_instructions(self):
        """The injector code may DOCUMENT that params are removed (in comments)
        but must never emit them in the systemMessage."""
        src = (REPO / "hooks" / "python" / "mode_injector.py").read_text(encoding="utf-8")
        # Strip comments and docstring before scanning
        # Rough: drop lines starting with '#' or inside triple-quoted strings
        no_comments = re.sub(r'"""[\s\S]*?"""', "", src)
        no_comments = re.sub(r"^\s*#.*$", "", no_comments, flags=re.MULTILINE)
        # Remove string literals containing mere mentions
        bad = re.findall(r"\"[^\"]*budget_tokens[^\"]*\"", no_comments)
        assert not bad, f"budget_tokens appears as executable string: {bad}"
