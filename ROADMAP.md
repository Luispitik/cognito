# Cognito — Roadmap

Planned work beyond the current release. Items move to `CHANGELOG.md` once shipped. Nothing here is a commitment — priorities shift. Open a Discussion if you want to push for something.

## v1.2.0 — targeted

- **Deeper Sinapsis integration.** Today the bridge injects rendered text into Executor / Verifier / Auditor. v1.2 pushes structured instincts (with confidence, domain, last-triggered-at) so Cognito can reason about them instead of just reading them.
- **`/cognition-metrics`** — slash command that reports which modes and phases fire most, which gates trigger most, and which templates are under-used. Uses the per-session logs introduced in v1.1.
- **Auto-promote instincts to gates.** Once an instinct has N+ occurrences, propose it as a gate rule in `_passive-triggers.json` (user accepts in one step).
- **Gitleaks integration** for the PII gate. Today `no-hardcode-pii` is a narrow regex (see SECURITY.md). v1.2 shells out to `gitleaks detect` on the staged content when the binary is available, keeping the regex as a best-effort fallback.
- **Structured JSON-line logs** across all hooks (events, session_id, hook name, duration, outcome). Makes the dashboard accurate without heuristics.
- **`/cognition-status --verify` hardening.** Full health check: Python version, config JSON validity, regex compile, hooks registered in `settings.json`, backup dir writable, Sinapsis bridge reachable.

## v2.0.0 — strategic

- **User-defined modes** in `modes/custom/` plus registry in `_modes.json`. Lets operators ship their own thinking modes without forking Cognito core.
- **Marketplace** for community modes, gates and profiles. Aligns with the broader Skills Marketplace milestone in the operator-wide roadmap.
- **Semver per mode**. Each mode carries its own version in frontmatter; updates can be granular.
- **Profile as runtime context**, not just install-time. Allow switching profiles in-session (e.g. `/cognition-profile alumno`) without reinstall.
- **Breaking changes we've flagged**:
  - Collapse `Estratega` into `Divergente` (they share 80%+ of the marcos already).
  - Collapse `Devil's Advocate` and `Auditor` into one mode with pre/post modifier (pre-mortem vs. post-mortem of the same template).
  - Drop `hookIntensity` from `_phases.json` — it is dead configuration today.
  - Unify the three sources of truth for mode↔phase binding (`_phases.json`, `_modes.json`, mode frontmatter) with a generator.

## Rejected / deferred

See `ARCHITECTURE.md` → "Decisiones rechazadas" for things we already ruled out (single agent that changes role, auto-phase-change without confirmation, MCP-based hooks, one giant SKILL.md).
