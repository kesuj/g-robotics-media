// ElevenLabs voiceover with word timings, one MP3 + one words JSON per beat.
//   node --env-file=<.env> vo.mjs <jobs.json>
//   jobs = [{ "text": "...", "mp3": "path.mp3", "words": "path.json" }]  (existing outputs are skipped)
// Voice "Eric" (same as the G. Robotics reels).
import { existsSync, readFileSync, writeFileSync } from "node:fs";

const VOICE_ID = process.env.EE_VOICE_ID || "cjVigY5qzO86Huf0OWal";
const MODELS = ["eleven_v3", "eleven_multilingual_v2"];
const apiKey = process.env.ELEVENLABS_API_KEY;
if (!apiKey) throw new Error("ELEVENLABS_API_KEY is not set");

async function speak(text) {
  let lastErr;
  for (const model_id of MODELS) {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}/with-timestamps`, {
      method: "POST",
      headers: { "xi-api-key": apiKey, "Content-Type": "application/json" },
      body: JSON.stringify({ text, model_id, voice_settings: { stability: 0.5, similarity_boost: 0.75, use_speaker_boost: true } }),
    });
    if (res.ok) return res.json();
    lastErr = `${model_id}: ${res.status} ${await res.text()}`;
  }
  throw new Error(lastErr);
}

// Characters → words with start/end seconds (spaces split words; punctuation stays on its word).
function toWords(al) {
  const words = [];
  let cur = null;
  al.characters.forEach((ch, i) => {
    if (/\s/.test(ch)) { cur = null; return; }
    if (!cur) { cur = { w: "", s: al.character_start_times_seconds[i], e: 0 }; words.push(cur); }
    cur.w += ch;
    cur.e = al.character_end_times_seconds[i];
  });
  return words;
}

const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
for (const job of jobs) {
  if (existsSync(job.mp3) && existsSync(job.words)) continue;
  const r = await speak(job.text);
  writeFileSync(job.mp3, Buffer.from(r.audio_base64, "base64"));
  writeFileSync(job.words, JSON.stringify(toWords(r.alignment || r.normalized_alignment)));
  console.log("vo", job.mp3);
}
