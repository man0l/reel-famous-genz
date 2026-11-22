// Beat lengths, total frames and word-synced subtitle groups. Pure.
import { CHIP_SETTLE, DEFAULT_SECONDS, FPS, HEADLINE_ANIM, OUTRO_IMAGE_SECONDS, STAGGER, TAIL_SECONDS, TRANSITION_FRAMES } from "./theme.ts";

export interface TimingInput {
  beats: readonly { seconds?: number; layout?: string; cta?: { kind?: string; in?: number; out?: number } }[];
  durations?: readonly number[];
  /** SLA-1547: silent frame-0 tail after the last beat (seconds) */
  loop?: number;
}

/** Seconds of voice for beat i when known (durations[i] > 0). */
export function voiceSeconds(s: TimingInput, i: number): number | undefined {
  const d = s.durations?.[i];
  return typeof d === "number" && d > 0 ? d : undefined;
}

/** Outro hold: a video cut plays its whole trimmed length, an image card holds `seconds` (default 3.5 s); the voice never cuts either short. */
export function outroHold(s: TimingInput, i: number): number {
  const b = s.beats[i];
  if (b?.layout !== "outro") return 0;
  if (b.cta?.kind === "video") return Math.max(0, (b.cta.out ?? 0) - (b.cta.in ?? 0));
  return b.seconds ?? OUTRO_IMAGE_SECONDS;
}

/** Beat length in seconds: durations[i] + 0.25 s tail, else the beat's `seconds`, else 3 s (outro: its hold, at least). */
export function beatSeconds(s: TimingInput, i: number): number {
  const d = voiceSeconds(s, i);
  const fallback = s.beats[i]?.layout === "outro" ? 0 : DEFAULT_SECONDS;
  const base = d !== undefined ? d + TAIL_SECONDS : (s.beats[i]?.seconds ?? fallback);
  return Math.max(base, outroHold(s, i));
}
export const beatFrames = (s: TimingInput, i: number, fps = FPS): number => Math.max(1, Math.round(beatSeconds(s, i) * fps));
/** Frames the voice is expected to fill (subtitle pacing): the beat minus its tail when durations are known. */
export const voiceFrames = (s: TimingInput, i: number, fps = FPS): number => {
  const d = voiceSeconds(s, i);
  return d !== undefined ? Math.max(1, Math.round(d * fps)) : beatFrames(s, i, fps);
};
/** Frames of the silent loop tail (frame 0 held after the last beat), 0 without one. */
export const loopFrames = (s: TimingInput, fps = FPS): number => (s.loop && s.loop > 0 ? Math.round(s.loop * fps) : 0);
export const bodyFrames = (s: TimingInput, fps = FPS): number => s.beats.reduce((n, _b, i) => n + beatFrames(s, i, fps), 0);
export const totalFrames = (s: TimingInput, fps = FPS): number => bodyFrames(s, fps) + loopFrames(s, fps);
export function beatStarts(s: TimingInput, fps = FPS): number[] {
  const out: number[] = [];
  let at = 0;
  for (let i = 0; i < s.beats.length; i++) {
    out.push(at);
    at += beatFrames(s, i, fps);
  }
  return out;
}
/**
 * cta_pick chip windows (seconds). Early chip: shown once, starts between `earliest` and `latest` (right after the hook beat when that is
 * inside the range), holds 3-4.5 s, always covers 5 s and is gone by `stop`. End chip: the whole final payoff beat.
 */
export const CTA_CHIP = { earliest: 3, latest: 5, minEnd: 5.5, holds: [4.5, 4, 3.5, 3], stop: 10, step: 0.5 } as const;

export const pad2 = (i: number): string => String(i).padStart(2, "0");

export interface SubWord {
  text: string;
  start: number;
  end: number;
}
export interface SubGroup {
  words: SubWord[];
  start: number;
  end: number;
}

const HARD = /[.!?;:]["')\]]*$/;
const SOFT = /[,—–-]["')\]]*$/;

/**
 * Split the voice line into 1-3 word groups (break at punctuation, max 3 words, no lone trailing word after a full group)
 * and spread word timings over `frames` proportionally to word length (+ a pause weight after punctuation).
 */
export function subtitleGroups(vo: string, frames: number): SubGroup[] {
  const tokens = vo.replace(/\*\*/g, "").trim().split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return [];
  const raw: string[][] = [];
  let cur: string[] = [];
  for (const t of tokens) {
    cur.push(t);
    if (cur.length === 3 || HARD.test(t) || (SOFT.test(t) && cur.length >= 2)) {
      raw.push(cur);
      cur = [];
    }
  }
  if (cur.length) raw.push(cur);
  const last = raw.length - 1;
  if (last > 0 && raw[last].length === 1 && raw[last - 1].length === 3 && !HARD.test(raw[last - 1][2])) {
    raw[last].unshift(raw[last - 1].pop() as string);
  }
  const weight = (w: string) => Math.max(2, w.replace(/[^\p{L}\p{N}]/gu, "").length) + (HARD.test(w) ? 4 : SOFT.test(w) ? 2 : 0);
  const total = raw.flat().reduce((n, w) => n + weight(w), 0);
  let acc = 0;
  const groups: SubGroup[] = [];
  for (const g of raw) {
    const words: SubWord[] = g.map((text) => {
      const start = (acc / total) * frames;
      acc += weight(text);
      return { text, start, end: (acc / total) * frames };
    });
    groups.push({ words, start: words[0].start, end: words[words.length - 1].end });
  }
  return groups;
}

/**
 * Entrance lead of the hook beat: the first frame where the headline has faded in, the keyword underline is drawn and the first
 * annotation + chip have settled (never before the beat-in transition ends), clamped to the beat. Video frame 0 and the cover still
 * both render beat 0 this many frames into its entrance, so the first frame already shows the hook. Derived from the entrance timings.
 */
export function coverFrame(s: TimingInput): number {
  const f = Math.max(
    TRANSITION_FRAMES,
    STAGGER.headline + HEADLINE_ANIM.fade,
    HEADLINE_ANIM.underlineDelay + HEADLINE_ANIM.underlineLen,
    STAGGER.firstAnim + STAGGER.chipAfter + CHIP_SETTLE,
  );
  return Math.min(f, Math.max(0, beatFrames(s, 0) - 1));
}
