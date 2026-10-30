"""Teaching live: a recording made through the Studio's teach API is learned and runs elsewhere."""
import json
import time

import httpx
import pytest

from eidos.studio import score_taught


def test_score_taught():
    state = {"records": [{"to": "a@b.co", "subject": "Hi", "message": ""}], "settings": {}, "saves": 0}
    assert score_taught("mail", state, {"to": "a@b.co", "subject": "Hi"})["success"]
    assert not score_taught("mail", state, {"to": "x@b.co", "subject": "Hi"})["success"]
    st = {"records": [], "settings": {"Two-factor sign-in": True, "Recovery email": "r@x.io"}, "saves": 1}
    assert score_taught("settings", st, {"recovery_email": "r@x.io"})["success"]
    assert not score_taught("settings", {**st, "saves": 0}, {"recovery_email": "r@x.io"})["success"]


def test_teach_rejects_unknown(studio):
    assert httpx.post(f"{studio}/api/teach/start", json={"task": "nope"}).status_code == 400
    assert httpx.post(f"{studio}/api/teach/teach-missing/input", json={"events": []}).status_code == 404
    assert httpx.delete(f"{studio}/api/skills/sample-mail").status_code == 400


def _sse(resp):
    for chunk in resp.iter_text():
        for block in chunk.split("\n\n"):
            if block.startswith("event: "):
                ev, data = block.split("\n", 1)
                yield ev[7:], json.loads(data[6:])


@pytest.mark.slow
def test_teach_learn_run(studio):
    """Record Mail live through the API (as the Studio page would), learn it, run it on design B with new values."""
    from playwright.sync_api import sync_playwright
    c = httpx.Client(base_url=studio, timeout=300)
    tid = c.post("/api/teach/start", json={"task": "mail"}).json()["id"]
    # where things are on design A, read from a reference page (the test plays the person)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ref = b.new_page(viewport={"width": 1200, "height": 760})
        ref.goto(f"{studio}/apps/everyday/index.html?task=mail&skin=A")

        def at(loc):
            bb = loc.bounding_box()
            return bb["x"] + min(bb["width"] / 2, 60), bb["y"] + bb["height"] / 2

        def click(loc):
            x, y = at(loc)
            c.post(f"/api/teach/{tid}/input", json={"events": [{"type": "move", "x": x, "y": y}, {"type": "down", "x": x, "y": y},
                                                              {"type": "up", "x": x, "y": y}]})
            time.sleep(0.5)
            c.post(f"/api/teach/{tid}/input", json={"events": [{"type": "move", "x": x + 30, "y": y + 44}]})
            time.sleep(0.4)
            loc.click()

        def field(label):
            return ref.locator(".field", has=ref.locator("label", has_text=label)).locator(".input").first

        click(ref.get_by_text("Compose", exact=True).first)
        for label, value in (("To", "omar@acme.io"), ("Subject", "Room booking"), ("Message", "Booked for Monday.")):
            click(field(label))
            for ch in value:
                c.post(f"/api/teach/{tid}/input", json={"events": [{"type": "text", "text": ch}]})
            time.sleep(0.8)
            field(label).type(value)
        click(ref.get_by_text("Send", exact=True).first)
        time.sleep(1.0)
        b.close()
    sid, steps = None, []
    with c.stream("POST", f"/api/teach/{tid}/finish", json={"name": "Book a room"}) as r:
        for ev, d in _sse(r):
            if ev == "step":
                steps.append(d["do"])
            if ev == "done":
                sid = d["skill"]
            if ev == "error":
                pytest.fail(d["msg"])
    assert steps == ["press", "type", "type", "type", "press"]
    prog = c.get(f"/api/skills/{sid}").json()["program"]
    assert prog["inputs"] == {"to": "omar@acme.io", "subject": "Room booking", "message": "Booked for Monday."}
    done = None
    with c.stream("POST", "/api/run", json={"skill": sid, "mode": "eidos", "target": {
            "app": "B", "inputs": {"to": "kenji@harbor.co", "subject": "Lunch", "message": "Noon works."}}}) as r:
        for ev, d in _sse(r):
            if ev == "done":
                done = d
    assert done["report"]["all_contracts_passed"] and done["truth"]["success"]
    assert c.delete(f"/api/skills/{sid}").json()["ok"]
