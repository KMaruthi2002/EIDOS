"""Deployment guards: access token, health check, daily model-call cap."""
import importlib

import pytest
from fastapi.testclient import TestClient


def client(monkeypatch, token=None):
    if token:
        monkeypatch.setenv("EIDOS_TOKEN", token)
    else:
        monkeypatch.delenv("EIDOS_TOKEN", raising=False)
    from eidos import studio
    return TestClient(studio.app)


def test_open_without_a_token(monkeypatch):
    c = client(monkeypatch)
    assert c.get("/healthz").json() == {"ok": True}
    assert c.get("/api/world/skills").status_code == 200


def test_token_required_when_set(monkeypatch):
    c = client(monkeypatch, "s3cret")
    assert c.get("/healthz").status_code == 200                 # health checks stay open
    assert c.get("/api/world/skills").status_code == 401
    assert c.get("/api/world/skills", headers={"Authorization": "Bearer s3cret"}).status_code == 200
    r = c.get("/world?token=s3cret", follow_redirects=False)     # the link sets a cookie and drops the token from the URL
    assert r.status_code in (302, 307) and "eidos_token" in r.headers.get("set-cookie", "")
    assert c.get("/api/world/skills").status_code == 200        # the cookie now works
    assert c.get("/api/world/skills", headers={"Authorization": "Bearer wrong"}, cookies={"eidos_token": "wrong"}).status_code == 401


def test_daily_call_cap(monkeypatch):
    from eidos import live
    monkeypatch.setattr(live, "DAILY_LIMIT", 2)
    live._DAY.update({"day": "", "calls": 0})
    live._count_call()
    live._count_call()
    with pytest.raises(live.LimitReached):
        live._count_call()
    assert live.usage()["calls_today"] == 2
    monkeypatch.setattr(live, "DAILY_LIMIT", 0)
