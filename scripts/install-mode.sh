#!/usr/bin/env bash
# =============================================================================
# Cognito - install-mode.sh (v2.0)
# =============================================================================
# Install a custom or community mode from a registry URL or local path.
#
# Registry format (JSON, hosted on GitHub raw or any HTTPS):
#   {
#     "modes": {
#       "<slug>": {
#         "name": "Display Name",
#         "url": "https://.../modes/<slug>/SKILL.md",
#         "sha256": "<hex>"
#       }
#     }
#   }
#
# Trust model (v2 intentionally minimal):
# - Registry JSON must be fetched over HTTPS.
# - If the entry carries sha256, the download is verified and refused on
#   mismatch.
# - Installed modes land under `modes/custom/<slug>/SKILL.md` and must be
#   enabled manually in `_operator-config.json` before they activate.
#
# Version: 2.0.0-rc1
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
REGISTRY_URL_DEFAULT="https://raw.githubusercontent.com/Luispitik/cognito-community/main/registry.json"

usage() {
    cat <<'EOF'
Usage: install-mode.sh [options] <slug>

Install a community mode under modes/custom/<slug>/.

Options:
  --registry=URL     Registry JSON URL (default: cognito-community main branch)
  --local=PATH       Install from a local SKILL.md instead of a remote fetch
  --target=PATH      Override the repo root (default: auto-detect)
  --list             List modes published in the registry and exit
  --force            Overwrite an existing modes/custom/<slug>/

Examples:
  install-mode.sh --list
  install-mode.sh socratic
  install-mode.sh --local=./mymode/SKILL.md mymode
EOF
}

REGISTRY_URL="$REGISTRY_URL_DEFAULT"
LOCAL_PATH=""
TARGET_DIR="$REPO_DIR"
LIST_ONLY=0
FORCE=0
SLUG=""

for arg in "$@"; do
    case "$arg" in
        --registry=*)  REGISTRY_URL="${arg#*=}" ;;
        --local=*)     LOCAL_PATH="${arg#*=}"  ;;
        --target=*)    TARGET_DIR="${arg#*=}"  ;;
        --list)        LIST_ONLY=1             ;;
        --force)       FORCE=1                 ;;
        -h|--help)     usage; exit 0           ;;
        -*)            echo "unknown flag: $arg" >&2; usage; exit 2 ;;
        *)             SLUG="$arg"             ;;
    esac
done

have() { command -v "$1" >/dev/null 2>&1; }

fetch_to() {
    # $1=url $2=outfile
    if have curl; then
        curl -fsSL "$1" -o "$2"
    elif have wget; then
        wget -qO "$2" "$1"
    else
        echo "need curl or wget" >&2
        return 1
    fi
}

if [ "$LIST_ONLY" = "1" ]; then
    tmp_registry=$(mktemp -t cognito-registry.XXXXXX)
    trap 'rm -f "$tmp_registry"' EXIT
    if ! fetch_to "$REGISTRY_URL" "$tmp_registry"; then
        echo "registry fetch failed: $REGISTRY_URL" >&2
        exit 1
    fi
    python3 - "$tmp_registry" <<'PYEOF'
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
modes = reg.get("modes", {})
if not modes:
    print("(registry has no modes)")
else:
    width = max(len(k) for k in modes)
    print(f"{'slug'.ljust(width)}  name")
    print("-" * (width + 30))
    for slug, meta in sorted(modes.items()):
        name = meta.get("name", "")
        print(f"{slug.ljust(width)}  {name}")
PYEOF
    exit 0
fi

if [ -z "$SLUG" ]; then
    usage; exit 2
fi

dest_dir="$TARGET_DIR/modes/custom/$SLUG"
if [ -d "$dest_dir" ] && [ "$FORCE" != "1" ]; then
    echo "mode already installed at $dest_dir (use --force to overwrite)" >&2
    exit 1
fi

mkdir -p "$dest_dir"
skill_md="$dest_dir/SKILL.md"

if [ -n "$LOCAL_PATH" ]; then
    if [ ! -f "$LOCAL_PATH" ]; then
        echo "local file not found: $LOCAL_PATH" >&2
        exit 1
    fi
    cp "$LOCAL_PATH" "$skill_md"
    echo "installed local mode -> $skill_md"
    echo "NOTE: add '$SLUG' to config/_operator-config.json → modes.enabled to activate."
    exit 0
fi

tmp_registry=$(mktemp -t cognito-registry.XXXXXX)
trap 'rm -f "$tmp_registry"' EXIT
if ! fetch_to "$REGISTRY_URL" "$tmp_registry"; then
    echo "registry fetch failed: $REGISTRY_URL" >&2
    exit 1
fi

meta=$(python3 - "$tmp_registry" "$SLUG" <<'PYEOF'
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
entry = reg.get("modes", {}).get(sys.argv[2])
if not entry:
    sys.exit(3)
print(entry.get("url", ""))
print(entry.get("sha256", ""))
print(entry.get("name", ""))
PYEOF
)
case "$?" in
    0) ;;
    3) echo "slug not in registry: $SLUG" >&2; exit 1 ;;
    *) echo "failed to parse registry" >&2; exit 1 ;;
esac

url=$(printf '%s\n' "$meta" | sed -n '1p')
sha=$(printf '%s\n' "$meta" | sed -n '2p')
name=$(printf '%s\n' "$meta" | sed -n '3p')

if [ -z "$url" ]; then
    echo "registry entry missing url" >&2
    exit 1
fi

echo "fetching $name ($SLUG) from $url"
if ! fetch_to "$url" "$skill_md"; then
    rm -rf "$dest_dir"
    echo "download failed" >&2
    exit 1
fi

if [ -n "$sha" ]; then
    actual=$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$skill_md")
    if [ "$actual" != "$sha" ]; then
        rm -rf "$dest_dir"
        echo "sha256 mismatch: expected $sha got $actual" >&2
        exit 1
    fi
    echo "   sha256 ok"
fi

echo "installed $SLUG -> $skill_md"
echo "NOTE: add '$SLUG' to config/_operator-config.json → modes.enabled to activate."
