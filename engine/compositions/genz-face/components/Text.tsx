import React from "react";
import { FONT, HOT_PILL, LANES, PETAL, PINK, TEASE } from "../theme.ts";
import { runs } from "../geometry.ts";
import { bare, wordWindows } from "../timing.ts";

/** Markup text: `*em*` takes the lane accent. */
export const Em: React.FC<{ text: string; lane: "A" | "B" }> = ({ text, lane }) => (
  <>
    {runs(text).map((r, i) => (
      <span key={i} style={r.em ? { color: LANES[lane].accent } : undefined}>
        {r.text}
      </span>
    ))}
  </>
);

/**
 * Word-by-word caption of one chunk: Noto Sans KR 800 54 px, spoken words at full strength, the rest dimmed, hot words in the pink pill.
 * `t` is the beat time in seconds, [from, to) the chunk's window.
 */
export const Caption: React.FC<{ chunk: string; hot?: string[]; t: number; from: number; to: number; onChar?: boolean; bottom?: number; right?: number; gamecard?: boolean }> = ({ chunk, hot = [], t, from, to, onChar, bottom = 430, right = 80, gamecard }) => {
  const ws = chunk.split(/\s+/).filter(Boolean);
  const win = wordWindows(ws, from, to);
  const hotSet = new Set(hot.map(bare));
  return (
    <div style={{ position: "absolute", left: 80, right, bottom, textAlign: "center", font: `800 54px/1.2 ${FONT.kr}`, letterSpacing: "-.01em", textShadow: "0 4px 16px rgba(0,0,0,.9), 0 0 30px rgba(255,79,163,.35)", zIndex: 6 }}>
      {ws.map((w, i) => {
        const on = t >= win[i][0] - 0.02;
        const isHot = hotSet.has(bare(w));
        const style: React.CSSProperties = { color: isHot ? (gamecard ? "#FFD778" : PETAL) : `rgba(255,255,255,${on ? 0.95 : 0.4})`, opacity: on ? 1 : 0.55 };
        if (isHot) Object.assign(style, { background: onChar ? "rgba(255,79,163,.55)" : HOT_PILL, padding: "0 14px", borderRadius: 14, boxShadow: "0 0 30px rgba(255,79,163,.5)" });
        else if (onChar) Object.assign(style, { background: "rgba(0,0,0,.62)", padding: "4px 14px", borderRadius: 12, boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone" });
        return (
          <React.Fragment key={i}>
            <span style={style}>{w}</span>{" "}
          </React.Fragment>
        );
      })}
    </div>
  );
};

/** SLA-1685 (board, 24 Nov): the small tease row at the top ("wait for #4…" plus the "2/4" chip of the feature on screen); no entrance, so frame 0 is the finished layout. */
export const TeaseRow: React.FC<{ text: string; line: boolean; n: number; of: number }> = ({ text, line, n, of }) =>
  line || n ? (
    <div style={{ position: "absolute", left: 0, right: 0, top: TEASE.top, display: "flex", justifyContent: "center", alignItems: "center", gap: TEASE.gap, zIndex: 7 }}>
      {line ? (
        <span style={{ font: `700 ${TEASE.size}px/1.2 ${FONT.kr}`, color: "#fff", background: "rgba(0,0,0,.55)", padding: "6px 22px", borderRadius: 16, textShadow: "0 2px 10px rgba(0,0,0,.8)" }}>{text}</span>
      ) : null}
      {n ? (
        <span style={{ font: `700 ${TEASE.chip}px/1.2 ${FONT.tag}`, color: "#fff", background: n === of ? PINK : "rgba(255,255,255,.18)", border: "2px solid rgba(255,255,255,.55)", padding: "4px 18px", borderRadius: 999, boxShadow: n === of ? "0 0 30px rgba(255,79,163,.6)" : "none", fontVariantNumeric: "tabular-nums" }}>
          {n}/{of}
        </span>
      ) : null}
    </div>
  ) : null;
