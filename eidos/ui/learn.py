"""Learn an everyday skill from a tutorial video: video -> steps -> program.

Works for any app made of the usual parts (buttons, labelled fields,
dropdowns, on/off switches). From the video frames alone it finds each
click, decides what kind of step it was by what the person touched and what
changed, reads the label that identifies the target, and records a visual
contract for the step:

  press   "Compose"            -> afterwards the screen shows "New message", "Subject"
  type    field "Subject"       -> the field shows {subject}
  choose  field "Time"          -> the field shows {time}
  toggle  "Two-factor sign-in"  -> the switch on that row is on (filled with color)

Every value the person typed or picked becomes an input named after its
field, so the same skill runs with new data. Targets are kept by label,
never by position, so the skill survives a redesign.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import cv2

from ..extract import detect_events, frame_index, masked, read_frames
from . import see as S


def clean(t: str) -> str:
    """Field text without the caret, dropdown arrow or focus-ring noise."""
    t = re.sub(r"[|▾▼¥]+", " ", t)
    t = re.sub(r"\s+[A-Za-z]$", "", t.strip()) if re.search(r"\s[vV]$", t.strip()) else t
    return t.strip(" |")


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def element(b, lns) -> bool:
    """A real control, not the outline of a word or the smudge left by the pointer."""
    if b[2] < 36 or b[3] < 18:
        return False
    ink = sum(w.w * w.h for ln in lns for w in ln.words if S.inside(b, w.cx, w.cy) and w.conf != S.SYNTH)
    return ink < 0.45 * b[2] * b[3]


def typed_into(pre, post, b) -> bool:
    """Text inside the field changed while the person typed."""
    before, after = clean(S.read_box(pre, b)), clean(S.read_box(post, b))
    return bool(after) and S.sim(before, after) < 0.8


def label_for(b, lns, bxs=None):
    """Text that labels a field: the nearest line on its left (same row) or just above it.
    Text inside other fields is never a label."""
    x, y, w, h = b
    if bxs:
        # other fields only; a box wrapping this one (a focus ring merged with its label) doesn't count
        fields = [f for f in bxs if S.is_field(f) and not (f[0] <= x + 3 and f[1] <= y + 3 and
                  f[0] + f[2] >= x + w - 3 and f[1] + f[3] >= y + h - 3)]
        lns = [ln for ln in lns if not any(S.inside(f, ln.cx, ln.cy) for f in fields)]
    cys = (y + min(h, 40) / 2, y + h / 2)
    # A label above a field sits right on top of it and starts where the field starts.
    above = [ln for ln in lns if 0 <= y - (ln.y + ln.h) < 26 and abs(ln.x - x) < 16]
    if above:
        return max(above, key=lambda ln: ln.y)
    left = [ln for ln in lns if ln.x + ln.w <= x + 4 and min(abs(ln.cy - c) for c in cys) < 14 and x - (ln.x + ln.w) < 260]
    if left:
        return max(left, key=lambda ln: ln.x + ln.w)
    return None


def row_label(b, lns):
    """Title of the settings row a switch sits on (the top line of the row)."""
    cy = b[1] + b[3] / 2
    c = [ln for ln in lns if abs(ln.cy - cy) < 26 and not S.inside(b, ln.cx, ln.cy)]
    if not c:
        return None
    top = min(ln.y for ln in c)
    return min([ln for ln in c if ln.y - top < 6], key=lambda ln: abs(ln.cx - (b[0] + b[2] / 2)))


def new_phrases(pre_l, post_l, exclude=()):
    out = []
    for ln in post_l:
        t = ln.text.strip(" .")
        if sum(ch.isalnum() for ch in t) < 3:
            continue
        if any(S.sim(t, p.text) > 0.85 and abs(p.cy - ln.cy) < 20 and abs(p.x - ln.x) < 40 for p in pre_l):
            continue
        if any(S.sim(t, e) > 0.8 for e in exclude):
            continue
        if not any(S.sim(t, o) > 0.85 for o in out):
            out.append(t)
    return out


def params_in(text: str, inputs: dict) -> list[str]:
    """Which inputs a phrase on screen shows (e.g. a new row with the merchant and amount)."""
    t, out = S.norm(text), []
    for k, v in sorted(inputs.items(), key=lambda kv: -len(kv[1])):
        v = S.norm(v)
        if len(v) >= 3 and (v in t or S.sim(t, v) > 0.85):
            out.append(k)
            t = t.replace(v, " ")
    return out


def analyze(video: Path, out_dir: Path, name: str | None = None) -> tuple[dict, dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = read_frames(Path(video), fps=15)
    events = [e for e in detect_events(frames) if e.kind == "click"]
    cache = {}

    def look(i):
        if i not in cache:
            img = masked(frames[i].img)
            cache[i] = (img, S.lines(img), S.boxes(img))
        return cache[i]

    steps, raw, inputs = [], [], {}
    k = 0
    while k < len(events):
        e = events[k]
        nxt = events[k + 1] if k + 1 < len(events) else None
        i_pre = frame_index(frames, e.t - 0.15)
        t_post = (nxt.t - 0.2) if nxt else min(frames[-1].t, e.t + 1.3)
        i_post = frame_index(frames, t_post)
        prev_t = events[k - 1].t if k else 0.0
        i_far = frame_index(frames, max(prev_t + 0.4, e.t - 1.0))
        pre, pl, pb = look(i_pre)
        post, ql, qb = look(i_post)
        far, fl, fb = look(i_far)
        pb, pl = fb + pb, fl + [ln for ln in pl if not any(S.sim(ln.text, f.text) > 0.9 and abs(ln.cy - f.cy) < 6 for f in fl)]
        # The element clicked: smallest real box under the click, seen before or after
        # (the pointer itself can leave a small smudge in the pre frame).
        b = S.box_at([bb for bb in pb if element(bb, pl)], e.x, e.y, max_w=900) or \
            S.box_at([bb for bb in qb if element(bb, ql)], e.x, e.y, max_w=900)
        step = {"index": len(steps) + 1, "t": round(e.t, 2), "point": [round(e.x), round(e.y)]}
        raw.append({"t": round(e.t, 2), "x": round(e.x), "y": round(e.y)})
        picked = None
        if b and S.is_field(b) and nxt:
            # Did a list open under the field, and did the next click pick an entry of it?
            opt = [ln for ln in ql if S.inside((ln.x, ln.y, ln.w, ln.h), nxt.x, nxt.y, pad=10)]
            if opt and not any(S.sim(opt[0].text, p.text) > 0.85 and abs(p.cy - opt[0].cy) < 8 for p in pl):
                i_after = frame_index(frames, (events[k + 2].t - 0.2) if k + 2 < len(events) else nxt.t + 1.0)
                shown = S.read_box(look(i_after)[0], b)
                if S.sim(clean(shown), opt[0].text) > 0.8:
                    picked = (opt[0].text, shown)
        if b and S.is_switch(b):
            lab = row_label(b, pl)
            step.update(action="toggle", label=lab.text if lab else "", box=b,
                        before_on=S.is_on(pre, b), after_on=S.is_on(post, b))
        elif b and S.is_field(b) and (picked or typed_into(pre, post, b)):
            lab = label_for(b, pl, pb) or label_for(b, ql, qb)
            label = lab.text if lab else f"field {len(steps) + 1}"
            if picked:
                value = picked[0]
                step.update(action="choose", label=label, value=value, shown=picked[1], box=b)
                raw.append({"t": round(nxt.t, 2), "x": round(nxt.x), "y": round(nxt.y)})
                k += 1
            else:
                # The caret blinks: read the field in a few frames after typing and vote.
                from collections import Counter
                times = [t_post - d for d in (0, 0.3, 0.6, 0.9)] + ([nxt.t + 0.5] if nxt else [])
                reads = [clean(S.read_box(look(frame_index(frames, tt))[0], b)) for tt in times]
                reads = [r for r in reads if r]
                caretless = [r for r in reads if not re.search(r"[\]\[}{|]$", r)]
                pool = caretless or reads
                value = max(pool, key=lambda r: (pool.count(r), len(r))) if pool else ""
                step.update(action="type", label=label, value=value, box=b)
                raw[-1]["typed"] = value
            inputs[slug(label)] = value
        else:
            def words_in(lns, box):
                return " ".join(w.text for ln in lns for w in ln.words if S.inside(box, w.cx, w.cy))
            label = ""
            if b and (b[2] > 420 or b[3] > 64):
                b = None
            if b:
                # read the control with the pointer gone: after the click if it is still there
                label = words_in(fl, b) or words_in(ql, b) or words_in(pl, b)
            if not label:
                near = [ln for ln in fl + pl if S.inside((ln.x, ln.y, ln.w, ln.h), e.x, e.y, pad=8)]
                label = near[0].text if near else ""
            step.update(action="press", label=label, box=b,
                        shows=new_phrases(pl, ql, exclude=[label])[:6])
        cv2.imwrite(str(out_dir / f"step{step['index']}_pre.png"), pre)
        cv2.imwrite(str(out_dir / f"step{step['index']}_post.png"), post)
        steps.append(step)
        k += 1

    trace = {"video": Path(video).name, "duration": round(frames[-1].t, 2), "frames_analyzed": len(frames),
             "screen": list(frames[0].img.shape[1::-1]), "events": raw, "steps": steps}
    program = compile_steps(trace, inputs, name)
    (out_dir / "trace.json").write_text(json.dumps(trace, indent=2, default=int))
    (out_dir / "program.json").write_text(json.dumps(program, indent=2))
    return trace, program


def compile_steps(trace: dict, inputs: dict, name: str | None) -> dict:
    out = []
    for s in trace["steps"]:
        st = {"id": s["index"], "do": s["action"], "video_time": s["t"],
              "evidence": {"pre": f"step{s['index']}_pre.png", "post": f"step{s['index']}_post.png"}}
        if s["action"] == "press":
            keys = list(dict.fromkeys(k for p in s["shows"] for k in params_in(p, inputs)))
            # After a submit, the contract is that the entered values show up on screen.
            # Otherwise (opening a form, switching page) it is the new text that appeared.
            shows = ["{" + k + "}" for k in keys] if keys else s["shows"][:3]
            st.update(target={"text": s["label"]}, contract={"screen_shows": shows},
                      intent=f"Press '{s['label']}'" + (f"; the screen should then show {', '.join(repr(p) for p in shows)}" if shows else ""))
        elif s["action"] in ("type", "choose"):
            key = slug(s["label"])
            st.update(target={"field": s["label"]}, value="{" + key + "}", learned_from=s["value"],
                      contract={"field_shows": "{" + key + "}"},
                      intent=("Type {%s} into the '%s' field" if s["action"] == "type" else "Pick {%s} in the '%s' list") % (key, s["label"]))
        elif s["action"] == "toggle":
            want = bool(s["after_on"])
            st.update(target={"row": s["label"]}, contract={"switch_on": want},
                      intent=f"Make sure '{s['label']}' is {'on' if want else 'off'}")
        out.append(st)
    return {"eidos": "0.2", "kind": "ui", "name": name or "Everyday skill", "learned_from": trace["video"],
            "inputs": inputs, "steps": out}


if __name__ == "__main__":
    import sys
    tr, prog = analyze(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
    for s in prog["steps"]:
        print(s["id"], s["do"], s["intent"], s["contract"])
    print("inputs:", prog["inputs"])
