"""mode-injector hook — Python entry point (v1.2).

Ported from `hooks/mode-injector.sh` heredoc. Runs once per turn on
UserPromptSubmit (since v1.1). Injects the active-mode SKILL.md content as
systemMessage, with smart per-mode and total budgets that cut at section
boundaries instead of mid-sentence. Also surfaces Sinapsis instincts when the
bridge is available and an instinct-consuming mode is active.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent))
    import _common  # type: ignore[no-redef]
else:
    from . import _common

# Content budgets — tuned for Claude Opus 4.7 (1M context). v1.1 removed the
# crude 60-line truncate; v2.1 triples the total budget to 48k chars (~12k
# tokens, ~1.2 % of the 1M window) so the full Divergente SKILL.md fits and the
# bundle crosses the Opus 4.7 4096-token cache minimum (prior 16k chars ≈ 4k
# tokens sat exactly at the cache-write threshold).
MAX_TOTAL_CHARS = 48_000
MAX_PER_MODE = 8_000
MODES_CONSUMING_INSTINCTS = {"ejecutor", "verificador", "auditor"}

# v2.1: map of mode.determinism → recommended effort level for Claude Opus 4.7.
# Used only when the mode does NOT declare its own `recommendedEffort` field
# and when phase-state does not carry an explicit `overrideEffort`.
_DETERMINISM_TO_EFFORT = {
    "low": "medium",
    "medium": "high",
    "high": "high",
}
_ALLOWED_EFFORTS = {"low", "medium", "high", "max"}


def _smart_truncate(text: str, limit: int) -> str:
    """Truncate at section boundaries when possible, else append [truncated]."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    for marker in ("\n---\n", "\n## ", "\n# "):
        idx = head.rfind(marker)
        if idx > limit // 2:
            return head[:idx] + "\n\n[truncated]"
    return head + "\n\n[truncated]"


def _render_sinapsis(cognito_dir: Path, operator_cfg: dict, active: list[str], log) -> str:
    """Render Sinapsis instincts block. Empty string if bridge unavailable."""
    if not any(m in MODES_CONSUMING_INSTINCTS for m in active):
        return ""
    bridge_script = cognito_dir / "integrations" / "sinapsis_bridge.py"
    if not bridge_script.is_file():
        return ""
    try:
        import importlib.util

        sys.path.insert(0, str(cognito_dir / "integrations"))
        spec = importlib.util.spec_from_file_location("sinapsis_bridge", bridge_script)
        if spec is None or spec.loader is None:
            return ""
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        bridge = mod.SinapsisBridge.detect(operator_config=operator_cfg)
        if not bridge.available:
            return ""
        injection = bridge.render_injection(limit=8)
        if injection:
            log(f"Sinapsis bridge activo (v{bridge.version or '?'}): instincts inyectados")
        return injection or ""
    except Exception as e:  # noqa: BLE001
        log(f"Bridge Sinapsis no disponible (degradando a standalone): {e}")
        return ""


def main() -> int:
    cognito_dir = _common.resolve_cognito_dir()
    _common.ensure_dirs(cognito_dir, "logs")

    raw = _common.read_stdin_capped()
    data = _common.parse_input_json(raw)
    session_id = _common.extract_session_id(data)
    log = _common.make_logger(cognito_dir, "mode-injector.log", session_id)

    cfg = cognito_dir / "config"
    state = _common.load_json(cfg / "_phase-state.json")
    modes = _common.load_json(cfg / "_modes.json")
    phases = _common.load_json(cfg / "_phases.json")
    operator = _common.load_json(cfg / "_operator-config.json")

    for name, obj in [("state", state), ("modes", modes), ("phases", phases), ("operator", operator)]:
        if not isinstance(obj, dict):
            log(f"Config '{name}' ausente o invalida. Salgo.")
            return 0

    current_phase = state.get("current", "discovery")  # type: ignore[union-attr]
    override_modes = state.get("overrideModes", []) if isinstance(state.get("overrideModes"), list) else []  # type: ignore[union-attr]
    enabled = set((operator.get("modes") or {}).get("enabled", []))  # type: ignore[union-attr]
    disabled = set((operator.get("modes") or {}).get("disabled", []))  # type: ignore[union-attr]

    phase_def = (phases.get("phases") or {}).get(current_phase, {})  # type: ignore[union-attr]
    default_modes = phase_def.get("defaultModes") or []

    active: list[str] = []
    for m in list(default_modes) + list(override_modes):
        if m in enabled and m not in disabled and m not in active:
            active.append(m)

    # v2.0 collapse: rewrite the active list through aliases when the operator
    # opted in. Keeps the API stable (users still type /estratega) while the
    # underlying skill injected is the collapsed one with a preset annotation.
    collapse_on = bool(
        ((operator.get("modes") or {}).get("collapseV2"))  # type: ignore[union-attr]
    )
    collapse_table = (modes.get("collapseV2") or {}).get("aliases", {}) if isinstance(modes, dict) else {}  # type: ignore[union-attr]
    collapse_presets: dict[str, str] = {}
    if collapse_on and isinstance(collapse_table, dict):
        rewritten: list[str] = []
        for m in active:
            alias = collapse_table.get(m)
            if isinstance(alias, dict) and alias.get("collapsesInto"):
                target = alias["collapsesInto"]
                preset = alias.get("preset", "")
                if target not in rewritten:
                    rewritten.append(target)
                if preset:
                    collapse_presets.setdefault(target, preset)
                log(f"collapseV2: {m} -> {target}" + (f" (preset={preset})" if preset else ""))
            elif m not in rewritten:
                rewritten.append(m)
        active = rewritten

    if not active:
        log("Sin modos activos.")
        return 0

    log(f"Modos activos: {','.join(active)} (fase: {current_phase})")

    parts: list[str] = []
    running_total = 0
    modes_defs = modes.get("modes") or {}  # type: ignore[union-attr]
    for mode in active:
        mode_def = modes_defs.get(mode, {}) if isinstance(modes_defs, dict) else {}
        skill_rel = mode_def.get("skillPath", "") if isinstance(mode_def, dict) else ""
        if not skill_rel:
            continue
        skill_full = cognito_dir / skill_rel
        if not skill_full.is_file():
            log(f"SKILL.md de '{mode}' no encontrado en {skill_full}")
            continue
        try:
            content = skill_full.read_text(encoding="utf-8")
        except OSError:
            log(f"No se pudo leer {skill_full}")
            continue

        chunk = _smart_truncate(content, MAX_PER_MODE)
        preset = collapse_presets.get(mode)
        header = (
            f"\n\n---\n## Modo activo: {mode}"
            + (f" (preset: {preset})" if preset else "")
            + "\n\n"
        )
        projected = running_total + len(header) + len(chunk)
        if projected > MAX_TOTAL_CHARS:
            remaining = MAX_TOTAL_CHARS - running_total - len(header)
            if remaining < 300:
                log(f"Budget agotado antes de '{mode}', omitido")
                break
            chunk = _smart_truncate(chunk, remaining)
        parts.append(header + chunk)
        running_total += len(header) + len(chunk)

    injection = _render_sinapsis(cognito_dir, operator, active, log)  # type: ignore[arg-type]
    if injection:
        parts.append(injection)

    # v2.1: append an effort hint so the consumer (Claude or the operator's
    # harness) can translate Cognito's determinism signal into the right
    # `output_config.effort` level for Opus 4.7. Precedence:
    #   1. state.overrideEffort (explicit operator override via /cognition-effort)
    #   2. mode.recommendedEffort (per-mode frontmatter)
    #   3. determinism → effort fallback mapping
    effort_hint = _resolve_effort_hint(state, active, modes_defs, log)
    if effort_hint:
        parts.append(_render_effort_block(effort_hint, active, state))

    if parts:
        print(json.dumps({"systemMessage": "".join(parts)}))
    return 0


def _resolve_effort_hint(
    state: dict,
    active: list[str],
    modes_defs: dict,
    log,
) -> dict | None:
    """Return {'level': str, 'source': str, 'per_mode': dict[str,str]} or None."""
    # 1. explicit override
    override = state.get("overrideEffort") if isinstance(state, dict) else None
    if isinstance(override, str) and override.lower() in _ALLOWED_EFFORTS:
        log(f"effort: override={override.lower()}")
        return {"level": override.lower(), "source": "override", "per_mode": {}}

    # 2+3. per-mode recommended effort (with determinism fallback)
    per_mode: dict[str, str] = {}
    ranked: list[tuple[int, str, str]] = []  # (rank, mode, effort)
    rank_of = {"low": 1, "medium": 2, "high": 3, "max": 4}
    for mode in active:
        md = modes_defs.get(mode, {}) if isinstance(modes_defs, dict) else {}
        if not isinstance(md, dict):
            continue
        recommended = md.get("recommendedEffort")
        if isinstance(recommended, str) and recommended.lower() in _ALLOWED_EFFORTS:
            effort = recommended.lower()
            source = "mode.recommendedEffort"
        else:
            det = md.get("determinism", "medium")
            effort = _DETERMINISM_TO_EFFORT.get(det, "high")
            source = f"determinism={det}"
        per_mode[mode] = effort
        ranked.append((rank_of.get(effort, 3), mode, effort))

    if not per_mode:
        return None

    # Pick the highest-effort mode as the session-level suggestion: a single
    # `max` in the active set wins. This matches intuition (if Auditor is on,
    # you want thorough thinking).
    ranked.sort(reverse=True)
    top_effort = ranked[0][2]
    log(f"effort: per_mode={per_mode} → recommend={top_effort}")
    return {"level": top_effort, "source": "mode.recommendedEffort", "per_mode": per_mode}


def _render_effort_block(hint: dict, active: list[str], state: dict) -> str:
    """Render the effort hint appended to the systemMessage."""
    level = hint["level"]
    source = hint.get("source", "")
    per_mode = hint.get("per_mode") or {}

    lines = [
        "\n\n---",
        "## Cognito · effort recommendation (Opus 4.7+)",
        "",
    ]
    if source == "override":
        lines.append(
            f"Effort forzado vía `/cognition-effort`: **`{level}`** "
            f"(sobrescribe la sugerencia por modo)."
        )
    else:
        modes_str = ", ".join(f"{m}→{e}" for m, e in per_mode.items()) or "n/a"
        lines.append(
            f"Effort sugerido para esta sesión: **`{level}`** "
            f"(el más alto entre modos activos: {modes_str})."
        )
    lines.append("")
    lines.append(
        "Si el harness expone `output_config.effort`, úsalo tal cual. "
        "Si estás leyendo esto como usuario: puedes ignorarlo — es una pista de "
        "Cognito sobre cuánto debería pensar el modelo antes de responder."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
