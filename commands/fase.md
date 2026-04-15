---
description: Cambia la fase activa de Cognito (discovery|planning|execution|review|shipping) o muestra estado actual con `status`.
argument-hint: [discovery|planning|execution|review|shipping|status]
---

# /fase

Controla la fase activa de Cognito para el proyecto actual.

## Tu tarea

Lee `$ARGUMENTS`:

### Si el argumento es una fase válida

1. Lee `~/.claude/cognito/config/_phases.json` para validar que existe.
2. Lee `~/.claude/cognito/config/_phase-state.json`.
3. Actualiza:
   - `current` → nueva fase
   - `previousPhases` → append la fase anterior con timestamp
   - `since` → timestamp actual (UTC ISO-8601)
   - `overrideModes` → vaciar (al cambiar fase, se resetean overrides)
   - `lastUpdatedBy` → "command-fase"
4. Reporta al usuario:

   ```
   ✓ Fase cambiada: [anterior] → [nueva]
   Modos activos por defecto en esta fase: [lista desde _phases.json → defaultModes]
   Recordatorio: [reminder de _phases.json → reminder]
   ```

### Si el argumento es `status` o vacío

Muestra fase actual:

```
📍 Fase actual: [current]
   Activa desde: [since]
   Duración: [cálculo desde since]
   Modos por defecto: [lista]
   Overrides activos: [lista o "ninguno"]
   Fase anterior: [previousPhases[-1] o "primera fase"]
```

### Si el argumento no es válido

Muestra fases disponibles:

```
⚠️ Fase no reconocida: "[arg]"
Fases válidas:
  - discovery   (exploración, anti-ancla)
  - planning    (decisión, pre-mortem, matriz)
  - execution   (ejecución, zero drift)
  - review      (auditoría, lessons)
  - shipping    (entrega, máximo determinismo)

Uso: /fase <nombre> | /fase status
```

## Reglas

1. **Confirmar antes de cambiar a `shipping`**: es fase crítica. Pregunta "¿Seguro? Shipping activa máximo determinismo y bloquea cambios de scope." antes de aplicar.
2. **Si la fase actual ya es la pedida**: reportar "Ya estás en fase [x]" y mostrar status.
3. **Nunca aplicar cambio sin confirmar al usuario** con la salida esperada.
4. **Si el archivo de estado no existe**: crearlo con defaults antes de escribir.

## Integración con Sinapsis

Si Sinapsis está instalado, al cambiar de fase registra el evento como observación (no bloqueante).
