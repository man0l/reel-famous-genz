import { Easing, staticFile } from "remotion";

export const clamp01 = (x: number): number => Math.min(1, Math.max(0, x));
export const easeOut = (t: number): number => Easing.out(Easing.cubic)(clamp01(t));
export const easeInOut = (t: number): number => Easing.inOut(Easing.cubic)(clamp01(t));

/** Still / asset path from script.faces (relative to the job's public/ folder) -> URL. */
export function assetSrc(path: string): string {
  if (/^(https?:|data:|blob:)/.test(path)) return path;
  return staticFile(path.replace(/^\/+/, ""));
}

/** Rough text width (px) of Montserrat 800/900 uppercase at `fontSize`, used to keep chips on the canvas. */
export const textWidth = (text: string, fontSize: number, em = 0.7): number => text.length * fontSize * em;
