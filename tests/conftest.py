"""Shared fixtures: a Studio server on a free port (it also serves the target apps)."""
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture(scope="session")
def studio():
    import uvicorn
    from eidos import studio as st
    port = _free_port()
    st.PORT["value"] = port
    server = uvicorn.Server(uvicorn.Config(st.app, host="127.0.0.1", port=port, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture(scope="session")
def shot(studio):
    """shot(url_query, actions) -> screenshot (BGR) of an everyday app after DOM-driven setup.

    The test drives the page directly to set up a state; only the perception under
    test looks at the pixels."""
    from playwright.sync_api import sync_playwright
    import cv2, numpy as np
    pw = sync_playwright().start()
    browser = pw.chromium.launch()

    def take(query, setup=None):
        page = browser.new_page(viewport={"width": 1200, "height": 760})
        page.goto(f"{studio}/apps/everyday/index.html?{query}")
        page.wait_for_timeout(300)
        if setup:
            setup(page)
            page.wait_for_timeout(300)
        img = cv2.imdecode(np.frombuffer(page.screenshot(), np.uint8), cv2.IMREAD_COLOR)
        page.close()
        return img
    yield take
    browser.close(); pw.stop()
