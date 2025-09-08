import React, { useEffect, useState, useContext } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Spinner } from '@/components/ui/spinner';
import { config } from '../config/env';

export const OAuthCallback: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState<string>('');
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const authContext = useContext(AuthContext);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get current URL and all parameters for debugging
        const currentUrl = window.location.href;
        const allParams = Object.fromEntries(searchParams.entries());
        const debugMessage = `URL: ${currentUrl}\nAll parameters: ${JSON.stringify(
          allParams,
          null,
          2,
        )}`;
        setDebugInfo(debugMessage);

        console.log('OAuth Callback Debug:', debugMessage);

        // Check for success/error parameters from backend redirect
        const success = searchParams.get('success');
        const errorParam = searchParams.get('error');

        if (success === 'false' || errorParam) {
          // Authentication failed
          const errorMessage = errorParam ? decodeURIComponent(errorParam) : 'Authentication failed';
          setError(errorMessage);
          setTimeout(() => navigate('/login', { replace: true }), 3000);
          return;
        }

        // If we reach here, the backend should have set the HttpOnly session cookie
        // We need to verify by calling the /session/me endpoint
        const response = await fetch(`${config.apiBaseUrl}/auth/oauth/microsoft/session/me`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const userData = await response.json();
          // Update the auth context with the user data
          if (authContext) {
            authContext.setUser(userData);
          }
          console.log('OAuth callback successful, redirecting to /home');
          navigate('/home', { replace: true });
        } else {
          // Session validation failed
          setError('Authentication session could not be established');
          setTimeout(() => navigate('/login', { replace: true }), 3000);
        }
      } catch (err) {
        console.error('OAuth callback error:', err);
        setError('An unexpected error occurred during authentication');
        setTimeout(() => navigate('/login', { replace: true }), 3000);
      } finally {
        setLoading(false);
      }
    };

    handleCallback();
  }, [searchParams, navigate, authContext]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-lg">
          <Spinner />
          <h2 className="mt-4 text-lg font-medium text-gray-900">Processing authentication...</h2>
          <p className="mt-2 text-sm text-gray-600">Please wait while we complete your login</p>
          {debugInfo && (
            <div className="mt-4 p-4 bg-gray-100 rounded-lg text-left">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Debug Info:</h3>
              <pre className="text-xs text-gray-600 whitespace-pre-wrap">{debugInfo}</pre>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full mb-4">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.314 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-red-800 mb-2">Authentication Failed</h3>
            <p className="text-sm text-red-600 mb-4">{error}</p>
            <p className="text-xs text-red-500">Redirecting to login page in a few seconds...</p>
            {debugInfo && (
              <div className="mt-4 p-4 bg-red-100 rounded-lg text-left">
                <h3 className="text-sm font-medium text-red-700 mb-2">Debug Info:</h3>
                <pre className="text-xs text-red-600 whitespace-pre-wrap max-h-40 overflow-y-auto">
                  {debugInfo}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // This shouldn't be reached, but just in case
  return null;
};
