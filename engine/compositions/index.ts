import type { CompositionDef } from "./types";
import { genzFace } from "./genz-face";

// reel-famous-genz renders only its own composition. facemetric/ and qoves/ hold the three helper files genz-face imports, copied from reel-factory.
export const compositions: CompositionDef[] = [genzFace];
