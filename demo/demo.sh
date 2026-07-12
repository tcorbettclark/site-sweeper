#!/usr/bin/env bash
set -euo pipefail

PORT=8765
DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
SITE_DIR="$DEMO_DIR/site"
SCREENSHOTS_DIR="$DEMO_DIR/screenshots"
LINKS_PATH="$DEMO_DIR/canonical_links.txt"

cd "$SITE_DIR"

echo "Starting local server on port $PORT..."
python3 -m http.server $PORT >/dev/null 2>&1 &
SERVER_PID=$!
sleep 1

cleanup() {
    echo "Stopping server..."
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "Running site-sweeper against http://localhost:$PORT"
echo ""

site-sweeper http://localhost:$PORT \
    --screenshots \
    --screenshots-dir "$SCREENSHOTS_DIR" \
    --links \
    --links-path "$LINKS_PATH" \
    --canonical \
    --external

echo ""
echo "Demo complete!"
echo "  Screenshots: $SCREENSHOTS_DIR/"
echo "  Canonical links: $LINKS_PATH"