import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GEIST } from "../fonts";
import { BRAND } from "../timeline";

// "This isn't just for checkouts" — three hackathon-themed verticals fan in, then
// resolve to "Any system. Any incident. Anywhere." Reinforces real-world breadth.
const VERTICALS = [
  { emoji: "💳", title: "Financial Services", line: "A bank's payments" },
  { emoji: "🏥", title: "Healthcare", line: "A hospital's records" },
  { emoji: "🎮", title: "Gaming", line: "A game's launch night" },
];

export const Generalization: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headIn = spring({ frame, fps, config: { damping: 200 } });
  // cards fan in ~0.5s..2.4s; the tagline lands after
  const taglineStart = 9.5 * fps;
  const tagIn = spring({ frame: frame - taglineStart, fps, config: { damping: 18, stiffness: 140 } });
  const cardsFade = interpolate(frame, [taglineStart - 6, taglineStart + 10], [1, 0.18], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: BRAND.stageDeep, alignItems: "center", justifyContent: "center" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 70% 55% at 50% 42%, rgba(249,115,22,0.10), transparent 70%)`,
        }}
      />

      <div
        style={{
          position: "absolute",
          top: 150,
          fontFamily: GEIST,
          fontWeight: 700,
          fontSize: 46,
          color: "rgba(255,255,255,0.92)",
          letterSpacing: "-0.02em",
          opacity: headIn,
          transform: `translateY(${interpolate(headIn, [0, 1], [-18, 0])}px)`,
        }}
      >
        This isn’t just for checkouts.
      </div>

      <div style={{ display: "flex", gap: 40, opacity: cardsFade }}>
        {VERTICALS.map((v, i) => {
          const cIn = spring({ frame: frame - 18 - i * 14, fps, config: { damping: 16, stiffness: 150, mass: 0.8 } });
          return (
            <div
              key={i}
              style={{
                width: 380,
                height: 300,
                borderRadius: 24,
                background: "rgba(255,255,255,0.04)",
                border: "1.5px solid rgba(255,255,255,0.12)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 20,
                opacity: cIn,
                transform: `translateY(${interpolate(cIn, [0, 1], [50, 0])}px) scale(${interpolate(cIn, [0, 1], [0.9, 1])})`,
                boxShadow: "0 24px 70px rgba(0,0,0,0.5)",
              }}
            >
              <div style={{ fontSize: 86 }}>{v.emoji}</div>
              <div style={{ fontFamily: GEIST, fontWeight: 700, fontSize: 34, color: "white", letterSpacing: "-0.02em" }}>
                {v.title}
              </div>
              <div style={{ fontFamily: GEIST, fontWeight: 400, fontSize: 25, color: "rgba(255,255,255,0.55)" }}>
                {v.line}
              </div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 150,
          fontFamily: GEIST,
          fontWeight: 800,
          fontSize: 64,
          letterSpacing: "-0.03em",
          opacity: tagIn,
          transform: `translateY(${interpolate(tagIn, [0, 1], [24, 0])}px)`,
          background: `linear-gradient(100deg, ${BRAND.amber300}, ${BRAND.amber500} 55%, ${BRAND.amber600})`,
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          color: "transparent",
        }}
      >
        Any system. Any incident. Anywhere.
      </div>
    </AbsoluteFill>
  );
};
