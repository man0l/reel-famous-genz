import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { calloutBox, cutRect, leadStart, plain, runs } from "../compositions/genz-face/geometry.ts";
import { beatAssetKeys, beatTexts, footerOf, parseScript, safeParseScript, ScriptError } from "../compositions/genz-face/schema.ts";
import { bare, clipFrames, plan, stepAt, wordWindows } from "../compositions/genz-face/timing.ts";
import { CUTS_PER_MIN, LANES, MAX_LINE_WORDS } from "../compositions/genz-face/theme.ts";

const DIR = join(dirname(fileURLToPath(import.meta.url)), "fixtures", "genz-face");
const load = (n: string): any => JSON.parse(readFileSync(join(DIR, n), "utf8"));
const clone = (o: any): any => JSON.parse(JSON.stringify(o));
const okNames = readdirSync(DIR).filter((f) => f.startsWith("ok-") && f.endsWith(".json")).sort();
const sdNames = readdirSync(DIR).filter((f) => f.startsWith("sd-") && f.endsWith(".json")).sort();
const rule = (s: any): string[] => {
  const r = safeParseScript(s);
  return r.ok ? [] : r.issues.map((i) => i.rule);
};

test("ok fixtures parse: K-pop lane A, K-pop lane B, game card", () => {
  assert.deepEqual(okNames, ["ok-A-yamal.json", "ok-B-keoghan.json", "ok-G-yamal.json"]);
  for (const n of okNames) {
    const s = parseScript(load(n));
    assert.equal(s.durations.length, s.beats.length);
    assert.equal(s.hangul, false, `${n}: Hangul stays off (English fallback) until a Korean speaker checks it`);
  }
});

test("lane tokens: accent lavender on football, pink on actors", () => {
  assert.equal(LANES.A.accent, "#C9B8FF");
  assert.equal(LANES.B.accent, "#FF4FA3");
  assert.equal(LANES.A.gamecard, "gold");
  assert.equal(LANES.B.gamecard, "hero");
});

test("beat skeleton: hook, bridge, 4-6 features, pivot, verdict, CTA (the test Reels use 6 features)", () => {
  for (const n of ["ok-A-yamal.json", "ok-B-keoghan.json"]) {
    const kinds = parseScript(load(n)).beats.map((b) => b.kind);
    assert.equal(kinds[0], "hook");
    assert.equal(kinds[1], "narrator");
    assert.equal(kinds.at(-1), "cta");
    assert.equal(kinds.at(-2), "verdict");
    assert.equal(kinds.at(-3), "narrator");
    const nf = kinds.filter((k) => k === "feature").length;
    assert.ok(nf >= 4 && nf <= 6, `${n}: ${nf} features`);
  }
  assert.equal(parseScript(load("ok-G-yamal.json")).beats.at(-2)?.kind, "walkout");
});

test("rhythm: 22-28 cuts a minute and about 38-50 s on the two test Reels (6 features, 0.2 s pads)", () => {
  for (const n of ["ok-A-yamal.json", "ok-B-keoghan.json"]) {
    const s = parseScript(load(n));
    const p = plan(s.durations, s.beats.map((b) => b.vo));
    assert.ok(p.cutsPerMin >= CUTS_PER_MIN.min && p.cutsPerMin <= CUTS_PER_MIN.max, `${n}: ${p.cutsPerMin.toFixed(1)} cuts/min`);
    assert.ok(p.tl.seconds >= 38 && p.tl.seconds <= 50, `${n}: ${p.tl.seconds.toFixed(1)} s`);
  }
});

test("plan: every beat starts on a cut, cuts are at least the gap apart, stepAt counts cuts so far", () => {
  const p = plan([4, 4, 4], ["one two three four five six seven eight.", "a b c d e f g h i j k l.", "x y z."], 1.4);
  assert.equal(p.beats[0].cuts[0], 0);
  assert.equal(p.beats[1].cuts[0], 0);
  for (let i = 1; i < p.cutTimes.length; i++) assert.ok(p.cutTimes[i] - p.cutTimes[i - 1] >= 1.4 - 1e-9);
  assert.equal(stepAt([0, 2, 4], 3), 1);
  assert.equal(stepAt([0, 2, 4], 9), 2);
});

test("word windows cover the chunk by character share; bare() strips punctuation and case", () => {
  const w = wordWindows(["a", "bbb"], 0, 4);
  assert.deepEqual(w, [[0, 1], [1, 4]]);
  assert.equal(bare("V-LINE,"), "vline");
});

test("*em* markup: runs and plain; an unclosed star is plain text", () => {
  assert.deepEqual(runs("nobody grades *the face.*"), [{ text: "nobody grades ", em: false }, { text: "the face.", em: true }]);
  assert.equal(plain("IF *X*"), "IF X");
  assert.deepEqual(runs("a * b"), [{ text: "a * b", em: false }]);
});

test("callout geometry: image-fraction anchor, lead line leaves the nearest box side", () => {
  const rect = cutRect({ w: 1500, x: -210, y: 80 }, 1.3, 1);
  assert.equal(rect.width, 1500);
  assert.ok(Math.abs(rect.height - 1950) < 1e-9);
  const box = calloutBox([60, 1130], "PUPPY EYES", "round", 470);
  assert.deepEqual(leadStart(box, [300, 700]), [box.l + box.w / 2, box.t]); // anchor above the box: top middle
  assert.deepEqual(leadStart(box, [5000, box.t + box.h / 2]), [box.l + box.w, box.t + box.h / 2]); // far right: right middle
  // scale 1 about the frame centre leaves the rect untouched; a punch grows it about the centre
  const big = cutRect({ w: 1000, x: 0, y: 0 }, 1, 1.1);
  assert.ok(Math.abs(big.width - 1100) < 1e-9);
});

test("rejected: unknown asset, durations length, unknown key, score out of 10, long line, missing credit, bad pose", () => {
  const a = load("ok-A-yamal.json");
  const bad = (f: (s: any) => void): any => {
    const s = clone(a);
    f(s);
    return s;
  };
  assert.ok(rule(bad((s) => (s.beats[0].img = "nope"))).includes("E3"));
  assert.ok(rule(bad((s) => s.durations.pop())).includes("E6"));
  assert.ok(rule(bad((s) => (s.extra = 1))).includes("E1"));
  assert.ok(rule(bad((s) => (s.beats[9].vo = "Result: 7.2/10."))).includes("E7"));
  assert.ok(rule(bad((s) => (s.beats[9].reason = "an 8/10 face"))).includes("E7"));
  const words = Array.from({ length: MAX_LINE_WORDS + 1 }, (_, i) => "w" + i).join(" ") + ".";
  assert.ok(rule(bad((s) => (s.beats[1].vo = words))).includes("E8"));
  assert.ok(rule(bad((s) => delete s.cite)).includes("E1"));
  assert.ok(rule(bad((s) => (s.beats[1].poses = ["wave"]))).includes("E1"));
  assert.ok(rule(bad((s) => (s.beats[2].callouts = []))).includes("E1"));
  assert.throws(() => parseScript(bad((s) => delete s.lens)), ScriptError);
});

test("footer: the per-image credit and the board text, once", () => {
  const s = parseScript(load("ok-A-yamal.json"));
  assert.ok(footerOf(s).includes("Wikimedia Commons"));
  assert.ok(footerOf(s).endsWith("AI-edited images"));
  assert.equal((footerOf(s).match(/AI-edited images/g) ?? []).length, 1);
  assert.equal(footerOf({ cite: "Photo by X, CC BY 4.0", footer: null }), "Photo by X, CC BY 4.0 · AI-edited images");
});

test("lint over the fixtures: no score, no rating or PSL words, no app pitch in anything said or shown", () => {
  const banned = /\b(canthal|mogging|mogs|blackpill|mewing|psl|chad|looksmax\w*|link in bio|download)\b/i;
  for (const n of okNames) {
    const s = parseScript(load(n));
    const text = JSON.stringify(s.beats);
    assert.ok(!banned.test(text), n);
    assert.ok(!/\d+\s*\/\s*10/.test(text), n);
  }
});

test("self-diagnosis fixtures (SLA-1653): E checks on the narrator, C numbered types, D A/B rounds; every one opens on a topic card", () => {
  assert.deepEqual(sdNames, ["sd-C-types.json", "sd-D-compare.json", "sd-E-selftest.json"]);
  const kinds = (n: string): string[] => parseScript(load(n)).beats.map((b) => b.kind);
  assert.deepEqual(kinds("sd-E-selftest.json"), ["topic", "narrator", "check", "check", "check", "cta"]);
  assert.deepEqual(kinds("sd-C-types.json"), ["topic", "narrator", "type", "type", "type", "type", "type", "type", "cta"]);
  assert.deepEqual(kinds("sd-D-compare.json"), ["topic", "narrator", "versus", "versus", "narrator", "cta"]);
  for (const n of sdNames) {
    const s = parseScript(load(n));
    assert.equal(s.episode_type, "self_diagnosis", n);
    assert.equal(s.name, undefined, `${n}: no celebrity name`);
    assert.ok(s.beats.at(-1)!.vo.startsWith("Comment "), n);
  }
  const e = parseScript(load("sd-E-selftest.json"));
  const hook = e.beats[0] as Extract<(typeof e.beats)[number], { kind: "topic" }>;
  assert.deepEqual(beatAssetKeys(hook), [], "E hook: no face, the narrator stands under the card");
  assert.deepEqual(hook.pills, ["1", "2", "3"]);
  const checks = e.beats.filter((b) => b.kind === "check");
  assert.deepEqual(checks.map((b) => (b.kind === "check" ? b.n : 0)), [1, 2, 3]);
  assert.deepEqual(beatAssetKeys(checks[2]), [], "the posture check has no demo face");
  const c = parseScript(load("sd-C-types.json"));
  assert.equal(c.beats.at(-1)!.kind === "cta" && (c.beats.at(-1) as { pills: string[] }).pills.length, 6, "C: six number pills in the CTA");
  const d = parseScript(load("sd-D-compare.json"));
  assert.deepEqual(beatAssetKeys(d.beats[2]), ["cut_barry_keoghan", "cut_jacob_elordi"]);
  assert.ok(beatTexts(d.beats[2]).includes("cooler, more striking"));
});

test("self-diagnosis beats are strict: unknown faces, a third A/B face, a number out of range and seven pills are rejected", () => {
  const e = load("sd-E-selftest.json");
  const d = load("sd-D-compare.json");
  const c = load("sd-C-types.json");
  const bad = (src: any, f: (s: any) => void): string[] => {
    const s = clone(src);
    f(s);
    return rule(s);
  };
  assert.ok(bad(e, (s) => (s.beats[2].img = "nope")).includes("E3"));
  assert.ok(bad(d, (s) => (s.beats[2].imgs = ["cut_barry_keoghan", "nope"])).includes("E3"));
  assert.ok(bad(d, (s) => s.beats[2].imgs.push("cut_barry_keoghan")).includes("E1"));
  assert.ok(bad(c, (s) => (s.beats[2].n = 0)).includes("E1"));
  assert.ok(bad(c, (s) => s.beats.at(-1).pills.push("7")).includes("E1"));
  assert.ok(bad(e, (s) => (s.beats[2].title = "a solid 8/10")).includes("E7"));
});

test("loop tail (SLA-1685): adds its frames after the end hold and moves nothing else; 0.3-2 s or E9", () => {
  const s = parseScript(load("ok-B-keoghan.json"));
  const vo = s.beats.map((b) => b.vo);
  const a = plan(s.durations, vo);
  const b = plan(s.durations, vo, undefined, 0.8);
  assert.equal(a.tl.frames, a.tl.body, "no tail without `loop`");
  assert.equal(b.tl.body, a.tl.frames);
  assert.equal(b.tl.frames - b.tl.body, 24);
  assert.deepEqual(b.tl.beats, a.tl.beats);
  assert.deepEqual(b.cutTimes, a.cutTimes);
  assert.equal(b.cutsPerMin, a.cutsPerMin, "the silent tail does not dilute the cut rate");
  assert.ok(Math.abs(b.tl.seconds - a.tl.seconds - 0.8) < 1e-9);
  assert.deepEqual(rule({ ...clone(load("ok-B-keoghan.json")), loop: 0.8 }), []);
  assert.deepEqual(rule({ ...clone(load("ok-B-keoghan.json")), loop: 0.2 }), ["E9"]);
  assert.deepEqual(rule({ ...clone(load("ok-B-keoghan.json")), loop: 2.5 }), ["E9"]);
});

test("hook (SLA-1685): full-frame layout by default, the old photocard on request, a strict crop", () => {
  const raw = clone(load("ok-B-keoghan.json"));
  const hook = parseScript(raw).beats[0];
  assert.equal(hook.kind, "hook");
  assert.equal((hook as any).layout, undefined, "no layout = full frame");
  raw.beats[0].layout = "card";
  assert.deepEqual(rule(raw), []);
  raw.beats[0].layout = "full";
  raw.beats[0].crop = { w: 1500, x: -210, y: 200 };
  assert.deepEqual(rule(raw), []);
  raw.beats[0].crop = { w: 1500, x: -210 };
  assert.deepEqual(rule(raw), ["E1"]);
  raw.beats[0].crop = { w: 1500, x: -210, y: 200 };
  raw.beats[0].layout = "split";
  assert.deepEqual(rule(raw), ["E1"]);
});

test("hook clip morph opener (SLA-1728): a strict clip, played for (out - in) / rate", () => {
  const raw = clone(load("ok-B-keoghan.json"));
  raw.beats[0].open = { clip: { src: "morph/clip.mp4", in: 1.5, out: 3.95, rate: 1.36 } };
  assert.deepEqual(rule(raw), []);
  assert.equal(clipFrames(raw.beats[0].open.clip), 54, "2.45 s of clip at 1.36x = 1.8 s");
  raw.beats[0].open = { clip: { src: "morph/clip.mp4", in: 1.5, out: 3.95 } };
  assert.deepEqual(rule(raw), ["E1"], "no rate");
  raw.beats[0].open = { clip: { src: "morph/clip.mp4", in: 1.5, out: 3.95, rate: 1.36, box: [0, 0, 1, 1] } };
  assert.deepEqual(rule(raw), ["E1"], "unknown key");
});

test("the first beat starts at frame 0, so the voice starts at 0.0 s (SLA-1685)", () => {
  for (const n of okNames) {
    const s = parseScript(load(n));
    const tl = plan(s.durations, s.beats.map((b) => b.vo)).tl;
    assert.equal(tl.beats[0].from, 0);
    assert.equal(tl.beats[0].off, 0);
  }
});

test("end hold (SLA-1685): the IG cut's shorter CTA hold moves only the last beat; 0.3-3 s", () => {
  const s = parseScript(load("ok-B-keoghan.json"));
  const vo = s.beats.map((b) => b.vo);
  const a = plan(s.durations, vo, undefined, 0.8);
  const b = plan(s.durations, vo, undefined, 0.8, 0.6);
  const n = s.beats.length - 1;
  assert.deepEqual(b.tl.beats.slice(0, n), a.tl.beats.slice(0, n));
  assert.equal(a.tl.frames - b.tl.frames, 18);
  assert.deepEqual(rule({ ...clone(load("ok-B-keoghan.json")), end_hold: 0.6, cut: "ig", platform: "ig" }), []);
  assert.deepEqual(rule({ ...clone(load("ok-B-keoghan.json")), end_hold: 0.1 }), ["E1"]);
});

test("axend beat (SLA-1685): needs its card and face assets; the card counts as an asset key", () => {
  const s = load("ok-G-yamal.json") as { beats: Record<string, unknown>[]; assets: Record<string, string>; ratios: Record<string, number>; durations: number[] };
  const img = String(s.beats.find((b) => b.kind === "walkout")?.img);
  s.beats.push({ kind: "axend", img, card: "axend_card", label: "Eve", vo: "Want your own face card? Scan yours in Axend." });
  s.durations.push(2.8);
  assert.ok(!safeParseScript(s).ok, "a missing card asset is an error");
  s.assets.axend_card = "brand/axend-call-2-action.png";
  s.ratios.axend_card = 1344 / 752;
  const r = safeParseScript(s);
  assert.ok(r.ok, JSON.stringify(r));
  assert.deepEqual(beatAssetKeys(r.ok ? r.script.beats.at(-1)! : (null as never)), [img, "axend_card"]);
});

test("tease (SLA-1685): the line during the hook only and in the loop tail, a 1/4 … 4/4 chip on each feature, strict shape", async () => {
  const { teaseAt, timeline } = await import("../compositions/genz-face/timing.ts");
  const kinds = ["hook", "feature", "feature", "feature", "feature", "axend"];
  const tl = timeline([2, 3, 3, 3, 3, 3], 30, 0.8);
  assert.deepEqual(teaseAt(kinds, tl, 0), { line: true, n: 0, of: 4 });
  assert.deepEqual(teaseAt(kinds, tl, tl.beats[1].from - 1), { line: true, n: 0, of: 4 }, "up to the last hook frame");
  assert.deepEqual(teaseAt(kinds, tl, tl.beats[1].from), { line: false, n: 1, of: 4 }, "gone on the first feature");
  assert.deepEqual(teaseAt(kinds, tl, tl.beats[4].from + 5), { line: false, n: 4, of: 4 });
  assert.deepEqual(teaseAt(kinds, tl, tl.beats[5].from), { line: false, n: 0, of: 4 });
  assert.deepEqual(teaseAt(kinds, tl, tl.body + 3), teaseAt(kinds, tl, 0), "the loop tail holds frame 0");
  const s = { ...clone(load("ok-B-keoghan.json")), tease: { text: "wait for #4…" } };
  const r = safeParseScript(s);
  assert.ok(r.ok && r.script.tease?.counter === true, JSON.stringify(r));
  assert.deepEqual(rule({ ...s, tease: { text: "wait for #4…", size: 3 } }), ["E1"]);
});

test("host (SLA-1685, board: the narrator is crucial): an optional boolean on the script; strict", () => {
  const s = load(okNames[0]);
  assert.equal(parseScript({ ...clone(s), host: true }).host, true);
  assert.equal(parseScript(clone(s)).host, undefined);
  assert.ok(rule({ ...clone(s), host: "corner" }).length > 0);
});
