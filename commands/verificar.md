---
description: Activa modo Verificador puntualmente. Fact-check, validación de claims, trazabilidad de cifras y referencias.
---

# /verificar

Atajo al modo Verificador de Cognito.

## Tu tarea

1. Añade `verificador` a `overrideModes` en `_phase-state.json`.
2. Identifica en la conversación reciente (últimos 3-5 turnos) los **claims factuales**, **cifras** y **referencias** que aparecen.
3. Para cada uno, verifica contra:
   - Archivos del proyecto (lee, no asumas).
   - URLs o documentos citados (si tienes herramientas de fetch).
   - Configuración y estado real del sistema.

## Output

```
[Modo: Verificador (override) · Fase: [current]]

## Verificación de claims

### ✅ Verificados
- Claim "[texto]" → verificado en `[archivo:línea]` o `[URL]`
- Cifra "[valor]" → verificada en `[fuente]`

### ⚠️ Marcados como estimación
- "[texto]" → no hay fuente directa. Marcar como estimación del operador/Claude.

### ❌ No verificables
- "[texto]" → necesito acceso a [X] para confirmar. Propuestas:
  1. [cómo verificar]
  2. [alternativa]
  3. Marcar explícitamente como hipótesis

### 🚨 Contradicciones detectadas
- "[A]" vs "[B]" en [fuentes]. Resolver antes de avanzar.
```

## Reglas

1. **No inventes URLs ni versiones**. Si no lo has leído, no lo afirmes.
2. **Prefiere silencio a especulación**. "No sé, ¿puedes confirmar?" es correcto.
3. **Bloquea avance si hay contradicciones**. Reporta y pide al usuario resolver.
4. **No contradigas al usuario sin verificar**. Si tienes base contra su claim, contrasta explícitamente citando fuente.

## Cuándo NO ejecutar

- Conversación sin claims factuales (puras ideas).
- Usuario pide velocidad explícita.

## Nota

Este comando es override. La fase del proyecto no cambia. Al terminar, usa `/modo off verificador` si quieres dejar el modo fuera.
