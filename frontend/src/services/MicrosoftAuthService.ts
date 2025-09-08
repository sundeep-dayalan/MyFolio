/**
 * Microsoft Entra ID Authentication Service
 * Handles OAuth 2.0 authentication flow with Microsoft Entra ID
 */

import config from '../config/env';
import { logger } from './LoggerService';
import type { UserResponse } from '../types/types';

const API_BASE_URL = config.apiBaseUrl;

export class MicrosoftAuthService {
  /**
   * Initiate Microsoft Entra ID OAuth login
   * Redirects to the backend OAuth endpoint which handles the full flow
   */
  static initiateLogin(): void {
    logger.info('Initiating Microsoft Entra ID OAuth login', 'AUTH');
    // Redirect to the secure server-side OAuth endpoint
    window.location.href = `${API_BASE_URL}/auth/oauth/microsoft`;
  }

  /**
   * Handle OAuth callback from backend
   * This should be called from your OAuth callback route
   */
  static async handleOAuthCallback(
    urlParams: URLSearchParams,
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const success = urlParams.get('success');
      const error = urlParams.get('error');
      const token = urlParams.get('token');
      const user = urlParams.get('user');

      if (success === 'false' || error) {
        const errorMessage = error ? decodeURIComponent(error) : 'Authentication failed';
        logger.error('OAuth callback error', 'AUTH', { error: errorMessage });
        return { success: false, error: errorMessage };
      }

      if (success === 'true' && token && user) {
        try {
          const userData: UserResponse = JSON.parse(decodeURIComponent(user));
          const tokenData = {
            access_token: token,
            token_type: 'bearer',
            expires_in: 7200, // 2 hours default
          };

          // Store authentication data
          this.setAuthData(userData, tokenData);
          logger.info('Microsoft OAuth callback successful', 'AUTH', { userId: userData.id });

          return { success: true };
        } catch (parseError) {
          logger.error('Failed to parse OAuth callback data', 'AUTH', parseError);
          return { success: false, error: 'Invalid authentication data received' };
        }
      }

      return { success: false, error: 'Missing required authentication parameters' };
    } catch (error) {
      logger.error('OAuth callback error', 'AUTH', error);
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
        // Attempt to revoke Microsoft token
        await fetch(`${API_BASE_URL}/auth/oauth/microsoft/revoke`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ token }),
        }).catch((error) => logger.warn('Token revocation failed during logout', 'AUTH', error)); // Don't fail logout if revocation fails
      }
    } catch (error) {
      logger.warn('Error during token revocation', 'AUTH', error);
    } finally {
      // Always clear local auth data
      this.clearAuthData();
    }
  }

  /**
   * Check if user is authenticated
   */
  static isAuthenticated(): boolean {
    // With HttpOnly cookies, we can't check authentication client-side
    // Let the API handle authentication - return true to enable UI
    // API will return 401 if not authenticated, triggering logout
    return true;
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
    // Extract session cookie value
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'session') {
        return value;
      }
    }
    return null;
  }

  /**
   * Check Microsoft OAuth configuration status
   */
  static async getOAuthStatus(): Promise<{
    microsoft_oauth_enabled: boolean;
    redirect_uri: string;
    frontend_url: string;
    tenant_id: string;
    available_flows: string[];
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/oauth/microsoft/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      logger.error('Failed to get Microsoft OAuth status', 'AUTH', error);
      throw error;
    }
  }

  /**
   * Store authentication data in localStorage
   */
  private static setAuthData(
    user: UserResponse,
    token: { access_token: string; token_type: string; expires_in: number },
  ): void {
    localStorage.setItem('authToken', token.access_token);
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('tokenType', token.token_type);
    localStorage.setItem('tokenExpiry', (Date.now() + token.expires_in * 1000).toString());

    logger.info('Authentication data stored successfully', 'AUTH');
  }

  /**
   * Clear authentication data from localStorage
   */
  private static clearAuthData(): void {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    localStorage.removeItem('tokenType');
    localStorage.removeItem('tokenExpiry');

    logger.info('Authentication data cleared', 'AUTH');
  }

  /**
   * Check if token is expired
   */
  static isTokenExpired(): boolean {
    // For cookie-based auth, the server handles token expiry
    // If the session cookie exists, we consider it valid
    // The browser will automatically remove expired cookies
    return !this.isAuthenticated();
  }

  /**
   * Refresh authentication status
   */
  static async refreshAuthStatus(): Promise<boolean> {
    if (!this.isAuthenticated() || this.isTokenExpired()) {
      this.clearAuthData();
      return false;
    }
    return true;
  }
}
