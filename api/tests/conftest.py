"""
Test configuration and fixtures.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User"
    }


@pytest.fixture
def test_google_credential():
    """Mock Google credential JWT token."""
    # This is a mock token for testing - in real tests you'd want to use proper test tokens
    import json
    import base64
    
    header = {"alg": "RS256", "kid": "test", "typ": "JWT"}
    payload = {
        "sub": "test_user_123",
        "email": "test@example.com", 
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/photo.jpg",
        "iat": 1234567890,
        "exp": 1234567890 + 3600
    }
    
    # Encode header and payload
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    # Mock signature
    signature = "mock_signature"
    
    return f"{header_encoded}.{payload_encoded}.{signature}"
