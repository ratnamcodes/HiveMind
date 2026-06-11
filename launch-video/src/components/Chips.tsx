import React from "react";
import {
  AbsoluteFill,
  interpolate,
  interpolateColors,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { GEIST, GEIST_MONO } from "../fonts";
import { BRAND, ChipCue, FPS } from "../timeline";

const Chip: React.FC<{ text: string; x: number; y: number; at: number; until: number }> = ({
  text,
  x,
  y,
  at,
  until,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const startFrame = Math.round(at * fps);
  const endFrame = Math.round(until * fps);
  if (frame < startFrame || frame > endFrame) return null;
  const enter = spring({ frame: frame - startFrame, fps, config: { damping: 16, stiffness: 180, mass: 0.7 } });
  const exit = interpolate(frame, [endFrame - 6, endFrame], [1, 0], {
    extrapolateLeft: "clamp",
  });
  const translate = x > 960 ? "translateX(-100%)" : "";
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        opacity: Math.min(enter, exit),
        transform: `${translate} scale(${interpolate(enter, [0, 1], [0.85, 1])})`,
        transformOrigin: x > 960 ? "right center" : "left center",
        background: "rgba(13,15,18,0.92)",
        border: `1.5px solid ${BRAND.amber500}`,
        borderRadius: 999,
        padding: "16px 30px",
        fontFamily: GEIST_MONO,
        fontWeight: 600,
        fontSize: 30,
        color: BRAND.amber300,
        boxShadow: "0 12px 50px rgba(0,0,0,0.6), 0 0 40px rgba(245,158,11,0.12)",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
};

const CounterChip: React.FC<{ counter: { at: number; until: number } }> = ({ counter }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const startFrame = Math.round(counter.at * fps);
  const endFrame = Math.round(counter.until * fps);
  if (frame < startFrame || frame > endFrame) return null;
  const local = frame - startFrame;
  const enter = spring({ frame: local, fps, config: { damping: 15, stiffness: 170, mass: 0.8 } });
  const exit = interpolate(frame, [endFrame - 6, endFrame], [1, 0], { extrapolateLeft: "clamp" });
  const value = interpolate(local, [6, 48], [1204, 2.9], {
    easing: (t) => 1 - Math.pow(1 - t, 5),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const display = value >= 10 ? Math.round(value).toLocaleString("en-US") : value.toFixed(1);
  const color = interpolateColors(value, [2.9, 300, 1204], [BRAND.emerald, BRAND.amber400, BRAND.red]);
  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        top: 110,
        transform: `translateX(-50%) scale(${interpolate(enter, [0, 1], [0.8, 1])})`,
        opacity: Math.min(enter, exit),
        background: "rgba(13,15,18,0.94)",
        border: "1.5px solid rgba(255,255,255,0.14)",
        borderRadius: 20,
        padding: "22px 44px",
        textAlign: "center",
        boxShadow: "0 16px 70px rgba(0,0,0,0.7)",
      }}
    >
      <div style={{ fontFamily: GEIST, fontWeight: 600, fontSize: 26, color: "rgba(255,255,255,0.6)", marginBottom: 6 }}>
        checkout p95 latency
      </div>
      <div style={{ fontFamily: GEIST_MONO, fontWeight: 600, fontSize: 64, color, letterSpacing: "-0.02em" }}>
        {display} ms
      </div>
    </div>
  );
};

export const Chips: React.FC<{ chips: ChipCue[]; counter: { at: number; until: number } }> = ({
  chips,
  counter,
}) => {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {chips.map((c, i) => (
        <Chip key={i} {...c} />
      ))}
      <CounterChip counter={counter} />
    </AbsoluteFill>
  );
};
