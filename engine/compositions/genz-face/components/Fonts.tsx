import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";
import { FONT_FILES } from "../theme.ts";

let loaded = false;
let pending: Promise<void> | null = null;

function loadFonts(): Promise<void> {
  if (!pending) {
    const faces = [
      new FontFace("Noto Sans KR", `url("${staticFile(FONT_FILES.kr)}")`, { weight: "100 900", style: "normal" }),
      new FontFace("Space Grotesk", `url("${staticFile(FONT_FILES.grotesk)}")`, { weight: "300 700", style: "normal" }),
      new FontFace("Anton", `url("${staticFile(FONT_FILES.anton)}")`, { weight: "400", style: "normal" }),
    ];
    pending = Promise.all(faces.map((f) => f.load())).then((ok) => {
      ok.forEach((f) => document.fonts.add(f));
      loaded = true;
    });
  }
  return pending;
}

/** Holds the render until Noto Sans KR (subset), Space Grotesk and Anton (public/fonts: formats/genz-face/fonts + the renderer's fonts) are loaded. Mount once per tree. */
export const Fonts: React.FC = () => {
  const [handle] = useState(() => (loaded ? null : delayRender("genz-face fonts", { timeoutInMilliseconds: 60000 })));
  useEffect(() => {
    if (handle === null) return;
    loadFonts().then(
      () => continueRender(handle),
      (e) => cancelRender(e),
    );
  }, [handle]);
  return null;
};
