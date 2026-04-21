# Cognito v2.0.0-rc1 — Verification commands

Every claim in the `[2.0.0-rc1]` entry of `CHANGELOG.md` is backed by one of
the commands below. Run them yourself — they write nothing outside the
repo and clean up after themselves.

## 1. Tests

```bash
python -m pytest tests/unit tests/integration -q
# Expected: 269 passed, 18 skipped (as of 2026-04-19, Windows Python 3.14).
```

## 2. Coverage

```bash
python -m pytest tests/unit tests/integration \
  --cov=hooks.python --cov=integrations --cov-report=term -q
# Expected: TOTAL 902 stmts / 57 % cover.
# Per-module: _common 73 %, phase_detector 82 %, gate_validator 84 %,
# mode_injector 58 %, session_closer 82 %, sinapsis_bridge 75 %,
# _daemon 17 %.
# Daemon is exercised end-to-end via subprocess in
# test_v2_daemon_and_collapse.py; pytest-cov does not instrument those child
# processes without COVERAGE_PROCESS_START wiring (v2.1 target).
```

## 3. Daemon latency benchmark

```bash
# Clean slate
rm -rf runtime logs/daemon.log 2>/dev/null

# OFF (v1.2 cold-start path)
for i in 1 2 3 4 5; do
  t0=$(python3 -c "import time; print(time.time_ns())")
  bash hooks/phase-detector.sh < tests/fixtures/typical-prompt.json >/dev/null 2>&1
  t1=$(python3 -c "import time; print(time.time_ns())")
  echo "cold run $i: $(( (t1 - t0) / 1000000 )) ms"
done

# ON
bash scripts/cognito-daemon.sh start
sleep 0.5
for i in 1 2 3 4 5; do
  t0=$(python3 -c "import time; print(time.time_ns())")
  bash hooks/phase-detector.sh < tests/fixtures/typical-prompt.json >/dev/null 2>&1
  t1=$(python3 -c "import time; print(time.time_ns())")
  echo "hot run $i: $(( (t1 - t0) / 1000000 )) ms"
done
bash scripts/cognito-daemon.sh stop
```

Expected on Windows Git Bash + Python 3.14:
- cold avg ≈ 635 ms
- hot  avg ≈ 495 ms
- Δ ≈ −140 ms (~22 %). NOT "90 % faster" — see CHANGELOG for why.

## 4. Daemon lifecycle end-to-end

```bash
bash scripts/cognito-daemon.sh status    # → "down: no pid file ..."
bash scripts/cognito-daemon.sh start     # → "started pid <n>"
bash scripts/cognito-daemon.sh status    # → "running: pid <n>  addr/socket ..."
bash hooks/phase-detector.sh < tests/fixtures/typical-prompt.json
echo "exit: $?"                           # → 0
bash scripts/cognito-daemon.sh stop      # → "stopped pid <n>"
bash scripts/cognito-daemon.sh status    # → "down: no pid file ..."
```

## 5. Collapse v2 behavior

```bash
# With collapseV2=false (default), Estratega appears as its own header:
python3 -c "
import json, shutil, subprocess, tempfile, os, sys
from pathlib import Path
repo = Path('.').resolve()
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / 'cog'
    shutil.copytree(repo, d, ignore=shutil.ignore_patterns('__pycache__','.git','.pytest_cache','tests','node_modules','runtime','logs'))
    shutil.copy(d/'config/_phase-state.default.json', d/'config/_phase-state.json')
    cfg = json.loads((d/'config/_operator-config.json').read_text('utf-8'))
    cfg.setdefault('modes',{})['enabled']=['divergente','estratega']
    cfg['modes']['disabled']=[]
    cfg['modes']['collapseV2']=False
    (d/'config/_operator-config.json').write_text(json.dumps(cfg,indent=2),'utf-8')
    env = os.environ.copy()
    env.update(COGNITO_DIR=str(d), COGNITO_DIR_RESOLVED=str(d), INPUT_JSON='{}')
    r = subprocess.run([sys.executable,'hooks/python/mode_injector.py'],env=env,capture_output=True,text=True)
    assert 'Modo activo: estratega' in r.stdout and 'preset:' not in r.stdout
    print('collapse off: estratega preserved')
    cfg['modes']['collapseV2']=True
    (d/'config/_operator-config.json').write_text(json.dumps(cfg,indent=2),'utf-8')
    r = subprocess.run([sys.executable,'hooks/python/mode_injector.py'],env=env,capture_output=True,text=True)
    assert 'Modo activo: estratega' not in r.stdout
    assert 'Modo activo: divergente (preset: time-horizon)' in r.stdout
    print('collapse on : estratega collapsed into divergente+preset')
"
```

## 6. Marketplace local install

```bash
# (skipped on Windows — POSIX mktemp/curl)
tmp=$(mktemp -d)
echo -e '---\nname: demo\n---\n# Demo mode' > "$tmp/SKILL.md"
bash scripts/install-mode.sh --local="$tmp/SKILL.md" --target="$tmp/inst" demo
test -f "$tmp/inst/modes/custom/demo/SKILL.md" && echo "install ok" || echo "FAIL"
rm -rf "$tmp"
```
