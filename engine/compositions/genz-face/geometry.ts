// Callout geometry (the layout() math of v4/src/gen3.py) and the *em* text markup. Pure.
import { H, W } from "./theme.ts";

export interface Crop {
  w: number;
  x: number;
  y: number;
}
export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** Placed rectangle of a painted cutout of ratio h/w (the probe's `cut(src, width, left, top)`). */
export const cutRect = (c: Crop, ratio: number, scale = 1, about: [number, number] = [W / 2, H / 2]): Rect => {
  const width = c.w * scale;
  const height = c.w * ratio * scale;
  return { left: about[0] + (c.x - about[0]) * scale, top: about[1] + (c.y - about[1]) * scale, width, height };
};

/** Image-fraction anchor -> frame pixels. */
export const anchorPx = (r: Rect, f: readonly [number, number]): [number, number] => [r.left + f[0] * r.width, r.top + f[1] * r.height];

export interface Box {
  l: number;
  t: number;
  w: number;
  h: number;
}

/** The lead line starts at the middle of the callout box side nearest to the anchor (top, bottom, left, right). */
export function leadStart(box: Box, target: readonly [number, number]): [number, number] {
  const cands: [number, number][] = [
    [box.l + box.w / 2, box.t],
    [box.l + box.w / 2, box.t + box.h],
    [box.l, box.t + box.h / 2],
    [box.l + box.w, box.t + box.h / 2],
  ];
  let best = cands[0];
  let bd = Infinity;
  for (const q of cands) {
    const d = Math.hypot(q[0] - target[0], q[1] - target[1]);
    if (d < bd) {
      bd = d;
      best = q;
    }
  }
  return best;
}

/** Estimated callout box (label line + chip line) for the lead line: the label is Noto Sans KR 900 50 px, the chip 27 px. */
export function calloutBox(pos: readonly [number, number], label: string, chip: string | undefined, width?: number): Box {
  const lw = label.length * 30 + 44;
  const w = width ?? Math.max(lw, Math.min(560, (chip?.length ?? 0) * 15 + 44));
  const chipLines = chip ? Math.max(1, Math.ceil((chip.length * 15 + 44) / w)) : 0;
  return { l: pos[0], t: pos[1], w, h: 82 + chipLines * 44 };
}

export interface Run {
  text: string;
  em: boolean;
}

/** "nobody grades *the face.*" -> runs; `*...*` takes the lane accent. An unclosed star is plain text. */
export function runs(s: string): Run[] {
  const out: Run[] = [];
  const parts = s.split("*");
  if (parts.length % 2 === 0) return [{ text: s, em: false }];
  parts.forEach((t, i) => {
    if (t) out.push({ text: t, em: i % 2 === 1 });
  });
  return out;
}

/** The markup stripped: what is spoken or captioned. */
export const plain = (s: string): string => s.split("*").join("");
