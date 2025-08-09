/**
 * OAuth Callback Component
 * Handles the OAuth callback from Google and processes authentication
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AuthService } from '../services/AuthService';
import Spinner from './Spinner';

export const OAuthCallback: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      try {
        setLoading(true);
        setError(null);

        // Process the OAuth callback
        const result = await AuthService.handleOAuthCallback(searchParams);

        if (result.success) {
          // Authentication successful, redirect to dashboard
          navigate('/dashboard', { replace: true });
        } else {
          // Authentication failed, show error
          setError(result.error || 'Authentication failed');
          
          // Redirect to login page after showing error
          setTimeout(() => {
            navigate('/login', { replace: true });
          }, 3000);
        }
      } catch (err) {
        console.error('OAuth callback error:', err);
        setError('An unexpected error occurred during authentication');
        
        // Redirect to login page after showing error
        setTimeout(() => {
          navigate('/login', { replace: true });
        }, 3000);
      } finally {
        setLoading(false);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Spinner />
          <h2 className="mt-4 text-lg font-medium text-gray-900">
            Processing authentication...
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Please wait while we complete your login
          </p>
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
            <h3 className="text-lg font-medium text-red-800 mb-2">
              Authentication Failed
            </h3>
            <p className="text-sm text-red-600 mb-4">
              {error}
            </p>
            <p className="text-xs text-red-500">
              Redirecting to login page in a few seconds...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // This shouldn't be reached, but just in case
  return null;
};
