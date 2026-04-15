#!/usr/bin/env python3
"""
Cognito Dashboard — Data Builder
=================================

Consolida `sessions/*.json`, `logs/*.log` y `config/*.json` en un único
`dashboard/data.json` consumible por el dashboard HTML.

Uso:
    python3 dashboard/api/build_data.py
    python3 dashboard/api/build_data.py --cognito-dir ~/.claude/cognito

Salida: `dashboard/data.json` con esta forma:

{
  "generatedAt": "2026-04-15T...",
  "cognitoDir": "...",
  "status": {
    "profile": "operator",
    "currentPhase": "discovery",
    "phaseSince": "2026-04-15T...",
    "overrideModes": [],
    "sinapsisBridge": {"available": true, "version": "4.3"}
  },
  "totals": {
    "sessions": 42,
    "modesUsed": 7,
    "gatesTriggered": 15,
    "phaseDetections": 8
  },
  "modeUsage": [
    {"mode": "divergente", "count": 12},
    ...
  ],
  "phaseDistribution": [
    {"phase": "discovery", "sessions": 10, "lastSeen": "..."},
    ...
  ],
  "gatesBreakdown": [
    {"gate": "n8n-retired", "count": 3},
    ...
  ],
  "recentSessions": [
    {"sessionId": "...", "closedAt": "...", "phaseAtClose": "...", "metrics": {...}},
    ...
  ],
  "activityTimeline": [
    {"date": "2026-04-10", "sessions": 3, "gates": 5, "injections": 12}
  ]
}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _read_json(path: Path) -> dict | list | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _read_lines(path: Path) -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            return f.readlines()
    except OSError:
        return []


def _read_status(cognito_dir: Path) -> dict:
    """Extrae snapshot de estado actual."""
    state = _read_json(cognito_dir / "config" / "_phase-state.json") or {}
    operator = _read_json(cognito_dir / "config" / "_operator-config.json") or {}

    sinapsis_status = {"available": False, "version": None}
    # Probar bridge si existe
    bridge_path = cognito_dir / "integrations" / "sinapsis_bridge.py"
    if bridge_path.exists():
        try:
            sys.path.insert(0, str(cognito_dir / "integrations"))
            from sinapsis_bridge import SinapsisBridge  # type: ignore
            b = SinapsisBridge.detect(operator_config=operator)
            sinapsis_status = {
                "available": b.available,
                "version": b.version,
                "instincts": len(b.get_active_instincts(limit=9999)) if b.available else 0,
            }
        except Exception as e:  # noqa: BLE001
            sinapsis_status["error"] = str(e)

    return {
        "profile": operator.get("profile", "unknown"),
        "currentPhase": state.get("current", "unknown"),
        "phaseSince": state.get("since"),
        "overrideModes": state.get("overrideModes", []),
        "sinapsisBridge": sinapsis_status,
    }


def _read_sessions(cognito_dir: Path) -> list[dict]:
    sessions_dir = cognito_dir / "sessions"
    if not sessions_dir.exists():
        return []
    rows: list[dict] = []
    for f in sorted(sessions_dir.glob("*.json")):
        data = _read_json(f)
        if isinstance(data, dict) and data.get("sessionId"):
            rows.append(data)
    # Ordenar por closedAt desc
    rows.sort(key=lambda r: r.get("closedAt", ""), reverse=True)
    return rows


def _parse_log_timestamps(cognito_dir: Path, log_name: str) -> list[datetime]:
    """Extrae timestamps de un log de hook (formato [YYYY-MM-DDTHH:MM:SSZ])."""
    log_path = cognito_dir / "logs" / log_name
    timestamps: list[datetime] = []
    regex = re.compile(r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]")
    for line in _read_lines(log_path):
        m = regex.match(line)
        if m:
            try:
                ts = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
                timestamps.append(ts)
            except ValueError:
                continue
    return timestamps


def _count_mode_usage(cognito_dir: Path) -> list[dict]:
    """Cuenta inyecciones por modo desde mode-injector.log."""
    log_path = cognito_dir / "logs" / "mode-injector.log"
    counter: Counter[str] = Counter()
    for line in _read_lines(log_path):
        # Formato típico: "... Modos activos: divergente,estratega (fase: discovery)"
        if "Modos activos:" in line:
            m = re.search(r"Modos activos: ([^\(]+)", line)
            if m:
                modes = [x.strip() for x in m.group(1).split(",") if x.strip()]
                for mode in modes:
                    counter[mode] += 1
    return [{"mode": m, "count": c} for m, c in counter.most_common()]


def _count_gates(cognito_dir: Path) -> list[dict]:
    """Cuenta violaciones por gate desde gate-validator.log."""
    log_path = cognito_dir / "logs" / "gate-validator.log"
    counter: Counter[str] = Counter()
    for line in _read_lines(log_path):
        # Formato: "... Violaciones para X: ['gate-1', 'gate-2']"
        m = re.search(r"Violaciones para [^:]+: \[([^\]]+)\]", line)
        if m:
            ids = re.findall(r"'([^']+)'", m.group(1))
            for gid in ids:
                counter[gid] += 1
    return [{"gate": g, "count": c} for g, c in counter.most_common()]


def _phase_distribution(sessions: list[dict]) -> list[dict]:
    """Cuenta sesiones por fase al cerrar."""
    by_phase: dict[str, dict] = {}
    for s in sessions:
        phase = s.get("phaseAtClose", "unknown")
        if phase not in by_phase:
            by_phase[phase] = {"phase": phase, "sessions": 0, "lastSeen": s.get("closedAt")}
        by_phase[phase]["sessions"] += 1
        last = by_phase[phase]["lastSeen"] or ""
        if (s.get("closedAt") or "") > last:
            by_phase[phase]["lastSeen"] = s.get("closedAt")
    return sorted(by_phase.values(), key=lambda r: r["sessions"], reverse=True)


def _activity_timeline(cognito_dir: Path, sessions: list[dict], days: int = 30) -> list[dict]:
    """Actividad por día: sesiones cerradas, gates disparadas, inyecciones."""
    daily_sessions: Counter[str] = Counter()
    daily_gates: Counter[str] = Counter()
    daily_injections: Counter[str] = Counter()

    for s in sessions:
        closed = s.get("closedAt")
        if closed and len(closed) >= 10:
            daily_sessions[closed[:10]] += 1

    for ts in _parse_log_timestamps(cognito_dir, "gate-validator.log"):
        daily_gates[ts.strftime("%Y-%m-%d")] += 1

    for ts in _parse_log_timestamps(cognito_dir, "mode-injector.log"):
        daily_injections[ts.strftime("%Y-%m-%d")] += 1

    # Conjunto de fechas únicas
    all_dates = sorted(
        set(daily_sessions) | set(daily_gates) | set(daily_injections),
        reverse=True,
    )[:days]
    return [
        {
            "date": d,
            "sessions": daily_sessions.get(d, 0),
            "gates": daily_gates.get(d, 0),
            "injections": daily_injections.get(d, 0),
        }
        for d in sorted(all_dates)
    ]


def build(cognito_dir: Path) -> dict:
    status = _read_status(cognito_dir)
    sessions = _read_sessions(cognito_dir)
    mode_usage = _count_mode_usage(cognito_dir)
    gates_breakdown = _count_gates(cognito_dir)
    phase_dist = _phase_distribution(sessions)
    timeline = _activity_timeline(cognito_dir, sessions)

    totals = {
        "sessions": len(sessions),
        "modesUsed": len(mode_usage),
        "gatesTriggered": sum(g["count"] for g in gates_breakdown),
        "phaseDetections": len(_parse_log_timestamps(cognito_dir, "phase-detector.log")),
    }

    return {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cognitoDir": str(cognito_dir),
        "status": status,
        "totals": totals,
        "modeUsage": mode_usage,
        "phaseDistribution": phase_dist,
        "gatesBreakdown": gates_breakdown,
        "recentSessions": sessions[:20],
        "activityTimeline": timeline,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera dashboard/data.json")
    ap.add_argument(
        "--cognito-dir",
        default=None,
        help="Dir de Cognito (default: auto-detect desde este script)",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="Ruta salida (default: dashboard/data.json junto al script)",
    )
    args = ap.parse_args()

    script_dir = Path(__file__).parent.resolve()
    default_cognito = script_dir.parent.parent  # dashboard/api/ -> cognito/
    cognito_dir = (
        Path(os.path.expanduser(args.cognito_dir)).resolve()
        if args.cognito_dir
        else default_cognito
    )

    if not (cognito_dir / "config").exists():
        print(f"[ERR] {cognito_dir} no parece una instalacion Cognito (falta config/)", file=sys.stderr)
        return 1

    data = build(cognito_dir)

    output_path = (
        Path(args.output).resolve()
        if args.output
        else (script_dir.parent / "data.json")
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Forzar UTF-8 en stdout para Windows (cp1252 rompe con emojis/unicode)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    print(f"[OK] Generado {output_path}")
    print(f"  Sessions:         {data['totals']['sessions']}")
    print(f"  Modes usados:     {data['totals']['modesUsed']}")
    print(f"  Gates disparados: {data['totals']['gatesTriggered']}")
    print(f"  Fase detecciones: {data['totals']['phaseDetections']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
