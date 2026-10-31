"""How well does one live look name the current step? Scored against CaptainCook4D's step labels.

A fixed sample of moments is drawn (seeded) from held-out recordings of the development recipes
and the round-1 recipes (both are development data now). At each moment t the true step is the
annotated step covering t, mapped to the program's steps through the demonstration's own labels
(the same mapping the benchmark uses for scoring). Each variant of the look sees only frames up
to t. Accuracy counts a look right if it names one of the program steps the true step maps to.

    python bench/look_lab.py sample            # draw the moments
    python bench/look_lab.py run <variant>     # run one variant on all of them
    python bench/look_lab.py report
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))
import world_bench as W                              # noqa: E402
from eidos import live                               # noqa: E402
from eidos.world import run as R                     # noqa: E402
from eidos.world.learn import _json, bind            # noqa: E402

OUT = ROOT / "runs" / "world" / "look_lab"
RECIPES = W.SPLITS["dev"] + W.SPLITS["test"]


def sample(n_per_recipe: int = 30, seed: int = 4711):
    rng = random.Random(seed)
    moments = []
    for recipe in RECIPES:
        recs = W.recordings(recipe)
        demo = W.demo_of(recs)
        prog = json.loads((W.OUT / "skills" / demo["rid"] / "program.json").read_text())
        pmap = W.step_map(prog, demo)
        inv = {}
        for p, a in pmap.items():
            inv.setdefault(a, []).append(p)
        cands = []
        for r in W.held_out(recs):
            for a in r["steps"]:
                if a["step_id"] in inv and a["end_time"] - a["start_time"] >= 6:
                    cands.append((r["rid"], a["step_id"], a["start_time"], a["end_time"]))
        for rid, sid, t0, t1 in rng.sample(cands, min(n_per_recipe, len(cands))):
            t = round(rng.uniform(t0 + 4, t1), 1)        # a moment inside the step, after it has begun
            moments.append({"recipe": recipe, "demo": demo["rid"], "rid": rid, "t": t, "true": inv[sid]})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "moments.json").write_text(json.dumps(moments, indent=1))
    print(len(moments), "moments")


def frames_upto(rid: str, t: float, span: float, fps: float = 1.0, width: int = 448):
    files = sorted(W.frames_dir(rid).glob("*.jpg"))
    times = [float(f.stem) for f in files]
    picked = []
    want = [t - span + (i + 1) / fps for i in range(int(span * fps))]
    for w in want:
        best = min(range(len(times)), key=lambda i: abs(times[i] - w) if times[i] <= t else 1e9)
        if times[best] <= t:
            img = cv2.imread(str(files[best]))
            if width != img.shape[1]:
                img = cv2.resize(img, (width, int(img.shape[0] * width / img.shape[1])))
            picked.append((times[best], img))
    return picked


RANKED = """A person is doing this task live: {title}.
The steps:
{steps}

These {n} frames are the last {secs} seconds from the live camera, oldest first.
Which step is the person working on right now? Give your best three guesses with how likely each is, most likely first. Use 0 for "none of these steps" (moving around, fetching things, idle, something else).
Reply only with JSON: {{"guesses": [{{"step": number, "p": 0.0 to 1.0}}, ...], "what": "what they are doing, in a few words"}}"""


async def look_variant(variant: str, prog: dict, rid: str, t: float) -> dict:
    title = prog.get("title", "task")
    steps = R.step_list(prog)
    if variant == "base":                               # what round 1 used
        win = frames_upto(rid, t, 6)
        out = await R.look(prog, win)
        return {"top": out["doing"], "ranked": [out["doing"]]}
    cfg = {"low": dict(span=6, effort="low", ranked=False),
           "ranked": dict(span=6, effort="minimal", ranked=True),
           "ranked_low": dict(span=6, effort="low", ranked=True),
           "ranked_long": dict(span=12, effort="minimal", ranked=True),
           "ranked_low_long": dict(span=12, effort="low", ranked=True),
           "ranked_20": dict(span=20, effort="minimal", ranked=True)}[variant]
    win = frames_upto(rid, t, cfg["span"])
    if cfg["ranked"]:
        prompt = RANKED.format(title=title, steps=steps, n=len(win), secs=cfg["span"])
    else:
        prompt = R.LOOK_PROMPT.format(title=title, steps=steps, n=len(win))
    content = [{"type": "input_image", "image_url": live.data_url(f, 70)} for _, f in win]
    content.append({"type": "input_text", "text": prompt})
    for attempt in range(3):
        try:
            r = await live.meta_responses(live.MODELS["spark"], content, "look lab", reasoning={"effort": cfg["effort"]})
            j = _json(live.output_text(r))
            if not isinstance(j, dict):
                continue
            ids = {s["id"] for s in prog["steps"]}
            if cfg["ranked"]:
                g = [x for x in j.get("guesses", []) if isinstance(x, dict)]
                ranked = []
                for x in g:
                    try:
                        s = int(x.get("step", 0))
                    except (TypeError, ValueError):
                        continue
                    ranked.append(s if s in ids else 0)
                return {"top": ranked[0] if ranked else 0, "ranked": ranked[:3],
                        "p": [float(x.get("p", 0) or 0) for x in g][:3]}
            d = int(j.get("doing", 0) or 0)
            return {"top": d if d in ids else 0, "ranked": [d]}
        except Exception:
            await asyncio.sleep(2 + 2 * attempt)
    return {"top": 0, "ranked": [], "failed": True}


async def run(variant: str, concurrency: int = 12):
    moments = json.loads((OUT / "moments.json").read_text())
    progs = {m["demo"]: json.loads((W.OUT / "skills" / m["demo"] / "program.json").read_text()) for m in moments}
    sem = asyncio.Semaphore(concurrency)

    async def one(m):
        async with sem:
            t0 = time.monotonic()
            res = await look_variant(variant, progs[m["demo"]], m["rid"], m["t"])
            return {**m, **res, "seconds": round(time.monotonic() - t0, 2)}

    rows = await asyncio.gather(*(one(m) for m in moments))
    (OUT / f"{variant}.json").write_text(json.dumps(rows, indent=1))
    report([variant])


def report(variants=None):
    variants = variants or sorted(p.stem for p in OUT.glob("*.json") if p.stem != "moments")
    for v in variants:
        rows = json.loads((OUT / f"{v}.json").read_text())
        top1 = sum(r["top"] in r["true"] for r in rows) / len(rows)
        top3 = sum(any(x in r["true"] for x in r["ranked"]) for r in rows) / len(rows)
        none = sum(r["top"] == 0 for r in rows) / len(rows)
        lat = sorted(r["seconds"] for r in rows)[len(rows) // 2]
        print(f"{v:18s} n={len(rows)} top1={top1:.3f} top3={top3:.3f} said-none={none:.2f} median_s={lat}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sample":
        sample()
    elif cmd == "run":
        asyncio.run(run(sys.argv[2]))
    else:
        report()
