"""Record the physical demo: the same learned stacking skill, bumped mid-task,
run with contract checks and with checks off. Writes mp4s plus a JSON report."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sim import Sim  # noqa: E402
from skill import learn, run, ground_truth  # noqa: E402

OUT = HERE / "runs" / "showcase"
LAYOUT = {"blue": (0.5, -0.15), "green": (0.58, 0.14), "yellow": (0.40, 0.05)}
COL = {"step": (40, 60, 90), "pass": (11, 143, 99), "fail": (207, 48, 73), "bump": (210, 120, 20), "info": (40, 60, 90)}


def write_mp4(frames, path: Path, fps=25):
    h, w = frames[0].shape[:2]
    tmp = path.with_suffix(".part.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                          "-crf", "20", str(tmp)], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close()
    if p.wait() == 0:
        tmp.rename(path)


def one(program, use_contracts: bool, label: str):
    sim = Sim(LAYOUT)
    state = {"msg": "", "kind": "info"}

    def overlay(img):
        img = img.copy()
        cv2.rectangle(img, (0, 0), (img.shape[1], 44), (255, 255, 255), -1)
        cv2.putText(img, label, (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 33, 48), 2, cv2.LINE_AA)
        if state["msg"]:
            c = COL.get(state["kind"], (40, 60, 90))
            cv2.rectangle(img, (0, img.shape[0] - 46), (img.shape[1], img.shape[0]), c, -1)
            cv2.putText(img, state["msg"][:78], (16, img.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (255, 255, 255), 2, cv2.LINE_AA)
        return img

    sim.overlay = overlay

    def log(msg, kind):
        # drop the measurement dict from captions; keep it in the report
        state["msg"], state["kind"] = msg.split(" {")[0], kind

    sim.home()
    bump = (1, lambda s: s.nudge("green", (0.0, 0.10)))
    rep = run(program, sim, use_contracts=use_contracts, disturb=bump, log_cb=log)
    truth = ground_truth(sim, program)
    state["msg"] = ("Agent says: done. " if rep["agent_says_done"] else "Agent says: failed. ") + \
                   ("Stack is correct." if truth else "Stack is NOT correct.")
    state["kind"] = "pass" if truth else "fail"
    sim.step(2.0)
    return sim.frames, {**rep, "truth": truth}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    demo = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "demo" / "sim_demo.mp4"
    program = learn(demo)
    (OUT / "program.json").write_text(json.dumps(program, indent=2))
    report = {"learned_from": demo.name, "program": program}
    for chk, name, label in [(True, "eidos", "EIDOS (checks on)"), (False, "nochk", "EIDOS with checks off")]:
        frames, rep = one(program, chk, label)
        write_mp4(frames, OUT / f"{name}.mp4")
        report[name] = rep
        print(name, "truth", rep["truth"], "agent says", rep["agent_says_done"], flush=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
