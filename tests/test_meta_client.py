"""The Meta Model API client against a fake server (a test double, not the real API).

These tests pin down the request shape and the parsing of replies, so the live path
can be switched on with a key without surprises. They say nothing about model quality."""
import asyncio
import json

import httpx
import pytest
from eidos import meta


@pytest.fixture
def fake(monkeypatch):
    seen = []

    def handler(req: httpx.Request):
        body = json.loads(req.content)
        seen.append({"url": str(req.url), "auth": req.headers.get("authorization"), "body": body})
        model = body["model"]
        if model == meta.MODELS["sam"]:
            text = "<0f>0<|box;x1=10;y1=20;x2=110;y2=60;w=10;h=10;c=0.97|><|mask;x=0;y=0;data=1,1,~a|>,1<|box;x1=0;y1=0;x2=5;y2=5;w=10;h=10;c=0.2|><|mask;x=0;y=0;data=1,1,~a|>"
        elif model == meta.MODELS["spark"]:
            text = 'Here you go: {"action": "type", "intent": "Type the recipient", "target": {"field": "To"}}'
        elif model == meta.MODELS["wonder"]:
            text = json.dumps({"name": "Send an email", "inputs": {"to": "x"}, "steps": []})
        else:
            return httpx.Response(200, json={"output": [{"content": [{"type": "output_image", "image_url": "data:image/png;base64,AAAA"}]}]})
        return httpx.Response(200, json={"output": [{"content": [{"type": "output_text", "text": text}]}]})

    real = httpx.AsyncClient
    monkeypatch.setattr(meta.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(meta, "KEY", "test-key")
    return seen


def test_sam_boxes_parsed_and_ranked(fake):
    import numpy as np
    boxes = asyncio.run(meta.sam_find(np.zeros((10, 10, 3), np.uint8), "the text field labelled To"))
    assert boxes[0] == {"box": [10.0, 20.0, 110.0, 60.0], "score": 0.97}
    assert fake[0]["auth"] == "Bearer test-key" and fake[0]["url"].endswith("/responses")
    content = fake[0]["body"]["input"][0]["content"]
    assert content[0]["text"] == "the text field labelled To" and content[1]["type"] == "input_image"


def test_spark_json_extracted_from_prose(fake):
    import numpy as np
    z = np.zeros((10, 10, 3), np.uint8)
    out = asyncio.run(meta.spark_read_step(z, z, (5, 5), [0, 0, 10, 10]))
    assert out["target"] == {"field": "To"}


def test_wonder_and_image(fake):
    assert asyncio.run(meta.wonder_compile({"steps": []}))["name"] == "Send an email"
    assert asyncio.run(meta.image_skill_card({"name": "Send an email"})).startswith("data:image/png")


def test_offline_without_key(monkeypatch):
    monkeypatch.setattr(meta, "KEY", "")
    assert not meta.live()
