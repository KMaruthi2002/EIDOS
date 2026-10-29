"""Run an everyday skill on any screen: perceive, ground by label, act, check.

Each step is grounded from a fresh screenshot (pixels only), acted on with
the mouse and keyboard, then checked against its visual contract. When a
contract fails, EIDOS clears whatever is in the way (Escape), looks again
and redoes the step, up to twice. With checks off it acts once per step and
assumes it worked. `replay` repeats the tutorial's clicks and keystrokes.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import async_playwright

from .. import vision as V
from ..recorder import OVERLAY
from . import see as S
from .learn import clean, label_for

VIEW = {"width": 1200, "height": 760}


@dataclass
class StepLog:
    id: int
    intent: str
    do: str
    grounding: list = field(default_factory=list)
    checks: list = field(default_factory=list)
    passed: bool = False
    attempts: int = 0
    t_start: float = 0.0
    t_end: float = 0.0


def bind(t, inputs):
    return re.sub(r"\{(\w+)\}", lambda m: str(inputs.get(m.group(1), m.group(0))), str(t))


def same_text(seen: str, want: str) -> bool:
    a, b = S.norm(clean(seen)), S.norm(want)
    if not a:
        return False
    return a == b or S.sim(a, b) >= 0.88 or (len(b) > 12 and b in a)


class Screen:
    def __init__(self, page):
        self.page = page

    async def look(self):
        await self.page.evaluate("document.querySelectorAll('#__eidos_cursor').forEach(e=>e.style.visibility='hidden')")
        img = V.to_bgr(await self.page.screenshot())
        await self.page.evaluate("document.querySelectorAll('#__eidos_cursor').forEach(e=>e.style.visibility='visible')")
        self.img = img
        self.lines = await asyncio.to_thread(S.lines, img)
        self.boxes = await asyncio.to_thread(S.boxes, img)
        return self

    def label_of(self, f, want: str | None = None):
        """The label that belongs to a box, read independently of how the box was found.
        Short labels ("To") can be missed by the full-screen pass, so the strips just above
        and to the left of the box are read too; with `want`, the closest reading is returned."""
        ln = label_for(f, self.lines, self.boxes)
        cands = [ln.text] if ln else []
        if not cands or (want and S.sim(cands[0], want) < 0.86):
            x, y, w, h = f
            for box in ((x - 2, max(0, y - 24), min(w, 260), 22), (max(0, x - 200), y, 196, min(h, 40))):
                t = S.read_label(self.img, box).strip(" .:|")
                if sum(c.isalpha() for c in t) >= 2:
                    cands.append(t)
        if not cands:
            return ""
        return max(cands, key=lambda t: S.sim(t, want)) if want else cands[0]

    def field(self, label):
        for thresh in (0.85, 0.72):
            for hit in S.find_text(self.lines, label, thresh):
                f = S.field_for(hit, self.boxes)
                if f and S.sim(self.label_of(f, label), label) >= 0.86:
                    return hit, f
        for f in sorted([b for b in self.boxes if S.is_field(b)], key=lambda b: (b[1], b[0])):
            if S.sim(self.label_of(f, label), label) >= 0.86 and not any(S.inside(o, f[0] + 5, f[1] + 5) and o != f and S.is_field(o) and o[2] * o[3] < f[2] * f[3] for o in self.boxes):
                return (1.0, f[0], f[1], 0, 0), f
        raise LookupError(f"no field labelled '{label}' on screen")

    def control(self, text):
        hits = S.find_text(self.lines, text, 0.84)
        if not hits:
            raise LookupError(f"no control reading '{text}' on screen")

        def rank(h):
            s, x, y, w, hh = h
            b = S.box_at([bb for bb in self.boxes if bb[2] <= 420 and 20 <= bb[3] <= 64], x + w / 2, y + hh / 2)
            filled = b is not None and S._filled(self.img, b)
            return (-round(s, 2), not b, not filled, -y)
        best = min(hits, key=rank)
        s, x, y, w, hh = best
        b = S.box_at([bb for bb in self.boxes if bb[2] <= 420 and 20 <= bb[3] <= 64], x + w / 2, y + hh / 2)
        return best, b

    def switch(self, label):
        for hit in S.find_text(self.lines, label, 0.8):
            sw = S.switch_for(hit, self.boxes, self.lines)
            if sw:
                return hit, sw
        raise LookupError(f"no switch next to '{label}'")

    def shows(self, phrase) -> bool:
        """The phrase is on screen outside any input field (so typed text doesn't count)."""
        fields = [b for b in self.boxes if S.is_field(b)]
        return any(not any(S.inside(b, h[1] + h[3] / 2, h[2] + h[4] / 2) for b in fields)
                   for h in S.find_text(self.lines, phrase, 0.82))


async def run_ui(program: dict, url: str, out_dir: Path, inputs: dict | None = None, use_contracts: bool = True,
                 record: bool = False, on_event=None, frame_every: float = 0.0, cursor_color: str = "#18c5d8") -> dict:
    async def emit(ev):
        if on_event:
            await on_event(ev)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = {**program["inputs"], **(inputs or {})}
    logs: list[StepLog] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        args = {"viewport": VIEW}
        if record:
            args.update(record_video_dir=str(out_dir / "_raw"), record_video_size=VIEW)
        ctx = await browser.new_context(**args)
        await ctx.add_init_script(f"window.__EIDOS_CURSOR_COLOR={json.dumps(cursor_color)};" + OVERLAY)
        page = await ctx.new_page()
        t0 = time.monotonic()
        await page.goto(url)
        await page.wait_for_timeout(700)
        await page.mouse.move(700, 420, steps=4)
        scr = Screen(page)
        streaming = {"on": bool(on_event and frame_every)}

        async def stream():
            while streaming["on"]:
                try:
                    jpg = await page.screenshot(type="jpeg", quality=62)
                    await emit({"type": "frame", "jpeg": base64.b64encode(jpg).decode()})
                except Exception:
                    pass
                await asyncio.sleep(frame_every)
        streamer = asyncio.create_task(stream()) if streaming["on"] else None

        async def glide(x, y):
            await page.mouse.move(x, y, steps=14)
            await page.wait_for_timeout(80)

        async def click(x, y):
            await glide(x, y)
            await page.mouse.click(x, y)

        def fpoint(f):
            return f[0] + min(60, f[2] / 3), f[1] + min(f[3], 40) / 2

        await emit({"type": "start", "url": url, "steps": len(program["steps"])})
        for st in program["steps"]:
            log = StepLog(st["id"], bind(st["intent"], inputs), st["do"], t_start=round(time.monotonic() - t0, 2))
            await emit({"type": "step_start", "id": st["id"], "intent": log.intent})
            tries = 3 if use_contracts else 1
            for attempt in range(tries):
                log.attempts = attempt + 1
                if attempt:
                    await page.keyboard.press("Escape")
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(300)
                    log.grounding.append({"how": "repair: contract failed, pressed Escape and redid the step"})
                try:
                    await scr.look()
                    do = st["do"]
                    if do == "press":
                        text = bind(st["target"]["text"], inputs)
                        hit, b = scr.control(text)
                        x, y = (b[0] + b[2] / 2, b[1] + b[3] / 2) if b else (hit[1] + hit[3] / 2, hit[2] + hit[4] / 2)
                        log.grounding.append({"how": f"found the control reading '{text}' by OCR", "at": [round(x), round(y)]})
                        await click(x, y)
                        await page.wait_for_timeout(650)
                        ok = True
                        if use_contracts:
                            await scr.look()
                            want = [bind(w, inputs) for w in st["contract"]["screen_shows"]]
                            seen = [w for w in want if scr.shows(w)]
                            ok = len(seen) >= max(1, (len(want) + 1) // 2) if want else True
                            log.checks.append({"contract": "screen then shows " + ", ".join(f"'{w}'" for w in want),
                                               "found": seen, "pass": ok})
                    elif do in ("type", "choose"):
                        label = st["target"]["field"]
                        value = bind(st["value"], inputs)
                        hit, f = scr.field(label)
                        log.grounding.append({"how": f"found the field labelled '{label}' by OCR, then its box", "box": list(f)})
                        await click(*fpoint(f))
                        if do == "type":
                            await page.keyboard.press("Control+A")
                            await page.keyboard.type(value, delay=18)
                        else:
                            await page.wait_for_timeout(350)
                            await scr.look()
                            region = (f[0] - 10, f[1] + f[3] - 4, f[2] + 20, 420)
                            opts = S.find_text(scr.lines, value, 0.85, region=region)
                            if not opts:
                                # read the open list row by row (small text on dark fills is easy to miss)
                                step_h = max(24, int(f[3] * 0.9))
                                y0 = f[1] + f[3] + 2
                                for k in range(0, 14):
                                    for dy in (0, step_h // 2):
                                        yy = y0 + k * step_h + dy
                                        if yy + step_h > scr.img.shape[0]:
                                            break
                                        t = S.read_label(scr.img, (f[0] + 4, yy, f[2] - 30, step_h))
                                        if same_text(t, value):
                                            opts = [(1.0, f[0] + 8, yy, min(200, f[2] - 40), step_h)]
                                            break
                                    if opts:
                                        break
                            if not opts:
                                raise LookupError(f"'{value}' not in the list that opened")
                            o = opts[0]
                            log.grounding.append({"how": f"opened the list and found '{value}'", "at": [o[1], o[2]]})
                            await click(o[1] + o[3] / 2, o[2] + o[4] / 2)
                        await page.wait_for_timeout(250)
                        ok = True
                        if use_contracts:
                            await scr.look()
                            seen = S.read_box(scr.img, f)
                            lab = scr.label_of(f, label)
                            lab_ok = S.sim(lab, label) >= 0.86
                            log.checks.append({"contract": f"the box written to is labelled '{label}'", "saw": lab, "pass": lab_ok})
                            ok = same_text(seen, value)
                            log.checks.append({"contract": f"the '{label}' field shows '{value}'", "saw": clean(seen), "pass": ok})
                            ok = ok and lab_ok
                    elif do == "toggle":
                        label = st["target"]["row"]
                        want = st["contract"]["switch_on"]
                        hit, sw = scr.switch(label)
                        state = S.is_on(scr.img, sw)
                        log.grounding.append({"how": f"found the switch on the '{label}' row", "box": list(sw),
                                              "was": "on" if state else "off"})
                        if not use_contracts or state != want:
                            await click(sw[0] + sw[2] / 2, sw[1] + sw[3] / 2)
                            await page.wait_for_timeout(300)
                        ok = True
                        if use_contracts:
                            await scr.look()
                            now = S.is_on(scr.img, sw)
                            ok = now == want
                            log.checks.append({"contract": f"the '{label}' switch is {'on' if want else 'off'}",
                                               "saw": "on" if now else "off", "pass": ok})
                    else:
                        raise LookupError(f"unknown step {do}")
                    log.passed = ok
                except LookupError as e:
                    log.checks.append({"contract": "find the target on this screen", "error": str(e), "pass": False})
                    log.passed = False
                if log.passed:
                    break
            log.t_end = round(time.monotonic() - t0, 2)
            logs.append(log)
            await emit({"type": "step_end", "id": st["id"], "passed": log.passed, "grounding": log.grounding, "checks": log.checks})
            if use_contracts and not log.passed:
                break
        await page.wait_for_timeout(600)
        streaming["on"] = False
        if streamer:
            await streamer
        state = await page.evaluate("window.__eidosState ? window.__eidosState() : null")
        video = await page.video.path() if record else None
        await ctx.close()
        await browser.close()
    report = {"url": url, "inputs": inputs, "use_contracts": use_contracts, "steps": [vars(l) for l in logs],
              "all_contracts_passed": all(l.passed for l in logs) and len(logs) == len(program["steps"]),
              "oracle_state": state}
    if video:
        _mp4(video, out_dir)
        report["video"] = "run.mp4"
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str))
    return report


async def replay_ui(trace: dict, url: str, out_dir: Path, record: bool = False, on_event=None) -> dict:
    """Copy the clicks: repeat the tutorial's pointer positions and keystrokes."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        args = {"viewport": VIEW}
        if record:
            args.update(record_video_dir=str(out_dir / "_raw"), record_video_size=VIEW)
        ctx = await browser.new_context(**args)
        await ctx.add_init_script("window.__EIDOS_CURSOR_COLOR='#18c5d8';" + OVERLAY)
        page = await ctx.new_page()
        await page.goto(url)
        await page.wait_for_timeout(700)
        prev = None
        for ev in trace["events"]:
            if prev is not None:
                await page.wait_for_timeout(int(min(1.2, max(0.3, (ev["t"] - prev) * 0.4)) * 1000))
            await page.mouse.move(ev["x"], ev["y"], steps=12)
            await page.mouse.click(ev["x"], ev["y"])
            if ev.get("typed"):
                await page.keyboard.type(ev["typed"], delay=18)
            prev = ev["t"]
        await page.wait_for_timeout(900)
        state = await page.evaluate("window.__eidosState ? window.__eidosState() : null")
        video = await page.video.path() if record else None
        await ctx.close()
        await browser.close()
    report = {"url": url, "replay": True, "oracle_state": state, "all_contracts_passed": None}
    if video:
        _mp4(video, out_dir)
        report["video"] = "run.mp4"
    return report


def _mp4(video, out_dir):
    import shutil
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-r", "30", "-crf", "23", str(out_dir / "run.mp4")], check=True)
    shutil.rmtree(out_dir / "_raw", ignore_errors=True)


if __name__ == "__main__":
    import random
    import sys
    from .tasks import fresh_inputs, score
    task, qs = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "skin=A")
    mode = sys.argv[3] if len(sys.argv) > 3 else "eidos"
    sk = Path(f"runs/ui_skill_{task}")
    prog = json.loads((sk / "program.json").read_text())
    inp = fresh_inputs(task, random.Random(1)) if "new" in sys.argv else {}
    url = f"http://localhost:8011/apps/everyday/index.html?task={task}&{qs}"
    if mode == "replay":
        rep = asyncio.run(replay_ui(json.loads((sk / "trace.json").read_text()), url, Path("/tmp/eidos/uirun")))
    else:
        rep = asyncio.run(run_ui(prog, url, Path("/tmp/eidos/uirun"), inp, use_contracts=(mode == "eidos")))
        for s in rep["steps"]:
            print(s["id"], s["passed"], s["attempts"], [c.get("saw", c.get("found", c.get("error"))) for c in s["checks"]])
    print("agent:", rep["all_contracts_passed"], "truth:", score(task, rep["oracle_state"], {**prog["inputs"], **inp}))
