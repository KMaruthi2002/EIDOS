"""Video -> steps -> visual contracts.

Reads a screen-recorded tutorial and recovers what the person did and what
each action changed on screen. Each recovered step carries a visual contract:
the screen region it acted on, the region that changed, and what that region
must show afterwards.

Live mode: SAM 3.1 segments the pointer, click markers, touched controls and
changed regions; Muse Spark reads and names them.
Offline mode (no API key): color segmentation finds the pointer and click
markers, frame differencing finds the changed regions, and OCR reads them.
Both modes write the same output format.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import cv2
import numpy as np

from . import vision as V

# Pointer / click-marker color used by common screen-recording tools' highlight
# (our recordings use the same convention). BGR.
CURSOR_BGR = np.array([111, 45, 255])


@dataclass
class Frame:
    t: float
    img: np.ndarray


@dataclass
class Event:
    kind: str                 # click | drag | type
    t: float
    x: float = 0
    y: float = 0
    x2: float = 0
    y2: float = 0
    text: str = ""


@dataclass
class Step:
    index: int
    action: str               # enter_text | select_range | press_control
    t_start: float
    t_end: float
    point: tuple
    point2: tuple | None = None
    text: str = ""
    target: dict = field(default_factory=dict)
    contract: dict = field(default_factory=dict)
    crops: dict = field(default_factory=dict)
    intent: str = ""


def read_frames(path: Path, fps: float = 15) -> list[Frame]:
    cap = cv2.VideoCapture(str(path))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    every = max(1, int(round(src_fps / fps)))
    frames, i = [], 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        if i % every == 0:
            frames.append(Frame(i / src_fps, img))
        i += 1
    return frames


def pointer_mask(img: np.ndarray) -> np.ndarray:
    d = np.abs(img.astype(int) - CURSOR_BGR).sum(axis=2)
    return (d < 90).astype(np.uint8)


def find_pointer(img: np.ndarray):
    """Pointer tip and whether a click ring is visible in this frame."""
    m = pointer_mask(img)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m)
    tip, ring = None, None
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 25:
            continue
        fill = area / float(w * h)
        if w >= 30 and h >= 30 and fill < 0.45:          # hollow circle = click marker
            ring = (x + w / 2, y + h / 2)
        elif 10 <= w <= 30 and 14 <= h <= 34:            # arrow
            tip = (x + 2, y + 2)
    if ring is None and n > 2:
        # The arrow's white outline can cut the ring into arcs: join nearby pieces and look again.
        n2, _, st2, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((5, 5), np.uint8)))
        for i in range(1, n2):
            x, y, w, h, area = st2[i]
            if 30 <= w <= 70 and 30 <= h <= 70 and area / float(w * h) < 0.6:
                ring = (x + w / 2, y + h / 2)
    return tip, ring


def masked(img: np.ndarray) -> np.ndarray:
    """Frame with the pointer and click marker painted out (for diffs and OCR)."""
    m = cv2.dilate(pointer_mask(img), np.ones((9, 9), np.uint8))
    return cv2.inpaint(img, m, 3, cv2.INPAINT_TELEA)


def detect_events(frames: list[Frame]) -> list[Event]:
    tips = []
    rings = []
    for f in frames:
        tip, ring = find_pointer(f.img)
        tips.append(tip)
        rings.append(ring)
    # A click is the first frame a new ring appears.
    downs = []
    for i, r in enumerate(rings):
        if r is not None and (i == 0 or rings[i - 1] is None):
            downs.append(i)
    events: list[Event] = []
    for k, i in enumerate(downs):
        x, y = rings[i]
        nxt = downs[k + 1] if k + 1 < len(downs) else len(frames)
        # Drag test: the pointer starts travelling immediately after the press
        # (a click is followed by a pause) and the screen changes along the path.
        horizon = min(nxt, i + int(1.5 * 15))
        early = next((tips[j] for j in range(i + 2, min(horizon, i + 4)) if tips[j] is not None), None)
        if early is not None and abs(early[0] - x) + abs(early[1] - y) > 25:
            end = i + 2
            for j in range(i + 3, horizon):
                if tips[j] is None or tips[j - 1] is None:
                    continue
                if abs(tips[j][0] - tips[j - 1][0]) + abs(tips[j][1] - tips[j - 1][1]) < 2:
                    end = j
                    break
                end = j
            ex, ey = tips[end]
            diff = V.changed_box(masked(frames[max(0, i - 1)].img), masked(frames[min(end + 3, nxt - 1)].img))
            if diff and diff[2] > 0.6 * abs(ex - x):
                events.append(Event("drag", frames[i].t, x, y, ex, ey))
                continue
        events.append(Event("click", frames[i].t, x, y))
    # one press can flicker the marker over two frames
    out: list[Event] = []
    for e in events:
        if out and e.kind == out[-1].kind == "click" and e.t - out[-1].t < 0.4 and abs(e.x - out[-1].x) + abs(e.y - out[-1].y) < 20:
            continue
        out.append(e)
    return out


def read_typed_text(frames, i0, i1, box) -> tuple[str, str]:
    """What was typed into the box, and what the box shows afterwards.

    OCR on mid-typing frames is noisy (caret, autocomplete popups), so we
    vote: formulas are recovered from frames showing a complete '=FN(...)'
    expression; plain text is the settled text displayed after Enter.
    """
    from collections import Counter
    final = V.ocr_region(masked(frames[i1 - 1].img), box) if i1 > i0 else ""
    formulas = Counter()
    for j in range(i0, i1, 2):
        t = V.ocr_region(masked(frames[j].img), box).replace(" ", "")
        m = re.search(r"=[A-Z]+\([A-Z]+\d+:[A-Z]+\d+\)", t)
        if m:
            formulas[m.group()] += 1
    if formulas:
        return formulas.most_common(1)[0][0], final
    return final, final


def frame_index(frames, t):
    return min(range(len(frames)), key=lambda i: abs(frames[i].t - t))


def analyze(video: Path, out_dir: Path, headers: list[str] | None = None) -> dict:
    """Run the offline extractor. Writes keyframes/crops and returns the trace."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = read_frames(video)
    events = detect_events(frames)
    # Reference frame: the settled screen shortly before the first action
    # (recordings often start on a blank or loading page).
    t_ref = max(0.0, (events[0].t if events else frames[-1].t) - 0.6)
    first = masked(frames[frame_index(frames, t_ref)].img)
    if headers is None:
        headers = [w.text for w in V.ocr_words(first) if w.text.istitle() and len(w.text) > 3]
    grid = V.infer_grid(first, headers)
    bounds = V.column_bounds(first, grid)

    def cell_box(x, y):
        c = min(range(len(bounds)), key=lambda k: 0 if bounds[k][0] <= x <= bounds[k][1] else abs((bounds[k][0] + bounds[k][1]) / 2 - x))
        l, r = bounds[c]
        yy = _snap_y(grid, y)
        return int(l + 2), int(yy - grid.row_h * 0.45), int(r - l - 3), int(grid.row_h * 0.9)

    steps: list[Step] = []
    selection = None
    in_grid = lambda x, y: y > grid.header_y - grid.row_h * 0.6 and x > grid.headers[0].x - grid.col_pitch * 0.3
    for k, ev in enumerate(events):
        i = frame_index(frames, ev.t)
        nxt_t = events[k + 1].t if k + 1 < len(events) else frames[-1].t + 0.01
        j = frame_index(frames, nxt_t)
        pre = masked(frames[max(0, i - 2)].img)
        post = masked(frames[max(i + 1, j - 1)].img)
        if ev.kind == "drag":
            st = Step(len(steps) + 1, "select_range", ev.t, nxt_t, (ev.x, ev.y), (ev.x2, ev.y2))
            a, b = cell_box(ev.x, ev.y), cell_box(ev.x2, ev.y2)
            selection = (a[0], a[1], b[0] + b[2] - a[0], a[3])
            st.contract["selection_box"] = selection
        elif in_grid(ev.x, ev.y):
            box = cell_box(ev.x, ev.y)
            typed, final = read_typed_text(frames, i + 1, j, box)
            st = Step(len(steps) + 1, "enter_text", ev.t, nxt_t, (ev.x, ev.y), text=typed)
            st.contract["cell_box"] = box
            st.contract["shows"] = final
        else:
            st = Step(len(steps) + 1, "press_control", ev.t, nxt_t, (ev.x, ev.y))
            # The control's look, from the first frame (no pointer over it).
            x, y = int(ev.x), int(ev.y)
            crop = first[max(0, y - 16):y + 16, max(0, x - 16):x + 16]
            cv2.imwrite(str(out_dir / f"step{st.index}_control.png"), crop)
            st.crops["control"] = f"step{st.index}_control.png"
        changed = V.changed_box(pre, post)
        st.contract["changed_box"] = changed
        cv2.imwrite(str(out_dir / f"step{st.index}_pre.png"), pre)
        cv2.imwrite(str(out_dir / f"step{st.index}_post.png"), post)
        st.crops.update({"pre": f"step{st.index}_pre.png", "post": f"step{st.index}_post.png"})
        probe = selection if (st.action == "press_control" and selection) else changed
        if probe:
            st.contract["probe_box"] = probe
            st.contract["ink_before"] = V.ink_ratio(pre, probe)
            st.contract["ink_after"] = V.ink_ratio(post, probe)
        steps.append(st)

    # Merge 'click on a cell' + following 'enter_text' is already one step;
    # drop empty clicks that typed nothing and changed nothing.
    steps = [s for s in steps if not (s.action == "enter_text" and not s.text and not s.contract.get("changed_box"))]
    for n, s in enumerate(steps, 1):
        s.index = n

    trace = {
        "video": video.name,
        "duration": frames[-1].t,
        "frames_analyzed": len(frames),
        "screen": {
            "headers": grid.header_names(),
            "data_rows": len(grid.data_rows_y),
            "row_numbers": [grid.row_labels.get(0), grid.row_labels.get(len(grid.data_rows_y) - 1)],
            "col_pitch": grid.col_pitch, "row_h": grid.row_h,
        },
        "events": [_jsonable(asdict(e)) for e in events],
        "steps": [_jsonable(asdict(s)) for s in steps],
    }
    annotate(trace, grid)
    trace = _jsonable(trace)
    (out_dir / "trace.json").write_text(json.dumps(trace, indent=2))
    return trace


def _snap_x(grid, x):
    return min((w.cx for w in grid.headers), key=lambda c: abs(c - x))


def _snap_y(grid, y):
    ys = grid.data_rows_y + [grid.first_empty_row_y + n * grid.row_h for n in range(3)]
    return min(ys, key=lambda c: abs(c - y))


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


# ---------------------------------------------------------------- semantics

def _row_ref(grid, y):
    if y > grid.data_rows_y[-1] + grid.row_h * 0.5:
        n = round((y - grid.first_empty_row_y) / grid.row_h)
        return "first_empty_after_data" if n == 0 else f"empty_after_data+{n}"
    i = min(range(len(grid.data_rows_y)), key=lambda k: abs(grid.data_rows_y[k] - y))
    return f"data_row[{i}]"


def _col_ref(grid, x):
    w = min(grid.headers, key=lambda h: abs(h.cx - x))
    return w.text


def annotate(trace: dict, grid) -> None:
    """Describe each step in screen-independent terms.

    This is the offline stand-in for Muse Spark: it maps pixel positions to
    table semantics (column names, 'first empty row after the data') and
    explains formula ranges in terms of the table, not cell addresses.
    """
    first_row, last_row = (int(v) for v in trace["screen"]["row_numbers"])
    for s in trace["steps"]:
        x, y = s["point"]
        if s["action"] == "enter_text":
            s["target"] = {"column": _col_ref(grid, x), "row": _row_ref(grid, y)}
            m = re.fullmatch(r"=\s*([A-Z]+)\s*\(\s*([A-Z]+)(\d+)\s*:\s*([A-Z]+)(\d+)\s*\)", s["text"].replace(" ", ""))
            if m:
                fn, c1, r1, c2, r2 = m.groups()
                col_idx = ord(c1) - 65
                col_name = grid.headers[col_idx].text if col_idx < len(grid.headers) else c1
                rows = "all_data_rows" if (int(r1), int(r2)) == (first_row, last_row) else f"rows {r1}-{r2}"
                s["formula"] = {"fn": fn, "column": col_name, "rows": rows, "as_typed": s["text"]}
                s["intent"] = f"{fn.title()} the {col_name} column over {rows.replace('_', ' ')} in the {s['target']['row'].replace('_', ' ')}"
                s["contract"]["expect"] = {"cell_number_equals": f"{fn}({col_name}, {rows})"}
            else:
                s["intent"] = f"Write '{s['text']}' in the {s['target']['column']} column of the {s['target']['row'].replace('_', ' ')}"
                s["contract"]["expect"] = {"cell_text_equals": s["text"]}
        elif s["action"] == "select_range":
            a = _col_ref(grid, s["point"][0])
            b = _col_ref(grid, s["point2"][0])
            whole = a == grid.headers[0].text and b == grid.headers[-1].text
            s["target"] = {"row": _row_ref(grid, y), "from": a, "to": b, "span": "full_table_width" if whole else "partial"}
            s["intent"] = f"Select the {s['target']['row'].replace('_', ' ')} across the {'whole table' if whole else a + ' to ' + b}"
            s["contract"]["expect"] = {"selection_spans": s["target"]["span"]}
        elif s["action"] == "press_control":
            c = s["contract"]
            effect = None
            if c.get("ink_before") is not None and c["ink_after"] > c["ink_before"] * 1.12:
                effect = "text_heavier"
            s["target"] = {"control_look": s["crops"].get("control"), "effect": effect}
            s["intent"] = "Make the selected text bold" if effect == "text_heavier" else "Press a toolbar control"
            s["contract"]["expect"] = {"selection_ink_increases": effect == "text_heavier"}
