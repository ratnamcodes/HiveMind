import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GEIST, GEIST_MONO } from "../fonts";
import { BRAND } from "../timeline";
import { HiveMark } from "./HiveMark";
import { DynatraceLogo } from "./DynatraceLogo";

// Opening card: personal hackathon intro. Friendly, clean — sets up the submission
// before the cold-open hook.
export const IntroCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoIn = spring({ frame, fps, config: { damping: 16, stiffness: 150, mass: 0.9 } });
  const nameIn = spring({ frame: frame - 10, fps, config: { damping: 200 } });
  const hackIn = spring({ frame: frame - 22, fps, config: { damping: 200 } });
  const trackIn = spring({ frame: frame - 38, fps, config: { damping: 18, stiffness: 150 } });
  const urlIn = spring({ frame: frame - 58, fps, config: { damping: 200 } });
  const drift = interpolate(frame, [0, 300], [1, 1.03]);

  return (
    <AbsoluteFill style={{ background: BRAND.stageDeep, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 60% 50% at 50% 40%, rgba(249,115,22,0.12), transparent 70%)`,
        }}
      />
      <div style={{ transform: `scale(${drift})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ transform: `scale(${logoIn})`, display: "flex", alignItems: "center", gap: 22 }}>
          <HiveMark size={96} />
          <div style={{ fontFamily: GEIST, fontWeight: 800, fontSize: 92, color: "white", letterSpacing: "-0.04em" }}>
            HiveMind
          </div>
        </div>

        <div
          style={{
            marginTop: 18,
            fontFamily: GEIST,
            fontWeight: 500,
            fontSize: 34,
            color: "rgba(255,255,255,0.62)",
            opacity: nameIn,
            transform: `translateY(${interpolate(nameIn, [0, 1], [18, 0])}px)`,
          }}
        >
          by Ratnam
        </div>

        <div
          style={{
            marginTop: 46,
            fontFamily: GEIST,
            fontWeight: 700,
            fontSize: 40,
            color: "white",
            letterSpacing: "-0.02em",
            opacity: hackIn,
            transform: `translateY(${interpolate(hackIn, [0, 1], [18, 0])}px)`,
          }}
        >
          Google Cloud Rapid Agent Hackathon
        </div>

        {/* Dynatrace track pill */}
        <div
          style={{
            marginTop: 22,
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "14px 26px",
            borderRadius: 999,
            background: "rgba(20,150,255,0.10)",
            border: `1.5px solid ${BRAND.dynatrace}`,
            opacity: trackIn,
            transform: `scale(${interpolate(trackIn, [0, 1], [0.9, 1])})`,
          }}
        >
          <DynatraceLogo size={34} />
          <span style={{ fontFamily: GEIST, fontWeight: 600, fontSize: 30, color: "#7CC4FF" }}>
            Dynatrace Track
          </span>
        </div>

        <div
          style={{
            marginTop: 40,
            fontFamily: GEIST_MONO,
            fontWeight: 500,
            fontSize: 26,
            color: "rgba(255,255,255,0.4)",
            opacity: urlIn,
          }}
        >
          rapid-agent.devpost.com
        </div>
      </div>
    </AbsoluteFill>
  );
};
