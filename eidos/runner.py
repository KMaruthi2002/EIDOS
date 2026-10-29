"""Run an EIDOS program on a live app, checking every step's visual contract.

For each step the runner:
  1. perceives the screen (what it can see, never the app's internals)
  2. grounds the step's target (which cell, which control)
  3. acts (click, type, drag, shortcut)
  4. checks the contract against the new screen
  5. if the check fails, tries the next way to reach the same intent

Grounding and checking go through `Perception`, which uses Meta models in
live mode and OCR / template matching offline.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from playwright.async_api import async_playwright

from . import vision as V
from .compiler import bind

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = (Path(__file__).parent / "overlay.js").read_text()
VIEW = {"width": 1100, "height": 620}


@dataclass
class StepLog:
    id: int
    intent: str
    action: str = ""
    grounding: list = field(default_factory=list)
    checks: list = field(default_factory=list)
    passed: bool = False
    t_start: float = 0
    t_end: float = 0
    shot_pre: str = ""
    shot_post: str = ""


class Table:
    """The table as perceived once before acting (the data's extent)."""

    def __init__(self, img, headers):
        self.grid = V.infer_grid(img, headers)
        self.bounds = V.column_bounds(img, self.grid)
        self.names = self.grid.header_names()

    def col(self, name=None, role=None):
        if name:
            try:
                h = self.grid.find_header(name)
                return self.grid.headers.index(h)
            except LookupError:
                pass
        if role == "first_column":
            return 0
        if role == "last_column":
            return len(self.bounds) - 1
        raise LookupError(f"no column named '{name}' on this screen")

    def x(self, c):
        l, r = self.bounds[c]
        return (l + r) / 2

    def letter(self, c):
        return V.column_letter(c)

    def cell_box(self, c, y):
        l, r = self.bounds[c]
        return int(l + 2), int(y - self.grid.row_h * 0.45), int(r - l - 3), int(self.grid.row_h * 0.9)

    @property
    def first_data_row_number(self):
        if 0 not in self.grid.row_labels:
            raise LookupError("could not read the row numbers")
        return int(self.grid.row_labels[0])

    @property
    def last_data_row_number(self):
        k = len(self.grid.data_rows_y) - 1
        if k not in self.grid.row_labels:
            raise LookupError("could not read the row numbers")
        return int(self.grid.row_labels[k])


async def run_program(program: dict, url: str, out_dir: Path, inputs: dict | None = None,
                      skill_dir: Path | None = None, use_contracts: bool = True,
                      record: bool = True, cursor_color: str = "#18c5d8",
                      on_event=None, frame_every: float = 0.0) -> dict:
    """Execute a program on the app at `url`. Returns a run report.

    on_event: optional async callable receiving dicts as the run progresses
    (start, step_start, step_end, frame) so a UI can follow along live.
    frame_every: seconds between live JPEG frames sent to on_event (0 = none).
    """
    async def emit(ev):
        if on_event:
            await on_event(ev)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = {**program["inputs"], **(inputs or {})}
    headers = list(dict.fromkeys(program["source_screen"]["headers"] +
                                 [v for k, v in inputs.items() if k.endswith("column")]))
    logs: list[StepLog] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx_args = {"viewport": VIEW}
        if record:
            ctx_args.update(record_video_dir=str(out_dir / "_raw"), record_video_size=VIEW)
        ctx = await browser.new_context(**ctx_args)
        await ctx.add_init_script(f"window.__EIDOS_CURSOR_COLOR={json.dumps(cursor_color)};" + OVERLAY)
        page = await ctx.new_page()
        t0 = time.monotonic()
        await page.goto(url)
        await page.wait_for_timeout(900)
        await page.mouse.move(700, 300, steps=5)

        async def shot():
            # Hide our own pointer while looking, so it never confuses perception.
            await page.evaluate("document.querySelectorAll('#__eidos_cursor').forEach(e=>e.style.visibility='hidden')")
            img = V.to_bgr(await page.screenshot())
            await page.evaluate("document.querySelectorAll('#__eidos_cursor').forEach(e=>e.style.visibility='visible')")
            return img

        try:
            table = Table(await shot(), headers)
            todo = program["steps"]
        except LookupError as e:
            table, todo = None, []
            logs.append(StepLog(0, "Find the table on screen", "perceive",
                                checks=[{"contract": "table visible", "error": str(e), "pass": False}]))
        anchors: dict[int, float] = {}
        selection_box = None

        async def glide(x, y):
            await page.mouse.move(x, y, steps=18)
            await page.wait_for_timeout(120)

        streaming = {"on": bool(on_event and frame_every)}

        async def stream_frames():
            import base64
            while streaming["on"]:
                try:
                    jpg = await page.screenshot(type="jpeg", quality=62)
                    await emit({"type": "frame", "jpeg": base64.b64encode(jpg).decode()})
                except Exception:
                    pass
                await asyncio.sleep(frame_every)

        streamer = asyncio.create_task(stream_frames()) if streaming["on"] else None
        await emit({"type": "start", "url": url, "steps": len(todo)})
        for st in todo:
            log = StepLog(st["id"], bind(st["intent"], inputs), st["do"])
            log.t_start = round(time.monotonic() - t0, 2)
            await emit({"type": "step_start", "id": st["id"], "intent": log.intent})
            pre = await shot()
            pre_name = f"run_step{st['id']}_pre.png"
            cv2.imwrite(str(out_dir / pre_name), pre)
            log.shot_pre = pre_name
            tgt = st.get("target", {})

            def row_y(ref):
                if ref.startswith("same_as:"):
                    return anchors[int(ref.split(":")[1])]
                if ref == "first_empty_after_data":
                    return table.grid.first_empty_row_y
                raise LookupError(ref)

            attempts = 2 if use_contracts else 1
            for attempt in range(attempts):
                if attempt:
                    # Repair: the step did not produce what the contract asks for.
                    # Dismiss anything in the way, look again, and redo the step.
                    log.grounding.append({"how": "repair: contract failed, pressed Escape and retried the step"})
                    # Once to close whatever is in the way, once more to cancel a
                    # half-finished edit it may have interrupted.
                    for _ in range(2):
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(250)
                    pre = await shot()
                try:
                    if st["do"] in ("enter_text", "enter_formula"):
                        y = row_y(tgt["row"])
                        anchors[st["id"]] = y
                        col_name = bind(tgt["column"], inputs)
                        role = "first_column" if st["do"] == "enter_text" else "last_column"
                        c = table.col(col_name, role)
                        if V.similar(table.names[c], col_name) < 0.8:
                            col_name = table.names[c]      # resolved by role, not by name
                        x = table.x(c)
                        log.grounding.append({"how": "screen reading (OCR) of headers and data extent",
                                              "column": table.names[c], "row_y": round(y), "point": [round(x), round(y)]})
                        if st["do"] == "enter_text":
                            text = bind(st["text"], inputs)
                        else:
                            f = st["formula"]
                            L = table.letter(table.col(bind(f["column"], inputs), "last_column"))
                            text = f"={f['fn']}({L}{table.first_data_row_number}:{L}{table.last_data_row_number})"
                            log.grounding.append({"how": "rewrote the formula for this screen",
                                                  "learned": st.get("learned_from"), "now": text})
                        await glide(x, y)
                        await page.mouse.click(x, y)
                        await page.wait_for_timeout(200)
                        await page.mouse.move(x + 34, y + 46, steps=6)
                        await page.keyboard.type(text, delay=70)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(450)
                        post = await shot()
                        box = table.cell_box(c, y)
                        seen = V.ocr_region(post, box)
                        # Independent evidence: the header directly above the cell we wrote must
                        # be the column the step intended. Reading back our own cell alone would
                        # only confirm that we wrote somewhere.
                        l, r = table.bounds[c]
                        hy = table.grid.header_y
                        hdr_seen = V.ocr_region(post, (int(l + 2), int(hy - table.grid.row_h * 0.45),
                                                       int(r - l - 3), int(table.grid.row_h * 0.9)))
                        col_ok = V.similar(hdr_seen, col_name) >= 0.8
                        log.checks.append({"contract": f"header above the cell reads '{col_name}'",
                                           "saw": hdr_seen, "pass": col_ok})
                        if st["do"] == "enter_text":
                            ok = V.similar(seen, text) >= 0.8
                            log.checks.append({"contract": f"cell shows '{text}'", "saw": seen, "pass": ok})
                        else:
                            vals = []
                            for ry in table.grid.data_rows_y:
                                n = V.parse_number(V.ocr_region(post, table.cell_box(c, ry)))
                                if n is not None:
                                    vals.append(n)
                            expected = sum(vals)
                            got = V.parse_number(seen)
                            ok = got is not None and abs(got - expected) < 0.5
                            log.checks.append({"contract": f"cell shows the {f['fn']} of the {table.names[c]} column read off the screen",
                                               "expected": expected, "saw": seen, "pass": ok})
                        log.passed = (ok and col_ok) or not use_contracts
                    elif st["do"] == "select_row":
                        y = row_y(tgt["row"])
                        x1, x2 = table.x(0), table.x(len(table.bounds) - 1)
                        log.grounding.append({"how": "table edges from gridlines", "from": [round(x1), round(y)], "to": [round(x2), round(y)]})
                        await glide(x1, y)
                        await page.mouse.down()
                        await page.mouse.move(x2, y, steps=26)
                        await page.mouse.up()
                        await page.wait_for_timeout(350)
                        post = await shot()
                        ch = V.changed_box(pre, post)
                        width = table.bounds[-1][1] - table.bounds[0][0]
                        # The change must span the row and stay on the row: a dialog or
                        # backdrop that changes the whole screen does not count.
                        cover, outside = V.band_change(
                            pre, post, table.bounds[0][0], table.bounds[-1][1], y, table.grid.row_h,
                            table.grid.header_y - table.grid.row_h, table.grid.first_empty_row_y + table.grid.row_h * 4)
                        ok = cover >= 0.8 and outside < 0.03
                        l0 = table.bounds[0][0]
                        selection_box = (int(l0 + 2), int(y - table.grid.row_h * 0.45), int(width - 4), int(table.grid.row_h * 0.9))
                        log.checks.append({"contract": "selection highlight covers the whole row, and only that row",
                                           "row_covered": round(cover, 2), "rest_of_table_changed": round(outside, 3), "pass": ok})
                        log.passed = ok or not use_contracts
                    elif st["do"] == "apply_format":
                        g = st["ground"]
                        before = V.ink_ratio(pre, selection_box)
                        tries = []
                        if g.get("look") and skill_dir:
                            tries.append(("look", g["look"]))
                        from . import meta
                        if meta.live() and g.get("concept"):
                            tries.append(("concept", g["concept"]))
                        tries += [("alt", a) for a in g.get("alternatives", [])]
                        ok = False
                        for kind, val in tries:
                            if kind == "look":
                                found = V.find_template(pre, str(skill_dir / val))
                                if not found:
                                    log.grounding.append({"how": "match the control's look from the tutorial", "found": False})
                                    continue
                                fx, fy, score, method = found
                                log.grounding.append({"how": "match the control's look from the tutorial", "found": True,
                                                      "method": method, "point": [round(fx), round(fy)], "score": round(score, 2)})
                                await glide(fx, fy)
                                await page.mouse.click(fx, fy)
                            elif kind == "concept":
                                boxes = await meta.sam_find(pre, val)
                                if not boxes:
                                    log.grounding.append({"how": "SAM 3.1 concept search", "concept": val, "found": False})
                                    continue
                                x1, y1, x2, y2 = boxes[0]["box"]
                                fx, fy = (x1 + x2) / 2, (y1 + y2) / 2
                                log.grounding.append({"how": "SAM 3.1 concept search", "concept": val, "found": True,
                                                      "point": [round(fx), round(fy)]})
                                await glide(fx, fy)
                                await page.mouse.click(fx, fy)
                            else:
                                keys = val.split(":", 1)[1]
                                log.grounding.append({"how": "same intent, different route", "shortcut": keys})
                                await page.keyboard.press(keys)
                            await page.wait_for_timeout(400)
                            post = await shot()
                            after = V.ink_ratio(post, selection_box)
                            ok = after > before * 1.12
                            log.checks.append({"contract": "text in the selected row got heavier (bold)",
                                               "ink_before": round(before, 4), "ink_after": round(after, 4), "pass": ok})
                            if ok or not use_contracts:
                                break
                            # Undo a wrong action before trying the next route.
                            if after < before * 0.95 or after > before * 1.02:
                                await page.keyboard.press("Control+z")
                                await page.wait_for_timeout(250)
                        log.passed = ok or not use_contracts
                except LookupError as e:
                    # Could not perceive what the step needs: a failed contract, not a crash.
                    log.checks.append({"contract": "perceive the target on this screen", "error": str(e), "pass": False})
                    log.passed = False
                if log.passed:
                    break
            log.t_end = round(time.monotonic() - t0, 2)
            post_name = f"run_step{st['id']}_post.png"
            cv2.imwrite(str(out_dir / post_name), await shot())
            log.shot_post = post_name
            logs.append(log)
            await emit({"type": "step_end", "id": st["id"], "passed": log.passed,
                        "grounding": log.grounding, "checks": log.checks})
            if use_contracts and not log.passed:
                break

        await page.mouse.move(760, 470, steps=12)
        await page.wait_for_timeout(900)
        streaming["on"] = False
        if streamer:
            await streamer
        state = await page.evaluate("window.__eidosState ? window.__eidosState() : null")
        video = await page.video.path() if record else None
        await ctx.close()
        await browser.close()

    report = {
        "url": url, "inputs": inputs, "use_contracts": use_contracts,
        "steps": [vars(l) for l in logs],
        "all_contracts_passed": all(l.passed for l in logs) and len(logs) == len(program["steps"]),
        "oracle_state": state,
    }
    if record and video:
        import subprocess, shutil
        mp4 = out_dir / "run.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-r", "30", "-crf", "22", str(mp4)], check=True)
        shutil.rmtree(out_dir / "_raw", ignore_errors=True)
        report["video"] = "run.mp4"
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    return report


async def replay(trace: dict, url: str, out_dir: Path, record: bool = True) -> dict:
    """Baseline: repeat the tutorial's exact clicks and keystrokes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx_args = {"viewport": VIEW}
        if record:
            ctx_args.update(record_video_dir=str(out_dir / "_raw"), record_video_size=VIEW)
        ctx = await browser.new_context(**ctx_args)
        await ctx.add_init_script("window.__EIDOS_CURSOR_COLOR='#9aa3ad';" + OVERLAY)
        page = await ctx.new_page()
        await page.goto(url)
        await page.wait_for_timeout(900)
        for s in trace["steps"]:
            x, y = s["point"]
            if s["action"] == "select_range":
                x2, y2 = s["point2"]
                await page.mouse.move(x, y, steps=18)
                await page.mouse.down()
                await page.mouse.move(x2, y2, steps=26)
                await page.mouse.up()
            else:
                await page.mouse.move(x, y, steps=18)
                await page.mouse.click(x, y)
                if s["action"] == "enter_text":
                    await page.keyboard.type(s["text"], delay=70)
                    await page.keyboard.press("Enter")
            await page.wait_for_timeout(450)
        await page.mouse.move(760, 470, steps=12)
        await page.wait_for_timeout(900)
        state = await page.evaluate("window.__eidosState ? window.__eidosState() : null")
        video = await page.video.path() if record else None
        await ctx.close()
        await browser.close()
    report = {"url": url, "baseline": "replay", "oracle_state": state}
    if record and video:
        import subprocess, shutil
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-r", "30", "-crf", "22", str(out_dir / "run.mp4")], check=True)
        shutil.rmtree(out_dir / "_raw", ignore_errors=True)
        report["video"] = "run.mp4"
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    return report
