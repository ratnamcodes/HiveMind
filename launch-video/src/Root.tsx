import React from "react";
import { Composition } from "remotion";
import { LaunchVideo } from "./LaunchVideo";
import { Teaser } from "./Teaser";
import { CONFIGS, FPS, HEIGHT, Pace, Voice, WIDTH } from "./timeline";
import { TEASER_DURATION_FRAMES } from "./teaser-timeline";

// Two final cuts, both Jessica + Tycho "Awake" (organic):
//  - Hackathon: full cut with the Ratnam / Dynatrace-track / devpost intro.
//  - Twitter: clean product launch, cold-opens on the incident (no hackathon framing).
const VERSIONS: { id: string; pace: Pace; voice: Voice; music: string }[] = [
  { id: "Hackathon", pace: "snappy", voice: "jessica", music: "v4.mp3" },
  { id: "Twitter", pace: "twitter", voice: "jessica", music: "v4.mp3" },
  // V2: re-cut to Justice "Genesis" — brand-first open, drop on the title sting,
  // silence-before-approval, climax slam on the recovery counter.
  { id: "TwitterV2", pace: "launch", voice: "jessica", music: "genesis-launch.mp3" },
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {VERSIONS.map((v) => (
        <Composition
          key={v.id}
          id={v.id}
          component={LaunchVideo}
          durationInFrames={Math.round(CONFIGS[v.pace].durSec * FPS)}
          fps={FPS}
          width={WIDTH}
          height={HEIGHT}
          defaultProps={{ voice: v.voice, pace: v.pace, music: v.music }}
        />
      ))}
      <Composition
        id="Teaser"
        component={Teaser}
        durationInFrames={TEASER_DURATION_FRAMES}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};
