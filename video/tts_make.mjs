// Generate one voiceover file per scene and a timeline with their durations.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { KokoroTTS } from "kokoro-js";

const project = process.argv[2];
const only = process.argv[3]; // optional scene id to regenerate
const spec = JSON.parse(fs.readFileSync(path.join(project, process.env.SPEC || "narration.json"), "utf8"));
const outDir = path.join(project, "public", process.env.VO || "vo");
fs.mkdirSync(outDir, { recursive: true });
const tts = await KokoroTTS.from_pretrained("onnx-community/Kokoro-82M-v1.0-ONNX", { dtype: "q8", device: "cpu" });

const wavSeconds = (file) => {
  const b = fs.readFileSync(file);
  const rate = b.readUInt32LE(24), bytesPerSec = b.readUInt32LE(28);
  let off = 12;
  while (off < b.length) {
    const id = b.toString("ascii", off, off + 4), size = b.readUInt32LE(off + 4);
    if (id === "data") return size / bytesPerSec;
    off += 8 + size;
  }
  return 0;
};

const timeline = [];
for (const s of spec.scenes) {
  const file = path.join(outDir, `${s.id}.wav`);
  if (!only || only === s.id || !fs.existsSync(file)) {
    // Kokoro drops whatever is past its token limit, so long scenes are spoken in sentence groups and joined.
    const parts = [];
    for (const sent of s.text.match(/[^.!?]+[.!?]+["')]?\s*/g) || [s.text]) {
      if (parts.length && (parts.at(-1) + sent).length < 260) parts[parts.length - 1] += sent; else parts.push(sent);
    }
    if (parts.length === 1) {
      const audio = await tts.generate(s.text, { voice: spec.voice, speed: 1.0 });
      await audio.save(file);
    } else {
      const tmp = parts.map((_, i) => `${file}.part${i}.wav`);
      for (const [i, t] of parts.entries()) await (await tts.generate(t.trim(), { voice: spec.voice, speed: 1.0 })).save(tmp[i]);
      const inputs = tmp.flatMap((f) => ["-i", f]);
      const filter = tmp.map((_, i) => `[${i}:a]`).join("") + `concat=n=${tmp.length}:v=0:a=1[a]`;
      execFileSync("ffmpeg", ["-y", "-loglevel", "error", ...inputs, "-filter_complex", filter, "-map", "[a]", file]);
      tmp.forEach((f) => fs.unlinkSync(f));
    }
  }
  timeline.push({ id: s.id, text: s.text, seconds: +wavSeconds(file).toFixed(3) });
  console.log(s.id, timeline.at(-1).seconds);
}
fs.writeFileSync(path.join(project, "src", process.env.TL || "timeline.json"), JSON.stringify(timeline, null, 2));
