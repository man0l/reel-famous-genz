import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Freeze, Img, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { assetSrc, pad2 } from "./util.ts";
import { Fonts } from "./components/Fonts.tsx";
import { Stage } from "./components/Stage.tsx";
import { Caption } from "./components/Text.tsx";
import { DEFAULT_POSES, Narrator, spriteFor } from "./components/Narrator.tsx";
import { CalloutView } from "./components/Callout.tsx";
import { BridgeText, CtaView, HookView, PackView, VerdictView, WalkoutView } from "./components/Cards.tsx";
import { CheckView, TopicView, TypeHeader, VersusView } from "./components/SelfTest.tsx";
import { cutRect } from "./geometry.ts";
import { parseScript, type Beat, type Script } from "./schema.ts";
import { FPS } from "./theme.ts";
import type { Pose } from "./theme.ts";
import { captionAt, fadeIn, framesSinceCut, plan, stepAt, type BeatPlan, type Plan } from "./timing.ts";

const planOf = (s: Script): Plan =>
  plan(
    s.durations,
    s.beats.map((b) => b.vo),
    undefined,
    s.loop ?? 0,
    s.end_hold,
  );

/** The cut a callout pops on: its explicit chunk, else the beat's k-th cut (so pops are counted cuts). */
const popChunk = (bp: BeatPlan, k: number, chunk?: number): number => chunk ?? bp.cuts[Math.min(k, bp.cuts.length - 1)] ?? 0;

const BeatView: React.FC<{ script: Script; index: number; bp: BeatPlan }> = ({ script, index, bp }) => {
  const frame = useCurrentFrame();
  const { time, parts, windows, cuts } = bp;
  const T = (time.from + frame) / FPS;
  const t = Math.max(0, T - time.off);
  const j = Math.max(0, captionAt(windows, t));
  const step = stepAt(cuts, j);
  const since = framesSinceCut(windows, cuts, j, t);
  const beat: Beat = script.beats[index];
  const { lane, lens } = script;
  const poseList: Pose[] = beat.poses?.length ? beat.poses : DEFAULT_POSES[beat.kind];
  const pose = poseList[Math.max(0, step) % poseList.length];
  const sprite = spriteFor(script.sprites, script.assets, pose);
  const enter = Math.round(t * FPS);
  const img = "img" in beat && beat.img ? script.assets[beat.img] : "";
  const imgs = beat.kind === "topic" ? (beat.imgs ?? []) : beat.kind === "versus" ? [...beat.imgs] : [];
  const srcs = imgs.map((k) => script.assets[k]);
  const ratios = imgs.map((k) => script.ratios[k]);
  const [from, to] = windows[j] ?? [0, time.shown];
  // the narrator carries the self-test: the topic card without a face and every check stand on him (75-80 % on screen, like @glowupmenclub's E reels)
  const onChar = beat.kind === "narrator" || beat.kind === "cta" || beat.kind === "verdict" || beat.kind === "walkout" || beat.kind === "check" || (beat.kind === "topic" && !imgs.length);
  const showNarrator = onChar;
  const side = beat.kind === "verdict" || beat.kind === "walkout";
  return (
    <AbsoluteFill style={{ opacity: fadeIn(index, T, time.off) }}>
      {beat.kind === "hook" ? <HookView b={beat} lane={lane} src={img} hangul={script.hangul} since={enter} /> : null}
      {beat.kind === "pack" ? <PackView b={beat} since={enter} /> : null}
      {beat.kind === "narrator" ? <BridgeText lines={beat.lines} lane={lane} since={enter} /> : null}
      {beat.kind === "feature" ? <FeatureView script={script} beat={beat} bp={bp} t={t} step={step} since={since} img={img} /> : null}
      {beat.kind === "verdict" ? <VerdictView b={beat} lane={lane} src={img} hangul={script.hangul} since={enter} chime={script.sfx} /> : null}
      {beat.kind === "walkout" ? <WalkoutView b={beat} lane={lane} src={img} since={enter} /> : null}
      {beat.kind === "cta" ? <CtaView b={beat} lane={lane} since={enter} /> : null}
      {beat.kind === "topic" ? <TopicView b={beat} srcs={srcs} ratios={ratios} since={enter} /> : null}
      {beat.kind === "check" ? <CheckView b={beat} src={img || undefined} ratio={beat.img ? script.ratios[beat.img] : undefined} since={enter} /> : null}
      {beat.kind === "type" ? (
        <>
          <FeatureView script={script} beat={beat} bp={bp} t={t} step={step} since={since} img={img} />
          <TypeHeader b={beat} since={enter} />
        </>
      ) : null}
      {beat.kind === "versus" ? <VersusView b={beat} srcs={srcs as [string, string]} ratios={ratios as [number, number]} since={enter} /> : null}
      {showNarrator ? <Narrator src={sprite} mode={side ? "side" : "full"} since={since} enter={enter} /> : null}
      <Caption chunk={parts[j] ?? ""} hot={beat.hot} t={t} from={from} to={to} onChar={onChar} bottom={beat.kind === "hook" || beat.kind === "pack" || (beat.kind === "topic" && imgs.length) ? 210 : 430} gamecard={lens === "gamecard"} />
    </AbsoluteFill>
  );
};

/** Feature beat: the painted cutout at 85-95 % frame height with callouts anchored on image fractions; every cut punches the crop in a little. */
const FeatureView: React.FC<{ script: Script; beat: Extract<Beat, { kind: "feature" | "type" }>; bp: BeatPlan; t: number; step: number; since: number; img: string }> = ({ script, beat, bp, t, step, since, img }) => {
  const key = beat.img;
  const ratio = script.ratios[key];
  const punch = interpolate(since, [0, 8], [0.05, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const scale = 1 + 0.025 * Math.max(0, step) + punch + (0.015 * t) / Math.max(1, bp.time.shown);
  const rect = cutRect(beat.crop, ratio, scale);
  return (
    <>
      <Img src={assetSrc(img)} style={{ position: "absolute", left: rect.left, top: rect.top, width: rect.width, zIndex: 1, filter: "drop-shadow(0 30px 50px rgba(0,0,0,.55))" }} />
      {beat.callouts.map((c, k) => {
        const at = bp.windows[popChunk(bp, k, c.chunk)]?.[0] ?? 0;
        const sinceC = Math.round((t - at) * FPS) - 4;
        return sinceC >= 0 ? <CalloutView key={k} c={c} rect={rect} since={sinceC} hangul={script.hangul} /> : null;
      })}
    </>
  );
};

const Music: React.FC<{ music: NonNullable<Script["music"]>; total: number }> = ({ music, total }) => {
  const frame = useCurrentFrame();
  const gain = music.volume ?? 0.14;
  const fin = Math.max(1, Math.round((music.fade_in ?? 0.3) * FPS));
  const fout = Math.max(1, Math.min(Math.round((music.fade_out ?? 1.2) * FPS), total - fin - 1));
  const volume = interpolate(frame, [0, fin, total - fout, total], [0, gain, gain, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <Audio src={staticFile(music.src)} loop volume={volume} name="music" />;
};

/** The reel for an already validated script: one Sequence per beat (picture + text, crossfaded), one voice clip per beat, lightstick clicks on callouts, a chime on the verdict. */
export const ReelView: React.FC<{ script: Script; audio?: boolean }> = ({ script, audio = true }) => {
  const pl = useMemo(() => planOf(script), [script]);
  const sfx = useMemo(() => {
    const out: { at: number; src: string; vol: number }[] = [];
    script.beats.forEach((b, i) => {
      const bp = pl.beats[i];
      if (b.kind === "check" || b.kind === "versus") out.push({ at: bp.time.off + 4 / FPS, src: "sfx/click.wav", vol: 0.5 });
      if (b.kind === "feature" || b.kind === "type") b.callouts.forEach((c, k) => out.push({ at: bp.time.off + (bp.windows[popChunk(bp, k, c.chunk)]?.[0] ?? 0) + 4 / FPS, src: "sfx/click.wav", vol: 0.5 }));
      if (b.kind === "verdict" || b.kind === "walkout") out.push({ at: bp.time.off + 0.3, src: "sfx/chime.wav", vol: 0.6 });
    });
    return out;
  }, [script, pl]);
  return (
    <AbsoluteFill style={{ background: "#0D0718", color: "#fff" }}>
      <Fonts />
      <Stage lane={script.lane} lens={script.lens} />
      {/* SLA-1685 (board, 24 Nov): no episode tag and no credit line in the picture; the photo credit and AI-edited note ride in the post text */}
      {pl.tl.beats.map((time, i) => (
        <Sequence key={i} from={time.from} durationInFrames={time.frames} name={`beat ${pad2(i)} ${script.beats[i].kind}`} layout="none">
          <BeatView script={script} index={i} bp={pl.beats[i]} />
        </Sequence>
      ))}
      {pl.tl.frames > pl.tl.body ? (
        // SLA-1685: silent loop tail, frame 0 of the hook held after the CTA so the replay reads as one loop (facemetric's SLA-1547 pattern)
        <Sequence from={pl.tl.body} durationInFrames={pl.tl.frames - pl.tl.body} name="loop tail" layout="none">
          <Freeze frame={0}>
            <BeatView script={script} index={0} bp={pl.beats[0]} />
          </Freeze>
        </Sequence>
      ) : null}
      {audio
        ? pl.tl.beats.map((time, i) => (
            <Sequence key={`a${i}`} from={time.from} durationInFrames={Math.round(time.span * FPS)} name={`vo ${pad2(i)}`} layout="none">
              <Audio src={staticFile(`vo/${pad2(i)}.mp3`)} />
            </Sequence>
          ))
        : null}
      {audio && script.sfx
        ? sfx.map((s, i) => (
            <Sequence key={`s${i}`} from={Math.round(s.at * FPS)} durationInFrames={Math.round(1.2 * FPS)} name="sfx" layout="none">
              <Audio src={staticFile(s.src)} volume={s.vol} />
            </Sequence>
          ))
        : null}
      {audio && script.music ? <Music music={script.music} total={pl.tl.frames} /> : null}
    </AbsoluteFill>
  );
};

/** Composition component: props are the whole script.json (with `durations`). Throws on an invalid script. */
export const Reel: React.FC<Record<string, unknown>> = (props) => {
  const script = useMemo(() => parseScript(props), [props]);
  return <ReelView script={script} />;
};

/** Frames of the whole reel for the given props (the composition length). */
export const totalFrames = (props: unknown): number => planOf(parseScript(props)).tl.frames;
