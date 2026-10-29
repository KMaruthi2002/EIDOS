"""Assemble the demo page from real run outputs (no hand-entered numbers)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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
    for split in ("dev", "test", "test_v1"):
        f = RUNS / f"bench_{split}" / "results.json"
        if f.exists():
            r = json.loads(f.read_text())
            bench[split] = {"summary": r["summary"], "seed": r["seed"]}

    data = {"trace": trace, "program": program, "showcase": showcase, "bench": bench}
    html = (ROOT / "web" / "demo_template.html").read_text()
    html = html.replace("/*DATA*/null", json.dumps(data))
    (OUT / "index.html").write_text(html)
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"{OUT / 'index.html'}  total {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
