"""Record the runs shown in the demo (with video), plus their baselines."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eidos.runner import run_program, replay      # noqa: E402
from eidos.score import score_totals                # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
SKILL = ROOT / "runs" / "tutorial_totals"
OUT = ROOT / "runs" / "showcase"

CASES = [
    {"id": "same", "title": "Same app, same data", "url": f"{BASE}/gridline.html",
     "data": ("Region", "Revenue")},
    {"id": "new_data", "title": "New data the video never showed", "url": f"{BASE}/gridline.html?data=inventory",
     "data": ("Warehouse", "Value")},
    {"id": "redesign", "title": "App redesigned: dark theme, sidebar, bigger cells, columns shuffled",
     "url": f"{BASE}/gridline.html?theme=dark&side=180&colw=140&rowh=32&order=4,0,1,2,3",
     "data": ("Region", "Revenue")},
    {"id": "other_app", "title": "A different app (Jspreadsheet)", "url": f"{BASE}/tabula.html",
     "data": ("Region", "Revenue")},
]


async def main():
    program = json.loads((SKILL / "program.json").read_text())
    trace = json.loads((SKILL / "trace.json").read_text())
    index = []
    for c in CASES:
        label_col, sum_col = c["data"]
        e = await run_program(program, c["url"], OUT / c["id"] / "eidos", inputs={"sum_column": sum_col, "label_column": label_col},
                              skill_dir=SKILL)
        r = await replay(trace, c["url"], OUT / c["id"] / "replay")
        se = score_totals(e["oracle_state"], "Total", label_col, sum_col)
        sr = score_totals(r["oracle_state"], "Total", label_col, sum_col)
        index.append({**{k: c[k] for k in ("id", "title", "url")}, "eidos": se, "replay": sr,
                      "eidos_self_report": e["all_contracts_passed"]})
        print(c["id"], "eidos", se["success"], "replay", sr["success"], flush=True)
    (OUT / "index.json").write_text(json.dumps(index, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
