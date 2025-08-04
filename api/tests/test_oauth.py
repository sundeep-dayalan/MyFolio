"""
Fixed OAuth tests with proper mocking.
"""
import pytest
from unittest.mock import Mock, patch


class TestOAuthStatus:
    """Test OAuth status endpoint."""
    
    def test_oauth_status_endpoint(self, client):
        """Test OAuth status endpoint returns correct status."""
        response = client.get("/api/v1/auth/oauth/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "google_oauth_enabled" in data
        assert data["google_oauth_enabled"] is True


class TestOAuthCallback:
    """Test OAuth callback behavior."""
    
    def test_callback_missing_code_redirects_with_error(self, client):
        """Test that missing code parameter redirects with error."""
        response = client.get("/api/v1/auth/oauth/google/callback", allow_redirects=False)
        assert response.status_code == 302
        
        location = response.headers.get("location", "")
        assert "error=" in location
    
    def test_callback_missing_state_redirects_with_error(self, client):
        """Test that missing state parameter redirects with error."""
        response = client.get("/api/v1/auth/oauth/google/callback?code=test_code", allow_redirects=False)
        assert response.status_code == 302
        
        location = response.headers.get("location", "")
        assert "error=" in location
    
    def test_callback_with_oauth_error_redirects(self, client):
        """Test that OAuth error parameter causes redirect with error."""
        response = client.get("/api/v1/auth/oauth/google/callback?error=access_denied", allow_redirects=False)
        assert response.status_code == 302
        
        location = response.headers.get("location", "")
        assert "error=" in location
