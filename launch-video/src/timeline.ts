// Shared constants + two pace configs (snappy / breathing). A "version" = (pace, music bed).
export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

// Source video: 1440x900. Camera coordinates are in source pixel space.
export const SRC_W = 1440;
export const SRC_H = 900;
export const FULL_Z = 0.88;

export type Cam = { z: number; cx: number; cy: number };
export type Shot = { from: number; dur: number; srcStart: number; rate?: number; camFrom: Cam; camTo: Cam };
export type ChipCue = { at: number; until: number; text: string; x: number; y: number; mono?: boolean };
export type Voice = "jessica" | "sarah" | "ratnam" | "male";
export type Pace = "snappy" | "breathing" | "twitter" | "launch";

export type TimelineConfig = {
  durSec: number;
  showIntro: boolean;
  introCard: { from: number; dur: number };
  titleCard: { from: number; dur: number };
  generalScene: { from: number; dur: number };
  endCard: { from: number; dur: number };
  shots: Shot[];
  voCues: { id: string; at: number }[];
  sfx: { file: string; at: number; vol: number }[];
  chips: ChipCue[];
  counter: { at: number; until: number };
  overlays: {
    redPulse: { from: number; dur: number };
    timelapse: { from: number; dur: number };
    flash: number[];
  };
  // launch-pace extras
  musicBase?: number; // overrides MUSIC.base
  duckLevel?: number; // music multiplier under VO (default 0.55)
  musicWindows?: { from: number; to: number; level: number }[]; // hard rides (silence-before-impact etc.)
  kineticTitles?: { at: number; dur: number; text: string }[];
  brandChip?: { at: number; until: number };
};

// Beats whose words are carried by a dedicated card/scene — suppress VO captions there.
export const CAPTION_SUPPRESS = new Set(["00-intro", "03-reveal", "08-general", "09-cta"]);

// Music: beds are all loudness-normalized to ~-16 LUFS, so one base works; subtle by default.
export const MUSIC = { base: 0.09, fadeIn: 0.5, fadeOut: 3.5 };

// ============================== SNAPPY (~96s) ==============================
const SNAPPY: TimelineConfig = {
  durSec: 96,
  showIntro: true,
  introCard: { from: 0.0, dur: 8.9 },
  titleCard: { from: 22.7, dur: 3.9 },
  generalScene: { from: 73.5, dur: 12.3 },
  endCard: { from: 85.8, dur: 10.2 },
  shots: [
    { from: 8.9, dur: 2.4, srcStart: 5.2, camFrom: { z: 1.55, cx: 620, cy: 210 }, camTo: { z: 1.85, cx: 560, cy: 170 } },
    { from: 11.3, dur: 2.0, srcStart: 12.9, camFrom: { z: 2.5, cx: 560, cy: 205 }, camTo: { z: 2.64, cx: 565, cy: 205 } },
    { from: 13.3, dur: 2.6, srcStart: 16.4, camFrom: { z: 2.2, cx: 620, cy: 285 }, camTo: { z: 2.32, cx: 630, cy: 295 } },
    { from: 15.9, dur: 3.3, srcStart: 16.4, camFrom: { z: 1.55, cx: 620, cy: 250 }, camTo: { z: 1.66, cx: 615, cy: 245 } },
    { from: 19.2, dur: 3.5, srcStart: 12.9, camFrom: { z: 2.2, cx: 560, cy: 245 }, camTo: { z: 2.34, cx: 565, cy: 248 } },
    { from: 26.6, dur: 2.7, srcStart: 22.2, camFrom: { z: FULL_Z, cx: 720, cy: 450 }, camTo: { z: 1.5, cx: 700, cy: 360 } },
    { from: 29.3, dur: 2.7, srcStart: 25.8, camFrom: { z: 2.05, cx: 695, cy: 395 }, camTo: { z: 2.2, cx: 700, cy: 400 } },
    { from: 32.0, dur: 1.1, srcStart: 38.3, camFrom: { z: 3.0, cx: 525, cy: 345 }, camTo: { z: 3.07, cx: 525, cy: 345 } },
    { from: 33.1, dur: 1.1, srcStart: 42.0, camFrom: { z: 3.0, cx: 525, cy: 345 }, camTo: { z: 3.07, cx: 525, cy: 345 } },
    { from: 34.2, dur: 2.8, srcStart: 122.5, camFrom: { z: 1.95, cx: 720, cy: 448 }, camTo: { z: 2.12, cx: 722, cy: 452 } },
    { from: 37.0, dur: 2.5, srcStart: 122.5, camFrom: { z: 1.7, cx: 620, cy: 590 }, camTo: { z: 1.8, cx: 625, cy: 615 } },
    { from: 39.5, dur: 3.5, srcStart: 129.8, camFrom: { z: 2.6, cx: 575, cy: 205 }, camTo: { z: 2.74, cx: 580, cy: 205 } },
    { from: 43.0, dur: 2.8, srcStart: 125.8, camFrom: { z: 2.1, cx: 690, cy: 588 }, camTo: { z: 2.2, cx: 695, cy: 598 } },
    { from: 45.8, dur: 5.7, srcStart: 163.0, camFrom: { z: 1.9, cx: 720, cy: 420 }, camTo: { z: 2.15, cx: 690, cy: 440 } },
    { from: 51.5, dur: 3.5, srcStart: 193.5, camFrom: { z: 1.9, cx: 710, cy: 592 }, camTo: { z: 1.98, cx: 715, cy: 600 } },
    { from: 55.0, dur: 5.5, srcStart: 200.0, camFrom: { z: 2.05, cx: 640, cy: 752 }, camTo: { z: 1.95, cx: 740, cy: 762 } },
    { from: 60.5, dur: 4.0, srcStart: 195.0, rate: 22, camFrom: { z: FULL_Z, cx: 720, cy: 450 }, camTo: { z: 1.05, cx: 730, cy: 520 } },
    { from: 64.5, dur: 9.0, srcStart: 291.7, camFrom: { z: 1.45, cx: 760, cy: 690 }, camTo: { z: 1.84, cx: 725, cy: 715 } },
  ],
  voCues: [
    { id: "00-intro", at: 0.4 }, { id: "01-hook", at: 9.1 }, { id: "02-problem", at: 16.1 },
    { id: "03-reveal", at: 23.0 }, { id: "04-detective", at: 26.9 }, { id: "05-swarm", at: 37.2 },
    { id: "06-gate", at: 51.7 }, { id: "07-proof", at: 60.7 }, { id: "08-general", at: 74.0 }, { id: "09-cta", at: 86.3 },
  ],
  sfx: [
    { file: "whoosh", at: 8.8, vol: 0.3 }, { file: "alarm", at: 8.95, vol: 0.32 },
    { file: "riser", at: 21.5, vol: 0.4 }, { file: "braam", at: 22.7, vol: 0.38 },
    { file: "whoosh", at: 26.55, vol: 0.3 }, { file: "whoosh", at: 36.95, vol: 0.26 },
    { file: "whoosh", at: 45.75, vol: 0.26 }, { file: "ding", at: 55.6, vol: 0.55 },
    { file: "whoosh", at: 60.45, vol: 0.28 }, { file: "braam", at: 64.5, vol: 0.4 },
    { file: "whoosh", at: 73.45, vol: 0.3 }, { file: "riser", at: 83.0, vol: 0.3 }, { file: "whoosh", at: 85.75, vol: 0.32 },
  ],
  chips: [
    { at: 29.9, until: 31.9, text: "Davis problem P-26065", x: 130, y: 150, mono: true },
    { at: 40.1, until: 42.8, text: "7 customers · $18,397/mo at risk", x: 130, y: 760, mono: true },
    { at: 46.7, until: 51.0, text: "real GitLab MR — !50", x: 130, y: 150, mono: true },
    { at: 56.9, until: 60.2, text: "Human-approved ✓", x: 130, y: 820, mono: true },
    { at: 68.5, until: 73.2, text: "SRG check: PASS", x: 1500, y: 800, mono: true },
  ],
  counter: { at: 64.9, until: 73.2 },
  overlays: { redPulse: { from: 8.9, dur: 3.2 }, timelapse: { from: 60.5, dur: 4 }, flash: [22.7, 64.5] },
};

// ============================== BREATHING (~106s) ==============================
const BREATHING: TimelineConfig = {
  durSec: 106,
  showIntro: true,
  introCard: { from: 0.0, dur: 9.6 },
  titleCard: { from: 24.8, dur: 4.6 },
  generalScene: { from: 82.0, dur: 13.0 },
  endCard: { from: 95.0, dur: 11.0 },
  shots: [
    { from: 9.6, dur: 3.0, srcStart: 5.2, camFrom: { z: 1.52, cx: 620, cy: 210 }, camTo: { z: 1.82, cx: 560, cy: 170 } },
    { from: 12.6, dur: 2.4, srcStart: 12.9, camFrom: { z: 2.48, cx: 560, cy: 205 }, camTo: { z: 2.62, cx: 565, cy: 205 } },
    { from: 15.0, dur: 2.4, srcStart: 16.4, camFrom: { z: 2.18, cx: 620, cy: 285 }, camTo: { z: 2.3, cx: 630, cy: 295 } },
    { from: 17.4, dur: 3.6, srcStart: 16.4, camFrom: { z: 1.52, cx: 620, cy: 250 }, camTo: { z: 1.64, cx: 615, cy: 245 } },
    { from: 21.0, dur: 3.8, srcStart: 12.9, camFrom: { z: 2.18, cx: 560, cy: 245 }, camTo: { z: 2.32, cx: 565, cy: 248 } },
    { from: 29.4, dur: 3.2, srcStart: 22.2, camFrom: { z: FULL_Z, cx: 720, cy: 450 }, camTo: { z: 1.48, cx: 700, cy: 360 } },
    { from: 32.6, dur: 3.2, srcStart: 25.8, camFrom: { z: 2.02, cx: 695, cy: 395 }, camTo: { z: 2.18, cx: 700, cy: 400 } },
    { from: 35.8, dur: 1.2, srcStart: 38.3, camFrom: { z: 3.0, cx: 525, cy: 345 }, camTo: { z: 3.07, cx: 525, cy: 345 } },
    { from: 37.0, dur: 1.2, srcStart: 42.0, camFrom: { z: 3.0, cx: 525, cy: 345 }, camTo: { z: 3.07, cx: 525, cy: 345 } },
    { from: 38.2, dur: 3.2, srcStart: 122.5, camFrom: { z: 1.92, cx: 720, cy: 448 }, camTo: { z: 2.08, cx: 722, cy: 452 } },
    { from: 41.4, dur: 2.8, srcStart: 122.5, camFrom: { z: 1.68, cx: 620, cy: 590 }, camTo: { z: 1.78, cx: 625, cy: 615 } },
    { from: 44.2, dur: 4.0, srcStart: 129.8, camFrom: { z: 2.58, cx: 575, cy: 205 }, camTo: { z: 2.72, cx: 580, cy: 205 } },
    { from: 48.2, dur: 3.0, srcStart: 125.8, camFrom: { z: 2.08, cx: 690, cy: 588 }, camTo: { z: 2.18, cx: 695, cy: 598 } },
    { from: 51.2, dur: 6.8, srcStart: 163.0, camFrom: { z: 1.88, cx: 720, cy: 420 }, camTo: { z: 2.14, cx: 690, cy: 440 } },
    { from: 58.0, dur: 3.8, srcStart: 193.5, camFrom: { z: 1.88, cx: 710, cy: 592 }, camTo: { z: 1.96, cx: 715, cy: 600 } },
    { from: 61.8, dur: 5.8, srcStart: 200.0, camFrom: { z: 2.02, cx: 640, cy: 752 }, camTo: { z: 1.93, cx: 740, cy: 762 } },
    { from: 67.6, dur: 4.4, srcStart: 195.0, rate: 20, camFrom: { z: FULL_Z, cx: 720, cy: 450 }, camTo: { z: 1.05, cx: 730, cy: 520 } },
    { from: 72.0, dur: 10.0, srcStart: 291.7, camFrom: { z: 1.42, cx: 760, cy: 690 }, camTo: { z: 1.82, cx: 725, cy: 715 } },
  ],
  voCues: [
    { id: "00-intro", at: 0.6 }, { id: "01-hook", at: 10.0 }, { id: "02-problem", at: 17.8 },
    { id: "03-reveal", at: 25.3 }, { id: "04-detective", at: 29.8 }, { id: "05-swarm", at: 41.8 },
    { id: "06-gate", at: 58.4 }, { id: "07-proof", at: 67.9 }, { id: "08-general", at: 82.6 }, { id: "09-cta", at: 95.9 },
  ],
  sfx: [
    { file: "whoosh", at: 9.5, vol: 0.3 }, { file: "alarm", at: 9.65, vol: 0.32 },
    { file: "riser", at: 23.7, vol: 0.4 }, { file: "braam", at: 24.8, vol: 0.38 },
    { file: "whoosh", at: 29.35, vol: 0.3 }, { file: "whoosh", at: 41.35, vol: 0.26 },
    { file: "whoosh", at: 51.15, vol: 0.26 }, { file: "ding", at: 62.3, vol: 0.55 },
    { file: "whoosh", at: 67.55, vol: 0.28 }, { file: "braam", at: 72.0, vol: 0.4 },
    { file: "whoosh", at: 81.95, vol: 0.3 }, { file: "riser", at: 93.0, vol: 0.3 }, { file: "whoosh", at: 94.95, vol: 0.32 },
  ],
  chips: [
    { at: 33.2, until: 35.6, text: "Davis problem P-26065", x: 130, y: 150, mono: true },
    { at: 44.8, until: 48.0, text: "7 customers · $18,397/mo at risk", x: 130, y: 760, mono: true },
    { at: 52.2, until: 57.6, text: "real GitLab MR — !50", x: 130, y: 150, mono: true },
    { at: 63.6, until: 67.3, text: "Human-approved ✓", x: 130, y: 820, mono: true },
    { at: 76.5, until: 81.5, text: "SRG check: PASS", x: 1500, y: 800, mono: true },
  ],
  counter: { at: 72.3, until: 81.5 },
  overlays: { redPulse: { from: 9.6, dur: 3.2 }, timelapse: { from: 67.6, dur: 4.4 }, flash: [24.8, 72.0] },
};

// TWITTER product-launch cut = SNAPPY minus the hackathon intro: drop the intro card
// + its VO, cold-open straight into the incident, everything shifted earlier.
const shiftConfig = (cfg: TimelineConfig, delta: number, durSec: number): TimelineConfig => ({
  durSec,
  showIntro: false,
  introCard: { from: 0, dur: 0 },
  titleCard: { from: cfg.titleCard.from - delta, dur: cfg.titleCard.dur },
  generalScene: { from: cfg.generalScene.from - delta, dur: cfg.generalScene.dur },
  endCard: { from: cfg.endCard.from - delta, dur: cfg.endCard.dur },
  shots: cfg.shots.map((s) => ({ ...s, from: s.from - delta })),
  voCues: cfg.voCues.filter((c) => c.id !== "00-intro").map((c) => ({ ...c, at: c.at - delta })),
  sfx: cfg.sfx.map((s) => ({ ...s, at: s.at - delta })),
  chips: cfg.chips.map((c) => ({ ...c, at: c.at - delta, until: c.until - delta })),
  counter: { at: cfg.counter.at - delta, until: cfg.counter.until - delta },
  overlays: {
    redPulse: { from: cfg.overlays.redPulse.from - delta, dur: cfg.overlays.redPulse.dur },
    timelapse: { from: cfg.overlays.timelapse.from - delta, dur: cfg.overlays.timelapse.dur },
    flash: cfg.overlays.flash.map((t) => t - delta),
  },
});

const TWITTER = shiftConfig(SNAPPY, 8.7, 88);

// ============================== LAUNCH (~90s, V2) ==============================
// Re-cut to Justice "Genesis" (beds/genesis-launch.mp3): bed built so the DROP lands
// at t=13.6 (title sting) and the climax re-drop SLAMS at t=51.54 (recovery payoff).
// Brand-first audio open ("Hey — this is HiveMind" at 0.7s), shots quantized to the
// ~98BPM grid (1.224s units) from the drop anchor, silence-before-impact around the
// approval click, SFX culled to alarm + ding (the track's own braams do the rest).
const G = (k: number) => +(13.6 + 1.224 * k).toFixed(2); // beat grid from the drop
const LAUNCH: TimelineConfig = {
  durSec: 90,
  showIntro: false,
  introCard: { from: 0, dur: 0 },
  titleCard: { from: 13.6, dur: 2.45 },
  generalScene: { from: G(41), dur: 12.24 }, // 63.78
  endCard: { from: G(51), dur: 13.98 }, // 76.02
  shots: [
    // cold open under the brand voice (Genesis fanfare = the alarm)
    { from: 0.0, dur: 2.9, srcStart: 5.2, camFrom: { z: 1.55, cx: 620, cy: 210 }, camTo: { z: 1.85, cx: 560, cy: 170 } },
    { from: 2.9, dur: 2.5, srcStart: 12.9, camFrom: { z: 2.5, cx: 560, cy: 205 }, camTo: { z: 2.64, cx: 565, cy: 205 } },
    { from: 5.4, dur: 2.45, srcStart: 16.4, camFrom: { z: 2.2, cx: 620, cy: 285 }, camTo: { z: 2.32, cx: 630, cy: 295 } },
    { from: 7.85, dur: 2.45, srcStart: 16.4, camFrom: { z: 1.55, cx: 620, cy: 250 }, camTo: { z: 1.66, cx: 615, cy: 245 } },
    // "So six AI agents took the call" — Detective's first message pops on screen
    { from: 10.3, dur: 3.3, srcStart: 20.8, camFrom: { z: 1.5, cx: 700, cy: 370 }, camTo: { z: 1.62, cx: 700, cy: 365 } },
    // (STING 13.6–16.05 on the drop)
    { from: G(2), dur: 2.45, srcStart: 24.0, camFrom: { z: 1.45, cx: 700, cy: 380 }, camTo: { z: 1.55, cx: 700, cy: 375 } },
    { from: G(4), dur: 2.44, srcStart: 26.2, camFrom: { z: 2.1, cx: 700, cy: 398 }, camTo: { z: 2.2, cx: 702, cy: 400 } },
    { from: G(6), dur: 1.22, srcStart: 38.3, camFrom: { z: 3.0, cx: 525, cy: 345 }, camTo: { z: 3.07, cx: 525, cy: 345 } },
    { from: G(7), dur: 1.22, srcStart: 42.0, camFrom: { z: 3.0, cx: 525, cy: 345 }, camTo: { z: 3.07, cx: 525, cy: 345 } },
    { from: G(8), dur: 2.45, srcStart: 122.5, camFrom: { z: 2.0, cx: 720, cy: 450 }, camTo: { z: 2.1, cx: 722, cy: 452 } },
    { from: G(10), dur: 2.45, srcStart: 122.5, camFrom: { z: 1.72, cx: 620, cy: 595 }, camTo: { z: 1.8, cx: 625, cy: 612 } },
    { from: G(12), dur: 3.67, srcStart: 129.8, camFrom: { z: 2.65, cx: 575, cy: 205 }, camTo: { z: 2.75, cx: 580, cy: 205 } },
    { from: G(15), dur: 2.45, srcStart: 125.8, camFrom: { z: 2.14, cx: 690, cy: 592 }, camTo: { z: 2.2, cx: 694, cy: 598 } },
    { from: G(17), dur: 4.89, srcStart: 163.0, camFrom: { z: 1.88, cx: 720, cy: 420 }, camTo: { z: 2.16, cx: 690, cy: 440 } },
    { from: G(21), dur: 3.67, srcStart: 193.5, camFrom: { z: 1.92, cx: 710, cy: 594 }, camTo: { z: 1.98, cx: 714, cy: 600 } },
    { from: G(24), dur: 4.9, srcStart: 200.0, camFrom: { z: 2.05, cx: 640, cy: 752 }, camTo: { z: 1.95, cx: 740, cy: 762 } },
    { from: G(28), dur: 3.67, srcStart: 195.0, rate: 24, camFrom: { z: FULL_Z, cx: 720, cy: 450 }, camTo: { z: 1.05, cx: 730, cy: 520 } },
    { from: G(31), dur: 12.24, srcStart: 291.7, camFrom: { z: 1.45, cx: 760, cy: 690 }, camTo: { z: 1.84, cx: 725, cy: 715 } },
  ],
  voCues: [
    { id: "00-launch", at: 0.7 },
    { id: "01-hook", at: 3.3 },
    { id: "03-reveal-launch", at: 10.35 },
    { id: "04-detective", at: 16.3 },
    { id: "05-swarm", at: 26.7 },
    { id: "06-gate", at: 40.0 },
    { id: "07a-proof-a", at: 48.9 },
    { id: "07b-proof-b", at: 54.6 },
    { id: "08-general", at: 64.3 },
    { id: "09-cta", at: 77.0 },
  ],
  sfx: [
    { file: "alarm", at: 0.35, vol: 0.3 },
    { file: "ding", at: 47.6, vol: 0.6 },
  ],
  chips: [
    { at: 29.0, until: 31.8, text: "7 customers · $18,397/mo at risk", x: 130, y: 760, mono: true },
    { at: 44.5, until: 47.4, text: "Human-approved ✓", x: 130, y: 820, mono: true },
    { at: 56.5, until: 62.5, text: "SRG check: PASS", x: 1500, y: 800, mono: true },
  ],
  counter: { at: 52.0, until: 63.3 },
  overlays: {
    redPulse: { from: 0, dur: 3.4 },
    timelapse: { from: G(28), dur: 3.67 },
    flash: [13.6, G(31)],
  },
  musicBase: 0.85,
  duckLevel: 0.3,
  musicWindows: [
    { from: 46.9, to: 50.1, level: 0.03 }, // silence-before-impact around the approval click
    { from: 50.1, to: 51.45, level: 0.14 }, // quiet creep under the timelapse into the slam
  ],
  kineticTitles: [
    { at: 16.35, dur: 1.5, text: "READS LIVE TELEMETRY" },
    { at: 23.55, dur: 1.5, text: "FINDS THE ROOT CAUSE" },
    { at: 28.45, dur: 1.5, text: "NAMES THE BLAST RADIUS" },
    { at: 34.6, dur: 1.5, text: "OPENS A REAL MR" },
  ],
  brandChip: { at: 1.9, until: 12.9 },
};

export const CONFIGS: Record<Pace, TimelineConfig> = {
  snappy: SNAPPY,
  breathing: BREATHING,
  twitter: TWITTER,
  launch: LAUNCH,
};

export const BRAND = {
  amber300: "#FDBA74",
  amber400: "#FB923C",
  amber500: "#F97316",
  amber600: "#EA580C",
  stage: "#0b0d10",
  stageDeep: "#07090b",
  emerald: "#34D399",
  red: "#EF4444",
  dynatrace: "#1496FF",
};
