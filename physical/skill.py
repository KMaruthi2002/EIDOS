"""Physical EIDOS: demonstration video -> stacking program -> checked robot run.

learn(video)      track coloured objects, find each pick-and-place, and record
                  what it achieved ("green is on blue") as a visual contract
run(program, sim) have the simulated arm do each step, check its contract from
                  the robot's own cameras, repair on failure, and re-check every
                  earlier contract before declaring the task done
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np

from perceive import COLORS, Side2Camera, SideCamera, TopCamera, find, locate_from_sides, relation

HALF = 0.022


# ---------------------------------------------------------------- learning

def track(video: Path, every: int = 2):
    """Per-frame blobs for each colour (BGR video in, RGB analysis)."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    out, i = [], 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        if i % every == 0:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            out.append((i / fps, rgb.shape[:2], find(rgb)))
        i += 1
    return out


def learn(video: Path) -> dict:
    """Find each placement in a demonstration and what it achieved."""
    frames = track(video)
    if not frames:
        raise ValueError("no frames")
    names = sorted({n for _, _, f in frames for n in f})
    h, w = frames[0][1]
    diag = math.hypot(w, h)

    # An object is 'at rest' when it is visible and has not moved for ~0.5 s.
    def pos(f, n):
        b = f[2].get(n)
        return (b.cx, b.cy) if b else None

    rests = []      # (t, {name: blob}) snapshots when every visible object is still
    win = 8
    for k in range(win, len(frames)):
        still = True
        for n in names:
            pts = [pos(frames[j], n) for j in range(k - win, k + 1)]
            if any(p is None for p in pts):
                still = False
                break
            spread = max(math.hypot(p[0] - pts[0][0], p[1] - pts[0][1]) for p in pts)
            if spread > 0.01 * diag:
                still = False
                break
        if still:
            rests.append((frames[k][0], frames[k][2]))
    # collapse consecutive rest frames into settled states
    states = []
    for t, blobs in rests:
        if states and t - states[-1]["t_end"] < 0.3:
            states[-1]["t_end"] = t
            states[-1]["blobs"] = blobs
        else:
            states.append({"t": t, "t_end": t, "blobs": blobs})

    steps = []
    for a, b in zip(states, states[1:]):
        moved = [n for n in names
                 if math.hypot(b["blobs"][n].cx - a["blobs"][n].cx, b["blobs"][n].cy - a["blobs"][n].cy) > 0.04 * diag]
        if len(moved) != 1:
            continue
        obj = moved[0]
        bo = b["blobs"][obj]
        target = None
        for n in names:
            if n == obj:
                continue
            if relation(bo, b["blobs"][n]) == "on" or _overhead_stack(a["blobs"], b["blobs"], obj, n):
                target = n
        steps.append({
            "do": "stack" if target else "move",
            "object": obj,
            "on": target,
            "video_time": [round(a["t_end"], 2), round(b["t"], 2)],
            "intent": f"Put the {obj} block on the {target} block" if target else f"Move the {obj} block",
            "contract": {"relation": [obj, "on", target]} if target else {"moved": obj},
        })
    return {"eidos": "0.1-physical", "learned_from": Path(video).name, "objects": names,
            "steps": steps, "settled_states": len(states)}


def _overhead_stack(before, after, obj, other) -> bool:
    """From above, stacking hides most of the lower object."""
    if other not in before or other not in after:
        return False
    o, u = after[obj], after[other]
    close = math.hypot(o.cx - u.cx, o.cy - u.cy) < 0.6 * max(o.w, o.h)
    shrank = after[other].area < 0.5 * before[other].area
    return close and shrank


# ---------------------------------------------------------------- running

class Eyes:
    """What the robot can see: an overhead camera and two level side cameras.

    Blocks fully visible from above are located from the top view; a block
    partly hidden under another is located from the two side views.
    """

    def __init__(self, sim):
        self.sim = sim
        self.top_cam, self.side_cam, self.side2_cam = TopCamera(), SideCamera(), Side2Camera()
        self.full_area = None

    def look(self):
        return (find(self.sim.render("top")), find(self.sim.render("side")), find(self.sim.render("side2")))

    def where(self, name, views=None):
        top, side, side2 = views or self.look()
        if self.full_area is None and top:
            self.full_area = max(b.area for b in top.values())
        b = top.get(name)
        if b is not None:
            wx, wy = self.top_cam.to_table(b.cx, b.cy, 2 * HALF)
            hidden_from_above = bool(self.full_area) and b.area < 0.75 * self.full_area
            if hidden_from_above and name in side and name in side2:
                return np.array(locate_from_sides(side[name], side2[name], self.side_cam, self.side2_cam))
            if name in side:
                z = self.side_cam.height(side[name].cy, wy)
            elif name in side2:
                c = self.side2_cam
                z = c.pos[2] - (side2[name].cy - c.h / 2) / c.f * (c.pos[0] - wx)
            else:
                # Seen only from above: something covers it, so it rests on the table.
                z = HALF
            wx, wy = self.top_cam.to_table(b.cx, b.cy, z + HALF)
            return np.array([wx, wy, z])
        if name in side and name in side2:
            return np.array(locate_from_sides(side[name], side2[name], self.side_cam, self.side2_cam))
        raise LookupError(f"cannot see the {name} block")

    def holds(self, rel) -> tuple[bool, dict]:
        a, _, b = rel
        views = self.look()
        try:
            pa, pb = self.where(a, views), self.where(b, views)
        except LookupError as e:
            return False, {"why": str(e)}
        dxy = float(np.hypot(*(pa[:2] - pb[:2])))
        dz = float(pa[2] - pb[2])
        ok = dxy < HALF * 0.9 and abs(dz - 2 * HALF) < HALF * 0.5
        return ok, {"offset_mm": round(dxy * 1000, 1), "height_gap_mm": round(dz * 1000, 1)}


def run(program: dict, sim, use_contracts: bool = True, disturb=None, log_cb=None) -> dict:
    """Execute a stacking program in the simulator.

    disturb: optional (after_step_index, callable(sim)) applied once, e.g. a
    bump that knocks the top block off.
    """
    eyes = Eyes(sim)
    logs = []
    done = []

    def say(msg, kind="info"):
        if log_cb:
            log_cb(msg, kind)

    def do_step(st, attempt):
        obj, dest = st["object"], st["on"]
        say(f"Step: put {obj} on {dest}" + (" (retry)" if attempt else ""), "step")
        _pick_place_seen(sim, eyes, obj, eyes.where(dest))
        sim.home()

    for i, st in enumerate(program["steps"]):
        if st["do"] != "stack":
            continue
        entry = {"step": i + 1, "intent": st["intent"], "checks": [], "repairs": 0}
        for attempt in range(3 if use_contracts else 1):
            if attempt:
                entry["repairs"] += 1
            try:
                do_step(st, attempt)
            except LookupError as e:
                entry["checks"].append({"pass": False, "why": str(e)})
                continue
            if disturb and disturb[0] == i:
                disturb[1](sim)
                disturb = None
                say("Someone bumps the table", "bump")
            if not use_contracts:
                entry["checks"].append({"pass": None, "why": "checks off"})
                break
            ok, ev = eyes.holds(st["contract"]["relation"])
            entry["checks"].append({"contract": " ".join(st["contract"]["relation"]), "pass": ok, **ev})
            say(f"Check: {' '.join(st['contract']['relation'])}: {'holds' if ok else 'FAILS'} {ev}", "pass" if ok else "fail")
            if ok:
                break
        entry["passed"] = bool(entry["checks"]) and entry["checks"][-1].get("pass") is not False
        logs.append(entry)
        done.append(st)
        # Before moving on, every earlier contract must still hold: a stack
        # that was knocked over has to be rebuilt from the lowest broken step.
        if use_contracts:
            for j, prev in enumerate(done[:-1]):
                ok, ev = eyes.holds(prev["contract"]["relation"])
                if not ok:
                    say(f"Earlier contract broken: {' '.join(prev['contract']['relation'])}. Rebuilding.", "fail")
                    for redo in done[j:]:
                        for attempt in range(3):
                            try:
                                do_step(redo, 1)
                            except LookupError as e:
                                say(f"Cannot see what it needs: {e}", "fail")
                                continue
                            if eyes.holds(redo["contract"]["relation"])[0]:
                                break
                    logs[-1]["repairs"] += 1
                    break

    final = []
    for st in program["steps"]:
        if st["do"] == "stack":
            ok, ev = eyes.holds(st["contract"]["relation"])
            final.append({"contract": " ".join(st["contract"]["relation"]), "pass": ok, **ev})
    agent_says = all(e.get("passed") for e in logs) if use_contracts else True
    return {"steps": logs, "final_contracts": final, "agent_says_done": agent_says}


def _pick_place_seen(sim, eyes, obj, p_dest):
    """Pick using where the cameras see the object, not the simulator's state."""
    p = eyes.where(obj)
    hover = 0.16
    sim.grip(False)
    sim.move_to([p[0], p[1], p[2] + hover], 1.0)
    sim.move_to([p[0], p[1], p[2] - 0.004], 0.7)
    sim.grip(True)
    sim.move_to([p[0], p[1], p[2] + hover], 0.8)
    dz = p_dest[2] + 2 * HALF
    sim.move_to([p_dest[0], p_dest[1], dz + hover], 1.1)
    sim.move_to([p_dest[0], p_dest[1], dz + 0.006], 0.7)
    sim.grip(False)
    sim.move_to([p_dest[0], p_dest[1], dz + hover], 0.7)


def ground_truth(sim, program) -> bool:
    """Scorer: uses the simulator's true block positions (the agent never does)."""
    for st in program["steps"]:
        if st["do"] != "stack":
            continue
        a, _, b = st["contract"]["relation"]
        pa, pb = sim.pos(a), sim.pos(b)
        if np.hypot(*(pa[:2] - pb[:2])) > HALF or abs((pa[2] - pb[2]) - 2 * HALF) > HALF * 0.5:
            return False
    return True


if __name__ == "__main__":
    import sys
    prog = learn(Path(sys.argv[1]))
    print(json.dumps(prog, indent=2))
