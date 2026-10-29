"""EIDOS command line.

  python -m eidos serve                      serve the two test apps on :8765
  python -m eidos record                     record the sample tutorial video
  python -m eidos learn VIDEO OUT_DIR        video -> trace + program (+ contracts)
  python -m eidos run OUT_DIR URL [k=v ...]  run a learned program on an app
"""
from __future__ import annotations

import asyncio
import functools
import http.server
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
