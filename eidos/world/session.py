"""A live session: frames arrive from a camera (or a video playing in the browser), and EIDOS
follows along in real time.

Frames come in about once a second. Every few seconds a look is started on the last few
seconds of frames. Looks run in parallel (each takes a few seconds), but their answers are fed
to the tracker strictly in time order, so the session behaves exactly like the benchmark
replay. When a required step ends, its contract is checked against the demonstration.
Everything that happens is pushed to listeners as events.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from . import run as R
from .learn import bind

MAX_SESSIONS = 4
IDLE_LIMIT = 20 * 60


class LiveSession:
    def __init__(self, sid: str, skill_dir: Path, program: dict, inputs: dict | None = None, reader: str = "spark"):
        self.id = sid
        self.reader = reader if reader in ("spark", "open") else "spark"
        self.program = program
        self.inputs = {**program.get("inputs", {}), **(inputs or {})}
        self.refs = R.load_refs(skill_dir, program)
        self.tracker = R.Tracker(program)
        self.frames: deque = deque(maxlen=60)            # (t, image), about a minute
        self.history: list = []                          # (t, small image) every 2 s, for searching back
        self.confirming: set = set()
        self.seen_at: list = []                          # (look time, step) for every look that saw a step
        self.pending: deque = deque()                    # look tasks, in time order
        self.next_look = R.LOOK
        self.listeners: list[asyncio.Queue] = []
        self.log: list[dict] = []
        self.checks: dict[int, dict] = {}
        self.finished = False
        self.last_seen = time.monotonic()
        self.started_at = time.monotonic()
        self._feeder: asyncio.Task | None = None

    # ---------------------------------------------------------------- events
    def emit(self, kind: str, data: dict):
        ev = {"kind": kind, **data}
        self.log.append(ev)
        for q in list(self.listeners):
            q.put_nowait(ev)

    def state(self) -> dict:
        tr = self.tracker
        steps = []
        for s in self.program["steps"]:
            sid = s["id"]
            st = "waiting"
            if sid in tr.started:
                st = "doing" if tr.current == sid else "done"
            c = self.checks.get(sid)
            steps.append({"id": sid, "do": bind(s["do"], self.inputs), "state": st,
                          "optional": bool(s.get("optional")), "check": c})
        return {"steps": steps, "current": tr.current, "next": tr.next_steps()[:3],
                "alerts": [e for e in tr.events if e["kind"] == "alert"]}

    # ---------------------------------------------------------------- frames
    def add_frame(self, t: float, jpeg: bytes):
        self.last_seen = time.monotonic()
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None or self.finished:
            return
        h, w = img.shape[:2]
        if w != 448:
            img = cv2.resize(img, (448, int(h * 448 / w)), interpolation=cv2.INTER_AREA)
        if self.frames and t <= self.frames[-1][0]:
            return
        self.frames.append((t, img))
        if not self.history or t - self.history[-1][0] >= 2:
            self.history.append((t, cv2.resize(img, (320, int(img.shape[0] * 320 / img.shape[1])))))
        while t >= self.next_look:
            win = [(ti, f) for ti, f in self.frames if self.next_look - R.LOOK < ti <= self.next_look]
            if len(win) >= 2:
                task = asyncio.create_task(R.look(self.program, win, self.inputs, self.reader))
                self.pending.append((self.next_look, win, task))
            self.next_look += R.EVERY
        if self._feeder is None or self._feeder.done():
            self._feeder = asyncio.create_task(self._feed())

    async def _feed(self):
        while self.pending:
            t, win, task = self.pending[0]
            lk = await task
            self.pending.popleft()
            self.emit("look", {"t": t, **lk})
            if lk["doing"]:
                self.seen_at.append((t, lk["doing"]))
            for ev in self.tracker.feed(t, lk["doing"]):
                self._on_event(ev)

    def _on_event(self, ev: dict):
        if ev["kind"] == "alert" and ev["type"] in ("order", "missing"):
            ev["kind"] = "checking"          # search back before saying it
            task = asyncio.create_task(self._confirm(ev))
            self.confirming.add(task)
            task.add_done_callback(self.confirming.discard)
            return
        self.emit("event", ev)
        if ev["kind"] == "end" and ev["step"] not in self.checks and R.checkable(self.tracker.by_id[ev["step"]]):
            self.checks[ev["step"]] = {"pending": True}
            asyncio.create_task(self._check(ev["step"], ev["t"]))
        self.emit("state", self.state())

    async def _confirm(self, ev: dict):
        stands, found = await R.confirm(self.program, ev, list(self.history), self.inputs)
        ev["searched"] = found
        if stands:
            ev["kind"] = "alert"
            self.emit("event", ev)
        else:
            ev["kind"] = "dismissed"
            for f in found:
                if f["done"] and f["step"] not in self.tracker.started:
                    self.tracker.started[f["step"]] = ev["t"]
            self.emit("dismissed", {"t": ev["t"], "text": ev["text"], "why": "; ".join(f["why"] for f in found)})
        self.emit("state", self.state())

    def _between(self, t0: float, t1: float) -> list:
        return [f for ti, f in self.frames if t0 <= ti <= t1]

    async def _wait_until(self, t: float):
        while not self.finished and (not self.frames or self.frames[-1][0] < t):
            await asyncio.sleep(0.5)

    async def _check(self, step_id: int, t: float):
        step = self.tracker.by_id[step_id]
        t_view = max([lt for lt, sid in self.seen_at if sid == step_id], default=t)

        async def between(t0, t1):
            await self._wait_until(t1)
            return self._between(t0, t1)

        first = R.pick(await between(t_view - 1, t_view) + await between(t, t + 3), 4)
        res = await R.check(self.program, step, self.refs.get(step_id), first, self.inputs)
        if res["ok"] is False:
            second = R.pick(await between(t + 6, t + 12), 3)
            res = (await R.check(self.program, step, self.refs.get(step_id), second, self.inputs)) if second else \
                {**res, "ok": None, "why": "not confirmed: " + res["why"]}
        self.checks[step_id] = res
        self.emit("check", {"t": t, "step": step_id, **res})
        if res["ok"] is False and not res.get("failed"):
            alert = {"t": self.frames[-1][0] if self.frames else t, "kind": "alert", "type": "contract", "step": step_id,
                     "text": f"Check failed on step {step_id} ({step['do']}): {res['why']}"}
            self.tracker.events.append(alert)
            self.emit("event", alert)
        self.emit("state", self.state())

    async def finish(self) -> dict:
        if self.finished:
            return self.summary()
        self.finished = True
        while self.pending:
            await asyncio.sleep(0.2)
        if self._feeder:
            await self._feeder
        t = self.frames[-1][0] if self.frames else 0
        for ev in self.tracker.finish(t):
            self._on_event(ev)
        for _ in range(90):                      # let running checks and searches land
            if not any(c.get("pending") for c in self.checks.values()) and not self.confirming:
                break
            await asyncio.sleep(0.5)
        s = self.summary()
        self.emit("state", self.state())
        self.emit("finished", s)
        return s

    def summary(self) -> dict:
        alerts = [e for e in self.tracker.events if e["kind"] == "alert"]
        return {"alerts": alerts, "verdict": "mistakes" if alerts else "followed",
                "seen": sorted(self.tracker.started), "steps": len(self.program["steps"])}


SESSIONS: dict[str, LiveSession] = {}


def reap():
    now = time.monotonic()
    for k, s in list(SESSIONS.items()):
        if now - s.last_seen > IDLE_LIMIT:
            SESSIONS.pop(k, None)
