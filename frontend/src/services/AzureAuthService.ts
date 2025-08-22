import type { OAuthCallbackResponse, UserResponse, Token } from '@/types/types';
import { config } from '../config/env';
import { logger } from './LoggerService';

const API_BASE_URL = config.apiBaseUrl;

export class AzureAuthService {
  /**
   * Initiate Google OAuth 2.0 flow for Azure backend
   */
  static initiateGoogleLogin(): void {
    // Clear any existing auth state
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');

    // Create OAuth URL parameters
    const params = new URLSearchParams({
      redirect_uri: `${window.location.origin}/oauth/callback`,
      response_type: 'code',
      scope: 'openid email profile',
      access_type: 'offline',
      prompt: 'consent'
    });

    // Redirect to Google OAuth
    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!googleClientId) {
      throw new Error('Google Client ID not configured');
    }

    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${googleClientId}&${params.toString()}`;
    window.location.href = authUrl;
  }

  /**
   * Handle OAuth callback from Google
   */
  static async handleOAuthCallback(
    urlParams: URLSearchParams,
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const code = urlParams.get('code');
      const error = urlParams.get('error');

      if (error) {
        return { success: false, error: `OAuth error: ${error}` };
      }

      if (!code) {
        return { success: false, error: 'Missing authorization code' };
      }

      // Send code to Azure Functions backend
      const response = await fetch(`${API_BASE_URL}/auth/google/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code,
          redirect_uri: `${window.location.origin}/oauth/callback`
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        return { success: false, error: errorData.error || 'Authentication failed' };
      }

      const data: OAuthCallbackResponse = await response.json();

      // Store authentication data
      this.setAuthData(data.user, data.access_token);

      return { success: true };
    } catch (error) {
      logger.error('OAuth callback error', 'AUTH', error);
      return { success: false, error: 'Network error during authentication' };
    }
  }

  /**
   * Logout user
   */
  static async logout(): Promise<void> {
    try {
      const token = localStorage.getItem('authToken');

      if (token) {
        // Optional: Call logout endpoint to invalidate token on server
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }).catch((error) => logger.warn('Server logout failed', 'AUTH', error));
      }
    } catch (error) {
      logger.warn('Error during logout', 'AUTH', error);
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
   * Refresh authentication token
   */
  static async refreshToken(): Promise<boolean> {
    try {
      const token = this.getAuthToken();
      if (!token) return false;

      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        this.clearAuthData();
        return false;
      }

      const data = await response.json();
      localStorage.setItem('authToken', data.access_token);
      
      // Update token expiration
      const expirationTime = Date.now() + 24 * 60 * 60 * 1000; // 24 hours
      localStorage.setItem('tokenExpiration', expirationTime.toString());

      return true;
    } catch (error) {
      logger.error('Token refresh failed', 'AUTH', error);
      this.clearAuthData();
      return false;
    }
  }

  /**
   * Make authenticated API request
   */
  static async authenticatedRequest(url: string, options: RequestInit = {}): Promise<Response> {
    const token = this.getAuthToken();

    if (!token) {
      throw new Error('No authentication token available');
    }

    // Check if token needs refresh
    if (this.isTokenExpired()) {
      const refreshed = await this.refreshToken();
      if (!refreshed) {
        throw new Error('Authentication token expired and refresh failed');
      }
    }

    const finalToken = this.getAuthToken();

    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${finalToken}`,
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Get user profile from API
   */
  static async getUserProfile(): Promise<UserResponse | null> {
    try {
      const response = await this.authenticatedRequest(`${API_BASE_URL}/users/me`);
      
      if (!response.ok) {
        if (response.status === 401) {
          this.clearAuthData();
          return null;
        }
        throw new Error(`Failed to get user profile: ${response.statusText}`);
      }

      const user = await response.json();
      localStorage.setItem('user', JSON.stringify(user));
      return user;
    } catch (error) {
      logger.error('Failed to get user profile', 'AUTH', error);
      return null;
    }
  }

  /**
   * Update user profile
   */
  static async updateUserProfile(updates: Partial<UserResponse>): Promise<UserResponse | null> {
    try {
      const response = await this.authenticatedRequest(`${API_BASE_URL}/users/me`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error(`Failed to update user profile: ${response.statusText}`);
      }

      const updatedUser = await response.json();
      localStorage.setItem('user', JSON.stringify(updatedUser));
      return updatedUser;
    } catch (error) {
      logger.error('Failed to update user profile', 'AUTH', error);
      return null;
    }
  }

  /**
   * Delete user account
   */
  static async deleteAccount(): Promise<boolean> {
    try {
      const response = await this.authenticatedRequest(`${API_BASE_URL}/users/me`, {
        method: 'DELETE',
      });

      if (response.ok) {
        this.clearAuthData();
        return true;
      }
      return false;
    } catch (error) {
      logger.error('Failed to delete account', 'AUTH', error);
      return false;
    }
  }

  // Private helper methods
  private static setAuthData(user: UserResponse, access_token: string): void {
    localStorage.setItem('authToken', access_token);
    localStorage.setItem('user', JSON.stringify(user));

    // Set token expiration (24 hours from now)
    const expirationTime = Date.now() + 24 * 60 * 60 * 1000;
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
   */
  static async refreshTokenIfNeeded(): Promise<boolean> {
    if (this.isTokenExpired()) {
      return await this.refreshToken();
    }
    return true;
  }
}