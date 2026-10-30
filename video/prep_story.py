"""Record the run clips for the explainer and write its data files.

    python video/prep_story.py record    # record split-screen clips (real runs)
    python video/prep_story.py data      # trace, program and results -> src/*.json
"""
import asyncio, json, random, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import os
VID = Path(os.environ.get("EIDOS_VIDEO_DIR", ROOT / "video"))   # the Remotion project
CLIPS, STILLS = VID / "public" / "clips", VID / "public" / "stills"
BASE = os.environ.get("EIDOS_STUDIO", "http://localhost:8000") + "/apps/everyday/index.html?task=mail&"


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def still(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", str(src), "-frames:v", "1", str(dst)], check=True)


async def record():
    from eidos.ui.run import run_ui, replay_ui
    from eidos.ui.tasks import fresh_inputs, score
    sk = ROOT / "runs" / "ui_skill_mail"
    prog = json.loads((sk / "program.json").read_text())
    trace = json.loads((sk / "trace.json").read_text())
    tmp = ROOT / "runs" / "story_rec"
    inp = {**prog["inputs"], **fresh_inputs("mail", random.Random(5))}
    other = BASE + "skin=B&theme=dark&order=2,0,1&data=21"
    out = {}
    r = await replay_ui(trace, other, tmp / "other_replay", record=True)
    out["other_replay"] = score("mail", r["oracle_state"], prog["inputs"])["success"]
    r = await run_ui(prog, other, tmp / "other_eidos", inp, record=True)
    out["other_eidos"] = (r["all_contracts_passed"], score("mail", r["oracle_state"], inp)["success"])
    # find an interruption moment where checks-off fails and EIDOS repairs
    for delay in (5.0, 6.5, 4.0, 8.0, 3.0):
        url = BASE + f"skin=A&popup={delay}&data=33"
        a = await run_ui(prog, url, tmp / "int_nochk", inp, use_contracts=False, record=True)
        b = await run_ui(prog, url, tmp / "int_eidos", inp, record=True)
        sa, sb = score("mail", a["oracle_state"], inp)["success"], score("mail", b["oracle_state"], inp)["success"]
        reps = sum(s["attempts"] - 1 for s in b["steps"])
        print("delay", delay, "nochk", sa, "eidos", sb, "repairs", reps)
        if not sa and sb and reps:
            out["interrupt_delay"] = delay
            break
    for k in ("other_replay", "other_eidos", "int_nochk", "int_eidos"):
        shutil.copy(tmp / k / "run.mp4", CLIPS / f"{k}.mp4")
        still(CLIPS / f"{k}.mp4", STILLS / f"{k}_end.png")
    print(out)


def data():
    for t in ("mail", "calendar", "expense", "settings"):
        shutil.copy(ROOT / "videos" / f"tutorial_{t}.mp4", CLIPS / f"tutorial_{t}.mp4")
    tr = json.loads((ROOT / "runs" / "ui_skill_mail" / "trace.json").read_text())
    (VID / "src" / "mail_trace.json").write_text(json.dumps({"steps": [
        {"t": s["t"], "box": s.get("box"), "value": s.get("value")} for s in tr["steps"]]}))
    prog = json.loads((ROOT / "runs" / "ui_skill_mail" / "program.json").read_text())
    rows = []
    for s in prog["steps"]:
        if s["do"] == "press":
            what, c = f"“{s['target']['text']}”", "screen then shows " + ", ".join(s["contract"]["screen_shows"])
        else:
            what, c = f"{s['value']} into “{s['target']['field']}”", f"the box labelled {s['target']['field']} shows {s['value']}"
        rows.append({"do": s["do"], "what": what, "contract": c})

    def tally(path, cond=None, systems=("replay", "nochk", "eidos")):
        rows_ = json.loads(Path(path).read_text())["rows"]
        f = lambda sysn: [r for r in rows_ if r["system"] == sysn and (cond is None or r["cond"] == cond)]
        return {s: [sum(r["success"] for r in f(s)), len(f(s))] for s in systems}, rows_
    ev, evrows = tally(ROOT / "runs" / "bench_everyday_test2" / "results.json")
    evint, _ = tally(ROOT / "runs" / "bench_everyday_test2" / "results.json", "interrupt")
    wd, wdrows = tally(ROOT / "runs" / "bench_everyday_words" / "results.json", systems=("eidos", "eidos_live"))
    # spreadsheet held-out (seed 9001), as used by the first explainer
    sh = json.loads((VID / "src" / "results.json").read_text())["test"]
    g = lambda d: [d["success"], d["n"]]
    sheet = {"replay": g(sh["all"]["replay"]), "nochk": g(sh["all"]["eidos_nochk"]), "eidos": g(sh["all"]["eidos"])}
    clips = {k: round(dur(CLIPS / f"{k}.mp4"), 2) for k in ("other_replay", "other_eidos", "int_nochk", "int_eidos", "renamed_offline", "renamed_live")
             if (CLIPS / f"{k}.mp4").exists()}
    ei = [r for r in evrows if r["system"] == "eidos"] + [r for r in wdrows if r["system"] == "eidos_live"]
    agree = [sum(r["says_done"] == r["success"] for r in ei) + sh["self"]["agrees_with_oracle"], len(ei) + sh["self"]["n"]]
    it = sh["interruption"]
    story = {"program": rows, "clips": clips, "results": {
        "everyday": {"title": f"Everyday tasks: {ev['eidos'][1]} runs across 4 tasks and 2 designs", **ev},
        "sheet": {"title": f"Spreadsheet task: {sheet['eidos'][1]} runs across 2 apps", **sheet},
        "words": {"title": f"Every control renamed: {wd['eidos'][1]} runs", "offline": wd["eidos"], "live": wd["eidos_live"]},
        "agree": f"{agree[0]}/{agree[1]}",
        "int_eidos": f"{evint['eidos'][0] + it['eidos']['success']}/{evint['eidos'][1] + it['eidos']['n']}",
        "int_nochk": f"{evint['nochk'][0] + it['eidos_nochk']['success']}/{evint['nochk'][1] + it['eidos_nochk']['n']}",
    }}
    (VID / "src" / "story.json").write_text(json.dumps(story, indent=2))
    print(json.dumps(story["results"], indent=1))


if __name__ == "__main__":
    asyncio.run(record()) if sys.argv[1] == "record" else data()
