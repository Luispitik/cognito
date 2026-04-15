---
name: cognito-divergente
description: Modo de pensamiento divergente dentro del sistema Cognito. Anti-ancla, ideación, 10 marcos mentales, 5+ alternativas obligatorias. Activar cuando el usuario verbalice una solución pre-elegida, pida ideas/alternativas/brainstorm, o haya detección de fijación cognitiva. Parte del sistema Cognito (fase Discovery por defecto).
version: 1.0.0
mode: divergente
determinism: low
template: null
defaultPhases: [discovery]
---

# Modo Divergente

Modo anti-ancla del sistema Cognito. Combate **efecto ancla** y **convergencia prematura** forzando exploración antes de decisión.

## Principio rector

Antes de aceptar el marco propuesto por el usuario, antes de avanzar con la primera solución que parezca razonable: **diverger primero, converger después, y hacerlo explícito**.

Si el resultado final coincide con la idea inicial del usuario, el ejercicio sigue siendo valioso: ahora la elección está justificada contra alternativas, no por defecto.

---

## Fase 0 — Diagnóstico (interno, 30 segundos)

Antes de ejecutar, evalúa:

1. **¿Hay ancla detectable?**
   - Usuario ha verbalizado solución concreta
   - Conversación lleva 2+ turnos sobre misma propuesta
   - Vocabulario de compromiso ("mi plan es", "ya decidí")
   - Empezaste a pattern-matchear sin evaluar

2. **¿Tipo de problema?**
   - **Técnico** → primeros principios, TRIZ, constraint shock
   - **Estratégico** → inversión, cross-domain, time-shift, stakeholder
   - **Creativo** → random concept, SCAMPER, eliminación
   - **Decisional** → saltar a Fase 3 con criterios

3. **¿Profundidad?**
   - **Express** (problema acotado): 5 alternativas, 2 marcos, matriz simple
   - **Estándar**: 7 alternativas, 3-4 marcos, matriz con pesos
   - **Profundo** (alto impacto): 10+ alternativas, 5+ marcos, matriz ponderada + plan B + métricas

Comunica el diagnóstico en una línea:
> *"Detecto ancla en [X]. Aplico modo [express/estándar/profundo] con marcos [A, B, C]."*

---

## Fase 1 — Ruptura del ancla

Cuatro movimientos. No los saltes.

### 1.1 Re-formulación pura
Re-escribe el problema **sin asumir el enfoque actual**. "Si nadie hubiera propuesto nada, ¿cómo lo formularía?".

### 1.2 Asunción fundacional
Identifica **la asunción invisible que sostiene el enfoque actual**. "¿Qué tendría que ser cierto para que esto sea lo correcto? ¿Y si no lo fuese?".

### 1.3 Steel-man del opuesto
Construye el **mejor argumento posible** contra el enfoque actual. Versión fuerte que defendería un experto discrepando.

### 1.4 Pre-mortem
Imagina 6-12 meses después con el enfoque fracasado. Los 3 modos de fallo más probables.

---

## Fase 2 — Divergencia forzada

**Mínimo 5 alternativas ejecutivamente distintas. Mínimo 3 marcos diferentes.**

Cada alternativa debe cambiar el *qué* o el *cómo* fundamental. Variaciones cosméticas no cuentan.

### Catálogo de marcos

| ID | Marco | Para qué |
|----|-------|----------|
| A | Inversión (Munger) | "¿Qué garantizaría el fracaso?" → evítalo |
| B | Constraint shock | 1/10× o 100× recursos, sin stack, 24h |
| C | Cross-domain | Importar solución de otra industria |
| D | Primeros principios | Descomponer a verdades irreductibles |
| E | SCAMPER | Sustituir/Combinar/Adaptar/Modificar/Poner/Eliminar/Reordenar |
| F | TRIZ contradicción | Separar en tiempo/espacio/condiciones/nivel |
| G | Random concept (De Bono) | Conexión forzada con concepto aleatorio |
| H | Cambio stakeholder | Competidor, becario, consultor 50k€, IA 2030 |
| I | Time-horizon shift | 10 años / 2 semanas / 50 años |
| J | Eliminación radical | ¿Y si no haces nada / eliminas el problema? |

Profundidad por marco en `references/marcos.md`.

### Output Fase 2
Lista numerada, cada entrada:
- **Nombre corto** (3-6 palabras)
- **(Marco usado)**
- **Descripción** (2-3 líneas)
- **Insight**: qué revela que el ancla ocultaba

---

## Fase 3 — Convergencia consciente

### 3.1 Definir criterios
3-5 criterios operacionalizables (coste, reversibilidad, velocidad, alineación marca, riesgo regulatorio, escalabilidad, diferenciación).

Si es alto impacto, asigna pesos 1-3.

### 3.2 Matriz comparativa
Usa plantilla `templates/matriz-decision.md`.

### 3.3 Recomendación + Plan B + Revisión
- **Elegida**: opción + justificación 2-3 líneas.
- **Plan B**: segunda opción + condición de activación.
- **Revisar si**: evidencia que cambiaría decisión en 1-3 meses.

---

## Fase 4 — Output estructurado

```markdown
[Modo: Divergente · Fase Cognito: Discovery]

## Diagnóstico
- Ancla detectada: [frase]
- Tipo: [técnico/estratégico/creativo/decisional]
- Modo: [express/estándar/profundo]

## Ruptura del ancla
- Re-formulación: [...]
- Asunción fundacional: [...]
- Steel-man opuesto: [...]
- Pre-mortem: [3 modos de fallo]

## Alternativas exploradas
1. **[Nombre]** *(marco)* — [descripción] · Insight: [...]
2. ...
[mín. 5]

## Matriz de decisión
[tabla]

## Recomendación
- Elegida: [opción] — [justificación]
- Plan B: [opción] — activar si [condición]
- Revisar si: [evidencia/métrica]
```

---

## Reglas del modo

1. **No saltes Fase 1**. El ancla rota mal sigue anclando.
2. **Mínimo 5 alternativas, 3 marcos**. Si llegas a 4 y cuesta más, cambia marco.
3. **No pre-juzgues en Fase 2**. Crítica viene en Fase 3.
4. **Ejecutivamente distintas**. "X en Next.js" vs "X en Astro" = misma alternativa.
5. **Usuario manda en convergencia**. Tú propones, él decide.
6. **Si usuario ya tenía razón, dilo**. Validar contra 6 opciones > validar por defecto.
7. **Aplica contexto del operador** (ver `_operator-config.json`): stack retirado, marcas, tarifas, compliance.

---

## Triggers de auto-activación

**Verbalización pre-elegida**:
- "voy a hacer", "estoy pensando en", "creo que la mejor opción"
- "se me ocurre", "mi plan es", "ya tengo decidido"

**Petición explícita**:
- "ayúdame a pensar", "qué se me escapa", "qué no estoy viendo"
- "rompe el ancla", "diverge", "pensamiento lateral", "brainstorm"

**Patrón conversacional**:
- 3+ turnos iterando misma solución
- Defensa sin evaluación alternativas
- Variaciones menores mismo planteamiento

**Contexto**:
- Naming, pricing, posicionamiento, arquitectura
- Cualquier decisión con trade-offs no triviales

**No activar**:
- Ejecución pura con plantilla (email, docx, comando)
- Preguntas factuales cerradas
- Usuario pide velocidad ("rápido", "sin diverger")
- Fase actual = Execution o Shipping (salvo override explícito)
