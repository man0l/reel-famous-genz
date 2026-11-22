// Beat timing, caption chunks, word windows and the cut plan of the genz-face reel. Pure. The crossfade / pad / end-hold timeline and the
// chunking are the qoves ones (same Remotion job layout: one voice clip per beat), so the reels sit on the same clock.
import { captionAt, captionWindows, chunks, fadeIn, timeline, type BeatTime, type Timeline } from "../qoves/timing.ts";
import { FPS, MIN_CUT_GAP_S } from "./theme.ts";

export { captionAt, captionWindows, chunks, fadeIn, timeline };
export type { BeatTime, Timeline };

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
export function plan(durations: readonly number[], vo: readonly string[], gap = MIN_CUT_GAP_S): Plan {
  const tl = timeline(durations, FPS);
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
  return { tl, beats, cutTimes, cutsPerMin: cutTimes.length / (tl.seconds / 60) };
}

/** How many cuts have happened in the beat by chunk index j (pose / crop step). */
export const stepAt = (cuts: readonly number[], j: number): number => cuts.filter((c) => c <= j).length - 1;

/** Frames since the cut that started step `chunk`'s group, for the scale punch (0 at the cut). */
export function framesSinceCut(windows: readonly [number, number][], cuts: readonly number[], j: number, t: number, fps = FPS): number {
  const start = windows[cuts.filter((c) => c <= j).pop() ?? 0][0];
  return Math.max(0, Math.round((t - start) * fps));
}
