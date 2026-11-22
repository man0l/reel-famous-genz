// Facemetric spec v2 section 2 tokens + layout geometry. Pure constants: imported by the renderer, the lint and the tests
// (no React, no remotion imports, relative imports carry the .ts extension so `node --experimental-strip-types` can load them).

export const W = 1080;
export const H = 1920;
export const FPS = 30;

/** Source stills are 1280x1920 (2:3). */
export const STILL_W = 1280;
export const STILL_H = 1920;

export const COLORS = {
  canvas: "#9CADBB",
  navy: "#0B1F3A",
  teal: "#10738F", // headline keyword
  tealBright: "#1A93B0", // check badge, end dots, active-card border
  purple: "#7C3AED",
  yellow: "#FACC15",
  white: "#FFFFFF",
  footer: "rgba(255,255,255,0.65)",
} as const;

export type Tone = "teal" | "purple" | "yellow";

/** Headline keyword colour for an `hl` value. */
export const HL_COLOR: Record<Tone, string> = { teal: COLORS.teal, purple: COLORS.purple, yellow: COLORS.yellow };
/** Accent colour (dots, rings, chip outline, borders) for a `tone`. */
export const TONE_COLOR: Record<Tone, string> = { teal: COLORS.tealBright, purple: COLORS.purple, yellow: COLORS.yellow };

export const FONT = {
  head: '"Anton", Impact, "Arial Narrow", sans-serif',
  body: '"Montserrat", "Helvetica Neue", Arial, sans-serif',
} as const;
export const FONT_FILES = { anton: "fonts/Anton-Regular.ttf", montserrat: "fonts/Montserrat[wght].ttf", inter: "fonts/Inter-latin-variable.woff2" } as const;

export const TYPE = {
  headline: 104, // <= 4 words
  headlineLong: 88, // hook headlines of 5-9 words (not in the spec: keeps 3 lines out of the chip stack)
  header: 72, // template A persistent header
  headlineLineHeight: 1.0,
  headlineOutline: 3, // visible white outline px (drawn as a 2x stroke under the fill)
  subtitle: 62,
  subtitleOutline: 4,
  chip: 34,
  chipSmallScale: 0.8,
  cardLabel: 30,
  value: 76, // Anton navy value above the ladder inset
  footer: 26,
} as const;

export const CARD = { radius: 44, border: 8, shadow: "0 18px 40px rgba(10,30,60,.22)" } as const;
export const LINE = { width: 5, tick: 26, dot: 8, dotRing: 3, drawFrames: 10, shadow: "drop-shadow(0 2px 4px rgba(0,0,0,.4))" } as const;

/** Stagger (frames inside a beat): headline + first subtitle 0, first anim 6, its chip 14, each further anim +9. */
export const STAGGER = { headline: 0, firstAnim: 6, chipAfter: 8, step: 9, draw: 10, thenBlend: 12 } as const;
/** Headline entrance (frames inside a beat): fade/slide-in length, keyword underline delay and length. The cover frame waits for the last of these. */
export const HEADLINE_ANIM = { fade: 6, underlineDelay: 8, underlineLen: 10 } as const;
/** Frames a chip needs after its start to finish its spring pop. */
export const CHIP_SETTLE = 14;
export const animStart = (k: number, base = 0): number => base + STAGGER.firstAnim + STAGGER.step * k;

/** Subtitle band: nothing but the subtitles may sit here. */
export const BAND = { top: 1440, bottom: 1560, center: 1500 } as const;
/** Clearance (px) kept between drawn graphics and the band/card-subtitle zone. */
export const BAND_MARGIN = 24;
export const MAX_ZOOM = 1.8;
export const TAIL_SECONDS = 0.25;
export const DEFAULT_SECONDS = 3;
/** Frames of overlap used by push / default ladder dissolve (the outgoing beat is extended by this many frames). */
export const TRANSITION_FRAMES = 8;

export type Rect = { x: number; y: number; w: number; h: number };
export const FULL: Rect = { x: 0, y: 0, w: W, h: H };

export const HEADLINE = { top: 140, side: 60, chipTop: 170 } as const;
export const HEADER = { top: 120, side: 40 } as const;
export const LABEL_CHIPS = { x: W / 2, y0: 440, step: 84 } as const;
/** Card beats: rounded card, subtitles sit inside its bottom 160 px. */
export const CARD_RECT: Rect = { x: 90, y: 500, w: 900, h: 1080 };
export const CARD_SUB_ZONE = 160;
export const SPLIT_RECTS: [Rect, Rect] = [
  { x: 50, y: 500, w: 480, h: 800 },
  { x: 550, y: 500, w: 480, h: 800 },
];
export const HALVES_RECT: Rect = { x: 90, y: 460, w: 900, h: 960 };
export const GRID = { w: 480, h: 450, xs: [50, 550], ys: [410, 940], pillY: 900, focusY: 0.42 } as const;
export const STRIP = { maxW: 190, margin: 30, gap: 10, aspect: 1.85, centerY: 820 } as const;
export const INSET = { size: 360, right: 50, valueY: 905, pillY: 1385, focusZoom: 2 } as const;
export const AGE_PILL = { x: 50, y: 1380 } as const;
export const GAUGE = { cx: W / 2, cy: 720, r: 290 } as const;
export const CITE = { y: 820, w: 880 } as const;
export const CHIP_MIN_Y = 410;

export const FOOTER_DEFAULT = "AI-edited images";
export const FOOTER_Y = 1830;

/** Outro (Axend CTA, SLA-1023 spec v2): the card canvas colour and the subtitle line centre (empty band y 1700-1800 of Manol's card). */
export const OUTRO = { canvas: "#0a0a0a", subY: 1750 } as const;
export const OUTRO_IMAGE_SECONDS = 3.5;
/** Card label patch (SLA-1031), in the card PNG's own 752x1344 pixels: cover the drawn "Chad", write the women's label in the same style. */
export const CARD_PX = { w: 752, h: 1344 } as const;
export const CARD_LABEL = { cover: { x: 515, y: 955, w: 125, h: 55 }, cover_color: "#131414", x: 523, baseline: 995, size: 38, weight: 500 } as const;
/** Scan thumbnail of the footage: the reel face sits 2 px inside the app's ring; the blue line is 233x6, one down-and-up pass per 1.5 s. */
export const SCAN_FACE = { inset: 2, line: { w: 233, h: 6, color: "#3E6FE8", amplitude: 100, period: 1.5, startOffset: -21 } } as const;

/** The "axend." wordmark of Manol's card PNG (752x1344: x 250-505, y 138-208, bg #0a0a0a), drawn centred on x 540 with its middle at y `cy` of the 1080 canvas; `lighten` hides the card's black on the app's #140e0a canvas. */
export const LOGO = { crop: { x: 250, y: 138, w: 255, h: 70 }, cy: 290 } as const;

/**
 * Per-platform layout (SLA-1565). The same reel is rendered once per app because each app's own UI covers a different part of the
 * 1080x1920 frame: TikTok (the master, x 60-960 / y 130-1416, the constants above), Instagram Reels (`ig`: ~420-460 px of caption and
 * audio row at the bottom, the like/comment/share/save column on the right ~120-175 px) and YouTube Shorts (`yt`: ~670 px of title,
 * channel, subscribe and sound at the bottom, ~192 px of buttons on the right). Everything that carries text or a label (subtitles,
 * the "AI-edited images" footer, inset value and pill, age pill, card subtitle strip, layout labels, cta_pick / brand chips, chips
 * placed by anims) stays inside `safe`; photos may run under the app UI as background only.
 * The top of the frame differs too (SLA-1646): Instagram lays its Reels / Friends tabs and back arrow (full screen) and the
 * username + "Original audio" row (feed, after its 4:5-ish crop) over y ~0-240, so the ig headline, header and top chip start at
 * y 280 (Meta's Reels guide: keep the top 14% = 269 px free of text) and the cards, grid and label chips below them move down.
 * Pick with `platform` in script.json (renderer: `render --platform ig,yt`); missing = tiktok, so masters render unchanged.
 */
export type Platform = "tiktok" | "ig" | "yt";
export const PLATFORMS: readonly Platform[] = ["tiktok", "ig", "yt"];
export interface Layout {
  /** text-safe box: x in [left, right], y in [top, bottom]; centred headlines may start at `head.headline` above `top` where the app has no UI mid-top */
  safe: { left: number; right: number; top: number; bottom: number };
  /** top of the beat headline, the template A header and the topChip row; label chips stack up from `labelY0`; anim chips stay below `chipMinY` */
  head: { headline: number; header: number; chip: number; labelY0: number; chipMinY: number };
  band: { top: number; bottom: number; center: number };
  /** subtitle line box (left/right inset from the canvas edges) */
  sub: { left: number; right: number };
  /** x range chips placed by anims stay inside */
  chipX: [number, number];
  footerY: number;
  card: Rect;
  split: [Rect, Rect];
  halves: Rect;
  grid: { w: number; h: number; xs: readonly [number, number]; ys: readonly [number, number]; pillY: number; focusY: number };
  inset: { size: number; right: number; valueY: number; pillY: number; squareY: number; circleY: number };
  /** inset with its value and pill, as the cta_pick chip must avoid it */
  insetGuard: Rect;
  agePill: { x: number; y: number };
  /** outro subtitle line centre (beats without cta.lineY) */
  outroSubY: number;
  /** lowest y any text may reach (top of the app's bottom UI); lint G4 checks it for ig / yt (TikTok keeps its 1830 footer) */
  uiBottom: number;
}

const TOP_DEFAULT = { headline: HEADLINE.top, header: HEADER.top, chip: HEADLINE.chipTop, labelY0: LABEL_CHIPS.y0, chipMinY: CHIP_MIN_Y } as const;

const TIKTOK: Layout = {
  safe: { left: 60, right: 960, top: 130, bottom: BAND.top - BAND_MARGIN },
  head: TOP_DEFAULT,
  band: BAND,
  sub: { left: 30, right: 30 },
  chipX: [28, W - 28],
  footerY: FOOTER_Y,
  card: CARD_RECT,
  split: SPLIT_RECTS,
  halves: HALVES_RECT,
  grid: GRID,
  inset: { size: INSET.size, right: INSET.right, valueY: INSET.valueY, pillY: INSET.pillY, squareY: 960, circleY: 1000 },
  insetGuard: { x: 640, y: 860, w: 390, h: 560 },
  agePill: AGE_PILL,
  outroSubY: OUTRO.subY,
  uiBottom: H,
};

// Instagram Reels: top ~240 px, bottom ~460 px and right ~175 px covered -> text inside x 65-905, y 280-1460.
const IG_BAND = { top: 1290, bottom: 1410, center: 1350 } as const;
const IG: Layout = {
  safe: { left: 65, right: 905, top: 280, bottom: IG_BAND.top - BAND_MARGIN },
  head: { headline: 280, header: 280, chip: 300, labelY0: 545, chipMinY: 550 },
  band: IG_BAND,
  sub: { left: 65, right: 175 },
  chipX: [65, 905],
  footerY: 1440,
  card: { x: 90, y: 600, w: 900, h: 810 },
  split: [
    { x: 50, y: 600, w: 480, h: 630 },
    { x: 550, y: 600, w: 480, h: 630 },
  ],
  halves: { x: 90, y: 590, w: 900, h: 670 },
  grid: { w: 480, h: 340, xs: [50, 550], ys: [520, 920], pillY: 890, focusY: 0.42 },
  inset: { size: 320, right: 175, valueY: 810, pillY: 1215, squareY: 860, circleY: 880 },
  insetGuard: { x: 565, y: 765, w: 360, h: 490 },
  agePill: { x: 65, y: 1230 },
  outroSubY: IG_BAND.center,
  uiBottom: 1460,
};

// YouTube Shorts: bottom ~670 px and right ~192 px covered -> text inside x 65-888, y <= 1250.
const YT_BAND = { top: 1080, bottom: 1200, center: 1140 } as const;
const YT: Layout = {
  safe: { left: 65, right: 888, top: 290, bottom: YT_BAND.top - BAND_MARGIN },
  head: TOP_DEFAULT,
  band: YT_BAND,
  sub: { left: 65, right: 192 },
  chipX: [65, 888],
  footerY: 1228,
  card: { x: 90, y: 420, w: 900, h: 780 },
  split: [
    { x: 50, y: 470, w: 480, h: 580 },
    { x: 550, y: 470, w: 480, h: 580 },
  ],
  halves: { x: 90, y: 440, w: 900, h: 610 },
  grid: { w: 480, h: 320, xs: [50, 550], ys: [380, 740], pillY: 720, focusY: 0.4 },
  inset: { size: 280, right: 192, valueY: 650, pillY: 1015, squareY: 700, circleY: 720 },
  insetGuard: { x: 588, y: 605, w: 320, h: 450 },
  agePill: { x: 65, y: 1020 },
  outroSubY: YT_BAND.center,
  uiBottom: 1250,
};

export const LAYOUT: Record<Platform, Layout> = { tiktok: TIKTOK, ig: IG, yt: YT };
/** The layout for a script (`platform` missing = tiktok). */
export const layoutOf = (s: { platform?: Platform }): Layout => LAYOUT[s.platform ?? "tiktok"];

export const TEMPLATE_BEATS:Record<string, [number, number]> = { C: [6, 9], A: [8, 9], B: [20, 35] }; // C: SLA-1547 learnings cut (lint.json template_beats)
export const VO_WORDS: [number, number] = [6, 16];
