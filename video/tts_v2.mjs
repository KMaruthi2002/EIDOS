// Natural narration: one Kokoro call per sentence, a real pause between sentences, then a light master.
import fs from "node:fs"; import path from "node:path"; import { execFileSync } from "node:child_process";
import { KokoroTTS } from "kokoro-js";
const project = process.argv[2];
const spec = JSON.parse(fs.readFileSync(path.join(project, process.env.SPEC), "utf8"));
const outDir = path.join(project, "public", process.env.VO); fs.mkdirSync(outDir, { recursive: true });
const tts = await KokoroTTS.from_pretrained("onnx-community/Kokoro-82M-v1.0-ONNX", { dtype: "q8", device: "cpu" });
const dur = (f) => +execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).toString().trim();
const timeline = [];
for (const s of spec.scenes) {
  const file = path.join(outDir, `${s.id}.wav`);
  const sents = s.text.match(/[^.!?]+[.!?]+["')]?\s*/g) || [s.text];
  const parts = [];
  for (const [i, sent] of sents.entries()) {
    const f = `${file}.p${i}.wav`;
    await (await tts.generate(sent.trim(), { voice: spec.voice, speed: spec.speed ?? 1 })).save(f);
    parts.push(f);
  }
  // join with pauses: a longer one after a question or a short punchy line
  const inputs = parts.flatMap((f) => ["-i", f]);
  let filter = "";
  parts.forEach((_, i) => { const gap = /[?]\s*$/.test(sents[i]) ? 0.55 : sents[i].trim().split(" ").length <= 3 ? 0.42 : 0.3; filter += `[${i}:a]apad=pad_dur=${i < parts.length - 1 ? gap : 0.15}[a${i}];`; });
  filter += parts.map((_, i) => `[a${i}]`).join("") + `concat=n=${parts.length}:v=0:a=1,highpass=f=70,lowpass=f=12000,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=3,equalizer=f=180:t=q:w=1.2:g=2,equalizer=f=2800:t=q:w=1:g=1.5,alimiter=limit=0.95[a]`;
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", ...inputs, "-filter_complex", filter, "-map", "[a]", "-ar", "44100", file]);
  parts.forEach((f) => fs.unlinkSync(f));
  timeline.push({ id: s.id, text: s.text, seconds: +dur(file).toFixed(3) });
  console.log(s.id, timeline.at(-1).seconds);
}
fs.writeFileSync(path.join(project, "src", process.env.TL), JSON.stringify(timeline, null, 2));
