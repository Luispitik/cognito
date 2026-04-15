#!/usr/bin/env python3
"""
seed_demo.py — Genera sesiones y logs ficticios para mostrar el dashboard.

Útil para:
- Demo en README con screenshots
- Validación visual del dashboard sin tener que usar Cognito 2 semanas
- Onboarding de nuevos usuarios

Uso:
    python3 dashboard/api/seed_demo.py
    python3 dashboard/api/seed_demo.py --sessions 60 --days 14
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

PHASES = ["discovery", "planning", "execution", "review", "shipping"]
MODES = [
    "divergente", "verificador", "devils-advocate", "consolidador",
    "ejecutor", "estratega", "auditor",
]
PHASE_MODES = {
    "discovery": ["divergente", "estratega"],
    "planning": ["devils-advocate", "consolidador", "estratega"],
    "execution": ["ejecutor", "verificador"],
    "review": ["auditor", "devils-advocate"],
    "shipping": ["ejecutor", "verificador"],
}
GATES = [
    "n8n-retired", "rls-supabase-required", "no-hardcode-pii",
    "no-commit-env", "operator-pricing-check", "eu-ai-act-sources",
]

SIGNALS = [
    "vamos a ejecutar", "qué se me escapa", "implementa", "review",
    "post-mortem", "ship it", "exploremos",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=35, help="Sesiones a generar")
    ap.add_argument("--days", type=int, default=21, help="Ventana temporal (dias)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    sessions_dir = PROJECT_ROOT / "sessions"
    logs_dir = PROJECT_ROOT / "logs"
    sessions_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # Limpiar previos
    for f in sessions_dir.glob("*.json"):
        f.unlink()
    for log in ("mode-injector.log", "gate-validator.log", "phase-detector.log", "session-closer.log"):
        (logs_dir / log).unlink(missing_ok=True)

    now = datetime.now(timezone.utc)

    gate_log = open(logs_dir / "gate-validator.log", "w", encoding="utf-8")
    mode_log = open(logs_dir / "mode-injector.log", "w", encoding="utf-8")
    phase_log = open(logs_dir / "phase-detector.log", "w", encoding="utf-8")

    for i in range(args.sessions):
        # Timestamp aleatorio en la ventana
        delta_days = random.uniform(0, args.days)
        delta_hours = random.uniform(0, 23)
        ts = now - timedelta(days=delta_days, hours=delta_hours)
        ts_iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Sesgo hacia execution/review (que es el uso típico)
        phase = random.choices(
            PHASES,
            weights=[20, 18, 30, 22, 10],
        )[0]

        # Modos según fase + overrides ocasionales
        base = PHASE_MODES[phase]
        overrides = random.sample(
            [m for m in MODES if m not in base],
            k=random.choices([0, 1, 2], weights=[60, 30, 10])[0],
        )
        active = base + overrides

        # Métricas
        gates_triggered = random.choices(
            [0, 0, 0, 1, 2, 3, 5],
            weights=[40, 30, 10, 10, 5, 3, 2],
        )[0]
        mode_injections = random.randint(3, 40)
        phase_detections = random.choices([0, 1, 2], weights=[70, 25, 5])[0]

        session_id = f"demo-{ts.strftime('%Y%m%d-%H%M%S')}-{i:03d}"
        session = {
            "sessionId": session_id,
            "closedAt": ts_iso,
            "phaseAtClose": phase,
            "metrics": {
                "gatesTriggered": gates_triggered,
                "modeInjections": mode_injections,
                "phaseDetections": phase_detections,
            },
        }
        with open(sessions_dir / f"{session_id}.json", "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)

        # Logs sintéticos
        for _ in range(mode_injections):
            log_ts = ts - timedelta(minutes=random.uniform(0, 60))
            mode_log.write(
                f"[{log_ts.strftime('%Y-%m-%dT%H:%M:%SZ')}] "
                f"Modos activos: {','.join(active)} (fase: {phase})\n"
            )

        for _ in range(gates_triggered):
            log_ts = ts - timedelta(minutes=random.uniform(0, 60))
            gates_hit = random.sample(GATES, k=random.randint(1, 2))
            gates_str = ", ".join(f"'{g}'" for g in gates_hit)
            gate_log.write(
                f"[{log_ts.strftime('%Y-%m-%dT%H:%M:%SZ')}] "
                f"Violaciones para demo/file{i}.ts: [{gates_str}]\n"
            )

        for _ in range(phase_detections):
            log_ts = ts - timedelta(minutes=random.uniform(0, 60))
            signal = random.choice(SIGNALS)
            target = random.choice([p for p in PHASES if p != phase])
            phase_log.write(
                f"[{log_ts.strftime('%Y-%m-%dT%H:%M:%SZ')}] "
                f'Detectado: "{signal}" -> sugerir {target} (medium)\n'
            )

    gate_log.close()
    mode_log.close()
    phase_log.close()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    print(f"[OK] Generadas {args.sessions} sesiones ficticias en {args.days} dias")
    print(f"  sessions/: {len(list(sessions_dir.glob('*.json')))} archivos")
    print(f"  logs/:     creados 3 logs con actividad sintetica")
    print()
    print("Siguiente paso:")
    print("  python3 dashboard/api/build_data.py && open dashboard/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
