"""Teach a skill live: you do the task once in a real browser, EIDOS records it.

The Studio streams the browser's screen to the page and forwards your pointer and
keys to it. The recording is made the way screen recorders make tutorials, with a
highlighted pointer and click rings, and then EIDOS learns from the video file
alone, exactly as it would from a video recorded anywhere else.
"""
from __future__ import annotations

import asyncio
import base64
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from playwright.async_api import async_playwright

from .recorder import OVERLAY

VIEW = {"width": 1200, "height": 760}
IDLE_LIMIT = 15 * 60          # seconds without input before a session is closed
MAX_LENGTH = 5 * 60           # longest recording
KEYS = {"Enter", "Backspace", "Tab", "Escape", "Delete", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"}


class Session:
    def __init__(self, sid: str, url: str, work: Path):
        self.id, self.url, self.work = sid, url, work
        self.pw = self.browser = self.ctx = self.page = None
        self.t0 = self.last_input = time.monotonic()
        self.lock = asyncio.Lock()
        self.x, self.y = VIEW["width"] / 2, VIEW["height"] / 2
        self.clicks = 0
        self.closed = False

    async def start(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch()
        self.ctx = await self.browser.new_context(viewport=VIEW, record_video_dir=str(self.work / "raw"), record_video_size=VIEW)
        await self.ctx.add_init_script(OVERLAY)
        self.page = await self.ctx.new_page()
        await self.page.goto(self.url)
        await self.page.mouse.move(self.x, self.y)
        self.t0 = time.monotonic()

    async def frame(self) -> str:
        async with self.lock:
            img = await self.page.screenshot(type="jpeg", quality=60)
        return base64.b64encode(img).decode()

    async def apply(self, events: list[dict]):
        """Pointer and key events from the page, in order. Coordinates are in screen pixels (1200 x 760)."""
        self.last_input = time.monotonic()
        m, kb = self.page.mouse, self.page.keyboard
        async with self.lock:
            for ev in events[:400]:
                t = ev.get("type")
                if t in ("move", "down", "up"):
                    x = max(0.0, min(VIEW["width"] - 1.0, float(ev.get("x", self.x))))
                    y = max(0.0, min(VIEW["height"] - 1.0, float(ev.get("y", self.y))))
                    # glide like a hand does, so the recording shows the pointer travel
                    steps = max(1, min(12, int(((x - self.x) ** 2 + (y - self.y) ** 2) ** 0.5 / 25)))
                    await m.move(x, y, steps=steps)
                    self.x, self.y = x, y
                    if t == "down":
                        await m.down()
                        self.clicks += 1
                    elif t == "up":
                        await m.up()
                elif t == "text":
                    await kb.type(str(ev.get("text", ""))[:200], delay=40)
                elif t == "key" and ev.get("key") in KEYS:
                    await kb.press(ev["key"])

    async def finish(self, dst: Path) -> Path:
        """Stop recording and write the tutorial video as mp4."""
        async with self.lock:
            await self.page.mouse.move(self.x + 40, self.y + 40, steps=6)
            await self.page.wait_for_timeout(1500)        # a beat at the end, like a person stopping a recording
            raw = await self.page.video.path()
            await self.close()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-r", "30", "-crf", "20", str(dst)], check=True)
        shutil.rmtree(self.work, ignore_errors=True)
        return dst

    async def close(self):
        if self.closed:
            return
        self.closed = True
        for obj in (self.ctx, self.browser):
            try:
                await obj.close()
            except Exception:
                pass
        try:
            await self.pw.stop()
        except Exception:
            pass


SESSIONS: dict[str, Session] = {}


async def open_session(url: str, work_root: Path) -> Session:
    await reap()
    if len(SESSIONS) >= 3:
        oldest = min(SESSIONS.values(), key=lambda s: s.last_input)
        await drop(oldest.id)
    sid = "teach-" + uuid.uuid4().hex[:8]
    s = Session(sid, url, work_root / sid)
    await s.start()
    SESSIONS[sid] = s
    return s


async def drop(sid: str):
    s = SESSIONS.pop(sid, None)
    if s:
        await s.close()
        shutil.rmtree(s.work, ignore_errors=True)


async def reap():
    now = time.monotonic()
    for sid, s in list(SESSIONS.items()):
        if now - s.last_input > IDLE_LIMIT or now - s.t0 > MAX_LENGTH + 60:
            await drop(sid)
