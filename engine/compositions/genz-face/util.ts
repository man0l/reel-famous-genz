import { staticFile } from "remotion";

/** Still / asset path from script.json (relative to the job's public/ folder) -> URL. */
export function assetSrc(path: string): string {
  if (/^(https?:|data:|blob:)/.test(path)) return path;
  return staticFile(path.replace(/^\/+/, ""));
}

export const pad2 = (i: number): string => String(i).padStart(2, "0");
