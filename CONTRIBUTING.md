# Contributing to Cognito

¡Gracias por considerar contribuir a Cognito! Este documento explica cómo.

## Filosofía

Cognito es un **sistema cognitivo compartible**. Las contribuciones que más valoramos:

1. **Nuevos modos** bien justificados (sesgo LLM concreto que resuelven).
2. **Mejoras a modos existentes** basadas en uso real.
3. **Nuevos profiles** para audiencias no cubiertas.
4. **Tests adicionales** que capturen casos edge.
5. **Traducciones** de SKILL.md, commands y templates.

## Antes de empezar

1. Lee [README.md](README.md) y [ARCHITECTURE.md](ARCHITECTURE.md).
2. Verifica que tu idea no esté ya en [CHANGELOG.md → Roadmap](CHANGELOG.md).
3. Abre un issue describiendo lo que quieres hacer (opcional para cambios pequeños).

## Setup de desarrollo

```bash
# Clonar fork
git clone https://github.com/TUUSUARIO/cognito.git
cd cognito

# Crear entorno Python
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements-test.txt

# Correr tests
bash tests/run_tests.sh
```

## Flujo de contribución

1. **Fork** el repo.
2. Crea una rama: `git checkout -b feat/mi-feature` o `fix/mi-fix`.
3. Haz cambios con commits pequeños y descriptivos (convención [conventional commits](https://www.conventionalcommits.org/)).
4. **Añade tests** para tu cambio.
5. Corre todos los tests: `bash tests/run_tests.sh`.
6. Actualiza `CHANGELOG.md` bajo `[Unreleased]`.
7. Abre Pull Request describiendo:
   - Qué problema resuelve.
   - Cómo lo resuelve.
   - Qué tests añadiste.

## Convenciones

### Commits
Prefijos:
- `feat:` nueva funcionalidad
- `fix:` bug fix
- `docs:` solo documentación
- `test:` solo tests
- `refactor:` cambio interno sin efecto externo
- `chore:` infraestructura, CI, deps

### Código
- **Bash hooks**: `set -euo pipefail`, shebang `#!/usr/bin/env bash`, Python helpers inline cuando jq no basta.
- **Python tests**: pytest, nombres `test_<qué>`, fixtures en `conftest.py`.
- **SKILL.md**: frontmatter válido, nombres con prefijo `cognito-`, triggers claros.
- **Templates**: plantilla fija, secciones mínimas definidas.
- **Naming**: kebab-case en archivos y directorios, snake_case en Python, camelCase en JSON.

### Añadir un nuevo modo

1. Crear `modes/<nombre>/SKILL.md` con frontmatter completo.
2. Registrar en `config/_modes.json`:
   ```json
   "nombre": {
     "displayName": "...",
     "description": "...",
     "skillPath": "modes/nombre/SKILL.md",
     "determinism": "low|medium|high",
     "triggers": { ... },
     "defaultPhases": [...]
   }
   ```
3. Si toca defaults de alguna fase, añadir a `config/_phases.json → phases.<fase>.defaultModes`.
4. Crear command atajo en `commands/<nombre>.md`.
5. Si necesita plantilla, crearla en `templates/<nombre>.md`.
6. **Añadir tests** en `tests/unit/` validando:
   - El modo aparece en _modes.json.
   - El SKILL.md tiene frontmatter válido.
   - Los triggers disparan en casos conocidos.
7. Actualizar `README.md` (tabla de modos) y `ARCHITECTURE.md` (tabla biases).

### Añadir un nuevo gate

1. Añadir regla en `config/_passive-triggers.json → gates.rules`.
2. Activar en profiles que lo necesiten (`profiles/*.yaml → installs.gates`).
3. Añadir test en `tests/unit/test_gate_validator.py` con caso positivo y negativo.

### Añadir un nuevo profile

1. Crear `profiles/<nombre>.yaml` siguiendo estructura de `operator.yaml`.
2. Documentar en `INSTALL.md`.
3. Actualizar `scripts/install.sh` para soportar `--profile=<nombre>`.

## Code review

Tu PR pasará por review. Busca feedback sobre:
- Consistencia con filosofía de Cognito.
- Claridad del SKILL.md (¿un tercero lo entiende?).
- Cobertura de tests.
- Impacto en profiles existentes.

## Licencia

Al contribuir, aceptas que tu código se distribuye bajo la licencia MIT del proyecto.

## Código de conducta

Sé respetuoso. La crítica debe ser sobre el código, no sobre personas. Ver [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) (si existe) o contactar al mantenedor.

## Contacto

- Issues: GitHub Issues del repo.
- Preguntas técnicas: Discussions del repo.
- Privado: Cognito maintainers, el operador.
