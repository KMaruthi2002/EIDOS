"""Learn a task program from one real-world demonstration video.

1. Watch: the video is read in short overlapping windows (8 frames, one per second). For each
   window Muse Spark says what the person is doing: the action, the objects and tools, any
   amount it can read or see, and what is visibly different at the end of the window.
2. Compile: the window notes, with their times, are compiled into a program (Muse Wonder, with
   Muse Spark as a fallback): steps in plain words, the objects each step uses, amounts that
   become inputs, which earlier steps each step really needs, and a visual contract for each
   step, meaning what a camera must be able to see once it is done.
3. Evidence: for every step the frames where it starts and ends are kept, so the contract can
   later be checked against what the video actually showed.

No labels or annotations are used: the only input is the video (and an optional title).
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import cv2

from .. import live
from . import frames as F

WINDOW = 8          # frames per window (one per second)
STRIDE = 4          # seconds between window starts
FAST = {"reasoning": {"effort": "minimal"}}

DESCRIBE = (
    "These {n} frames are one second apart, from a video of a person doing a hands-on task{hint}. "
    "Say what the person does in these seconds. Reply only with JSON: "
    '{{"action": "short verb phrase, or \\"none\\" if they are only moving around, fetching things or idle", '
    '"objects": ["things being worked on"], "tools": ["tools or utensils in use"], '
    '"amount": "any amount, size, count, time or setting you can read or clearly see, else null", '
    '"after": "what is visibly different at the end compared with the start"}}'
)

COMPILE = """You compile a demonstration video into a program that someone (a person, or later a robot) can follow, and that a camera can check.
Title given by the user: {title}
Below are notes on the video, one per window, with times in seconds. Notes overlap and can be noisy.

Return only JSON with this shape:
{{"title": "short name of the task",
  "domain": "one or two words, e.g. cooking, sewing, bike repair",
  "inputs": {{"name": "value"}},
  "steps": [{{"id": 1, "do": "imperative instruction, with the amount written as {{input_name}} where there is one",
             "verb": "one verb", "objects": ["..."], "tools": ["..."],
             "start": seconds, "end": seconds,
             "focus": "one or two plain words naming the thing whose state shows this step is done, for an object detector (e.g. \"handle\", \"tomato slices\", \"mug\")",
             "done_when": "what a camera can see once this step is done, specific enough to tell it apart from the step not being done or done wrongly",
             "needs": [ids of earlier steps that must physically be done before this one],
             "optional": true if the step only sets up or tidies (fetching, unpacking, opening a container, putting away) and the result does not depend on it, else false}}]}}

Rules:
- Steps are at the level a careful person would write instructions: one meaningful change to the work per step. Leave out walking, fetching and idle moments unless they change the work.
- Merge notes that describe the same step. Use the times of the notes for start and end.
- "inputs" holds amounts, sizes, counts, durations and settings that someone might want to change (for example "salt": "1/4 teaspoon"). Use names in snake_case.
- "needs" lists only real dependencies (you cannot place slices before slicing), not steps that merely happened earlier in this video.
- Write "do" and "done_when" so they hold for anyone doing the task with their own things: name the role of an object ("the mug", "the cutting board", "the RAM stick"), not this video's colour, brand or packaging.
- "done_when" describes the lasting change to the work itself (the state of the objects, e.g. "tomato cut into slices on the board"), never a hand pose or a moment in motion, and must be visible in a single camera frame.

NOTES:
{notes}"""


def _json(text: str):
    j = live.first_json(text)
    if j is None:
        m = re.search(r"\{.*\}", text or "", re.S)
        if m:
            try:
                j = json.loads(m.group())
            except json.JSONDecodeError:
                return None
    return j


async def describe(window: list[tuple[float, object]], hint: str, sem: asyncio.Semaphore, which: str = "spark") -> dict:
    prompt = DESCRIBE.format(n=min(len(window), live.OPEN_MAX_IMAGES) if which == "open" else len(window), hint=hint)
    async with sem:
        for attempt in range(3):
            try:
                j = _json(await live.ask([f for _, f in window], prompt, "watch window", which, effort="minimal"))
                if isinstance(j, dict):
                    return {"t0": window[0][0], "t1": window[-1][0], **j}
            except Exception:
                await asyncio.sleep(2 + 3 * attempt)
    return {"t0": window[0][0], "t1": window[-1][0], "action": "unknown"}


def windows(fr: list, size: int = WINDOW, stride: int = STRIDE) -> list[list]:
    out = []
    for i in range(0, max(1, len(fr) - size + 1), stride):
        out.append(fr[i:i + size])
    if fr and (not out or out[-1][-1][0] < fr[-1][0]):
        out.append(fr[-size:])
    return out


def notes_text(notes: list[dict]) -> str:
    lines = []
    for n in notes:
        if (n.get("action") or "none").lower() in ("none", "unknown", ""):
            lines.append(f"[{n['t0']:.0f}-{n['t1']:.0f}] (no task action)")
            continue
        bits = [f"[{n['t0']:.0f}-{n['t1']:.0f}] {n.get('action')}"]
        if n.get("objects"):
            bits.append("objects: " + ", ".join(map(str, n["objects"])))
        if n.get("tools"):
            bits.append("tools: " + ", ".join(map(str, n["tools"])))
        if n.get("amount"):
            bits.append(f"amount: {n['amount']}")
        if n.get("after"):
            bits.append(f"after: {n['after']}")
        lines.append(" | ".join(bits))
    return "\n".join(lines)


async def compile_program(notes: list[dict], title: str, which: str = "spark") -> dict:
    prompt = COMPILE.format(title=title or "(none)", notes=notes_text(notes))
    if which == "open":            # no Meta key: Muse Spark Open compiles
        for attempt in range(3):
            try:
                j = _json(await live.baseten_chat([{"type": "text", "text": prompt}], "compile program", temperature=0))
                if isinstance(j, dict) and j.get("steps"):
                    j["compiled_by"] = live.MODELS["open"]
                    return j
            except Exception:
                await asyncio.sleep(3 + 3 * attempt)
        raise RuntimeError("could not compile a program from the notes")
    for model, extra in ((live.MODELS["wonder"], {"reasoning": {"effort": "medium"}}),
                         (live.MODELS["spark"], {"reasoning": {"effort": "medium"}})):
        try:
            r = await live.meta_responses(model, [{"type": "input_text", "text": prompt}], "compile program", **extra)
            j = _json(live.output_text(r))
            if isinstance(j, dict) and j.get("steps"):
                j["compiled_by"] = model
                return j
        except Exception:
            continue
    raise RuntimeError("could not compile a program from the notes")


def tidy(program: dict) -> dict:
    steps = sorted(program["steps"], key=lambda s: float(s.get("start", 0)))
    remap = {s["id"]: i + 1 for i, s in enumerate(steps)}
    for s in steps:
        s["id"] = remap[s["id"]]
        s["needs"] = sorted({remap[n] for n in s.get("needs", []) if n in remap and remap[n] < s["id"]})
        s["start"], s["end"] = float(s.get("start", 0)), float(s.get("end", 0))
    program["steps"] = steps
    program.setdefault("inputs", {})
    return program


def bind(text: str, inputs: dict) -> str:
    """'Add {salt} of salt' with the current inputs."""
    return re.sub(r"\{(\w+)\}", lambda m: str(inputs.get(m.group(1), m.group(0))), text or "")


def save_evidence(video: str, program: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(video)
    for s in program["steps"]:
        ev = {}
        for key, t in (("start", s["start"] + 0.5), ("end", max(s["start"], s["end"] - 0.5))):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, f = cap.read()
            if ok:
                name = f"step{s['id']}_{key}.jpg"
                cv2.imwrite(str(out / name), F.small(f, 640), [cv2.IMWRITE_JPEG_QUALITY, 85])
                ev[key] = name
        s["evidence"] = ev
    cap.release()


async def outline(program: dict, out: Path) -> None:
    """SAM 3.1 outlines the thing each contract is about, in the frame where the demonstration
    finished the step. Stored as boxes relative to the frame (0..1), drawn as the contract outline."""
    sem = asyncio.Semaphore(6)

    async def one(s):
        name = (s.get("evidence") or {}).get("end")
        if not name:
            return
        img = cv2.imread(str(out / "evidence" / name))
        h, w = img.shape[:2]
        phrases = [s.get("focus")] + list(s.get("objects") or [])
        for ph in [p for p in phrases if p][:3]:
            try:
                async with sem:
                    boxes = await live.sam_find(img, str(ph))
            except Exception:
                continue
            good = [b for b in boxes if b["score"] >= 0.5][:3]
            if good:
                s["evidence"]["boxes"] = [[round(b["box"][0] / w, 4), round(b["box"][1] / h, 4),
                                           round(b["box"][2] / w, 4), round(b["box"][3] / h, 4)] for b in good]
                s["evidence"]["outlined"] = str(ph)
                return

    await asyncio.gather(*(one(s) for s in program["steps"]))


async def learn(video: str, out: Path, title: str = "", concurrency: int = 8, progress=None, which: str | None = None) -> dict:
    which = which or live.world_reader()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fr = F.sample(video, 1.0)
    if progress:
        await progress({"stage": "watch", "frames": len(fr), "seconds": fr[-1][0] if fr else 0})
    sem = asyncio.Semaphore(concurrency)
    hint = f" ({title})" if title else ""
    wins = windows(fr)
    tasks = [describe(w, hint, sem, which) for w in wins]
    notes = []
    for coro in asyncio.as_completed(tasks):
        n = await coro
        notes.append(n)
        if progress:
            await progress({"stage": "note", "done": len(notes), "of": len(tasks), "note": n})
    notes.sort(key=lambda n: n["t0"])
    (out / "notes.json").write_text(json.dumps(notes, indent=1))
    if progress:
        await progress({"stage": "compile"})
    program = tidy(await compile_program(notes, title, which))
    program["learned_from"] = Path(video).name
    program["video_seconds"] = fr[-1][0] if fr else 0
    save_evidence(video, program, out / "evidence")
    if progress:
        await progress({"stage": "outline"})
    if which == "spark":           # SAM 3.1 needs the Meta key
        await outline(program, out)
    (out / "program.json").write_text(json.dumps(program, indent=1))
    return program
