---
description: Dashboard completo del estado de Cognito. Con --verify corre una auditoría de salud.
---

# /cognition-status

Dashboard del estado del sistema Cognito.

## Subcomandos

- `/cognition-status` — dashboard legible (el formato de abajo).
- `/cognition-status --verify` — ejecuta `scripts/cognition-verify.sh` y muestra el resultado. Útil para debuggear instalaciones rotas.
- `/cognition-status --json` — vuelca los mismos datos como JSON (útil para scripting).

Cuando el usuario añada `--verify`, corre **exactamente**:

```bash
bash ~/.claude/cognito/../cognito-repo/scripts/cognition-verify.sh
```

o si el repo no está cerca, ejecuta el script desde la carpeta de install
(`~/.claude/cognito/scripts/cognition-verify.sh` si existe) y presenta el
resultado. Exit code != 0 implica que al menos un check FAIL.

## Tu tarea (modo dashboard, sin `--verify`)

Lee los siguientes archivos y compón el dashboard:

- `~/.claude/cognito/config/_phase-state.json` → fase, timestamps, overrides
- `~/.claude/cognito/config/_operator-config.json` → perfil, modos habilitados, gates
- `~/.claude/cognito/config/_modes.json` → definiciones
- `~/.claude/cognito/config/_phases.json` → defaults por fase
- `~/.claude/cognito/sessions/` → últimas sesiones cerradas
- `~/.claude/cognito/logs/` → métricas si existen

## Formato de salida

```
╭─ Cognito Status ─────────────────────────────────────╮
│ Perfil:       [profile]                               │
│ Versión:      [version de _operator-config]           │
│                                                       │
│ 📍 FASE                                                │
│ Actual:       [current] (desde: [since])              │
│ Duración:     [cálculo]                               │
│ Anterior:     [previousPhases[-1] o "primera"]        │
│                                                       │
│ 🧠 MODOS                                              │
│ Por defecto:  [lista con ✓]                           │
│ Overrides:    [lista con ⭐ o "ninguno"]              │
│ Habilitados:  [enabled.length]/[total]                │
│ Deshabilit.:  [disabled o "ninguno"]                  │
│                                                       │
│ 🔒 HOOKS                                              │
│ phase-detector:  [activo si disponible]               │
│ mode-injector:   [activo si disponible]               │
│ gate-validator:  [activo si disponible]               │
│ session-closer:  [activo si disponible]               │
│                                                       │
│ 🛡 GATES                                              │
│ Activos:      [lista con ✓]                           │
│ Desactivad.:  [lista o "ninguno"]                     │
│                                                       │
│ 📊 SESIÓN ACTUAL                                      │
│ Inyecciones modo: [count de logs mode-injector]       │
│ Detecciones fase: [count de logs phase-detector]      │
│ Gates disparados: [count de logs gate-validator]      │
│                                                       │
│ 📈 HISTORIAL (últimas 3 sesiones)                     │
│ [timestamp]: fase=[x], gates=[n], injections=[m]      │
│ [timestamp]: ...                                      │
│                                                       │
│ 🔗 INTEGRACIONES                                      │
│ Sinapsis:     [✓ o ✗]                                │
│ Skill Router: [✓ o ✗]                                │
│                                                       │
│ ⚠️ WARNINGS (si aplica)                               │
│ - [warning específico, ej: "Fase ejecución hace >7d"] │
│                                                       │
╰───────────────────────────────────────────────────────╯

Comandos disponibles:
  /fase <nombre>              cambiar fase
  /modo <nombre>              activar modo (override)
  /modo off <nombre>          desactivar override
  /cognition-gate off <id>    desactivar gate
  /cognition-reset            resetear estado
```

## Reglas

1. **Si falta algún archivo de config**: reporta cuál y sugiere re-instalar.
2. **Si no hay sesiones previas**: omitir sección historial.
3. **Warnings automáticos**:
   - "Fase [x] activa hace más de 14 días sin cambio" → sugerir revisar.
   - "Gates X% deshabilitadas" si >30% → sugerir revisar configuración.
   - "Sinapsis configurado como installed pero archivos no encontrados" → sugerir reparar.
4. **Formato legible**: usa el box-drawing consistente. Respeta anchos.

## Notas

- No modifiques ningún archivo, solo lectura.
- Si `sessions/` está vacío, primera sesión o instalación reciente.
- El cálculo de duración de fase debe ser humano ("3 horas", "2 días"), no ISO.
