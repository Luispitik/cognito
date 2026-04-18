# Cognito — Installation

> Canonical repo: [github.com/Luispitik/cognito](https://github.com/Luispitik/cognito). Replace with your fork URL if you are working from a fork.

## Requirements

- **Claude Code CLI** installed.
- **Bash** (Git Bash on Windows, native on macOS / Linux).
- **Python 3.10+** — hard requirement. Hooks and the install script spawn `python3` and rely on PEP 604 syntax. On Windows, use Python from python.org and make sure `python3` is on `PATH` (not just `python`).
- **jq** — strongly recommended. Enables automatic hook registration in `~/.claude/settings.json`. Without jq, install prints a paste-ready snippet you can merge manually.

## Install in one line

Pick the profile that matches your context:

```bash
# Clone
git clone https://github.com/Luispitik/cognito.git ~/cognito
cd ~/cognito

# Choose a profile
bash scripts/install.sh --profile=operator   # founder / advanced operator
bash scripts/install.sh --profile=alumno     # pedagogical MVP (4 modes)
bash scripts/install.sh --profile=public     # open-source, generic
bash scripts/install.sh --profile=client --client-intake=./client-intake.json
```

`install.sh` will:

1. Validate your profile and Python version.
2. Parse `profiles/<profile>.yaml` and copy only the modes, hooks, gates and templates listed there.
3. Install mode skills to `~/.claude/skills/` and slash commands to `~/.claude/commands/`.
4. Seed `~/.claude/cognito/` with the chosen profile's config.
5. Merge hook registrations into `~/.claude/settings.json` using `jq` (or print the snippet if jq is absent).
6. Back up any existing install into `~/.claude/cognito-backups/<timestamp>/` and preserve your `_phase-state.json`.

Then open a new Claude Code session and run `/cognition-status`.

## What each profile installs

| Profile | Modes | Hooks | Gates |
|---|---|---|---|
| `operator` | 7 | 4 (phase-detector, mode-injector, gate-validator, session-closer) | 6 (incl. `no-commit-env`, `rls-supabase-required`, `eu-ai-act-sources`) |
| `alumno` | 4 (Divergente, Verificador, Consolidador, Ejecutor) | 2 (mode-injector, gate-validator) | 2 (`generic-best-practices`, `no-commit-env`) |
| `public` | 7 | 2 (mode-injector, session-closer) | 0 (user defines their own) |
| `client` | 5 | 4 | configurable via `--client-intake=FILE` |

See the YAML under `profiles/<name>.yaml` for the authoritative list; `install.sh` parses them at runtime.

## Install options

```
--profile=NAME           operator | alumno | public | client   (required)
--target=PATH            install dir (default: ~/.claude/cognito)
--settings=PATH          settings.json to modify (default: ~/.claude/settings.json)
--skip-settings          do not touch settings.json; print the snippet instead
--client-intake=PATH     intake JSON (only for --profile=client)
```

## Verify

```bash
# Re-open Claude Code, then:
/cognition-status
/cognition-status --verify   # health check (v1.1+)
```

A healthy install reports:

```
Cognito status
  profile : operator
  phase   : discovery
  modes   : 7 installed, 2 default-active in this phase
  hooks   : 4/4 registered
  gates   : 6 enabled, 0 disabled
  bridge  : Sinapsis available v4.3
```

## Update

```bash
cd ~/cognito
git pull
bash scripts/update.sh              # non-destructive refresh
bash scripts/update.sh --dry-run    # preview changes
```

`update.sh` refreshes hooks, templates, phases, `SKILL.md` and the Sinapsis bridge from the repo. It **never** touches your `_phase-state.json`, `_operator-config.json`, `logs/`, or `sessions/`.

## Uninstall

```bash
bash scripts/uninstall.sh
# or
bash scripts/uninstall.sh --yes --target=~/.claude/cognito
```

`uninstall.sh` removes the install directory, the 10 Cognito slash commands, the 7 mode skills, and — when jq is available — strips every `cognito-*` entry from `~/.claude/settings.json`.

## Manual installation (no script)

If you prefer not to run the installer, follow these steps:

### 1. Copy files

```bash
mkdir -p ~/.claude/cognito/{config,hooks,logs,sessions,templates,phases,integrations}

cp -r ~/cognito/hooks/*.sh          ~/.claude/cognito/hooks/
cp ~/cognito/config/*.json          ~/.claude/cognito/config/
cp ~/cognito/config/_phase-state.default.json ~/.claude/cognito/config/_phase-state.json
cp -r ~/cognito/templates           ~/.claude/cognito/
cp -r ~/cognito/phases              ~/.claude/cognito/
cp -r ~/cognito/integrations/.      ~/.claude/cognito/integrations/
cp ~/cognito/SKILL.md               ~/.claude/cognito/

cp -r ~/cognito/modes/*             ~/.claude/skills/
cp ~/cognito/commands/*.md          ~/.claude/commands/

chmod +x ~/.claude/cognito/hooks/*.sh
```

### 2. Register hooks in `~/.claude/settings.json`

Merge this block into the `hooks` key of your `settings.json` (adjust the path if you installed elsewhere):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "name": "cognito-phase-detector",
        "command": "bash ~/.claude/cognito/hooks/phase-detector.sh",
        "blocking": false
      },
      {
        "name": "cognito-mode-injector",
        "command": "bash ~/.claude/cognito/hooks/mode-injector.sh",
        "blocking": false
      }
    ],
    "PreToolUse": [
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

> Note: `mode-injector` lives on `UserPromptSubmit` since v1.1.0. Earlier versions registered it on `PreToolUse`, which caused redundant injection on every tool call.

## Troubleshooting

### `/cognition-status` does nothing
- Re-open Claude Code (it reloads slash commands on session start).
- Check `~/.claude/commands/cognition-status.md` exists.

### Hooks don't fire
- `chmod +x ~/.claude/cognito/hooks/*.sh`.
- Git Bash only on Windows — paths must be absolute in `settings.json`.
- Run `/cognition-status --verify` to see which hooks the harness registered.

### A mode doesn't activate when I type `/divergir`
- `~/.claude/skills/divergente/SKILL.md` must exist.
- `config/_operator-config.json → modes.disabled` must NOT list that mode.

### A gate blocks something it shouldn't
- Toggle via `/cognition-gate off <gate-id>` (or edit `_operator-config.json → gates.disabled`).
- The PII gate (`no-hardcode-pii`) uses best-effort regex; see [SECURITY.md](SECURITY.md) → Known limitations.

### Install failed with `python3: command not found`
- Python 3.10+ is required. Install from python.org (Windows) and tick "Add to PATH".
- Git Bash usually exposes `python3` when Python is on PATH; otherwise `alias python3=python` in `~/.bashrc`.

## Next steps

- [README.md](README.md) — quick overview.
- [ARCHITECTURE.md](ARCHITECTURE.md) — design decisions and v1.1 "known limitations".
- Run `/fase discovery` + `/divergir` on a real problem to feel the difference.
