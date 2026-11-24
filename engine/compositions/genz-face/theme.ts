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
export const PAD_S = 0.35;
export const END_HOLD_S = 1.2;
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
