// Strict zod schema for the genz-face script.json (genz-face.beat.v1). Source of truth: formats/genz-face/beat.schema.json and BUILD-BRIEF section 1.
// Unknown keys are errors. Rule ids in messages ("[E2] ...") become SchemaIssue.rule:
// E1 schema, E3 unknown asset key, E6 durations length, E7 no score out of 10 on screen, E8 text over 14 words, E9 loop tail outside 0.3-2 s.
import { z } from "zod";
import { LOOP_S, MAX_CHIPS, MAX_FEATURES, MAX_LINE_WORDS, MAX_PILLS, POSES } from "./theme.ts";

const Name = z.string().min(1);
const Frac = z.number().min(-0.25).max(1.25);
const Pt = z.tuple([Frac, Frac]);
const Xy = z.tuple([z.number(), z.number()]);
const Pair = z.tuple([Name, Name]);
const Stat = z.tuple([Name, z.number().int().min(0).max(99)]);
/** SLA-1685: one Axend score panel patched over the card ("8.7 · ICON"); `value` on the card's 0-10 scale, the bar fills to value / 10. */
const AxendPanel = z.strictObject({ value: z.number().min(0).max(10), tag: z.string().min(1).max(10) });
const Pose = z.enum(POSES);
const Num = z.number().int().min(1).max(9);

/** Spoken line and on-screen words shared by every beat. `hot` words are drawn in the pink pill of the caption. */
const common = { vo: Name, hot: z.array(Name).max(3).optional(), poses: z.array(Pose).max(8).optional() };

export const CropSchema = z.strictObject({ w: z.number().positive(), x: z.number(), y: z.number() });
export const CalloutSchema = z.strictObject({
  at: Pt,
  label: Name,
  ko: z.string().optional(),
  chip: z.string().optional(),
  stat: Stat.optional(),
  pos: Xy,
  w: z.number().positive().optional(),
  /** caption chunk (0-based) at which the callout pops; default its index in the beat */
  chunk: z.number().int().min(0).optional(),
});

export const BeatSchema = z.discriminatedUnion("kind", [
  z.strictObject({ kind: z.literal("hook"), img: Name, head: z.array(Name).min(1).max(4), sub: z.string().optional(), sub_ko: z.string().optional(), card: Pair, tilt: z.number().min(-12).max(12).optional(), badge: Pair.optional(),
    /** SLA-1685: "full" (default) = the cutout fills the frame from frame 0, headline burned in over it; "card" = the old holo photocard */
    layout: z.enum(["full", "card"]).optional(),
    /** full layout: cutout width / left / top in frame pixels (theme HOOK_FULL.crop when missing) */
    crop: CropSchema.optional(),
    ...common }),
  z.strictObject({ kind: z.literal("pack"), img: Name, head: z.array(Name).min(1).max(3), name: Name, sub: z.string().optional(), ...common }),
  z.strictObject({ kind: z.literal("narrator"), lines: z.array(Name).min(1).max(4), ...common }),
  z.strictObject({ kind: z.literal("feature"), img: Name, crop: CropSchema, callouts: z.array(CalloutSchema).min(1).max(3), ...common }),
  z.strictObject({
    kind: z.literal("verdict"),
    img: Name,
    head: z.string().optional(),
    word: Name,
    ko: z.string().optional(),
    reason: Name,
    chips: z.array(Pair).max(MAX_CHIPS).optional(),
    ...common,
  }),
  z.strictObject({
    kind: z.literal("walkout"),
    img: Name,
    name: Name,
    sub: z.string().optional(),
    ovr: z.number().int().min(1).max(99),
    rarity: z.enum(["RARE", "HERO", "GOLD", "ICON"]),
    stats: z.array(Stat).length(6),
    ...common,
  }),
  /** SLA-1685 (board, 24 Nov): the Axend CTA after the game card (or, with `score`, instead of it: the payoff variant, the reel's own score counts up in the panels), reel-factory's card PNG (`card`) with the reel's face in its circle; "Chad" is patched to `label`. */
  z.strictObject({ kind: z.literal("axend"), img: Name, card: Name, label: z.string().optional(), score: AxendPanel.optional(), potential: AxendPanel.optional(), ...common }),
  z.strictObject({ kind: z.literal("cta"), head: z.array(Name).min(1).max(3), pills: z.array(Name).min(2).max(MAX_PILLS), on: z.number().int().min(0).optional(), tease: z.string().optional(), ...common }),
  /** Self-diagnosis hook (C, D, E): a topic card ("6 CHEEK TYPES") instead of the name photocard. No image = the narrator stands under it; one = a demo face; two = A/B side by side. */
  z.strictObject({ kind: z.literal("topic"), head: z.array(Name).min(1).max(4), sub: z.string().optional(), imgs: z.array(Name).max(2).optional(), labels: z.array(Name).max(2).optional(), pills: z.array(Name).max(MAX_PILLS).optional(), ...common }),
  /** Self-test check (E): the narrator waist-up and centred, a numbered check card above it, an optional small demo cutout with guide lines (`marks`, image-fraction y). */
  z.strictObject({ kind: z.literal("check"), n: Num, title: Name, chip: z.string().optional(), img: Name.optional(), demo_crop: CropSchema.optional(), marks: z.array(Frac).max(5).optional(), ...common }),
  /** Numbered type (C): the demo face like a feature beat, with the type number and name on top. */
  z.strictObject({ kind: z.literal("type"), n: Num, title: Name, img: Name, crop: CropSchema, callouts: z.array(CalloutSchema).max(3).default([]), ...common }),
  /** This or that (D): two faces side by side with A/B labels, the compared feature on top, one chip under each. */
  z.strictObject({
    kind: z.literal("versus"),
    title: Name,
    imgs: z.tuple([Name, Name]),
    labels: Pair.optional(),
    crops: z.tuple([CropSchema, CropSchema]).optional(),
    chips: z.tuple([z.string(), z.string()]).optional(),
    ...common,
  }),
]);
export type Beat = z.infer<typeof BeatSchema>;
export type BeatKind = Beat["kind"];

export const ScriptSchema = z
  .strictObject({
    format: z.literal("genz-face").optional(),
    reel_id: z.string().optional(),
    footer: z.string().nullable().optional(),
    template: z.string().optional(),
    lane: z.enum(["A", "B"]),
    lens: z.enum(["kpop", "gamecard"]),
    episode_type: z.enum(["celebrity", "self_diagnosis"]),
    kicker: z.string().optional(),
    /** top-left episode tag: "FACE DEBUT · EP.07" plus the Hangul accent, drawn only when `hangul` is true */
    tag: z.strictObject({ en: Name, ko: z.string().optional() }),
    name: z.string().optional(),
    /** per-image credit line: "Portrait painted from a photo by <author>, <licence>, Wikimedia Commons" */
    cite: Name,
    /** Hangul accents are decorative until a Korean speaker has checked them; false = English fallback */
    hangul: z.boolean().default(false),
    assets: z.record(Name, Name),
    /** pose name -> asset key of the narrator sprite (the outfit is chosen by the pack: idol_fb lane A, idol_film lane B, idol self-diagnosis) */
    sprites: z.partialRecord(Pose, Name),
    /** asset key -> height / width of the painted cutout (callout anchors are image fractions) */
    ratios: z.record(Name, z.number().positive()),
    beats: z.array(BeatSchema).min(1),
    durations: z.array(z.number().positive()),
    music: z.strictObject({ src: Name, volume: z.number().min(0).max(1).optional(), fade_in: z.number().min(0).optional(), fade_out: z.number().min(0).optional() }).nullable().optional(),
    /** lightstick click on callouts, chime on the verdict (public/sfx/*.wav, staged by the renderer) */
    sfx: z.boolean().default(true),
    caption: z.string().optional(),
    platform: z.enum(["ig", "yt"]).optional(),
    /** SLA-1685: seconds of silent loop tail after the end hold (frame 0 held, so the replay reads as one loop) */
    loop: z.number().optional(),
    /** SLA-1685: "ig" = the Instagram cut (4 callouts, 20-30 s); the renderer ignores it */
    cut: z.enum(["full", "ig"]).optional(),
    /** SLA-1685: seconds the last beat holds after its voice (theme END_HOLD_S when missing; the IG cut uses 0.6) */
    end_hold: z.number().min(0.3).max(3).optional(),
    /** SLA-1685 (board, 24 Nov: option 2, then "hook only"): a small line at the top during the hook ("wait for #4…"), and with `counter`
     * a "1/4 … 4/4" chip on every feature beat */
    tease: z.strictObject({ text: z.string().min(1).max(40), counter: z.boolean().default(true) }).optional(),
  })
  .superRefine((s, ctx) => {
    s.beats.forEach((b, i) => {
      for (const key of beatAssetKeys(b)) {
        if (!(key in s.assets)) ctx.addIssue({ code: "custom", path: ["beats", i], message: `[E3] unknown asset key "${key}" (not in assets)` });
        else if (!(key in s.ratios)) ctx.addIssue({ code: "custom", path: ["ratios"], message: `[E3] asset "${key}" has no entry in ratios` });
      }
      if (b.kind === "feature" && b.callouts.length > MAX_FEATURES) ctx.addIssue({ code: "custom", path: ["beats", i], message: "[E1] too many callouts" });
      for (const text of beatTexts(b)) {
        if (/\b\d+(\.\d+)?\s*\/\s*10\b/.test(text)) ctx.addIssue({ code: "custom", path: ["beats", i], message: `[E7] a score out of 10 is not allowed on screen or in voice: "${text}"` });
      }
      for (const line of b.vo.split(/(?<=[.?!])\s+/)) {
        const words = line.trim().split(/\s+/).length;
        if (words > MAX_LINE_WORDS) ctx.addIssue({ code: "custom", path: ["beats", i, "vo"], message: `[E8] a spoken line has ${words} words (max ${MAX_LINE_WORDS}): "${line}"` });
      }
    });
    for (const k of Object.values(s.sprites)) if (k && !(k in s.assets)) ctx.addIssue({ code: "custom", path: ["sprites"], message: `[E3] unknown asset key "${k}" (not in assets)` });
    if (s.loop !== undefined && !(s.loop >= LOOP_S.min && s.loop <= LOOP_S.max)) {
      ctx.addIssue({ code: "custom", path: ["loop"], message: `[E9] loop tail ${s.loop} s is outside ${LOOP_S.min}-${LOOP_S.max} s` });
    }
    if (s.durations.length !== s.beats.length) {
      ctx.addIssue({ code: "custom", path: ["durations"], message: `[E6] durations has ${s.durations.length} entries for ${s.beats.length} beats` });
    }
  });
export type Script = z.infer<typeof ScriptSchema>;

/** Every asset key a beat refers to. */
export function beatAssetKeys(b: Beat): string[] {
  if (b.kind === "topic") return b.imgs ?? [];
  if (b.kind === "versus") return [...b.imgs];
  if (b.kind === "axend") return [b.img, b.card];
  return "img" in b && b.img ? [b.img] : [];
}

/** Every string a beat shows or says (for the lint rules E7). */
export function beatTexts(b: Beat): string[] {
  const out: string[] = [b.vo];
  if ("head" in b) out.push(...(Array.isArray(b.head) ? b.head : b.head ? [b.head] : []));
  if (b.kind === "narrator") out.push(...b.lines);
  if (b.kind === "feature") out.push(...b.callouts.flatMap((c) => [c.label, c.chip ?? ""]));
  if (b.kind === "verdict") out.push(b.word, b.reason);
  if (b.kind === "cta") out.push(...b.pills, b.tease ?? "");
  if (b.kind === "topic") out.push(b.sub ?? "", ...(b.labels ?? []), ...(b.pills ?? []));
  if (b.kind === "check") out.push(b.title, b.chip ?? "");
  if (b.kind === "type") out.push(b.title, ...b.callouts.flatMap((c) => [c.label, c.chip ?? ""]));
  if (b.kind === "versus") out.push(b.title, ...(b.labels ?? []), ...(b.chips ?? []));
  return out.filter(Boolean);
}

export interface SchemaIssue {
  rule: string;
  path: string;
  message: string;
  beat?: number;
}

const fmtPath = (p: readonly PropertyKey[]): string => p.reduce<string>((acc, k) => (typeof k === "number" ? `${acc}[${k}]` : acc ? `${acc}.${String(k)}` : String(k)), "");

export function schemaIssues(err: z.ZodError): SchemaIssue[] {
  return err.issues.map((is) => {
    const m = /^\[(E\d+)\] (.*)$/s.exec(is.message);
    const path = fmtPath(is.path);
    const mb = /^beats\[(\d+)\]/.exec(path);
    let message = m ? m[2] : is.message;
    if (is.code === "unrecognized_keys") message = `unknown key ${(is as { keys: string[] }).keys.map((k) => `"${k}"`).join(", ")}`;
    return { rule: m ? m[1] : "E1", path, message, ...(mb ? { beat: Number(mb[1]) } : {}) };
  });
}

export class ScriptError extends Error {
  issues: SchemaIssue[];
  constructor(issues: SchemaIssue[]) {
    super("invalid genz-face script:\n" + issues.map((i) => `  ${i.rule} ${i.path || "<root>"}: ${i.message}`).join("\n"));
    this.issues = issues;
  }
}

export function safeParseScript(json: unknown): { ok: true; script: Script } | { ok: false; issues: SchemaIssue[] } {
  const r = ScriptSchema.safeParse(json);
  return r.success ? { ok: true, script: r.data } : { ok: false, issues: schemaIssues(r.error) };
}

/** Parse + validate a script (props of the `genz-face` composition: the whole script.json, plus `durations`). Throws ScriptError. */
export function parseScript(json: unknown): Script {
  const r = safeParseScript(json);
  if (!r.ok) throw new ScriptError(r.issues);
  return r.script;
}

/** Footer line of every beat: the per-image credit, then the board text. */
export function footerOf(s: Pick<Script, "cite" | "footer">): string {
  const c = s.cite.trim();
  return c.includes("AI-edited images") ? c : `${c} · AI-edited images`;
}
