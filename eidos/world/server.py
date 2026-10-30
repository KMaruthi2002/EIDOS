"""Studio endpoints for the physical world: learn from a real-world video, then follow a live
camera (or a video played as if live)."""
from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from .. import live
from . import learn as L
from .session import MAX_SESSIONS, SESSIONS, LiveSession, reap

ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS = ROOT / "studio_data" / "skills"
SAMPLES = ROOT / "samples" / "world"
router = APIRouter()


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def seed():
    """Ship the sample real-world skills (learned from the bundled demonstration videos)."""
    if not SAMPLES.exists():
        return
    for src in sorted(SAMPLES.iterdir()):
        if (src / "program.json").exists():
            dst = SKILLS / f"world-{src.name}"
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)


seed()


def _skill(sid: str) -> Path:
    p = SKILLS / Path(sid).name
    meta = p / "meta.json"
    if not (p / "program.json").exists() or not meta.exists() or json.loads(meta.read_text()).get("kind") != "world":
        raise HTTPException(404, "skill not found")
    return p


@router.get("/world", response_class=HTMLResponse)
def page():
    return (ROOT / "web" / "world" / "index.html").read_text()


@router.get("/api/world/skills")
def skills():
    out = []
    for p in sorted(SKILLS.iterdir()) if SKILLS.exists() else []:
        m = p / "meta.json"
        if (p / "program.json").exists() and m.exists():
            meta = json.loads(m.read_text())
            if meta.get("kind") == "world":
                prog = json.loads((p / "program.json").read_text())
                out.append({**meta, "title": prog.get("title"), "domain": prog.get("domain"), "steps": len(prog["steps"])})
    out.sort(key=lambda x: (not x.get("sample"), x.get("order", 99), -x.get("created", 0)))
    return out


@router.get("/api/world/skills/{sid}")
def skill(sid: str):
    p = _skill(sid)
    return {"meta": json.loads((p / "meta.json").read_text()), "program": json.loads((p / "program.json").read_text()),
            "notes": json.loads((p / "notes.json").read_text()) if (p / "notes.json").exists() else [],
            "practice": json.loads((p / "practice.json").read_text()) if (p / "practice.json").exists() else []}


@router.get("/api/world/skills/{sid}/file/{name:path}")
def skill_file(sid: str, name: str):
    p = _skill(sid)
    f = (p / name).resolve()
    if not str(f).startswith(str(p.resolve())) or not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


@router.post("/api/world/skills/{sid}/steps/{step_id}")
async def set_step(sid: str, step_id: int, request: Request):
    """The person who owns the skill decides: mark a step optional (a habit) or required."""
    p = _skill(sid)
    body = await request.json()
    prog = json.loads((p / "program.json").read_text())
    for s in prog["steps"]:
        if s["id"] == step_id:
            s["optional"] = bool(body.get("optional"))
            s["set_by_user"] = True
    (p / "program.json").write_text(json.dumps(prog, indent=1))
    return {"ok": True}


@router.delete("/api/world/skills/{sid}")
def delete(sid: str):
    p = _skill(sid)
    if json.loads((p / "meta.json").read_text()).get("sample"):
        raise HTTPException(400, "sample skills cannot be deleted")
    shutil.rmtree(p)
    return {"ok": True}


@router.post("/api/world/learn")
async def learn(file: UploadFile = File(...), title: str = Form("")):
    if not live.meta_live():
        raise HTTPException(400, "Learning from real-world video needs a Meta Model API key (MODEL_API_KEY in .env).")
    sid = "world-" + uuid.uuid4().hex[:8]
    out = SKILLS / sid
    out.mkdir(parents=True)
    video = out / "video.mp4"
    with video.open("wb") as f:
        while chunk := await file.read(1 << 20):
            f.write(chunk)

    async def stream():
        q: asyncio.Queue = asyncio.Queue()

        async def progress(ev):
            await q.put(ev)

        task = asyncio.create_task(L.learn(str(video), out, title, progress=progress))
        yield sse("status", {"msg": "Watching the video", "skill": sid})
        while not task.done() or not q.empty():
            try:
                ev = await asyncio.wait_for(q.get(), 0.5)
            except asyncio.TimeoutError:
                continue
            if ev["stage"] == "watch":
                yield sse("status", {"msg": f"Watching {ev['seconds']:.0f} seconds of video, eight seconds at a time"})
            elif ev["stage"] == "note":
                yield sse("note", ev)
            elif ev["stage"] == "compile":
                yield sse("status", {"msg": "Compiling the notes into a program (Muse Wonder)"})
            elif ev["stage"] == "outline":
                yield sse("status", {"msg": "Outlining what each step is about (SAM 3.1)"})
        try:
            prog = task.result()
        except Exception as e:
            shutil.rmtree(out, ignore_errors=True)
            yield sse("error", {"msg": f"Could not learn from this video: {e}"})
            return
        (out / "meta.json").write_text(json.dumps({"id": sid, "kind": "world", "name": prog.get("title"),
                                                   "source": file.filename or "your video", "created": time.time()}))
        yield sse("program", prog)
        yield sse("done", {"skill": sid})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/api/world/live/start")
async def live_start(request: Request):
    reap()
    if not live.meta_live():
        raise HTTPException(400, "Following live needs a Meta Model API key (MODEL_API_KEY in .env).")
    if len(SESSIONS) >= MAX_SESSIONS:
        raise HTTPException(429, "Too many live sessions are open. Finish one first.")
    body = await request.json()
    p = _skill(body.get("skill", ""))
    prog = json.loads((p / "program.json").read_text())
    reader = body.get("reader", "spark")
    if reader == "open" and not live.open_live():
        raise HTTPException(400, "Muse Spark Open needs a Baseten key (BASETEN_API_KEY in .env).")
    s = LiveSession(uuid.uuid4().hex[:10], p, prog, body.get("inputs") or {}, reader)
    SESSIONS[s.id] = s
    return {"id": s.id, "state": s.state()}


def _session(lid: str) -> LiveSession:
    s = SESSIONS.get(lid)
    if not s:
        raise HTTPException(404, "live session not found")
    return s


@router.post("/api/world/live/{lid}/frame")
async def live_frame(lid: str, request: Request, t: float):
    s = _session(lid)
    s.add_frame(t, await request.body())
    return {"ok": True}


@router.get("/api/world/live/{lid}/events")
async def live_events(lid: str):
    s = _session(lid)
    q: asyncio.Queue = asyncio.Queue()
    s.listeners.append(q)

    async def stream():
        try:
            yield sse("state", s.state())
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), 15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield sse(ev["kind"], ev)
                if ev["kind"] == "finished":
                    return
        finally:
            if q in s.listeners:
                s.listeners.remove(q)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/api/world/live/{lid}/finish")
async def live_finish(lid: str):
    s = _session(lid)
    out = await s.finish()
    asyncio.get_running_loop().call_later(60, lambda: SESSIONS.pop(lid, None))
    return out
