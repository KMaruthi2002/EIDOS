"""Pull real benchmark numbers and clip lengths into the video project."""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent.parent   # the EIDOS repo
V = Path(__file__).parent
split = sys.argv[1] if len(sys.argv) > 1 else "test"
r = json.loads((E / "runs" / f"bench_{split}" / "results.json").read_text())["summary"]
dur = {}
for f in (V / "public" / "clips").glob("*.mp4"):
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout
    dur[f.stem] = float(d)
out = {"test": {"all": r["all"], "redesign": r["redesign"], "interruption": r.get("interruption"),
                "self": r["eidos_self_report"], "replay_silent": r["replay_silent_failures"]},
       "clips": dur, "split": split}
# Narration for the results scene, written from the numbers.
a, it, sr = r["all"], r.get("interruption"), r["eidos_self_report"]
words = {n: w for n, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
say = lambda n: words.get(n, str(n))
verdict = "every time" if sr["agrees_with_oracle"] == sr["n"] else f"in {say(sr['agrees_with_oracle'])} of {say(sr['n'])}"
text = (f"Across {say(a['eidos']['n'])} runs, with the redesigns and interruptions drawn from a held-out seed, copying the clicks finished the task "
        f"{say(a['replay']['success'])} time{'s' if a['replay']['success'] != 1 else ''}. Eye-doss finished {say(a['eidos']['success'])}, "
        f"and its own verdict matched the truth {verdict}.")
if it:
    text += (f" When a dialog interrupted the task, Eye-doss finished {say(it['eidos']['success'])} of {say(it['eidos']['n'])}. "
             f"With the checks off, {say(it['eidos_nochk']['success'])}.")
nar = json.loads((V / "narration.json").read_text())
for sc in nar["scenes"]:
    if sc["id"] == "results":
        sc["text"] = text
(V / "narration.json").write_text(json.dumps(nar, indent=2, ensure_ascii=False))
print(text)
(V / "src" / "results.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out["test"], indent=1))
