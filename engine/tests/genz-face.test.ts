import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { calloutBox, cutRect, leadStart, plain, runs } from "../compositions/genz-face/geometry.ts";
import { footerOf, parseScript, safeParseScript, ScriptError } from "../compositions/genz-face/schema.ts";
import { bare, plan, stepAt, wordWindows } from "../compositions/genz-face/timing.ts";
import { CUTS_PER_MIN, LANES, MAX_LINE_WORDS } from "../compositions/genz-face/theme.ts";

const DIR = join(dirname(fileURLToPath(import.meta.url)), "fixtures", "genz-face");
const load = (n: string): any => JSON.parse(readFileSync(join(DIR, n), "utf8"));
const clone = (o: any): any => JSON.parse(JSON.stringify(o));
const okNames = readdirSync(DIR).filter((f) => f.startsWith("ok-") && f.endsWith(".json")).sort();
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

test("rhythm: 22-28 cuts a minute and about 41-50 s on the two test Reels", () => {
  for (const n of ["ok-A-yamal.json", "ok-B-keoghan.json"]) {
    const s = parseScript(load(n));
    const p = plan(s.durations, s.beats.map((b) => b.vo));
    assert.ok(p.cutsPerMin >= CUTS_PER_MIN.min && p.cutsPerMin <= CUTS_PER_MIN.max, `${n}: ${p.cutsPerMin.toFixed(1)} cuts/min`);
    assert.ok(p.tl.seconds >= 40.5 && p.tl.seconds <= 50, `${n}: ${p.tl.seconds.toFixed(1)} s`);
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
