"""
Test the main application endpoints.
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


def test_root_endpoint(client: TestClient):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_docs_available_in_development(client: TestClient):
    """Test that API docs are available in development."""
    response = client.get("/docs")
    # Should return 200 in development mode
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_health_check(async_client):
    """Test health check with async client."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
