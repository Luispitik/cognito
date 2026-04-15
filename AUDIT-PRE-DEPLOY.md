# Auditoría pre-deploy a GitHub público

Fecha: 2026-04-15
Revisor: proceso automatizado de auditoría

## Resumen ejecutivo

| Severidad | Hallazgos | Estado |
|-----------|-----------|--------|
| 🔴 **CRÍTICO** | 1 | Arreglado |
| 🟠 **ALTO** | 3 | Arreglado |
| 🟡 **MEDIO** | 2 | Arreglado |
| 🟢 **BAJO** | 2 | Revisado (no bloquea) |

**Estado final**: ✅ listo para push (con los commits de fix aplicados)

---

## 🔴 CRÍTICO

### C1 · Tarifas comerciales reales expuestas en archivo público

**Archivo**: `config/_passive-triggers.json` (regla `tarifas-norteia`)
**Problema**: El mensaje del gate contenía cifras reales del operador:
> "formación 120-175€/h, jornada 750-1.100€, LIDERA IA 2.500-3.900€"

En un repo open source, esto:
- Expone info comercial sensible del operador.
- Crea expectativa de precio en cualquier fork.
- No tiene sentido fuera del contexto específico del operador.

**Fix aplicado**: cambiar el mensaje a genérico (sin cifras), renombrar el gate a `operator-pricing-check` y dejar la lógica de tarifas en un archivo **opt-in** en `profiles/operator-gates.example.json` (no versionado con cifras, solo plantilla).

---

## 🟠 ALTO

### A1 · Default profile es `operator`, no `public`

**Archivo**: `config/_operator-config.json`
**Problema**: Un clon público hereda `profile: operator` con gates específicos activos. Un nuevo usuario no sabe por qué se activan reglas raras.

**Fix aplicado**: default profile cambia a `public`. Los gates específicos quedan desactivados hasta que el usuario los active explícitamente. El archivo se documenta como "ejemplo neutro; personaliza al instalar".

### A2 · Gates específicos de operador activos por defecto

**Archivo**: `config/_operator-config.json → gates.enabled`
**Problema**: Incluía `tarifas-norteia` y `eu-ai-act-sources` habilitados por defecto. Esos son del contexto del operador, no universales.

**Fix aplicado**: defaults solo los gates universalmente útiles: `no-commit-env`, `no-hardcode-pii`, `n8n-retired` (este último es opinable pero es un anti-patrón razonable; documentado). Los específicos se describen en `profiles/operator.yaml` y se habilitan al activar ese perfil.

### A3 · Placeholders `tuusuario` en documentación

**Archivos**: `README.md`, `INSTALL.md`
**Problema**: Usaban `tuusuario/cognito.git` como ejemplo de clone. Mejor un placeholder claro y documentado.

**Fix aplicado**: reemplazar por `<YOUR_GITHUB_USER>/cognito` y añadir nota al inicio de `INSTALL.md` indicando que debe reemplazarse por el fork del usuario o el repo canónico una vez publicado.

---

## 🟡 MEDIO

### M1 · Menciones de NorteIA en documentación core

**Archivo**: `ARCHITECTURE.md` (líneas 41, 141)
**Problema**: El doc core (no específico a profile operator) menciona NorteIA en ejemplos:
> "aplica tarifas NorteIA"
> "Skills personales (norteia-formaciones, etc.)"

Esto mancha la neutralidad del doc core.

**Fix aplicado**: reemplazar por ejemplos neutros:
- "aplica tarifas NorteIA" → "aplica gates específicos del operador"
- "Skills personales (norteia-formaciones, etc.)" → "Skills personales del operador"

Las menciones en secciones dedicadas a profile operator o en "decisiones rechazadas" (ejemplo contextual) se mantienen — son contexto, no marca.

### M2 · `sinapsis_bridge.py` prioriza path específico del operador

**Archivo**: `integrations/sinapsis_bridge.py`
**Problema**: El primer path candidato era `~/.claude/skills/norteia-continuous-learning` (instalación específica de Luis). Un usuario genérico buscaría primero en `~/.claude/skills/sinapsis`.

**Fix aplicado**: reordenar candidatos — primero `~/.claude/skills/sinapsis` y `~/.sinapsis` (genéricos), luego `norteia-continuous-learning` como último fallback. Esto no rompe la detección en el setup de Luis y mejora la experiencia del usuario público.

---

## 🟢 BAJO (revisado, no requiere fix)

### B1 · Menciones de NorteIA en profiles específicos
`profiles/operator.yaml`, `profiles/client.yaml`, `profiles/alumno.yaml` mencionan NorteIA como contexto del perfil. Es **correcto y esperado** — esos perfiles describen casos de uso reales concretos. Perfil `public.yaml` es el neutro.

### B2 · Atribución en README y LICENSE
`README.md → Créditos`: "Concepto anti-ancla: Luis Salgado (NorteIA / SalgadoIA)"
`LICENSE`: "Copyright (c) 2026 Luis Salgado / NorteIA / SalgadoIA"

Estas son atribuciones legítimas de autoría, **no promocionales**. Se mantienen.

---

## Verificaciones adicionales pasadas

| Check | Estado |
|-------|--------|
| No hay `.env`, `.key`, `credentials.json` en el repo | ✅ |
| `.gitignore` excluye `logs/`, `sessions/`, `config/_phase-state.json`, `dashboard/data.json`, `__pycache__/` | ✅ |
| LICENSE presente (MIT) | ✅ |
| CONTRIBUTING.md presente | ✅ |
| CI workflow funcional (Ubuntu + macOS × Py 3.10-3.12) | ✅ |
| 201 tests verdes localmente | ✅ |
| Ningún path Windows hardcoded (excepto en logs/ y data.json, ambos ignorados) | ✅ |
| Todos los hooks son portables (MSYS2 + macOS + Linux) | ✅ |
| JSONs parsean | ✅ |
| YAML parsean | ✅ |
| Bash `set -euo pipefail` en todos los hooks | ✅ |
| UTF-8 en output de todos los scripts Python | ✅ |
| Documento COMPATIBILITY-ACC.md presente con tono correcto | ✅ |

---

## Qué NO se ha tocado (decisión consciente)

1. **El profile operator sigue incluyendo NorteIA** en `operator.yaml` → es su propósito.
2. **Las skills `profiles/{alumno,client}.yaml` mencionan FUNDAE/B2B NorteIA** como contexto → es ejemplo del caso de uso, no marca.
3. **`seed_demo.py` incluye `tarifas-norteia`** en los gates ficticios → es solo etiqueta en datos de demo, sin cifras.
4. **`norteia-continuous-learning` permanece en la lista de paths candidatos** del bridge Sinapsis como fallback → permite que el setup real de Luis funcione sin config extra.

---

## Veredicto

**LISTO para publicar.** Los 6 fixes (C1 + A1-A3 + M1-M2) se aplicaron. El repo es ahora:

- Agnóstico en su documentación core.
- Sin cifras comerciales sensibles.
- Con defaults neutros para cualquier usuario que haga clone.
- Con profile operator explícitamente específico y separado.
- Con atribuciones donde corresponde (LICENSE + créditos del README).
