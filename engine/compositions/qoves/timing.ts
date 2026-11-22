// Beat timing, caption chunks and crossfade of the qoves reel, mirroring page.html (compose) and layers.js chunks(). Pure.
import { END_HOLD_S, FPS, PAD_S, PUSH, XFADE_S } from "./theme.ts";

/** layers.js chunks(): 3-6 words, break after . , ? ! once 3 words are in, a short tail joins the previous chunk. */
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
  seconds: number;
  frames: number;
}

export function timeline(durations: readonly number[], fps = FPS): Timeline {
  const n = durations.length;
  const beats: BeatTime[] = [];
  let off = 0;
  for (let i = 0; i < n; i++) {
    const last = i === n - 1;
    const span = durations[i] + (last ? END_HOLD_S : PAD_S);
    beats.push({ voice: durations[i], span, shown: span + (last ? 0 : XFADE_S), off, from: Math.round(off * fps), frames: 0 });
    off += span;
  }
  const frames = Math.round(off * fps);
  beats.forEach((b, i) => {
    const end = i === n - 1 ? frames : Math.round((b.off + b.shown) * fps);
    b.frames = Math.max(1, end - b.from);
  });
  return { beats, seconds: off, frames };
}

/** Crossfade opacity of beat i at global time T (seconds): 1 for the first beat, else ramps 0 -> 1 over XFADE_S from its start. */
export function fadeIn(i: number, T: number, off: number): number {
  if (i === 0) return 1;
  return Math.min(1, Math.max(0, (T - off) / XFADE_S));
}

/** Push-in scale of a single still at beat time t (seconds) over `shown` seconds. */
export const pushScale = (t: number, shown: number): number => 1 + (PUSH * t) / shown;

/** Which of `n` stills a fast montage shows at beat time t: equal slices of the shown time, hard cuts. */
export const fastIndex = (t: number, shown: number, n: number): number => Math.max(0, Math.min(n - 1, Math.floor(t / (shown / n))));
