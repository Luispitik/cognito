# Cognito — Cognitive Operating System para Claude Code

**Cognito** es un sistema operativo de pensamiento que orquesta **7 modos cognitivos** según **5 fases de proyecto**, con **determinismo selectivo** en los puntos críticos y libertad creativa donde importa.

Nace para corregir dos sesgos conocidos de los LLMs — **efecto ancla** y **convergencia prematura** — y los resuelve no con un único antídoto, sino con una infraestructura que:

1. Activa el modo de pensamiento adecuado a cada momento (divergente, verificador, ejecutor, …).
2. Bloquea anti-patrones con hooks deterministas (como Sinapsis).
3. Deja respirar la creatividad en ideación y análisis.
4. Se configura por perfil de audiencia (operador avanzado, alumno, público, cliente B2B).

Está inspirado en [Sinapsis](https://github.com/Luispitik/sinapsis) (aprendizaje continuo) y extiende el sistema de skills de Claude Code con una capa de orquestación cognitiva.

---

## ¿Qué problema resuelve?

| Síntoma | Causa | Respuesta de Cognito |
|---------|-------|-----------------------|
| Claude acepta tu primera propuesta sin cuestionar | Efecto ancla | **Modo Divergente** + hook anti-ancla en Discovery |
| Claude genera outputs plausibles pero incorrectos | Alucinación / no verifica | **Modo Verificador** activo en Execution |
| Claude se desvía de instrucciones claras | No hay checklist forzado | **Modo Ejecutor** + plantillas rígidas + gate-validator |
| Decides "porque sí" sin comparar alternativas | Falta convergencia explícita | **Modo Consolidador** + matriz decisión obligatoria |
| Entregas algo y luego sale el problema que no viste | No hubo pre-mortem | **Modo Devil's Advocate** en Planning |
| No hay reflexión post-proyecto | Falta ciclo de review | **Modo Auditor** en Review |
| Decides cosas tácticas sin mirar el marco mayor | Miopía estratégica | **Modo Estratega** en Discovery y Planning |

---

## Arquitectura en una frase

> **Fases** (cuándo) × **Modos** (cómo pensar) × **Hooks** (qué es determinista) × **Perfiles** (para quién) = Cognito.

Ver [ARCHITECTURE.md](ARCHITECTURE.md) para decisiones técnicas completas.

---

## Los 7 modos

| Modo | Qué hace | Determinismo | Fases donde aparece por defecto |
|------|----------|--------------|--------------------------------|
| **Divergente** | Anti-ancla, 10 marcos mentales, 5+ alternativas | Bajo | Discovery |
| **Estratega** | Time-horizon, stakeholders, trade-offs macro | Bajo | Discovery, Planning |
| **Devil's Advocate** | Pre-mortem, steel-man del opuesto, crítica | Medio (plantilla) | Planning, Review |
| **Consolidador** | Matriz decisión, síntesis, convergencia | Medio (plantilla) | Planning |
| **Ejecutor** | Checklists rígidas, plantillas fijas | **Alto (hook+plantilla)** | Execution, Shipping |
| **Verificador** | Fact-check, anti-alucinación, validaciones | **Alto (hook gate)** | Execution, Shipping |
| **Auditor** | Post-mortem, QA de outputs, lessons learned | **Alto (hook+plantilla)** | Review |

---

## Las 5 fases

```
Discovery → Planning → Execution → Review → Shipping
    ↑                                           ↓
    └───────────── (nuevo ciclo) ──────────────┘
```

| Fase | Objetivo | Modos activos por defecto |
|------|----------|---------------------------|
| **Discovery** | Entender problema, explorar espacio de soluciones | Divergente + Estratega |
| **Planning** | Decidir qué hacer, anticipar fallos | Devil's Advocate + Consolidador + Estratega |
| **Execution** | Construir sin desviarse, verificar sobre la marcha | Ejecutor + Verificador |
| **Review** | Revisar lo hecho, extraer aprendizajes | Auditor + Devil's Advocate |
| **Shipping** | Entregar con máxima fiabilidad | Ejecutor + Verificador (máximo determinismo) |

Ver [phases/](phases/) para specs detallados.

---

## Activación: híbrido (recomendado)

1. **Estado persistente** de la fase en `.claude/cognito/_phase-state.json`.
2. **Cambio explícito** con `/fase discovery|planning|execution|review|shipping`.
3. **Override puntual** con `/modo divergente|verificador|...` (activa el modo sin cambiar fase).
4. **Sugerencia suave** (no auto-cambio): un hook detecta señales ("vamos a ejecutar", "qué se me escapa") y sugiere cambio; tú confirmas.
5. **Dashboard** con `/cognition-status`.

---

## Determinismo selectivo: dónde sí, dónde no

| Dónde | Qué | Cómo |
|-------|-----|------|
| Anti-patrones críticos | "No uses n8n", "RLS en Supabase", "No hardcodees PII" | **Hook** `gate-validator.sh` (PreToolUse Write/Edit) bloquea y avisa |
| Detección de fase | "vamos a ejecutar", "revisemos lo hecho" | **Hook** `phase-detector.sh` (UserPromptSubmit) sugiere cambio |
| Inyección de modo | Claude necesita instrucciones del modo activo | **Hook** `mode-injector.sh` (PreToolUse) inyecta `systemMessage` |
| Cierre de sesión | Registro de modos usados, decisiones tomadas | **Hook** `session-closer.sh` (Stop) |
| Outputs estructurados | Matriz decisión, checklist, pre-mortem | **Plantilla fija** en `templates/` — Claude rellena, no altera |
| Ideación libre | Divergencia, análisis, creatividad | **No-determinismo** — solo instrucciones prompt |

---

## Integración opcional con Sinapsis

Cognito funciona **standalone por defecto**. Si tienes [Sinapsis](https://github.com/Luispitik/sinapsis) instalado (aprendizaje continuo con instincts), Cognito lo detecta automáticamente y:

- Inyecta instincts `confirmed`/`permanent` al contexto cuando Ejecutor/Verificador/Auditor están activos.
- Muestra el estado del bridge en `/cognition-status` y en el dashboard.
- Nunca rompe si Sinapsis falla: degrada silenciosamente a standalone.

Detalles en [integrations/README.md](integrations/README.md).

---

## Dashboard web

Visualización de actividad sin backend. HTML estático + Tailwind + Chart.js.

```bash
python3 dashboard/api/build_data.py   # genera data.json
bash dashboard/serve.sh                # sirve en localhost:8765
```

Incluye: KPIs (sesiones, modos, gates, detecciones), charts de uso por modo/fase, timeline de 30 días, top gates disparados, tabla de sesiones recientes, estado del bridge Sinapsis.

Demo con datos ficticios:
```bash
python3 dashboard/api/seed_demo.py    # genera 35 sesiones sintéticas
```

Detalles en [dashboard/README.md](dashboard/README.md).

---

## Estructura del directorio

```
cognito/
├── README.md · ARCHITECTURE.md · INSTALL.md · CONTRIBUTING.md · CHANGELOG.md
├── SKILL.md                      ← meta-orquestador
├── config/                       ← 5 JSONs (estado + config)
├── hooks/                        ← 4 scripts deterministas
│   ├── phase-detector.sh         (UserPromptSubmit)
│   ├── mode-injector.sh          (PreToolUse, consume bridge Sinapsis si existe)
│   ├── gate-validator.sh         (PreToolUse Write/Edit)
│   └── session-closer.sh         (Stop)
├── modes/                        ← 7 skills hijas (divergente, verificador, ...)
├── phases/                       ← 5 specs de fase
├── commands/                     ← 10 slash commands
├── templates/                    ← 5 plantillas estructuradas
├── profiles/                     ← 4 YAML por audiencia
├── integrations/                 ← bridges opcionales
│   ├── sinapsis_bridge.py        (auto-detect Sinapsis)
│   └── README.md                 (cómo añadir más integraciones)
├── dashboard/                    ← web estático
│   ├── index.html · app.js · styles.css
│   ├── api/build_data.py         (consolida sessions + logs)
│   ├── api/seed_demo.py          (datos demo)
│   └── serve.sh
├── tests/
│   ├── unit/ (pytest)            ← 180+ tests
│   ├── integration/ (pytest)     ← flows end-to-end
│   ├── bats/hooks.bats           ← 20+ tests cross-shell (CI)
│   └── run_tests.sh
├── scripts/install.sh, uninstall.sh
└── .github/workflows/test.yml    ← CI Ubuntu + macOS × Python 3.10-3.12
```

---

## Instalación rápida

```bash
# 1. Clonar o descargar Cognito
git clone https://github.com/<YOUR_GITHUB_USER>/cognito.git

# 2. Elegir perfil e instalar
cd cognito
./scripts/install.sh --profile=operator     # o alumno, public, client

# 3. Verificar
/cognition-status
```

Ver [INSTALL.md](INSTALL.md) para detalles por perfil.

---

## Filosofía

1. **Pensar mejor no es pensar más, es pensar con el modo correcto en el momento correcto.**
2. **El determinismo es caro y útil: gástalo en las gates críticas, no en la ideación.**
3. **El mejor anti-ancla es un sistema que te obligue a diverger antes de ejecutar.**
4. **Si tu intuición tenía razón, haberla validado contra 5 alternativas la hace más sólida.**
5. **Un sistema compartible es un sistema modular.** Los perfiles separan contexto de sistema.

---

## Créditos

- Concepto anti-ancla: Cognito maintainers (Cognito maintainers).
- Catálogo de marcos: síntesis de Munger, De Bono, TRIZ, SCAMPER, primeros principios.
- Arquitectura deterministas: inspirada en Sinapsis (Luispitik/sinapsis).
- Pattern modos/fases: influenciado por Six Thinking Hats (De Bono) y Sistema 1/2 (Kahneman).

## Licencia

MIT. Forkea, adapta, comparte.
