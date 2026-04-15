# Plantilla — Auditoría de Output

Usa esta plantilla en modo **Auditor** (fase Review).

---

## Metadata

- **Proyecto / sprint / entrega auditada**: [nombre]
- **Periodo**: [desde] → [hasta]
- **Tipo de auditoría**: Pre-shipping / Post-shipping / Sprint retro / Incidente
- **Auditor**: [Cognito + operador]
- **Fecha auditoría**: [timestamp]

## Alcance

- **Outputs revisados**: [código, documentos, decisiones, entregables]
- **Fuera de alcance**: [lo que explícitamente no se audita]

---

## 1. Qué funcionó (retener)

*Máximo 3 puntos priorizados.*

### 1.1 [Práctica]
- **Descripción concreta**: [...]
- **Evidencia**: [archivo, commit, documento, cifra]
- **Por qué funcionó**: [análisis breve]
- **Recomendación**: replicar en [contextos similares]

### 1.2 [Práctica]
...

### 1.3 [Práctica]
...

---

## 2. Qué no funcionó (corregir)

*Máximo 3 puntos priorizados.*

### 2.1 [Problema]
- **Descripción concreta**: [...]
- **Causa raíz probable**: [análisis, no especulación]
- **Impacto observado**: [cifra, tiempo perdido, retrabajo]
- **Acción correctiva propuesta**:
  - **Qué**: [acción concreta]
  - **Dueño**: [quién]
  - **Plazo**: [cuándo]
  - **Cómo verificar**: [criterio de éxito]

### 2.2 [Problema]
...

### 2.3 [Problema]
...

---

## 3. Qué faltó (añadir)

### 3.1 [Gap]
- **Qué debería haberse hecho y no se hizo**: [...]
- **Consecuencia**: [...]
- **Cómo detectar antes la próxima vez**: [mecanismo, gate, checklist]

### 3.2 [Gap]
...

---

## 4. Lessons learned (codificables)

*Formular como reglas imperativas, aptas para promocionar a Sinapsis instincts.*

### L1: [Nombre de la lección]
- **Regla**: "Cuando [contexto], [hacer/evitar] [acción], porque [razón]"
- **Contexto de aplicación**: [cuándo aplica]
- **Cómo detectar**: [trigger observable]
- **¿Añadir a Sinapsis?**: sí / no — [razón]
- **Scope**: global / project / personal

### L2: [Nombre de la lección]
...

---

## 5. Patrones detectados

- **¿Se parece a algo anterior?**:
  - [ ] No — caso único
  - [ ] Sí — referencia: [proyecto/incidente previo]
- **¿Anti-patrón repetido?**:
  - [ ] No
  - [ ] Sí — cuál: [...]
    - **Propuesta**: codificar como gate en `_passive-triggers.json`

---

## 6. Calidad del output

| Criterio | Nivel | Evidencia | Qué falta si no "alto" |
|----------|-------|-----------|------------------------|
| Completitud | Alto/Medio/Bajo | [...] | [...] |
| Consistencia interna | ... | ... | ... |
| Consistencia con decisiones previas | ... | ... | ... |
| Robustez (tests, edge cases) | ... | ... | ... |
| Documentación | ... | ... | ... |
| Compliance (EU AI Act, RGPD, etc.) | ... | ... | ... |
| Ready to ship | sí/no | ... | ... |

---

## 7. Veredicto

- [ ] **LISTO** — pasar a Shipping.
- [ ] **AJUSTAR** — aplicar [N] cambios listados en sección 2 antes de Shipping:
  - [ ] Acción 2.1
  - [ ] Acción 2.2
  - [ ] ...
- [ ] **REPLANTEAR** — volver a fase [Discovery/Planning] porque [razón específica].

### Justificación del veredicto
[2-3 líneas]

### Si LISTO, siguientes pasos
1. [...]
2. [...]

### Si AJUSTAR, re-auditar cuando
- [ ] Las acciones correctivas estén completadas.
- [ ] [Evidencia concreta de que se resolvieron los problemas]

---

## 8. Integración con Sinapsis (si está instalado)

**Instincts candidatos para promover**:
- [ ] L1 — `/instinct-add` (requiere confirmación del operador)
- [ ] L2 — `/instinct-add` (requiere confirmación del operador)

**Instincts existentes validados/refutados por esta auditoría**:
- ✓ [Instinct ID]: confirmado de nuevo.
- ✗ [Instinct ID]: refutado por [evidencia] — candidato a revisar.

---

## Validación de la auditoría

- [ ] Cada punto de "retener/corregir/añadir" tiene evidencia concreta (no opinión).
- [ ] Lessons formuladas como reglas imperativas.
- [ ] Veredicto claro (LISTO/AJUSTAR/REPLANTEAR) con justificación.
- [ ] Acciones correctivas con dueño y plazo.
- [ ] Sin blame storm (causa raíz, no culpable).
- [ ] Patrones cross-proyecto mencionados si aplica.
