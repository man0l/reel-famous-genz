import React from "react";
import { Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { assetSrc } from "../../facemetric/components/util.ts";
import { FONT, GAME, HOLO, LANES, PETAL, PHOTOCARD } from "../theme.ts";
import { Em } from "./Text.tsx";
import type { Beat } from "../schema.ts";

type Of<K extends Beat["kind"]> = Extract<Beat, { kind: K }>;

const shadowText = "0 8px 30px rgba(0,0,0,.7), 0 0 60px rgba(201,184,255,.35)";

/** Hook: headline (Noto Sans KR 900 100 px), the "which position / concept" sub line, and the holo photocard with the painted cutout and name strip. */
export const HookView: React.FC<{ b: Of<"hook">; lane: "A" | "B"; src: string; hangul: boolean; since: number }> = ({ b, lane, src, hangul, since }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const subTop = 200 + b.head.length * 98 + 34;
  const cardTop = Math.max(PHOTOCARD.top, subTop + 80);
  const pop = spring({ frame: since, fps, config: { damping: 16, stiffness: 140 } });
  const tilt = (b.tilt ?? (lane === "A" ? -4 : 3)) * (1 - 0.35 * (1 - pop));
  return (
    <>
      <h1 style={{ position: "absolute", left: 60, right: 60, top: 200, margin: 0, font: `900 100px/.98 ${FONT.kr}`, letterSpacing: "-.02em", textShadow: shadowText, zIndex: 3 }}>
        {b.head.map((l, i) => (
          <React.Fragment key={i}>
            {i ? <br /> : null}
            <Em text={l} lane={lane} />
          </React.Fragment>
        ))}
      </h1>
      {b.sub ? (
        <div style={{ position: "absolute", left: 60, right: 60, top: subTop, font: `500 40px/1.2 ${FONT.kr}`, color: "rgba(255,255,255,.85)", zIndex: 3 }}>
          {b.sub}
          {hangul && b.sub_ko ? <span style={{ color: PETAL, fontWeight: 700, marginLeft: 10 }}>{b.sub_ko}</span> : null}
        </div>
      ) : null}
      <div
        style={{
          position: "absolute",
          width: PHOTOCARD.width,
          left: PHOTOCARD.left,
          top: cardTop,
          padding: PHOTOCARD.border,
          borderRadius: PHOTOCARD.radius,
          background: `conic-gradient(from ${20 + frame * 1.2}deg, #ffb3ec, #b3fff2, #fff3b3, #c9b8ff, #ffb3ec)`,
          boxShadow: "0 40px 80px rgba(0,0,0,.6), 0 0 60px rgba(255,214,242,.25)",
          transform: `rotate(${tilt}deg) scale(${0.9 + 0.1 * pop})`,
          zIndex: 2,
        }}
      >
        <div style={{ position: "relative", borderRadius: 30, overflow: "hidden", background: LANES[lane].cardInner, height: PHOTOCARD.innerH }}>
          <Img src={assetSrc(src)} style={{ position: "absolute", width: "118%", left: "-9%", top: "-2%" }} />
          <div style={{ position: "absolute", left: 30, bottom: 26 }}>
            <b style={{ display: "block", font: `900 72px/1 ${FONT.kr}`, letterSpacing: "-.01em", textShadow: "0 4px 20px rgba(0,0,0,.8)" }}>{b.card[0]}</b>
            <i style={{ display: "block", font: `500 24px/1 ${FONT.tag}`, fontStyle: "normal", color: PETAL, marginTop: 10, letterSpacing: ".1em" }}>{b.card[1]}</i>
          </div>
          <div style={{ position: "absolute", right: 30, top: 26, font: `900 22px/1 ${FONT.kr}`, letterSpacing: ".2em", color: "rgba(255,255,255,.75)", textAlign: "right" }}>
            {(b.badge ?? ["FACE", "DEBUT"])[0]}
            <br />
            {(b.badge ?? ["FACE", "DEBUT"])[1]}
          </div>
        </div>
      </div>
    </>
  );
};

/** Narrator beat text (bridge / pivot): 2-3 lines above the narrator, Noto Sans KR 900 86 px, centred. */
export const BridgeText: React.FC<{ lines: string[]; lane: "A" | "B"; since: number }> = ({ lines, lane, since }) => (
  <div style={{ position: "absolute", left: 60, right: 60, top: 220, font: `900 86px/1.04 ${FONT.kr}`, letterSpacing: "-.02em", textAlign: "center", zIndex: 3, textShadow: "0 8px 30px rgba(0,0,0,.7)" }}>
    {lines.map((l, i) => (
      <div key={i} style={{ opacity: interpolate(since - i * 5, [0, 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        <Em text={l} lane={lane} />
      </div>
    ))}
  </div>
);

/** K-pop verdict card: a position (A) or a concept (B) word in the lane accent, one-line reason, up to four chips. No score. */
export const VerdictView: React.FC<{ b: Of<"verdict">; lane: "A" | "B"; src: string; hangul: boolean; since: number; chime: boolean }> = ({ b, lane, src, hangul, since }) => {
  const { fps } = useVideoConfig();
  const pop = spring({ frame: since, fps, config: { damping: 13, stiffness: 120 } });
  const accent = LANES[lane].accent;
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        width: 720,
        top: 200,
        background: "rgba(13,7,24,.88)",
        borderRadius: 36,
        padding: "30px 34px 34px",
        textAlign: "center",
        boxShadow: "0 30px 80px rgba(0,0,0,.6), 0 0 0 4px rgba(255,214,242,.35), 0 0 80px rgba(255,79,163,.3)",
        zIndex: 3,
        transform: `scale(${0.85 + 0.15 * pop})`,
        opacity: Math.min(1, since / 4),
      }}
    >
      <div style={{ font: `700 24px/1 ${FONT.tag}`, letterSpacing: ".22em", color: PETAL, textAlign: "left" }}>{b.head ?? "RESULT"}</div>
      <div style={{ position: "relative", width: 300, height: 390, borderRadius: 24, overflow: "hidden", margin: "30px auto 10px", background: HOLO }}>
        <Img src={assetSrc(src)} style={{ position: "absolute", width: "120%", left: "-10%", top: 0, borderRadius: 20 }} />
      </div>
      <div style={{ font: `900 170px/.95 ${FONT.kr}`, letterSpacing: "-.03em", margin: "18px 0 6px", color: accent, textShadow: `0 0 50px ${accent}99` }}>{b.word}</div>
      <div style={{ font: `600 30px/1.2 ${FONT.kr}`, color: "rgba(255,255,255,.75)", marginBottom: b.chips?.length ? 26 : 0 }}>
        {hangul && b.ko ? b.ko + " · " : ""}
        {b.reason}
      </div>
      {b.chips?.length ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          {b.chips.map(([k, v], i) => (
            <div key={i} style={{ font: `700 24px/1 ${FONT.tag}`, background: "rgba(255,255,255,.07)", border: "2px solid rgba(255,214,242,.35)", padding: "20px 10px", borderRadius: 18, letterSpacing: ".08em", opacity: Math.min(1, Math.max(0, (since - 6 - i * 3) / 4)) }}>
              {k}
              <b style={{ color: PETAL, font: `900 40px/1 ${FONT.kr}`, display: "block", marginTop: 10, letterSpacing: "-.01em" }}>{v}</b>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

/** Comment CTA: headline 140 px with the lane accent word, 3-4 pills (the verdict's lit), next-episode tease. The narrator stands below it. */
export const CtaView: React.FC<{ b: Of<"cta">; lane: "A" | "B"; since: number }> = ({ b, lane, since }) => (
  <>
    <div style={{ position: "absolute", left: 60, right: 60, top: 220, textAlign: "center", zIndex: 3 }}>
      <div style={{ font: `900 140px/.95 ${FONT.kr}`, letterSpacing: "-.03em", textShadow: "0 10px 40px rgba(0,0,0,.7)" }}>
        {b.head.map((l, i) => (
          <React.Fragment key={i}>
            {i ? <br /> : null}
            <Em text={l} lane={lane} />
          </React.Fragment>
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 18, margin: "40px 0 0" }}>
        {b.pills.map((p, i) => {
          const on = b.on === i;
          return (
            <div key={i} style={{ font: `800 44px/1 ${FONT.kr}`, padding: "22px 32px", border: `4px solid ${PETAL}`, borderRadius: 999, color: on ? "#1A0A2E" : PETAL, background: on ? PETAL : "rgba(0,0,0,.4)", opacity: Math.min(1, Math.max(0, (since - 4 - i * 3) / 4)) }}>
              {p}
            </div>
          );
        })}
      </div>
    </div>
    {b.tease ? <div style={{ position: "absolute", left: 80, right: 80, top: b.pills.length > 2 ? 775 : 720, textAlign: "center", font: `500 30px/1.35 ${FONT.kr}`, color: "rgba(255,255,255,.85)", zIndex: 6, textShadow: "0 4px 16px rgba(0,0,0,.9)" }}>{b.tease}</div> : null}
  </>
);

/** Game-card hook (pack opening): foil pack with a tear line, "your pack" line and the name. */
export const PackView: React.FC<{ b: Of<"pack">; since: number }> = ({ b, since }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: since, fps, config: { damping: 11, stiffness: 120 } });
  const shake = since > 20 ? Math.sin(frame * 1.7) * 3 * Math.min(1, (since - 20) / 30) : 0;
  return (
    <>
      <div style={{ position: "absolute", left: 60, right: 60, top: 150, textAlign: "center", font: `400 130px/1 ${FONT.num}`, letterSpacing: ".06em", textShadow: "0 0 40px rgba(255,215,120,.6)", zIndex: 3 }}>
        {b.head.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 270, top: 560, width: 540, height: 780, borderRadius: 36, transform: `rotate(${shake}deg) scale(${0.7 + 0.3 * pop})`, background: `linear-gradient(${120 + frame * 2}deg, #7A4DFF, #FFD778 35%, #FF4FA3 60%, #4DD0FF)`, boxShadow: "0 40px 90px rgba(0,0,0,.7), 0 0 80px rgba(255,215,120,.4)", zIndex: 3 }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 60, height: 14, background: "repeating-linear-gradient(90deg, rgba(255,255,255,.8) 0 18px, transparent 18px 30px)" }} />
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", color: "#1A0A2E", font: `400 120px/1 ${FONT.num}`, letterSpacing: ".06em" }}>
          FACE
          <span style={{ font: `700 34px/1 ${FONT.tag}`, letterSpacing: ".3em", marginTop: 18 }}>PACK</span>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1380, textAlign: "center", font: `500 34px/1 ${FONT.tag}`, letterSpacing: ".08em", color: "rgba(255,255,255,.85)", zIndex: 3 }}>
        {b.sub ?? "your pack"}: <b style={{ color: GAME.gold.accent }}>{b.name}</b>
      </div>
    </>
  );
};

/** Game-card verdict: WALKOUT, the 620x900 card (gold = football, hero = actors) with OVR, name and six stats revealed one by one. Own design, no EA/FUT/Panini assets. */
export const WalkoutView: React.FC<{ b: Of<"walkout">; lane: "A" | "B"; src: string; since: number }> = ({ b, lane, src, since }) => {
  const { fps } = useVideoConfig();
  const v = GAME[LANES[lane].gamecard];
  const pop = spring({ frame: since, fps, config: { damping: 12, stiffness: 100 } });
  const ovr = Math.round(b.ovr * Math.min(1, since / 24));
  return (
    <>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center", font: `400 150px/1 ${FONT.num}`, letterSpacing: ".06em", color: "#fff", textShadow: "0 0 40px rgba(255,215,120,.6)", zIndex: 3, transform: `scale(${1 + 0.2 * (1 - pop)})` }}>WALKOUT</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 320, textAlign: "center", font: `500 34px/1 ${FONT.tag}`, color: "rgba(255,255,255,.8)", letterSpacing: ".08em", zIndex: 3 }}>
        {b.sub ?? "your pack"}: <b style={{ color: GAME.gold.accent }}>{b.name}</b>
      </div>
      <div style={{ position: "absolute", left: 90, top: 420, width: GAME.card.w, height: GAME.card.h, borderRadius: GAME.card.radius, padding: "40px 36px", zIndex: 3, background: v.fill, color: v.text, boxShadow: `0 40px 90px rgba(0,0,0,.7)${v.ring === "none" ? "" : ", " + v.ring}`, transform: `scale(${0.8 + 0.2 * pop}) rotate(${(1 - pop) * -6}deg)` }}>
        <div style={{ position: "absolute", left: 40, top: 40 }}>
          <b style={{ display: "block", font: `400 150px/1 ${FONT.num}` }}>{ovr}</b>
          <span style={{ display: "block", font: `700 28px/1 ${FONT.tag}`, letterSpacing: ".2em", marginTop: 6 }}>FACE</span>
          <span style={{ display: "block", font: `700 22px/1 ${FONT.tag}`, letterSpacing: ".2em", opacity: 0.8, marginTop: 8 }}>{b.rarity}</span>
        </div>
        <div style={{ position: "absolute", right: 30, top: 50, width: 360, height: 400, overflow: "hidden" }}>
          <Img src={assetSrc(src)} style={{ width: "135%", marginLeft: "-18%", marginTop: "-2%", filter: "drop-shadow(0 20px 30px rgba(0,0,0,.4))" }} />
        </div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 470, textAlign: "center", font: `400 96px/1 ${FONT.num}`, letterSpacing: ".06em", borderTop: "3px solid currentColor", borderBottom: "3px solid currentColor", margin: "0 36px", padding: "14px 0 10px" }}>{b.name.split(" ").slice(-1)[0]}</div>
        <div style={{ position: "absolute", left: 36, right: 36, top: 630, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "14px 10px", textAlign: "center" }}>
          {b.stats.map(([k, n], i) => {
            const s = Math.min(1, Math.max(0, (since - 14 - i * 6) / 6));
            return (
              <div key={k} style={{ font: `700 26px/1 ${FONT.tag}`, letterSpacing: ".12em", opacity: s, transform: `scale(${0.7 + 0.3 * s})` }}>
                <b style={{ display: "block", font: `400 76px/1 ${FONT.num}`, marginBottom: 6 }}>{Math.round(Number(n) * s)}</b>
                {k}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
};
