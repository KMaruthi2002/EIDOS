"""The live path, end to end, against a fake Meta server (a test double, not the real models).

The fake plays Muse Spark with a fixed synonym table, so these tests show that EIDOS asks
the right question, uses only answers that are on screen, and still checks every step.
They say nothing about how well the real models answer."""
import json
import random
import re
from pathlib import Path

import httpx
import pytest
from eidos import live as L
from eidos.ui.run import run_ui
from eidos.ui.tasks import URL, fresh_inputs, score

ROOT = Path(__file__).resolve().parent.parent
SYN = {"Compose": "New email", "To": "Recipient", "Subject": "Topic", "Message": "Body", "Send": "Deliver",
       "New message": "Write an email", "New expense": "Add receipt", "Merchant": "Vendor", "Amount": "Total",
       "Category": "Kind", "Submit": "Send for approval", "Security": "Privacy and safety",
       "Two-factor sign-in": "Two-step verification", "Recovery email": "Backup email", "Save changes": "Apply",
       "Settings saved": "Changes applied", "Sign-in and security": "Account protection"}


def fake_meta(lie=False):
    def handler(req: httpx.Request):
        body = json.loads(req.content)
        text = next(c["text"] for c in body["input"][0]["content"] if c["type"] == "input_text")
        if body["model"] == L.MODELS["sam"]:
            return httpx.Response(200, json={"output_text": "<0f>"})
        wanted = re.search(r'labelled "([^"]+)"', text).group(1)
        cands = re.findall(r"^- (.*)$", text, re.M)
        ans = "Totally Made Up" if lie else SYN.get(wanted, "NONE")
        hit = next((c for c in cands if c.lower() == ans.lower()), None)
        return httpx.Response(200, json={"output_text": json.dumps({"answer": hit or ("NONE" if not lie else ans)})})
    return handler


@pytest.fixture
def patched(monkeypatch):
    def use(handler):
        real = httpx.AsyncClient
        monkeypatch.setattr(L.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
        monkeypatch.setattr(L, "META_KEY", "test-key")
        monkeypatch.setattr(L, "BASETEN_KEY", "")
    return use


def prog(task):
    return json.loads((ROOT / "runs" / f"ui_skill_{task}" / "program.json").read_text())


@pytest.mark.slow
@pytest.mark.parametrize("task", ["mail", "expense", "settings"])
async def test_renamed_controls_need_the_model(studio, patched, task, tmp_path):
    p = prog(task)
    inputs = {**p["inputs"], **fresh_inputs(task, random.Random(3))}
    url = f"{studio}{URL}?task={task}&skin=A&words=alt"
    off = await run_ui(p, url, tmp_path / "off", inputs, live=False)
    assert not off["all_contracts_passed"] and not score(task, off["oracle_state"], inputs)["success"]
    patched(fake_meta())
    on = await run_ui(p, url, tmp_path / "on", inputs, live=True)
    assert score(task, on["oracle_state"], inputs)["success"], on["aliases"]
    assert on["all_contracts_passed"] and on["aliases"] and on["model_calls"]


@pytest.mark.slow
async def test_an_answer_that_is_not_on_screen_is_rejected(studio, patched, tmp_path):
    patched(fake_meta(lie=True))
    p = prog("mail")
    rep = await run_ui(p, f"{studio}{URL}?task=mail&skin=A&words=alt", tmp_path, p["inputs"], live=True)
    assert not rep["all_contracts_passed"] and not rep["aliases"]


def test_sam_tokens_parsed():
    t = "<0f>0<|box;x1=353;y1=382;x2=453;y2=427;w=537;h=561|><|mask;x=0;y=0;data=46,101,~abc|>,1<|box;x1=1;y1=2;x2=3;y2=4;w=537;h=561;c=0.5|><|mask;x=0;y=0;data=1,1,~a|>"
    b = L.parse_sam(t)
    assert b[0]["box"] == [353.0, 382.0, 453.0, 427.0] and b[0]["frame"] == (537, 561) and b[1]["score"] == 0.5
