#!/usr/bin/env bash
set -euo pipefail

SCREENSHOTS_DIR="$DEMO_DIR/screenshots"
LINKS_PATH="$DEMO_DIR/canonical_links.txt"
URL="http://localhost:8765"

type_cmd() {
    local cmd="$1"
    local delay="${2:-0.03}"
    local i char
    printf '\r\x1b[K$ '
    for (( i=0; i<${#cmd}; i++ )); do
        char="${cmd:$i:1}"
        printf '%s' "$char"
        sleep "$delay"
    done
    echo ""
}

type_cmd "site-sweeper $URL --external"

site-sweeper "$URL" \
    --screenshots \
    --screenshots-dir "$SCREENSHOTS_DIR" \
    --links \
    --links-path "$LINKS_PATH" \
    --canonical \
    --external

sleep 10
