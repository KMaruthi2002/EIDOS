"""Meta Model API client: the live perception and reasoning layer.

    SAM 3.1     find things on screen from a text concept ("bold button",
                "mouse pointer", "the cell that changed") -> boxes/masks
    Muse Spark  read a step: before/after frames + the touched region
                -> what the person intended, in words
    Muse Wonder turn a step trace into a general program (inputs, targets,
                contracts), and check a failed step to suggest a repair
    Muse Image  draw a skill card for the skill library

Set META_MODEL_API_KEY to enable. Without it EIDOS runs offline.
Endpoint shape follows the Meta Model API /v1/responses format; the exact
SAM 3.1 output grammar is parsed defensively (JSON first, then numbers).
"""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import cv2
import httpx

# Read a local .env (KEY=value lines) if present, without overriding the shell.
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

API = os.environ.get("META_API_BASE", "https://api.meta.ai/v1")
KEY = os.environ.get("META_MODEL_API_KEY", "")
MODELS = {
    "spark": os.environ.get("MUSE_SPARK_MODEL", "muse-spark-1.3"),
    "sam": os.environ.get("SAM_MODEL", "sam-3.1"),
    "wonder": os.environ.get("MUSE_WONDER_MODEL", "muse-wonder"),
    "image": os.environ.get("MUSE_IMAGE_MODEL", "muse-image"),
}


def live() -> bool:
    return bool(KEY)


def _img_url(img) -> str:
    if isinstance(img, (str, Path)):
        data = Path(img).read_bytes()
    else:
        ok, buf = cv2.imencode(".png", img)
        data = buf.tobytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


async def _call(model: str, content: list, **extra) -> dict:
    async with httpx.AsyncClient(timeout=120, headers={"Authorization": f"Bearer {KEY}"}) as c:
        r = await c.post(f"{API}/responses", json={"model": model, "input": [{"role": "user", "content": content}], **extra})
        r.raise_for_status()
        return r.json()


def _text(resp: dict) -> str:
    out = []
    for item in resp.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") == "output_text":
                out.append(c.get("text", ""))
    return "\n".join(out) or resp.get("output_text", "")


def _json(text: str):
    m = re.search(r"\{.*\}|\[.*\]", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


async def sam_find(img, concept: str) -> list[dict]:
    """Boxes for `concept` in the image, best first: [{box:[x1,y1,x2,y2], score}]."""
    resp = await _call(MODELS["sam"], [
        {"type": "input_image", "image_url": _img_url(img)},
        {"type": "input_text", "text": concept},
    ])
    raw = _text(resp)
    parsed = _json(raw)
    boxes = []
    if isinstance(parsed, dict):
        parsed = parsed.get("detections") or parsed.get("segments") or parsed.get("objects") or []
    if isinstance(parsed, list):
        for d in parsed:
            b = d.get("box") or d.get("bbox") if isinstance(d, dict) else d
            if isinstance(b, dict):
                b = [b.get("x1"), b.get("y1"), b.get("x2"), b.get("y2")]
            if b and len(b) >= 4:
                boxes.append({"box": [float(v) for v in b[:4]], "score": float(d.get("score", 0.9)) if isinstance(d, dict) else 0.9})
    if not boxes:
        nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", raw)]
        for i in range(0, len(nums) - 3, 4):
            boxes.append({"box": nums[i:i + 4], "score": 0.5})
    return sorted(boxes, key=lambda b: -b["score"])


async def spark_read_step(pre, post, point, changed_box) -> dict:
    """Ask Muse Spark what a step was for."""
    prompt = (
        "These are two frames from a screen-recorded software tutorial, before and after one action. "
        f"The person acted at pixel {list(map(int, point))}; the region that changed is {changed_box}. "
        "Describe the step in terms that would still make sense if the app looked different "
        "(column names, 'first empty row below the data', control purpose), never pixel positions. "
        'Reply as JSON: {"action": "...", "intent": "...", "target": {...}, "expected_result": "..."}'
    )
    resp = await _call(MODELS["spark"], [
        {"type": "input_image", "image_url": _img_url(pre)},
        {"type": "input_image", "image_url": _img_url(post)},
        {"type": "input_text", "text": prompt},
    ], temperature=0.2)
    return _json(_text(resp)) or {"raw": _text(resp)}


async def wonder_compile(trace: dict) -> dict | None:
    """Ask Muse Wonder to generalize a trace into an EIDOS program."""
    prompt = (
        "You compile screen-recorded demonstrations into reusable agent programs.\n"
        "Given this step trace (from one video), output an EIDOS program as JSON with keys "
        "name, inputs, steps. Each step: do, intent, target (semantic, no pixels), contract "
        "(what the screen must show after the step). Turn values that were specific to the video "
        "(names, ranges, sizes) into inputs or relative references, and explain each formula's range "
        "in terms of the table.\n\nTRACE:\n" + json.dumps(trace)[:60000]
    )
    resp = await _call(MODELS["wonder"], [{"type": "input_text", "text": prompt}], reasoning={"effort": "high"})
    return _json(_text(resp))


async def image_skill_card(program: dict) -> str | None:
    """A small illustrated card for the skill library."""
    prompt = (f"A minimal, elegant trading-card style illustration for a learned software skill named "
              f"'{program['name']}'. Abstract spreadsheet motif, one accent color, no text.")
    resp = await _call(MODELS["image"], [{"type": "input_text", "text": prompt}])
    for item in resp.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") == "output_image":
                return c.get("image_url")
    return None
