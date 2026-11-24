// Beat timing, caption chunks, word windows and the cut plan of the genz-face reel. Pure. One voice clip per beat; beats sit on one
// clock (voice + pad, crossfade into the next, an end hold after the last).
import { END_HOLD_S, FPS, MIN_CUT_GAP_S, PAD_S, XFADE_S } from "./theme.ts";

/** Caption chunks: 3-6 words, break after . , ? ! once 3 words are in, a short tail joins the previous chunk. */
export function chunks(text: string): string[] {
  const words = text.split(/\s+/);
  const out: string[] = [];
  let cur: string[] = [];
  for (const w of words) {
    cur.push(w);
    if (cur.length >= 6 || (/[.,?!]$/.test(w) && cur.length >= 3)) {
      out.push(cur.join(" "));
      cur = [];
    }
  }
  if (cur.length) {
    if (cur.length < 3 && out.length) out[out.length - 1] += " " + cur.join(" ");
    else out.push(cur.join(" "));
  }
  return out;
}

/** Caption windows [from, to) in seconds of the beat: spread over the voice by character share, the last runs to the beat's end. */
export function captionWindows(parts: readonly string[], voice: number, end: number): [number, number][] {
  const tot = parts.reduce((n, c) => n + c.length, 0) || 1;
  let a = 0;
  return parts.map((c, j) => {
    const st = a;
    a += (voice * c.length) / tot;
    return [st, j === parts.length - 1 ? end : a];
  });
}

/** Index of the caption window showing at beat time t (seconds). The last window includes its end. */
export function captionAt(windows: readonly [number, number][], t: number): number {
  for (let j = 0; j < windows.length; j++) {
    const last = j === windows.length - 1;
    if (t >= windows[j][0] && (t < windows[j][1] || (last && t <= windows[j][1]))) return j;
  }
  return windows.length ? windows.length - 1 : -1;
}

export interface BeatTime {
  /** voice seconds (durations.json) */
  voice: number;
  /** seconds from this beat's start to the next beat's start (voice + pad, or + end hold) */
  span: number;
  /** seconds this beat stays on screen: span + the next beat's crossfade (not for the last) */
  shown: number;
  /** start in seconds */
  off: number;
  /** first frame / frames shown */
  from: number;
  frames: number;
}

export interface Timeline {
  beats: BeatTime[];
  /** whole reel, loop tail included */
  seconds: number;
  frames: number;
  /** first frame of the silent loop tail (= frames without one) */
  body: number;
}

/** `loop`: seconds of silent loop tail after the end hold (frame 0 held, SLA-1685); it adds frames and moves nothing else. `endHold`: hold
 * after the last clip (the IG cut shortens it, the loop tail carries the end). */
export function timeline(durations: readonly number[], fps = FPS, loop = 0, endHold = END_HOLD_S): Timeline {
  const n = durations.length;
  const beats: BeatTime[] = [];
  let off = 0;
  for (let i = 0; i < n; i++) {
    const last = i === n - 1;
    const span = durations[i] + (last ? endHold : PAD_S);
    beats.push({ voice: durations[i], span, shown: span + (last ? 0 : XFADE_S), off, from: Math.round(off * fps), frames: 0 });
    off += span;
  }
  const body = Math.round(off * fps);
  const tail = loop > 0 ? Math.round(loop * fps) : 0;
  beats.forEach((b, i) => {
    const end = i === n - 1 ? body : Math.round((b.off + b.shown) * fps);
    b.frames = Math.max(1, end - b.from);
  });
  return { beats, seconds: off + tail / fps, frames: body + tail, body };
}

/** Crossfade opacity of beat i at global time T (seconds): 1 for the first beat, else ramps 0 -> 1 over XFADE_S from its start. */
export function fadeIn(i: number, T: number, off: number): number {
  if (i === 0) return 1;
  return Math.min(1, Math.max(0, (T - off) / XFADE_S));
}

/** Lowercased word without punctuation, for matching a spoken word against a beat's `hot` list. */
export const bare = (w: string): string => w.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");

/** Word windows [from, to) in seconds of the beat for the words of one caption chunk starting at `from`: spread by character share. */
export function wordWindows(words: readonly string[], from: number, to: number): [number, number][] {
  const tot = words.reduce((n, w) => n + w.length, 0) || 1;
  let a = from;
  return words.map((w) => {
    const st = a;
    a += ((to - from) * w.length) / tot;
    return [st, a];
  });
}

export interface BeatPlan {
  time: BeatTime;
  parts: string[];
  windows: [number, number][];
  /** chunk indices that are visual cuts (pose swap, crop punch, callout pop); chunk 0 always is (the beat starts) */
  cuts: number[];
}

export interface Plan {
  tl: Timeline;
  beats: BeatPlan[];
  /** absolute seconds of every cut, in order */
  cutTimes: number[];
  cutsPerMin: number;
}

/** The cut plan: a chunk start is a cut when it is at least MIN_CUT_GAP_S after the previous cut, so the rate stays in 22-28 cuts a minute. */
export function plan(durations: readonly number[], vo: readonly string[], gap = MIN_CUT_GAP_S, loop = 0, endHold = END_HOLD_S): Plan {
  const tl = timeline(durations, FPS, loop, endHold);
  let last = -Infinity;
  const cutTimes: number[] = [];
  const beats = tl.beats.map((time, i) => {
    const parts = chunks(vo[i]);
    const windows = captionWindows(parts, time.voice, time.shown);
    const cuts: number[] = [];
    windows.forEach(([a], j) => {
      const abs = time.off + a;
      if (j === 0 || abs - last >= gap) {
        cuts.push(j);
        cutTimes.push(abs);
        last = abs;
      }
    });
    return { time, parts, windows, cuts };
  });
  return { tl, beats, cutTimes, cutsPerMin: cutTimes.length / (tl.body / FPS / 60) };
}

/** How many cuts have happened in the beat by chunk index j (pose / crop step). */
export const stepAt = (cuts: readonly number[], j: number): number => cuts.filter((c) => c <= j).length - 1;

/** Frames since the cut that started step `chunk`'s group, for the scale punch (0 at the cut). */
export function framesSinceCut(windows: readonly [number, number][], cuts: readonly number[], j: number, t: number, fps = FPS): number {
  const start = windows[cuts.filter((c) => c <= j).pop() ?? 0][0];
  return Math.max(0, Math.round((t - start) * fps));
}

/** SLA-1685 tease: what the top row shows at `frame`: the line during the hook only (board, 24 Nov: "hook only", like @glowupmenclub's
 * caption, which is up for the first seconds) and in the loop tail (frame 0 held), and the feature's place ("2/4") on a feature beat.
 * A beat counts from its first frame. */
export function teaseAt(kinds: readonly string[], tl: Timeline, frame: number): { line: boolean; n: number; of: number } {
  const of = kinds.filter((k) => k === "feature").length;
  const f = frame >= tl.body ? 0 : frame;
  let i = 0;
  while (i + 1 < tl.beats.length && tl.beats[i + 1].from <= f) i++;
  const n = kinds[i] === "feature" ? kinds.slice(0, i + 1).filter((k) => k === "feature").length : 0;
  return { line: kinds[i] === "hook", n, of };
}
