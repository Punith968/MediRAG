import pytest

from app.main import app


@pytest.mark.anyio
async def test_health_endpoint_reports_backend_status(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    async def fake_health_dependencies():
        return None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert "models" in payload
    assert "pinecone" in payload
    assert "vector_count" in payload
