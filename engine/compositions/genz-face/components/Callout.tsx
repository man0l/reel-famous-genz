import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, PETAL } from "../theme.ts";
import { calloutBox, leadStart } from "../geometry.ts";
import type { Rect } from "../geometry.ts";
import type { Beat } from "../schema.ts";

type Callout = Extract<Beat, { kind: "feature" }>["callouts"][number];

/** Feature callout: dot + ring on the image-fraction anchor, lead line to the nearest side of the box, fan-vocabulary label (+ Hangul accent) and the stat chip. `since` = frames since it popped. */
export const CalloutView: React.FC<{ c: Callout; rect: Rect; since: number; hangul: boolean }> = ({ c, rect, since, hangul }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  void frame;
  const target: [number, number] = [rect.left + c.at[0] * rect.width, rect.top + c.at[1] * rect.height];
  const chip = c.stat ? undefined : c.chip;
  const box = calloutBox(c.pos, c.label + (hangul && c.ko ? "  " + c.ko : ""), c.stat ? "000" : chip, c.w);
  const from = leadStart(box, target);
  const pop = spring({ frame: since, fps, config: { damping: 14, stiffness: 220 } });
  const draw = interpolate(since, [0, 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const x2 = from[0] + (target[0] - from[0]) * draw;
  const y2 = from[1] + (target[1] - from[1]) * draw;
  return (
    <>
      <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0, zIndex: 2, pointerEvents: "none" }}>
        <line x1={from[0]} y1={from[1]} x2={x2} y2={y2} stroke={PETAL} strokeWidth={4} />
        <circle cx={target[0]} cy={target[1]} r={14 * Math.min(1, draw * 2)} fill={PETAL} />
        <circle cx={target[0]} cy={target[1]} r={30 * Math.min(1, draw * 2)} fill="none" stroke={PETAL} strokeWidth={3} opacity={0.8} />
      </svg>
      <div style={{ position: "absolute", left: c.pos[0], top: c.pos[1], width: c.w, zIndex: 3, transform: `scale(${0.8 + 0.2 * pop})`, transformOrigin: "0 100%", opacity: Math.min(1, since / 3) }}>
        <div style={{ whiteSpace: "nowrap", font: `900 50px/1 ${FONT.kr}`, color: "#1A0A2E", background: PETAL, padding: "16px 22px 14px", borderRadius: "16px 16px 0 0", display: "inline-block", letterSpacing: "-.01em" }}>
          {c.label}
          {hangul && c.ko ? <span style={{ fontSize: 30, fontWeight: 700, color: "#C0248A", marginLeft: 10 }}>{c.ko}</span> : null}
        </div>
        {c.stat ? (
          <div style={{ display: "block", background: "rgba(13,7,24,.85)", padding: "10px 22px", borderRadius: "0 16px 16px 16px", font: `400 76px/1 ${FONT.num}`, color: PETAL }}>{Math.round(Number(c.stat[1]) * Math.min(1, since / 10))}</div>
        ) : chip ? (
          <div style={{ font: `600 27px/1.3 ${FONT.kr}`, color: PETAL, background: "rgba(13,7,24,.85)", padding: "14px 22px", borderRadius: "0 16px 16px 16px", display: "block" }}>{chip}</div>
        ) : null}
      </div>
    </>
  );
};
