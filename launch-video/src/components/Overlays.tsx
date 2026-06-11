import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { GEIST, GEIST_MONO } from "../fonts";
import { BRAND } from "../timeline";

// Subtle global vignette
export const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      background: "radial-gradient(ellipse 75% 70% at 50% 50%, transparent 55%, rgba(0,0,0,0.34) 100%)",
    }}
  />
);

// Red emergency pulse for the cold open (first ~3s)
export const RedPulse: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pulse = (Math.sin(t * Math.PI * 2 * 1.1 - Math.PI / 2) + 1) / 2;
  const decay = interpolate(t, [0, 2.8, 3.4], [1, 1, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        background: `radial-gradient(ellipse 70% 45% at 50% 12%, rgba(239,68,68,${0.16 * pulse * decay}), transparent 70%)`,
      }}
    />
  );
};

// Amber flash on the big slams (frame-local: mount via Sequence at the hit)
export const Flash: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 1, 7], [0, 0.42, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ pointerEvents: "none", background: `rgba(251,191,36,${opacity})` }} />
  );
};

// Timelapse HUD: 18x badge, status line, progress sweep (mounted 64–69s)
export const TimelapseOverlay: React.FC<{ durInFrames: number }> = ({ durInFrames }) => {
  const frame = useCurrentFrame();
  const dots = ".".repeat((Math.floor(frame / 10) % 3) + 1);
  const progress = interpolate(frame, [0, durInFrames], [0, 100]);
  const enter = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: enter }}>
      <div
        style={{
          position: "absolute",
          top: 64,
          right: 80,
          display: "flex",
          alignItems: "center",
          gap: 18,
          background: "rgba(13,15,18,0.92)",
          border: "1.5px solid rgba(255,255,255,0.15)",
          borderRadius: 999,
          padding: "14px 28px",
        }}
      >
        <span style={{ fontFamily: GEIST_MONO, fontWeight: 600, fontSize: 34, color: BRAND.amber400 }}>18×</span>
        <span style={{ fontFamily: GEIST, fontWeight: 600, fontSize: 28, color: "rgba(255,255,255,0.85)" }}>
          verifying recovery on live telemetry{dots}
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          height: 6,
          width: `${progress}%`,
          background: `linear-gradient(90deg, ${BRAND.amber500}, ${BRAND.amber300})`,
        }}
      />
    </AbsoluteFill>
  );
};
