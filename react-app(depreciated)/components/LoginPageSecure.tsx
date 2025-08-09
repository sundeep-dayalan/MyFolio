/**
 * Updated Login Page with Secure Server-Side OAuth
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthService } from '../services/AuthService';
import { OAuthStatusResponse } from '../types';

export const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [oauthStatus, setOauthStatus] = useState<OAuthStatusResponse | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is already authenticated
    if (AuthService.isAuthenticated()) {
      navigate('/dashboard', { replace: true });
      return;
    }

    // Get OAuth configuration status
    const checkOAuthStatus = async () => {
      try {
        const status = await AuthService.getOAuthStatus();
        setOauthStatus(status);
      } catch (error) {
        console.error('Failed to get OAuth status:', error);
      }
    };

    checkOAuthStatus();
  }, [navigate]);

  const handleGoogleLogin = async () => {
    if (!oauthStatus?.google_oauth_enabled) {
      alert('Google OAuth is not configured');
      return;
    }

    setLoading(true);
    
    try {
      // This will redirect to the backend OAuth endpoint
      AuthService.initiateGoogleLogin();
    } catch (error) {
      console.error('Failed to initiate Google login:', error);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Personal Wealth Management
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in to access your financial dashboard
          </p>
        </div>

        {/* Login Form */}
        <div className="mt-8 space-y-6">
          <div className="bg-white py-8 px-6 shadow rounded-lg">
            {/* OAuth Status Indicator */}
            {oauthStatus && (
              <div className="mb-6">
                <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  oauthStatus.google_oauth_enabled 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {oauthStatus.google_oauth_enabled ? '✓ OAuth Enabled' : '✗ OAuth Disabled'}
                </div>
              </div>
            )}

            {/* Google Sign In Button */}
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={loading || !oauthStatus?.google_oauth_enabled}
              className={`group relative w-full flex justify-center py-3 px-4 border border-gray-300 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors ${
                loading || !oauthStatus?.google_oauth_enabled
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'text-gray-700 bg-white hover:bg-gray-50'
              }`}
            >
              <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                {loading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-t-2 border-blue-500"></div>
                ) : (
                  // Google Icon
                  <svg className="h-5 w-5" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                )}
              </span>
              {loading ? 'Signing in...' : 'Continue with Google'}
            </button>

            {/* Security Notice */}
            <div className="mt-6 text-center">
              <p className="text-xs text-gray-500">
                🔒 Secure server-side authentication with OAuth 2.0
              </p>
            </div>
          </div>

          {/* Additional Information */}
          <div className="text-center">
            <p className="text-sm text-gray-600">
              By signing in, you agree to our{' '}
              <a href="#" className="font-medium text-blue-600 hover:text-blue-500">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="#" className="font-medium text-blue-600 hover:text-blue-500">
                Privacy Policy
              </a>
            </p>
          </div>

          {/* Development Info */}
          {process.env.NODE_ENV === 'development' && oauthStatus && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <h4 className="text-sm font-medium text-blue-800 mb-2">Development Info:</h4>
              <div className="text-xs text-blue-600 space-y-1">
                <p>OAuth Enabled: {oauthStatus.google_oauth_enabled ? 'Yes' : 'No'}</p>
                <p>Redirect URI: {oauthStatus.redirect_uri}</p>
                <p>Available Flows: {oauthStatus.available_flows.join(', ')}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
