#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
SITE_DIR="$DEMO_DIR/site"
SCREENSHOTS_DIR="$DEMO_DIR/screenshots"
LINKS_PATH="$DEMO_DIR/canonical_links.txt"
CAST_FILE="$DEMO_DIR/demo.cast"
GIF_FILE="$DEMO_DIR/demo.gif"
PORT=8765

if ! command -v agg &>/dev/null; then
    echo "Error: agg is required to generate the GIF."
    echo "Install with: brew install agg"
    exit 1
fi

cd "$SITE_DIR"
echo "Starting local server..."
python3 -m http.server "$PORT" >/dev/null 2>&1 &
SERVER_PID=$!
sleep 1

cleanup() {
    echo "Stopping server..."
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

rm -f "$CAST_FILE" "$GIF_FILE"
rm -rf "$SCREENSHOTS_DIR" "$LINKS_PATH"

echo "Recording demo with asciinema..."
echo ""

uv run asciinema rec "$CAST_FILE" --overwrite --cols 120 --rows 48 --command "DEMO_DIR=$DEMO_DIR bash $DEMO_DIR/_demo_run.sh"

echo ""
echo "Converting recording to GIF..."
agg --font-size 14 "$CAST_FILE" "$GIF_FILE"

echo ""
echo "Done!"
echo "  Cast:        $CAST_FILE"
echo "  GIF:         $GIF_FILE"
echo "  Screenshots: $SCREENSHOTS_DIR/"
echo "  Links:       $LINKS_PATH"
