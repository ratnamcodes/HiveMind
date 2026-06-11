import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { Cam, FPS, SRC_H, SRC_W } from "../timeline";

// Camera engine: the 1440x900 recording sits centered on the 1920x1080 stage in
// a rounded "window"; the camera scales/translates it so (cx, cy) in source
// pixels lands at the comp center at zoom z (z=0.88 shows the framed wide shot).
export const DemoShot: React.FC<{
  srcStart: number;
  rate?: number;
  durInFrames: number;
  camFrom: Cam;
  camTo: Cam;
}> = ({ srcStart, rate = 1, durInFrames, camFrom, camTo }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, durInFrames], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const z = interpolate(p, [0, 1], [camFrom.z, camTo.z]);
  const cx = interpolate(p, [0, 1], [camFrom.cx, camTo.cx]);
  const cy = interpolate(p, [0, 1], [camFrom.cy, camTo.cy]);

  const s = z * 1.2; // base fit scale for 1440->1920 is 1.333; we treat z=1 as 1.2 for margins
  const tx = SRC_W / 2 - cx;
  const ty = SRC_H / 2 - cy;

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: (1920 - SRC_W) / 2,
          top: (1080 - SRC_H) / 2,
          width: SRC_W,
          height: SRC_H,
          transform: `scale(${s}) translate(${tx}px, ${ty}px)`,
          transformOrigin: "center center",
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: 12,
            overflow: "hidden",
            border: "1px solid rgba(255,255,255,0.09)",
            boxShadow: "0 30px 90px rgba(0,0,0,0.65), 0 0 120px rgba(245,158,11,0.06)",
            background: "#0d0f12",
          }}
        >
          <OffthreadVideo
            src={staticFile("video/demo.mp4")}
            trimBefore={Math.round(srcStart * FPS)}
            playbackRate={rate}
            muted
            style={{ width: SRC_W, height: SRC_H }}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
