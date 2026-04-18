---
name: cognition-gate
description: Enable, disable, list or inspect Cognito gates at runtime.
---

# /cognition-gate

Manages individual gates defined in `config/_passive-triggers.json` and toggled
via `config/_operator-config.json → gates.enabled / gates.disabled`.

Runtime toggle only; it does not edit the gate definitions themselves.

## Usage

- `/cognition-gate list` — show every gate and whether it is enabled for the current profile.
- `/cognition-gate on <id>` — enable a gate for this installation.
- `/cognition-gate off <id>` — disable a gate for this installation.
- `/cognition-gate info <id>` — print the full rule: pattern, files affected, action, message.

## What Claude does when this command is invoked

1. Reads `_passive-triggers.json` and collects every rule under `gates.rules`.
2. Reads `_operator-config.json` → `gates.enabled` / `gates.disabled`.
3. For `list` or `info`: prints a table or the requested rule — no writes.
4. For `on <id>` or `off <id>`:
   - Load `_operator-config.json`.
   - Move `<id>` between `enabled` and `disabled` as requested.
   - Write the file back with 2-space indent.
   - Report the new state.

## Safety

- Never modifies `_passive-triggers.json`. That is the source of truth for gate definitions.
- Changes apply to the **next** tool call that triggers `gate-validator` — not retroactively.
- `off` on a critical gate (e.g. `no-commit-env`, `no-hardcode-pii`) is accepted but **warned**
  in the output so the operator understands the loss of protection.

## Examples

```
/cognition-gate list
# -> table: id | enabled | action | files

/cognition-gate off operator-pricing-check
# -> disabled: operator-pricing-check (was enabled)

/cognition-gate on rls-supabase-required
# -> enabled: rls-supabase-required
```

## Related

- `/cognition-status` — overall health + active modes + active gates.
- `SECURITY.md` → Hardening recommendations for users.
