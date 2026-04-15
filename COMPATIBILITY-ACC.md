# Cognito × ACC Core Skills — Compatibilidad

Este documento mapea la relación entre **Cognito** y [ACC Core Skills](https://github.com/ricautomation/acc_core_skills).

## Qué es esta relación

ACC Core Skills **no es inspiración** de Cognito. Son **dos proyectos desarrollados de forma independiente** que, al converger, resultaron tener filosofía muy cercana:

- **Cognito** nace de una skill anti-ancla personal + la arquitectura de hooks de [Sinapsis](https://github.com/Luispitik/sinapsis).
- **ACC Core Skills** nace de un enfoque de "cognitive architecture" modular para LLMs genéricos.

Convergieron por llegar al mismo principio: **la calidad del razonamiento mejora cuando el sistema cognitivo es modular, explícito y componible**.

Los llamamos **primos ideológicos**.

## Diferencia de scope

|  | ACC Core Skills | Cognito |
|---|----------------|----------|
| **Nivel** | Librería de módulos prompt-level | Sistema operativo cognitivo completo |
| **Target** | Cualquier LLM (Claude/Gemini/MiniMax) | Claude Code nativo |
| **Unidad** | Módulo cognitivo (`core-X.md`) | Modo (`modes/X/SKILL.md`) + Fase (`phases/X.md`) |
| **Activación** | Inyección manual en prompt | Hooks deterministas + estado persistente |
| **Estado** | Sin estado entre sesiones | `_phase-state.json`, `sessions/`, `logs/` |
| **Ejecución** | Puramente prompt | Prompt + bash hooks + Python |
| **Entregables** | Módulos en `references/*.md` | Modos + plantillas + commands + dashboard + bridge |

**Analogía**: ACC Core Skills es a Cognito lo que **POSIX** es a **Linux**. ACC define principios universales transferibles; Cognito realiza esos principios en un entorno concreto con toda la infraestructura que implica.

## Mapeo módulos ACC ↔ modos Cognito

| Módulo ACC | Modo o componente Cognito equivalente |
|-----------|---------------------------------------|
| `core-zero-hallucination` | **Modo Verificador** (`modes/verificador/`) |
| `core-ockham` | **Modo Consolidador** (navaja de decisión en la matriz) |
| `core-elicitation` | Fase **Discovery** — elicitación antes de cerrar |
| `core-state-vector` | `config/_phase-state.json` + estructura de fases |
| `reasoning-causal-chain` | **Modo Devil's Advocate** — pre-mortem con cadena causal |
| `reasoning-hypothesis-first` | **Modo Divergente** — "asunción fundacional" (Fase 1.2) |
| `reasoning-constraint-map` | Marco B del Divergente (Constraint shock) — `modes/divergente/references/marcos.md` |
| `output-density-max` | **Modo Ejecutor** — plantillas rígidas en `templates/checklist-deploy.md` |
| `output-uncertainty-map` | **Modo Auditor** — tabla de calidad del output en `templates/auditoria-output.md` |

Solapamiento conceptual estimado: **~80%**.

## Lo que Cognito añade por encima de ACC

Elementos que no existen en ACC y son específicos de la capa "OS":

1. **Fases del proyecto** (Discovery → Planning → Execution → Review → Shipping) como eje temporal que gobierna qué módulos están activos.
2. **Hooks deterministas** (`phase-detector.sh`, `mode-injector.sh`, `gate-validator.sh`, `session-closer.sh`) que imponen el determinismo selectivo antes/después de cada acción de Claude.
3. **Gates de anti-patrones** (`_passive-triggers.json`) que bloquean acciones concretas — un escalón por debajo del prompt.
4. **Estado persistente** entre sesiones (`sessions/*.json` + `config/_phase-state.json`).
5. **Perfiles multi-audiencia** (`profiles/*.yaml`) para adaptarse a operador avanzado / alumno / público / cliente.
6. **Integración opcional con Sinapsis** — bridge para aprendizaje continuo.
7. **Dashboard web** para visualizar uso y métricas.

## Lo que ACC hace mejor que Cognito (por diseño)

1. **Portabilidad a otros LLMs**: Cognito solo funciona en Claude Code. ACC funciona en cualquier chat LLM.
2. **Minimalismo**: ACC es librería pura. Cognito trae carga operativa (bash, Python, tests, CI).
3. **Granularidad**: un módulo ACC es una unidad más atómica que un modo Cognito. Se componen más libremente.
4. **Formalidad**: ACC especifica protocolos de verificación explícitos (state-vector, hypothesis-first). Cognito los delega al prompt del modo.

## ¿Son complementarios?

Sí. Un operador puede:

- Usar **solo ACC** si trabaja con varios LLMs y quiere módulos cognitivos puros (peso mínimo).
- Usar **solo Cognito** si trabaja en Claude Code y quiere orquestación completa con estado.
- Usar **ambos** en Claude Code: Cognito orquesta fases y hooks; dentro de un modo concreto puede cargar un módulo ACC específico como plantilla de referencia.

## Intenciones cruzadas

- Cognito **no pretende sustituir** ACC ni ser parte de su repo. Son productos con peso y scope distintos.
- Cognito **sí puede contribuir** módulos atómicos a ACC donde encaje (p.ej., un `reasoning-divergent-frames.md` extraído del catálogo de 10 marcos del modo Divergente, si los mantenedores de ACC lo quieren).
- ACC se cita aquí por honestidad intelectual: alguien familiarizado con ACC reconocerá el aire de familia y merece saber cómo se relacionan los conceptos.

## Atribuciones

- **Cognito**: Cognito maintainers · [Luispitik/cognito](https://github.com/Luispitik/cognito) · MIT
- **ACC Core Skills**: `ricautomation` · [ricautomation/acc_core_skills](https://github.com/ricautomation/acc_core_skills) · MIT
- **Sinapsis** (base arquitectónica de los hooks de Cognito): Cognito maintainers · [Luispitik/sinapsis](https://github.com/Luispitik/sinapsis) · MIT

## FAQ

**¿Por qué no fusionar Cognito con ACC?**
Porque son productos con scope distinto. ACC es una librería minimalista; Cognito trae infraestructura operativa (hooks, dashboard, tests, CI) que desbordaría la filosofía de ACC.

**¿Puedo usar módulos ACC dentro de un modo Cognito?**
Sí. Un `SKILL.md` de modo Cognito puede referenciar un módulo ACC en su sección de "references". No hay acoplamiento técnico: Cognito lee markdown, igual que ACC.

**¿Van a evolucionar juntos?**
Cada proyecto tiene su propio roadmap. Sincronizar no es objetivo. Si aparecen divergencias, este documento documenta el punto de encuentro en el tiempo, no un compromiso futuro.
