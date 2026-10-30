"""Meta Model API client: the live perception and reasoning layer.

    SAM 3.1     find things on screen from a text concept ("bold button",
                "mouse pointer", "the cell that changed") -> boxes/masks
    Muse Spark  read a step: before/after frames + the touched region
                -> what the person intended, in words
    Muse Wonder turn a step trace into a general program (inputs, targets,
                contracts), and check a failed step to suggest a repair
    Muse Image  draw a skill card for the skill library

Set MODEL_API_KEY (or put it in .env) to enable. Without it EIDOS runs offline.
Requests use the Meta Model API Responses format (POST /v1/responses); SAM 3.1
replies in special-token text, parsed by eidos.live.parse_sam.
"""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import cv2
import httpx

# Keys, endpoint and model IDs live in eidos/live.py (one source of truth).
from . import live as _L

API = _L.META_BASE
KEY = _L.META_KEY
MODELS = {"spark": _L.MODELS["spark"], "sam": _L.MODELS["sam"], "wonder": _L.MODELS["wonder"], "image": _L.MODELS["image"]}


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
    """Boxes for `concept` in the image, best first: [{box:[x1,y1,x2,y2], score}] (SAM 3.1 token output)."""
    resp = await _call(MODELS["sam"], [
        {"type": "input_text", "text": concept},
        {"type": "input_image", "image_url": _img_url(img)},
    ], metadata={"include_confidence": "true"})
    return [{"box": b["box"], "score": b["score"]} for b in _L.parse_sam(_text(resp))]


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
    prompt = (f"A minimal, elegant illustration for a learned software skill named "
              f"'{program['name']}'. Flat shapes, one accent color, no text.")
    resp = await _call(MODELS["image"], [{"type": "input_text", "text": prompt}])
    for item in resp.get("output", []):
        for c in item.get("content", []) or []:
            if c.get("type") == "output_image":
                return c.get("image_url")
    return None
