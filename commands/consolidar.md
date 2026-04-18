---
description: Activa modo Consolidador. Convergencia explícita con matriz decisión ponderada.
---

# /consolidar

Atajo al modo Consolidador de Cognito.

## Tu tarea

1. Añade `consolidador` a `overrideModes` en `_phase-state.json`.
2. Identifica las alternativas en curso en la conversación (si no hay ≥2, pide al usuario definir alternativas o ejecuta `/divergir` primero).
3. Usa plantilla `templates/matriz-decision.md`:
   - Definir 3-5 criterios operacionalizables
   - Asignar pesos 1-3 si hay alto impacto
   - Construir matriz alternativa × criterios
   - Calcular totales
   - Identificar trade-off de cada alternativa
   - Recomendación + Plan B + métricas de revisión

## Output

Usa la estructura completa de `templates/matriz-decision.md`. Header:

```
[Modo: Consolidador (override) · Fase: [current]]

## Consolidación — [Decisión]
[...]
```

## Reglas

1. **Criterios operacionalizables**: "¿cumple X?" con métrica, no "encaja con marca".
2. **Puntuación honesta**: no inflar para favorecer una opción.
3. **Trade-off concreto por alternativa**: nómbralo.
4. **Una recomendación, no dos**.
5. **Plan B con condición accionable**: "Si MRR no crece >10%/mes en 3 meses", no "si no va bien".
6. **Empates explícitos**: si <5% diferencia, dilo. No fuerces desempate.

## Cuándo NO ejecutar

- <2 alternativas disponibles.
- Fase actual = Execution/Shipping (consolidación ya ocurrió en Planning).
- Decisión trivial sin trade-offs.

## Interacción con Devil's Advocate

Si el usuario ejecuta `/devils-advocate` después de ti, incorpora sus críticas en la matriz. No es fallo del consolidador; es iteración sana.

## Nota

Override. Al terminar, `/modo off consolidador`.
