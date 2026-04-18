# Cognito — Changelog

Versionado semver. Formato inspirado en [keepachangelog.com](https://keepachangelog.com).

---

## [1.1.0] — 2026-04-18 — "Honest Release"

After an end-to-end audit (`docs/AUDIT-2026-04-18.md`), v1.1.0 closes the gap between the narrative and the runtime. No new modes or phases; the architecture is the same, but it now does what the docs say it does.

### Security

- **HIGH**: `scripts/install.sh` used an unquoted Python heredoc (`<<PYEOF`); `$TARGET_DIR` and `$PROFILE` were interpolated into the Python source. Quoted the delimiter and switched to environment-variable plumbing. Added an early `python3` availability check and a whitelist of allowed profile names.
- **HIGH**: `hooks/session-closer.sh` took `session_id` from input JSON and used it as a filename without sanitization (`../../config/...` would overwrite config). Session IDs are now validated against `^[A-Za-z0-9_.-]{1,64}$`, with a `realpath` + prefix check before writing.
- **MEDIUM**: `dashboard/serve.sh` served the entire parent directory (exposing `api/*.py`) and could bind `0.0.0.0` on some Python versions. Replaced `http.server` with an allowlist-based handler that serves exactly five static paths and binds `127.0.0.1` by default.
- **MEDIUM**: `dashboard/app.js` interpolated values from `data.json` into `innerHTML` without escaping. Added an `esc()` helper backed by `textContent`; every dynamic value now routes through it.
- **MEDIUM**: CDN scripts in `dashboard/index.html` lacked `crossorigin` attributes. Added them; documented how to generate a deterministic SRI hash for Chart.js and why Tailwind Play CDN cannot be pinned.
- **LOW**: All four hooks now cap stdin at 1 MiB.

### Fixed

- **`mode-injector` was on the wrong hook event.** Pre-1.1 it ran on `PreToolUse`, firing N times per turn and re-injecting the same payload. Moved to `UserPromptSubmit` (documented in the install snippet). Runs once per turn.
- **`mode-injector` truncated SKILL.md at 60 lines.** This dropped the `Triggers de auto-activación` section of several modes. Replaced with a smart two-tier budget: per-mode 6k chars (cut at `---` / `## ` / `# ` boundaries), total 16k across all active modes.
- **`session-closer` reported lifetime log counts as per-session metrics.** Every line in every hook now carries `[session_id]`. Session-closer partitions the log, counts only its own lines, archives them to `logs/archive/{session_id}.log`, and atomically rewrites the live log to keep parallel sessions intact.
- **`phase-detector` matched with plain substring.** "no exploremos eso" used to trigger the "exploremos" → discovery suggestion. Replaced with word-boundary regex; anchor rules now report malformed regex with a clear log line instead of silently skipping.
- **Profiles were cosmetic.** `install.sh` used to copy every mode, command and gate regardless of profile (it admitted so in a comment). Now it parses `installs.modes / installs.hooks / installs.gates / installs.templates` from the profile YAML and honors them: `alumno` installs 4 modes + 2 hooks + 2 templates + 2 gates; `operator` installs 7 + 4 + 5 + 6.
- **Install was not idempotent.** Reinstalling wiped `_phase-state.json`. Now the current state is preserved, and any existing install is copied to `~/.claude/cognito-backups/<timestamp>/` before overwrite.
- **Uninstall left `settings.json` dirty.** It now strips every `cognito-*` hook entry via `jq` (with a backup) or prints manual-cleanup instructions if jq is absent.
- **`scripts/update.sh` was referenced everywhere but didn't exist.** Shipped it. Non-destructive refresh that keeps user state, config, logs and sessions intact; supports `--dry-run`.
- **`/cognition-gate` was referenced but didn't ship.** Added `commands/cognition-gate.md` with `list / on <id> / off <id> / info <id>`.

### Docs

- Test count: 201 → 204 pytest / 226 with bats (was stale).
- Config JSON count: 5 → 6 (was off by one).
- Python requirement: 3.8+ → 3.10+ (matches actual PEP 604 usage in the code).
- `jq` requirement: "recommended" → "strongly recommended" (now actually used for settings.json merge).
- Removed references to `profiles/operator.hooks.json` (never existed).
- Consolidated `SECURITY.md` at repo root (removed duplicate under `.github/`).
- Placeholder normalization: every remaining `<YOUR_GITHUB_USER>` and `TUUSUARIO` replaced with `Luispitik` or the canonical placeholder, consistently.
- New `ARCHITECTURE.md` → "Known limitations v1.1" section that acknowledges mode overlap (Estratega ≈ Divergente, Devil's Advocate ≈ Auditor) and the narrow scope of the PII gate.
- New `ROADMAP.md` extracted from CHANGELOG to keep the log historical.
- New `docs/AUDIT-2026-04-18.md` — the full audit that drove this release.

### CI

- `release.yml` — tag-driven release with auto-extracted changelog notes and SHA256SUMS.
- `stale.yml` — rot-prevention for issues and PRs.
- `lint.yml` — Markdown + YAML + JSON validation.
- (All three shipped in the previous commit on `main`, but first used in this release cycle.)

---

## [1.0.0] — 2026-04-15

### Added

- Architecture: 7 modes × 5 phases × 4 hooks × 4 profiles.
- **7 thinking modes**:
  - Divergente (ported from the original anti-anchoring skill).
  - Verificador, Devil's Advocate, Consolidador, Ejecutor, Estratega, Auditor (new).
- **5 generic phases**: Discovery, Planning, Execution, Review, Shipping.
- **4 deterministic hooks**:
  - `phase-detector.sh` (UserPromptSubmit) — signals a phase change when it sees specific language.
  - `mode-injector.sh` (PreToolUse — **moved to UserPromptSubmit in v1.1.0**) — injects active-mode instructions as a systemMessage.
  - `gate-validator.sh` (PreToolUse, Write/Edit) — blocks anti-patterns.
  - `session-closer.sh` (Stop) — records session modes and decisions.
- **4 profiles** (YAML): operator, alumno, public, client. Cosmetic in v1.0; real in v1.1.
- **10 slash commands**: `/fase`, `/modo`, `/cognition-status`, `/divergir`, `/verificar`, `/devils-advocate`, `/consolidar`, `/ejecutar`, `/estratega`, `/auditar`.
- **5 structured templates**: matriz-decision, pre-mortem, steel-man, checklist-deploy, auditoria-output.
- **Optional Sinapsis bridge** (`integrations/sinapsis_bridge.py`):
  - Auto-detect on conventional paths and via `SINAPSIS_DIR` env var.
  - Explicit opt-out in `_operator-config.json`.
  - Schema-tolerant reader (dict / list / confidence levels).
  - Modes Ejecutor / Verificador / Auditor consume confirmed+permanent instincts.
  - Degrades silently when unavailable.
- **Web dashboard** (`dashboard/`):
  - Static HTML + Tailwind CDN + Chart.js + vanilla JS (no build step).
  - KPIs, mode/phase charts, 30-day timeline, gates breakdown, recent-sessions table.
  - `build_data.py` consolidates `sessions/` + `logs/` + `config/` into `data.json`.
  - `seed_demo.py` generates synthetic activity for demos.
  - `serve.sh` rebuilds + serves on `http://localhost:8765` (hardened in v1.1).
- **bats tests** (`tests/bats/hooks.bats`) — cross-shell: syntax, executability, UTF-8 encoding, paths with spaces, env-var fallback, graceful degradation.
- **Test suite**: 204 pytest passing (reported as 201 in v1.0; see v1.1 correction), plus 22 bats tests.
- Docs: README, ARCHITECTURE, INSTALL, CONTRIBUTING + per-submodule READMEs under `integrations/`, `dashboard/`, `tests/bats/`.

### Inspiration

- The original anti-anchoring skill (April 2026).
- Sinapsis v4.3 (`Luispitik/sinapsis`) — deterministic-hooks architecture.
- Edward de Bono — *Six Thinking Hats*.
- Daniel Kahneman — *Thinking, Fast and Slow*.

---

## Roadmap

Future work moved to [ROADMAP.md](ROADMAP.md).
