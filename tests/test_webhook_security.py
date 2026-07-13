"""Tests de seguridad del webhook — solo lectura publica, escritura autenticada.

Principio: el dashboard es PUBLICO (GET /, /dashboard, /trades*.csv) pero el
endpoint de ESCRITURA (POST /webhook) debe exigir X-API-KEY para que nadie
pueda inyectar trades falsos en la DB.
"""
import importlib
import pytest
from aiohttp.test_utils import TestClient, TestServer
from src import webhook as wh

API_KEY = "test-secret-key-123"


def _make_app(monkeypatch, present):
    if present:
        monkeypatch.setenv("WEBHOOK_API_KEY", API_KEY)
    else:
        monkeypatch.delenv("WEBHOOK_API_KEY", raising=False)
    importlib.reload(wh)
    return wh.make_app()


@pytest.fixture
def app_without_key(monkeypatch):
    return _make_app(monkeypatch, present=False)


@pytest.fixture
def app_with_key(monkeypatch):
    return _make_app(monkeypatch, present=True)


async def test_post_webhook_without_key_is_rejected(app_without_key):
    """Cualquiera sin la API key NO debe poder escribir."""
    client = TestClient(TestServer(app_without_key))
    await client.start_server()
    resp = await client.post("/webhook", json={"activo": "BTC/USDT"})
    await client.close()
    assert resp.status == 401


async def test_post_webhook_with_key_is_accepted(app_with_key):
    """El bot (que conoce la key) SI puede escribir."""
    client = TestClient(TestServer(app_with_key))
    await client.start_server()
    resp = await client.post(
        "/webhook",
        json={"activo": "BTC/USDT", "resultado": "WIN"},
        headers={"X-API-KEY": API_KEY},
    )
    await client.close()
    assert resp.status == 200


async def test_get_dashboard_is_public(app_with_key):
    """El panel de lectura debe seguir accesible sin auth."""
    client = TestClient(TestServer(app_with_key))
    await client.start_server()
    resp = await client.get("/dashboard")
    await client.close()
    assert resp.status in (200, 202)
