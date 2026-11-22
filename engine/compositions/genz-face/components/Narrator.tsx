import React from "react";
import { Img, interpolate, useCurrentFrame } from "remotion";
import { assetSrc } from "../../facemetric/components/util.ts";
import { NARRATOR, type Pose } from "../theme.ts";

export const DEFAULT_POSES: Record<string, Pose[]> = {
  narrator: ["point", "think", "cross", "present"],
  cta: ["cross", "present", "point"],
  verdict: ["present"],
  walkout: ["present"],
  hook: ["point"],
  pack: ["point"],
  feature: ["point"],
};

/** The sprite asset for a pose; a pose the outfit has no sprite for (shock / approve until SLA-1641 delivers them) falls back to the first pose it has. */
export function spriteFor(sprites: Partial<Record<Pose, string>>, assets: Record<string, string>, pose: Pose): string | undefined {
  const key = sprites[pose] ?? Object.values(sprites)[0];
  return key ? assets[key] : undefined;
}

/**
 * The Airport Idol, waist-up, bottom-anchored. `full` = 1080 px tall (56-70 % of the frame), centred; `side` = half-size at the right (verdict).
 * The pose swaps on a cut (`step` indexes the beat's pose list) and every swap punches the scale (frame `since` = frames since the cut).
 */
export const Narrator: React.FC<{ src?: string; mode: "full" | "side"; since: number; enter: number }> = ({ src, mode, since, enter }) => {
  const frame = useCurrentFrame();
  if (!src) return null;
  const punch = interpolate(since, [0, NARRATOR.punchFrames], [NARRATOR.punch, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const rise = interpolate(enter, [0, 8], [60, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const h = mode === "full" ? NARRATOR.full : NARRATOR.side;
  const float = Math.sin(frame / 18) * 4;
  const pos: React.CSSProperties = mode === "full" ? { left: "50%", transform: `translateX(-50%) translateY(${rise + float}px) scale(${1 + punch})` } : { right: NARRATOR.sideRight, transform: `translateY(${rise + float}px) scale(${1 + punch})` };
  return <Img src={assetSrc(src)} style={{ position: "absolute", bottom: 0, height: h, width: "auto", zIndex: 2, transformOrigin: "50% 100%", filter: "drop-shadow(0 20px 40px rgba(0,0,0,.6))", ...pos }} />;
};
