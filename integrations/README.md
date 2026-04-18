# Cognito — Integraciones opcionales

Cognito funciona **standalone por defecto**. Las integraciones de este directorio son **opt-in, auto-detectadas** y degradan silenciosamente si el otro sistema no está instalado.

## Filosofía

1. **Cero acoplamiento duro**: Cognito nunca `import`-a código de otro sistema. Lee su estado vía filesystem (archivos JSON públicos).
2. **Auto-detect**: buscamos en rutas convencionales; si no está, seguimos adelante.
3. **Opt-out explícito**: en `config/_operator-config.json → integrations.<nombre>.installed = false` el operador puede desactivar aunque esté instalado.
4. **Tolerancia a versiones**: si el schema del otro sistema cambia, fallamos silencioso, no crasheamos.

---

## Sinapsis Bridge

**Archivo**: [sinapsis_bridge.py](sinapsis_bridge.py)

**Qué aporta**:

- El modo **Ejecutor** y **Verificador** pueden consultar los *instincts confirmed/permanent* que Sinapsis ha aprendido.
- Esos instincts se inyectan como contexto al `systemMessage` durante `mode-injector.sh`.
- El modo **Auditor** propone nuevos instincts de Sinapsis como candidatos al terminar una sesión Review.
- `/cognition-status` muestra si el bridge está activo y cuántos instincts hay disponibles.

**Detección (en este orden)**:

1. Path explícito pasado al constructor (`SinapsisBridge.detect(explicit_path=...)`).
2. `_operator-config.json → integrations.sinapsis.path`.
3. Variable de entorno `SINAPSIS_DIR`.
4. Rutas candidatas:
   - `~/.claude/skills/sinapsis-learning`
   - `~/.claude/skills/sinapsis`
   - `~/.sinapsis`
   - `~/sinapsis`

Un directorio se considera Sinapsis si contiene alguno de: `_instincts-index.json`, `instincts/`, `_passive-rules.json`, o un `SKILL.md`.

**Formatos soportados**:
El bridge es tolerante a variantes del schema:

- `_instincts-index.json` puede ser `{"instincts": [...]}`, `{"items": [...]}`, `{"id1": {...}, ...}` o una lista directa.
- Cada instinct puede tener `confidence` en `{draft, quarantine, confirmed, permanent}`. Solo `confirmed` y `permanent` se consumen.
- Campos esperados: `rule` o `body` o `description` (al menos uno), `scope` (opcional), `occurrences` (opcional, para ordenar).

**Verificación manual**:

```bash
# Probar que detecta Sinapsis (o que degrada limpio si no)
python3 integrations/sinapsis_bridge.py --status

# Ver el bloque que se inyectaría al contexto
python3 integrations/sinapsis_bridge.py --inject

# Override de path
python3 integrations/sinapsis_bridge.py --path ~/custom-sinapsis --status
```

**Desactivar aunque esté instalado**:

Edita `config/_operator-config.json`:

```json
{
  "integrations": {
    "sinapsis": {
      "installed": false
    }
  }
}
```

---

## Añadir una nueva integración

Template:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FooBridge:
    root: Path | None = None
    available: bool = False

    @classmethod
    def detect(cls, ...) -> "FooBridge":
        # 1. Recolectar candidates (explicit, env, convención)
        # 2. Para cada uno, comprobar heurística de "parece Foo"
        # 3. Si no, retornar instance con available=False
        ...

    def get_<lo_que_aporta>(self) -> ...:
        if not self.available:
            return []  # Degrada silencioso
        ...

    def render_injection(self) -> str:
        if not self.available:
            return ""  # Cognito no inyecta nada
        return "..."  # Bloque markdown a añadir
```

**Reglas**:

- Siempre retornar estructura vacía (no excepción) si `not available`.
- Siempre usar `OSError`/`json.JSONDecodeError` como recuperables.
- Documentar en este README qué aporta al sistema.
- Añadir tests en `tests/unit/test_integration_<nombre>.py`.

---

## Futuras integraciones (ideas)

- **obsidian-sync**: si el operador tiene vault Obsidian configurado, sincronizar decisiones de Cognito a notas.
- **skill-router**: si está instalado, exponer los modos de Cognito al router para instalación on-demand.
- **docusign**: para el modo Ejecutor en fase Shipping de propuestas contractuales.

Cada integración nueva = 1 archivo Python + sección en este README + tests.
