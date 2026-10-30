"""The physical-world runner, offline: the model calls are replaced with scripted answers."""
import asyncio

import cv2
import numpy as np
import pytest

from eidos.world import run as R
from eidos.world import session as S
from eidos.world.calibrate import calibrate

def run(coro):
    """A fresh event loop per call, independent of loops other tests leave behind."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


PROGRAM = {
    "title": "Replace a part in a cabinet",
    "inputs": {},
    "steps": [
        {"id": 1, "do": "Turn the power off", "done_when": "switch is off", "needs": []},
        {"id": 2, "do": "Open the door", "done_when": "door open", "needs": [1], "optional": True},
        {"id": 3, "do": "Remove the old part", "done_when": "slot empty", "needs": [2]},
        {"id": 4, "do": "Put the part on the shelf", "done_when": "part on shelf", "needs": [3], "optional": True},
        {"id": 5, "do": "Install the new part", "done_when": "new part seated", "needs": [3]},
    ],
}


def feed(tr, seq, t0=6.0):
    for i, d in enumerate(seq):
        tr.feed(t0 + 3 * i, d)


def alerts(tr):
    return [(e["type"], e["step"]) for e in tr.events if e["kind"] == "alert"]


def test_in_order_raises_nothing():
    tr = R.Tracker(PROGRAM)
    feed(tr, [0, 1, 1, 2, 2, 3, 3, 0, 4, 4, 5, 5, 0])
    tr.finish(60)
    assert alerts(tr) == []
    assert set(tr.started) == {1, 2, 3, 4, 5}


def test_one_stray_look_does_not_start_a_step():
    tr = R.Tracker(PROGRAM)
    feed(tr, [1, 1, 5, 1, 3, 3])          # a single look at step 5 is noise
    assert 5 not in tr.started


def test_order_alert_passes_through_an_optional_step():
    """Opening the door is optional, but it needs the power off, so removing the part does too."""
    tr = R.Tracker(PROGRAM)
    feed(tr, [0, 2, 2, 3, 3])
    assert ("order", 3) in alerts(tr)
    order = next(e for e in tr.events if e["kind"] == "alert")
    assert order["before"] == [1]


def test_optional_steps_never_raise_alerts():
    tr = R.Tracker(PROGRAM)
    feed(tr, [1, 1, 4, 4, 3, 3, 5, 5])   # the shelf step out of place: it is optional
    tr.finish(40)
    assert alerts(tr) == []


def test_skipped_required_step_is_reported_at_the_end():
    tr = R.Tracker(PROGRAM)
    feed(tr, [1, 1, 3, 3])
    tr.finish(30)
    assert ("missing", 5) in alerts(tr)
    assert ("missing", 4) not in alerts(tr)


def test_next_steps_follow_the_dependencies():
    tr = R.Tracker(PROGRAM)
    assert tr.next_steps() == [1]
    feed(tr, [1, 1])
    assert 3 in tr.next_steps() and 5 not in tr.next_steps()   # 3 needs only 1, through optional 2


def frames(n):
    return [(float(i), np.zeros((252, 448, 3), np.uint8)) for i in range(n)]


def scripted(seq):
    async def look(program, window, inputs=None, which="spark"):
        t = window[-1][0]
        return {"doing": seq.get(int(t), 0), "what": "scripted"}
    return look


def test_calibration_learns_what_is_essential(monkeypatch):
    """A second correct demonstration that never puts the part on a shelf and does 5 before 3:
    the shelf step stays optional, step 5 loses its need for step 3 only if 3 came later."""
    import copy
    prog = copy.deepcopy(PROGRAM)
    prog["steps"][4]["needs"] = [3]
    seq = {t: d for t, d in zip(range(6, 60, 3), [1, 1, 2, 2, 5, 5, 3, 3, 0, 0])}
    monkeypatch.setattr(R, "look", scripted(seq))

    async def never(*a, **k):
        return {"ok": True, "why": "fine"}
    monkeypatch.setattr(R, "check", never)

    async def found(*a, **k):
        return {"done": True, "why": "seen"}
    monkeypatch.setattr(R, "search", found)
    out, _ = run(calibrate(prog, {}, frames(60)))
    s5 = next(s for s in out["steps"] if s["id"] == 5)
    assert s5["needs"] == []
    assert any(c["change"].startswith("no longer needs") for c in out["calibration"]["changes"])


def test_replay_search_back_dismisses_a_missed_step(monkeypatch):
    seq = {t: d for t, d in zip(range(6, 60, 3), [0, 0, 3, 3, 5, 5, 0])}   # step 1 never recognised
    monkeypatch.setattr(R, "look", scripted(seq))

    async def found(program, step, frames, inputs=None):
        return {"done": True if step["id"] == 1 else False, "why": "searched"}
    monkeypatch.setattr(R, "search", found)
    res = run(R.replay(PROGRAM, {}, frames(30), contracts=False))
    assert not [a for a in res["alerts"] if a["step"] == 3 and a["type"] == "order"]
    assert res["dismissed"]


def test_replay_keeps_an_alert_the_search_cannot_settle(monkeypatch):
    seq = {t: d for t, d in zip(range(6, 60, 3), [0, 0, 3, 3, 5, 5, 0])}
    monkeypatch.setattr(R, "look", scripted(seq))

    async def unsure(program, step, frames, inputs=None):
        return {"done": None, "why": "cannot tell"}
    monkeypatch.setattr(R, "search", unsure)
    res = run(R.replay(PROGRAM, {}, frames(30), contracts=False))
    assert ("order", 3) in [(a["type"], a["step"]) for a in res["alerts"]]


def test_live_session_feeds_looks_in_time_order(monkeypatch, tmp_path):
    """Looks finish out of order (later ones faster); the tracker must still see them in order."""
    seq = {6: 1, 9: 1, 12: 3, 15: 3, 18: 5, 21: 5}

    async def look(program, window, inputs=None, which="spark"):
        t = window[-1][0]
        await asyncio.sleep(0.05 if t > 10 else 0.2)
        return {"doing": seq.get(int(t), 0), "what": "scripted"}
    monkeypatch.setattr(R, "look", look)

    async def ok(*a, **k):
        return {"ok": True, "why": "fine"}
    monkeypatch.setattr(R, "check", ok)

    async def go():
        s = S.LiveSession("t", tmp_path, PROGRAM)
        q = asyncio.Queue()
        s.listeners.append(q)
        jpeg = cv2.imencode(".jpg", np.zeros((252, 448, 3), np.uint8))[1].tobytes()
        for t in range(0, 25):
            s.add_frame(float(t), jpeg)
        await asyncio.sleep(0.5)
        out = await s.finish()
        looks = []
        while not q.empty():
            ev = q.get_nowait()
            if ev["kind"] == "look":
                looks.append(ev["t"])
        return out, looks

    out, looks = run(go())
    assert looks == sorted(looks)
    assert out["seen"] == [1, 3, 5]
