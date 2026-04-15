# Cognito — Changelog

Versionado semver. Formato inspirado en [keepachangelog.com](https://keepachangelog.com).

---

## [1.0.0] — 2026-04-15

### Añadido
- Arquitectura de 7 modos × 5 fases × 4 hooks × 4 perfiles.
- **7 modos** de pensamiento:
  - Divergente (migrado desde skill anti-ancla original de Luis).
  - Verificador, Devil's Advocate, Consolidador, Ejecutor, Estratega, Auditor (nuevos).
- **5 fases** genéricas: Discovery, Planning, Execution, Review, Shipping.
- **4 hooks deterministas**:
  - `phase-detector.sh` (UserPromptSubmit) — sugiere cambio de fase por señales detectadas.
  - `mode-injector.sh` (PreToolUse) — inyecta instrucciones del modo activo como systemMessage.
  - `gate-validator.sh` (PreToolUse Write/Edit) — bloquea anti-patrones.
  - `session-closer.sh` (Stop) — registra modos y decisiones de la sesión.
- **4 perfiles** YAML: operator, alumno, public, client.
- **10 slash commands**: `/fase`, `/modo`, `/cognition-status`, `/divergir`, `/verificar`, `/devils-advocate`, `/consolidar`, `/ejecutar`, `/estratega`, `/auditar`.
- **5 plantillas** estructuradas: matriz-decision, pre-mortem, steel-man, checklist-deploy, auditoria-output.
- **Bridge opcional con Sinapsis** (`integrations/sinapsis_bridge.py`):
  - Auto-detect en paths convencionales y env var `SINAPSIS_DIR`.
  - Opt-out explícito desde `_operator-config.json`.
  - Lectura tolerante a variantes de schema (dict, list, confidence levels).
  - Modos Ejecutor/Verificador/Auditor reciben instincts confirmed/permanent como contexto.
  - Degrada silenciosamente si Sinapsis no está instalado.
- **Dashboard web** (`dashboard/`):
  - HTML estático + Tailwind CDN + Chart.js + vanilla JS (sin build).
  - KPIs, charts de modos/fases/timeline, breakdown de gates, tabla de sesiones.
  - `build_data.py` consolida `sessions/` + `logs/` + `config/` en `data.json`.
  - `seed_demo.py` genera actividad ficticia para demos.
  - `serve.sh` regenera + sirve en `http://localhost:8765`.
- **Tests bats** (`tests/bats/hooks.bats`):
  - 20+ tests que complementan pytest: syntax, ejecutabilidad, encoding UTF-8, paths con espacios, fallback sin env var, degradación sin config.
  - CI ejecuta en Ubuntu + macOS.
- **Suite de tests**: 201 passing.
- Documentación: README, ARCHITECTURE, INSTALL, CONTRIBUTING + READMEs por submódulo (integrations/, tests/bats/, dashboard/).

### Inspiración
- Skill anti-ancla original de Cognito maintainers (abril 2026).
- Sinapsis v4.3 (Luispitik/sinapsis) — arquitectura de hooks deterministas.
- Six Thinking Hats (Edward de Bono).
- Sistema 1/Sistema 2 (Kahneman).

---

## [Próximas versiones — Roadmap]

### [1.1.0] — planned
- Installer CLI (`./scripts/install.sh --profile=X`).
- Tests automatizados por hook.
- Actualización no-destructiva (`./scripts/update.sh` respeta customizaciones).

### [1.2.0] — planned
- Integración con Sinapsis: Modo Ejecutor consume instincts activos del sistema de aprendizaje.
- Métricas de uso: `/cognition-metrics` muestra qué modos/fases se usan más.
- Auto-promote de instincts a gates cuando umbral de ocurrencias se supera.

### [2.0.0] — planned
- Modos custom por usuario en `modes/custom/`.
- Marketplace público en GitHub con registro de modos y perfiles de la comunidad.
- Semver por modo (cada modo tiene su versión, permite actualizaciones granulares).
