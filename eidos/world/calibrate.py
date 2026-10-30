"""Show it again: calibrate a learned program on a second correct demonstration.

One video cannot tell EIDOS which of the demonstrator's habits matter. A second correct
demonstration (another person, another place) can: the program is run on it exactly as it
would run live, and

- a step the second demonstration never shows becomes optional (a habit, not a requirement);
- a dependency the second demonstration does not respect is dropped (an order that happened
  to be used, not one the task needs);
- a contract that fails on a correct demonstration is switched off (it cannot be judged
  reliably from a camera, so it would only raise false alarms).

What changed and why is recorded in the program, so it can be shown and undone.
"""
from __future__ import annotations

from . import run as R


async def calibrate(program: dict, refs: dict, frames: list, source: str = "second demonstration",
                    concurrency: int = 8, looks: list | None = None) -> tuple[dict, dict]:
    res = await R.replay(program, refs, frames, contracts=True, concurrency=concurrency, looks=looks)
    started = res["started"]
    changes = []
    by_id = {s["id"]: s for s in program["steps"]}
    for s in program["steps"]:
        if s.get("optional"):
            continue
        if s["id"] not in started:
            s["optional"] = True
            s["why_optional"] = f"not seen in the {source}"
            changes.append({"step": s["id"], "change": "optional", "why": s["why_optional"]})
    for s in program["steps"]:
        keep = []
        for n in s.get("needs", []):
            if s["id"] in started and (n not in started or started[n] > started[s["id"]]) and not by_id[n].get("optional"):
                changes.append({"step": s["id"], "change": f"no longer needs step {n}",
                                "why": f"the {source} did step {s['id']} first"})
                continue
            keep.append(n)
        s["needs"] = keep
    for c in res["checks"]:
        if c["ok"] is False:
            by_id[c["step"]]["check"] = False
            changes.append({"step": c["step"], "change": "contract not checked",
                            "why": f"it failed on the {source}, which was done correctly: {c['why']}"})
    program["calibration"] = {"source": source, "changes": changes}
    return program, res
