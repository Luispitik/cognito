"""Cognito hook modules (v1.2).

Heredocs extracted from `hooks/*.sh` into importable Python for:
- Real subprocess-independent test coverage (pytest-cov tracks imports).
- No more bash quoting traps.
- Portable invocation: `python3 -m hooks.python.<name>` works on Windows,
  macOS and Linux without `cygpath`.

The bash wrappers in `hooks/*.sh` remain as thin dispatchers so existing
Claude Code hook registrations (which invoke `bash hooks/<name>.sh`) keep
working unchanged.
"""
