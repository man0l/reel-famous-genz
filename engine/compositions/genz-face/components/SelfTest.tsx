import React from "react";
import { Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { assetSrc } from "../util.ts";
import { FONT, LANES, PETAL, PHOTOCARD, SELFTEST } from "../theme.ts";
import { Em } from "./Text.tsx";
import type { Beat } from "../schema.ts";

type Of<K extends Beat["kind"]> = Extract<Beat, { kind: K }>;

const shadowText = "0 8px 30px rgba(0,0,0,.7), 0 0 60px rgba(201,184,255,.35)";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const fade = (since: number, delay = 0, len = 5): number => interpolate(since - delay, [0, len], [0, 1], clamp);

/** The step number of a check or a type: a dark pill with the number in Anton, like @glowupmenclub's "1" / "2" / "3" bar. */
export const NumPill: React.FC<{ n: number | string; since: number; style?: React.CSSProperties }> = ({ n, since, style }) => {
  const { fps } = useVideoConfig();
  const pop = spring({ frame: since, fps, config: { damping: 14, stiffness: 200 } });
  return (
    <div
      style={{
        display: "inline-block",
        minWidth: 150,
        textAlign: "center",
        font: `400 78px/1 ${FONT.num}`,
        padding: "12px 34px 8px",
        borderRadius: 22,
        color: PETAL,
        background: "rgba(13,7,24,.82)",
        boxShadow: "0 0 0 4px rgba(255,214,242,.45), 0 20px 40px rgba(0,0,0,.5)",
        transform: `scale(${0.7 + 0.3 * pop})`,
        ...style,
      }}
    >
      {n}
    </div>
  );
};

/** A painted cutout inside a holo frame, cropped by `crop` (image width / left / top in card pixels), with optional guide lines at image-fraction y. */
const DemoCard: React.FC<{ src: string; ratio: number; w: number; h: number; crop: { w: number; x: number; y: number }; marks?: number[]; since: number; label?: string; tilt?: number }> = ({
  src,
  ratio,
  w,
  h,
  crop,
  marks,
  since,
  label,
  tilt = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: since, fps, config: { damping: 16, stiffness: 140 } });
  const imgH = crop.w * ratio;
  return (
    <div
      style={{
        position: "relative",
        width: w,
        padding: 10,
        borderRadius: 34,
        background: `conic-gradient(from ${20 + frame * 1.2}deg, #ffb3ec, #b3fff2, #fff3b3, #c9b8ff, #ffb3ec)`,
        boxShadow: "0 30px 70px rgba(0,0,0,.6), 0 0 50px rgba(255,214,242,.25)",
        transform: `rotate(${tilt * (1 - 0.35 * (1 - pop))}deg) scale(${0.9 + 0.1 * pop})`,
      }}
    >
      <div style={{ position: "relative", height: h, borderRadius: 26, overflow: "hidden", background: LANES.B.cardInner }}>
        <Img src={assetSrc(src)} style={{ position: "absolute", width: crop.w, left: crop.x, top: crop.y }} />
        {(marks ?? []).map((m, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 0,
              width: `${100 * fade(since, 8 + i * 5, 6)}%`,
              top: crop.y + m * imgH - 2,
              height: 4,
              background: PETAL,
              boxShadow: "0 0 12px rgba(255,79,163,.9)",
            }}
          />
        ))}
        {label ? (
          <div style={{ position: "absolute", left: 22, top: 18, font: `400 110px/1 ${FONT.num}`, color: PETAL, textShadow: "0 6px 24px rgba(0,0,0,.85)" }}>{label}</div>
        ) : null}
      </div>
    </div>
  );
};

/** Self-diagnosis hook (C, D, E): the topic as the headline ("ATTRACTIVE TO *GIRLS?*"), the sub line, then the narrator (no image), one demo face, or A/B faces; optional number pills. */
export const TopicView: React.FC<{ b: Of<"topic">; srcs: string[]; ratios: number[]; since: number }> = ({ b, srcs, ratios, since }) => {
  const head = b.head.length;
  const subTop = 200 + head * 98 + 30;
  const pillTop = subTop + (b.sub ? 80 : 10);
  return (
    <>
      <h1 style={{ position: "absolute", left: 60, right: 60, top: 200, margin: 0, font: `900 104px/.98 ${FONT.kr}`, letterSpacing: "-.02em", textAlign: "center", textShadow: shadowText, zIndex: 3 }}>
        {b.head.map((l, i) => (
          <div key={i} style={{ opacity: fade(since, i * 4) }}>
            <Em text={l} lane="B" />
          </div>
        ))}
      </h1>
      {b.sub ? <div style={{ position: "absolute", left: 60, right: 60, top: subTop, textAlign: "center", font: `500 42px/1.2 ${FONT.kr}`, color: "rgba(255,255,255,.88)", zIndex: 3, opacity: fade(since, 6) }}>{b.sub}</div> : null}
      {b.pills?.length ? (
        <div style={{ position: "absolute", left: 60, right: 60, top: pillTop, display: "flex", justifyContent: "center", gap: 22, zIndex: 3 }}>
          {b.pills.map((p, i) => (
            <NumPill key={i} n={p} since={since - 10 - i * 4} style={{ minWidth: 120, fontSize: 60 }} />
          ))}
        </div>
      ) : null}
      {srcs.length === 1 ? (
        <div style={{ position: "absolute", left: PHOTOCARD.left + 20, top: Math.max(640, pillTop + 40), zIndex: 2 }}>
          <DemoCard src={srcs[0]} ratio={ratios[0]} w={PHOTOCARD.width - 40} h={SELFTEST.topicCardH} crop={{ w: 1000, x: -150, y: -140 }} since={since} tilt={3} />
        </div>
      ) : null}
      {srcs.length === 2
        ? srcs.map((s, i) => (
            <div key={i} style={{ position: "absolute", left: i ? 556 : 44, top: Math.max(660, pillTop + 40), zIndex: 2 }}>
              <DemoCard src={s} ratio={ratios[i]} w={480} h={SELFTEST.versusH} crop={{ w: 720, x: -120, y: -110 }} since={since - i * 4} label={b.labels?.[i]} tilt={i ? 2 : -2} />
            </div>
          ))
        : null}
    </>
  );
};

/** Self-test check (E): number pill, title and chip above the centred narrator; with a demo, the text sits left and the demo card right. */
export const CheckView: React.FC<{ b: Of<"check">; src?: string; ratio?: number; since: number }> = ({ b, src, ratio, since }) => {
  const demo = !!src;
  const box: React.CSSProperties = demo ? { left: 60, width: 560, textAlign: "left" } : { left: 60, right: 60, textAlign: "center" };
  return (
    <>
      <div style={{ position: "absolute", top: 190, zIndex: 3, ...box }}>
        <NumPill n={b.n} since={since} />
        <div style={{ marginTop: 34, font: `900 ${demo ? 76 : 92}px/1 ${FONT.kr}`, letterSpacing: "-.02em", textShadow: shadowText, opacity: fade(since, 4) }}>
          <Em text={b.title} lane="B" />
        </div>
        {b.chip ? (
          <div style={{ marginTop: 22, display: "inline-block", font: `600 36px/1.3 ${FONT.kr}`, color: PETAL, background: "rgba(13,7,24,.8)", padding: "14px 24px", borderRadius: 18, opacity: fade(since, 8) }}>{b.chip}</div>
        ) : null}
      </div>
      {demo ? (
        <div style={{ position: "absolute", left: 640, top: 170, zIndex: 3 }}>
          <DemoCard src={src} ratio={ratio ?? 1.3} w={SELFTEST.demoW} h={SELFTEST.demoH} crop={b.demo_crop ?? SELFTEST.demoCrop} marks={b.marks} since={since - 6} tilt={3} />
        </div>
      ) : null}
    </>
  );
};

/** Type header (C): the number pill and the type name over the demo face. */
export const TypeHeader: React.FC<{ b: Of<"type">; since: number }> = ({ b, since }) => (
  <div style={{ position: "absolute", left: 60, right: 60, top: 170, textAlign: "center", zIndex: 4 }}>
    <NumPill n={b.n} since={since} />
    <div style={{ marginTop: 22, font: `900 88px/1 ${FONT.kr}`, letterSpacing: "-.02em", textShadow: "0 6px 26px rgba(0,0,0,.9), 0 0 40px rgba(13,7,24,.9)", opacity: fade(since, 3) }}>
      <Em text={b.title} lane="B" />
    </div>
  </div>
);

/** This or that (D): the compared feature on top, two faces side by side with A / B, a chip under each. */
export const VersusView: React.FC<{ b: Of<"versus">; srcs: [string, string]; ratios: [number, number]; since: number }> = ({ b, srcs, ratios, since }) => {
  const labels = b.labels ?? ["A", "B"];
  const crops = b.crops ?? [SELFTEST.versusCrop, SELFTEST.versusCrop];
  return (
    <>
      <div style={{ position: "absolute", left: 60, right: 60, top: 190, textAlign: "center", font: `900 92px/1 ${FONT.kr}`, letterSpacing: "-.02em", textShadow: shadowText, zIndex: 3, opacity: fade(since, 0) }}>
        <Em text={b.title} lane="B" />
      </div>
      {srcs.map((s, i) => (
        <div key={i} style={{ position: "absolute", left: i ? 556 : 44, top: 360, zIndex: 2 }}>
          <DemoCard src={s} ratio={ratios[i]} w={480} h={SELFTEST.versusH} crop={crops[i]} since={since - i * 5} label={labels[i]} tilt={i ? 2 : -2} />
          {b.chips?.[i] ? (
            <div style={{ marginTop: 26, textAlign: "center", font: `700 38px/1.25 ${FONT.kr}`, color: PETAL, background: "rgba(13,7,24,.82)", padding: "14px 18px", borderRadius: 18, opacity: fade(since, 10 + i * 5) }}>{b.chips[i]}</div>
          ) : null}
        </div>
      ))}
      <div style={{ position: "absolute", left: 490, top: 700, width: 100, textAlign: "center", font: `400 70px/1 ${FONT.num}`, color: "#fff", textShadow: "0 0 30px rgba(255,79,163,.9)", zIndex: 4, opacity: fade(since, 6) }}>VS</div>
    </>
  );
};

