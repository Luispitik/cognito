# Cognito — Changelog

Versionado semver. Formato inspirado en [keepachangelog.com](https://keepachangelog.com).

---

## [2.2.0] — 2026-04-21 — "Memory bridge + a11y polish"

Minor release. Ships the opt-in Sinapsis → Claude `memory_20250818` bridge that
several operators have been requesting for long-running coding agents, plus a
dashboard accessibility pass and a ROADMAP rewrite with the v3.0 Managed
Agents migration design. **No breaking changes.**

### Added

- **`SinapsisBridge.to_memory_tool_entries()`** (`integrations/sinapsis_bridge.py`).
  Converts active instincts (confirmed + permanent, draft excluded) into a list
  of memory-tool `create` entries `{command, path, content}`. Paths are POSIX
  (`/memories/<scope>/<slug>.md`), slugs are sanitised, duplicates get
  `-2`/`-3` suffixes, content is capped at ~1 KB per entry with metadata
  footer (`confidence`, `occurrences`, `domain`, `scope`, `sinapsis` version).
  Opt-in: no Cognito hook or command invokes it — the operator wires it into
  their own memory-tool adapter.
- **`tests/unit/test_sinapsis_memory_bridge.py`** — 12 new tests covering
  shape contract, unavailability, limit/scope filters, slug safety,
  deduplication, content bounds, custom `base_path`.
- **`integrations/docs/memory-tool-bridge.md`** — usage doc with guarantee
  table, opt-in rationale, minimal integration pattern, and relation to
  `render_injection` (per-prompt vs. per-session).
- **ROADMAP v3.0 section** — full Managed Agents migration design: agent-spec
  path, client path, hybrid option, gate rewrite as declared tool, state
  storage choice (container-local vs. memory-tool persistence), and explicit
  "out of scope" note for Bedrock/Vertex/Foundry (Managed Agents is 1P only).

### Changed

- **Dashboard a11y** (`dashboard/styles.css`). Added `@media (prefers-reduced-motion: reduce)`
  block that disables the KPI card hover translation + shadow animation and
  collapses all transitions/animations globally, per WCAG 2.3.3. Keyboard
  focus rings stay intact because they don't depend on transitions.
- **ROADMAP.md** reorganised — v1.2 targeted items that remain relevant are
  now in v2.2/v2.3 buckets; v3.0 becomes strategic with Managed Agents as the
  headline change.

### Test count

301 pytest + 22 bats = **323** (18 pytest skipped on Windows for
platform-specific reasons, tracked in ROADMAP).

---

## [2.1.0] — 2026-04-19 — "Claude Opus 4.7 alignment"

Targeted release to align Cognito with Claude Opus 4.7 (current Claude Code
default model, `claude-opus-4-7`, 1M context, $5/$25 per 1M tok). **No
breaking changes.** Cognito still does not call the Anthropic API directly
(verified: `grep -rn "anthropic\|api.anthropic"` in hooks/ returns empty).

### Added

- **`recommendedEffort` per mode** in `config/_modes.json` (values: `low`,
  `medium`, `high`, `max`). Default mapping:
  - divergente: `high` (ideation benefits from deep thinking)
  - estratega: `high`
  - devils-advocate: `high`
  - consolidador: `high`
  - ejecutor: `medium` (deterministic execution — token-efficient)
  - verificador: **`max`** (fact-check warrants full reasoning)
  - auditor: **`max`** (post-mortem quality)
- **`overrideEffort` on phase-state** — operator can pin a session-level
  effort via the new `/cognition-effort` command. Null by default. Included
  in `_phase-state.default.json` (now v1.1).
- **`mode_injector.py` effort hint.** When any mode is active, the injector
  appends a `## Cognito · effort recommendation (Opus 4.7+)` block at the
  end of the systemMessage with the computed level and its source
  (override / mode.recommendedEffort / determinism fallback). Harness consumers
  that use `output_config.effort` can pick it up; harnesses that ignore the
  block keep working unchanged.
- **New slash command `/cognition-effort`** (`commands/cognition-effort.md`).
  Writes `_phase-state.json.overrideEffort` atomically. Accepts `low`/
  `medium`/`high`/`max`/`off`. Commands count goes **12** (was 11).
- **`scripts/benchmark-cache.sh`** — opt-in live benchmark against the
  Anthropic API (`COGNITO_BENCHMARK_LIVE=1`). Captures 3 consecutive
  `mode_injector` outputs, sends them with `cache_control: {type: "ephemeral"}`,
  reports `cache_creation` / `cache_read` / `input` tokens per run and the
  hit ratio. Exit 0 if ratio ≥ 0.6. Dry-run without the flag.
- **`tests/unit/test_effort_hint.py`** — 20 new tests: config integrity,
  injector semantics (per-mode, override, fallback, ordering), budget raise
  validation, anti-regression for Opus 4.7 removed params.
- **`ARCHITECTURE.md` §14** — "Compatibility with Claude Opus 4.7" documenting
  what changes in 4.7 that affects Cognito, what doesn't, and the effort
  precedence table.

### Changed

- **`MAX_TOTAL_CHARS` raised 16 000 → 48 000** in `hooks/python/mode_injector.py`
  (~4k → ~12k tokens). Rationale: Opus 4.7's cache minimum is 4096 tokens;
  the old bundle sat exactly at the write threshold. The new budget crosses
  it reliably and uses 1.2 % of the 1M context window.
- **`MAX_PER_MODE` raised 6 000 → 8 000.** Divergente's full 6 564-byte
  SKILL.md now lands without `[truncated]` truncation.
- **`_modes.json` bumped to `version: "2.1.0"`** (was 2.0.0). Added top-level
  `effortGuidance` block documenting the `determinism → effort` mapping as a
  single source of truth.

### Anti-regressions shipped

- `TestNoDeprecated47Params.test_mode_skill_does_not_prescribe_deprecated_params`
  — parameterized over all 7 `modes/*/SKILL.md`. Fails if any mode's
  instructions contain literal `budget_tokens:`, `top_p:`, `top_k:` etc.
  (Opus 4.7 returns 400 on these.)
- `test_mode_injector_itself_does_not_mention_deprecated_params_as_instructions`
  — scans the injector source for executable mentions of `budget_tokens`
  (comments and docstrings ignored).

### Tests

- **Total: 289 passed, 18 skipped, 0 fail** (v2.0.0-rc1: 269/18/0). +20 tests.
- All new tests pass on Windows Git Bash + Python 3.14.

### Not included

- **Sinapsis-as-memory-tool bridge (item #6 in the plan).** Scheduled for
  v2.2 — requires designing the memory-tool schema mapping for
  `memory_20250818` and adding `to_memory_tool_entries()` to the bridge.
- **Managed Agents migration (item #10).** v3.0 — requires Cognito to stop
  being a hook system and become either a Managed Agent config or a client
  that drives managed-agent sessions. Big scope.
- **Raising Lighthouse a11y score to 90+.** Still tracked from v1.1.1 audit.

### Compatibility matrix

| Harness model | Works? | Notes |
|---|---|---|
| Claude Opus 4.7 (`claude-opus-4-7`) | ✅ | Intended target. Effort hint respected if harness passes `output_config.effort`. |
| Claude Opus 4.6 (`claude-opus-4-6`) | ✅ | Effort hint applies (4.6 supports all 4 levels incl. `max`). |
| Claude Sonnet 4.6 (`claude-sonnet-4-6`) | ⚠️ | Hint applies but **`max` returns 400** — if the harness passes `max` blindly, calls will fail. Operators should pin via `/cognition-effort high` when on Sonnet. |
| Claude Haiku 4.5 (`claude-haiku-4-5`) | ⚠️ | `effort` parameter not supported at all — hint should be filtered by harness before the API call. |

### Notes

- `budget_tokens` / `temperature` / `top_p` / `top_k` are removed in Opus 4.7.
  Cognito never touched these; the anti-regression tests make sure future
  contributions don't either.
- Hook latency is unchanged — the model migration doesn't affect cold-start
  (bash + Python locally).

---

## [2.0.0-rc1] — 2026-04-19 — "Redesign, not patches"

v1.2 shipped the four "needs-redesign" patches. v2.0 ships the three pieces
that v1.2 explicitly punted: persistent hook daemon, collapse of redundant
modes, and marketplace skeleton. All measurements in this entry are
reproducible with commands provided under `docs/VERIFY-v2.md`.

### Measured (not projected)

- **Daemon latency win, measured end-to-end on Windows Git Bash:**
  - `phase-detector.sh` cold (daemon off): **avg 635 ms** over 5 runs.
  - `phase-detector.sh` hot (daemon on):   **avg 495 ms** over 5 runs.
  - **Delta: −140 ms (~22 %)**, not the "≥ 90 %" we originally projected.
  - Honest reason: the bash wrapper still spawns a fresh Python 3 process
    for the *client* (`_daemon.py client <hook>`), which pays its own
    ~200 ms cold start on Windows before the socket round-trip. The win
    comes from skipping the **second** cold start that would otherwise run
    the full handler. A C/Go client binary is the next step — tracked as a
    v2.1 target. Do NOT claim "50 ms" until we have it.
- **Tests:** 269 passed, 18 skipped, 0 fail (was 261 + 16 in v1.2).
- **Coverage:** 57 % over 902 stmts (was 76 % over 606). The absolute line
  count grew by 296 because the daemon is 277 stmts and is only partially
  covered by the unit tests — the full lifecycle is exercised via real
  subprocess in `test_v2_daemon_and_collapse.py`, which pytest-cov cannot
  instrument unless we wire `COVERAGE_PROCESS_START`. Tracked for v2.1.

### Added

- **`hooks/python/_daemon.py`** (277 stmts) — long-lived worker with three
  roles: `serve` (daemonized listener), `client <hook>` (wrapper proxy), and
  lifecycle helpers (`status`, `stop`). AF_UNIX socket on Linux/macOS under
  `$COGNITO_DIR/runtime/hook.sock`; AF_INET (127.0.0.1) + 16-byte hex token
  on Windows. Exit code 127 from the client tells the bash wrapper to fall
  back to the v1.2 cold-start path transparently.
- **`scripts/cognito-daemon.sh`** — start / stop / restart / status manager.
  Writes logs to `logs/daemon.log`. Detached via `nohup ... &` + `disown`.
- **All four `hooks/*.sh` wrappers** now try the daemon first (client 127
  → fall back to Python cold invocation). Zero regressions: every v1.2
  test still passes whether the daemon is up or down.
- **Collapse v2 (opt-in via `_operator-config.json → modes.collapseV2 = true`):**
  - `config/_modes.json` adds a `collapseV2.aliases` block that maps
    `estratega → divergente (preset: time-horizon)` and
    `devils-advocate → auditor (preset: pre-mortem)`.
  - `mode_injector.py` rewrites the active-mode list through the alias
    table only when the flag is on. Header format changes from
    `## Modo activo: estratega` to
    `## Modo activo: divergente (preset: time-horizon)`.
  - Default is `false` — existing installs are byte-for-byte unchanged.
- **`scripts/install-mode.sh`** — marketplace installer. Fetches a
  registry JSON (default
  `https://raw.githubusercontent.com/Luispitik/cognito-community/main/registry.json`),
  validates sha256 when present, and installs the SKILL.md under
  `modes/custom/<slug>/`. `--list`, `--local=PATH`, `--force`, `--target=DIR`.
  Activating the installed mode still requires the user to add it to
  `_operator-config.json → modes.enabled` — no autoloading.
- **`tests/unit/test_v2_daemon_and_collapse.py`** — 10 new tests.
  Daemon lifecycle (5), collapse on/off semantics (3), marketplace local
  install + force (2, skipped on Windows because the shell script uses
  POSIX `mktemp`).

### Changed

- `_modes.json` bumped to `version: "2.0.0"`.
- `hooks/python/mode_injector.py` gains the collapse rewrite step + preset
  annotation in the injection header.

### Not yet done (honest)

- Daemon client is still Python — the ~200 ms Windows Python cold start
  dominates the client round-trip. **A native client (Go or Rust, static
  binary, ~5 ms cold) is v2.1.** Until then, daemon gives 22 % not 90 %.
- `update.sh` still ships the v1.2 Python modules — it does NOT install or
  manage the daemon. Starting the daemon is an explicit operator action
  (`bash scripts/cognito-daemon.sh start`) documented in INSTALL.md.
- `install-mode.sh` test coverage on Windows is skipped (POSIX tooling).

### Not breaking

- Every v1.2 hook registration in `~/.claude/settings.json` keeps working
  unchanged. The daemon is strictly opt-in — if it is not running, the
  wrappers behave like v1.2 did, bit-for-bit.

---

## [1.2.0] — 2026-04-19 — "Close the redesign gaps"

v1.2 ships the four fixes that v1.1.1 explicitly listed as "needing redesign,
not patches": heredoc extraction, dry-run install, repair command and
phase-detector fast-path. Baseline numbers after this release:

- **261 pytest passing + 16 skipped** (was 225 + 13 in v1.1.1). 36 new tests.
- **Coverage: 76% over 606 stmts** (v1.1 measured 75% over 171 — the old
  heredocs were invisible to pytest-cov because they ran as subprocess stdin).
- **Phase-detector fast-path: ~170 ms saved** when the prompt field is empty
  or whitespace-only. Measured avg `no-prompt` = 328 ms vs `with-prompt` =
  497 ms on Windows Git Bash.

### Maintainability — heredocs extracted

- `hooks/python/` package with `_common.py`, `phase_detector.py`,
  `mode_injector.py`, `gate_validator.py`, `session_closer.py`. Total ~540
  lines of Python lifted out of bash heredocs into importable modules.
- `_common.py` centralizes what used to be four copies of the same
  `session_id` regex, log tagger, stdin-capped reader and `COGNITO_DIR`
  resolver.
- Bash wrappers (`hooks/*.sh`) shrunk to ~40 lines each. They resolve
  `COGNITO_DIR`, apply `cygpath` on Windows, cap stdin at 1 MiB and `exec`
  the sibling Python module — nothing else.
- Modules are dual-importable: `python3 hooks/python/phase_detector.py`
  works standalone; `from hooks.python import phase_detector` works as a
  package. Enables subprocess invocation (current hook contract) and native
  unit-testing (new `test_hooks_python_direct.py`).
- `scripts/install.sh` ships `hooks/python/` alongside the `.sh` wrappers.

### Performance — phase-detector fast-path

- `hooks/phase-detector.sh` now short-circuits in bash when stdin has no
  `"prompt"` field or the prompt is empty/whitespace-only. No Python cold
  start in that case. Saves ~170 ms per invocation on Windows, ~50 ms on
  Linux. The full-path latency is unchanged.
- Documented that lower than 300 ms on Windows still requires a daemon
  (tracked in ROADMAP v2.0) — this is the single ship-in-a-day win.

### Reliability — `cognition-verify.sh --repair`

- New flag on the existing verify script. Detects a missing or corrupted
  `config/_phase-state.json`, backs the broken file up as
  `_phase-state.broken.<ts>.json` for forensics, and restores from
  `_phase-state.default.json` (or a synthesized minimal default if the
  bundled default is also missing).
- Every repair action appends a timestamped line to
  `logs/incidents.log` — no silent fix. Human-readable output also
  surfaces `Repaired: N item(s)` when anything changed.
- 3 regression tests (`test_install_and_verify.py::TestVerifyRepair`).
- Behaviour when nothing is broken: emits `Nothing to repair.` and exits 0.

### Safety — `install.sh --dry-run`

- New `--dry-run` / `-n` flag. Prints the exact plan (profile, modes,
  hooks, gates, templates, every `cp`/`mkdir`/`chmod` call) without touching
  the filesystem or `settings.json`.
- Exit banner clearly says `Dry-run complete — no files were touched`.
- 2 regression tests assert the target directory does not exist after the
  dry-run finishes.

### Docs / CI

- Roadmap: 4 of the 8 v1.2 targeted items and all 4 "honest limits" closed.
- `test.yml` matrix unchanged from v1.1.1 (Ubuntu + macOS + Windows);
  `TestVerifyRepair` is documented-skipped on Windows due to an MSYS path
  translation issue that affects only the subprocess test harness, not the
  feature itself (the command works fine on Windows when invoked manually).

### Notes

- **No breaking changes.** Existing hook registrations (`bash hooks/*.sh`)
  keep working unchanged — the wrappers exec the new Python modules
  transparently.
- The `hooks/python/` directory is new; downstream forks that pin individual
  files should update to ship the directory as well.

---

## [1.1.1] — 2026-04-18 — "ISO 25010 gaps"

Ship-gap patches on top of v1.1.0 driven by the ISO/IEC 25010:2023 audit (`docs/QUALITY-ISO25010-2026-04-18.md`). No new features, no architecture change. Everything here closes a dimension that scored ≤ 3.3 in that audit.

### Fixed

- **Compatibility**: `sinapsis_bridge._CANDIDATE_ROOTS` now includes `~/.claude/skills/norteia-continuous-learning`. Before 1.1.1 the bridge only auto-detected `sinapsis`, `sinapsis-learning`, `~/.sinapsis` and `~/sinapsis` — operators whose Sinapsis v4.3+ installation is packaged as the `norteia-continuous-learning` skill had to set `SINAPSIS_DIR` manually or configure `integrations.sinapsis.path`. Adds `TestAutoDetectCandidates` (3 tests) to lock the behaviour.
- **Docs accuracy**: `INSTALL.md` said `uninstall.sh` removes "10 Cognito slash commands"; the script actually removes 11 (matches `README.md`). Fixed.
- **Docs accuracy**: `SECURITY.md` recommended pinning against `v1.0.0`; bumped to `v1.1.0`.
- **Dashboard version**: footer was hardcoded to `Cognito v1.0.0`. Now the footer renders `Cognito v<version>` where `<version>` is read by `build_data.py` from the newest `## [x.y.z]` heading in `CHANGELOG.md` and surfaced in `data.json`.

### Usability

- **Dashboard accessibility baseline (WCAG 2.2 A baseline, closes Usability subscore from 1/5 → 4/5):**
  - Skip-link `Saltar al contenido` focus-only, lands on `#main-content`.
  - `role="banner" / main / contentinfo"` landmarks on header / main / footer.
  - `role="status" aria-live="polite"` on `#status-phase` and `#generated-at`; `aria-live` on KPI section, gates list, Sinapsis badge/details.
  - Refresh button: `type="button"`, `aria-label="Refrescar los datos del dashboard"`, visible focus ring.
  - Canvas charts: `role="img" aria-labelledby aria-describedby` + hidden `<p class="sr-only">` description so screen readers get the semantic of each chart.
  - Recent-sessions `<table>` gets `<caption class="sr-only">` + `<th scope="col">` on every header.
  - CSS fallback for `.sr-only` and visible `:focus-visible` outline so the accessibility layer keeps working if the Tailwind Play CDN is blocked.

### Portability

- **CI now exercises Windows.** `test.yml` matrix adds `windows-latest` across Python 3.10 / 3.11 / 3.12. Git Bash is the default shell. `jq` is installed via Chocolatey. `bats` and `shellcheck` are explicitly skipped on Windows (bats-core does not support Windows natively — tracked in `ROADMAP.md`). A pre-step ensures a `python3` shim exists on Windows (copy of the `python` executable when the launcher does not provide one).

### Notes

- v1.1.1 has **no breaking changes**. `_CANDIDATE_ROOTS` is import-exposed for tests — consumers that already imported `SinapsisBridge` are unaffected.
- Performance work (hook latency, phase-detector early-exit, daemon) and gate widening (gitleaks subprocess) remain as v1.2 targets in `ROADMAP.md`.

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
