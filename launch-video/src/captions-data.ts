import { Caption, createTikTokStyleCaptions, TikTokPage } from "@remotion/captions";
import { CONFIGS, Pace, Voice } from "./timeline";

import jIntro from "../public/audio/vo/jessica/00-intro.words.json";
import jHook from "../public/audio/vo/jessica/01-hook.words.json";
import jProblem from "../public/audio/vo/jessica/02-problem.words.json";
import jReveal from "../public/audio/vo/jessica/03-reveal.words.json";
import jDetective from "../public/audio/vo/jessica/04-detective.words.json";
import jSwarm from "../public/audio/vo/jessica/05-swarm.words.json";
import jGate from "../public/audio/vo/jessica/06-gate.words.json";
import jProof from "../public/audio/vo/jessica/07-proof.words.json";
import jGeneral from "../public/audio/vo/jessica/08-general.words.json";
import jCta from "../public/audio/vo/jessica/09-cta.words.json";
import jLaunch from "../public/audio/vo/jessica/00-launch.words.json";
import jRevealLaunch from "../public/audio/vo/jessica/03-reveal-launch.words.json";
import jProofA from "../public/audio/vo/jessica/07a-proof-a.words.json";
import jProofB from "../public/audio/vo/jessica/07b-proof-b.words.json";
import sIntro from "../public/audio/vo/sarah/00-intro.words.json";
import sHook from "../public/audio/vo/sarah/01-hook.words.json";
import sProblem from "../public/audio/vo/sarah/02-problem.words.json";
import sReveal from "../public/audio/vo/sarah/03-reveal.words.json";
import sDetective from "../public/audio/vo/sarah/04-detective.words.json";
import sSwarm from "../public/audio/vo/sarah/05-swarm.words.json";
import sGate from "../public/audio/vo/sarah/06-gate.words.json";
import sProof from "../public/audio/vo/sarah/07-proof.words.json";
import sGeneral from "../public/audio/vo/sarah/08-general.words.json";
import sCta from "../public/audio/vo/sarah/09-cta.words.json";
// Ratnam (cloned) + male
import rIntro from "../public/audio/vo/ratnam/00-intro.words.json";
import rHook from "../public/audio/vo/ratnam/01-hook.words.json";
import rProblem from "../public/audio/vo/ratnam/02-problem.words.json";
import rReveal from "../public/audio/vo/ratnam/03-reveal.words.json";
import rDetective from "../public/audio/vo/ratnam/04-detective.words.json";
import rSwarm from "../public/audio/vo/ratnam/05-swarm.words.json";
import rGate from "../public/audio/vo/ratnam/06-gate.words.json";
import rProof from "../public/audio/vo/ratnam/07-proof.words.json";
import rGeneral from "../public/audio/vo/ratnam/08-general.words.json";
import rCta from "../public/audio/vo/ratnam/09-cta.words.json";
import mIntro from "../public/audio/vo/male/00-intro.words.json";
import mHook from "../public/audio/vo/male/01-hook.words.json";
import mProblem from "../public/audio/vo/male/02-problem.words.json";
import mReveal from "../public/audio/vo/male/03-reveal.words.json";
import mDetective from "../public/audio/vo/male/04-detective.words.json";
import mSwarm from "../public/audio/vo/male/05-swarm.words.json";
import mGate from "../public/audio/vo/male/06-gate.words.json";
import mProof from "../public/audio/vo/male/07-proof.words.json";
import mGeneral from "../public/audio/vo/male/08-general.words.json";
import mCta from "../public/audio/vo/male/09-cta.words.json";

type WordsFile = { id: string; durationMs: number; words: { text: string; startMs: number; endMs: number }[] };

const FILES_BY_VOICE: Record<Voice, Record<string, WordsFile>> = {
  jessica: Object.fromEntries(
    [jIntro, jHook, jProblem, jReveal, jDetective, jSwarm, jGate, jProof, jGeneral, jCta, jLaunch, jRevealLaunch, jProofA, jProofB].map((f) => [f.id, f as WordsFile])
  ),
  sarah: Object.fromEntries(
    [sIntro, sHook, sProblem, sReveal, sDetective, sSwarm, sGate, sProof, sGeneral, sCta].map((f) => [f.id, f as WordsFile])
  ),
  ratnam: Object.fromEntries(
    [rIntro, rHook, rProblem, rReveal, rDetective, rSwarm, rGate, rProof, rGeneral, rCta].map((f) => [f.id, f as WordsFile])
  ),
  male: Object.fromEntries(
    [mIntro, mHook, mProblem, mReveal, mDetective, mSwarm, mGate, mProof, mGeneral, mCta].map((f) => [f.id, f as WordsFile])
  ),
};

export type BeatCaptions = { id: string; startSec: number; durationMs: number; pages: TikTokPage[] };

const buildBeatCaptions = (voice: Voice, pace: Pace): BeatCaptions[] =>
  CONFIGS[pace].voCues.flatMap(({ id, at }) => {
    const file = FILES_BY_VOICE[voice][id];
    if (!file) return []; // this voice has no take for this beat (launch beats are jessica-only)
    const sentences: { text: string; startMs: number; endMs: number }[][] = [];
    let cur: { text: string; startMs: number; endMs: number }[] = [];
    for (const w of file.words) {
      cur.push(w);
      if (/[.?!]$/.test(w.text)) { sentences.push(cur); cur = []; }
    }
    if (cur.length) sentences.push(cur);
    const pages: TikTokPage[] = sentences.flatMap((words) => {
      const captions: Caption[] = words.map((w, i) => ({
        text: (i === 0 ? "" : " ") + w.text,
        startMs: w.startMs,
        endMs: w.endMs,
        timestampMs: (w.startMs + w.endMs) / 2,
        confidence: null,
      }));
      return createTikTokStyleCaptions({ captions, combineTokensWithinMilliseconds: 950 }).pages;
    });
    return { id, startSec: at, durationMs: file.durationMs, pages };
  });

const VOICES: Voice[] = ["jessica", "sarah", "ratnam", "male"];
const PACES: Pace[] = ["snappy", "breathing", "twitter", "launch"];

export const BEAT_CAPTIONS: Record<Pace, Record<Voice, BeatCaptions[]>> = Object.fromEntries(
  PACES.map((p) => [p, Object.fromEntries(VOICES.map((v) => [v, buildBeatCaptions(v, p)]))])
) as Record<Pace, Record<Voice, BeatCaptions[]>>;

export const VO_INTERVALS: Record<Pace, Record<Voice, { from: number; to: number }[]>> = Object.fromEntries(
  PACES.map((p) => [
    p,
    Object.fromEntries(
      VOICES.map((v) => [
        v,
        CONFIGS[p].voCues.flatMap(({ id, at }) => {
          const f = FILES_BY_VOICE[v][id];
          return f ? [{ from: at, to: at + f.durationMs / 1000 }] : [];
        }),
      ])
    ),
  ])
) as Record<Pace, Record<Voice, { from: number; to: number }[]>>;
