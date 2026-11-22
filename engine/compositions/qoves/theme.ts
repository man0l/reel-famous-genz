// qoves tokens, copied from the retired cf-worker layers.js (git history before SLA-996 step 3) (CSS) and page.html (timing). Pure constants (no React / remotion imports).

export const W = 1080;
export const H = 1920;
export const FPS = 30;

export const BG = "#677e8e";
export const FOOTER = "AI-edited images";

/** page.html: 0.25 s crossfade, 0.35 s pad after every beat but the last, 1.2 s hold after the last. */
export const XFADE_S = 0.25;
export const PAD_S = 0.35;
export const END_HOLD_S = 1.2;
/** Single stills push in by 6% over the beat (page.html: 1 + 0.06 * t / L). */
export const PUSH = 0.06;
/** `zoom` = scale 2.3 about an anchor of the still (layers.js ANCHOR). */
export const ZOOM_SCALE = 2.3;
export const ANCHOR = { eyes: "50% 29%", lips: "50% 47%", face: "50% 33%" } as const;
export type Zoom = keyof typeof ANCHOR;
export const ZOOMS = Object.keys(ANCHOR) as Zoom[];

export const FONT = {
  sans: "Inter, 'Helvetica Neue', Arial, sans-serif",
  serif: "'Cormorant Garamond', Georgia, serif",
} as const;
export const FONT_FILES = {
  inter: "fonts/Inter-latin-variable.woff2",
  cormorant: "fonts/CormorantGaramond-Italic-latin-variable.woff2",
} as const;

export const SINGLE_BOX = { left: 0, top: 380, width: 1080, height: 1200 } as const;
/** Top/bottom fade of the single still (.fade). */
export const FADE_MASK = "linear-gradient(to bottom,transparent 0,#000 12%,#000 82%,transparent 100%)";
export const PAIR = { left: 30, step: 520, top: 440, width: 500, height: 900, labelTop: 1365, labelLeft: 280 } as const;
export const SINGLE_LABEL = { left: 540, top: 1470 } as const;
export const GRID_GAP_Y = 14;
export const CAPTION_TOP = 1560;
export const CAPTION_TOP_GRID_LONG = 1500;
export const CARD1 = { left: 240, top: 300, width: 600 } as const;
export const CARDS3 = { left: 30, step: 345, top: 1110, width: 330 } as const;
export const MAX_GRID = 9;
export const MAX_FAST = 6;
