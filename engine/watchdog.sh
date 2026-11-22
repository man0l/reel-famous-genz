#!/usr/bin/env bash
# watchdog.sh <label> -- <command...>
# Runs the command in its own session at nice 15, samples the process tree every 2 s and
# kills the whole tree if it breaches: tree RSS > MAX_RSS_MB, MemAvailable < MIN_AVAIL_MB,
# or wall time > MAX_SECS. Writes <label>.csv (samples) and <label>.summary.
set -u
LABEL="$1"; shift; [ "$1" = "--" ] && shift
MAX_RSS_MB=${MAX_RSS_MB:-2800}
MIN_AVAIL_MB=${MIN_AVAIL_MB:-600}
MAX_SECS=${MAX_SECS:-900}
OUT="${LABEL}.csv"; SUM="${LABEL}.summary"
echo "t_s,tree_rss_mb,tree_cpu_pct,mem_avail_mb,load1,nproc_tree" > "$OUT"

setsid nice -n 15 "$@" > "${LABEL}.log" 2>&1 &
PID=$!
START=$(date +%s)
PEAK=0; PEAK_AVAIL_DROP=0; MIN_AVAIL=999999; REASON=ok
prev_cpu=0; prev_t=$START

tree_pids() { # all pids whose session id == PID
  for p in /proc/[0-9]*; do
    s=$(awk '{print $6}' "$p/stat" 2>/dev/null) || continue
    [ "$s" = "$PID" ] && echo "${p#/proc/}"
  done
}

while kill -0 "$PID" 2>/dev/null; do
  sleep 2
  now=$(date +%s); t=$((now-START))
  rss=0; cpu=0; n=0
  for p in $(tree_pids); do
    r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null); rss=$((rss + ${r:-0}))
    c=$(awk '{print $14+$15}' /proc/$p/stat 2>/dev/null); cpu=$((cpu + ${c:-0}))
    n=$((n+1))
  done
  rss_mb=$((rss/1024))
  avail_mb=$(( $(awk '/MemAvailable/{print $2}' /proc/meminfo) / 1024 ))
  load1=$(cut -d' ' -f1 /proc/loadavg)
  dt=$((now-prev_t)); [ $dt -lt 1 ] && dt=1
  cpu_pct=$(( (cpu - prev_cpu) * 100 / 100 / dt )); prev_cpu=$cpu; prev_t=$now
  echo "$t,$rss_mb,$cpu_pct,$avail_mb,$load1,$n" >> "$OUT"
  [ $rss_mb -gt $PEAK ] && PEAK=$rss_mb
  [ $avail_mb -lt $MIN_AVAIL ] && MIN_AVAIL=$avail_mb
  if [ $rss_mb -gt $MAX_RSS_MB ]; then REASON="killed: tree RSS ${rss_mb}MB > ${MAX_RSS_MB}MB"; break; fi
  if [ $avail_mb -lt $MIN_AVAIL_MB ]; then REASON="killed: MemAvailable ${avail_mb}MB < ${MIN_AVAIL_MB}MB"; break; fi
  if [ $t -gt $MAX_SECS ]; then REASON="killed: wall ${t}s > ${MAX_SECS}s"; break; fi
done

if [ "$REASON" != ok ]; then
  kill -TERM -- -"$PID" 2>/dev/null; sleep 3; kill -KILL -- -"$PID" 2>/dev/null
  EXIT=137
else
  wait "$PID"; EXIT=$?
fi
END=$(date +%s)
{
  echo "label=$LABEL"
  echo "exit=$EXIT"
  echo "reason=$REASON"
  echo "wall_s=$((END-START))"
  echo "peak_tree_rss_mb=$PEAK"
  echo "min_mem_avail_mb=$MIN_AVAIL"
  echo "limits: rss>${MAX_RSS_MB}MB avail<${MIN_AVAIL_MB}MB wall>${MAX_SECS}s nice=15"
} | tee "$SUM"
exit $EXIT
