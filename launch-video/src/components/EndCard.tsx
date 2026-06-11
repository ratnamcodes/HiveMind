import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GEIST } from "../fonts";
import { BRAND } from "../timeline";
import { HiveMark } from "./HiveMark";

export const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoIn = spring({ frame, fps, config: { damping: 16, stiffness: 150, mass: 0.9 } });
  const tagIn = spring({ frame: frame - 10, fps, config: { damping: 200 } });
  const urlIn = spring({ frame: frame - 26, fps, config: { damping: 18, stiffness: 140 } });
  const subIn = spring({ frame: frame - 44, fps, config: { damping: 200 } });
  const partnersIn = spring({ frame: frame - 120, fps, config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ background: BRAND.stageDeep, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 60% 50% at 50% 45%, rgba(245,158,11,0.13), transparent 70%)`,
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 30 }}>
        <div
          style={{
            transform: `scale(${logoIn})`,
            display: "flex",
            alignItems: "center",
            gap: 20,
          }}
        >
          <HiveMark size={84} />
          <div style={{ fontFamily: GEIST, fontWeight: 800, fontSize: 76, color: "white", letterSpacing: "-0.04em" }}>
            HiveMind
          </div>
        </div>
        <div
          style={{
            fontFamily: GEIST,
            fontWeight: 600,
            fontSize: 44,
            color: "rgba(255,255,255,0.9)",
            letterSpacing: "-0.02em",
            opacity: tagIn,
            transform: `translateY(${interpolate(tagIn, [0, 1], [26, 0])}px)`,
          }}
        >
          Incidents, fixed end to end.
        </div>
        <div
          style={{
            fontFamily: GEIST,
            fontWeight: 800,
            fontSize: 108,
            letterSpacing: "-0.03em",
            background: `linear-gradient(100deg, ${BRAND.amber300}, ${BRAND.amber500} 55%, ${BRAND.amber600})`,
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
            opacity: urlIn,
            transform: `scale(${interpolate(urlIn, [0, 1], [0.92, 1])})`,
            marginTop: 14,
          }}
        >
          heyhivemind.com
        </div>
        <div
          style={{
            fontFamily: GEIST,
            fontWeight: 400,
            fontSize: 32,
            color: "rgba(255,255,255,0.55)",
            opacity: subIn,
          }}
        >
          You approve every change.
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 72,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: GEIST,
          fontWeight: 400,
          fontSize: 24,
          color: "rgba(255,255,255,0.38)",
          opacity: partnersIn,
        }}
      >
        Built on Dynatrace · GitLab · Elastic · MongoDB · BigQuery · Vertex AI
      </div>
    </AbsoluteFill>
  );
};
