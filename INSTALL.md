# Cognito — Instalación

> **Nota**: Los ejemplos de `git clone` usan `<YOUR_GITHUB_USER>` como placeholder. Reemplázalo por el fork del usuario o por el repo canónico cuando esté publicado.

## Requisitos

- Claude Code CLI instalado.
- Bash disponible (Git Bash en Windows, nativo en macOS/Linux).
- `jq` para manipular JSON (recomendado, no obligatorio).
- Python 3.8+ (opcional, para hooks Python).

---

## Instalación por perfil

Elige el perfil que mejor encaje con tu caso de uso.

### Perfil `operator` — Founder/consultor Claude Code avanzado

**Asume**: Sinapsis instalado, skills personales existentes, lenguaje denso.

```bash
# 1. Clonar
git clone https://github.com/<YOUR_GITHUB_USER>/cognito.git ~/cognito

# 2. Instalar globalmente
cp -r ~/cognito ~/.claude/cognito

# 3. Registrar hooks en settings.json
cat ~/cognito/profiles/operator.hooks.json >> ~/.claude/settings.json
# Edita settings.json y fusiona correctamente (ver ejemplo abajo)

# 4. Registrar commands
cp ~/cognito/commands/*.md ~/.claude/commands/

# 5. Inicializar estado
cp ~/cognito/config/_phase-state.default.json ~/.claude/cognito/config/_phase-state.json

# 6. Verificar
# En una sesión nueva de Claude Code:
/cognition-status
```

### Perfil `alumno` — Alumno de formación corporativa / formación

**Asume**: Claude Code recién instalado, sin Sinapsis, necesita explicaciones.

```bash
git clone https://github.com/<YOUR_GITHUB_USER>/cognito.git ~/cognito
bash ~/cognito/scripts/install.sh --profile=alumno
```

Instala **4 modos pedagógicos** (Divergente, Verificador, Consolidador, Ejecutor) y 2 hooks. Incluye `onboarding-tutorial.md` que Claude lee en la primera sesión para explicar cómo funciona.

### Perfil `public` — Open source / genérico

**Asume**: Sin contexto del operador, portabilidad máxima.

```bash
git clone https://github.com/<YOUR_GITHUB_USER>/cognito.git
cd cognito
./scripts/install.sh --profile=public
```

Instala los 7 modos con lenguaje neutro (sin referencias operator), sin gates específicos.

### Perfil `client` — Cliente B2B

**Asume**: Cliente el operador en proyecto de transformación digital.

```bash
./scripts/install.sh --profile=client --client-intake=./client-intake.json
```

El archivo `client-intake.json` (generado durante onboarding del cliente) configura gates específicos del cliente (stack, compliance, branding).

---

## Instalación manual (si el script no funciona)

### Paso 1: copiar archivos

```bash
# Skills de modos → skills globales
cp -r ~/cognito/modes/* ~/.claude/skills/

# Commands → commands globales
cp ~/cognito/commands/*.md ~/.claude/commands/

# Config en directorio propio de Cognito
mkdir -p ~/.claude/cognito
cp -r ~/cognito/config ~/.claude/cognito/
cp -r ~/cognito/hooks ~/.claude/cognito/
cp -r ~/cognito/templates ~/.claude/cognito/
cp -r ~/cognito/phases ~/.claude/cognito/
cp ~/cognito/SKILL.md ~/.claude/cognito/
```

### Paso 2: registrar hooks en `~/.claude/settings.json`

Añade en la clave `hooks`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "name": "cognito-phase-detector",
        "command": "bash ~/.claude/cognito/hooks/phase-detector.sh",
        "blocking": false
      }
    ],
    "PreToolUse": [
      {
        "name": "cognito-mode-injector",
        "command": "bash ~/.claude/cognito/hooks/mode-injector.sh",
        "blocking": false
      },
      {
        "name": "cognito-gate-validator",
        "command": "bash ~/.claude/cognito/hooks/gate-validator.sh",
        "matchers": {"tool": ["Write", "Edit"]},
        "blocking": true
      }
    ],
    "Stop": [
      {
        "name": "cognito-session-closer",
        "command": "bash ~/.claude/cognito/hooks/session-closer.sh",
        "blocking": false
      }
    ]
  }
}
```

### Paso 3: inicializar estado

```bash
cp ~/.claude/cognito/config/_phase-state.default.json ~/.claude/cognito/config/_phase-state.json
chmod +x ~/.claude/cognito/hooks/*.sh
```

### Paso 4: verificar

Inicia sesión Claude Code, escribe:

```
/cognition-status
```

Deberías ver:

```
╭─ Cognito Status ────────────────────────────╮
│ Perfil: operator                             │
│ Fase actual: discovery                       │
│ Modos activos por defecto: Divergente, Estratega │
│ Hooks registrados: 4/4 ✓                     │
│ Gates activos: n8n, rls-supabase, tarifas    │
│ Última sesión cerrada: 2026-04-15T14:32:00   │
╰──────────────────────────────────────────────╯
```

---

## Desinstalación

```bash
# Borrar commands
rm ~/.claude/commands/{fase,modo,cognition-status,divergir,verificar,devils-advocate,consolidar,ejecutar,estratega,auditar}.md

# Borrar skills de modos
rm -rf ~/.claude/skills/{divergente,verificador,devils-advocate,consolidador,ejecutor,estratega,auditor}

# Borrar directorio Cognito
rm -rf ~/.claude/cognito

# Editar settings.json y quitar los bloques "cognito-*"
```

---

## Troubleshooting

### "/cognition-status no funciona"

- Verifica que `~/.claude/commands/cognition-status.md` existe.
- Cierra y reabre la sesión Claude Code (recarga commands).

### "Los hooks no se disparan"

- Verifica permisos: `chmod +x ~/.claude/cognito/hooks/*.sh`.
- En Windows, usa Git Bash o WSL para ejecutar los `.sh`.
- Revisa `~/.claude/settings.json` — los paths deben ser absolutos.

### "El modo no se activa aunque hago /modo divergente"

- Verifica que `~/.claude/skills/divergente/SKILL.md` existe.
- Verifica que el command `/modo` está leyendo `_phase-state.json`.
- Revisa el log de sesión en `~/.claude/cognito/logs/session-*.log`.

### "Gate bloquea cosas que no debería"

- Edita `~/.claude/cognito/config/_passive-triggers.json → gates`.
- Desactiva gates individuales con `/cognition-gate off <nombre>`.

---

## Actualización

```bash
cd ~/cognito
git pull
bash scripts/update.sh
```

El script `update.sh` respeta customizaciones: solo actualiza archivos core, no tocando los que tengas modificados.

---

## Próximos pasos

- Lee [README.md](README.md) para visión general.
- Lee [ARCHITECTURE.md](ARCHITECTURE.md) para decisiones técnicas.
- Explora `modes/` para entender cada modo.
- Prueba `/fase discovery` + `/divergir` en un problema real.
