"""Assemble the demo page from real run outputs (no hand-entered numbers)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
RUNS = ROOT / "runs"
OUT = ROOT / "web" / "demo"


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "assets" / "runs").mkdir(parents=True)
    skill = RUNS / "tutorial_totals"
    trace = json.loads((skill / "trace.json").read_text())
    program = json.loads((skill / "program.json").read_text())
    shutil.copy(ROOT / "videos" / "tutorial_totals.mp4", OUT / "assets" / "tutorial_totals.mp4")
    import cv2
    for s in trace["steps"]:
        c = s["contract"]
        box = c.get("selection_box") or c.get("cell_box") or c.get("probe_box") or [60, 380, 560, 24]
        y0 = max(0, int(box[1]) - 40)
        for k in ("pre", "post"):
            im = cv2.imread(str(skill / s["crops"][k]))
            crop = im[y0:y0 + 90, 40:640]
            cv2.imwrite(str(OUT / "assets" / ("zoom_" + s["crops"][k])), cv2.resize(crop, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC))

    showcase = json.loads((RUNS / "showcase" / "index.json").read_text())
    for c in showcase:
        for sysname in ("eidos", "replay"):
            src = RUNS / "showcase" / c["id"] / sysname / "run.mp4"
            shutil.copy(src, OUT / "assets" / "runs" / f"{c['id']}_{sysname}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", str(src), "-frames:v", "1",
                            "-q:v", "3", str(OUT / "assets" / "runs" / f"{c['id']}_{sysname}_end.jpg")], check=True)
        rep = json.loads((RUNS / "showcase" / c["id"] / "eidos" / "report.json").read_text())
        rep.pop("oracle_state", None)
        c["eidos_report"] = rep

    bench = {}
    for split in ("dev", "test", "test_v1", "test_v2"):
        f = RUNS / f"bench_{split}" / "results.json"
        if f.exists():
            r = json.loads(f.read_text())
            bench[split] = {"summary": r["summary"], "seed": r["seed"]}

    # ---- everyday tasks
    from eidos.ui.tasks import TITLES
    import re as _re
    ev = {"tasks": [], "clips": [], "bench": {}}
    for task, title in TITLES.items():
        prog = json.loads((RUNS / f"ui_skill_{task}" / "program.json").read_text())
        shutil.copy(ROOT / "videos" / f"tutorial_{task}.mp4", OUT / "assets" / f"tutorial_{task}.mp4")
        bindv = lambda t: _re.sub(r"\{(\w+)\}", lambda m: f"{{{m.group(1)}}}", t)
        ev["tasks"].append({"task": task, "title": title, "inputs": prog["inputs"],
                            "steps": [{"do": st["do"], "intent": st["intent"], "contract": st["contract"],
                                       "target": st["target"]} for st in prog["steps"]]})
    sc = RUNS / "showcase_everyday"
    idx = {c["id"]: c for c in json.loads((sc / "index.json").read_text())}
    for k in idx:
        shutil.copy(sc / k / "run.mp4", OUT / "assets" / "runs" / f"ev_{k}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", str(sc / k / "run.mp4"), "-frames:v", "1",
                        "-q:v", "3", str(OUT / "assets" / "runs" / f"ev_{k}_end.jpg")], check=True)
        rep = json.loads((sc / k / "report.json").read_text())
        idx[k]["steps"] = [{"id": st["id"], "intent": st["intent"], "passed": st["passed"], "attempts": st["attempts"],
                            "t_start": st.get("t_start"), "t_end": st.get("t_end"),
                            "model": next((g["how"] for g in st.get("grounding", []) if " matched " in g.get("how", "")), None),
                            "checks": [{"contract": c["contract"], "pass": c["pass"]} for c in st["checks"] if not c.get("advisory")],
                            "sam": [c["pass"] for c in st["checks"] if c.get("advisory")]}
                           for st in rep.get("steps", [])]
        idx[k]["inputs"] = rep.get("inputs")
        idx[k]["aliases"] = rep.get("aliases") or {}
    ev["clips"] = [
        {"id": "other", "title": "A second design of the mail app (design B), dark mode, fields reordered, new values. One example run",
         "left": idx["other_replay"], "right": idx["other_eidos"]},
        {"id": "interrupt", "title": "A dialog pops up mid-task and swallows input. One example run",
         "left": idx["int_nochk"], "right": idx["int_eidos"]},
    ] + ([{"id": "renamed", "title": "Design C: every control renamed (Recipient for To, Deliver for Send), design B, dark mode. One example run; the Muse Spark run plays at 3x",
           "left": idx["renamed_offline"], "right": idx["renamed_live"], "rate": 3}] if "renamed_live" in idx else [])
    for task in TITLES:
        card = RUNS / f"ui_skill_{task}" / "card.webp"
        if card.exists():
            shutil.copy(card, OUT / "assets" / f"card_{task}.webp")
    for t in ev["tasks"]:
        t["card"] = (OUT / "assets" / f"card_{t['task']}.webp").exists()
    # design C (renamed controls) and the Muse Spark Open runs on the same conditions
    for split in ("words", "words_open", "words_dev", "words_dev_open"):
        f = RUNS / f"bench_everyday_{split}" / "results.json"
        if not f.exists():
            continue
        rows = json.loads(f.read_text())["rows"]
        systems = [x for x in ("replay", "replay_new", "nochk", "eidos", "eidos_live", "eidos_open") if any(r["system"] == x for r in rows)]
        summ = {task: {x: {"success": sum(r["success"] for r in rows if r["system"] == x and r["task"] == task),
                           "n": sum(1 for r in rows if r["system"] == x and r["task"] == task)} for x in systems}
                for task in list(TITLES) + ["all"] if task == "all" or any(r["task"] == task for r in rows)}
        summ["all"] = {x: {"success": sum(r["success"] for r in rows if r["system"] == x),
                           "n": sum(1 for r in rows if r["system"] == x)} for x in systems}
        summ["agree"] = {x: {"agree": sum(r["says_done"] == r["success"] for r in rows if r["system"] == x),
                             "n": sum(1 for r in rows if r["system"] == x)} for x in systems}
        ev["bench"][split] = {"seed": json.loads(f.read_text())["seed"], "summary": summ, "systems": systems}
    for split in ("test2", "test", "dev"):
        f = RUNS / f"bench_everyday_{split}" / "results.json"
        if not f.exists():
            continue
        rows = json.loads(f.read_text())["rows"]
        summ = {}
        for cond in ("same", "new_data", "redesign", "other_app", "interrupt", "all"):
            rs = [r for r in rows if cond == "all" or r["cond"] == cond]
            summ[cond] = {sysn: {"success": sum(r["success"] for r in rs if r["system"] == sysn),
                                 "n": sum(1 for r in rs if r["system"] == sysn)}
                          for sysn in ("replay", "replay_new", "nochk", "eidos") if any(r["system"] == sysn for r in rows)}
        ei = [r for r in rows if r["system"] == "eidos"]
        summ["agree"] = {"agree": sum(r["says_done"] == r["success"] for r in ei), "n": len(ei),
                         "silent": sum(r["says_done"] and not r["success"] for r in ei)}
        nk = [r for r in rows if r["system"] == "nochk" and r["cond"] == "interrupt"]
        summ["nochk_claimed_interrupt"] = {"said_done": sum(r["says_done"] for r in nk), "n": len(nk)}
        ev["bench"][split] = {"seed": json.loads(f.read_text())["seed"], "summary": summ}
    film = ROOT / "web" / "explainer_720.mp4"
    if film.exists():
        shutil.copy(film, OUT / "assets" / "explainer.mp4")
        shutil.copy(ROOT / "web" / "explainer_poster.jpg", OUT / "assets" / "explainer_poster.jpg")
    # ---- real world
    world = None
    wsk = ROOT / "samples" / "world" / "cabinet"
    if (wsk / "program.json").exists():
        (OUT / "assets" / "world").mkdir(parents=True, exist_ok=True)
        for f in (wsk / "evidence").glob("*_end.jpg"):
            shutil.copy(f, OUT / "assets" / "world" / f.name)
        live_clip = ROOT / "web" / "world_live.mp4"
        if live_clip.exists():
            shutil.copy(live_clip, OUT / "assets" / "world_live.mp4")
            shutil.copy(ROOT / "web" / "world_live.jpg", OUT / "assets" / "world_live.jpg")
        world = {"program": json.loads((wsk / "program.json").read_text())}
        for split in ("test", "dev"):
            f = RUNS / "world" / f"summary_{split}.json"
            if f.exists():
                sm = json.loads(f.read_text())
                sm.pop("rows", None)
                world[split] = sm
    data = {"trace": trace, "program": program, "showcase": showcase, "bench": bench, "everyday": ev,
            "film": film.exists(), "world": world}
    html = (ROOT / "web" / "demo_template.html").read_text()
    html = html.replace("/*DATA*/null", json.dumps(data))
    html = html.replace("<!--VIEWPORT_META-->", "")
    (OUT / "index.html").write_text(html)
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"{OUT / 'index.html'}  total {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
