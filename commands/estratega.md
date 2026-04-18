---
description: Activa modo Estratega. Time-horizon shift, stakeholders, trade-offs macro.
---

# /estratega

Atajo al modo Estratega de Cognito.

## Tu tarea

1. Añade `estratega` a `overrideModes` en `_phase-state.json`.
2. Identifica la decisión táctica en conversación.
3. Eleva a análisis estratégico:
   - **Horizontes temporales**: 1 mes, 1 año, 5 años, 10 años
   - **Stakeholders**: competidor, mejor cliente, regulador, inversor, equipo
   - **Trade-offs macro**: velocidad vs marca, ingresos vs reputación, etc.
   - **Alineación con visión** (si hay visión declarada)

## Output

```
[Modo: Estratega (override) · Fase: [current]]

## Análisis estratégico — [Decisión]

### Contexto táctico
[Qué se decide a nivel operacional]

### Horizontes temporales
| Horizonte | Cómo se ve esta decisión |
|-----------|--------------------------|
| 1 mes | [...] |
| 1 año | [...] |
| 5 años | [...] |
| 10 años | [...] |

### Stakeholders clave
| Stakeholder | Reacción | Por qué importa |
|-------------|----------|-----------------|
| [...] | [...] | [...] |

### Trade-offs macro
- **Tensión**: [A vs B]
  - Si priorizas A: [consecuencia a 1 año]
  - Si priorizas B: [consecuencia a 1 año]

### Alineación con visión
- Visión declarada: "[...]" (o "no declarada — sugiero clarificar")
- Esta decisión [+/-] alineada porque [...]

### Recomendación estratégica
[Confirmar decisión táctica / proponer alternativa / pedir más datos]
```

## Reglas

1. **No futurología**: usa presente + tendencias observables, no predicciones.
2. **Stakeholders reales**: adapta al contexto del operador.
3. **Trade-offs concretos**: "si eliges A sacrificas B cuantificado en X".
4. **No moralizar**: consecuencias estratégicas, no juicios.
5. **No convertir todo en estrategia**: preguntas tácticas triviales no necesitan análisis de 10 años.

## Cuándo NO ejecutar

- Decisión trivial (nombre de variable, elección tool menor).
- Fase Execution (es tarde para zoom-out).
- Usuario pide velocidad.

## Nota

Override. Al terminar, `/modo off estratega`.
