import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BEAT_CAPTIONS } from "../captions-data";
import { GEIST } from "../fonts";
import { BRAND, CAPTION_SUPPRESS, Pace, Voice } from "../timeline";

export const Captions: React.FC<{ voice: Voice; pace: Pace }> = ({ voice, pace }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tSec = frame / fps;

  const beat = BEAT_CAPTIONS[pace][voice].find(
    (b) => tSec >= b.startSec && tSec <= b.startSec + b.durationMs / 1000 + 0.25
  );
  if (!beat || CAPTION_SUPPRESS.has(beat.id)) return null;

  const localMs = (tSec - beat.startSec) * 1000;
  const page = beat.pages.find((p) => localMs >= p.startMs && localMs < p.startMs + p.durationMs + 120);
  if (!page) return null;

  const pageStartFrame = Math.round(((beat.startSec * 1000 + page.startMs) / 1000) * fps);
  const enter = spring({ frame: frame - pageStartFrame, fps, config: { damping: 200, stiffness: 220 } });

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 918,
          display: "flex",
          justifyContent: "center",
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [16, 0])}px)`,
        }}
      >
        <div
          style={{
            fontFamily: GEIST,
            fontWeight: 700,
            fontSize: 56,
            letterSpacing: "-0.015em",
            whiteSpace: "pre",
            textShadow: "0 3px 10px rgba(0,0,0,0.95), 0 8px 40px rgba(0,0,0,0.8)",
            display: "flex",
          }}
        >
          {page.tokens.map((tok, i) => {
            const active = localMs >= tok.fromMs && localMs < tok.toMs;
            const past = localMs >= tok.toMs;
            return (
              <span
                key={i}
                style={{
                  color: active ? BRAND.amber400 : "white",
                  opacity: active || past ? 1 : 0.55,
                  transform: active ? "scale(1.07)" : "scale(1)",
                  display: "inline-block",
                  whiteSpace: "pre",
                }}
              >
                {tok.text}
              </span>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
