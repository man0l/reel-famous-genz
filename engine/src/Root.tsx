import React from "react";
import { Composition } from "remotion";
import { compositions } from "../compositions";

export const Root: React.FC = () => (
  <>
    {compositions.map((c) => (
      <Composition
        key={c.id}
        id={c.id}
        component={c.component as React.FC<any>}
        width={c.width}
        height={c.height}
        fps={c.fps}
        durationInFrames={1}
        defaultProps={c.defaultProps}
        calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, c.frames(props)) })}
      />
    ))}
  </>
);
