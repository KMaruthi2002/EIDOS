"""The Studio's API and a click-through of the whole app in a browser."""
import httpx
import pytest


def test_api(studio):
    skills = httpx.get(f"{studio}/api/skills").json()
    ids = {s["id"] for s in skills}
    assert {"sample-mail", "sample-calendar", "sample-expense", "sample-settings", "sample-totals"} <= ids
    d = httpx.get(f"{studio}/api/skills/sample-mail").json()
    assert d["program"]["kind"] == "ui" and len(d["program"]["steps"]) == 5
    url = httpx.get(f"{studio}/api/target_ui", params={"task": "mail", "app_": "B", "dark": True}).json()["url"]
    assert "skin=B" in url and "theme=dark" in url
    assert "everyday_test" in httpx.get(f"{studio}/api/results").json()


@pytest.mark.slow
def test_click_through(studio):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": 1440, "height": 960})
        errors = []
        p.on("pageerror", lambda e: errors.append(str(e)))
        p.goto(studio)
        p.click('.sample[data-id="sample-expense"]')
        p.wait_for_selector("#learnSteps .step")
        assert p.locator("#learnSteps .step").count() == 5
        p.click("#toRun")
        p.click('#appSeg button[data-v="B"]')
        p.check('#redesign input[data-k="dark"]', force=True)
        p.check("#o_popup", force=True)
        p.click("#go")
        p.wait_for_selector("#verdict:not([hidden])", timeout=240_000)
        text = p.inner_text("#verdict")
        assert "matches what really happened" in text
        p.click("#openResults")
        p.wait_for_selector("#resBody .bench")
        assert not errors, errors
        b.close()
