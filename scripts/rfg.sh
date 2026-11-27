#!/usr/bin/env bash
# reel-famous-genz entrypoint: rfg.sh <command> [args]  (see SKILL.md). Stdlib python; node + sharp only for the chroma key; reel-factory's pylib for the clip morph.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export RFG_HOME=${RFG_HOME:-/paperclip/instances/default/data/reel-famous-genz/${PAPERCLIP_COMPANY_ID:-default}}
if [ -z "${RF_SHARP:-}" ]; then
  RF_SHARP=$(ls -d /app/node_modules/.pnpm/sharp@*/node_modules 2>/dev/null | head -1 || true); export RF_SHARP
fi
# SLA-1728: the clip morph opener needs PIL, numpy, OpenCV and mediapipe: reel-factory's pylib (plus the libEGL/libGLESv2 libmediapipe.so
# links against in its _syslib); without it the reel keeps its still hook
RF_PYLIB="${RF_PYLIB:-/paperclip/instances/default/data/reel-factory/pylib}"
if [ -d "$RF_PYLIB" ]; then
  export PYTHONPATH="$RF_PYLIB${PYTHONPATH:+:$PYTHONPATH}"
  export LD_LIBRARY_PATH="$RF_PYLIB/_syslib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
cd "$HERE"
exec python3 rfg.py "$@"
