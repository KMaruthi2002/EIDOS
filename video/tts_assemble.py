# Join the per-sentence takes into one file per scene with natural pauses, master lightly, and
# write the exact sentence start times (measured, not estimated) for the video to sync against.
import json, os, re, subprocess, sys, math
SRC = sys.argv[1]; V = os.environ.get("VIDEO_DIR", "."); VO = sys.argv[2] if len(sys.argv) > 2 else "vo8"
out = f"{V}/public/{VO}"; os.makedirs(out, exist_ok=True)
dur = lambda f: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).decode().strip())
spec = json.load(open(f"narr8.json"))
timeline, sent = [], {}
for s in spec["scenes"]:
    meta = json.load(open(f"{SRC}/{s['id']}.json")); parts, sents = meta["parts"], meta["sents"]
    starts, acc, inputs, fl = [], 0.0, [], ""
    for i, (p, text) in enumerate(zip(parts, sents)):
        d = dur(p)
        # trim silence at both ends of each take, then pad with the pause that fits the sentence
        gap = 0.0 if i == len(parts) - 1 else (0.55 if text.strip().endswith("?") else 0.42 if len(text.split()) <= 3 else 0.32)
        inputs += ["-i", p]
        fl += f"[{i}:a]silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse,apad=pad_dur={gap + 0.12}[a{i}];"
        starts.append(round(acc, 3))
        acc += d  # provisional; replaced below by measuring the joined file
    fl += "".join(f"[a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1,highpass=f=75,lowpass=f=9500,acompressor=threshold=-19dB:ratio=2.2:attack=10:release=140:makeup=2,equalizer=f=220:t=q:w=1.2:g=1.5,equalizer=f=3200:t=q:w=1.2:g=1,alimiter=limit=0.93[a]"
    f_out = f"{out}/{s['id']}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fl, "-map", "[a]", "-ar", "44100", f_out], check=True)
    # measure real sentence starts: trim each take the same way and sum
    acc, starts = 0.0, []
    for i, (p, text) in enumerate(zip(parts, sents)):
        tmp = f"{SRC}/_trim.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", p, "-af", "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse", tmp], check=True)
        starts.append(round(acc, 3))
        gap = 0.0 if i == len(parts) - 1 else (0.55 if text.strip().endswith("?") else 0.42 if len(text.split()) <= 3 else 0.32)
        acc += dur(tmp) + gap + 0.12
    total = dur(f_out)
    timeline.append({"id": s["id"], "text": s["text"], "seconds": round(total, 3)}); sent[s["id"]] = starts
    print(s["id"], round(total, 2), starts)
json.dump(timeline, open(f"{V}/src/timeline8.json", "w"), indent=2); json.dump(sent, open(f"{V}/src/v8_sent.json", "w"))
# scene timing snapped to the beat, then the scene starts for the score and the sound cues
tl = {x["id"]: x["seconds"] for x in timeline}; lead = 0.6
pads = {"hook": 1.2, "name": 1.6, "learn": 1.2, "live": 1.0, "alert": 1.2, "robot": 1.4, "meta": 1.2, "close": 2.6}
ids = list(pads); durs = [math.ceil((tl[i] + lead + pads[i]) / 0.5) * 0.5 for i in ids]; tr = 0.4
st = [round(sum(durs[:i]) - tr * i, 3) for i in range(len(durs))]; total = sum(durs) - tr * (len(durs) - 1)
json.dump({"ids": ids, "durations": durs, "tr": tr, "lead": lead, "vo": VO}, open(f"{V}/src/v8_timing.json", "w"))
json.dump({"total": total, "starts": st, "drop": st[1], "bpm": 120}, open(f"{V}/music_v8_scenes.json", "w"))
print("total", total, "starts", st)
