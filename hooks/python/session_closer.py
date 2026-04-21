"""session-closer hook — Python entry point (v1.2).

Ported from `hooks/session-closer.sh` heredoc. Runs on Stop. Partitions the
per-hook log files by session_id, counts only this session's lines, archives
them to `logs/archive/<session_id>.log` and atomically rewrites the live logs
so parallel sessions stay intact. The session summary lands in
`sessions/<session_id>.json` after a realpath + prefix check that blocks
path-traversal session_ids.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent))
    import _common  # type: ignore[no-redef]
else:
    from . import _common


def _partition_and_count(
    log_file: Path,
    archive_file: Path,
    session_id: str,
    substring: str,
    log,
) -> int:
    """Count matches of `substring` in log lines tagged with this session_id or
    [unknown], archive them, and rewrite the live log without those lines.
    """
    if not log_file.is_file():
        return 0
    tag_mine = f"[{session_id}]"
    tag_unknown = "[unknown]"

    try:
        lines = log_file.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return 0

    mine = [ln for ln in lines if tag_mine in ln or tag_unknown in ln]
    others = [ln for ln in lines if not (tag_mine in ln or tag_unknown in ln)]
    count = sum(1 for ln in mine if substring in ln)

    try:
        if mine:
            archive_file.parent.mkdir(parents=True, exist_ok=True)
            with open(archive_file, "a", encoding="utf-8") as f:
                f.write(f"# --- from {log_file.name} ---\n")
                f.writelines(mine)
        tmp = log_file.with_suffix(log_file.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(others)
        os.replace(tmp, log_file)
    except OSError as e:
        log(f"No se pudo rotar {log_file}: {e}")

    return count


def main() -> int:
    cognito_dir = _common.resolve_cognito_dir()
    _common.ensure_dirs(cognito_dir, "logs", "sessions", "logs/archive")

    raw = _common.read_stdin_capped()
    data = _common.parse_input_json(raw)

    # Fallback session_id when the harness doesn't provide one at close time.
    now = datetime.now(timezone.utc)
    fallback = f"session-{now.strftime('%Y%m%d-%H%M%S')}"
    session_id = _common.extract_session_id(data, fallback=fallback)

    log = _common.make_logger(cognito_dir, "session-closer.log", session_id)

    raw_sid = data.get("session_id") or data.get("sessionId")
    if raw_sid and session_id == fallback:
        log(f"session_id invalido (descartado): {raw_sid!r}")

    state_file = cognito_dir / "config" / "_phase-state.json"
    logs_dir = cognito_dir / "logs"
    sessions_dir = cognito_dir / "sessions"

    state = _common.load_json(state_file)
    current_phase = "unknown"
    if isinstance(state, dict):
        current_phase = state.get("current", "unknown")

    archive_file = logs_dir / "archive" / f"{session_id}.log"

    gates = _partition_and_count(
        logs_dir / "gate-validator.log", archive_file, session_id, "Violaciones para", log
    )
    injections = _partition_and_count(
        logs_dir / "mode-injector.log", archive_file, session_id, "Modos activos", log
    )
    detections = _partition_and_count(
        logs_dir / "phase-detector.log", archive_file, session_id, "Detectado:", log
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "sessionId": session_id,
        "closedAt": timestamp,
        "phaseAtClose": current_phase,
        "metrics": {
            "gatesTriggered": gates,
            "modeInjections": injections,
            "phaseDetections": detections,
        },
    }

    session_file = sessions_dir / f"{session_id}.json"
    try:
        sessions_real = Path(os.path.realpath(sessions_dir))
        session_real = Path(os.path.realpath(session_file))
        # Defense in depth: refuse any path that escapes sessions_dir, even if
        # session_id passed the regex. Covers exotic cases (symlinks mid-path).
        if not str(session_real).startswith(str(sessions_real) + os.sep) and session_real != sessions_real:
            log(f"Path escape detectado: {session_real} fuera de {sessions_real}")
            return 0
        with open(session_real, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
    except OSError as e:
        log(f"Error escribiendo session file: {e}")
        return 0

    log(
        f"Sesion {session_id} cerrada. Fase: {current_phase}. "
        f"Gates: {gates}. Injections: {injections}. Detections: {detections}."
    )

    if isinstance(state, dict):
        state["sessionId"] = session_id
        state["lastUpdatedBy"] = "session-closer"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError as e:
            log(f"Error actualizando state: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
