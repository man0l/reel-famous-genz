import type React from "react";

/** One renderable composition. A format pack's composition folder exports one of these and is listed in compositions/index.ts. */
export interface CompositionDef {
  id: string;
  component: React.ComponentType<any>;
  width: number;
  height: number;
  fps: number;
  defaultProps: Record<string, unknown>;
  frames: (props: any) => number;
}
