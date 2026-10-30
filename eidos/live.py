"""The live model layer: Meta Model API (SAM 3.1, Muse Spark, Muse Wonder, Muse Image)
and Muse Spark Open on Baseten.

Keys come from the environment or a local .env file (never committed):
    MODEL_API_KEY       Meta Model API          https://api.meta.ai/v1
    BASETEN_API_KEY     Baseten (Muse Spark Open, OpenAI-compatible)
    EIDOS_READER        which model reads screens: "spark" (default) or "open" (Muse Spark Open)

Everything a model says is treated as a proposal and checked against the screen:
a label it picks must be text that is actually on the screen, and a box SAM returns
is compared with the box found from pixels.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import cv2
import httpx

_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

META_BASE = os.environ.get("META_API_BASE", "https://api.meta.ai/v1")
META_KEY = os.environ.get("MODEL_API_KEY") or os.environ.get("META_MODEL_API_KEY", "")
BASETEN_BASE = os.environ.get("BASETEN_API_BASE", "https://inference.baseten.co/v1")
BASETEN_KEY = os.environ.get("BASETEN_API_KEY", "")
MODELS = {
    "spark": os.environ.get("MUSE_SPARK_MODEL", "muse-spark-1.3"),
    "wonder": os.environ.get("MUSE_WONDER_MODEL", "muse-wonder-1.0"),
    "image": os.environ.get("MUSE_IMAGE_MODEL", "muse-image-1.0"),
    "sam": os.environ.get("SAM_MODEL", "sam-3.1"),
    "open": os.environ.get("MUSE_OPEN_MODEL", "meta-models/muse-spark-open"),
}
LOG: list[dict] = []          # every live call made in this process: model, purpose, seconds, ok


def meta_live() -> bool:
    return bool(META_KEY)


def open_live() -> bool:
    return bool(BASETEN_KEY)


def works(which: str) -> bool:
    """One tiny real call, to tell a working key from a present but rejected one."""
    try:
        if which == "open":
            r = httpx.post(f"{BASETEN_BASE}/chat/completions", headers={"Authorization": f"Bearer {BASETEN_KEY}"},
                           json={"model": MODELS["open"], "messages": [{"role": "user", "content": "ok"}], "max_tokens": 1}, timeout=60)
        else:
            r = httpx.post(f"{META_BASE}/responses", headers={"Authorization": f"Bearer {META_KEY}"},
                           json={"model": MODELS["spark"], "input": "ok", "max_output_tokens": 16}, timeout=60)
        return r.status_code < 400
    except Exception:
        return False


def reader() -> str | None:
    """Which model reads screens for meaning, if any key is set."""
    want = os.environ.get("EIDOS_READER", "spark")
    if want == "open" and open_live():
        return "open"
    if meta_live():
        return "spark"
    if open_live():
        return "open"
    return None


def data_url(img, quality: int = 80) -> str:
    if isinstance(img, (str, Path)):
        img = cv2.imread(str(img))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def _record(model, purpose, t0, ok, err=None):
    LOG.append({"model": model, "purpose": purpose, "seconds": round(time.monotonic() - t0, 2), "ok": ok,
                **({"error": err} if err else {})})


async def meta_responses(model: str, content: list, purpose: str, **extra) -> dict:
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=120, headers={"Authorization": f"Bearer {META_KEY}"}) as c:
            r = await c.post(f"{META_BASE}/responses",
                             json={"model": model, "input": [{"role": "user", "content": content}], **extra})
            r.raise_for_status()
            out = r.json()
        _record(model, purpose, t0, True)
        return out
    except Exception as e:
        _record(model, purpose, t0, False, repr(e)[:200])
        raise


async def baseten_chat(content: list, purpose: str, **extra) -> str:
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=120, headers={"Authorization": f"Bearer {BASETEN_KEY}"}) as c:
            r = await c.post(f"{BASETEN_BASE}/chat/completions",
                             json={"model": MODELS["open"], "messages": [{"role": "user", "content": content}], **extra})
            r.raise_for_status()
            out = r.json()["choices"][0]["message"]["content"]
        _record(MODELS["open"], purpose, t0, True)
        return out if isinstance(out, str) else json.dumps(out)
    except Exception as e:
        _record(MODELS["open"], purpose, t0, False, repr(e)[:200])
        raise


def output_text(resp: dict) -> str:
    if resp.get("output_text"):
        return resp["output_text"]
    parts = []
    for item in resp.get("output", []) or []:
        for c in item.get("content", []) or []:
            if c.get("type") in ("output_text", "text"):
                parts.append(c.get("text", ""))
    return "".join(parts)


def first_json(text: str):
    m = re.search(r"\{.*\}|\[.*\]", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- reading for meaning

async def ask_reader(img, prompt: str, purpose: str, which: str | None = None) -> str:
    which = which or reader()
    if which == "spark":
        resp = await meta_responses(MODELS["spark"], [{"type": "input_image", "image_url": data_url(img)},
                                                      {"type": "input_text", "text": prompt}], purpose)
        return output_text(resp)
    if which == "open":
        return await baseten_chat([{"type": "image_url", "image_url": {"url": data_url(img)}},
                                   {"type": "text", "text": prompt}], purpose, temperature=0)
    raise RuntimeError("no model key set")


async def match_label(img, wanted: str, role: str, task: str, candidates: list[str], which: str | None = None) -> str | None:
    """Which text on this screen plays the role that `wanted` played in the tutorial?

    The answer must be one of `candidates` (text read off this screen), so the result can
    be grounded and checked from pixels like any other label."""
    cands = list(dict.fromkeys(c for c in candidates if 1 < len(c) <= 80))[:120]
    prompt = (
        f"You are helping a software agent repeat a task it learned from a tutorial video: {task}.\n"
        f"In the tutorial, the {role} was labelled \"{wanted}\". This screenshot is a different design of the app, "
        f"where wording may differ.\nHere is the text visible on this screen:\n"
        + "\n".join(f"- {c}" for c in cands)
        + f"\n\nWhich one of these is the {role} that means the same as \"{wanted}\" here? "
        "Answer with exactly one item copied from the list, or NONE if nothing matches. "
        'Reply as JSON: {"answer": "..."}'
    )
    text = await ask_reader(img, prompt, f"match '{wanted}'", which)
    j = first_json(text)
    ans = (j or {}).get("answer") if isinstance(j, dict) else None
    if not ans:
        m = re.search(r'"?answer"?\s*[:=]\s*"([^"]+)"', text or "")
        ans = m.group(1) if m else None
    if not ans or ans.strip().upper() == "NONE":
        return None
    ans = ans.strip()
    # must be on the screen: exact candidate, or the closest one if the model changed case/spacing
    from difflib import SequenceMatcher
    best = max(cands, key=lambda c: SequenceMatcher(None, c.lower(), ans.lower()).ratio(), default=None)
    if best and SequenceMatcher(None, best.lower(), ans.lower()).ratio() >= 0.85:
        return best
    return None


# --------------------------------------------------------------------------- SAM 3.1

BOX = re.compile(r"<\|box;([^|]*)\|>")


def parse_sam(text: str) -> list[dict]:
    """Boxes from SAM 3.1's special-token output: <Nf>id<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..[;c=..]|><|mask;...|>"""
    out = []
    for m in BOX.finditer(text or ""):
        kv = dict(p.split("=", 1) for p in m.group(1).split(";") if "=" in p)
        try:
            x1, y1, x2, y2 = (float(kv[k]) for k in ("x1", "y1", "x2", "y2"))
        except (KeyError, ValueError):
            continue
        out.append({"box": [x1, y1, x2, y2], "score": float(kv.get("c", 1.0)),
                    "frame": (int(kv["w"]), int(kv["h"])) if "w" in kv and "h" in kv else None})
    return sorted(out, key=lambda b: -b["score"])


async def sam_find(img, phrase: str) -> list[dict]:
    resp = await meta_responses(MODELS["sam"], [{"type": "input_text", "text": phrase},
                                                {"type": "input_image", "image_url": data_url(img, 90)}],
                                f"SAM '{phrase}'", metadata={"include_confidence": "true"})
    boxes = parse_sam(output_text(resp))
    h, w = img.shape[:2]
    for b in boxes:        # scale if SAM reports a different frame size
        if b["frame"] and b["frame"] != (w, h):
            sx, sy = w / b["frame"][0], h / b["frame"][1]
            b["box"] = [b["box"][0] * sx, b["box"][1] * sy, b["box"][2] * sx, b["box"][3] * sy]
    return boxes


def iou(a, b) -> float:
    """a, b as [x1, y1, x2, y2]."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


# --------------------------------------------------------------------------- learning-time models

async def wonder_compile(steps: list[dict], task: str) -> dict | None:
    prompt = (
        "You turn a screen-recorded demonstration into a reusable agent program.\n"
        f"Task: {task}. Here are the steps recovered from the video (JSON). Return JSON with keys "
        "\"name\", \"inputs\" (each typed or picked value becomes a named input) and \"steps\" "
        "(each with \"do\" in press|type|choose|toggle, \"target\" naming the control by its label, "
        "\"intent\" in plain words, and \"contract\": what must newly be true on screen afterwards). "
        "Never use pixel positions.\n\nSTEPS:\n" + json.dumps(steps)[:40000]
    )
    resp = await meta_responses(MODELS["wonder"], [{"type": "input_text", "text": prompt}], "compile program",
                                reasoning={"effort": "medium"})
    return first_json(output_text(resp))


async def image_card(name: str, steps: list[str]) -> bytes | None:
    t0 = time.monotonic()
    prompt = (f"A clean, minimal illustration for a skill card titled \"{name}\". The skill: " + "; ".join(steps)[:400]
              + ". Flat shapes, cool blue palette, a dashed outline motif, no text, no logos.")
    try:
        async with httpx.AsyncClient(timeout=180, headers={"Authorization": f"Bearer {META_KEY}"}) as c:
            r = await c.post(f"{META_BASE}/images/generations",
                             json={"model": MODELS["image"], "prompt": prompt, "size": "1024x1024", "response_format": "b64_json"})
            r.raise_for_status()
            d = r.json()["data"][0]
        _record(MODELS["image"], "skill card", t0, True)
        if d.get("b64_json"):
            return base64.b64decode(d["b64_json"])
        if d.get("url"):
            async with httpx.AsyncClient(timeout=60) as c:
                return (await c.get(d["url"])).content
    except Exception as e:
        _record(MODELS["image"], "skill card", t0, False, repr(e)[:200])
    return None
