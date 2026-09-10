"""Unit tests for FastAPI application wiring, CORS configuration, and lifespan."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, lifespan

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] == settings.environment


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Document Copilot API"
    assert data["status"] == "running"


def test_cors_preflight_allowed_origin():
    # Send preflight OPTIONS request from configured allowed origin
    origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:5173"
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_disallowed_origin():
    # Send preflight OPTIONS request from unknown origin
    response = client.options(
        "/health",
        headers={
            "Origin": "http://evil-attacker.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "http://evil-attacker.com"


@pytest.mark.asyncio
async def test_lifespan_handler():
    # Test that the lifespan context manager enters and exits cleanly
    async with lifespan(app):
        pass
