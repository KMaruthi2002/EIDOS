"""EIDOS command line.

  python -m eidos serve                      serve the two test apps on :8765
  python -m eidos record                     record the sample tutorial video
  python -m eidos learn VIDEO OUT_DIR        video -> trace + program (+ contracts)
  python -m eidos run OUT_DIR URL [k=v ...]  run a learned program on an app
  python -m eidos check-live                 call each Meta model once (needs META_MODEL_API_KEY)
  python -m eidos studio [PORT]              the EIDOS Studio app at http://localhost:8000
                                             (also serves the everyday apps at /apps/everyday/)

Everyday tasks (mail, calendar, expense, settings; start the Studio first):
  python -m eidos record-ui [TASK ...]       record the tutorial videos
  python -m eidos learn-ui VIDEO OUT_DIR     video -> trace + program
  python -m eidos run-ui OUT_DIR TASK [QUERY] [--checks-off] [--new-data]
        QUERY sets the app's design, e.g. "skin=B&theme=dark&order=2,0,1&popup=4"
"""
from __future__ import annotations

import asyncio
import functools
import http.server
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_UI = "http://localhost:8000"   # the Studio serves the everyday apps


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = argv[0]
    if cmd == "serve":
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "apps"))
        print("Serving the test apps at http://localhost:8765 (gridline.html = App A, tabula.html = App B)")
        http.server.ThreadingHTTPServer(("", 8765), handler).serve_forever()
    elif cmd == "record":
        from .recorder import record_totals_tutorial
        base = argv[1] if len(argv) > 1 else "http://localhost:8765"
        print(asyncio.run(record_totals_tutorial(base, ROOT / "videos")))
    elif cmd == "learn":
        from .compiler import compile_trace
        from .extract import analyze
        from . import meta
        video, out = Path(argv[1]), Path(argv[2])
        trace = analyze(video, out)
        program = compile_trace(trace)
        if meta.live():
            # Muse Wonder writes the program; keep the offline one for comparison.
            live_prog = asyncio.run(meta.wonder_compile(trace))
            if live_prog:
                (out / "program.wonder.json").write_text(json.dumps(live_prog, indent=2))
        (out / "program.json").write_text(json.dumps(program, indent=2))
        for s in program["steps"]:
            print(f"{s['id']}. {s['intent']}")
        print(f"\nProgram written to {out / 'program.json'}")
    elif cmd == "run":
        from .runner import run_program
        out, url = Path(argv[1]), argv[2]
        inputs = dict(kv.split("=", 1) for kv in argv[3:])
        program = json.loads((out / "program.json").read_text())
        rep = asyncio.run(run_program(program, url, out / "run", inputs=inputs, skill_dir=out))
        for s in rep["steps"]:
            mark = "ok " if s["passed"] else "FAIL"
            print(f"[{mark}] {s['intent']}")
            for c in s["checks"]:
                print(f"         {c['contract']}: {'pass' if c['pass'] else 'fail'}")
        print("\nAll contracts passed." if rep["all_contracts_passed"] else "\nStopped: a contract failed.")
    elif cmd == "record-ui":
        from .ui.recorder import record
        from .ui.tasks import TUTORIALS
        for t in argv[1:] or list(TUTORIALS):
            print(asyncio.run(record(t, BASE_UI, ROOT / "videos")))
    elif cmd == "learn-ui":
        from .ui.learn import analyze as ui_analyze
        trace, prog = ui_analyze(Path(argv[1]), Path(argv[2]))
        for s in prog["steps"]:
            print(f"{s['id']}. {s['intent']}")
        print("inputs:", prog["inputs"])
    elif cmd == "run-ui":
        import random
        from .ui.run import run_ui
        from .ui.tasks import URL, fresh_inputs, score
        out, task = Path(argv[1]), argv[2]
        rest = [a for a in argv[3:] if not a.startswith("--")]
        query = rest[0] if rest else "skin=A"
        program = json.loads((out / "program.json").read_text())
        inputs = fresh_inputs(task, random.Random()) if "--new-data" in argv else {}
        url = f"{BASE_UI}{URL}?task={task}&{query}"
        rep = asyncio.run(run_ui(program, url, out / "run", inputs, use_contracts="--checks-off" not in argv))
        for s in rep["steps"]:
            print(f"[{'ok ' if s['passed'] else 'FAIL'}] {s['intent']}")
            for c in s["checks"]:
                print(f"         {c['contract']}: {'pass' if c['pass'] else 'fail'}")
        print("\nAgent says:", "done, every check passed" if rep["all_contracts_passed"] else "stopped, a check failed")
        print("Truth (app state):", score(task, rep["oracle_state"], {**program["inputs"], **inputs}))
    elif cmd == "studio":
        from .studio import main as studio
        studio(int(argv[1]) if len(argv) > 1 else 8000)
    elif cmd == "check-live":
        asyncio.run(check_live())
    else:
        print(__doc__)


async def check_live():
    """Smoke-test the four Meta models on a real frame from the sample tutorial."""
    import cv2
    from . import meta
    if not meta.live():
        print("META_MODEL_API_KEY is not set.")
        return
    skill = ROOT / "runs" / "tutorial_totals"
    pre = cv2.imread(str(skill / "step4_pre.png"))
    post = cv2.imread(str(skill / "step4_post.png"))
    trace = json.loads((skill / "trace.json").read_text())

    async def attempt(name, coro):
        try:
            out = await coro
            print(f"[ok]   {name}: {json.dumps(out)[:300]}")
        except Exception as e:                     # report and keep going
            print(f"[fail] {name}: {e!r}"[:400])

    await attempt("SAM 3.1   'bold text button'", meta.sam_find(pre, "bold text button"))
    await attempt("SAM 3.1   'mouse pointer'", meta.sam_find(post, "mouse pointer"))
    await attempt("Muse Spark read step 4", meta.spark_read_step(pre, post, (388, 60), trace["steps"][3]["contract"].get("changed_box")))
    await attempt("Muse Wonder compile", meta.wonder_compile(trace))
    await attempt("Muse Image skill card", meta.image_skill_card({"name": "Add a totals row"}))


if __name__ == "__main__":
    main(sys.argv[1:])
