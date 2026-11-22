#!/usr/bin/env node
// Render one reel. Used unchanged by both targets (VPS render.sh and the Cloudflare container).
//   node render-job.mjs <job-dir> <out.mp4>
//   node render-job.mjs --still <job-dir> <out.jpg>      (cover still: job.json `still_composition` at `still_frame` (default 0), 1080x1920 JPEG under 1 MB)
//   node render-job.mjs --slides <job-dir> <out-dir>     (carousel slides, SLA-1573: job.json `slides_composition` plans the slides of script.json, writes <out-dir>/ig/NN.jpg (1080x1350), <out-dir>/pin/NN.jpg (1000x1500) and <out-dir>/slides.json)
//   node render-job.mjs --ensure-browser | --prebundle   (image build / first run: download Chrome, warm the bundle cache)
// <job-dir>: job.json {reel_id, composition}, script.json (the composition's input props), public/ (stills, vo, fonts).
// Writes <job-dir>/progress.json as it renders and prints one JSON line per progress step on stdout.
// Env: RF_REMOTION_HOME (bundle cache, default <this dir>/.cache), RF_CONCURRENCY (default 1), RF_BROWSER (executable override),
//      RF_CHUNK_FRAMES (frames per resumable chunk, default 150).
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { combineChunks, ensureBrowser, renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { encodeRates } from "./bitrate.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CACHE = process.env.RF_REMOTION_HOME || path.join(HERE, ".cache");
export const browserExecutable = process.env.RF_BROWSER || null;
export const chromiumOptions = { gl: "swangle" };

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const f = path.join(dir, e.name);
    if (e.isDirectory()) walk(f, out); else out.push(f);
  }
  return out;
}

/** Hash of everything that changes the bundle: compositions, entry, package versions. */
function sourceKey() {
  const h = createHash("sha1");
  for (const root of ["compositions", "src"]) {
    for (const f of walk(path.join(HERE, root))) { h.update(path.relative(HERE, f)); h.update(fs.readFileSync(f)); }
  }
  for (const f of ["package.json", "package-lock.json"]) {
    if (fs.existsSync(path.join(HERE, f))) h.update(fs.readFileSync(path.join(HERE, f)));
  }
  return h.digest("hex").slice(0, 16);
}

export async function getBundle() {
  const dir = path.join(CACHE, "bundles", sourceKey());
  if (fs.existsSync(path.join(dir, "index.html"))) return dir;
  fs.mkdirSync(path.dirname(dir), { recursive: true });
  const tmp = dir + ".tmp-" + process.pid;
  const emptyPublic = fs.mkdtempSync(path.join(CACHE, "empty-public-"));
  await bundle({ entryPoint: path.join(HERE, "src", "index.ts"), outDir: tmp, publicDir: emptyPublic });
  fs.rmSync(emptyPublic, { recursive: true, force: true });
  try { fs.renameSync(tmp, dir); } catch { fs.rmSync(tmp, { recursive: true, force: true }); }
  return dir;
}

/** Container memory (MB) for progress lines, so a failure tail shows how close the render was to the limit. */
function mem() {
  const rd = (f) => { try { return fs.readFileSync(f, "utf8").trim(); } catch { return ""; } };
  const mb = (v) => (/^\d+$/.test(v) ? Math.round(Number(v) / 1048576) : v || undefined);
  return { cg: mb(rd("/sys/fs/cgroup/memory.current") || rd("/sys/fs/cgroup/memory/memory.usage_in_bytes")), cgMax: mb(rd("/sys/fs/cgroup/memory.max") || rd("/sys/fs/cgroup/memory/memory.limit_in_bytes")), free: Math.round(os.freemem() / 1048576), total: Math.round(os.totalmem() / 1048576), cpus: os.cpus().length };
}

function progress(job, o) {
  const line = JSON.stringify({ ...o, mem: mem() });
  console.log(line);
  const f = path.join(job, "progress.json");
  fs.writeFileSync(f + ".tmp", line); fs.renameSync(f + ".tmp", f);
}

const MAX_STILL_BYTES = 1_000_000;

/** Cover JPEG: render the still composition (one frame), stepping the JPEG quality down until the file is under 1 MB. */
async function still(job, out) {
  if (!job || !out) { console.error("usage: render-job.mjs --still <job-dir> <out.jpg>"); process.exit(2); }
  const meta = JSON.parse(fs.readFileSync(path.join(job, "job.json"), "utf8"));
  if (!meta.still_composition) throw new Error("job.json has no still_composition");
  const inputProps = JSON.parse(fs.readFileSync(path.join(job, "script.json"), "utf8"));
  progress(job, { phase: "bundling", progress: 0 });
  const base = await getBundle();
  const serveUrl = path.join(job, "bundle");
  fs.rmSync(serveUrl, { recursive: true, force: true });
  fs.cpSync(base, serveUrl, { recursive: true });
  if (fs.existsSync(path.join(job, "public"))) fs.cpSync(path.join(job, "public"), path.join(serveUrl, "public"), { recursive: true });
  await ensureBrowser({ browserExecutable });
  const composition = await selectComposition({ serveUrl, id: meta.still_composition, inputProps, browserExecutable, chromiumOptions, timeoutInMilliseconds: 120000 });
  progress(job, { phase: "rendering", progress: 0.5, width: composition.width, height: composition.height });
  let bytes = 0;
  for (const jpegQuality of [92, 85, 78, 70, 60]) {
    await renderStill({ composition, serveUrl, inputProps, output: out, frame: Math.min(meta.still_frame ?? 0, composition.durationInFrames - 1), imageFormat: "jpeg", jpegQuality, browserExecutable, chromiumOptions, timeoutInMilliseconds: 120000, overwrite: true });
    bytes = fs.statSync(out).size;
    if (bytes < MAX_STILL_BYTES) { progress(job, { phase: "done", progress: 1, bytes, jpegQuality }); break; }
  }
  fs.rmSync(serveUrl, { recursive: true, force: true });
  if (bytes >= MAX_STILL_BYTES) throw new Error(`cover JPEG is ${bytes} bytes at quality 60 (limit ${MAX_STILL_BYTES})`);
}

const SLIDE_SETS = [{ dir: "ig", suffix: "", width: 1080, height: 1350, pinOnly: false }, { dir: "pin", suffix: "-pin", width: 1000, height: 1500, pinOnly: true }];

/** Carousel slides: plan them (compositions/facemetric/slides/plan.ts, needs a node that strips types), then one still per slide and per size, JPEG under 1 MB. */
async function slides(job, outDir) {
  if (!job || !outDir) { console.error("usage: render-job.mjs --slides <job-dir> <out-dir>"); process.exit(2); }
  const meta = JSON.parse(fs.readFileSync(path.join(job, "job.json"), "utf8"));
  if (!meta.slides_composition) throw new Error("job.json has no slides_composition");
  const script = JSON.parse(fs.readFileSync(path.join(job, "script.json"), "utf8"));
  const { parseScript } = await import("./compositions/facemetric/schema.ts");
  const { planSlides } = await import("./compositions/facemetric/slides/plan.ts");
  const plan = planSlides(parseScript(script));
  progress(job, { phase: "bundling", progress: 0, slides: plan.length });
  const base = await getBundle();
  const serveUrl = path.join(job, "bundle");
  fs.rmSync(serveUrl, { recursive: true, force: true });
  fs.cpSync(base, serveUrl, { recursive: true });
  if (fs.existsSync(path.join(job, "public"))) fs.cpSync(path.join(job, "public"), path.join(serveUrl, "public"), { recursive: true });
  await ensureBrowser({ browserExecutable });
  const done = [];
  const total = plan.length + plan.filter((s) => s.pin).length;
  for (const set of SLIDE_SETS) {
    fs.mkdirSync(path.join(outDir, set.dir), { recursive: true });
    let n = 0;
    let composition = null; // same size for every slide of a set: selected once with the first slide's props
    for (const [i, slide] of plan.entries()) {
      if (set.pinOnly && !slide.pin) continue;
      n++;
      const inputProps = { script, slide };
      composition ??= await selectComposition({ serveUrl, id: meta.slides_composition + set.suffix, inputProps, browserExecutable, chromiumOptions, timeoutInMilliseconds: 120000 });
      if (composition.width !== set.width || composition.height !== set.height) throw new Error(`${composition.id} is ${composition.width}x${composition.height}, expected ${set.width}x${set.height}`);
      const file = path.join(outDir, set.dir, String(n).padStart(2, "0") + ".jpg");
      let bytes = 0;
      for (const jpegQuality of [92, 85, 78, 70, 60]) {
        await renderStill({ composition: { ...composition, props: inputProps }, serveUrl, inputProps, output: file, frame: 0, imageFormat: "jpeg", jpegQuality, browserExecutable, chromiumOptions, timeoutInMilliseconds: 120000, overwrite: true });
        bytes = fs.statSync(file).size;
        if (bytes < MAX_STILL_BYTES) break;
      }
      if (bytes >= MAX_STILL_BYTES) throw new Error(`slide ${file} is ${bytes} bytes at quality 60 (limit ${MAX_STILL_BYTES})`);
      done.push({ set: set.dir, file: path.basename(file), kind: slide.kind, beat: slide.index, frame: slide.frame, bytes, plan: i });
      progress(job, { phase: "rendering", progress: Math.round((done.length / total) * 1000) / 1000, slides: done.length });
    }
  }
  fs.writeFileSync(path.join(outDir, "slides.json"), JSON.stringify({ reel_id: meta.reel_id, plan, files: done }, null, 1));
  fs.rmSync(serveUrl, { recursive: true, force: true });
  progress(job, { phase: "done", progress: 1, slides: done.length });
}

async function main() {
  fs.mkdirSync(CACHE, { recursive: true });
  if (process.argv[2] === "--ensure-browser") {
    await ensureBrowser({ browserExecutable });
    console.log(JSON.stringify({ ok: true }));
    return;
  }
  if (process.argv[2] === "--prebundle") {
    await getBundle();
    console.log(JSON.stringify({ ok: true, bundle: sourceKey() }));
    return;
  }
  if (process.argv[2] === "--still") return still(process.argv[3], process.argv[4]);
  if (process.argv[2] === "--slides") return slides(process.argv[3], process.argv[4]);
  const [job, out] = process.argv.slice(2);
  if (!job || !out) { console.error("usage: render-job.mjs <job-dir> <out.mp4>"); process.exit(2); }
  const meta = JSON.parse(fs.readFileSync(path.join(job, "job.json"), "utf8"));
  const inputProps = JSON.parse(fs.readFileSync(path.join(job, "script.json"), "utf8"));

  progress(job, { phase: "bundling", progress: 0 });
  const base = await getBundle();
  // Per-job copy of the bundle so this job's stills/voice/fonts can sit in its public/ folder.
  const serveUrl = path.join(job, "bundle");
  fs.rmSync(serveUrl, { recursive: true, force: true });
  fs.cpSync(base, serveUrl, { recursive: true });
  if (fs.existsSync(path.join(job, "public"))) fs.cpSync(path.join(job, "public"), path.join(serveUrl, "public"), { recursive: true });

  await ensureBrowser({ browserExecutable });
  const composition = await selectComposition({ serveUrl, id: meta.composition, inputProps, browserExecutable, chromiumOptions, timeoutInMilliseconds: 300000 });
  const rates = encodeRates(composition.durationInFrames / composition.fps);
  progress(job, { phase: "rendering", progress: 0, frames: composition.durationInFrames, fps: composition.fps, ...rates });
  // Rendered in chunks that survive a killed run: finished chunks stay in <job>/chunks and a re-run (the container
  // retries render-job) only renders what is missing. Each chunk writes its audio separately with seamless-AAC padding
  // and combineChunks stitches them (the same scheme Remotion Lambda uses). Video chunks must be MPEG-TS: for h264,
  // combineChunks byte-concatenates them, which silently keeps only the first chunk if they are MP4.
  const N = composition.durationInFrames;
  const per = Math.max(30, Number(process.env.RF_CHUNK_FRAMES || 150));
  const chunks = path.join(job, "chunks");
  fs.mkdirSync(chunks, { recursive: true });
  const videoFiles = [], audioFiles = [];
  for (let a = 0, i = 0; a < N; a += per, i++) {
    const b = Math.min(N, a + per) - 1;
    const v = path.join(chunks, `v${String(i).padStart(4, "0")}.ts`), au = path.join(chunks, `a${String(i).padStart(4, "0")}.aac`);
    videoFiles.push(v); audioFiles.push(au);
    if (fs.existsSync(v) && fs.existsSync(au)) continue;
    let last = 0;
    await renderMedia({
      composition, serveUrl, inputProps, browserExecutable, chromiumOptions, timeoutInMilliseconds: 300000, overwrite: true,
      concurrency: Number(process.env.RF_CONCURRENCY || 1), frameRange: [a, b], outputLocation: v + ".part.ts", separateAudioTo: au + ".part.aac",
      forSeamlessAacConcatenation: true, codec: "h264-ts", audioCodec: "aac", imageFormat: "jpeg", videoBitrate: rates.videoBitrate, audioBitrate: rates.audioBitrate,
      onProgress: ({ progress: pr }) => {
        const all = (a + pr * (b - a + 1)) / N;
        if (all - last >= 0.02 || pr >= 1) { last = all; progress(job, { phase: "rendering", progress: Math.round(all * 1000) / 1000, rendered: Math.round(all * N) }); }
      },
    });
    fs.renameSync(au + ".part.aac", au);
    fs.renameSync(v + ".part.ts", v);
  }
  await combineChunks({
    videoFiles, audioFiles, outputLocation: out, codec: "h264", audioCodec: "aac", audioBitrate: rates.audioBitrate,
    fps: composition.fps, framesPerChunk: per, compositionDurationInFrames: N, preferLossless: false,
  });
  fs.rmSync(chunks, { recursive: true, force: true });
  fs.rmSync(serveUrl, { recursive: true, force: true });
  progress(job, { phase: "done", progress: 1, bytes: fs.statSync(out).size });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((e) => { console.error(String(e && e.stack || e)); process.exit(1); });
}
