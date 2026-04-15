# Governance

Cognito is an open-source project under an MIT license. This document describes how decisions are made.

## Roles

### Users
Anyone who installs or uses Cognito. No formal role.

### Contributors
Anyone whose PR has been merged. Credited in commit history and CHANGELOG.

### Maintainers
Contributors with merge rights. Currently listed in `.github/CODEOWNERS`.

### Project lead
The person who owns the canonical repository (@Luispitik). Holds final decision on scope, direction, and releases.

## Decision making

### Lightweight (most changes)
Small changes — bug fixes, docs, tests, new modes that follow existing patterns — are decided by lazy consensus among maintainers. If no maintainer objects within 5 working days, the PR is approved by default.

### Substantive (architectural changes)
Changes that affect the public API, break existing configurations, or change governance require explicit approval from the project lead.

Examples:
- Adding or removing modes
- Changing the hook contract
- Renaming config files or keys
- Bumping major version

### Security
Security issues follow [SECURITY.md](SECURITY.md). Project lead + security reporter coordinate disclosure.

## Release cadence

- **Patch (`1.0.x`)**: as needed. Bugfixes, docs.
- **Minor (`1.x.0`)**: approximately quarterly. New modes, new integrations, new profiles.
- **Major (`x.0.0`)**: only for breaking changes. Deprecation warnings published in previous minor.

## Versioning

Semver 2.0.0. See [CHANGELOG.md](CHANGELOG.md).

## Branch model

- `main`: always releasable. Protected. Tests green required.
- Feature branches: off `main`, merged via PR.
- Tags: `vMAJOR.MINOR.PATCH` on merge commits.

## How to become a maintainer

Sustained, high-quality contributions over 3+ months. Existing maintainers invite new ones; no application process.

## Conflicts of interest

Maintainers should abstain from reviewing their own PRs (GitHub enforces this by default) and disclose any commercial interest in a PR they review.

## Forking

You are free to fork, modify, and distribute under MIT. Forks that add commercial features or proprietary modes should rename the project to avoid brand confusion.
