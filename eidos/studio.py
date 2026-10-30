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
from .ui import learn as ui_learn
from .ui.run import run_ui, replay_ui
from .ui.tasks import TITLES, fresh_inputs, score as ui_score, N_FIELDS, _norm
from . import teach
import random

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
    if src.exists():
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
        shutil.copy(ROOT / "videos" / "tutorial_totals.mp4", dst / "video.mp4")
        meta = {"id": "sample-totals", "name": "Add a totals row", "source": "Sample tutorial (14 s)", "created": time.time()}
        (dst / "meta.json").write_text(json.dumps(meta))


_seed_sample()


def _seed_everyday():
    for task, title in TITLES.items():
        dst = SKILLS / f"sample-{task}"
        src = ROOT / "runs" / f"ui_skill_{task}"
        if src.exists():
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
            shutil.copy(ROOT / "videos" / f"tutorial_{task}.mp4", dst / "video.mp4")
            (dst / "meta.json").write_text(json.dumps({"id": dst.name, "name": title, "kind": "ui", "task": task,
                                                       "source": f"Sample tutorial ({task})", "created": time.time()}))


_seed_everyday()


def _skill(sid: str) -> Path:
    p = SKILLS / sid
    if not (p / "program.json").exists():
        raise HTTPException(404, "skill not found")
    return p


# ------------------------------------------------------------------ pages

@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "web" / "studio" / "index.html").read_text()


@app.get("/api/sample/{name}.mp4")
def sample_video(name: str):
    f = ROOT / "videos" / f"tutorial_{Path(name).name}.mp4"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


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


async def learn_ui_stream(sid: str, out: Path, video: Path, task: str, source: str, name: str, taught: bool = False):
    """Learn an everyday skill from a video, streaming what was found."""
    yield sse("status", {"msg": "Reading the video frames: finding clicks, labels, fields and switches", "skill": sid})
    loop = asyncio.get_running_loop()
    try:
        trace, prog = await loop.run_in_executor(None, ui_learn.analyze, video, out, name)
    except Exception as e:
        shutil.rmtree(out, ignore_errors=True)
        yield sse("error", {"msg": f"Could not learn from this video: {e}"})
        return
    if not prog["steps"]:
        shutil.rmtree(out, ignore_errors=True)
        yield sse("error", {"msg": "No clicks were found in this video, so there is nothing to learn."})
        return
    yield sse("status", {"msg": f"Found {len(trace['events'])} clicks in {trace['frames_analyzed']} frames"})
    for st in prog["steps"]:
        yield sse("step", {**st, "learned": st.get("learned_from") or st["target"].get("text") or st["target"].get("row")})
        await asyncio.sleep(0.3)
    (out / "meta.json").write_text(json.dumps({"id": sid, "name": name, "kind": "ui", "task": task,
                                               "source": source, "taught": taught, "created": time.time()}))
    yield sse("program", prog)
    yield sse("done", {"skill": sid})


# ------------------------------------------------------------------ learning

@app.post("/api/learn")
async def learn(file: UploadFile | None = File(default=None), kind: str = "sheet", sample: str = "totals", task: str = ""):
    """Upload a tutorial video; stream the analysis as it happens."""
    sid = "skill-" + uuid.uuid4().hex[:8]
    out = SKILLS / sid
    out.mkdir(parents=True)
    video = out / "video.mp4"
    if file is None:
        if sample in TITLES:
            kind, task = "ui", sample
        shutil.copy(ROOT / "videos" / f"tutorial_{sample}.mp4", video)
        source = f"Sample tutorial ({sample})"
    else:
        with video.open("wb") as f:
            while chunk := await file.read(1 << 20):
                f.write(chunk)
        source = file.filename or "uploaded video"

    if kind == "ui":
        return StreamingResponse(learn_ui_stream(sid, out, video, task, source, TITLES.get(task, "Everyday skill")),
                                 media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

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
    if program.get("kind") == "ui":
        meta = json.loads((p / "meta.json").read_text()) if (p / "meta.json").exists() else {}
        return await run_everyday(program, trace, meta, opts, mode, p)
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


def everyday_url(task: str, opts: dict) -> str:
    q = {"task": task, "skin": "B" if opts.get("app") == "B" else "A", "data": opts.get("seed", 1)}
    if opts.get("app") == "C":                 # design C: the same app with every control renamed
        q["words"] = "alt"
    if opts.get("dark"):
        q["theme"] = "dark"
    if opts.get("nav") and opts["nav"] != "default":
        q["nav"] = opts["nav"]
    if opts.get("labels_top"):
        q["labels"] = "top"
    if opts.get("btn_top"):
        q["btn"] = "top"
    if opts.get("big"):
        q["scale"] = "1.2"
    if opts.get("shuffle"):
        n = N_FIELDS[task]
        q["order"] = ",".join(str((i + 1) % n) for i in range(n))
    if opts.get("popup"):
        q["popup"] = 4.0
    return f"http://127.0.0.1:{PORT['value']}/apps/everyday/index.html?" + "&".join(f"{k}={v}" for k, v in q.items())


async def run_everyday(program, trace, meta, opts, mode, p):
    task = meta.get("task") or opts.get("task") or "mail"
    inputs = dict(program["inputs"])
    if opts.get("newdata"):
        fresh = fresh_inputs(task, random.Random(time.time())) if task in TITLES else {}
        inputs.update({k: v for k, v in fresh.items() if k in inputs})
    if isinstance(opts.get("inputs"), dict):            # values the person typed in the Studio
        inputs.update({k: str(v).strip()[:120] for k, v in opts["inputs"].items() if k in inputs and str(v).strip()})
    url = everyday_url(task, opts)
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(ev):
        await queue.put(ev)

    async def worker():
        async with RUN_LOCK:
            out = DATA / "runs" / uuid.uuid4().hex[:8]
            try:
                if mode == "replay":
                    await queue.put({"type": "start", "url": url, "steps": len(trace["events"])})
                    sub = {program["inputs"][k]: v for k, v in inputs.items() if k in program["inputs"]} if opts.get("newdata") else None
                    rep = await replay_ui(trace, url, out, substitute=sub)
                else:
                    rep = await run_ui(program, url, out, inputs, use_contracts=(mode in ("eidos", "live")),
                                       on_event=on_event, frame_every=0.3, live=(mode == "live"),
                                       reader="spark" if mode == "live" else None)
                truth = (score_taught if meta.get("taught") else ui_score)(task, rep.get("oracle_state"), inputs)
                rep.pop("oracle_state", None)
                await queue.put({"type": "done", "report": rep, "truth": truth, "url": url, "mode": mode, "inputs": inputs})
            except Exception as e:
                await queue.put({"type": "error", "msg": repr(e)})

    task_ = asyncio.create_task(worker())

    async def stream():
        yield sse("status", {"msg": "Waiting for the browser" if RUN_LOCK.locked() else "Starting", "url": url, "inputs": inputs})
        while True:
            ev = await queue.get()
            yield sse(ev["type"], ev)
            if ev["type"] in ("done", "error"):
                break
        await task_

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def score_taught(task: str, state: dict | None, inputs: dict) -> dict:
    """A skill you taught may do more or less than the sample task, so success is:
    a new record (or a saved settings page) that holds every value this run entered."""
    if not state:
        return {"success": False, "why": "no state"}
    want = [_norm(v) for v in inputs.values() if str(v).strip()]
    if task == "settings":
        vals = [_norm(v) for v in state["settings"].values() if isinstance(v, str)]
        ok = state["saves"] >= 1 and all(w in vals for w in want)
        return {"success": ok, "why": "" if ok else ("settings were not saved" if not state["saves"] else f"saved settings: {state['settings']}")}
    recs = state["records"]
    good = [r for r in recs if all(any(_norm(x) == w for x in r.values()) for w in want)]
    ok = len(good) == 1 and len(recs) == 1
    return {"success": ok, "why": "" if ok else (f"{len(good)} matching of {len(recs)} saved: {recs[:2]}" if recs else "nothing was saved")}


# ------------------------------------------------------------------ teaching live

@app.post("/api/teach/start")
async def teach_start(request: Request):
    body = await request.json()
    task = body.get("task", "mail")
    if task not in TITLES:
        raise HTTPException(400, "unknown app")
    url = f"http://127.0.0.1:{PORT['value']}/apps/everyday/index.html?task={task}&skin=A"
    try:
        s = await teach.open_session(url, DATA / "teach")
    except Exception as e:
        raise HTTPException(500, f"Could not start a browser: {e}")
    return {"id": s.id, "width": teach.VIEW["width"], "height": teach.VIEW["height"], "task": task}


@app.get("/api/teach/{tid}/frames")
async def teach_frames(tid: str):
    s = teach.SESSIONS.get(tid)
    if not s:
        raise HTTPException(404, "no such recording")

    async def stream():
        while not s.closed:
            try:
                jpeg = await s.frame()
            except Exception:
                break
            yield sse("frame", {"jpeg": jpeg, "seconds": round(time.monotonic() - s.t0, 1), "clicks": s.clicks})
            await asyncio.sleep(0.11)
        yield sse("closed", {})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/teach/{tid}/input")
async def teach_input(tid: str, request: Request):
    s = teach.SESSIONS.get(tid)
    if not s or s.closed:
        raise HTTPException(404, "no such recording")
    body = await request.json()
    await s.apply(body.get("events", []))
    return {"ok": True, "clicks": s.clicks}


@app.post("/api/teach/{tid}/cancel")
async def teach_cancel(tid: str):
    await teach.drop(tid)
    return {"ok": True}


@app.post("/api/teach/{tid}/finish")
async def teach_finish(tid: str, request: Request):
    s = teach.SESSIONS.pop(tid, None)
    if not s:
        raise HTTPException(404, "no such recording")
    body = await request.json()
    task = next((t for t in TITLES if f"task={t}&" in s.url), "mail")
    name = (str(body.get("name") or "").strip() or f"My skill ({TITLES[task].lower()})")[:80]
    sid = "skill-" + uuid.uuid4().hex[:8]
    out = SKILLS / sid
    out.mkdir(parents=True)
    video = out / "video.mp4"
    seconds = round(time.monotonic() - s.t0, 1)
    try:
        await s.finish(video)
    except Exception as e:
        shutil.rmtree(out, ignore_errors=True)
        raise HTTPException(500, f"Could not save the recording: {e}")
    return StreamingResponse(learn_ui_stream(sid, out, video, task, f"your recording ({seconds:.0f} s)", name, taught=True),
                             media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.delete("/api/skills/{sid}")
def delete_skill(sid: str):
    if sid.startswith("sample-"):
        raise HTTPException(400, "sample skills can't be deleted")
    p = _skill(sid)
    shutil.rmtree(p)
    return {"ok": True}


@app.get("/api/skills/{sid}/download")
def download_skill(sid: str):
    p = _skill(sid)
    prog = json.loads((p / "program.json").read_text())
    return JSONResponse(prog, headers={"Content-Disposition": f'attachment; filename="{sid}.skill.json"'})


@app.get("/api/target_ui")
def preview_target_ui(task: str = "mail", app_: str = "A", dark: bool = False, labels_top: bool = False, shuffle: bool = False,
                      btn_top: bool = False, big: bool = False, nav: str = "default"):
    return {"url": everyday_url(task, {"app": app_, "dark": dark, "labels_top": labels_top, "shuffle": shuffle,
                                       "btn_top": btn_top, "big": big, "nav": nav})}


@app.get("/api/live")
def live_status():
    from . import live as L
    return {"meta": L.meta_live(), "open": L.open_live(), "models": L.MODELS}


@app.get("/api/skills/{sid}/card")
async def skill_card(sid: str):
    """The skill's card, drawn once by Muse Image and kept with the skill."""
    from . import live as L
    p = _skill(sid)
    f = p / "card.webp"
    if not f.exists():
        if not L.meta_live():
            raise HTTPException(404, "no card yet, and no Meta Model API key to draw one")
        prog = json.loads((p / "program.json").read_text())
        meta = json.loads((p / "meta.json").read_text()) if (p / "meta.json").exists() else {}
        img = await L.image_card(meta.get("name", prog.get("name", "Skill")), [st["intent"].split(";")[0] for st in prog["steps"]])
        if not img:
            raise HTTPException(502, "Muse Image did not return a card")
        f.write_bytes(img)
    return FileResponse(f, media_type="image/webp")


@app.get("/api/results")
def results():
    """Benchmark summaries from the result files in runs/ (nothing typed by hand)."""
    out = {}
    for split in ("test", "test2", "dev", "words", "words_dev"):
        f = ROOT / "runs" / f"bench_everyday_{split}" / "results.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        rows = d["rows"]
        for extra in (f"{split}_open",):      # Muse Spark Open runs on the same conditions
            g = ROOT / "runs" / f"bench_everyday_{extra}" / "results.json"
            if g.exists():
                rows = rows + json.loads(g.read_text())["rows"]
        systems = [x for x in ("replay", "replay_new", "nochk", "eidos", "eidos_live", "eidos_open") if any(r["system"] == x for r in rows)]
        summ = {}
        for cond in ("same", "new_data", "redesign", "other_app", "interrupt", "all"):
            summ[cond] = {x: {"success": sum(r["success"] for r in rows if r["system"] == x and (cond == "all" or r["cond"] == cond)),
                              "n": sum(1 for r in rows if r["system"] == x and (cond == "all" or r["cond"] == cond))} for x in systems}
        ei = [r for r in rows if r["system"] == "eidos"]
        summ["agree"] = {"agree": sum(r["says_done"] == r["success"] for r in ei), "n": len(ei),
                         "silent": sum(r["says_done"] and not r["success"] for r in ei)}
        out[f"everyday_{split}"] = {"seed": d["seed"], "systems": systems, "summary": summ}
    f = ROOT / "runs" / "bench_test" / "results.json"
    if f.exists():
        d = json.loads(f.read_text())
        out["sheet_test"] = {"seed": d.get("seed"), "summary": d["summary"]}
    return out


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
