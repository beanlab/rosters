#!/usr/bin/env bash
# Convert Markdown to standalone HTML and PDF without opening either output.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: render-md.sh <input.md> [output.html] [output.pdf]" >&2
  exit 2
fi

TOOLS_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
INPUT=$1
HTML=${2:-"${INPUT%.*}.html"}
PDF=${3:-"${INPUT%.*}.pdf"}

python3 "$TOOLS_DIR/md-to-html.py" "$INPUT" "$HTML"
node "$TOOLS_DIR/html-to-pdf.mjs" "$HTML" "$PDF"
