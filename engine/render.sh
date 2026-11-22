#!/usr/bin/env bash
# VPS target of the remotion renderer. render.sh <job-dir> <out.mp4|out.jpg>  (a .jpg output renders the cover still, job.json still_composition)
#   render.sh --slides <job-dir> <out-dir>  carousel slides (job.json slides_composition): <out-dir>/ig/NN.jpg, pin/NN.jpg, slides.json (SLA-1573)
# Runs render-job.mjs under watchdog.sh (nice 15, one reel at a time, RSS / MemAvailable / wall limits).
# Runtime (node_modules, Chrome headless shell, user-space lib bundle, bundle cache, fonts) lives in RF_REMOTION_HOME,
# outside the read-only skill dir, and is built once. Never prints env values.
set -euo pipefail
SLIDES=0; [ "${1:-}" = "--slides" ] && { SLIDES=1; shift; }
JOB=${1:?usage: render.sh [--slides] <job-dir> <out.mp4>}; OUT=${2:?usage: render.sh <job-dir> <out.mp4>}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RT=${RF_REMOTION_HOME:-${REEL_FACTORY_HOME:?set REEL_FACTORY_HOME or RF_REMOTION_HOME}/remotion-runtime}
MIN_AVAIL_MB=${MIN_AVAIL_MB:-600}; START_AVAIL_MB=${RF_START_AVAIL_MB:-1024}
export MAX_RSS_MB=${MAX_RSS_MB:-2800} MIN_AVAIL_MB MAX_SECS=${MAX_SECS:-1500}
mkdir -p "$RT" "$JOB"; JOB=$(cd "$JOB" && pwd); OUT=$(mkdir -p "$(dirname "$OUT")" && cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")

exec 9>"$RT/render.lock"
flock -n 9 || { echo "render.sh: another remotion render is running on this box (concurrency 1)" >&2; exit 75; }

avail=$(( $(awk '/MemAvailable/{print $2}' /proc/meminfo) / 1024 ))
[ "$avail" -ge "$START_AVAIL_MB" ] || { echo "render.sh: MemAvailable ${avail} MB < ${START_AVAIL_MB} MB, not starting" >&2; exit 75; }

# 1. app copy with node_modules (re-synced when the sources change, npm ci only when the lock changes)
APP="$RT/app"; mkdir -p "$APP"
for f in package.json package-lock.json render-job.mjs bitrate.mjs; do if [ -f "$HERE/$f" ]; then cp "$HERE/$f" "$APP/$f"; fi; done
for d in src compositions fonts; do rm -rf "$APP/$d"; cp -r "$HERE/$d" "$APP/$d"; done
want=$(cat "$APP/package.json" "$APP/package-lock.json" 2>/dev/null | sha1sum | cut -c1-16)
if [ "$(cat "$APP/.deps" 2>/dev/null)" != "$want" ]; then
  echo "render.sh: installing node dependencies"; (cd "$APP" && if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi)
  echo "$want" > "$APP/.deps"
fi
export RF_REMOTION_HOME="$RT/cache"

# 2. Chrome headless shell + user-space libs (no root): fetch-libs.py is only needed on a box that lacks the shared libraries
CHROME=$(find "$APP/node_modules/.remotion" -name chrome-headless-shell -type f 2>/dev/null | head -1 || true)
if [ -z "$CHROME" ]; then (cd "$APP" && node render-job.mjs --ensure-browser >/dev/null); CHROME=$(find "$APP/node_modules/.remotion" -name chrome-headless-shell -type f | head -1); fi
LIBDIRS="$RT/libs/usr/lib/x86_64-linux-gnu:$RT/libs/lib/x86_64-linux-gnu"
if LD_LIBRARY_PATH="$LIBDIRS" ldd "$CHROME" 2>/dev/null | grep -q "not found"; then
  echo "render.sh: fetching the user-space lib bundle for headless Chrome"; RF_LIBS_DIR="$RT/libs" python3 "$HERE/fetch-libs.py" "$CHROME" >/dev/null
fi
cat > "$RT/chrome-wrapper.sh" <<WRAP
#!/usr/bin/env bash
export LD_LIBRARY_PATH="$LIBDIRS\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
exec "$CHROME" "\$@"
WRAP
chmod +x "$RT/chrome-wrapper.sh"; export RF_BROWSER="$RT/chrome-wrapper.sh"

# 3. fonts for Chrome (system font lookup only; the compositions load their own web fonts from public/fonts)
mkdir -p "$RT/fonts" "$RT/fontcache"; cp -u "$HERE"/fonts/* "$RT/fonts/" 2>/dev/null || true
[ -d "$JOB/public/fonts" ] && cp -u "$JOB"/public/fonts/* "$RT/fonts/" 2>/dev/null || true
cat > "$RT/fonts.conf" <<FC
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>$RT/fonts</dir>
  <cachedir>$RT/fontcache</cachedir>
  <alias><family>sans-serif</family><prefer><family>Montserrat</family></prefer></alias>
</fontconfig>
FC
export FONTCONFIG_FILE="$RT/fonts.conf" RF_CONCURRENCY=${RF_CONCURRENCY:-1}

# 4. render under the watchdog (kills the whole tree on a breach, exit 137)
if [ "$SLIDES" = 1 ]; then
  # the slide plan is TypeScript (compositions/facemetric/slides/plan.ts) loaded by node itself, so node must strip types
  rm -rf "$OUT"; cd "$APP"; set +e
  NODE_OPTIONS="${NODE_OPTIONS:-} --experimental-strip-types --no-warnings" "$HERE/watchdog.sh" "$JOB/watchdog" -- node "$APP/render-job.mjs" --slides "$JOB" "$OUT"
  rc=$?; set -e
  [ "$rc" -eq 0 ] && [ -s "$OUT/slides.json" ] && echo "render.sh: wrote $OUT"
  exit $rc
fi
case "$OUT" in
  *.jpg) PART="${OUT%.jpg}.part.jpg"; MODE=(--still) ;;  # Remotion validates the extension
  *)     PART="${OUT%.mp4}.part.mp4"; MODE=() ;;
esac
rm -f "$OUT"
cd "$APP"
set +e
"$HERE/watchdog.sh" "$JOB/watchdog" -- node "$APP/render-job.mjs" ${MODE[@]+"${MODE[@]}"} "$JOB" "$PART"
rc=$?
set -e
[ "$rc" -eq 0 ] && [ -s "$PART" ] && mv "$PART" "$OUT" \
  && echo "render.sh: wrote $OUT"
rm -f "$PART"
exit $rc
