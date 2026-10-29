"""EIDOS pilot benchmark.

One tutorial video (App A, sales data) is compiled into a program once.
The program then runs under conditions the video never showed:

  same        App A, same data                      (sanity check)
  new_data    App A, different dataset and size     (generalization)
  redesign    App A redesigned: dark theme, sidebar, (robustness to UI change)
              resized cells, reordered columns
  other_app   App B (Jspreadsheet), both datasets    (cross-app transfer)

Systems compared:
  replay        repeat the tutorial's exact clicks and keystrokes
  eidos         full EIDOS (intent program + visual contracts + repair)
  eidos_nochk   EIDOS with contract checking switched off (ablation)

Scoring uses each app's internal state, which the agent never sees.
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eidos.runner import run_program, replay          # noqa: E402
from eidos.score import score_totals                    # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
SKILL = ROOT / "runs" / "tutorial_totals"
OUT = ROOT / "runs" / "bench"
N_REDESIGNS = int(sys.argv[2]) if len(sys.argv) > 2 else 12

DATA = {
    "sales": {"label_column": "Region", "sum_column": "Revenue"},
    "inventory": {"label_column": "Warehouse", "sum_column": "Value"},
}


def conditions():
    out = [
        {"id": "same", "group": "same", "app": "A", "url": f"{BASE}/gridline.html", "data": "sales"},
        {"id": "new_data", "group": "new_data", "app": "A", "url": f"{BASE}/gridline.html?data=inventory", "data": "inventory"},
        {"id": "other_app_sales", "group": "other_app", "app": "B", "url": f"{BASE}/tabula.html", "data": "sales"},
        {"id": "other_app_inventory", "group": "other_app", "app": "B", "url": f"{BASE}/tabula.html?data=inventory", "data": "inventory"},
    ]
    rng = random.Random(7)
    for i in range(N_REDESIGNS):
        order = list(range(5))
        rng.shuffle(order)
        q = {
            "theme": rng.choice(["dark", "light"]),
            "side": rng.choice([0, 120, 180, 240]),
            "colw": rng.choice([90, 110, 130, 150]),
            "rowh": rng.choice([22, 25, 28, 32]),
            "order": ",".join(map(str, order)),
        }
        data = rng.choice(["sales", "inventory"])
        qs = "&".join(f"{k}={v}" for k, v in q.items())
        out.append({"id": f"redesign_{i:02d}", "group": "redesign", "app": "A",
                    "url": f"{BASE}/gridline.html?{qs}&data={data}", "data": data, "mutation": q})
    return out


async def one(cond, system, program, trace, sem):
    async with sem:
        d = OUT / cond["id"] / system
        inputs = {"sum_column": DATA[cond["data"]]["sum_column"]}
        try:
            if system == "replay":
                rep = await replay(trace, cond["url"], d, record=False)
            else:
                rep = await run_program(program, cond["url"], d, inputs=inputs, skill_dir=SKILL,
                                        use_contracts=(system == "eidos"), record=False)
        except Exception as e:                                     # a crash is a failure
            rep = {"error": repr(e), "oracle_state": None}
        sc = score_totals(rep.get("oracle_state"), "Total", DATA[cond["data"]]["label_column"],
                          DATA[cond["data"]]["sum_column"])
        claimed = rep.get("all_contracts_passed")
        row = {"condition": cond["id"], "group": cond["group"], "app": cond["app"], "system": system,
               "success": sc["success"], "detail": sc,
               # EIDOS says whether it believes it succeeded; replay never knows.
               "self_report": claimed if system == "eidos" else None,
               "error": rep.get("error")}
        print(f"{cond['id']:<22} {system:<12} {'PASS' if sc['success'] else 'fail'}"
              f"{'' if row['self_report'] is None else '  (agent says ' + ('ok' if claimed else 'FAILED') + ')'}",
              flush=True)
        return row


async def main():
    program = json.loads((SKILL / "program.json").read_text())
    trace = json.loads((SKILL / "trace.json").read_text())
    sem = asyncio.Semaphore(4)
    conds = conditions()
    rows = await asyncio.gather(*[one(c, s, program, trace, sem)
                                  for c in conds for s in ("replay", "eidos", "eidos_nochk")])
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for g in ("same", "new_data", "redesign", "other_app", "all"):
        for s in ("replay", "eidos", "eidos_nochk"):
            sel = [r for r in rows if r["system"] == s and (g == "all" or r["group"] == g)]
            summary.setdefault(g, {})[s] = {"n": len(sel), "success": sum(r["success"] for r in sel)}
    # Honesty: how often did EIDOS's own verdict match the truth?
    ev = [r for r in rows if r["system"] == "eidos"]
    summary["eidos_self_report"] = {
        "n": len(ev),
        "agrees_with_oracle": sum(1 for r in ev if bool(r["self_report"]) == r["success"]),
        "silent_failures": sum(1 for r in ev if r["self_report"] and not r["success"]),
    }
    rp = [r for r in rows if r["system"] == "replay"]
    summary["replay_silent_failures"] = sum(1 for r in rp if not r["success"])
    (OUT / "results.json").write_text(json.dumps({"conditions": conds, "rows": rows, "summary": summary}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
