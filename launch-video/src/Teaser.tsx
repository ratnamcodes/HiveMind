import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  interpolateColors,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { DemoShot } from "./components/DemoShot";
import { EndCard } from "./components/EndCard";
import { Flash, RedPulse, TimelapseOverlay, Vignette } from "./components/Overlays";
import { TeaserCaption } from "./components/TeaserCaption";
import { GEIST, GEIST_MONO } from "./fonts";
import { BRAND, FPS } from "./timeline";
import { T_BED, T_COUNTER, T_ENDCARD, T_SFX, T_SHOTS, T_STOPDOWN } from "./teaser-timeline";

const toF = (sec: number) => Math.round(sec * FPS);

const ReceiptCounter: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = toF(T_COUNTER.at);
  const end = toF(T_COUNTER.until);
  if (frame < start || frame > end) return null;
  const local = frame - start;
  const enter = spring({ frame: local, fps, config: { damping: 15, stiffness: 170, mass: 0.8 } });
  const exit = interpolate(frame, [end - 6, end], [1, 0], { extrapolateLeft: "clamp" });
  const value = interpolate(local, [6, 52], [1204, 2.9], {
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
        top: 96,
        transform: `translateX(-50%) scale(${interpolate(enter, [0, 1], [0.8, 1])})`,
        opacity: Math.min(enter, exit),
        background: "rgba(13,15,18,0.95)",
        border: "1.5px solid rgba(255,255,255,0.14)",
        borderRadius: 22,
        padding: "24px 50px",
        textAlign: "center",
        boxShadow: "0 18px 80px rgba(0,0,0,0.7)",
      }}
    >
      <div style={{ fontFamily: GEIST, fontWeight: 600, fontSize: 28, color: "rgba(255,255,255,0.6)", marginBottom: 8 }}>
        checkout p95 latency
      </div>
      <div style={{ fontFamily: GEIST_MONO, fontWeight: 600, fontSize: 76, color, letterSpacing: "-0.02em" }}>
        {display} ms
      </div>
    </div>
  );
};

export const Teaser: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: BRAND.stage }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 65% 55% at 50% 38%, rgba(245,158,11,0.07), transparent 70%)`,
        }}
      />

      {T_SHOTS.map((shot, i) => {
        const durInFrames = toF(shot.dur);
        return (
          <Sequence key={i} from={toF(shot.from)} durationInFrames={durInFrames} premountFor={45}>
            <DemoShot
              srcStart={shot.srcStart}
              rate={shot.rate}
              durInFrames={durInFrames}
              camFrom={shot.camFrom}
              camTo={shot.camTo}
            />
          </Sequence>
        );
      })}

      <Sequence from={toF(T_ENDCARD.from)} durationInFrames={toF(T_ENDCARD.dur)}>
        <EndCard />
      </Sequence>

      {/* Overlays */}
      <Sequence from={0} durationInFrames={toF(2.6)}>
        <RedPulse />
      </Sequence>
      <Sequence from={toF(19.0)} durationInFrames={toF(2.3)}>
        <TimelapseOverlay durInFrames={toF(2.3)} />
      </Sequence>
      <Sequence from={toF(21.3)} durationInFrames={10}>
        <Flash />
      </Sequence>
      <Vignette />

      {/* Foreground */}
      <ReceiptCounter />
      <TeaserCaption />

      {/* Audio */}
      <Audio
        src={staticFile(`audio/${T_BED.file}`)}
        volume={(f) => {
          const sec = f / FPS;
          const stop = interpolate(
            sec,
            [T_STOPDOWN.from - 0.25, T_STOPDOWN.from, T_STOPDOWN.to, T_STOPDOWN.to + 0.4],
            [1, T_STOPDOWN.level, T_STOPDOWN.level, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
          return Math.max(0, T_BED.base * stop);
        }}
      />
      {T_SFX.map(({ file, at, vol }, i) => (
        <Sequence key={`${file}-${i}`} from={toF(at)}>
          <Audio src={staticFile(`audio/sfx/${file}.mp3`)} volume={vol} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
