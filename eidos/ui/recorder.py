"""Record everyday-task tutorials: a person doing the task in App A, captured
like a Loom video with a highlighted pointer and click rings.

The recorder plays the person, so it may look at the page to know where things
are. EIDOS only ever gets the resulting video file.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path

from playwright.async_api import async_playwright

from ..recorder import Human, OVERLAY
from .tasks import TUTORIALS, URL

VIEW = {"width": 1200, "height": 760}
ROOT = Path(__file__).resolve().parents[2]


async def _center(page, loc):
    b = await loc.bounding_box()
    return b["x"] + min(b["width"] / 2, 60 if b["width"] > 200 else b["width"] / 2), b["y"] + b["height"] / 2


def field_input(page, label):
    return page.locator(".field", has=page.locator("label", has_text=label)).locator(".input").first


async def record(task: str, base_url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f"_raw_{task}"
    shutil.rmtree(tmp, ignore_errors=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport=VIEW, record_video_dir=str(tmp), record_video_size=VIEW)
        await ctx.add_init_script(OVERLAY)
        t0 = time.monotonic()
        page = await ctx.new_page()
        await page.goto(f"{base_url}{URL}?task={task}&skin=A")
        await page.wait_for_timeout(600)
        h = Human(page, t0)
        await h.move(700, 400, 0.3)
        await h.pause(1.0)
        for act in TUTORIALS[task]:
            kind = act[0]
            if kind == "click":
                loc = page.get_by_text(act[1], exact=True).first
                x, y = await _center(page, loc)
                await h.click(x, y, f"click {act[1]}")
                await h.pause(0.6)
            elif kind == "type":
                x, y = await _center(page, field_input(page, act[1]))
                await h.click(x, y, f"field {act[1]}")
                t = h._t()
                await page.keyboard.type(act[2], delay=85)
                h.log.append({"t": t, "type": "type", "text": act[2], "label": act[1]})
                await h.pause(0.7)
            elif kind == "choose":
                x, y = await _center(page, field_input(page, act[1]))
                await h.click(x, y, f"open {act[1]}")
                await h.pause(0.5)
                opt = page.locator(".opt", has_text=act[2]).first
                x, y = await _center(page, opt)
                await h.click(x, y, f"choose {act[2]}")
                await h.pause(0.4)
            elif kind == "toggle":
                sw = page.locator(".toggle-row", has=page.locator(".t", has_text=act[1])).locator(".switch")
                x, y = await _center(page, sw)
                await h.click(x, y, f"toggle {act[1]}")
                await h.pause(0.5)
        await h.move(900, 600, 0.8)
        await h.pause(1.8)
        video = await page.video.path()
        await ctx.close()
        await browser.close()
    mp4 = out_dir / f"tutorial_{task}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-r", "30", "-crf", "20", str(mp4)], check=True)
    (out_dir / f"tutorial_{task}.truth.json").write_text(json.dumps(h.log, indent=2))
    shutil.rmtree(tmp, ignore_errors=True)
    return mp4


if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8011"
    for t in (sys.argv[2:] or list(TUTORIALS)):
        print(asyncio.run(record(t, base, ROOT / "videos")))
