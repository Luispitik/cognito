"""gate-validator hook — Python entry point (v1.2).

Ported from `hooks/gate-validator.sh` heredoc. Runs on PreToolUse matching
Write and Edit. Blocks (exit 1) or warns (exit 0 + systemMessage) depending
on the rule action. Enabled/disabled gates come from operator-config;
rule definitions from passive-triggers.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent))
    import _common  # type: ignore[no-redef]
else:
    from . import _common


def main() -> int:
    cognito_dir = _common.resolve_cognito_dir()
    _common.ensure_dirs(cognito_dir, "logs")

    raw = _common.read_stdin_capped()
    data = _common.parse_input_json(raw)
    session_id = _common.extract_session_id(data)
    log = _common.make_logger(cognito_dir, "gate-validator.log", session_id)

    tool_input = data.get("tool_input") or data.get("input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", tool_input.get("new_string", "")) or ""
    if not file_path:
        log("Sin file_path. Salgo.")
        return 0

    cfg = cognito_dir / "config"
    triggers = _common.load_json(cfg / "_passive-triggers.json")
    operator = _common.load_json(cfg / "_operator-config.json")
    if not isinstance(triggers, dict) or not isinstance(operator, dict):
        log("Config ausente o ilegible. Salgo sin validar.")
        return 0

    enabled = set((operator.get("gates") or {}).get("enabled", []))
    disabled = set((operator.get("gates") or {}).get("disabled", []))

    violations: list[dict] = []
    file_basename = os.path.basename(file_path)

    for rule in (triggers.get("gates") or {}).get("rules", []):
        if not isinstance(rule, dict):
            continue
        gate_id = rule.get("id", "")
        if gate_id not in enabled or gate_id in disabled:
            continue

        files_affected = rule.get("filesAffected") or ["*"]
        if not isinstance(files_affected, list):
            continue
        matches_file = any(
            fnmatch.fnmatch(file_path, pat) or fnmatch.fnmatch(file_basename, pat)
            for pat in files_affected
            if isinstance(pat, str)
        )
        if not matches_file:
            continue

        pattern = rule.get("pattern", "")
        if not isinstance(pattern, str) or not pattern:
            continue
        try:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append({
                    "id": gate_id,
                    "action": rule.get("action", "warn"),
                    "message": rule.get("message", ""),
                    "override": rule.get("override"),
                })
        except re.error:
            continue

    if not violations:
        log(f"Sin violaciones para {file_path}")
        return 0

    ids = [v["id"] for v in violations]
    log(f"Violaciones para {file_path}: {ids}")

    has_block = any(v.get("action") == "block" for v in violations)

    parts = []
    for v in violations:
        emoji = "[BLOCK]" if v["action"] == "block" else "[WARN]"
        line = f"{emoji} Gate [{v['id']}]: {v['message']}"
        if v.get("override"):
            line += f" Override: {v['override']}"
        parts.append(line)
    message = "\n".join(parts)

    if has_block:
        print(message, file=sys.stderr)
        return 1
    print(json.dumps({"systemMessage": message}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
