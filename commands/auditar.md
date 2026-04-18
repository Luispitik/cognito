---
description: Activa modo Auditor. Post-mortem estructurado, lessons learned, QA output.
---

# /auditar

Atajo al modo Auditor de Cognito.

## Tu tarea

1. Añade `auditor` a `overrideModes` en `_phase-state.json`.
2. Identifica el alcance de la auditoría (proyecto, sprint, entrega, incidente).
3. Usa plantilla `templates/auditoria-output.md` completa:
   - Qué funcionó (máx 3)
   - Qué no funcionó (máx 3)
   - Qué faltó (máx 3)
   - Lessons learned codificables
   - Patrones detectados
   - Calidad del output (tabla)
   - Veredicto: LISTO / AJUSTAR / REPLANTEAR

## Output

Usa la estructura completa de `templates/auditoria-output.md`. Header:

```
[Modo: Auditor (override) · Fase: [current]]

## Auditoría — [Alcance]
[...]
```

## Tipos de auditoría

Detecta el tipo del contexto:

- **Pre-shipping**: foco en "ready to ship?"
- **Post-shipping**: foco en lessons + patrones
- **Sprint retro**: foco en acciones siguiente sprint
- **Incidente**: foco en causa raíz + prevención

## Reglas

1. **Evidencia, no opinión**: cada punto con cita/ejemplo/cifra.
2. **Separar persona de práctica**: "el flujo X falla", no "Fulano hizo mal".
3. **Lessons formuladas como reglas**: "Cuando X, siempre Y porque Z".
4. **Jerarquizar**: máx 3 por sección.
5. **Veredicto claro**: LISTO / AJUSTAR / REPLANTEAR con justificación.

## Integración con Sinapsis

Si Sinapsis está instalado, al final propón lessons candidatos a instincts:

```
**Lessons candidatos para Sinapsis**:
- L1: "[regla]" — scope: [global/project] — `/instinct-add` para promover
```

No añadas instincts sin confirmación del usuario.

## Cuándo NO ejecutar

- Proyecto en curso sin entregable finalizado (audita algo concreto).
- Sin datos suficientes para evidencia.

## Nota

Override. Al terminar, `/modo off auditor`.
