# Plantilla — Pre-mortem

Usa esta plantilla en modo **Devil's Advocate** (fase Planning o Review).

Principio: *imagina que han pasado 6-12 meses y el plan ha fracasado. Escribe el post-mortem antes de empezar.*

---

## Contexto

- **Decisión / plan**: [nombre corto]
- **Horizonte del pre-mortem**: [3 / 6 / 12 / 24 meses]
- **Fase actual**: [Planning / Review]

## Escenario de fracaso

> "Estamos a [fecha + N meses]. El plan ha fracasado. Revisemos qué pasó."

## 3-5 causas raíz del fracaso (hipotéticas pero realistas)

### Causa raíz 1: [Nombre corto]

- **Qué ocurrió**: [descripción concreta]
- **Síntomas tempranos** (qué habríamos podido detectar antes): [...]
- **Momento de no-retorno**: [cuándo pasó de reversible a irreversible]
- **Probabilidad estimada**: Alta / Media / Baja

### Causa raíz 2: [Nombre corto]

- **Qué ocurrió**: [...]
- **Síntomas tempranos**: [...]
- **Momento de no-retorno**: [...]
- **Probabilidad estimada**: [...]

### Causa raíz 3: [Nombre corto]

...

(Máximo 5. Si llegas a más, jerarquiza y agrupa.)

## Steel-man del opuesto

*El mejor argumento posible contra hacer esto (no straw-man):*

> [Argumento estructurado que un experto competente daría para NO hacer este plan. Debe ser convincente, no fácil de derribar.]

## Puntos de fragilidad concretos

- **Asunción crítica**: [cuál] → ¿qué pasa si no se cumple?
- **Dependencia externa**: [cuál] → ¿qué control tenemos?
- **Recurso escaso**: [cuál] → ¿qué falta para que sobre?
- **Reversibilidad**: [baja / media / alta] — [por qué]
- **Ventana temporal**: [hay deadline crítico? ¿qué pasa si se pierde?]

## Mitigaciones propuestas

| Causa raíz | Mitigación concreta | Coste (€/tiempo) | Efectividad esperada |
|------------|--------------------|-----------------|---------------------|
| 1 | [...] | [...] | Alta/Media/Baja |
| 2 | [...] | [...] | [...] |
| 3 | [...] | [...] | [...] |

**Prioriza por ratio efectividad/coste.** No todo hay que mitigar.

## Veredicto

- [ ] **Decisión apropiada tal cual** — procedemos.
- [ ] **Decisión apropiada con cambios** — aplicar mitigaciones antes de proceder.
- [ ] **Replantear** — volver a fase [Discovery/Planning] porque [...].

### Si procedemos

**Monitorizar estas señales de alarma tempranas**:

1. [señal concreta con umbral]
2. [...]
3. [...]

**Si alguna señal se dispara**: [acción predefinida]

---

## Validación del pre-mortem

- [ ] Las causas raíz son concretas (no "el mercado puede cambiar").
- [ ] Cada causa tiene síntomas tempranos observables.
- [ ] El steel-man es convincente (no caricatura).
- [ ] Las mitigaciones son accionables con dueño y plazo implícitos.
- [ ] El veredicto es claro (no "depende").
- [ ] Hay señales de alarma definidas para monitoreo futuro.
