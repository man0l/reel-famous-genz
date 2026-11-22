#!/usr/bin/env bash
# reel-famous-genz entrypoint: rfg.sh <command> [args]  (see SKILL.md). Stdlib python; node + sharp only for the chroma key.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export RFG_HOME=${RFG_HOME:-/paperclip/instances/default/data/reel-famous-genz/${PAPERCLIP_COMPANY_ID:-default}}
if [ -z "${RF_SHARP:-}" ]; then
  RF_SHARP=$(ls -d /app/node_modules/.pnpm/sharp@*/node_modules 2>/dev/null | head -1 || true); export RF_SHARP
fi
cd "$HERE"
exec python3 rfg.py "$@"
