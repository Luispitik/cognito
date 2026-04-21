"""phase-detector hook — Python entry point (v1.2).

Ported from the bash heredoc in `hooks/phase-detector.sh`. Semantics are
identical to v1.1.0:
- Word-boundary signal match (no substring false positives — "no exploremos"
  does NOT trigger "exploremos").
- Best-confidence wins (high > medium > low).
- Anchor detection runs after phase detection when no phase change fired.

Never forces a phase change: emits a systemMessage with a suggestion that
Claude surfaces to the user.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Importable both as package and as standalone script.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent))
    import _common  # type: ignore[no-redef]
else:
    from . import _common


_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def _matches_signal(signal: str, haystack: str) -> bool:
    """Word-boundary match. Handles multi-word signals ('vamos a ejecutar')
    via re.escape. Degrades to False on regex errors instead of raising."""
    if not signal:
        return False
    try:
        pattern = r"\b" + re.escape(signal) + r"\b"
        return bool(re.search(pattern, haystack))
    except re.error:
        return False


def _suggest_phase(triggers: dict, prompt_lower: str) -> dict | None:
    """Pick the best (highest-confidence) matching rule, or None."""
    best = None
    best_conf = 0
    for rule in (triggers.get("phaseDetection") or {}).get("rules", []):
        if not isinstance(rule, dict):
            continue
        signal = (rule.get("signal") or "").lower()
        if not _matches_signal(signal, prompt_lower):
            continue
        conf = rule.get("confidence", "low")
        rank = _CONFIDENCE_RANK.get(conf, 0)
        if rank > best_conf:
            best_conf = rank
            best = {
                "signal": rule.get("signal", ""),
                "suggestPhase": rule.get("suggestPhase", ""),
                "confidence": conf,
            }
    return best


def _detect_anchor(triggers: dict, prompt_lower: str, log) -> str | None:
    """Return the matched anchor pattern (human-readable), or None."""
    for rule in (triggers.get("anchorDetection") or {}).get("rules", []):
        if not isinstance(rule, dict):
            continue
        raw_pat = (rule.get("pattern") or "").lower()
        if not raw_pat:
            continue
        # Anchor patterns use [x] as wildcard placeholder.
        regex_src = raw_pat.replace("[x]", ".+")
        try:
            compiled = re.compile(regex_src)
        except re.error as exc:
            log(f"Regex invalido en anchor rule '{rule.get('pattern')}': {exc}")
            continue
        try:
            if compiled.search(prompt_lower):
                return rule.get("pattern", "")
        except Exception as exc:  # noqa: BLE001
            log(f"Error evaluando anchor rule: {exc}")
    return None


def main() -> int:
    cognito_dir = _common.resolve_cognito_dir()
    _common.ensure_dirs(cognito_dir, "logs")

    raw = _common.read_stdin_capped()
    data = _common.parse_input_json(raw)
    session_id = _common.extract_session_id(data)
    log = _common.make_logger(cognito_dir, "phase-detector.log", session_id)

    prompt = data.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        log("Sin prompt. Salgo.")
        return 0

    state = _common.load_json(cognito_dir / "config" / "_phase-state.json")
    triggers = _common.load_json(cognito_dir / "config" / "_passive-triggers.json")
    if not isinstance(triggers, dict):
        log("Triggers file ausente o ilegible. Salgo.")
        return 0

    current_phase = "discovery"
    if isinstance(state, dict):
        current_phase = state.get("current", "discovery")

    prompt_lower = prompt.lower()

    best = _suggest_phase(triggers, prompt_lower)
    if (
        best
        and best["suggestPhase"]
        and best["suggestPhase"] != current_phase
        and best["confidence"] in ("high", "medium")
    ):
        log(f'Detectado: "{best["signal"]}" -> sugerir {best["suggestPhase"]} ({best["confidence"]})')
        msg = (
            f'Cognito detecto senal "{best["signal"]}" que sugiere pasar '
            f'de fase "{current_phase}" a "{best["suggestPhase"]}" '
            f'(confianza: {best["confidence"]}). Si aplica, sugiere al usuario: '
            f'/fase {best["suggestPhase"]}. NO apliques el cambio sin confirmacion.'
        )
        print(json.dumps({"systemMessage": msg}))
        return 0

    anchor = _detect_anchor(triggers, prompt_lower, log)
    if anchor:
        log(f'Ancla detectada: "{anchor}" -> sugerir Divergente')
        msg = (
            f'Cognito detecto posible ancla cognitiva ("{anchor}"). '
            f'Considera activar modo Divergente. Sugerencia: /modo divergente o /divergir.'
        )
        print(json.dumps({"systemMessage": msg}))
        return 0

    log(f"Sin deteccion. Fase actual: {current_phase}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
