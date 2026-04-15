---
description: Activa modo Devil's Advocate. Pre-mortem + steel-man del opuesto sobre la propuesta actual.
---

# /devils-advocate

Atajo al modo Devil's Advocate de Cognito.

## Tu tarea

1. Añade `devils-advocate` a `overrideModes` en `_phase-state.json`.
2. Identifica la propuesta/plan/decisión activa en la conversación.
3. Usa plantilla `templates/pre-mortem.md` para generar:
   - Escenario de fracaso a 6-12 meses
   - 3-5 causas raíz con probabilidad
   - Steel-man del opuesto (plantilla `templates/steel-man.md` opcional)
   - Puntos de fragilidad concretos (asunciones, dependencias, reversibilidad)
   - Mitigaciones propuestas con coste y efectividad
   - Veredicto: procedemos tal cual / con cambios / replantear

## Output

```
[Modo: Devil's Advocate (override) · Fase: [current]]

## Pre-mortem — [Nombre de la decisión]

### Contexto
[1-2 líneas]

### Escenario de fracaso (6-12 meses)
[...]

### Causas raíz
1. [Causa 1] — probabilidad: [...], síntomas tempranos: [...]
2. ...
3. ...

### Steel-man del opuesto
[Mejor argumento contra, no caricatura]

### Puntos de fragilidad
- Asunción crítica: [...]
- Dependencia externa: [...]
- Recurso escaso: [...]
- Reversibilidad: [...]

### Mitigaciones
[Tabla con causa → mitigación → coste → efectividad]

### Veredicto
[PROCEDE / PROCEDE CON CAMBIOS / REPLANTEAR]

Si PROCEDE CON CAMBIOS:
- [Cambio 1]
- [Cambio 2]

Si PROCEDE, monitorizar:
- [Señal de alarma 1]
- [Señal de alarma 2]
```

## Reglas

1. **Críticas accionables**: cada crítica con mitigación concreta.
2. **Steel-man real**: argumento contrario convincente, no fácil de derribar.
3. **Cifras, no adjetivos**: "30% probabilidad X" > "riesgo alto".
4. **Máximo 5 puntos**: jerarquiza.
5. **Veredicto claro**: no "depende" ni "tal vez".

## Cuándo NO ejecutar
- Sin propuesta definida en conversación.
- Usuario pide ejecución (fase Execution activa).

## Nota
Override. Al terminar, `/modo off devils-advocate` si procede.
