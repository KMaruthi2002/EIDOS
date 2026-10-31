"""Version 3 of live tracking: ranked looks and evidence, instead of single answers and votes.

Measured on 300 labelled moments from ten recipes (bench/look_lab.py), a look that sees the last
20 seconds and gives its three best guesses with likelihoods names the right step first 66% of
the time and among its three 84% of the time, against 50% for round 1's single answer over 6
seconds, which also answered "none of these steps" in 31% of moments inside a step.

So each look is treated as soft evidence. Every step keeps a running total of how likely the
looks found it. A step counts as done once its total passes `seen` (about one confident look,
or several partial ones). An out-of-order alert is a candidate only when a step is confirmed
while a required step it needs has almost no evidence at all (below `absent`); a skipped-step
alert, when the run ends with a required step under `seen`. Every candidate is then searched
for over everything seen so far (run.confirm) before it is raised. Nothing uses the future.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .. import live
from .learn import FAST, _json
from . import run as R

SPAN = 20          # seconds of frames per look (one per second)
EVERY = 3.0

RANKED_PROMPT = """A person is doing this task live: {title}.
The steps:
{steps}

These {n} frames are the last {n} seconds from the live camera, oldest first.
Which step is the person working on right now? Give your best three guesses with how likely each is, most likely first. Use 0 for "none of these steps" (moving around, fetching things, idle, something else).
Reply only with JSON: {{"guesses": [{{"step": number, "p": 0.0 to 1.0}}, ...], "what": "what they are doing, in a few words"}}"""


async def look_ranked(program: dict, window: list, inputs=None, which: str = "spark") -> dict:
    prompt = RANKED_PROMPT.format(title=program.get("title", "task"), steps=R.step_list(program, inputs), n=len(window))
    ids = {s["id"] for s in program["steps"]}
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
            if not isinstance(j, dict):
                continue
            dist: dict[int, float] = {}
            for g in j.get("guesses", []) or []:
                if not isinstance(g, dict):
                    continue
                try:
                    s, p = int(g.get("step", 0)), float(g.get("p", 0) or 0)
                except (TypeError, ValueError):
                    continue
                s = s if s in ids else 0
                dist[s] = dist.get(s, 0.0) + max(0.0, min(1.0, p))
            tot = sum(dist.values())
            if tot > 1.0:
                dist = {k: v / tot for k, v in dist.items()}
            top = max(dist, key=dist.get) if dist else 0
            return {"doing": top, "dist": {str(k): round(v, 3) for k, v in dist.items()}, "what": str(j.get("what", ""))[:120]}
        except Exception:
            await asyncio.sleep(1.5 + 2 * attempt)
    return {"doing": 0, "dist": {}, "what": "", "failed": True}


@dataclass
class EvidenceTracker:
    program: dict
    seen_at: float = 0.9          # evidence that confirms a step was done
    absent: float = 0.35          # below this, a needed step has essentially not been seen
    min_p: float = 0.0            # a look's likelihood for a step counts as evidence only from this up
    evidence: dict = field(default_factory=dict)
    started: dict = field(default_factory=dict)     # step -> time of its first real sign (p >= 0.3)
    confirmed: dict = field(default_factory=dict)   # step -> time its evidence passed seen_at
    current: int = 0
    events: list = field(default_factory=list)

    def __post_init__(self):
        self.by_id = {s["id"]: s for s in self.program["steps"]}
        self._votes = R.Tracker(self.program)      # only for needs() and required()

    def required(self, sid: int) -> bool:
        return self._votes.required(sid)

    def needs(self, sid: int) -> set:
        return self._votes.needs(sid)

    def feed(self, t: float, look: dict) -> list[dict]:
        dist = {int(k): v for k, v in (look.get("dist") or {}).items()}
        if not dist and look.get("doing"):
            dist = {int(look["doing"]): 1.0}
        new = []
        for s, p in dist.items():
            if not s:
                continue
            if p >= self.min_p:
                self.evidence[s] = self.evidence.get(s, 0.0) + p
            if p >= 0.3:
                self.started.setdefault(s, t)
        # current step: the most likely one in this look, if it is likely enough
        top = max(dist, key=dist.get) if dist else 0
        cur = top if top and dist[top] >= 0.4 else 0
        if cur != self.current:
            if self.current:
                new.append({"t": t, "kind": "end", "step": self.current})
            if cur:
                new.append({"t": t, "kind": "start", "step": cur, "first": cur not in self.started or self.started[cur] == t})
            self.current = cur
        for s in sorted(dist):
            if s and s not in self.confirmed and self.evidence.get(s, 0) >= self.seen_at:
                self.confirmed[s] = t
                self.started.setdefault(s, t)
                if self.required(s):
                    gaps = sorted(n for n in self.needs(s) if self.evidence.get(n, 0) < self.absent)
                    if gaps:
                        need = " and ".join(f"step {n} ({self.by_id[n]['do']})" for n in gaps)
                        new.append({"t": t, "kind": "alert", "type": "order", "step": s, "before": gaps,
                                    "text": f"Out of order: step {s} ({self.by_id[s]['do']}) started before {need}."})
        self.events += new
        return new

    def finish(self, t: float) -> list[dict]:
        new = []
        if self.current:
            new.append({"t": t, "kind": "end", "step": self.current})
            self.current = 0
        for s in self.program["steps"]:
            if self.required(s["id"]) and self.evidence.get(s["id"], 0) < self.seen_at:
                new.append({"t": t, "kind": "alert", "type": "missing", "step": s["id"],
                            "text": f"Skipped: step {s['id']} ({s['do']}) was never seen."})
        self.events += new
        return new

    def next_steps(self) -> list[int]:
        done = set(self.confirmed)
        return [s["id"] for s in self.program["steps"] if s["id"] not in done and all(n in done for n in self.needs(s["id"]))]


async def replay(program: dict, refs: dict, frames: list, concurrency: int = 10, inputs=None, which: str = "spark",
                 looks: list | None = None, contracts: bool = True, verify: bool = True,
                 seen_at: float = 0.9, absent: float = 0.35) -> dict:
    """Run on a recording as if live, with ranked looks and the evidence tracker. Failed visual
    checks are notes, not alarms (in round 1 they fired as often on correct recordings)."""
    sem = asyncio.Semaphore(concurrency)
    times = [t for t, _ in frames]
    if looks is None:
        jobs, t = [], float(R.LOOK)
        while t <= (times[-1] if times else 0) + 0.01:
            win = [(ti, f) for ti, f in frames if t - SPAN < ti <= t]
            if len(win) >= 2:
                jobs.append((t, win))
            t += EVERY

        async def one(t, win):
            async with sem:
                return {"t": t, **(await look_ranked(program, win, inputs, which))}
        looks = sorted(await asyncio.gather(*(one(t, w) for t, w in jobs)), key=lambda x: x["t"])
    tr = EvidenceTracker(program, seen_at=seen_at, absent=absent)
    for lk in looks:
        tr.feed(lk["t"], lk)
    tr.finish(times[-1] if times else 0)

    if verify:
        cands = [e for e in tr.events if e["kind"] == "alert" and e["type"] in ("order", "missing")]

        async def conf(e):
            async with sem:
                return e, await R.confirm(program, e, frames, inputs)
        for e, (stands, found) in await asyncio.gather(*(conf(e) for e in cands)):
            e["searched"] = found
            if not stands:
                e["kind"] = "dismissed"

    checks = []
    if contracts:
        last_seen = {}
        for lk in looks:
            if lk.get("doing"):
                last_seen[lk["doing"]] = lk["t"]
        at = lambda t0, t1: [f for ti, f in frames if t0 <= ti <= t1]
        ends, seen = [], set()
        for ev in tr.events:
            if ev["kind"] == "end" and ev["step"] not in seen and R.checkable(tr.by_id[ev["step"]]):
                seen.add(ev["step"])
                ends.append(ev)

        async def chk(ev):
            sid = ev["step"]
            async with sem:
                res = await R.verdict(program, tr.by_id[sid], refs.get(sid), at, ev["t"], last_seen.get(sid, ev["t"]), inputs)
            return {"t": ev["t"], "step": sid, **res}
        checks = await asyncio.gather(*(chk(e) for e in ends))
        for c in checks:
            if c["ok"] is False and not c.get("failed"):
                tr.events.append({"t": c["t_alert"], "kind": "note", "type": "contract", "step": c["step"],
                                  "text": f"Please look at step {c['step']} ({tr.by_id[c['step']]['do']}): {c['why']}"})
    tr.events.sort(key=lambda e: e["t"])
    return {"looks": looks, "events": tr.events, "checks": checks,
            "dismissed": [e for e in tr.events if e["kind"] == "dismissed"],
            "alerts": [e for e in tr.events if e["kind"] == "alert"],
            "started": tr.started, "confirmed": tr.confirmed, "evidence": tr.evidence}
