// ~31s no-VO teaser for X / social. Works on mute: punchy statement captions carry
// the story, music + SFX drive it, ends on the receipt and the URL.
import { Cam, FPS } from "./timeline";

export const TEASER_DURATION_SEC = 31;
export const TEASER_DURATION_FRAMES = TEASER_DURATION_SEC * FPS;

export type TShot = {
  from: number;
  dur: number;
  srcStart: number;
  rate?: number;
  camFrom: Cam;
  camTo: Cam;
};

export const T_SHOTS: TShot[] = [
  // hook — SEV1 alert hits (first frame = the thumbnail)
  { from: 0.0, dur: 2.6, srcStart: 5.2, camFrom: { z: 1.55, cx: 600, cy: 200 }, camTo: { z: 1.8, cx: 560, cy: 170 } },
  // the stakes — latency / SLO
  { from: 2.6, dur: 2.6, srcStart: 12.9, camFrom: { z: 2.5, cx: 560, cy: 205 }, camTo: { z: 2.62, cx: 565, cy: 205 } },
  // detective root cause
  { from: 5.2, dur: 2.4, srcStart: 25.8, camFrom: { z: 2.05, cx: 695, cy: 395 }, camTo: { z: 2.2, cx: 700, cy: 400 } },
  // pill closeup (verify_dql) — "real data"
  { from: 7.6, dur: 2.0, srcStart: 38.3, camFrom: { z: 3.0, cx: 525, cy: 345 }, camTo: { z: 3.08, cx: 525, cy: 345 } },
  // money on the line — green impact row
  { from: 9.6, dur: 2.8, srcStart: 129.8, camFrom: { z: 2.55, cx: 575, cy: 205 }, camTo: { z: 2.68, cx: 580, cy: 205 } },
  // the fix — real MR
  { from: 12.4, dur: 3.6, srcStart: 163.0, camFrom: { z: 1.85, cx: 720, cy: 420 }, camTo: { z: 2.2, cx: 690, cy: 440 } },
  // approval
  { from: 16.0, dur: 3.0, srcStart: 193.5, camFrom: { z: 1.9, cx: 710, cy: 592 }, camTo: { z: 1.98, cx: 715, cy: 600 } },
  // timelapse (speed-ramp the wait)
  { from: 19.0, dur: 2.3, srcStart: 195.0, rate: 18, camFrom: { z: 0.9, cx: 720, cy: 460 }, camTo: { z: 1.05, cx: 730, cy: 520 } },
  // RECEIPT — recovery verified + counter
  { from: 21.3, dur: 5.5, srcStart: 291.7, camFrom: { z: 1.5, cx: 758, cy: 690 }, camTo: { z: 1.85, cx: 728, cy: 715 } },
];

export const T_ENDCARD = { from: 26.8, dur: 4.2 };

export type TCaption = { from: number; to: number; text: string };
export const T_CAPTIONS: TCaption[] = [
  { from: 0.25, to: 2.55, text: "3AM. Checkout is down." },
  { from: 2.7, to: 5.15, text: "1,204ms latency — SLO blown." },
  { from: 5.3, to: 7.55, text: "Six AI agents take the case." },
  { from: 7.7, to: 9.55, text: "Root cause, in your live data." },
  { from: 9.7, to: 12.35, text: "$18,397 a month at risk." },
  { from: 12.5, to: 15.95, text: "The fix — a real merge request." },
  { from: 16.1, to: 18.95, text: "You approve. One click." },
  { from: 19.1, to: 21.25, text: "Then it proves it worked." },
];

// Counter chip on the receipt (1,204 ms -> 2.9 ms)
export const T_COUNTER = { at: 21.7, until: 26.7 };

export const T_SFX: { file: string; at: number; vol: number }[] = [
  { file: "alarm", at: 0.2, vol: 0.45 },
  { file: "braam", at: 0.4, vol: 0.4 },
  { file: "whoosh", at: 2.6, vol: 0.3 },
  { file: "whoosh", at: 5.2, vol: 0.3 },
  { file: "whoosh", at: 7.6, vol: 0.26 },
  { file: "whoosh", at: 9.6, vol: 0.3 },
  { file: "whoosh", at: 12.4, vol: 0.3 },
  { file: "ding", at: 16.1, vol: 0.6 },
  { file: "whoosh", at: 19.0, vol: 0.3 },
  { file: "braam", at: 21.4, vol: 0.5 },
  { file: "whoosh", at: 26.8, vol: 0.34 },
];

// Music: driving Complex window; brief stopdown before the receipt slam.
export const T_BED = { file: "music-teaser.mp3", base: 0.72, fadeOut: 2.8 };
export const T_STOPDOWN = { from: 20.2, to: 21.35, level: 0.08 };
