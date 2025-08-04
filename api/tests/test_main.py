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
    # In development mode (DEBUG=True), docs should be available
    # In test environment, we set DEBUG=True, so docs should be accessible
    assert response.status_code == 200
