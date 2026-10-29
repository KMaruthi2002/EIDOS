"""Benchmark scorer. Uses each app's internal state (the oracle), which the
agent never sees, to decide whether a run truly completed the task."""
from __future__ import annotations

import re

from .vision import similar


def _rows(state):
    return [[c["v"] for c in r] for r in state["cells"]]


def score_totals(state: dict, label: str, label_column: str, sum_column: str) -> dict:
    """Did the run add a bold totals row with a correct SUM of sum_column?"""
    if not state:
        return {"success": False, "why": "no state"}
    rows = _rows(state)
    header = rows[0]
    def col(name):
        for j, h in enumerate(header):
            if similar(str(h), name) > 0.85:
                return j
        return None
    lc, sc = col(label_column), col(sum_column)
    if lc is None or sc is None:
        return {"success": False, "why": "columns missing"}
    # data rows = rows before the first row whose label cell is the label or empty
    n = 1
    while n < len(rows) and lc < len(rows[n]) and rows[n][lc] not in ("", label):
        n += 1
    data = rows[1:n]
    expected = sum(float(r[sc]) for r in data if sc < len(r) and str(r[sc]).replace(".", "").isdigit())
    tr = n
    if tr >= len(rows):
        return {"success": False, "why": "no totals row", "expected": expected}
    cells = state["cells"][tr]
    label_ok = lc < len(cells) and cells[lc]["v"] == label
    f = cells[sc]["v"] if sc < len(cells) else ""
    m = re.fullmatch(r"=SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)", str(f).replace(" ", ""))
    sum_ok = False
    got = None
    if m:
        c1, r1, c2, r2 = m.groups()
        ci = ord(c1) - 65
        # App A: sheet row k is oracle index k-1. App B: data row k is oracle index k.
        off = -1 if state["app"] == "A" else 0
        vals = [float(rows[k + off][ci]) for k in range(int(r1), int(r2) + 1)
                if 0 <= k + off < len(rows) and ci < len(rows[k + off]) and str(rows[k + off][ci]).replace(".", "").isdigit()]
        got = sum(vals)
        sum_ok = c1 == c2 and abs(got - expected) < 0.5 and ci == sc
    bold_ok = label_ok and sc < len(cells) and cells[lc]["bold"] and cells[sc]["bold"]
    return {"success": bool(label_ok and sum_ok and bold_ok), "label_ok": label_ok, "sum_ok": sum_ok,
            "bold_ok": bool(bold_ok), "formula": f, "expected": expected, "got": got}
