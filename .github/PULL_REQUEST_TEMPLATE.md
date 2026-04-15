## Summary
<!-- 1-3 sentences: what does this PR change and why? -->

## Type

- [ ] `feat` — new functionality
- [ ] `fix` — bug fix
- [ ] `docs` — documentation only
- [ ] `test` — tests only
- [ ] `refactor` — internal change, no external effect
- [ ] `chore` — infra, CI, deps
- [ ] `perf` — performance
- [ ] `security` — hardening or vulnerability fix

## Scope

- [ ] Modes (`modes/`)
- [ ] Phases (`phases/`)
- [ ] Hooks (`hooks/`)
- [ ] Config (`config/`)
- [ ] Templates (`templates/`)
- [ ] Profiles (`profiles/`)
- [ ] Commands (`commands/`)
- [ ] Integrations (`integrations/`)
- [ ] Dashboard (`dashboard/`)
- [ ] Tests (`tests/`)
- [ ] Docs / infra

## Checklist

- [ ] Tests added or updated (pytest and/or bats)
- [ ] `bash tests/run_tests.sh` passes locally
- [ ] Documentation updated where relevant (README, ARCHITECTURE, etc.)
- [ ] CHANGELOG.md entry added under `[Unreleased]` (unless trivial)
- [ ] No personal or sensitive data introduced
- [ ] Conventional commit prefix in PR title

## Testing notes
<!-- How can a reviewer verify this? Commands, scenarios, edge cases. -->

## Related issues
<!-- "Closes #N", "Refs #N" -->

## Security review

- [ ] No new external inputs
- [ ] No new filesystem writes outside `COGNITO_DIR`
- [ ] No new dependencies (or deps audited and added to Dependabot scope)
- [ ] No regex with catastrophic backtracking risk
