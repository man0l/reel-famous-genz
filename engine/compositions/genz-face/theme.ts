// genz-face tokens (SLA-1643), verbatim from the v4 probe CSS (research/genz-face-samples-2026-11-21/v4/src/gen3.py) and BUILD-BRIEF sections 2 and 4.
// Pure constants (no React / remotion imports). Everything is CSS/SVG: no lightstick, agency, group, show, EA/FUT/Panini assets or fonts.

export const W = 1080;
export const H = 1920;
export const FPS = 30;
export const CANVAS = "#0D0718";
export const FOOTER = "AI-edited images";

/** Lane token object: the K-pop lens is themed per subject lane (A football, B Gen Z actors and creators). */
export interface LaneTokens {
  accent: string;
  /** top / side glows of the stage background */
  glow: string;
  sparkle: string;
  /** photocard inner gradient */
  cardInner: string;
  /** game-card variant of the lane */
  gamecard: "gold" | "hero";
}

export const LANES: Record<"A" | "B", LaneTokens> = {
  A: {
    accent: "#C9B8FF",
    glow: "radial-gradient(ellipse at 50% 15%, rgba(201,184,255,.55) 0%, rgba(13,7,24,0) 55%), radial-gradient(ellipse at 20% 90%, rgba(255,79,163,.35) 0%, rgba(13,7,24,0) 50%)",
    sparkle: "#FFD6F2",
    cardInner: "linear-gradient(180deg, #2A1B4E, #140B2B)",
    gamecard: "gold",
  },
  B: {
    accent: "#FF4FA3",
    glow: "radial-gradient(ellipse at 50% 15%, rgba(255,79,163,.5) 0%, rgba(13,7,24,0) 55%), radial-gradient(ellipse at 80% 90%, rgba(201,184,255,.3) 0%, rgba(13,7,24,0) 50%)",
    sparkle: "#FFB3D9",
    cardInner: "linear-gradient(180deg, #2B0F1F, #0E0609)",
    gamecard: "hero",
  },
};

export const PINK = "#FF4FA3";
export const PETAL = "#FFD6F2";
export const HOLO = "conic-gradient(from 20deg, #ffb3ec, #b3fff2, #fff3b3, #c9b8ff, #ffb3ec)";
export const HOT_PILL = "rgba(255,79,163,.35)";
export const SPARKLES = 16;

export const FONT = {
  kr: "'Noto Sans KR', 'Inter', sans-serif",
  tag: "'Space Grotesk', 'Noto Sans KR', sans-serif",
  num: "'Anton', 'Noto Sans KR', sans-serif",
} as const;
export const FONT_FILES = {
  kr: "fonts/NotoSansKR-subset.woff2",
  grotesk: "fonts/SpaceGrotesk-latin.woff2",
  anton: "fonts/Anton-Regular.ttf",
} as const;

/** Game-card lens (BUILD-BRIEF section 4). */
export const GAME = {
  canvas: "#061024",
  bg: "radial-gradient(ellipse at 50% 40%, #16306A 0%, #061024 60%, #02060F 100%)",
  card: { w: 620, h: 900, radius: "40px 40px 160px 160px / 40px 40px 120px 120px" },
  gold: { fill: "linear-gradient(160deg, #FFF0B8 0%, #E8C25A 30%, #B8862A 70%, #8A5F14 100%)", text: "#3A2606", ring: "none", rays: "rgba(255,215,120,.10)", glow: "rgba(255,215,120,.45)", accent: "#FFD778" },
  hero: { fill: "linear-gradient(160deg, #3A1C66 0%, #22103F 40%, #0E0620 100%)", text: "#F1E6FF", ring: "0 0 0 4px #B48CFF", rays: "rgba(170,90,255,.12)", glow: "rgba(170,90,255,.5)", accent: "#B48CFF" },
  /** the six game-card stats, in reveal order */
  stats: ["EYE", "JAW", "SYM", "NOS", "BRW", "SKN"],
  rarity: ["RARE", "HERO", "GOLD", "ICON"],
} as const;

/** Narrator: waist-up, 60-70 % of frame height, bottom-anchored and centred (never a corner mascot). Verdict beats seat it half-size at the right. */
export const NARRATOR = { full: 1080, side: 760, sideRight: -20, punch: 0.04, punchFrames: 7 } as const;

/** Photocard (hook): the holo frame around the painted cutout. */
export const PHOTOCARD = { width: 740, left: 170, top: 560, innerH: 880, border: 12, radius: 40 } as const;

/** SLA-1685: full-frame hook. The painted cutout fills the frame from frame 0 (crop = width / left / top in frame pixels, a topic's `hook_crop`
 * wins) with no headline over it (the hook is in the captions), and nothing animates in: frame 0 is the finished layout. */
export const HOOK_FULL = { crop: { w: 1400, x: -160, y: 250 } } as const;

/** Self-diagnosis layouts (C, D, E): the demo card of a check (crop = image width / left / top in card pixels), the topic card and the A/B panels. */
export const SELFTEST = {
  demoW: 380,
  demoH: 520,
  demoCrop: { w: 600, x: -110, y: -150 },
  topicCardH: 700,
  versusH: 700,
  versusCrop: { w: 760, x: -140, y: -150 },
} as const;

/** Rhythm: 22-28 cuts a minute from pose swaps on caption groups and callout pops (a cut is never closer than MIN_CUT_GAP_S to the last). */
export const CUTS_PER_MIN = { min: 22, max: 28 } as const;
export const MIN_CUT_GAP_S = 1.4;

/** Beat clock (seconds): crossfade between beats, pad after each voice clip, hold after the last. */
export const XFADE_S = 0.25;
export const PAD_S = 0.2;
export const END_HOLD_S = 1.2;
/** SLA-1685 (board, 24 Nov: pace): a feature beat starts on a hard cut, a white flash and a crash zoom instead of a crossfade. */
export const HARD_CUT = { flash: 0.5, flashFrames: 5, zoom: 0.16, zoomFrames: 7 } as const;

/** SLA-1685: reel-factory's Axend CTA card (Manol's 752x1344 PNG, scaled to the 1080 width it is 1080x1930), its circle in frame pixels
 * (centre x, y, diameter; 820 hides the placeholder's checkerboard rim) and the "Chad" rating pill patched for another label (card pixels). */
export const AXEND = {
  card: { w: 752, h: 1344 },
  circle: [533, 747, 820],
  label: { cover: { x: 515, y: 955, w: 125, h: 55 }, color: "#131414", x: 523, baseline: 995, size: 38, weight: 500 },
  /** SLA-1685 payoff variant: the two score panels (card pixels, measured on the PNG): the area covering "2.9 · Sub-3" / "7 · Chad", the number
   * baseline and size, the bar track; the number counts up and the bar fills over `countFrames` once the card is in. */
  panels: {
    score: { cover: { x: 48, y: 942, w: 292, h: 72 }, x: 54, bar: { x: 51, y: 1050, w: 281, h: 23 }, fill: "#fc0200", glow: "rgba(252,2,0,0.75)", dot: "#fc0200" },
    potential: { cover: { x: 418, y: 942, w: 292, h: 72 }, x: 423, bar: { x: 421, y: 1050, w: 279, h: 23 }, fill: "#5ef2f5", glow: "rgba(94,242,245,0.8)", dot: "#5ef2f5" },
  },
  panelBg: "#131414",
  number: { baseline: 1006, size: 72, weight: 700 },
  tag: { baseline: 995, size: 38, weight: 500 },
  countFrames: 18,
  /** the card rises in and the face settles into the circle over these frames */
  enterFrames: 9,
  faceFrom: 1.3,
} as const;

/** SLA-1685 (board, 24 Nov): the on-screen tease, kept small at the top so the face stays the hook: the line and the feature counter chip
 * share one centred row (`top` in frame pixels); the last chip ("4/4") turns pink. */
export const TEASE = { top: 168, size: 42, chip: 38, gap: 16 } as const;

/** SLA-1685: silent loop tail after the end hold (frame 0 held, the facemetric pattern): allowed range of the script's `loop`. */
export const LOOP_S = { min: 0.3, max: 2 } as const;

export const MAX_FEATURES = 6;
/** BUILD-BRIEF section 6: lines under 14 words. */
export const MAX_LINE_WORDS = 13;
export const MAX_CHIPS = 4;
/** CTA / topic pills: up to six (C: "1"-"6"). */
export const MAX_PILLS = 6;
export const POSES = ["point", "think", "cross", "present", "shock", "approve", "hair", "profile", "phone"] as const;
export type Pose = (typeof POSES)[number];
