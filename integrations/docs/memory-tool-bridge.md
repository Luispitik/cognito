# Sinapsis → Claude memory_20250818 bridge

**Stage:** v2.2 — opt-in, no default wiring.
**Module:** `integrations/sinapsis_bridge.py`
**Method:** `SinapsisBridge.to_memory_tool_entries()`

Cognito never calls the Claude API directly. But when an **operator** drives
Claude with the [`memory_20250818`](https://docs.claude.com/en/docs/build-with-claude/memory)
tool, they often want Sinapsis's confirmed/permanent instincts to land in the
model's persistent memory on first contact instead of re-injecting them as
system text on every request.

This bridge provides that conversion — and nothing else.

---

## What it returns

```python
bridge = SinapsisBridge.detect()
entries = bridge.to_memory_tool_entries(limit=20, scope="global")
```

Each entry is a dict in the exact shape the memory tool expects when you
invoke the `create` command:

```json
{
  "command": "create",
  "path": "/memories/global/supabase-siempre-rls.md",
  "content": "# Supabase siempre RLS\n\nCuando uses Supabase, activar RLS...\n\n_confidence: permanent · occurrences: 42 · domain: backend, supabase · scope: global · sinapsis: v4.3.0_"
}
```

Contract guarantees (covered by `tests/unit/test_sinapsis_memory_bridge.py`):

| Property             | Guarantee                                                   |
| -------------------- | ----------------------------------------------------------- |
| `command`            | Always `"create"` in v2.2 (write-only, no view/rename).     |
| `path`               | POSIX-style (`/` only), starts with `base_path`, `.md`.     |
| `path` uniqueness    | Duplicate slugs get `-2`, `-3`, ... suffixes.               |
| Unsafe chars         | `/`, `\`, `:`, `*`, etc. in instinct IDs are replaced.      |
| `content`            | Markdown with H1 title, rule body, metadata footer.         |
| `content` length     | Capped (~1 KB) — original payload stays in Sinapsis.        |
| Empty input          | Returns `[]` if bridge unavailable or index empty.          |
| Draft instincts      | Excluded (same filter as `get_active_instincts`).           |

---

## Why this is opt-in

Cognito is model-neutral. Writing to Claude's memory tool means:

1. The caller is running Claude (not another LLM).
2. The caller explicitly wants memory persistence across sessions.
3. The caller accepts the cost of larger memory store over time.

None of those assumptions hold for every Cognito user, so the method exists
but **no hook or command in Cognito invokes it**. The operator owns the wiring.

---

## Minimal integration pattern

Pseudocode for an operator-side helper that warms the memory store once per
new session (call this from your own code, not from Cognito hooks):

```python
from pathlib import Path
import anthropic
from cognito.integrations.sinapsis_bridge import SinapsisBridge

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY

bridge = SinapsisBridge.detect()
if not bridge.available:
    return  # Sinapsis not installed — nothing to seed

entries = bridge.to_memory_tool_entries(limit=30, scope="global")
if not entries:
    return

# Your memory-tool adapter. The SDK exposes the memory tool as a normal tool
# call; your harness inspects tool_use blocks and replays them through a
# file-backed handler. Example sketch:
memory_root = Path("~/.cognito/memory").expanduser()
memory_root.mkdir(parents=True, exist_ok=True)

for entry in entries:
    # strip leading slash so we can join under memory_root safely
    rel = entry["path"].lstrip("/")
    target = memory_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(entry["content"], encoding="utf-8")
```

When Claude next runs with the memory tool enabled, it sees the seeded
`/memories/global/*.md` files via the tool's `view` command.

---

## What's intentionally missing

- **No `str_replace` / `insert` / `delete` entries.** v2.2 only seeds fresh
  state. Updates happen naturally through Sinapsis's own pipeline and the
  operator re-runs the bridge when they want to refresh.
- **No SDK client inside Cognito.** `sinapsis_bridge.py` depends only on
  stdlib. All network calls live in the operator's code.
- **No auto-invocation from hooks.** Hooks run on every prompt; memory writes
  should be rare. Keep them where you can batch them.
- **No rename/deletion of removed instincts.** If Sinapsis expires an instinct,
  the memory file lingers until the operator cleans up. That's the trade-off
  for keeping Cognito stateless.

---

## Relation to `render_injection`

Both methods read the same `get_active_instincts` feed:

| Method                         | Purpose                                | Frequency           |
| ------------------------------ | -------------------------------------- | ------------------- |
| `render_injection(limit=10)`   | System-message inject, per-prompt      | Every turn (cheap)  |
| `to_memory_tool_entries(...)`  | Seed Claude memory tool, per-session   | Rare (once)         |

You can use both — there's no conflict. The injected block is transient; the
memory entries are persistent across sessions. Most operators will want
render-injection as the default and only reach for the memory bridge when they
operate a long-running coding agent where re-sending the full instinct block
wastes tokens.

---

## Testing

Run just the bridge tests:

```bash
python -m pytest tests/unit/test_sinapsis_memory_bridge.py -v
```

12 tests cover: shape, opt-in, slugify, dedup, scope/limit filters, metadata
in content, custom `base_path`, and `base_path` normalisation.
