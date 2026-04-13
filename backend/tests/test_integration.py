# backend/tests/test_integration.py
import pytest
from httpx import AsyncClient
from main import app
from config import settings

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_database_connection():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/layer3/incidents")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_sse_stream():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/stream")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"