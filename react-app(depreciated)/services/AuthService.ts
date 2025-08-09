/**
 * Updated React authentication service for secure server-side OAuth
 */
import { UserResponse, Token, OAuthCallbackResponse } from '../types';
import { config } from '../config/env';

const API_BASE_URL = config.apiBaseUrl;

export class AuthService {
  /**
   * Initiate Google OAuth 2.0 flow (server-side)
   * This replaces the client-side Google OAuth
   */
  static initiateGoogleLogin(): void {
    // Clear any existing auth state
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    
    // Redirect to FastAPI OAuth endpoint
    window.location.href = `${API_BASE_URL}/auth/oauth/google`;
  }

  /**
   * Handle OAuth callback from backend
   * This should be called from your OAuth callback route
   */
  static async handleOAuthCallback(
    urlParams: URLSearchParams
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const code = urlParams.get('code');
      const state = urlParams.get('state');
      const error = urlParams.get('error');

      if (error) {
        return { success: false, error: `OAuth error: ${error}` };
      }

      if (!code || !state) {
        return { success: false, error: 'Missing authorization parameters' };
      }

      // The callback endpoint will handle token exchange
      const response = await fetch(
        `${API_BASE_URL}/auth/oauth/google/callback?code=${code}&state=${state}`,
        {
          method: 'GET',
          credentials: 'include', // Include session cookies
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        return { success: false, error: errorData.detail || 'Authentication failed' };
      }

      const data: OAuthCallbackResponse = await response.json();
      
      // Store authentication data
      this.setAuthData(data.user, data.token);
      
      return { success: true };
    } catch (error) {
      console.error('OAuth callback error:', error);
      return { success: false, error: 'Network error during authentication' };
    }
  }

  /**
   * Logout user and revoke OAuth tokens
   */
  static async logout(): Promise<void> {
    try {
      const token = localStorage.getItem('authToken');
      
      if (token) {
        // Attempt to revoke Google token
        await fetch(`${API_BASE_URL}/auth/oauth/google/revoke`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ token }),
        }).catch(console.warn); // Don't fail logout if revocation fails
      }
    } catch (error) {
      console.warn('Error during token revocation:', error);
    } finally {
      // Always clear local auth data
      this.clearAuthData();
    }
  }

  /**
   * Check if user is authenticated
   */
  static isAuthenticated(): boolean {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('user');
    return Boolean(token && user);
  }

  /**
   * Get current user data
   */
  static getCurrentUser(): UserResponse | null {
    const userData = localStorage.getItem('user');
    return userData ? JSON.parse(userData) : null;
  }

  /**
   * Get authentication token
   */
  static getAuthToken(): string | null {
    return localStorage.getItem('authToken');
  }

  /**
   * Check OAuth configuration status
   */
  static async getOAuthStatus(): Promise<{
    google_oauth_enabled: boolean;
    redirect_uri: string;
    available_flows: string[];
  }> {
    const response = await fetch(`${API_BASE_URL}/auth/oauth/status`);
    return response.json();
  }

  /**
   * Make authenticated API request
   */
  static async authenticatedRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const token = this.getAuthToken();
    
    if (!token) {
      throw new Error('No authentication token available');
    }

    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
  }

  // Private helper methods
  private static setAuthData(user: UserResponse, token: Token): void {
    localStorage.setItem('authToken', token.access_token);
    localStorage.setItem('user', JSON.stringify(user));
    
    // Optional: Set token expiration
    const expirationTime = Date.now() + (token.expires_in * 1000);
    localStorage.setItem('tokenExpiration', expirationTime.toString());
  }

  private static clearAuthData(): void {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    localStorage.removeItem('tokenExpiration');
  }

  /**
   * Check if token is expired
   */
  static isTokenExpired(): boolean {
    const expiration = localStorage.getItem('tokenExpiration');
    if (!expiration) return true;
    
    return Date.now() > parseInt(expiration);
  }

  /**
   * Refresh token if needed
   * You can implement this to call a refresh endpoint
   */
  static async refreshTokenIfNeeded(): Promise<boolean> {
    if (this.isTokenExpired()) {
      // For now, just logout if token is expired
      // You can implement a refresh endpoint later
      this.clearAuthData();
      return false;
    }
    return true;
  }
}
