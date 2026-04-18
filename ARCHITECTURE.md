# Cognito — Arquitectura

Este documento explica **por qué** Cognito está estructurado así y qué trade-offs se tomaron.

---

## 1. Principios de diseño

### 1.1 Modularidad sobre monolitismo

Cada modo es una skill independiente. Se pueden activar, desactivar, reemplazar o customizar sin tocar el resto.

### 1.2 Determinismo donde importa

Los hooks bash/python son deterministas (mismo input = mismo output). Se usan para **gates críticos** (bloquear anti-patrones, validar outputs) pero no para tareas creativas.

### 1.3 Estado persistente mínimo

Solo 1 archivo guarda el estado mutable (`_phase-state.json`). Los demás JSONs son configuración.

### 1.4 Audiencias como perfiles, no como forks

El código es uno. La adaptación a alumnos / público / cliente se hace vía YAML profiles que controlan qué se instala y cómo se formula.

### 1.5 Sin romper nada existente

Cognito convive con Sinapsis, skill-router, skills personales. No pisa hooks, no reescribe configuración global.

---

## 2. Modos × Fases × Hooks × Perfiles

Las 4 dimensiones ortogonales de Cognito:

```
┌─────────────────────────────────────────────────────────────┐
│  FASES        (cuándo)    Discovery → Planning → ...        │
│  MODOS        (cómo)      Divergente, Verificador, ...      │
│  HOOKS        (qué fija)  Gate-validator, Mode-injector, ... │
│  PERFILES     (para qué)  Operator, Alumno, Público, Cliente │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Comportamiento resultante
```

Ejemplo: **Fase Execution** × **Modo Ejecutor+Verificador** × **Hook gate-validator activo** × **Perfil Operator** = Claude construye sin divergir, valida anti-patrones (n8n, hardcode), aplica los gates específicos del operador.

Mismo escenario con **Perfil Público** = sin referencias a operador específico, lenguaje neutro, hooks genéricos.

---

## 3. Los 7 modos: por qué estos

Partimos del bestiario de sesgos conocidos de LLMs + ciclo cognitivo humano. La mapeamos así:

| Bias LLM / momento cognitivo | Modo correspondiente |
|------------------------------|---------------------|
| Anchor bias, pattern matching | **Divergente** |
| Availability heuristic, miopía | **Estratega** |
| Confirmation bias, optimismo | **Devil's Advocate** |
| Analysis paralysis, indecisión | **Consolidador** |
| Drift, distracción | **Ejecutor** |
| Hallucination, overconfidence | **Verificador** |
| No reflection, no learning | **Auditor** |

Cubre el ciclo: *explorar → criticar → decidir → ejecutar → verificar → reflexionar*.

---

## 4. Las 5 fases: por qué estas

Escogimos fases **genéricas** sobre fases específicas de un caso de uso (Lead/Propuesta/…) por 3 razones:

1. **Portabilidad**: funcionan para desarrollo software, consultoría, contenido, formación.
2. **Audiencia mixta**: el mismo framework sirve a operador avanzado, alumno de formación corporativa y cliente B2B.
3. **Mapping fácil**: los perfiles mapean fases genéricas a workflows específicos (ver `profiles/*.yaml`).

### Transiciones válidas

```
Discovery ─┬→ Planning ──→ Execution ──→ Review ──→ Shipping
           │                    ↑              │
           └────────┐      ┌────┴──┐      ┌───┘
                    ↓      ↓       ↓      ↓
                 (cualquier fase puede volver a Discovery si aparece sorpresa)
```

Cognito permite cualquier transición. No es un workflow rígido.

---

## 5. Activación híbrida: por qué

### Alternativas evaluadas

| Opción | Pros | Contras |
|--------|------|---------|
| Solo slash commands | Control total | Fricción, olvido |
| Solo estado persistente | Un comando y listo | Cambios cuestan, poco ágil |
| Solo hooks auto-detect | Fluido | Impredecible, difícil debuggear |
| **Híbrido (elegido)** | Flexible + controlado | Más piezas |

### Decisión final

- **Estado persistente** en `_phase-state.json` → la fase del proyecto (persiste entre sesiones).
- **Slash commands** (`/fase`, `/modo`) → cambios explícitos con feedback visible.
- **Hook sugerente** (no auto-aplicar) → detecta señales, sugiere cambio, tú confirmas con un sí/no.

La clave es: **la auto-detección sugiere, nunca decide**. El usuario mantiene agencia.

---

## 6. Determinismo selectivo

### Cuándo usar hook determinista

- **Gate crítico**: donde un error es caro (deploy, PII, compliance).
- **Convención no-negociable**: "nunca n8n", "RLS obligatorio".
- **Detección de señales**: entrada estructurada que requiere clasificación.
- **Log de estado**: registro inmutable de decisiones tomadas.

### Cuándo usar plantilla fija

- **Output estructurado** que debe mantener formato: matriz decisión, pre-mortem, checklist.
- Claude rellena valores, no altera estructura.

### Cuándo dejar libre

- **Ideación**, divergencia.
- **Análisis profundo** donde variedad añade valor.
- **Síntesis creativa** que no se beneficia de plantilla.

### Los 4 hooks de Cognito

| Hook | Evento | Función | Editable por el usuario |
|------|--------|---------|-------------------------|
| `phase-detector.sh` | UserPromptSubmit | Detecta señales de cambio de fase y propone (word-boundary regex desde v1.1) | Sí (reglas en `_passive-triggers.json`) |
| `mode-injector.sh` | **UserPromptSubmit** (desde v1.1; pre-1.1 usaba PreToolUse) | Inyecta instrucciones del modo activo como systemMessage, una vez por turno | No (lógica fija) |
| `gate-validator.sh` | PreToolUse Write/Edit | Valida anti-patrones antes de escribir | Sí (reglas en `_passive-triggers.json → gates`) |
| `session-closer.sh` | Stop | Cuenta métricas filtradas por session_id y rota logs a `logs/archive/` (desde v1.1) | No (lógica fija) |

---

## 7. Cómo se integra con Sinapsis y el resto del ecosistema

### Separación de responsabilidades

| Sistema | Responsabilidad |
|---------|-----------------|
| **Sinapsis** | Aprendizaje continuo: observar, aprender reglas, inyectar como instincts |
| **Cognito** | Orquestación cognitiva: modos de pensamiento según fase |
| **Skill Router** | Instalación y descubrimiento de skills |
| **Skills personales** del operador | Ejecución de tareas específicas del dominio |

### Interacción

1. Sinapsis aprende que "cuando el operador edita `.env` debe recordarse que no se commitea" → genera instinct.
2. Cognito, en fase Execution con modo Ejecutor, ve ese instinct y lo incorpora al checklist.
3. Gate-validator de Cognito bloquea `git add .env` con el razonamiento del instinct.

Cognito **consume** pero no modifica el sistema Sinapsis.

### No conflict

- Cognito usa su propio namespace `_cognito-*` en los archivos.
- Sus hooks viven en `cognito/hooks/`, no en `~/.claude/hooks/` (global).
- Se registran en settings.json con nombre explícito `cognito-*`.

---

## 8. Los 4 perfiles: diseño multi-audiencia

```yaml
# operator.yaml
profile: operator
audience: "Founder/consultor con Claude Code avanzado"
assumes:
  - Sinapsis instalado
  - skills del operador presentes
  - Lenguaje técnico denso
installs:
  modes: [divergente, verificador, devils-advocate, consolidador, ejecutor, estratega, auditor]
  hooks: all
  gates: [n8n, rls-supabase, operator-pricing-check, eu-ai-act]
  templates: all
```

```yaml
# alumno.yaml
profile: alumno
audience: "Alumno curso corporate training programs o similar"
assumes:
  - Claude Code recién instalado
  - Sin Sinapsis
  - Necesita explicaciones
installs:
  modes: [divergente, verificador, consolidador, ejecutor]  # MVP pedagógico
  hooks: [mode-injector, gate-validator]
  gates: [generic-best-practices]
  templates: [matriz-decision, checklist-deploy]
  extras:
    - onboarding-tutorial.md
    - glosario-modos.md
```

```yaml
# public.yaml
profile: public
audience: "Open source, genérico"
assumes:
  - Sin contexto del operador
  - Inglés y español
  - Portabilidad máxima
installs:
  modes: all
  hooks: [mode-injector, session-closer]  # sin gate-validator (gates son específicos)
  gates: []
  templates: all
strips:
  - referencias a operator
  - tarifas específicas
  - marcas
```

```yaml
# client.yaml
profile: client
audience: "cliente B2B en transformación digital"
assumes:
  - Stack heterogéneo
  - Necesita documentación
  - Proyectos de 3-12 meses
installs:
  modes: [divergente, devils-advocate, consolidador, ejecutor, auditor]
  hooks: [phase-detector, mode-injector, gate-validator, session-closer]
  gates: [client-specific-from-intake]  # configurables en onboarding
  templates: all + client-reporting.md
```

---

## 9. Versionado

Semver por componente:

- Sistema global: `MAJOR.MINOR.PATCH` en `CHANGELOG.md`.
- Cada modo: versión propia en `modes/<name>/SKILL.md` frontmatter.
- Cada hook: versión propia en cabecera del script.

**MAJOR** = cambio de arquitectura (añadir/quitar modo, cambiar fases, cambiar formato de estado).
**MINOR** = nuevo template, nuevo perfil, nueva regla de gate.
**PATCH** = fix en hook, mejora en prompt de un modo.

---

## 10. Decisiones rechazadas (por si alguien las reabre)

### ❌ Agente único que cambia de rol

Rechazado porque: pérdida de determinismo, rol ambiguo, difícil debuggear qué modo estaba activo cuando algo falló.

### ❌ Fases específicas del operador como default

Rechazado porque: baja portabilidad. Las fases específicas quedan en `profiles/operator.yaml → mapping`.

### ❌ Auto-cambio de fase por detección

Rechazado porque: LLM pierde agencia del usuario. La detección sugiere, no aplica.

### ❌ Hook MCP en lugar de bash

Rechazado porque: dependencia externa (servidor MCP) añade fragilidad. Bash/Python son locales.

### ❌ Un único SKILL.md gigante

Rechazado porque: imposible de customizar por audiencia. Modularidad en `modes/` es clave.

---

## 11. Roadmap

### v1.0 (actual)

- 7 modos + 5 fases + 4 hooks + 4 perfiles.
- Instalación manual.
- Dashboard `/cognition-status`.

### v1.1

- Installer CLI `./scripts/install.sh --profile=X`.
- Tests automatizados por hook.

### v1.2

- Integración con Sinapsis (modo Ejecutor consume instincts activos).
- Métricas: qué modos/fases se usan más.

### v2.0

- Modos custom por usuario (`modes/custom/` + registro en `_modes.json`).
- Marketplace público en GitHub (como Skills Marketplace en roadmap de Luis).

---

## 12. Anti-patrones conocidos

### Activar todos los modos siempre

Consume contexto, ralentiza. Usar fases como filtro natural.

### Gates demasiado agresivos

Bloquear edición de `package.json` por "seguridad" es contraproducente. Gates = anti-patrones, no preferencias.

### Copiar-pegar entre perfiles

Si una regla aparece en 3+ perfiles, subirla al core. Si solo en 1, dejarla en el perfil.

### Modos sin disparador claro

Cada modo debe tener trigger detectable (verbalización + contexto). Si no, se convierte en ruido.

---

## 13. Known limitations (v1.1)

v1.1.0 was the "Honest Release" — it closes the gap between the docs and the runtime. These limitations remain and are flagged for the v1.2 / v2.0 roadmap:

### Mode taxonomy has overlap

The 7 modes were designed from a catalogue of LLM biases, but in practice some pairs converge:

- **Estratega** adds "time-horizon shift" and "stakeholder perspective" to the marcos catalogue. Both already appear as marcos H and I inside **Divergente**. Realistically they are one mode with two presets.
- **Devil's Advocate** (pre-mortem) and **Auditor** (post-mortem) share the same template structure, changing only tense. Realistically one mode with a pre/post modifier.

We kept the 7-mode API intact in v1.1 to avoid breaking skills/commands. v2.0 is the right moment to collapse.

### "Determinismo selectivo" only applies to one hook

Only `gate-validator.sh` implements a true block/allow gate. The other three hooks are:

- `phase-detector.sh` — word-boundary regex suggestion, never forces.
- `mode-injector.sh` — file concatenation with a size budget.
- `session-closer.sh` — log partitioning and rotation, no runtime decision.

The framing was overstated pre-v1.1. Useful orchestration, not a decision framework.

### Phases × modes has three sources of truth

The binding "phase X defaults to modes Y,Z" lives in three places that can drift apart:

- `config/_phases.json → phases.<id>.defaultModes`
- `config/_modes.json → modes.<id>.defaultPhases`
- mode frontmatter in `modes/<id>/SKILL.md`

There is no generator or test that enforces agreement today. v2.0 plans to collapse these into one source and generate the others.

### PII gate (`no-hardcode-pii`) is narrow

The default regex catches `const email = "foo@bar.com"` but misses JSON (`"email": "..."`), object shorthand, Python dicts without quotes, and most variants that are not literal `=` assignment. It is best-effort protection, not a compliance boundary. See [SECURITY.md → Known limitations](SECURITY.md). v1.2 plans to invoke `gitleaks` as a subprocess when available.

### `hookIntensity` is dead configuration

`_phases.json` declares per-phase `hookIntensity` (`low/medium/high`). No hook reads it. Kept for API stability; will be removed or wired up in v2.0.
