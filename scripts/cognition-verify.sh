#!/usr/bin/env bash
# =============================================================================
# Cognito — health check (v1.1.0+)
# =============================================================================
# Ran by `/cognition-status --verify` (or directly).
# Reports OK / WARN / FAIL per check. Exit code != 0 if any FAIL.
#
# Usage:
#   bash scripts/cognition-verify.sh
#   bash scripts/cognition-verify.sh --target=/custom/path
#   bash scripts/cognition-verify.sh --settings=/custom/settings.json
#   bash scripts/cognition-verify.sh --json            # machine-readable
# =============================================================================

set -uo pipefail

TARGET_DIR="${HOME}/.claude/cognito"
SETTINGS_FILE="${HOME}/.claude/settings.json"
JSON_OUT=0

for arg in "$@"; do
    case "$arg" in
        --target=*)   TARGET_DIR="${arg#*=}"    ;;
        --settings=*) SETTINGS_FILE="${arg#*=}" ;;
        --json)       JSON_OUT=1                ;;
        --help|-h)
            cat <<'EOF'
Usage: bash scripts/cognition-verify.sh [options]

Options:
  --target=PATH     install dir (default: ~/.claude/cognito)
  --settings=PATH   settings.json (default: ~/.claude/settings.json)
  --json            emit JSON lines instead of human-readable
EOF
            exit 0
            ;;
    esac
done

export TARGET_DIR SETTINGS_FILE JSON_OUT

python3 <<'PYEOF'
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TARGET = Path(os.environ["TARGET_DIR"])
SETTINGS = Path(os.environ["SETTINGS_FILE"])
JSON_OUT = os.environ.get("JSON_OUT") == "1"

results = []

def check(name: str, status: str, detail: str = ""):
    """status in {ok, warn, fail}."""
    results.append({"name": name, "status": status, "detail": detail})

# 1. Python version
py = sys.version_info
if py >= (3, 10):
    check("python-3.10+", "ok", f"python {py.major}.{py.minor}.{py.micro}")
else:
    check("python-3.10+", "fail", f"found {py.major}.{py.minor}; Cognito requires 3.10+")

# 2. jq present (strongly recommended for install/uninstall settings.json merge)
if shutil.which("jq"):
    check("jq", "ok")
else:
    check("jq", "warn", "jq not on PATH — install.sh falls back to printing snippet")

# 3. Install dir exists
if TARGET.is_dir():
    check("install-dir", "ok", str(TARGET))
else:
    check("install-dir", "fail", f"not found: {TARGET}")
    # Early exit: nothing else works without the install dir.
    for r in results:
        if JSON_OUT:
            print(json.dumps(r))
        else:
            icon = {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}[r["status"]]
            print(f"[{icon}] {r['name']:<24} {r['detail']}")
    sys.exit(1 if any(r["status"] == "fail" for r in results) else 0)

# 4. Each config JSON exists and parses
EXPECTED_JSONS = [
    "_modes.json",
    "_phases.json",
    "_passive-triggers.json",
    "_operator-config.json",
    "_phase-state.json",
    "_phase-state.default.json",
]
for name in EXPECTED_JSONS:
    path = TARGET / "config" / name
    if not path.is_file():
        check(f"config/{name}", "fail", "missing")
        continue
    try:
        with open(path, encoding="utf-8") as f:
            json.load(f)
        check(f"config/{name}", "ok")
    except Exception as e:
        check(f"config/{name}", "fail", f"invalid JSON: {e}")

# 5. Regex patterns compile (passive-triggers)
try:
    with open(TARGET / "config" / "_passive-triggers.json", encoding="utf-8") as f:
        trig = json.load(f)
    bad = 0
    for rule in trig.get("gates", {}).get("rules", []):
        pat = rule.get("pattern", "")
        try:
            re.compile(pat)
        except re.error:
            bad += 1
    for rule in trig.get("anchorDetection", {}).get("rules", []):
        pat = rule.get("pattern", "").lower().replace("[x]", ".+")
        if not pat:
            continue
        try:
            re.compile(pat)
        except re.error:
            bad += 1
    if bad == 0:
        check("regex-patterns", "ok", "all regex patterns compile")
    else:
        check("regex-patterns", "warn", f"{bad} pattern(s) failed to compile")
except Exception as e:
    check("regex-patterns", "warn", f"could not inspect: {e}")

# 6. Hook scripts present + executable
HOOKS = ["phase-detector.sh", "mode-injector.sh", "gate-validator.sh", "session-closer.sh"]
for h in HOOKS:
    path = TARGET / "hooks" / h
    if not path.is_file():
        check(f"hooks/{h}", "warn", "missing (profile may not install this hook)")
        continue
    mode = path.stat().st_mode
    if mode & 0o111:
        check(f"hooks/{h}", "ok")
    else:
        check(f"hooks/{h}", "warn", "not executable (chmod +x)")

# 7. settings.json has the cognito-* hooks registered
if not SETTINGS.is_file():
    check("settings.json", "warn", f"not found: {SETTINGS}")
else:
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            stg = json.load(f)
        hooks_block = (stg or {}).get("hooks") or {}
        installed_hooks = [h for h in HOOKS if (TARGET / "hooks" / h).is_file()]
        registered = set()
        for event, entries in hooks_block.items():
            for entry in entries or []:
                name = entry.get("name", "")
                if name.startswith("cognito-"):
                    registered.add(name.replace("cognito-", "") + ".sh")
        missing = [h for h in installed_hooks if h not in registered]
        if not installed_hooks:
            check("settings-hooks", "warn", "no hooks installed to register")
        elif not missing:
            check("settings-hooks", "ok", f"{len(registered)} cognito-* hook(s) registered")
        else:
            check("settings-hooks", "warn", f"unregistered: {', '.join(missing)}")
    except Exception as e:
        check("settings-hooks", "warn", f"could not read settings.json: {e}")

# 8. _phase-state writable
ps = TARGET / "config" / "_phase-state.json"
if ps.is_file() and os.access(ps, os.W_OK):
    check("phase-state-writable", "ok")
else:
    check("phase-state-writable", "fail", f"{ps} not writable")

# 9. logs dir and sessions dir writable
for d in ("logs", "sessions"):
    path = TARGET / d
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".verify-write-test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        check(f"{d}-writable", "ok")
    except Exception as e:
        check(f"{d}-writable", "fail", str(e))

# 10. Sinapsis bridge: detectable or cleanly opt-out
try:
    bridge_path = TARGET / "integrations" / "sinapsis_bridge.py"
    op_cfg_path = TARGET / "config" / "_operator-config.json"
    op_cfg = {}
    if op_cfg_path.is_file():
        op_cfg = json.loads(op_cfg_path.read_text(encoding="utf-8"))
    sinapsis_declared = (op_cfg.get("integrations", {}) or {}).get("sinapsis", {}) or {}
    declared_installed = sinapsis_declared.get("installed", None)
    if not bridge_path.is_file():
        check("sinapsis-bridge", "warn", "bridge script missing (standalone mode)")
    else:
        # Try to import and run detect()
        sys.path.insert(0, str(TARGET / "integrations"))
        try:
            import importlib
            spec = importlib.util.spec_from_file_location("sinapsis_bridge", bridge_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            bridge = mod.SinapsisBridge.detect(operator_config=op_cfg)
            if bridge.available:
                check("sinapsis-bridge", "ok", f"detected v{bridge.version or '?'}")
            elif declared_installed is False:
                check("sinapsis-bridge", "ok", "opt-out honored (integrations.sinapsis.installed=false)")
            else:
                check("sinapsis-bridge", "ok", "standalone (no Sinapsis install detected)")
        except Exception as e:
            check("sinapsis-bridge", "warn", f"bridge import failed: {e}")
except Exception as e:
    check("sinapsis-bridge", "warn", str(e))

# ----- Emit results ----------------------------------------------------------
has_fail = any(r["status"] == "fail" for r in results)
n_warn = sum(1 for r in results if r["status"] == "warn")
n_ok = sum(1 for r in results if r["status"] == "ok")

if JSON_OUT:
    for r in results:
        print(json.dumps(r))
else:
    print("Cognito health check")
    print("=" * 56)
    for r in results:
        icon = {"ok": "ok  ", "warn": "WARN", "fail": "FAIL"}[r["status"]]
        detail = f" -- {r['detail']}" if r["detail"] else ""
        print(f"[{icon}] {r['name']:<26}{detail}")
    print("=" * 56)
    print(f"Summary: {n_ok} ok, {n_warn} warn, {sum(1 for r in results if r['status'] == 'fail')} fail")

sys.exit(1 if has_fail else 0)
PYEOF
