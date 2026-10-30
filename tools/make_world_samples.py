"""Build the sample real-world skills that ship with the Studio.

Each sample is learned from one demonstration video, calibrated on a second one, and comes with
practice recordings that can be played in the Studio as if they were a live camera.

Sources (both allow reuse with credit):
- CaptainCook4D (Peddi et al., NeurIPS 2024), Apache License 2.0: cooking recordings with labelled mistakes.
- HoloAssist (Wang et al., ICCV 2023), CDLA-Permissive-2.0: first-person recordings of technicians.

    python tools/make_world_samples.py        # needs MODEL_API_KEY and the source videos under EIDOS_DATA
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eidos.world import frames as F, learn as L, run as R   # noqa: E402
from eidos.world.calibrate import calibrate               # noqa: E402

DATA = Path(os.environ.get("EIDOS_DATA", ROOT.parent / "data"))
OUT = ROOT / "samples" / "world"
CC = "CaptainCook4D (Apache 2.0)"
HA = "HoloAssist (CDLA-Permissive-2.0)"

SAMPLES = [
    {"name": "tomato", "order": 1, "title": "", "credit": CC,
     "skill": ROOT / "runs" / "world" / "skills" / "12_2",          # the benchmark skill, already learned and calibrated
     "video": DATA / "cc" / "12_2" / "12_2.mp4", "source": "a cooking video (CaptainCook4D 12_2)",
     "practice": [
         {"id": "skipped-oil", "video": DATA / "cc" / "12_6" / "12_6.mp4",
          "label": "Another cook who skips a step",
          "note": "A different person in a different kitchen. Labelled in the dataset: never adds the olive oil."},
         {"id": "clean", "video": DATA / "cc" / "12_9" / "12_9.mp4",
          "label": "Another cook, done correctly",
          "note": "A different person in a different kitchen, with no mistakes labelled in the dataset."},
     ]},
    {"name": "ram", "order": 2, "title": "Install RAM in a desktop computer", "credit": HA,
     "video": DATA / "holo" / "R181-12Oct-RAM.mp4", "calib": DATA / "holo" / "R185-13Oct-RAM.mp4",
     "source": "a technician's head-camera video (HoloAssist R181)",
     "practice": [
         {"id": "tech-2", "video": DATA / "holo" / "R215-17Nov-Ram.mp4", "label": "Another technician",
          "note": "A different technician doing the same job (HoloAssist R215)."},
         {"id": "tech-3", "video": DATA / "holo" / "R197-25Oct-RAM.mp4", "label": "A third technician",
          "note": "Another technician, another day (HoloAssist R197)."},
     ]},
    {"name": "gpu", "order": 4, "title": "Install a graphics card", "credit": HA,
     "video": DATA / "holo" / "R196-25Oct-GraphicsCard.mp4", "calib": DATA / "holo" / "R197-25Oct-GraphicsCard.mp4",
     "source": "a technician's head-camera video (HoloAssist R196)",
     "practice": [
         {"id": "tech-2", "video": DATA / "holo" / "R176-11Oct-Graphicscard.mp4", "label": "Another technician",
          "note": "A different technician doing the same job (HoloAssist R176)."},
     ]},
    {"name": "cabinet", "order": 3, "title": "Replace a part in an electrical control cabinet", "credit": HA,
     "video": DATA / "holo" / "R189-24Oct-CircuitBreaker.mp4", "calib": DATA / "holo" / "R201-7Nov-CircuitBreaker.mp4",
     "source": "a technician's head-camera video (HoloAssist R189)",
     "practice": [
         {"id": "tech-2", "video": DATA / "holo" / "R092-28July-Circuit-Breaker.mp4", "label": "Another technician",
          "note": "A different technician doing the same job (HoloAssist R092)."},
         {"id": "power-on", "video": DATA / "holo" / "R092-28July-Circuit-Breaker.mp4", "cut": [15.0, 20.0],
          "label": "Edited: the power is never switched off",
          "note": "The same recording with the seconds where the disconnect switch is turned off cut out, "
                  "so the cabinet is opened with the power still on. This one is edited for the demo."},
     ]},
]


def encode(src: Path, dst: Path, cut: list | None = None):
    dst.parent.mkdir(parents=True, exist_ok=True)
    vf = "scale=640:-2,fps=24"
    if cut:
        vf = f"select='not(between(t,{cut[0]},{cut[1]}))',setpts=N/FRAME_RATE/TB," + vf
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map_metadata", "-1", str(dst)], check=True)


async def build(spec: dict):
    out = OUT / spec["name"]
    if spec.get("skill"):
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        for f in ("program.json", "notes.json"):
            shutil.copy(spec["skill"] / f, out / f)
        shutil.copytree(spec["skill"] / "evidence", out / "evidence")
        prog = json.loads((out / "program.json").read_text())
    else:
        if not (out / "program.json").exists() or "calibration" not in json.loads((out / "program.json").read_text()):
            prog = await L.learn(str(spec["video"]), out, spec["title"])
            prog, _ = await calibrate(prog, R.load_refs(out, prog), F.sample(str(spec["calib"]), 1.0),
                                      source=f"second demonstration ({spec['calib'].stem.split('-')[0]})")
            (out / "program.json").write_text(json.dumps(prog, indent=1))
        prog = json.loads((out / "program.json").read_text())
    encode(spec["video"], out / "video.mp4")
    practice = []
    for p in spec["practice"]:
        encode(p["video"], out / "practice" / f"{p['id']}.mp4", p.get("cut"))
        practice.append({"file": f"practice/{p['id']}.mp4", "label": p["label"], "note": p["note"]})
    (out / "practice.json").write_text(json.dumps(practice, indent=1))
    (out / "meta.json").write_text(json.dumps({
        "id": f"world-{spec['name']}", "kind": "world", "name": prog["title"], "sample": True, "order": spec["order"],
        "source": spec["source"], "credit": spec["credit"], "created": time.time()}))
    print("built", spec["name"], prog["title"], len(prog["steps"]), "steps", flush=True)


async def main(names: list[str]):
    for s in SAMPLES:
        if not names or s["name"] in names:
            await build(s)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
