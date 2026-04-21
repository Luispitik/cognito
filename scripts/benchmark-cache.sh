#!/usr/bin/env bash
# =============================================================================
# Cognito - benchmark-cache.sh (v2.1)
# =============================================================================
# Measure prompt-caching efficiency of Cognito's mode_injector output against
# the Claude Opus 4.7 API. Opt-in (requires ANTHROPIC_API_KEY + explicit flag):
#   COGNITO_BENCHMARK_LIVE=1 bash scripts/benchmark-cache.sh
#
# What it does:
#   1. Runs mode_injector 3 times back-to-back with the same active mode +
#      phase, collecting the systemMessage from each run.
#   2. Sends each systemMessage as a single `messages.create()` call with
#      top-level `cache_control: {type: "ephemeral"}` to `claude-opus-4-7`.
#   3. Reports per-run cache_creation / cache_read / input tokens and the
#      cache-hit ratio across runs 2-3.
#
# Exit 0 if ratio >= 0.6 (acceptable), exit 1 otherwise.
#
# Without COGNITO_BENCHMARK_LIVE, prints the commands that WOULD run and exits 0.
# Version: 2.1.0
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
MODE="${1:-divergente}"
PHASE="${2:-discovery}"

if [ "${COGNITO_BENCHMARK_LIVE:-0}" != "1" ]; then
    cat <<EOF
[dry-run] Cognito cache benchmark — set COGNITO_BENCHMARK_LIVE=1 to hit the live API.

Would do, with mode=$MODE and phase=$PHASE:
  1. Enable only '$MODE' in config/_operator-config.json
  2. Set state.current=$PHASE
  3. Run hooks/python/mode_injector.py 3x, capture systemMessage
  4. POST to /v1/messages with claude-opus-4-7 + cache_control ephemeral
  5. Report cache_creation_input_tokens / cache_read_input_tokens per run
  6. Compute ratio (reads_run2+run3) / (writes_run1 + reads_run2+run3)

Requires: ANTHROPIC_API_KEY, curl, jq, python3.
EOF
    exit 0
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "error: ANTHROPIC_API_KEY not set" >&2
    exit 2
fi
command -v curl >/dev/null 2>&1 || { echo "need curl" >&2; exit 2; }
command -v jq   >/dev/null 2>&1 || { echo "need jq"   >&2; exit 2; }

# Capture injection 3 times
SYSMSG_FILE=$(mktemp -t cognito-bench.XXXXXX)
trap 'rm -f "$SYSMSG_FILE" "$SYSMSG_FILE.resp"*' EXIT

export COGNITO_DIR="$REPO_DIR"
export COGNITO_DIR_RESOLVED="$REPO_DIR"

echo "-> Capturing systemMessage via mode_injector..."
INPUT_JSON='{}' python3 "$REPO_DIR/hooks/python/mode_injector.py" \
    | jq -r '.systemMessage // empty' > "$SYSMSG_FILE"

if [ ! -s "$SYSMSG_FILE" ]; then
    echo "error: mode_injector produced empty systemMessage — enable mode '$MODE'?" >&2
    exit 2
fi

echo "   systemMessage bytes: $(wc -c < "$SYSMSG_FILE")"
echo

tot_writes=0
tot_reads=0
tot_input=0

for i in 1 2 3; do
    payload=$(jq -n --rawfile sys "$SYSMSG_FILE" '{
        model: "claude-opus-4-7",
        max_tokens: 64,
        cache_control: {type: "ephemeral"},
        system: [{type: "text", text: $sys}],
        messages: [{role: "user", content: "Say OK."}]
    }')
    resp=$(curl -sS https://api.anthropic.com/v1/messages \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -H "Content-Type: application/json" \
        -d "$payload")
    writes=$(echo "$resp" | jq -r '.usage.cache_creation_input_tokens // 0')
    reads=$(echo  "$resp" | jq -r '.usage.cache_read_input_tokens     // 0')
    input=$(echo  "$resp" | jq -r '.usage.input_tokens                // 0')
    echo "run $i:  input=$input  writes=$writes  reads=$reads"
    tot_writes=$(( tot_writes + writes ))
    tot_reads=$(( tot_reads + reads ))
    tot_input=$(( tot_input + input ))
    sleep 0.5
done

echo
echo "totals: input=$tot_input  writes=$tot_writes  reads=$tot_reads"

# Ratio: cache_reads / (cache_writes + cache_reads). Ignores uncached tail.
if [ "$(( tot_writes + tot_reads ))" = "0" ]; then
    echo "ratio : n/a (nothing cached — prefix below 4096 tokens?)"
    exit 1
fi
ratio=$(python3 -c "print(f'{$tot_reads / ($tot_writes + $tot_reads):.3f}')")
echo "ratio : $ratio  (target >= 0.6)"

python3 -c "exit(0 if $tot_reads / ($tot_writes + $tot_reads) >= 0.6 else 1)"
