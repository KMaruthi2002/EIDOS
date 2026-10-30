"""Run a learned task program live, from a camera feed or a video played in real time.

Every few seconds the runner looks at the last few seconds of frames and asks Muse Spark which
step of the program is happening (or none). Each look is independent of the others, so a
wrong look cannot derail the ones after it; a small state machine smooths the looks into
step starts and ends. From those it raises alerts the moment they become true:

- order: a step starts before a step it needs has been seen;
- contract: a step has ended, and the result on camera does not match its visual contract,
  checked against the frame where the demonstration finished the same step;
- missing: when the run is finished, a required step was never seen.

Nothing here uses frames from the future: every decision at time t uses frames up to t, and
alerts are stamped with the time the model answered.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2

from .. import live
from .learn import FAST, _json, bind

LOOK = 6            # frames per look (one per second)
EVERY = 3.0         # seconds between looks

LOOK_PROMPT = """A person is doing this task live: {title}.
The steps:
{steps}

These {n} frames are the last {n} seconds from the live camera, oldest first.
Which one step is the person working on right now? Use 0 if they are doing none of these steps (moving around, fetching things, idle, or something else).
Reply only with JSON: {{"doing": step number or 0, "what": "what they are doing, in a few words"}}"""

CHECK_PROMPT = """A person has just finished a step of a task: {title}.
Step: {do}
The demonstration's result: {done_when}

The first image is the demonstration video at the moment this step was finished, done correctly.
The other images are the live camera after the person finished the same step.

Did the person achieve what this step is for? Judge the purpose of the step, not how the demonstrator happened to arrange things: where an item was set down, what it rests on, which hand, the order of the camera's view, or their own kind of plate, mug, tool, brand or colour do not matter. Ignore later steps not done yet, and differences of place, lighting and angle.
Answer false only when the live images clearly show the step's purpose was not achieved or was done wrong: a wrong item, a clearly wrong amount, a result that is clearly undone or badly done.
If the result is not clearly visible (out of view, blocked by hands, too small to see, blurred), answer null rather than guessing.
Reply only with JSON: {{"ok": true, false, or null, "why": "one short sentence"}}"""


def step_list(program: dict, inputs: dict | None = None) -> str:
    inputs = {**program.get("inputs", {}), **(inputs or {})}
    return "\n".join(f"{s['id']}. {bind(s['do'], inputs)}" for s in program["steps"])


async def look(program: dict, window: list[tuple[float, object]], inputs=None, which: str = "spark") -> dict:
    prompt = LOOK_PROMPT.format(title=program.get("title", "task"), steps=step_list(program, inputs), n=len(window))
    for attempt in range(3):
        try:
            if which == "open":
                content = [{"type": "image_url", "image_url": {"url": live.data_url(f, 70)}} for _, f in window]
                content.append({"type": "text", "text": prompt})
                text = await live.baseten_chat(content, "live look", temperature=0)
            else:
                content = [{"type": "input_image", "image_url": live.data_url(f, 70)} for _, f in window]
                content.append({"type": "input_text", "text": prompt})
                text = live.output_text(await live.meta_responses(live.MODELS["spark"], content, "live look", **FAST))
            j = _json(text)
            if isinstance(j, dict):
                d = j.get("doing", 0)
                try:
                    d = int(d)
                except (TypeError, ValueError):
                    d = 0
                ids = {s["id"] for s in program["steps"]}
                return {"doing": d if d in ids else 0, "what": str(j.get("what", ""))[:120]}
        except Exception:
            await asyncio.sleep(1.5 + 2 * attempt)
    return {"doing": 0, "what": "", "failed": True}


async def check(program: dict, step: dict, ref_img, live_frames: list, inputs=None) -> dict:
    inputs = {**program.get("inputs", {}), **(inputs or {})}
    prompt = CHECK_PROMPT.format(title=program.get("title", "task"), do=bind(step["do"], inputs),
                                 done_when=bind(step["done_when"], inputs))
    content = []
    if ref_img is not None:
        content.append({"type": "input_image", "image_url": live.data_url(ref_img, 75)})
    content += [{"type": "input_image", "image_url": live.data_url(f, 75)} for f in live_frames]
    content.append({"type": "input_text", "text": prompt})
    for attempt in range(3):
        try:
            r = await live.meta_responses(live.MODELS["spark"], content, "check contract", reasoning={"effort": "low"})
            j = _json(live.output_text(r))
            if isinstance(j, dict) and "ok" in j:
                v = j["ok"]
                ok = v if isinstance(v, bool) or v is None else {"true": True, "false": False}.get(str(v).lower())
                return {"ok": ok, "why": str(j.get("why", ""))[:200]}
        except Exception:
            await asyncio.sleep(1.5 + 2 * attempt)
    return {"ok": True, "why": "check unavailable", "failed": True}


SEARCH_PROMPT = """A person is doing this task: {title}.
These {n} frames are spread over the last {mins} of the live camera, oldest first.
Did the person do this step at any point in these frames: "{do}"?
It counts if you can see it being done, or see its result ({done_when}) appear.
Reply only with JSON: {{"done": true, false, or null if you cannot tell, "why": "one short sentence"}}"""


async def search(program: dict, step: dict, frames: list, inputs=None) -> dict:
    """Before saying a step was skipped, look back over everything so far for it, the way a
    person would rewind before accusing someone. Only a clear "yes, it was done" dismisses the alert."""
    inputs = {**program.get("inputs", {}), **(inputs or {})}
    fr = pick(frames, 16)
    if not fr:
        return {"done": None, "why": "no frames"}
    span = (frames[-1][0] - frames[0][0]) if isinstance(frames[0], tuple) else 0
    imgs = [f for _, f in fr] if isinstance(fr[0], tuple) else fr
    mins = f"{max(1, round(span / 60))} minute{'s' if round(span / 60) > 1 else ''}" if span else "few minutes"
    prompt = SEARCH_PROMPT.format(title=program.get("title", "task"), n=len(imgs), mins=mins,
                                  do=bind(step["do"], inputs), done_when=bind(step["done_when"], inputs))
    content = [{"type": "input_image", "image_url": live.data_url(f, 65)} for f in imgs]
    content.append({"type": "input_text", "text": prompt})
    for attempt in range(3):
        try:
            r = await live.meta_responses(live.MODELS["spark"], content, "search back", reasoning={"effort": "low"})
            j = _json(live.output_text(r))
            if isinstance(j, dict) and "done" in j:
                v = j["done"]
                done = v if isinstance(v, bool) or v is None else {"true": True, "false": False}.get(str(v).lower())
                return {"done": done, "why": str(j.get("why", ""))[:200]}
        except Exception:
            await asyncio.sleep(1.5 + 2 * attempt)
    return {"done": None, "why": "search unavailable", "failed": True}


async def confirm(program: dict, alert: dict, frames: list, inputs=None) -> tuple[bool, list]:
    """True if the alert stands after searching back. Order alerts are checked per missing step."""
    by_id = {s["id"]: s for s in program["steps"]}
    upto = [x for x in frames if x[0] <= alert["t"]]
    targets = alert["before"] if alert["type"] == "order" else [alert["step"]]
    found = []
    for n in targets:
        r = await search(program, by_id[n], upto, inputs)
        found.append({"step": n, **r})
    # the alert stands unless the search clearly finds every missing step was done after all;
    # "cannot tell" does not dismiss it (on the dev recipes that only ever hid real mistakes)
    return not all(f["done"] is True for f in found), found


@dataclass
class Tracker:
    """Turns looks into step starts and ends, and raises order and missing-step alerts."""
    program: dict
    votes: int = 2                     # a step is on once it wins this many of the last 3 looks
    history: list = field(default_factory=list)
    current: int = 0
    started: dict = field(default_factory=dict)     # step id -> time first seen
    ended: dict = field(default_factory=dict)       # step id -> time last left
    events: list = field(default_factory=list)

    def __post_init__(self):
        self.by_id = {s["id"]: s for s in self.program["steps"]}

    def required(self, sid: int) -> bool:
        return not self.by_id[sid].get("optional", False)

    def needs(self, sid: int, seen=None) -> set:
        """Required steps that must come before this one. An optional step passes its own needs
        on: if opening a door is optional but needs the power off, whatever needs the door open
        still needs the power off."""
        seen = seen if seen is not None else set()
        out = set()
        for n in self.by_id[sid].get("needs", []):
            if n in seen or n not in self.by_id:
                continue
            seen.add(n)
            out |= {n} if self.required(n) else self.needs(n, seen)
        return out

    def feed(self, t: float, doing: int) -> list[dict]:
        """One look at time t. Returns the events it caused."""
        self.history.append(doing)
        last = self.history[-3:]
        winner = max(set(last), key=last.count)
        new = []
        if winner != self.current and last.count(winner) >= min(self.votes, len(last)):
            if self.current:
                self.ended[self.current] = t
                new.append({"t": t, "kind": "end", "step": self.current})
            self.current = winner
            if winner:
                first = winner not in self.started
                self.started.setdefault(winner, t)
                new.append({"t": t, "kind": "start", "step": winner, "first": first})
                if first and self.required(winner):
                    gaps = sorted(n for n in self.needs(winner) if n not in self.started)
                    if gaps:
                        need = " and ".join(f"step {n} ({self.by_id[n]['do']})" for n in gaps)
                        new.append({"t": t, "kind": "alert", "type": "order", "step": winner, "before": gaps,
                                    "text": f"Out of order: step {winner} ({self.by_id[winner]['do']}) started before {need}."})
        self.events += new
        return new

    def finish(self, t: float) -> list[dict]:
        new = []
        if self.current:
            self.ended[self.current] = t
            new.append({"t": t, "kind": "end", "step": self.current})
            self.current = 0
        for s in self.program["steps"]:
            if s["id"] not in self.started and self.required(s["id"]):
                new.append({"t": t, "kind": "alert", "type": "missing", "step": s["id"],
                            "text": f"Skipped: step {s['id']} ({s['do']}) was never seen."})
        self.events += new
        return new

    def next_steps(self) -> list[int]:
        """Steps whose needs are all seen and that have not started: what to do next."""
        return [s["id"] for s in self.program["steps"]
                if s["id"] not in self.started and all(n in self.started for n in self.needs(s["id"]))]


def checkable(step: dict) -> bool:
    return not step.get("optional") and step.get("check", True) is not False


def pick(fr: list, n: int) -> list:
    if len(fr) <= n:
        return fr
    return [fr[round(i * (len(fr) - 1) / (n - 1))] for i in range(n)]


async def verdict(program: dict, step: dict, ref, frames_between, t_end: float, t_view: float, inputs=None) -> dict:
    """Check a finished step's contract, the way a careful person would.

    First look: the last moment the step was in view plus the few seconds after it ended.
    A failure is only reported if a second look a little later (when the work has usually
    settled and the hands have moved away) fails too. If either look cannot see enough,
    nothing is reported."""
    first = pick(frames_between(t_view - 1, t_view) + frames_between(t_end, t_end + 3), 4)
    r1 = await check(program, step, ref, first, inputs)
    if r1["ok"] is not False:
        return {**r1, "t_alert": t_end + 3, "looks": 1}
    second = pick(frames_between(t_end + 6, t_end + 12), 3)
    if not second:
        return {**r1, "ok": None, "why": "not confirmed: " + r1["why"], "t_alert": t_end + 3, "looks": 1}
    r2 = await check(program, step, ref, second, inputs)
    if r2["ok"] is False:
        return {**r2, "t_alert": t_end + 12, "looks": 2, "first": r1["why"]}
    return {**r2, "t_alert": t_end + 12, "looks": 2, "first": r1["why"]}


def load_refs(skill_dir: Path, program: dict) -> dict:
    refs = {}
    for s in program["steps"]:
        name = (s.get("evidence") or {}).get("end")
        if name and (skill_dir / "evidence" / name).exists():
            img = cv2.imread(str(skill_dir / "evidence" / name))
            h, w = img.shape[:2]
            refs[s["id"]] = cv2.resize(img, (448, int(h * 448 / w)))
    return refs


async def replay(program: dict, refs: dict, frames: list[tuple[float, object]], contracts: bool = True,
                 concurrency: int = 8, inputs=None, which: str = "spark", looks: list | None = None,
                 verify: bool = True) -> dict:
    """Run on a recording as if live: look k at time t sees only frames up to t.

    The looks are independent, so they are computed in parallel and then fed to the tracker
    in time order, exactly as a live session would see them."""
    sem = asyncio.Semaphore(concurrency)
    times = [t for t, _ in frames]
    jobs = []
    t = LOOK
    while t <= (times[-1] if times else 0) + 0.01:
        win = [(ti, f) for ti, f in frames if t - LOOK < ti <= t]
        if win:
            jobs.append((t, win))
        t += EVERY

    async def one(t, win):
        async with sem:
            return t, await look(program, win, inputs, which)

    if looks is not None:          # looks computed earlier for the same steps (they do not depend on anything else)
        looks = [(lk["t"], {k: v for k, v in lk.items() if k != "t"}) for lk in looks]
    else:
        looks = sorted(await asyncio.gather(*(one(t, w) for t, w in jobs)), key=lambda x: x[0])
    tr = Tracker(program)
    for t, lk in looks:
        tr.feed(t, lk["doing"])
    tr.finish(times[-1] if times else 0)

    if verify:
        candidates = [e for e in tr.events if e["kind"] == "alert" and e["type"] in ("order", "missing")]

        async def conf(e):
            async with sem:
                return e, await confirm(program, e, frames, inputs)
        for e, (stands, found) in await asyncio.gather(*(conf(e) for e in candidates)):
            e["searched"] = found
            if not stands:
                e["kind"] = "dismissed"

    checks = []
    if contracts:
        last_seen = {}
        for t, lk in looks:
            if lk["doing"]:
                last_seen[lk["doing"]] = t
        at = lambda t0, t1: [f for ti, f in frames if t0 <= ti <= t1]

        async def chk(ev):
            sid = ev["step"]
            async with sem:
                res = await verdict(program, tr.by_id[sid], refs.get(sid), at, ev["t"], last_seen.get(sid, ev["t"]), inputs)
            return {"t": ev["t"], "step": sid, **res}
        seen = set()
        ends = []
        for ev in tr.events:
            if ev["kind"] == "end" and ev["step"] not in seen and checkable(tr.by_id[ev["step"]]):
                seen.add(ev["step"])
                ends.append(ev)
        checks = await asyncio.gather(*(chk(e) for e in ends))
        for c in checks:
            if c["ok"] is False and not c.get("failed"):
                tr.events.append({"t": c["t_alert"], "kind": "alert", "type": "contract", "step": c["step"],
                                  "text": f"Check failed on step {c['step']} ({tr.by_id[c['step']]['do']}): {c['why']}"})
    tr.events.sort(key=lambda e: e["t"])
    return {"looks": [{"t": t, **lk} for t, lk in looks], "events": tr.events, "checks": checks,
            "dismissed": [e for e in tr.events if e["kind"] == "dismissed"],
            "alerts": [e for e in tr.events if e["kind"] == "alert"], "started": tr.started}
