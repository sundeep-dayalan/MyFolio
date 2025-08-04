"""
Tests for OAuth authentication endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestOAuthEndpoints:
    """Test OAuth authentication endpoints."""
    
    def test_oauth_status_endpoint(self):
        """Test OAuth status endpoint."""
        response = client.get("/api/v1/auth/oauth/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "google_oauth_enabled" in data
        assert "redirect_uri" in data
        assert "available_flows" in data
        assert data["available_flows"] == ["authorization_code"]
    
    def test_google_oauth_login_redirect(self):
        """Test Google OAuth login redirects to Google."""
        response = client.get("/api/v1/auth/oauth/google", allow_redirects=False)
        assert response.status_code == 302
        
        # Check that it redirects to Google
        location = response.headers.get("location")
        assert location is not None
        assert "accounts.google.com" in location
        assert "oauth2/auth" in location
    
    def test_google_oauth_callback_missing_code(self):
        """Test OAuth callback without authorization code."""
        response = client.get("/api/v1/auth/oauth/google/callback")
        assert response.status_code == 400
        
        data = response.json()
        assert "Authorization code is required" in data["detail"]
    
    def test_google_oauth_callback_missing_state(self):
        """Test OAuth callback without state parameter."""
        response = client.get("/api/v1/auth/oauth/google/callback?code=test_code")
        assert response.status_code == 400
        
        data = response.json()
        assert "State parameter is required" in data["detail"]
    
    def test_google_oauth_callback_invalid_state(self):
        """Test OAuth callback with invalid state parameter."""
        # First make a request to establish session
        client.get("/api/v1/auth/oauth/google", allow_redirects=False)
        
        # Then try callback with wrong state
        response = client.get("/api/v1/auth/oauth/google/callback?code=test_code&state=wrong_state")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid state parameter" in data["detail"]
    
    @patch('app.services.google_oauth_service.GoogleOAuthService.revoke_token')
    def test_revoke_token_endpoint(self, mock_revoke):
        """Test token revocation endpoint."""
        mock_revoke.return_value = True
        
        response = client.post(
            "/api/v1/auth/oauth/google/revoke",
            json={"token": "test_token"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Token revoked successfully" in data["message"]
        mock_revoke.assert_called_once_with("test_token")
    
    @patch('app.services.google_oauth_service.GoogleOAuthService.revoke_token')
    def test_revoke_token_failure(self, mock_revoke):
        """Test token revocation failure."""
        mock_revoke.return_value = False
        
        response = client.post(
            "/api/v1/auth/oauth/google/revoke",
            json={"token": "invalid_token"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Token revocation may have failed" in data["message"]
        assert data.get("warning") is True
    
    def test_oauth_callback_error_parameter(self):
        """Test OAuth callback with error parameter."""
        response = client.get("/api/v1/auth/oauth/google/callback?error=access_denied")
        assert response.status_code == 400
        
        data = response.json()
        assert "OAuth error: access_denied" in data["detail"]


class TestOAuthSecurity:
    """Test OAuth security features."""
    
    def test_state_parameter_generation(self):
        """Test that state parameter is generated for CSRF protection."""
        response = client.get("/api/v1/auth/oauth/google", allow_redirects=False)
        location = response.headers.get("location")
        
        assert "state=" in location
        # State should be at least 32 characters (URL-safe base64)
        state_param = location.split("state=")[1].split("&")[0]
        assert len(state_param) >= 32
    
    def test_redirect_uri_in_auth_url(self):
        """Test that redirect URI is included in auth URL."""
        response = client.get("/api/v1/auth/oauth/google", allow_redirects=False)
        location = response.headers.get("location")
        
        assert "redirect_uri=" in location
        assert "callback" in location
    
    def test_scope_parameters_in_auth_url(self):
        """Test that required scopes are included in auth URL."""
        response = client.get("/api/v1/auth/oauth/google", allow_redirects=False)
        location = response.headers.get("location")
        
        assert "scope=" in location
        assert "openid" in location
        assert "email" in location
        assert "profile" in location


@pytest.fixture
def mock_firebase():
    """Mock Firebase client for testing."""
    with patch('app.database.firebase_client') as mock_client:
        yield mock_client


@pytest.fixture
def mock_user_service():
    """Mock user service for testing."""
    with patch('app.services.user_service.UserService') as mock_service:
        yield mock_service


@pytest.fixture
def mock_auth_service():
    """Mock auth service for testing."""
    with patch('app.services.auth_service.AuthService') as mock_service:
        yield mock_service
