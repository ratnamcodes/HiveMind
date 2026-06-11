import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";
import fs from "node:fs";
import path from "node:path";

const envFile = fs.readFileSync(new URL("../../.env", import.meta.url), "utf8");
const apiKey = envFile.match(/^ELEVENLABS_API_KEY=(.+)$/m)?.[1]?.trim();
if (!apiKey) throw new Error("ELEVENLABS_API_KEY not found in ../.env");

const client = new ElevenLabsClient({ apiKey });

// Voice variants. Run `node scripts/generate-vo.mjs <key> [key2 ...]`, or no arg for the
// default set. Natural/human settings: keep `style` LOW (high style = over-acted/AI-sounding).
const VOICES = {
  // excited but human, warm conversational female (primary). speed 1.05 = a touch
  // faster/snappier without rushing or sounding synthetic.
  jessica: {
    voiceId: "cgSgspJ2msm6clMCkdW9",
    modelId: "eleven_multilingual_v2",
    settings: { stability: 0.42, similarityBoost: 0.9, style: 0.14, useSpeakerBoost: true, speed: 1.05 },
  },
  // natural, warm, confident female (alternate)
  sarah: {
    voiceId: "EXAVITQu4vr4xnSDxMaL",
    modelId: "eleven_multilingual_v2",
    settings: { stability: 0.42, similarityBoost: 0.9, style: 0.12, useSpeakerBoost: true, speed: 1.05 },
  },
  // Ratnam's own cloned voice (primary). Cloned voices: high similarity, moderate
  // stability, zero style for the most natural/real read.
  ratnam: {
    voiceId: "DnOK75xIqPzE2dgsm1RR",
    modelId: "eleven_multilingual_v2",
    settings: { stability: 0.5, similarityBoost: 0.9, style: 0.0, useSpeakerBoost: true, speed: 1.05 },
  },
  // Male narration voice
  male: {
    voiceId: "cnEghz8I8E5yxLrLAvrp",
    modelId: "eleven_multilingual_v2",
    settings: { stability: 0.5, similarityBoost: 0.9, style: 0.0, useSpeakerBoost: true, speed: 1.05 },
  },
};

const BEATS = [
  { id: "00-intro", text: "Hey, I'm Ratnam. This is HiveMind — my build for the Google Cloud Rapid Agent Hackathon, Dynatrace track. Watch this." },
  { id: "00-launch", text: "Hey — this is HiveMind." },
  { id: "01-hook", text: "It's 3 a.m., and a real store's checkout just died. Money's leaking. Customers are gone." },
  { id: "02-problem", text: "Normally? A human wakes up to stare at dashboards and guess. We can do way better." },
  { id: "03-reveal", text: "So I gave the whole incident to six AI agents." },
  { id: "03-reveal-launch", text: "So six AI agents took the call." },
  { id: "04-detective", text: "Before you'd even log in, Detective's already in Dynatrace, writing its own queries — and it nails it. A hidden, 1.2-second delay in the payment service." },
  { id: "05-swarm", text: "Then the swarm moves at once. Liaison does the math — seven customers, eighteen grand a month. And CodeArch writes the fix, and opens a real merge request." },
  { id: "06-gate", text: "Here's the part I love. A Reviewer tears it apart and pushes back. But nothing ships until you say go." },
  { id: "07-proof", text: "Then it proves it worked. 1.2 seconds, down to three milliseconds — confirmed on live telemetry." },
  { id: "07a-proof-a", text: "Then... it proves it worked." },
  { id: "07b-proof-b", text: "1.2 seconds, down to three milliseconds — confirmed on live telemetry." },
  { id: "08-general", text: "And checkout was just the demo. The same agents protect a bank's payments, a hospital's records, a game's launch night. Any system. Any incident. Anywhere." },
  { id: "09-cta", text: "This is HiveMind. Incidents, fixed end to end." },
];

const get = (obj, camel, snake) => obj?.[camel] ?? obj?.[snake];

const alignmentToWords = (alignment) => {
  const chars = get(alignment, "characters", "characters");
  const starts = get(alignment, "characterStartTimesSeconds", "character_start_times_seconds");
  const ends = get(alignment, "characterEndTimesSeconds", "character_end_times_seconds");
  const words = [];
  let cur = null;
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i];
    if (/\s/.test(ch)) {
      if (cur) { words.push(cur); cur = null; }
      continue;
    }
    if (!cur) cur = { text: ch, startMs: Math.round(starts[i] * 1000), endMs: Math.round(ends[i] * 1000) };
    else { cur.text += ch; cur.endMs = Math.round(ends[i] * 1000); }
  }
  if (cur) words.push(cur);
  return words;
};

async function generateVoice(key) {
  const voice = VOICES[key];
  const outDir = new URL(`../public/audio/vo/${key}/`, import.meta.url).pathname;
  fs.mkdirSync(outDir, { recursive: true });
  for (let i = 0; i < BEATS.length; i++) {
    const beat = BEATS[i];
    const mp3Path = path.join(outDir, `${beat.id}.mp3`);
    const wordsPath = path.join(outDir, `${beat.id}.words.json`);
    if (fs.existsSync(mp3Path) && fs.existsSync(wordsPath)) {
      console.log(`[${key}] skip ${beat.id} (exists)`);
      continue;
    }
    const res = await client.textToSpeech.convertWithTimestamps(voice.voiceId, {
      text: beat.text,
      modelId: voice.modelId,
      outputFormat: "mp3_44100_128",
      previousText: i > 0 ? BEATS[i - 1].text : undefined,
      nextText: i < BEATS.length - 1 ? BEATS[i + 1].text : undefined,
      voiceSettings: voice.settings,
    });
    const audioB64 = get(res, "audioBase64", "audio_base64");
    const alignment = get(res, "alignment", "alignment");
    fs.writeFileSync(mp3Path, Buffer.from(audioB64, "base64"));
    const words = alignmentToWords(alignment);
    const durationMs = words.length ? words[words.length - 1].endMs : 0;
    fs.writeFileSync(wordsPath, JSON.stringify({ id: beat.id, text: beat.text, durationMs, words }, null, 2));
    console.log(`[${key}] ${beat.id}: ${(durationMs / 1000).toFixed(2)}s, ${words.length} words`);
  }
}

const targets = process.argv.length > 2 ? process.argv.slice(2) : ["ratnam", "male"];
for (const key of targets) {
  if (!VOICES[key]) throw new Error(`unknown voice '${key}'`);
  await generateVoice(key);
}
console.log("done");
