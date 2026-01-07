import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_healthz_and_discovery():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r1 = await ac.get("/api/v1/healthz")
        assert r1.status_code == 200
        assert r1.json()["status"] == "ok"

        r2 = await ac.get("/api/v1/discovery/")
        assert r2.status_code == 200
        body = r2.json()
        assert body.get("service") == "gateway-api"
        assert any(ep["path"] == "/api/v1/healthz" for ep in body.get("endpoints", []))
