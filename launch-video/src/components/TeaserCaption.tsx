import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GEIST } from "../fonts";
import { BRAND } from "../timeline";
import { T_CAPTIONS } from "../teaser-timeline";

// Punchy full-phrase statement captions (no VO — these carry the story on mute).
// The keyword in each line is highlighted amber.
const HIGHLIGHT: Record<string, string> = {
  "3AM. Checkout is down.": "down",
  "1,204ms latency — SLO blown.": "blown",
  "Six AI agents take the case.": "Six AI agents",
  "Root cause, in your live data.": "Root cause",
  "$18,397 a month at risk.": "$18,397",
  "The fix — a real merge request.": "merge request",
  "You approve. One click.": "One click",
  "Then it proves it worked.": "proves",
};

const renderWithHighlight = (text: string) => {
  const key = HIGHLIGHT[text];
  if (!key || !text.includes(key)) return <span>{text}</span>;
  const [before, after] = text.split(key);
  return (
    <>
      <span>{before}</span>
      <span style={{ color: BRAND.amber400 }}>{key}</span>
      <span>{after}</span>
    </>
  );
};

export const TeaserCaption: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tSec = frame / fps;
  const cap = T_CAPTIONS.find((c) => tSec >= c.from && tSec <= c.to);
  if (!cap) return null;

  const fromFrame = Math.round(cap.from * fps);
  const toFrame = Math.round(cap.to * fps);
  const enter = spring({ frame: frame - fromFrame, fps, config: { damping: 18, stiffness: 200, mass: 0.7 } });
  const exit = interpolate(frame, [toFrame - 5, toFrame], [1, 0], { extrapolateLeft: "clamp" });

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 858,
          display: "flex",
          justifyContent: "center",
          opacity: Math.min(enter, exit),
          transform: `translateY(${interpolate(enter, [0, 1], [26, 0])}px) scale(${interpolate(enter, [0, 1], [0.94, 1])})`,
        }}
      >
        <div
          style={{
            fontFamily: GEIST,
            fontWeight: 800,
            fontSize: 66,
            letterSpacing: "-0.02em",
            color: "white",
            textAlign: "center",
            textShadow: "0 4px 14px rgba(0,0,0,0.95), 0 10px 50px rgba(0,0,0,0.85)",
            padding: "0 80px",
          }}
        >
          {renderWithHighlight(cap.text)}
        </div>
      </div>
    </AbsoluteFill>
  );
};
