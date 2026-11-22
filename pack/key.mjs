// Chroma-key a painted portrait on flat magenta (#FF00FF) to a transparent PNG cutout. usage: node key.mjs <in.png> <out.png>
// Needs `sharp`: resolved from RF_SHARP (a node_modules dir or the sharp folder), else from the normal node resolution.
import { createRequire } from "node:module";
import { join } from "node:path";
const [src, dst] = process.argv.slice(2);
if (!src || !dst) { console.error("usage: node key.mjs <in.png> <out.png>"); process.exit(2); }
const req = createRequire(join(process.env.RF_SHARP || process.cwd(), "noop.js"));
let sharp;
try { sharp = req("sharp"); } catch { sharp = req(process.env.RF_SHARP || "sharp"); }
const { data, info } = await sharp(src).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
const { width: W, height: H } = info;
const out = Buffer.alloc(W * H * 4);
for (let i = 0; i < W * H; i++) {
  const r = data[i * 4], g = data[i * 4 + 1], b = data[i * 4 + 2];
  const m = Math.min(r, b) - g; // ~255 for pure magenta, <= 0 for anything else
  let a = 255;
  if (m > 150) a = 0;
  else if (m > 60) a = Math.round(255 * (1 - (m - 60) / 90));
  let rr = r, bb = b;
  if (a > 0 && a < 255) { const t = (255 - a) / 255; rr = Math.round(r - (r - g) * t * 0.9); bb = Math.round(b - (b - g) * t * 0.9); }
  else if (a === 255 && m > 20) { rr = Math.round(r - (r - g) * 0.5); bb = Math.round(b - (b - g) * 0.5); }
  out[i * 4] = a === 0 ? 0 : rr; out[i * 4 + 1] = a === 0 ? 0 : g; out[i * 4 + 2] = a === 0 ? 0 : bb; out[i * 4 + 3] = a;
}
await sharp(out, { raw: { width: W, height: H, channels: 4 } }).png().toFile(dst);
console.log("keyed", W + "x" + H);
