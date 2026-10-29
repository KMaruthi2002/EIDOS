"""EIDOS Studio: learn a skill from a video and run it live, in the browser.

    python -m eidos studio          then open http://localhost:8000

Everything runs on this machine: the two target apps are served from
/apps, the agent drives a headless browser, and progress streams to the page
as server-sent events (including live JPEG frames of what the agent sees).
"""
from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .compiler import compile_trace
from .extract import analyze
from .runner import run_program, replay
from .score import score_totals

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "studio_data"
SKILLS = DATA / "skills"
UPLOADS = DATA / "uploads"
for d in (SKILLS, UPLOADS):
    d.mkdir(parents=True, exist_ok=True)

DATASETS = {
    "sales": {"label_column": "Region", "sum_column": "Revenue"},
    "inventory": {"label_column": "Warehouse", "sum_column": "Value"},
}

app = FastAPI(title="EIDOS Studio")
app.mount("/apps", StaticFiles(directory=str(ROOT / "apps")), name="apps")
RUN_LOCK = asyncio.Lock()
PORT = {"value": 8000}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _seed_sample():
    """Ship the sample skill learned from the bundled tutorial."""
    dst = SKILLS / "sample-totals"
    src = ROOT / "runs" / "tutorial_totals"
    if not dst.exists() and src.exists():
        shutil.copytree(src, dst)
        shutil.copy(ROOT / "videos" / "tutorial_totals.mp4", dst / "video.mp4")
        meta = {"id": "sample-totals", "name": "Add a totals row", "source": "Sample tutorial (14 s)", "created": time.time()}
        (dst / "meta.json").write_text(json.dumps(meta))


_seed_sample()


def _skill(sid: str) -> Path:
    p = SKILLS / sid
    if not (p / "program.json").exists():
        raise HTTPException(404, "skill not found")
    return p


# ------------------------------------------------------------------ pages

@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "web" / "studio" / "index.html").read_text()


@app.get("/api/skills")
def list_skills():
    out = []
    for p in sorted(SKILLS.iterdir()):
        if (p / "program.json").exists():
            meta = json.loads((p / "meta.json").read_text()) if (p / "meta.json").exists() else {"id": p.name}
            prog = json.loads((p / "program.json").read_text())
            out.append({**meta, "steps": len(prog["steps"]), "inputs": prog["inputs"]})
    return out


@app.get("/api/skills/{sid}")
def get_skill(sid: str):
    p = _skill(sid)
    return {
        "meta": json.loads((p / "meta.json").read_text()) if (p / "meta.json").exists() else {"id": sid},
        "trace": json.loads((p / "trace.json").read_text()),
        "program": json.loads((p / "program.json").read_text()),
    }


@app.get("/api/skills/{sid}/file/{name}")
def skill_file(sid: str, name: str):
    p = _skill(sid) / Path(name).name
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# ------------------------------------------------------------------ learning

@app.post("/api/learn")
async def learn(file: UploadFile | None = File(default=None)):
    """Upload a tutorial video; stream the analysis as it happens."""
    sid = "skill-" + uuid.uuid4().hex[:8]
    out = SKILLS / sid
    out.mkdir(parents=True)
    video = out / "video.mp4"
    if file is None:
        shutil.copy(ROOT / "videos" / "tutorial_totals.mp4", video)
        source = "Sample tutorial (14 s)"
    else:
        with video.open("wb") as f:
            while chunk := await file.read(1 << 20):
                f.write(chunk)
        source = file.filename or "uploaded video"

    async def stream():
        yield sse("status", {"msg": "Reading the video frames", "skill": sid})
        loop = asyncio.get_running_loop()
        try:
            trace = await loop.run_in_executor(None, analyze, video, out, None)
        except Exception as e:  # report, don't crash the server
            yield sse("error", {"msg": f"Could not learn from this video: {e}"})
            return
        yield sse("status", {"msg": f"Found {len(trace['events'])} pointer actions in {trace['frames_analyzed']} frames"})
        for s in trace["steps"]:
            yield sse("step", s)
            await asyncio.sleep(0.25)
        prog = compile_trace(trace)
        (out / "program.json").write_text(json.dumps(prog, indent=2))
        (out / "meta.json").write_text(json.dumps({"id": sid, "name": prog["name"], "source": source, "created": time.time()}))
        yield sse("program", prog)
        yield sse("done", {"skill": sid})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


# ------------------------------------------------------------------ running

def target_url(opts: dict) -> str:
    base = f"http://127.0.0.1:{PORT['value']}/apps"
    page = "tabula.html" if opts.get("app") == "B" else "gridline.html"
    q = {"data": opts.get("data", "sales")}
    if opts.get("app") != "B":
        if opts.get("dark"):
            q["theme"] = "dark"
        if opts.get("sidebar"):
            q["side"] = 180
        if opts.get("big"):
            q["colw"], q["rowh"] = 140, 32
        if opts.get("shuffle"):
            q["order"] = "4,0,1,2,3"
    if opts.get("popup"):
        q["popup"] = 4.0
    return f"{base}/{page}?" + "&".join(f"{k}={v}" for k, v in q.items())


@app.post("/api/run")
async def run(request: Request):
    body = await request.json()
    sid = body.get("skill", "sample-totals")
    opts = body.get("target", {})
    mode = body.get("mode", "eidos")          # eidos | nochk | replay
    p = _skill(sid)
    program = json.loads((p / "program.json").read_text())
    trace = json.loads((p / "trace.json").read_text())
    data = DATASETS.get(opts.get("data", "sales"), DATASETS["sales"])
    inputs = {**data, **{k: v for k, v in (body.get("inputs") or {}).items() if v}}
    url = target_url(opts)
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(ev):
        await queue.put(ev)

    async def worker():
        async with RUN_LOCK:
            out = DATA / "runs" / uuid.uuid4().hex[:8]
            try:
                if mode == "replay":
                    await queue.put({"type": "start", "url": url, "steps": len(trace["steps"])})
                    rep = await replay(trace, url, out, record=False)
                else:
                    rep = await run_program(program, url, out, inputs=inputs, skill_dir=p,
                                            use_contracts=(mode == "eidos"), record=False,
                                            on_event=on_event, frame_every=0.3)
                truth = score_totals(rep.get("oracle_state"), inputs.get("label", program["inputs"].get("label", "Total")),
                                     inputs["label_column"], inputs["sum_column"])
                rep.pop("oracle_state", None)
                await queue.put({"type": "done", "report": rep, "truth": truth, "url": url, "mode": mode})
            except Exception as e:
                await queue.put({"type": "error", "msg": repr(e)})

    task = asyncio.create_task(worker())

    async def stream():
        yield sse("status", {"msg": "Waiting for the browser" if RUN_LOCK.locked() else "Starting", "url": url})
        while True:
            ev = await queue.get()
            yield sse(ev["type"], ev)
            if ev["type"] in ("done", "error"):
                break
        await task

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/target")
def preview_target(app_: str = "A", data: str = "sales", dark: bool = False, sidebar: bool = False,
                   big: bool = False, shuffle: bool = False, popup: bool = False):
    return {"url": target_url({"app": app_, "data": data, "dark": dark, "sidebar": sidebar, "big": big,
                               "shuffle": shuffle, "popup": popup})}


def main(port: int = 8000):
    import uvicorn
    PORT["value"] = port
    print(f"EIDOS Studio: open http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
