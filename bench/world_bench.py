"""Live mistake detection on real recordings: CaptainCook4D.

CaptainCook4D (Peddi et al., NeurIPS 2024 Datasets and Benchmarks) has hundreds of first-person
recordings of people cooking recipes, many with deliberate mistakes that are labelled step by step
(missing steps, wrong order, wrong amounts, wrong technique, wrong timing and so on).

For each recipe, EIDOS learns a program from ONE recording without mistakes (the first one by
recording id; no labels are used to learn). Every other recording of that recipe, by other
people in other kitchens, is then run through the live runner as if it were a camera feed:
each look at time t sees only frames up to t. The labels are used only to score.

Splits: dev recipes were used to tune the runner; test recipes were run once with the frozen
runner.

    python bench/world_bench.py prep  --split dev     # download, sample 1 frame/s, keep frames
    python bench/world_bench.py learn --split dev
    python bench/world_bench.py run   --split dev
    python bench/world_bench.py baseline --split dev
    python bench/world_bench.py score --split dev

Data lives outside the repo (EIDOS_DATA, default ../data). Annotations come from
https://github.com/CaptainCook4D/annotations; videos from a public 360p mirror on Hugging Face.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eidos import live                                  # noqa: E402
from eidos.world import frames as F, learn as L, run as R   # noqa: E402
from eidos.world.calibrate import calibrate, calibrate_v3  # noqa: E402
from eidos.world import track as T                        # noqa: E402
from eidos.world.learn import _json                      # noqa: E402

DATA = Path(os.environ.get("EIDOS_DATA", ROOT.parent / "data"))
ANN = DATA / "cc_ann" / "annotation_json"
MIRROR = "https://huggingface.co/datasets/SabrianLinnn/captain_cook_4d/resolve/main/resolution_360p/{rid}_360p.mp4"
OUT = ROOT / "runs" / "world"

SPLITS = {
    # tuning only
    "dev": ["Tomato Mozzarella Salad", "Spiced Hot Chocolate"],
    # chosen by rule before any test run: the eight next-shortest recipes by average recording length
    "test": ["Microwave Egg Sandwich", "Pinwheels", "Breakfast Burritos", "Microwave French Toast",
             "Microwave Mug Pizza", "Cheese Pimiento", "Cucumber Raita", "Butter Corn Cup"],
    # round 2, fixed by the same rule before version 3 was tuned: the next six shortest recipes
    # by average recording length, none of them ever looked at
    "test2": ["Herb Omelet with Fried Tomatoes", "Ramen", "Blender Banana Pancakes", "Zoodles", "Coffee",
              "Caprese Bruschetta"],
}


def recordings(recipe: str) -> list[dict]:
    steps = json.loads((ANN / "complete_step_annotations.json").read_text())
    errs = {r["recording_id"]: r for r in json.loads((ANN / "error_annotations.json").read_text())}
    out = []
    for rid, r in steps.items():
        if r["activity_name"] != recipe:
            continue
        e = errs.get(rid, {})
        tags = [er["tag"] for s in e.get("step_annotations", []) for er in s.get("errors", [])]
        out.append({"rid": rid, "recipe": recipe, "person": r["person_id"], "env": r["environment"],
                    "steps": r["steps"], "is_error": bool(e.get("is_error")), "tags": tags,
                    "err_steps": e.get("step_annotations", [])})
    key = lambda x: tuple(int(p) for p in x["rid"].split("_"))
    return sorted(out, key=key)


def demo_of(recs: list[dict]) -> dict:
    """The recording EIDOS learns from: the first one (by id) with no mistakes."""
    return next(r for r in recs if not r["is_error"])


def calib_of(recs: list[dict]) -> dict:
    """The second correct demonstration, used to calibrate: the next one (by id) with no mistakes."""
    return [r for r in recs if not r["is_error"]][1]


# version 1: learn from one correct recording, calibrate on the next (round 1 was run with this)
# version 2: calibrate on the next two, sighting rule on, failed checks are notes, not alarms
VERSION = {"v": 1}
# version 3: ranked 20-second looks and the evidence tracker (eidos/world/track.py), calibrated on
# one extra demonstration; visual checks are notes, not alarms. Thresholds are set on development data.
PARAMS = {"seen_at": 0.9, "absent": 0.35}


def calibs_of(recs: list[dict]) -> list[dict]:
    clean = [r for r in recs if not r["is_error"]]
    return clean[1:3] if VERSION["v"] == 2 else clean[1:2]


def held_out(recs: list[dict]) -> list[dict]:
    used = {demo_of(recs)["rid"]} | {c["rid"] for c in calibs_of(recs)}
    return [r for r in recs if r["rid"] not in used]


def tag() -> str:
    return "" if VERSION["v"] == 1 else f"_v{VERSION['v']}"


def skills_dir() -> Path:
    return OUT / ("skills" + tag())


def looks_cache(demo: str, rid: str, prog: dict) -> Path:
    """Looks depend only on the step list shown to the model (and the kind of look), so they are cached by it."""
    import hashlib
    h = hashlib.sha1(R.step_list(prog).encode()).hexdigest()[:10]
    kind = "__ranked20" if VERSION["v"] >= 3 else ""
    return OUT / "looks" / f"{demo}__{rid}__{h}{kind}.json"


def frames_dir(rid: str) -> Path:
    return DATA / "cc" / rid / "frames"


def video_path(rid: str) -> Path:
    return DATA / "cc" / rid / f"{rid}.mp4"


def prep_one(rid: str, keep_video: bool) -> bool:
    fd = frames_dir(rid)
    if (fd / "done").exists() and (not keep_video or video_path(rid).exists()):
        return True
    vp = video_path(rid)
    vp.parent.mkdir(parents=True, exist_ok=True)
    if not vp.exists():
        r = subprocess.run(["curl", "-sfL", "-m", "900", "-o", str(vp), MIRROR.format(rid=rid)])
        if r.returncode != 0:
            vp.unlink(missing_ok=True)
            return False
    fd.mkdir(parents=True, exist_ok=True)
    for t, f in F.sample(str(vp), 1.0):
        cv2.imwrite(str(fd / f"{t:08.2f}.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 82])
    (fd / "done").write_text("ok")
    if not keep_video:
        vp.unlink(missing_ok=True)
    return True


def load_frames(rid: str) -> list[tuple[float, object]]:
    fd = frames_dir(rid)
    return [(float(p.stem), cv2.imread(str(p))) for p in sorted(fd.glob("*.jpg"))]


# --------------------------------------------------------------------------- scoring helpers

def overlap(a0, a1, b0, b1) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def step_map(program: dict, demo: dict) -> dict:
    """Program step id -> annotated step_id, by time overlap in the demonstration recording.
    Used only for scoring."""
    m = {}
    for s in program["steps"]:
        best, bo = None, 0.0
        for a in demo["steps"]:
            o = overlap(s["start"], s["end"], a["start_time"], a["end_time"])
            if o > bo:
                best, bo = a["step_id"], o
        if best is not None:
            m[s["id"]] = best
    return m


# --------------------------------------------------------------------------- stages

async def do_learn(split: str):
    for recipe in SPLITS[split]:
        recs = recordings(recipe)
        demo = demo_of(recs)
        sk = OUT / "skills" / demo["rid"]
        if (sk / "program_raw.json").exists():
            continue
        prep_one(demo["rid"], keep_video=True)
        t0 = time.monotonic()
        prog = await L.learn(str(video_path(demo["rid"])), sk)
        prog["recipe"] = recipe
        prog["learn_seconds"] = round(time.monotonic() - t0, 1)
        (sk / "program_raw.json").write_text(json.dumps(prog, indent=1))
        print(f"learned {recipe} from {demo['rid']}: {len(prog['steps'])} steps in {prog['learn_seconds']}s", flush=True)
    for recipe in SPLITS[split]:
        recs = recordings(recipe)
        demo = demo_of(recs)
        raw_dir = OUT / "skills" / demo["rid"]
        sk = skills_dir() / demo["rid"]
        if (sk / "program.json").exists() and "calibration" in json.loads((sk / "program.json").read_text()):
            continue
        if sk != raw_dir:
            sk.mkdir(parents=True, exist_ok=True)
            shutil.copytree(raw_dir / "evidence", sk / "evidence", dirs_exist_ok=True)
        prog = json.loads((raw_dir / "program_raw.json").read_text())
        changes = []
        for i, cal in enumerate(calibs_of(recs)):
            prep_one(cal["rid"], keep_video=False)
            cache = looks_cache(demo["rid"], cal["rid"], prog)
            cal_fn = calibrate_v3 if VERSION["v"] >= 3 else calibrate
            prog, res = await cal_fn(prog, R.load_refs(sk, prog), load_frames(cal["rid"]),
                                     source=f"{['second', 'third'][i]} demonstration ({cal['rid']})",
                                     looks=json.loads(cache.read_text()) if cache.exists() else None)
            changes += res["changes"] if VERSION["v"] >= 3 else prog["calibration"]["changes"]
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(res["looks"]))
        prog["calibration"] = {"source": ", ".join(c["rid"] for c in calibs_of(recs)), "changes": changes}
        (sk / "program.json").write_text(json.dumps(prog, indent=1))
        print(f"calibrated {recipe} on {prog['calibration']['source']}: {len(changes)} changes", flush=True)


async def do_run(split: str, concurrency: int, only: str | None = None, sightings: bool = False):
    """sightings=False is the tracker the test split was run with (frozen); True adds the rule,
    made after that run, that a step seen once counts when a step that needs it starts. Its
    results go to a separate folder."""
    for recipe in SPLITS[split]:
        recs = recordings(recipe)
        demo = demo_of(recs)
        sk = skills_dir() / demo["rid"]
        prog = json.loads((sk / "program.json").read_text())
        refs = R.load_refs(sk, prog)
        for r in held_out(recs):
            if only and r["rid"] != only:
                continue
            v2 = VERSION["v"] >= 2
            dst = OUT / (split + tag() + ("_sightings" if sightings and not v2 else "")) / f"{r['rid']}.json"
            if dst.exists():
                continue
            if not prep_one(r["rid"], keep_video=False):
                print("download failed", r["rid"], flush=True)
                continue
            fr = load_frames(r["rid"])
            n0 = len(live.LOG)
            t0 = time.monotonic()
            cache = looks_cache(demo["rid"], r["rid"], prog)
            cached = json.loads(cache.read_text()) if cache.exists() else None
            if VERSION["v"] >= 3:
                res = await T.replay(prog, refs, fr, concurrency=concurrency, looks=cached, contracts=False,
                                     seen_at=PARAMS["seen_at"], absent=PARAMS["absent"])
            else:
                res = await R.replay(prog, refs, fr, concurrency=concurrency, sightings=sightings or v2,
                                     contract_alarms=not v2, looks=cached)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(res["looks"]))
            calls = live.LOG[n0:]
            res.update({"rid": r["rid"], "recipe": recipe, "demo": demo["rid"], "seconds": fr[-1][0] if fr else 0,
                        "wall": round(time.monotonic() - t0, 1),
                        "look_latency": sorted(c["seconds"] for c in calls if c["purpose"] == "live look"),
                        "failed_calls": sum(1 for c in calls if not c["ok"])})
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(json.dumps(res))
            print(f"{recipe} {r['rid']} truth={'error' if r['is_error'] else 'clean'} "
                  f"alerts={[a['type'] for a in res['alerts']]} wall={res['wall']}s", flush=True)


BASELINE = """A person was asked to do this task: {title}.
The steps:
{steps}

These {n} frames are spread evenly over their whole recording, oldest first.
Did the person make any mistake: skip a step, do steps in the wrong order, use a wrong amount, use a wrong technique, or anything else that does not follow the steps?
Reply only with JSON: {{"mistake": true or false, "what": "one short sentence"}}"""


BASELINE_STEPS = """A person was asked to do this task: {title}.
The steps:
{steps}

These {n} frames are spread evenly over their whole recording, oldest first.
Which of these steps did the person skip entirely? List only steps you are confident were never done.
Reply only with JSON: {{"skipped": [step numbers], "why": "one short sentence"}}"""


async def do_baseline_steps(split: str, n: int = 24, concurrency: int = 6):
    """Muse Spark asked directly which steps were skipped (to compare with EIDOS naming skipped steps)."""
    sem = asyncio.Semaphore(concurrency)

    async def one(prog, r):
        dst = OUT / split / "baseline_steps" / f"{r['rid']}.json"
        if dst.exists():
            return
        async with sem:
            files = sorted(frames_dir(r["rid"]).glob("*.jpg"))
            idx = [round(i * (len(files) - 1) / (n - 1)) for i in range(n)]
            content = [{"type": "input_image", "image_url": live.data_url(cv2.imread(str(files[i])), 70)} for i in idx]
            content.append({"type": "input_text", "text": BASELINE_STEPS.format(title=prog["title"], steps=R.step_list(prog), n=n)})
            for attempt in range(3):
                try:
                    resp = await live.meta_responses(live.MODELS["spark"], content, "baseline steps", reasoning={"effort": "low"})
                    j = _json(live.output_text(resp))
                    if isinstance(j, dict) and "skipped" in j:
                        sk = [int(x) for x in j["skipped"] if str(x).isdigit()]
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_text(json.dumps({"rid": r["rid"], "skipped": sk, "why": j.get("why", "")}))
                        return
                except Exception:
                    await asyncio.sleep(3 + 3 * attempt)

    jobs = []
    for recipe in SPLITS[split]:
        recs = recordings(recipe)
        demo = demo_of(recs)
        prog = json.loads((OUT / "skills" / demo["rid"] / "program.json").read_text())
        jobs += [one(prog, r) for r in held_out(recs)]
    await asyncio.gather(*jobs)


async def do_baseline(split: str, n: int = 24, concurrency: int = 6):
    sem = asyncio.Semaphore(concurrency)

    async def one(prog, r):
        dst = OUT / split / "baseline" / f"{r['rid']}.json"
        if dst.exists():
            return
        if not prep_one(r["rid"], keep_video=False):
            return
        async with sem:
            # only the frames the question uses, loaded when its turn comes (all recordings at
            # once would not fit in memory)
            files = sorted(frames_dir(r["rid"]).glob("*.jpg"))
            idx = [round(i * (len(files) - 1) / (n - 1)) for i in range(n)]
            content = [{"type": "input_image", "image_url": live.data_url(cv2.imread(str(files[i])), 70)} for i in idx]
            content.append({"type": "input_text", "text": BASELINE.format(title=prog["title"], steps=R.step_list(prog), n=n)})
            for attempt in range(3):
                try:
                    resp = await live.meta_responses(live.MODELS["spark"], content, "baseline", reasoning={"effort": "low"})
                    j = _json(live.output_text(resp))
                    if isinstance(j, dict) and "mistake" in j:
                        m = j["mistake"] if isinstance(j["mistake"], bool) else str(j["mistake"]).lower() == "true"
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_text(json.dumps({"rid": r["rid"], "mistake": m, "what": j.get("what", "")}))
                        return
                except Exception:
                    await asyncio.sleep(3 + 3 * attempt)

    jobs = []
    for recipe in SPLITS[split]:
        recs = recordings(recipe)
        demo = demo_of(recs)
        prog = json.loads((OUT / "skills" / demo["rid"] / "program.json").read_text())
        jobs += [one(prog, r) for r in held_out(recs)]
    await asyncio.gather(*jobs)


def prf(pred: list[bool], truth: list[bool]) -> dict:
    tp = sum(p and t for p, t in zip(pred, truth))
    fp = sum(p and not t for p, t in zip(pred, truth))
    fn = sum(t and not p for p, t in zip(pred, truth))
    tn = sum(not p and not t for p, t in zip(pred, truth))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"n": len(pred), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(prec, 3),
            "recall": round(rec, 3), "f1": round(f1, 3), "accuracy": round((tp + tn) / len(pred), 3) if pred else 0.0}


def do_score(split: str, variant: str = "") -> dict:
    rows, track_hit, track_n, lat = [], 0, 0, []
    skip_stats = {}
    miss_hit = miss_n = 0
    for recipe in SPLITS[split]:
        recs = recordings(recipe)
        demo = demo_of(recs)
        prog = json.loads((skills_dir() / demo["rid"] / "program.json").read_text())
        pmap = step_map(prog, demo)                     # program step -> annotated step
        inv = {}
        for p, a in pmap.items():
            inv.setdefault(a, set()).add(p)
        for r in held_out(recs):
            f = OUT / (split + variant) / f"{r['rid']}.json"
            if not f.exists():
                continue
            res = json.loads(f.read_text())
            lat += res.get("look_latency", [])
            types = [a["type"] for a in res["alerts"]]
            b = OUT / split / "baseline" / f"{r['rid']}.json"
            base = json.loads(b.read_text())["mistake"] if b.exists() else None
            rows.append({"rid": r["rid"], "recipe": recipe, "truth": r["is_error"], "tags": r["tags"],
                         "eidos": bool(types), "eidos_nocontract": any(t != "contract" for t in types),
                         "eidos_nosearch": bool(types) or bool(res.get("dismissed")),
                         "baseline": base, "alerts": types})
            # step tracking: looks inside an annotated step whose step EIDOS learned
            for lk in res["looks"]:
                for a in r["steps"]:
                    if a["start_time"] <= lk["t"] - 1 and lk["t"] <= a["end_time"] and a["step_id"] in inv:
                        track_n += 1
                        track_hit += lk["doing"] in inv[a["step_id"]]
                        break
            # skipped steps: how many steps each system says were skipped (EIDOS: only "missing"
            # alerts, i.e. never seen by the end; the baseline: its list)
            bs = OUT / (split) / "baseline_steps" / f"{r['rid']}.json"
            base_sk = set(json.loads(bs.read_text())["skipped"]) if bs.exists() else None
            eid_sk = {a["step"] for a in res["alerts"] if a["type"] == "missing"}
            labelled = {s_["step_id"] for s_ in r["err_steps"] if any(e["tag"] == "Missing Step" for e in s_.get("errors", []))}
            for sysname, claimed in (("eidos", eid_sk), ("baseline", base_sk)):
                if claimed is None:
                    continue
                d = skip_stats.setdefault(sysname, {"labelled": 0, "named": 0, "claims_on_correct_recordings": 0, "correct_recordings": 0,
                                                     "claims_total": 0, "claims_matching_a_label": 0})
                for a in labelled:
                    if a in inv:
                        d["labelled"] += 1
                        d["named"] += bool(inv[a] & claimed)
                d["claims_total"] += len(claimed)
                d["claims_matching_a_label"] += sum(1 for c in claimed if pmap.get(c) in labelled)
                if not r["is_error"]:
                    d["correct_recordings"] += 1
                    d["claims_on_correct_recordings"] += len(claimed)
            # missing steps: was the right step reported missing?
            missing_alerts = {a["step"] for a in res["alerts"] if a["type"] in ("missing", "order")}
            for s in r["err_steps"]:
                if any(e["tag"] == "Missing Step" for e in s.get("errors", [])) and s["step_id"] in inv:
                    miss_n += 1
                    miss_hit += bool(inv[s["step_id"]] & missing_alerts)
    truth = [x["truth"] for x in rows]
    with_base = [x for x in rows if x["baseline"] is not None]
    by_tag = {}
    for x in rows:
        for t in set(x["tags"]):
            d = by_tag.setdefault(t, {"n": 0, "eidos": 0, "baseline": 0})
            d["n"] += 1
            d["eidos"] += x["eidos"]
            d["baseline"] += bool(x["baseline"])
    lat.sort()
    summary = {
        "split": split, "recipes": SPLITS[split], "recordings": len(rows),
        "with_mistakes": sum(truth), "without_mistakes": len(truth) - sum(truth),
        "eidos": prf([x["eidos"] for x in rows], truth),
        "eidos_no_contracts": prf([x["eidos_nocontract"] for x in rows], truth),
        "eidos_no_search_back": prf([x["eidos_nosearch"] for x in rows], truth),
        "baseline_ask_muse_spark": prf([x["baseline"] for x in with_base], [x["truth"] for x in with_base]) if with_base else None,
        "recall_by_mistake_type": by_tag,
        "missing_step_named_correctly": {"n": miss_n, "hit": miss_hit},
        "skipped_steps": skip_stats,
        "step_tracking": {"looks": track_n, "correct": track_hit, "accuracy": round(track_hit / track_n, 3) if track_n else None},
        "look_latency_median_s": lat[len(lat) // 2] if lat else None,
        "rows": rows,
    }
    (OUT / f"summary_{split}{variant}.json").write_text(json.dumps(summary, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prep", "learn", "run", "baseline", "baseline_steps", "score"])
    ap.add_argument("--split", default="dev")
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--only")
    ap.add_argument("--version", type=int, default=1, help="1: as round 1 was run; 2: two calibration demos, sighting rule, checks as notes; 3: ranked looks and evidence tracker")
    ap.add_argument("--seen-at", type=float, default=0.9)
    ap.add_argument("--absent", type=float, default=0.35)
    ap.add_argument("--sightings", action="store_true", help="the tracker rule added after the test run (separate results)")
    a = ap.parse_args()
    VERSION["v"] = a.version
    PARAMS.update({"seen_at": a.seen_at, "absent": a.absent})
    if a.stage == "prep":
        for recipe in SPLITS[a.split]:
            recs = recordings(recipe)
            demo = demo_of(recs)
            for r in recs:
                ok = prep_one(r["rid"], keep_video=(r["rid"] == demo["rid"]))
                print(r["rid"], "ok" if ok else "FAILED", flush=True)
    elif a.stage == "learn":
        asyncio.run(do_learn(a.split))
    elif a.stage == "run":
        asyncio.run(do_run(a.split, a.concurrency, a.only, a.sightings))
    elif a.stage == "baseline":
        asyncio.run(do_baseline(a.split))
    elif a.stage == "baseline_steps":
        asyncio.run(do_baseline_steps(a.split))
    else:
        s = do_score(a.split, tag() or ("_sightings" if a.sightings else ""))
        print(json.dumps({k: v for k, v in s.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
