import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { CANVAS, GAME, LANES, SPARKLES } from "../theme.ts";

/** Deterministic sparkle field (the probe's random.seed(7) look): mulberry32, so every frame and every render agree. */
export function sparkles(n: number, seed = 7): { x: number; y: number; s: number; o: number; ph: number }[] {
  let a = seed >>> 0;
  const rnd = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const sizes = [18, 26, 36, 48, 64];
  const ops = [0.35, 0.5, 0.7, 0.9];
  return Array.from({ length: n }, () => ({ x: 2 + rnd() * 96, y: 2 + rnd() * 96, s: sizes[Math.floor(rnd() * 5)], o: ops[Math.floor(rnd() * 4)], ph: rnd() * Math.PI * 2 }));
}

const STAR = "polygon(50% 0%, 58% 42%, 100% 50%, 58% 58%, 50% 100%, 42% 58%, 0% 50%, 42% 42%)";

/** Lane background: K-pop lens = lane glows + stage floor + sparkles; game-card lens = pack-opening night with conic rays. */
export const Stage: React.FC<{ lane: "A" | "B"; lens: "kpop" | "gamecard" }> = ({ lane, lens }) => {
  const frame = useCurrentFrame();
  const t = LANES[lane];
  const field = useMemo(() => sparkles(SPARKLES), []);
  if (lens === "gamecard") {
    const g = GAME[t.gamecard];
    return (
      <AbsoluteFill style={{ background: GAME.canvas }}>
        <AbsoluteFill style={{ background: GAME.bg }} />
        <div style={{ position: "absolute", inset: -400, background: `repeating-conic-gradient(from ${frame * 0.15}deg at 50% 50%, rgba(0,0,0,0) 0deg 9deg, ${g.rays} 9deg 12deg)` }} />
        <div style={{ position: "absolute", left: "50%", top: "46%", width: 900, height: 900, transform: "translate(-50%,-50%)", background: `radial-gradient(circle, ${g.glow}, rgba(0,0,0,0) 60%)` }} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: `${t.glow}, ${CANVAS}` }}>
      <div style={{ position: "absolute", left: "-10%", right: "-10%", bottom: 0, height: 520, background: "linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,.06))", borderTop: "2px solid rgba(255,255,255,.08)" }} />
      {field.map((s, i) => (
        <span
          key={i}
          style={{
            position: "absolute",
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: s.s,
            height: s.s,
            opacity: s.o * (0.65 + 0.35 * Math.sin(frame / 14 + s.ph)),
            background: t.sparkle,
            clipPath: STAR,
            filter: "drop-shadow(0 0 10px #fff)",
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
