import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GEIST } from "../fonts";
import { BRAND } from "../timeline";
import { HiveMark } from "./HiveMark";

// Lower-third brand chip: pops on the spoken word "HiveMind" during the cold open
// (Dollar Shave Club rule: the name lands inside the first sentence, in motion).
export const BrandChip: React.FC<{ at: number; until: number }> = ({ at, until }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = Math.round(at * fps);
  const end = Math.round(until * fps);
  if (frame < start || frame > end) return null;
  const enter = spring({ frame: frame - start, fps, config: { damping: 14, stiffness: 200, mass: 0.6 } });
  const exit = interpolate(frame, [end - 8, end], [1, 0], { extrapolateLeft: "clamp" });
  return (
    <div
      style={{
        position: "absolute",
        left: 90,
        top: 800,
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "16px 28px 16px 18px",
        borderRadius: 16,
        background: "rgba(13,15,18,0.94)",
        border: "1.5px solid rgba(255,255,255,0.14)",
        boxShadow: "0 14px 60px rgba(0,0,0,0.6)",
        opacity: Math.min(enter, exit),
        transform: `translateY(${interpolate(enter, [0, 1], [22, 0])}px) scale(${interpolate(enter, [0, 1], [0.92, 1])})`,
        transformOrigin: "left center",
      }}
    >
      <HiveMark size={44} />
      <span style={{ fontFamily: GEIST, fontWeight: 700, fontSize: 34, color: "white", letterSpacing: "-0.02em" }}>
        HiveMind
      </span>
    </div>
  );
};

// Kinetic 2-4 word titles on the beat grid (Linear grammar): big, fast, gone.
export const KineticTitles: React.FC<{ titles: { at: number; dur: number; text: string }[] }> = ({
  titles,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {titles.map((t, i) => {
        const start = Math.round(t.at * fps);
        const end = Math.round((t.at + t.dur) * fps);
        if (frame < start || frame > end) return null;
        const enter = spring({ frame: frame - start, fps, config: { damping: 13, stiffness: 260, mass: 0.55 } });
        const exit = interpolate(frame, [end - 5, end], [1, 0], { extrapolateLeft: "clamp" });
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 250,
              display: "flex",
              justifyContent: "center",
              opacity: Math.min(enter, exit),
            }}
          >
            <div
              style={{
                fontFamily: GEIST,
                fontWeight: 800,
                fontSize: 84,
                letterSpacing: "-0.01em",
                color: "white",
                textTransform: "uppercase",
                textShadow: "0 6px 30px rgba(0,0,0,0.95), 0 14px 80px rgba(0,0,0,0.8)",
                transform: `scale(${interpolate(enter, [0, 1], [0.85, 1])})`,
                borderBottom: `6px solid ${BRAND.amber500}`,
                paddingBottom: 8,
              }}
            >
              {t.text}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
