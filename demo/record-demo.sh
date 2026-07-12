#!/usr/bin/env bash
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
CAST_FILE="$DEMO_DIR/demo.cast"
GIF_FILE="$DEMO_DIR/demo.gif"

if ! command -v agg &>/dev/null; then
    echo "Error: agg is required to generate the GIF."
    echo "Install with: brew install agg"
    exit 1
fi

rm -f "$CAST_FILE" "$GIF_FILE"

echo "Recording demo with asciinema..."
echo ""

uv run asciinema rec "$CAST_FILE" --overwrite --command "bash $DEMO_DIR/demo.sh"

echo ""
echo "Converting recording to GIF..."
agg "$CAST_FILE" "$GIF_FILE"

echo ""
echo "Done!"
echo "  Cast: $CAST_FILE"
echo "  GIF:  $GIF_FILE"