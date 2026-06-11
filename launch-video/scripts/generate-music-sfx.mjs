import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";
import fs from "node:fs";
import path from "node:path";

const envFile = fs.readFileSync(new URL("../../.env", import.meta.url), "utf8");
const apiKey = envFile.match(/^ELEVENLABS_API_KEY=(.+)$/m)?.[1]?.trim();
const client = new ElevenLabsClient({ apiKey });

const audioDir = new URL("../public/audio/", import.meta.url).pathname;
fs.mkdirSync(path.join(audioDir, "sfx"), { recursive: true });

async function streamToBuffer(stream) {
  const chunks = [];
  for await (const c of stream) chunks.push(c);
  return Buffer.concat(chunks);
}

// ---------- Music bed (95s, structured to the storyboard) ----------
const musicPath = path.join(audioDir, "music.mp3");
if (!fs.existsSync(musicPath)) {
  const prompt =
    "Instrumental cinematic electronic trailer score for a tech product launch, 95 seconds, modern and confident. " +
    "Structure: 0-13s dark pulsing synth bass with urgent ticking percussion, tension building; " +
    "13-15s a short riser that cuts to near-silence; " +
    "15-53s a confident driving electronic groove with momentum, four on the floor, dark synths; " +
    "53-69s stripped-back suspenseful breakdown, sparse pulses, rising tension; " +
    "69-95s euphoric uplifting resolution with warm chords and a clean final ending, no fade-out. " +
    "No vocals, no melody hooks that fight a voiceover. Modern devtool launch trailer energy.";
  try {
    const stream = await client.music.compose({
      prompt,
      musicLengthMs: 95000,
      forceInstrumental: true,
    });
    fs.writeFileSync(musicPath, await streamToBuffer(stream));
    console.log("music.mp3 written (music API)");
  } catch (e) {
    console.error("music.compose failed:", e?.statusCode ?? "", String(e).slice(0, 300));
    // Fallback: loopable bed via sound-generation v2
    const loop = await client.textToSoundEffects.convert({
      text: "dark driving electronic music loop, pulsing synth bass, confident tech trailer energy, seamless loop, instrumental",
      durationSeconds: 22,
      promptInfluence: 0.4,
      loop: true,
    });
    fs.writeFileSync(path.join(audioDir, "music-loop.mp3"), await streamToBuffer(loop));
    console.log("music-loop.mp3 written (SFX fallback)");
  }
} else console.log("skip music (exists)");

// ---------- SFX ----------
const SFX = [
  { id: "whoosh", text: "quick airy whoosh transition, clean and short", duration: 0.8, influence: 0.6 },
  { id: "braam", text: "deep cinematic braam impact hit, modern trailer, punchy and short", duration: 1.8, influence: 0.6 },
  { id: "riser", text: "tense cinematic riser building up for two seconds then cutting off abruptly", duration: 2.0, influence: 0.6 },
  { id: "ding", text: "soft satisfying UI approval chime, single clean pleasant note", duration: 1.0, influence: 0.7 },
  { id: "alarm", text: "subtle urgent digital alert pulse, two muffled beeps, serious", duration: 1.5, influence: 0.6 },
];
for (const s of SFX) {
  const p = path.join(audioDir, "sfx", `${s.id}.mp3`);
  if (fs.existsSync(p)) { console.log(`skip ${s.id}`); continue; }
  const stream = await client.textToSoundEffects.convert({
    text: s.text,
    durationSeconds: s.duration,
    promptInfluence: s.influence,
  });
  fs.writeFileSync(p, await streamToBuffer(stream));
  console.log(`sfx/${s.id}.mp3 written`);
}
console.log("done");
