import { Reel, totalFrames } from "./Reel.tsx";
import { FPS, H, W } from "./theme.ts";
import type { CompositionDef } from "../types";

/** Smallest valid script: one narrator beat. Real jobs pass the whole script.json (plus durations) as input props. */
export const defaultScript = {
  format: "genz-face",
  lane: "A",
  lens: "kpop",
  episode_type: "celebrity",
  tag: { en: "FACE DEBUT · EP.00" },
  cite: "AI-edited images",
  assets: { "a.png": "stills/a.png" },
  sprites: {},
  ratios: {},
  beats: [{ kind: "narrator", lines: ["hello *idol.*"], vo: "A tiny valid script so the composition always loads." }],
  durations: [3],
};

export const genzFace: CompositionDef = {
  id: "genz-face",
  component: Reel,
  width: W,
  height: H,
  fps: FPS,
  defaultProps: defaultScript,
  frames: (props) => totalFrames(props),
};

export { totalFrames };
