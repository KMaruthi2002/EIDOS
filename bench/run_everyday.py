"""Everyday-task benchmark: four tasks, five conditions, three systems.

    python bench/run_everyday.py BASE_URL SPLIT     (SPLIT = dev | test)

dev uses seed 7 (used while fixing bugs). test uses seed 31337 and is run once.
For each task: same app and data as the tutorial; new data; random redesigns of
App A; App B (a different design) with random variations; and runs where a
dialog interrupts at a random moment. Every run except "same" uses fresh
inputs, so a system that copies the tutorial's typing cannot pass by luck.
Success is judged from the app's internal state, which no system sees.
"""
from __future__ import annotations

import asyncio
import os
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eidos.ui.run import run_ui, replay_ui          # noqa: E402
from eidos.ui.tasks import TUTORIALS, N_FIELDS, fresh_inputs, score, URL   # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
SPLIT = sys.argv[2] if len(sys.argv) > 2 else "dev"
SEED = {"dev": 7, "test": 31337, "test2": 50505, "words_dev": 8, "words": 60606,
        "words_dev_open": 8, "words_open": 60606}.get(SPLIT, int(SPLIT) if SPLIT.isdigit() else 7)
ONLY_OPEN = SPLIT.endswith("_open")   # same conditions as the matching split, Muse Spark Open only
WORDS = SPLIT.startswith("words")     # design C: every control renamed (needs a model to read meaning)
N_REDESIGN, N_OTHER, N_INTERRUPT = 6, 3, 4
OUT = ROOT / "runs" / f"bench_everyday_{SPLIT}"
from eidos import live as L    # noqa: E402
# a live system is included only if its key actually works (one tiny test call)
SYSTEMS = ("replay", "replay_new", "nochk", "eidos") + (("eidos_live",) if L.meta_live() and L.works("spark") else ()) \
    + (("eidos_open",) if L.open_live() and L.works("open") else ())
if ONLY_OPEN:
    SYSTEMS = ("eidos_open",)


def redesign(rng, task, skin):
    q = {"skin": skin}
    while True:
        if rng.random() < 0.5:
            q["theme"] = "dark"
        q["nav"] = rng.choice(["left", "right", "top"])
        q["labels"] = rng.choice(["left", "top"])
        q["btn"] = rng.choice(["top", "bottom"])
        q["scale"] = rng.choice(["1", "1.1", "1.2"])
        if rng.random() < 0.75:
            perm = list(range(N_FIELDS[task]))
            rng.shuffle(perm)
            q["order"] = ",".join(map(str, perm))
        default = {"A": ("left", "left", "bottom"), "B": ("top", "top", "top")}[skin]
        if skin == "B" or (q["nav"], q["labels"], q["btn"]) != default or "theme" in q or "order" in q:
            return q


def conditions():
    rng = random.Random(SEED)
    out = []
    if WORDS:
        for task in TUTORIALS:
            for _ in range(8):
                skin = rng.choice(["A", "B"])
                q = redesign(rng, task, skin) if rng.random() < 0.5 else {"skin": skin}
                q.update(words="alt", data=rng.randint(2, 99))
                out.append({"task": task, "cond": "renamed", "q": q, "inputs": fresh_inputs(task, rng)})
        return out
    for task in TUTORIALS:
        out.append({"task": task, "cond": "same", "q": {"skin": "A"}, "inputs": None})
        out.append({"task": task, "cond": "new_data", "q": {"skin": "A", "data": rng.randint(2, 99)}, "inputs": fresh_inputs(task, rng)})
        for _ in range(N_REDESIGN):
            q = redesign(rng, task, "A"); q["data"] = rng.randint(2, 99)
            out.append({"task": task, "cond": "redesign", "q": q, "inputs": fresh_inputs(task, rng)})
        for _ in range(N_OTHER):
            q = redesign(rng, task, "B"); q["data"] = rng.randint(2, 99)
            out.append({"task": task, "cond": "other_app", "q": q, "inputs": fresh_inputs(task, rng)})
        for _ in range(N_INTERRUPT):
            skin = rng.choice(["A", "B"])
            q = redesign(rng, task, skin) if rng.random() < 0.5 else {"skin": skin}
            q["data"] = rng.randint(2, 99)
            q["popup"] = round(rng.uniform(1.5, 9.0), 1)
            out.append({"task": task, "cond": "interrupt", "q": q, "inputs": fresh_inputs(task, rng)})
    return out


async def one(sem, i, c, system):
    task = c["task"]
    sk = ROOT / "runs" / f"ui_skill_{task}"
    prog = json.loads((sk / "program.json").read_text())
    inputs = {**prog["inputs"], **(c["inputs"] or {})}
    url = f"{BASE}{URL}?task={task}&" + "&".join(f"{k}={v}" for k, v in c["q"].items())
    out = OUT / f"{i:03d}_{task}_{c['cond']}_{system}"
    async with sem:
        t = time.monotonic()
        try:
            if system in ("replay", "replay_new"):
                # Copying the clicks never checks anything, so it has no verdict of its own;
                # it is counted as "says done". replay_new types this run's values.
                sub = {prog["inputs"][k]: v for k, v in inputs.items() if k in prog["inputs"]} if system == "replay_new" else None
                rep = await replay_ui(json.loads((sk / "trace.json").read_text()), url, out, substitute=sub)
                says = True
            else:
                rep = await run_ui(prog, url, out, inputs, use_contracts=(system != "nochk"),
                                   live=system in ("eidos_live", "eidos_open"),
                                   reader={"eidos_live": "spark", "eidos_open": "open"}.get(system))
                says = rep["all_contracts_passed"] if system != "nochk" else all(
                    not any("error" in ch for ch in s["checks"]) for s in rep["steps"])
            truth = score(task, rep.get("oracle_state"), inputs)
        except Exception as e:
            says, truth, rep = False, {"success": False, "why": f"crash: {e!r}"}, {}
        dt = round(time.monotonic() - t, 1)
    row = {"i": i, "task": task, "cond": c["cond"], "system": system, "url": url, "inputs": inputs,
           "says_done": bool(says), "success": truth["success"], "why": truth.get("why", ""), "seconds": dt,
           "repairs": sum(max(0, s.get("attempts", 1) - 1) for s in rep.get("steps", []))}
    print(f"{i:03d} {task:9s} {c['cond']:10s} {system:7s} says={row['says_done']!s:5s} truth={row['success']!s:5s} {dt}s {row['why'][:60]}", flush=True)
    return row


async def main():
    if SPLIT != "dev" and (OUT / "results.json").exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT}/results.json already holds the recorded held-out result. A held-out seed is run once; "
                 "pass --force to overwrite it, or choose another seed.")
    OUT.mkdir(parents=True, exist_ok=True)
    conds = conditions()
    sem = asyncio.Semaphore(int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 3)
    jobs = [one(sem, i, c, s) for i, c in enumerate(conds) for s in SYSTEMS]
    rows = await asyncio.gather(*jobs)
    (OUT / "results.json").write_text(json.dumps({"seed": SEED, "split": SPLIT, "rows": rows}, indent=2))
    summarize(rows)


def summarize(rows):
    def cell(rs):
        return f"{sum(r['success'] for r in rs)}/{len(rs)}"
    systems = [x for x in SYSTEMS if any(r["system"] == x for r in rows)]
    print("\ncondition    runs  " + "  ".join(f"{x:10s}" for x in systems))
    groups = [(c, lambda r, c=c: r["cond"] == c) for c in ("same", "new_data", "redesign", "other_app", "interrupt", "renamed")]
    groups += [("ALL", lambda r: True)] + [(f"  {t}", lambda r, t=t: r["task"] == t) for t in TUTORIALS]
    for name, f in groups:
        by = {x: [r for r in rows if f(r) and r["system"] == x] for x in systems}
        print(f"{name:12s} {len(by[systems[0]]):4d}  " + "  ".join(f"{cell(by[x]):10s}" for x in systems))
    for x in [x for x in ("nochk", "eidos", "eidos_live", "eidos_open") if x in systems]:
        rs = [r for r in rows if r["system"] == x]
        agree = sum(r["says_done"] == r["success"] for r in rs)
        silent = sum(r["says_done"] and not r["success"] for r in rs)
        print(f"{x}: verdict matches truth {agree}/{len(rs)}; silent failures {silent}")


if __name__ == "__main__":
    asyncio.run(main())
