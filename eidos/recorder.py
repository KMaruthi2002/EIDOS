"""Record a screen-capture tutorial of a person doing a task, like a Loom video.

The output is an ordinary video file (plus a ground-truth action log used
only to measure how accurately EIDOS recovers the steps from pixels).
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = (Path(__file__).parent / "overlay.js").read_text()
VIEW = {"width": 1100, "height": 620}


class Human:
    """Moves and types at human pace and logs what it did."""

    def __init__(self, page, t0):
        self.page, self.t0, self.log = page, t0, []
        self.x, self.y = 550, 300

    def _t(self):
        return round(time.monotonic() - self.t0, 3)

    async def pause(self, s):
        await self.page.wait_for_timeout(int(s * 1000))

    async def move(self, x, y, dur=0.6):
        steps = max(8, int(dur * 40))
        await self.page.mouse.move(x, y, steps=steps)
        self.x, self.y = x, y

    async def click(self, x, y, label):
        await self.move(x, y)
        await self.pause(0.25)
        t = self._t()
        await self.page.mouse.click(x, y)
        self.log.append({"t": t, "type": "click", "x": x, "y": y, "label": label})
        await self.pause(0.3)
        # People nudge the pointer off what they clicked before typing.
        await self.move(x + 34, y + 46, 0.25)
        await self.pause(0.15)

    async def type(self, text, label):
        t = self._t()
        await self.page.keyboard.type(text, delay=110)
        await self.pause(0.3)
        await self.page.keyboard.press("Enter")
        self.log.append({"t": t, "type": "type", "text": text, "label": label})
        await self.pause(0.7)

    async def drag(self, x1, y1, x2, y2, label):
        await self.move(x1, y1)
        await self.pause(0.2)
        t = self._t()
        await self.page.mouse.down()
        await self.page.mouse.move(x2, y2, steps=30)
        await self.page.mouse.up()
        self.log.append({"t": t, "type": "drag", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": label})
        await self.pause(0.6)


async def record_totals_tutorial(base_url: str, out_dir: Path) -> Path:
    """A person adds a bold 'Total' row with a SUM of Revenue in App A."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "_raw"
    shutil.rmtree(tmp, ignore_errors=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport=VIEW, record_video_dir=str(tmp), record_video_size=VIEW)
        await ctx.add_init_script(OVERLAY)
        t0 = time.monotonic()
        page = await ctx.new_page()
        await page.goto(f"{base_url}/gridline.html")
        await page.wait_for_timeout(600)
        h = Human(page, t0)
        await h.move(700, 300, 0.3)
        await h.pause(1.0)
        y12 = 101 + 11 * 25 + 12
        await h.click(115, y12, "first empty cell under Region")
        await h.type("Total", "label the totals row")
        await h.click(555, y12, "Revenue cell in the totals row")
        await h.type("=SUM(E2:E11)", "sum the revenue column")
        await h.drag(115, y12, 555, y12, "select the totals row")
        await h.click(384, 56, "bold button")
        await h.move(760, 470, 0.8)
        await h.pause(1.6)
        video = await page.video.path()
        await ctx.close()
        await browser.close()
    mp4 = out_dir / "tutorial_totals.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-r", "30", "-crf", "20", str(mp4)], check=True)
    (out_dir / "tutorial_totals.truth.json").write_text(json.dumps(h.log, indent=2))
    shutil.rmtree(tmp, ignore_errors=True)
    return mp4


if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
    print(asyncio.run(record_totals_tutorial(base, ROOT / "videos")))
