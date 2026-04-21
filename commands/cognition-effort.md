---
name: cognition-effort
description: "Sugiere o fuerza el nivel de `effort` (low/medium/high/max) que Cognito añade al systemMessage. Útil con Claude Opus 4.7+ (el parámetro `output_config.effort` importa más en 4.7 que en versiones previas)."
---

# `/cognition-effort`

v2.1+. Permite al operador sobrescribir la recomendación automática de effort
que `mode_injector` infiere de los modos activos.

**Precedencia efectiva** (lo que acaba saliendo al systemMessage):

1. `config/_phase-state.json → overrideEffort` (esta pista — la pone este comando).
2. `config/_modes.json → modes.<id>.recommendedEffort` por modo activo.
3. Fallback determinism → effort (`low→medium`, `medium→high`, `high→high`).

---

## Uso

```
/cognition-effort              # muestra el estado actual (recomendación y override)
/cognition-effort low          # fuerza low en la próxima inyección
/cognition-effort medium
/cognition-effort high
/cognition-effort max          # Opus-tier only (Opus 4.6+); Sonnet/Haiku devolverán 400
/cognition-effort off          # elimina el override, vuelve a la recomendación automática
```

---

## Qué hace exactamente

1. Valida que `$1` sea uno de `low`, `medium`, `high`, `max`, `off`, o vacío.
2. Abre `config/_phase-state.json`, escribe:
   - `overrideEffort = <level>` si se pasa nivel válido.
   - `overrideEffort = null` si se pasa `off` o string vacío.
3. Actualiza `lastUpdatedBy = "cognition-effort"`.
4. Muestra el nivel efectivo (override si existe, si no la recomendación por
   modo activo, si no el fallback por determinism).

No toca el harness. El hint sale en el `systemMessage` del siguiente turno
cuando `mode-injector` se dispare.

---

## Notas para el operador

- **Opus 4.7**: `effort=max` vale la pena en modos críticos (Verificador,
  Auditor en Review), pero cuesta más tokens. Para Ejecutor con checklist
  estable, `low`/`medium` es más eficiente.
- **Sonnet 4.6**: no soporta `max` — devolverá 400. Si tu harness usa Sonnet,
  evita forzar `max` aquí.
- **Haiku 4.5**: no soporta el parámetro `effort` en absoluto — el hint se
  emite igual pero tu harness debe ignorarlo (o filtrarlo antes de llamar a
  la API).
- La escritura es atómica (archivo temporal + rename). Si el JSON se corrompe,
  usa `/cognition-status --verify --repair`.
