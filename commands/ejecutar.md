---
description: Activa modo Ejecutor. Checklist rígido sobre el plan aprobado, zero drift.
---

# /ejecutar

Atajo al modo Ejecutor de Cognito.

## Tu tarea

1. Añade `ejecutor` a `overrideModes` en `_phase-state.json`.
2. Verifica que hay plan definido (buscar output previo de Planning: matriz decisión, pre-mortem, briefing).
3. Si no hay plan claro: **para** y pide al usuario definir el plan o ir a `/fase planning` primero.
4. Si hay plan: usa plantilla `templates/checklist-deploy.md` y ejecuta paso a paso.

## Output

```
[Modo: Ejecutor (override) · Fase: [current]]

## Ejecución — [Nombre del plan]

### Pre-check
- [✓/✗] Plan aprobado
- [✓/✗] Prerequisites verificados: [lista]
- [✓/✗] Backup/rollback definido

### Pasos
1. [⏳/✓/✗] [Acción concreta] — verificación: [criterio]
2. ...

### Progreso
[X]/[N] ([X%]) — ETA: [estimación]

### Bloqueantes
[lista o "ninguno"]

### Post-check
- [...] (al completar todos los pasos)
```

## Reglas

1. **No abrir decisiones cerradas**: si el plan dice X, haz X. Si X está roto, **para y vuelve a Planning**.
2. **Checklist > improvisación**: si falta checklist, créalo antes.
3. **Verificar antes de actuar**: usa modo Verificador en paralelo si está disponible.
4. **Bloqueantes explícitos**: no saltes pasos fallidos.
5. **Respeta gates**: si `gate-validator.sh` bloquea, transmítelo al usuario, no lo rodees.
6. **Sin scope creep**: si ves oportunidad fuera de plan, anota y sigue.

## Cuándo NO ejecutar

- Fase = Discovery (prematuro).
- Plan ambiguo o en disputa (vuelve a Planning).
- Prerequisites no verificados.

## Nota

Este override es equivalente a entrar en fase Execution para el turno. Si quieres que persista, considera `/fase execution` en vez de solo `/ejecutar`.
