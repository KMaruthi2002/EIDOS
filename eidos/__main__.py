"""EIDOS command line.

  python -m eidos serve                      serve the two test apps on :8765
  python -m eidos record                     record the sample tutorial video
  python -m eidos learn VIDEO OUT_DIR        video -> trace + program (+ contracts)
  python -m eidos run OUT_DIR URL [k=v ...]  run a learned program on an app
  python -m eidos check-live                 call each live model once (needs MODEL_API_KEY and/or BASETEN_API_KEY in .env)
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
    """Call each live model once on real frames and report what came back."""
    import cv2
    from . import live as L
    from . import meta
    if not (L.meta_live() or L.open_live()):
        print("No keys set. Put MODEL_API_KEY (Meta Model API) and/or BASETEN_API_KEY in .env.")
        return
    shot = cv2.imread(str(ROOT / "runs" / "ui_skill_mail" / "step2_pre.png")) if (ROOT / "runs" / "ui_skill_mail" / "step2_pre.png").exists() else None
    if shot is None:
        import numpy as np
        shot = np.full((760, 1200, 3), 255, np.uint8)

    async def attempt(name, coro):
        try:
            out = await coro
            print(f"[ok]   {name}: {json.dumps(out, default=str)[:300]}")
        except Exception as e:                     # report and keep going
            print(f"[fail] {name}: {e!r}"[:400])

    cands = ["Recipient", "Topic", "Body", "Deliver", "Cancel", "Inbox", "Outbox"]
    if L.meta_live():
        await attempt("SAM 3.1      'the text field labelled To'", L.sam_find(shot, "the text field labelled To"))
        await attempt("Muse Spark   match 'To'", L.match_label(shot, "To", "input field label", "Send an email", cands, "spark"))
        await attempt("Muse Wonder  compile", L.wonder_compile([{"do": "press", "label": "Compose"}, {"do": "type", "label": "To", "value": "maya@northwind.com"}], "Send an email"))
        await attempt("Muse Image   skill card", L.image_card("Send an email", ["press Compose", "type To", "press Send"]))
    if L.open_live():
        await attempt("Muse Spark Open (Baseten) match 'Send'", L.match_label(shot, "Send", "button", "Send an email", cands, "open"))
    for c in L.LOG:
        print("  ", c)


if __name__ == "__main__":
    main(sys.argv[1:])
