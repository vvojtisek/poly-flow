import json
import logging

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import health
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_healthz(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


async def test_request_id_echoed(client):
    r = await client.get("/healthz", headers={"x-request-id": "abc"})
    assert r.headers["x-request-id"] == "abc"


async def test_readyz_ok(client, monkeypatch):
    async def ok():
        return None

    monkeypatch.setattr(health, "_check_db", ok)
    monkeypatch.setattr(health, "_check_redis", ok)
    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


async def test_readyz_unready(client, monkeypatch):
    async def ok():
        return None

    async def boom():
        raise ConnectionError("down")

    monkeypatch.setattr(health, "_check_db", boom)
    monkeypatch.setattr(health, "_check_redis", ok)
    r = await client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["checks"]["postgres"] == {"ok": False, "error": "ConnectionError"}
    assert body["checks"]["redis"]["ok"] is True


async def test_request_log_fields(client, caplog, monkeypatch):
    async def boom():
        raise ConnectionError("down")

    monkeypatch.setattr(health, "_check_db", boom)
    monkeypatch.setattr(health, "_check_redis", boom)
    caplog.set_level(logging.INFO, logger="polyflow.http")
    await client.get("/readyz")  # /healthz is intentionally not logged
    rec = [r for r in caplog.records if r.name == "polyflow.http" and r.msg == "request"][-1]
    assert rec.path == "/readyz" and rec.status == 503 and rec.method == "GET"


def test_json_formatter_output():
    from app.core.logging import JsonFormatter

    rec = logging.LogRecord("x", logging.INFO, "f", 1, "hello", (), None)
    rec.foo = "bar"
    out = json.loads(JsonFormatter().format(rec))
    assert out["msg"] == "hello" and out["foo"] == "bar" and out["level"] == "INFO"
