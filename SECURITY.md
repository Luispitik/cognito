# Security Policy

Cognito takes security seriously. This document explains how we support releases, how to report a vulnerability, and what is in scope.

> GitHub looks for `SECURITY.md` in `.github/`, the repo root, or `docs/`. The single canonical copy lives at the **repository root**.

---

## Supported Versions

Cognito follows [Semantic Versioning 2.0.0](https://semver.org/). Only the latest **MINOR** of the current **MAJOR** receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

When a new MAJOR is released, the previous MAJOR receives **3 months of critical-only** security patches before EOL.

---

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Use one of these private channels:

1. **GitHub Security Advisories** (preferred) — [Report a vulnerability](https://github.com/Luispitik/cognito/security/advisories/new). Keeps the report confidential until a fix ships.
2. **Private message** to a maintainer through their GitHub profile.

### What to include

- **Affected version(s)**: tag or commit SHA
- **Component**: `hooks/`, `integrations/`, `dashboard/`, `scripts/`, `config/`, CI, docs
- **Description** of the vulnerability (1–3 sentences)
- **Impact**: what an attacker can do (e.g., arbitrary command execution, data exfiltration, gate bypass)
- **Reproduction steps**: minimal example or PoC
- **Suggested fix or mitigation** (optional)

### Response timeline

| Phase | Target |
|-------|--------|
| Acknowledgement | within **72 hours** |
| Triage + CVSS v3.1 severity | within **7 days** |
| Fix or mitigation (HIGH/CRITICAL) | within **30 days** |
| Coordinated public disclosure | after fix release, in agreement with reporter |

For **critical** vulnerabilities (RCE, auth bypass, exfiltration) we accelerate: patch within 7 days when feasible. Non-critical issues ship in the next scheduled minor release.

---

## Scope

### In scope

- `hooks/*.sh` — shell injection, path traversal, privilege escalation
- `integrations/*.py` — RCE, deserialization, SSRF
- `dashboard/api/*.py` — injection, path traversal
- `config/*.json` and `profiles/*.yaml` — parsing flaws that lead to code exec
- `scripts/install.sh` — privilege escalation, arbitrary writes outside `~/.claude/`
- `.github/workflows/*.yml` — supply-chain attacks, token exfiltration
- The Sinapsis bridge — instinct injection, regex DoS

### Out of scope

- Vulnerabilities in **Claude Code itself** — please report to Anthropic.
- Vulnerabilities in **upstream dependencies** already disclosed upstream — report to the respective project (Python stdlib, pytest, bats-core, Chart.js, Tailwind).
- **Denial of service** via local resource exhaustion — Cognito runs in a single user session, not multi-tenant.
- **Social engineering** of maintainers or users.
- **Physical access** to a user's machine.
- Issues in **forks** that modify Cognito's default configuration.
- **Already-documented "by design" behavior** — e.g., gates are opt-in; the user is responsible for enabling them.

---

## Threat Model

Cognito is a **local-only** tool that runs inside a user's Claude Code session. Assumptions:

1. The user trusts Claude Code and their shell environment.
2. The filesystem where Cognito runs is the user's (no multi-tenancy).
3. Cognito has **no network access** by design — no server, no telemetry, no auto-update.
4. The dashboard is **read-only over `localhost`** (HTTP, no auth) — the user is responsible for not exposing port 8765 to the network.

### Threats considered

| Threat | Mitigation |
|--------|------------|
| **Malicious hook execution** — a compromised hook could run arbitrary code as the user | Hooks ship read-only in the repo, require explicit registration in `settings.json`, ShellCheck runs in CI |
| **Path traversal** — crafted prompt or filename tricks a hook into reading/writing outside `COGNITO_DIR` | Paths resolved against a fixed base via `realpath`; gate-validator refuses paths containing `..` |
| **Gate bypass** — content that should trigger a block does not | Regex tests + audit in `AUDIT-PRE-DEPLOY.md` |
| **Config injection** — malicious `_passive-triggers.json` adds rules that exfiltrate data | Config files live locally, never downloaded; user owns the install |
| **Sinapsis bridge poisoning** — a malicious Sinapsis install injects harmful instincts | Auto-detect can be disabled in `_operator-config.json → integrations.sinapsis.installed: false` |
| **Sensitive data in logs / sessions / dashboard** | `logs/`, `sessions/`, `dashboard/data.json` are `.gitignore`-d by default |
| **Adversarial prompt injection** to a hook | Hooks tolerate malformed JSON, missing files, and adversarial prompts without crashing |

### Attacker model

The attacker can:
- Submit arbitrary text as a Claude prompt (adversarial prompt injection)
- Place crafted files in the working directory
- Modify Cognito config files only if they already have filesystem access (already-compromised system)

The attacker cannot, by Cognito's design:
- Reach Cognito over the network (no network surface)
- Exfiltrate session data to a remote server (no telemetry)

---

## Known limitations

- **`gate-validator.sh` is advisory** — a determined user can override gates with `/cognition-gate override <id>`. Gates protect against honest mistakes, not against malicious actors who already have shell access.
- **`sinapsis_bridge.py` executes regex** from `_passive-triggers.json`. Malformed regex is caught; pathological regex (ReDoS) could stall a hook for seconds (CPU only, no crash). Mitigated by Python's `re` engine timeouts in CPython ≥ 3.11.

---

## Hardening recommendations for users

When you install Cognito, consider:

1. **Review the hooks** in `hooks/` before registering them in `settings.json`. They run with your user privileges on every Claude Code action.
2. **Do not commit** `logs/`, `sessions/`, `dashboard/data.json`, or `config/_phase-state.json` — they may contain prompt content or file paths. The default `.gitignore` excludes them.
3. **Keep `bash`, `jq`, `python3` updated** — hooks depend on these system tools.
4. **Pin your Cognito version** in any downstream automation: `git clone --branch v1.0.0` or use a submodule tracking a tag.
5. **Disable gates you don't need** — an always-on gate that matches broadly may log sensitive content. See `config/_operator-config.json → gates.enabled`.
6. **Run the test suite** before trusting a fork: `bash tests/run_tests.sh` must report all passing.

---

## Cryptographic scope

Cognito does **not** implement any cryptography. It does not encrypt, decrypt, sign, or hash user data. All data at rest is plaintext JSON / logs under `~/.claude/cognito/`. Protect the directory with OS-level permissions if you share the machine.

---

## Supply chain

- **Runtime dependencies**: Python 3.10+ stdlib only — no PyPI dependencies.
- **Test dependencies**: `pytest`, `pyyaml` (see `requirements-test.txt`). Audited via Dependabot — see [`.github/dependabot.yml`](.github/dependabot.yml).
- **Hook dependencies**: `bash`, `jq` (optional), `python3`. Standard Unix tools. No third-party scripts downloaded at runtime.
- **Dashboard CDNs**: Tailwind CSS and Chart.js from public CDNs, pinned to major versions. Self-host from `dashboard/` if CDN compromise is a concern.
- **CI security scans**: CodeQL, Bandit (Python SAST), ShellCheck (Bash SAST), Gitleaks (secrets), Dependency Review — see [`.github/workflows/security.yml`](.github/workflows/security.yml).

---

## Bounty / Acknowledgement

Cognito is MIT-licensed and maintained by volunteers — **no monetary bounty program**. Valid reports are credited in:

- `CHANGELOG.md` security section of the release that fixes the issue.
- The published GitHub Security Advisory.
- The Hall of Fame below (with the reporter's permission).

Reporters can request anonymity at any time.

---

## Hall of Fame

Reporters of valid vulnerabilities are listed here once published advisories ship.

*No entries yet.*
