/**
 * OAuth Callback Page - Handles Google OAuth callback and processes authentication
 */
import React, { useEffect, useState, useContext } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { AuthContextType } from '../types';
import Spinner from '../components/Spinner';

const OAuthCallbackPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useContext(AuthContext) as AuthContextType;

  // Add debug info to the page
  const [debugInfo, setDebugInfo] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Only run if we're actually on the callback page with parameters
        if (location.pathname !== '/auth/callback' || !window.location.search) {
          console.log('Not on callback page or no search params, skipping...');
          setLoading(false);
          return;
        }

        setLoading(true);
        setError(null);

        const currentUrl = window.location.href;
        const searchString = window.location.search;
        
        console.log('=== OAuth Callback Debug ===');
        console.log('Current URL:', currentUrl);
        console.log('Location pathname:', location.pathname);
        console.log('Search string:', searchString);
        console.log('Hash:', window.location.hash);

        const success = searchParams.get('success');
        const error = searchParams.get('error');
        const token = searchParams.get('token');
        const userStr = searchParams.get('user');

        console.log('Parsed URL params:', { 
          success, 
          error, 
          token: token ? `${token.substring(0, 20)}...` : 'missing', 
          user: userStr ? 'present' : 'missing' 
        });

        setDebugInfo(`URL: ${currentUrl}\nParams: success=${success}, token=${token ? 'present' : 'missing'}, user=${userStr ? 'present' : 'missing'}`);

        if (error || success === 'false') {
          console.log('Authentication failed:', error);
          setError(`Authentication failed: ${error || 'Unknown error'}`);
          setTimeout(() => navigate('/login', { replace: true }), 3000);
          return;
        }

        if (success === 'true' && token && userStr) {
          try {
            console.log('Parsing user data...');
            const userData = JSON.parse(decodeURIComponent(userStr));
            console.log('Parsed user data:', userData);
            
            // Store data in localStorage immediately
            localStorage.setItem('authToken', token);
            localStorage.setItem('user', JSON.stringify(userData));
            console.log('Data stored in localStorage');
            
            // Set user in auth context
            console.log('Setting user in auth context...');
            auth.setUser(userData, token);
            
            console.log('Navigating to home immediately...');
            // Navigate immediately since data is now in localStorage
            navigate('/home', { replace: true });
            
          } catch (parseErr) {
            console.error('Failed to parse user data:', parseErr);
            setError('Invalid authentication response');
            setTimeout(() => navigate('/login', { replace: true }), 3000);
          }
        } else {
          console.log('Missing required authentication parameters');
          setError('Missing authentication parameters');
          setTimeout(() => navigate('/login', { replace: true }), 3000);
        }
        
      } catch (err) {
        console.error('OAuth callback error:', err);
        setError('Network error during authentication');
        setTimeout(() => navigate('/login', { replace: true }), 3000);
      } finally {
        setLoading(false);
      }
    };

    handleCallback();
  }, [location.pathname, searchParams]); // Only run when pathname or search params change

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900 p-4">
        <div className="text-center max-w-lg">
          <Spinner />
          <h2 className="mt-4 text-lg font-medium text-white">
            Processing authentication...
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            Please wait while we complete your login
          </p>
          {debugInfo && (
            <div className="mt-4 p-4 bg-slate-800 rounded-lg text-left">
              <h3 className="text-sm font-medium text-slate-300 mb-2">Debug Info:</h3>
              <pre className="text-xs text-slate-400 whitespace-pre-wrap">{debugInfo}</pre>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900 p-4">
        <div className="text-center max-w-md mx-auto">
          <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-500/20 rounded-full mb-4">
              <svg 
                className="w-6 h-6 text-red-400" 
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
            <h3 className="text-lg font-medium text-red-300 mb-2">
              Authentication Failed
            </h3>
            <p className="text-sm text-red-400 mb-4">
              {error}
            </p>
            <p className="text-xs text-red-500">
              Redirecting to login page in a few seconds...
            </p>
            <button 
              onClick={() => navigate('/home')} 
              className="mt-2 px-4 py-2 bg-blue-600 text-white rounded text-sm"
            >
              Go to Home (Manual)
            </button>
            {debugInfo && (
              <div className="mt-4 p-4 bg-slate-800 rounded-lg text-left">
                <h3 className="text-sm font-medium text-slate-300 mb-2">Debug Info:</h3>
                <pre className="text-xs text-slate-400 whitespace-pre-wrap">{debugInfo}</pre>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default OAuthCallbackPage;
