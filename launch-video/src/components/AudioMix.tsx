import React from "react";
import { Audio, Sequence, interpolate, staticFile } from "remotion";
import { VO_INTERVALS } from "../captions-data";
import { CONFIGS, FPS, MUSIC, Pace, Voice } from "../timeline";

// Music dynamics: duck under VO with fast returns (the bed "breathes" in every gap),
// plus per-config hard windows (silence-before-impact, quiet creeps).
const musicFactor = (
  sec: number,
  intervals: { from: number; to: number }[],
  duckLevel: number,
  windows: { from: number; to: number; level: number }[]
): number => {
  let factor = 1;
  for (const { from, to } of intervals) {
    const f = interpolate(sec, [from - 0.25, from, to, to + 0.35], [1, duckLevel, duckLevel, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    factor = Math.min(factor, f);
  }
  for (const { from, to, level } of windows) {
    const f = interpolate(sec, [from - 0.2, from, to, to + 0.3], [1, level, level, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    factor = Math.min(factor, f);
  }
  return factor;
};

export const AudioMix: React.FC<{ voice: Voice; pace: Pace; music: string; musicGain?: number }> = ({
  voice,
  pace,
  music,
  musicGain = 1,
}) => {
  const cfg = CONFIGS[pace];
  const intervals = VO_INTERVALS[pace][voice];
  const durFrames = Math.round(cfg.durSec * FPS);
  const base = (cfg.musicBase ?? MUSIC.base) * musicGain;
  const duckLevel = cfg.duckLevel ?? 0.55;
  const windows = cfg.musicWindows ?? [];

  return (
    <>
      {/* Voiceover */}
      {cfg.voCues.map(({ id, at }) => (
        <Sequence key={id} from={Math.round(at * FPS)}>
          <Audio src={staticFile(`audio/vo/${voice}/${id}.mp3`)} volume={1} />
        </Sequence>
      ))}

      {/* Music bed */}
      <Sequence from={0} durationInFrames={durFrames}>
        <Audio
          src={staticFile(`audio/beds/${music}`)}
          volume={(f) => {
            const sec = f / FPS;
            const fadeIn = interpolate(f, [0, MUSIC.fadeIn * FPS], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const fadeOut = interpolate(f, [durFrames - MUSIC.fadeOut * FPS, durFrames - 1], [1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return Math.max(0, Math.min(1, base * fadeIn * fadeOut * musicFactor(sec, intervals, duckLevel, windows)));
          }}
        />
      </Sequence>

      {/* SFX */}
      {cfg.sfx.map(({ file, at, vol }, i) => (
        <Sequence key={`${file}-${i}`} from={Math.round(at * FPS)}>
          <Audio src={staticFile(`audio/sfx/${file}.mp3`)} volume={vol} />
        </Sequence>
      ))}
    </>
  );
};
