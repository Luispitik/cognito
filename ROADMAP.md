# Cognito — Roadmap

Planned work beyond the current release. Items move to `CHANGELOG.md` once shipped. Nothing here is a commitment — priorities shift. Open a Discussion if you want to push for something.

## v2.2 — in flight

- **Sinapsis → Claude `memory_20250818` bridge** (landed). `SinapsisBridge.to_memory_tool_entries()` converts confirmed/permanent instincts into `create`-command entries the operator can replay into Claude's persistent memory. Opt-in only: no hook or command invokes it by default. See `integrations/docs/memory-tool-bridge.md`.
- **Dashboard a11y hardening**. `prefers-reduced-motion: reduce` now disables hover translations; keyboard focus rings are explicit; heading hierarchy is flat-per-section. Keeps Lighthouse ≥ 90 without a build step.
- **Opus 4.7 effort surface**. `recommendedEffort` per mode + `/cognition-effort {low|medium|high|max|off}` overlay shipped in v2.1; v2.2 raises `MAX_TOTAL_CHARS` to 48 KB so the cache floor is reliably cleared for all modes.
- **Deeper Sinapsis integration** (carried forward from v1.2). Today the bridge injects rendered text into Executor / Verifier / Auditor. v2.2 pushes structured instincts (with confidence, domain, last-triggered-at) so Cognito can reason about them instead of just reading them.
- **Auto-promote instincts to gates** (carried forward). Once an instinct has N+ occurrences, propose it as a gate rule in `_passive-triggers.json` (user accepts in one step).

## v2.3 — targeted

- **`/cognition-metrics`** — slash command that reports which modes and phases fire most, which gates trigger most, and which templates are under-used. Uses the per-session logs introduced in v1.1.
- **Gitleaks integration** for the PII gate. Today `no-hardcode-pii` is a narrow regex (see SECURITY.md). v2.3 shells out to `gitleaks detect` on the staged content when the binary is available, keeping the regex as a best-effort fallback.
- **Structured JSON-line logs** across all hooks (events, session_id, hook name, duration, outcome). Makes the dashboard accurate without heuristics.
- **Daemon parity on Windows**. v2.0 ships AF_INET + 16-byte hex token on Windows; v2.3 benchmarks end-to-end latency vs. AF_UNIX on Linux to confirm the gap stays inside the cache-hit budget.

## v3.0 — strategic

### Managed Agents migration path

**Context.** Today Cognito is a hook layer inside Claude Code: `UserPromptSubmit` injects system text, `PreToolUse` gates Write/Edit, `Stop` closes sessions. The agent loop runs in Claude Code itself. When a user wants Cognito on a server (CI bot, long-running coding agent, multi-session workspace), hooks don't fit — there is no Claude Code process to hook into. Anthropic's **Managed Agents** beta (`managed-agents-2026-04-01`) is the natural target: Anthropic runs the agent loop, hosts the per-session container, and streams events over SSE.

**Design options** (we will pick one, not all):

1. **Agent config path — Cognito ships a reference agent.**
   - `scripts/cognito-agent-spec.{yaml,json}` defines `model: claude-opus-4-7`, `system: <SKILL.md bundle>`, `tools: [...]`, and the phase/mode state file template.
   - `POST /v1/agents` creates the agent **once**; the agent ID is checked into the repo (or stored by the operator).
   - Sessions (`POST /v1/sessions`) reference the agent ID. Cognito's phase/mode/gate state is passed as the session's user message (or written to the session's container via a bootstrap tool call on first turn).
   - **Pros:** minimal client code. Operator gets phases/modes inside a managed session for free.
   - **Cons:** hooks become inert (no `PreToolUse` in Managed Agents today — tool execution runs in the container). We replace the gate-validator with an equivalent server-side tool that wraps Write/Edit.

2. **Client path — Cognito drives managed-agent sessions from the operator side.**
   - Cognito stays a hook-based system for Claude Code. A new `cognito-managed-agent` CLI (Python, stdlib + `anthropic` SDK only) opens a session, streams events, and applies the same phase/mode/gate logic that the hooks apply today — but in-process instead of via shell scripts.
   - The daemon introduced in v2.0 becomes the shared brain: Claude Code hooks and the managed-agent CLI both hit the daemon for `get_phase`, `should_gate`, `log_session`.
   - **Pros:** zero changes to the current hook surface. Works with any transport.
   - **Cons:** we maintain two agent loops (Claude Code's + Anthropic's Managed Agents) and have to keep their state reconciled.

3. **Hybrid.** Publish the agent spec (option 1) for operators who want a stateless managed agent, and ship the CLI (option 2) for operators who want hooks + managed agents to share state. This is the most likely shape — it keeps Cognito optional wherever the operator runs it.

**Gate rewrite.** In a Managed Agents world, `gate-validator` becomes a **declared tool** the agent must call before any write. The tool runs server-side inside the session container, reads the same `_passive-triggers.json`, and returns `{allow: bool, reason: str}`. Claude Code's `PreToolUse` hook stays as a local fast-path; when present, it pre-empts the tool call.

**State storage.** Phase/mode state is ~1 KB of JSON. Two options:
- Per-session file under `/workspace/.cognito/_phase-state.json` (container-local, ephemeral).
- Agent-level memory via the `memory_20250818` tool (persistent across sessions under the same agent).

Default: per-session for 3.0, with a feature flag to promote to memory.

**Out of scope for v3.0.** Bedrock / Vertex / Foundry don't expose Managed Agents. Cognito's Claude Code surface stays the primary deployment there; v3.0 just adds a second surface on first-party Anthropic.

### Other v3.0 work

- **User-defined modes** in `modes/custom/` plus registry in `_modes.json`. Lets operators ship their own thinking modes without forking Cognito core.
- **Marketplace** for community modes, gates and profiles. Aligns with the broader Skills Marketplace milestone in the operator-wide roadmap.
- **Semver per mode**. Each mode carries its own version in frontmatter; updates can be granular.
- **Profile as runtime context**, not just install-time. Allow switching profiles in-session (e.g. `/cognition-profile alumno`) without reinstall.
- **Breaking changes we've flagged**:
  - Collapse `Estratega` into `Divergente` (they share 80%+ of the marcos already). v2.0 ships an opt-in alias; v3.0 makes it default.
  - Collapse `Devil's Advocate` and `Auditor` into one mode with pre/post modifier (pre-mortem vs. post-mortem of the same template).
  - Drop `hookIntensity` from `_phases.json` — it is dead configuration today.
  - Unify the three sources of truth for mode↔phase binding (`_phases.json`, `_modes.json`, mode frontmatter) with a generator.

## Rejected / deferred

See `ARCHITECTURE.md` → "Decisiones rechazadas" for things we already ruled out (single agent that changes role, auto-phase-change without confirmation, MCP-based hooks, one giant SKILL.md).
