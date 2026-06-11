import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GEIST } from "../fonts";
import { BRAND } from "../timeline";
import { HiveMark } from "./HiveMark";

const TAGLINE = ["Incidents,", "fixed", "end", "to", "end."];

export const TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slam = spring({ frame, fps, config: { damping: 14, stiffness: 160, mass: 0.8 } });
  const drift = interpolate(frame, [0, 165], [1, 1.04]);
  const glow = interpolate(frame, [0, 10, 165], [0, 1, 0.75], { extrapolateRight: "clamp" });
  const nodeProgress = interpolate(frame, [6, 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: BRAND.stageDeep, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 55% 45% at 50% 42%, rgba(245,158,11,${0.16 * glow}), transparent 70%)`,
        }}
      />
      <div style={{ transform: `scale(${drift})`, display: "flex", flexDirection: "column", alignItems: "center", gap: 36 }}>
        <div style={{ transform: `scale(${slam})`, display: "flex", alignItems: "center", gap: 28 }}>
          <HiveMark size={120} nodeProgress={nodeProgress} />
          <div style={{ fontFamily: GEIST, fontWeight: 800, fontSize: 110, color: "white", letterSpacing: "-0.04em" }}>
            HiveMind
          </div>
        </div>
        <div style={{ display: "flex", gap: 22 }}>
          {TAGLINE.map((word, i) => {
            const wp = spring({ frame: frame - 16 - i * 4, fps, config: { damping: 200 } });
            return (
              <span
                key={i}
                style={{
                  fontFamily: GEIST,
                  fontWeight: 600,
                  fontSize: 54,
                  color: "rgba(255,255,255,0.92)",
                  letterSpacing: "-0.02em",
                  opacity: wp,
                  transform: `translateY(${interpolate(wp, [0, 1], [34, 0])}px)`,
                  display: "inline-block",
                }}
              >
                {word}
              </span>
            );
          })}
        </div>
        <div
          style={{
            height: 4,
            width: interpolate(
              spring({ frame: frame - 34, fps, config: { damping: 200 } }),
              [0, 1],
              [0, 560]
            ),
            borderRadius: 2,
            background: `linear-gradient(90deg, ${BRAND.amber400}, ${BRAND.amber600})`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
