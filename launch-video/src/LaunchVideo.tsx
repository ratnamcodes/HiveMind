import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { AudioMix } from "./components/AudioMix";
import { Captions } from "./components/Captions";
import { Chips } from "./components/Chips";
import { DemoShot } from "./components/DemoShot";
import { EndCard } from "./components/EndCard";
import { Generalization } from "./components/Generalization";
import { IntroCard } from "./components/IntroCard";
import { BrandChip, KineticTitles } from "./components/LaunchExtras";
import { Flash, RedPulse, TimelapseOverlay, Vignette } from "./components/Overlays";
import { TitleCard } from "./components/TitleCard";
import { BRAND, CONFIGS, FPS, Pace, Voice } from "./timeline";

const toF = (sec: number) => Math.round(sec * FPS);

export const LaunchVideo: React.FC<{ voice: Voice; pace: Pace; music: string; musicGain?: number }> = ({
  voice,
  pace,
  music,
  musicGain,
}) => {
  const cfg = CONFIGS[pace];
  return (
    <AbsoluteFill style={{ background: BRAND.stage }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 65% 55% at 50% 38%, rgba(249,115,22,0.07), transparent 70%)`,
        }}
      />

      {/* Demo shots */}
      {cfg.shots.map((shot, i) => {
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

      {/* Cards / scenes */}
      {cfg.showIntro && (
        <Sequence from={toF(cfg.introCard.from)} durationInFrames={toF(cfg.introCard.dur)}>
          <IntroCard />
        </Sequence>
      )}
      <Sequence from={toF(cfg.titleCard.from)} durationInFrames={toF(cfg.titleCard.dur)}>
        <TitleCard />
      </Sequence>
      <Sequence from={toF(cfg.generalScene.from)} durationInFrames={toF(cfg.generalScene.dur)}>
        <Generalization />
      </Sequence>
      <Sequence from={toF(cfg.endCard.from)} durationInFrames={toF(cfg.endCard.dur)}>
        <EndCard />
      </Sequence>

      {/* Overlays */}
      <Sequence from={toF(cfg.overlays.redPulse.from)} durationInFrames={toF(cfg.overlays.redPulse.dur)}>
        <RedPulse />
      </Sequence>
      <Sequence from={toF(cfg.overlays.timelapse.from)} durationInFrames={toF(cfg.overlays.timelapse.dur)}>
        <TimelapseOverlay durInFrames={toF(cfg.overlays.timelapse.dur)} />
      </Sequence>
      {cfg.overlays.flash.map((t, i) => (
        <Sequence key={i} from={toF(t)} durationInFrames={10}>
          <Flash />
        </Sequence>
      ))}
      <Vignette />

      {/* Foreground UI */}
      <Chips chips={cfg.chips} counter={cfg.counter} />
      {cfg.kineticTitles && <KineticTitles titles={cfg.kineticTitles} />}
      {cfg.brandChip && <BrandChip at={cfg.brandChip.at} until={cfg.brandChip.until} />}
      <Captions voice={voice} pace={pace} />

      <AudioMix voice={voice} pace={pace} music={music} musicGain={musicGain} />
    </AbsoluteFill>
  );
};
