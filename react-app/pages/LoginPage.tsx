
import React, { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { AuthContextType, OAuthStatusResponse } from '../types';
import GoogleIcon from '../components/icons/GoogleIcon';
import Spinner from '../components/Spinner';
import config from '../config/env';

const LoginPage: React.FC = () => {
    const auth = useContext(AuthContext) as AuthContextType;
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [oauthStatus, setOauthStatus] = useState<OAuthStatusResponse | null>(null);

    const API_BASE_URL = config.apiBaseUrl;

    useEffect(() => {
        // Check if user is already authenticated
        if (auth.user) {
            navigate('/home');
            return;
        }

        // Get OAuth configuration status
        const checkOAuthStatus = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/auth/oauth/status`);
                const status: OAuthStatusResponse = await response.json();
                setOauthStatus(status);
            } catch (error) {
                console.error('Failed to get OAuth status:', error);
                setError('Failed to load authentication configuration');
            }
        };

        checkOAuthStatus();
    }, [auth.user, navigate]);

    const handleGoogleLogin = async () => {
        if (!oauthStatus?.google_oauth_enabled) {
            setError('Google OAuth is not configured');
            return;
        }

        setIsLoading(true);
        setError(null);
        
        try {
            // Redirect to the secure server-side OAuth endpoint
            window.location.href = `${API_BASE_URL}/auth/oauth/google`;
        } catch (error) {
            console.error('Failed to initiate Google login:', error);
            setError('Failed to start authentication');
            setIsLoading(false);
        }
    };
    

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-900 p-4">
            <div className="w-full max-w-sm mx-auto bg-slate-800 rounded-2xl shadow-2xl p-8 border border-slate-700">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
                    <p className="text-slate-400">Sign in to continue</p>
                </div>
                
                {error && <div className="bg-red-500/20 text-red-300 p-3 rounded-lg mb-6 text-center text-sm">{error}</div>}

                <div className="flex flex-col items-center justify-center space-y-4 h-24">
                    {isLoading ? (
                        <div className="text-center">
                            <Spinner />
                            <p className="text-slate-400 text-sm mt-2">Starting authentication...</p>
                        </div>
                    ) : (
                        <button
                            onClick={handleGoogleLogin}
                            disabled={!oauthStatus?.google_oauth_enabled}
                            className={`flex items-center justify-center space-x-3 w-full py-3 px-4 border border-slate-600 rounded-lg text-white font-medium transition-colors ${
                                !oauthStatus?.google_oauth_enabled
                                    ? 'bg-slate-700 cursor-not-allowed opacity-50'
                                    : 'bg-slate-700 hover:bg-slate-600 active:bg-slate-800'
                            }`}
                        >
                            <GoogleIcon />
                            <span>Continue with Google</span>
                        </button>
                    )}
                    
                    {/* OAuth Status Indicator for Development */}
                    {oauthStatus && (
                        <div className="text-center">
                            <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                                oauthStatus.google_oauth_enabled 
                                    ? 'bg-green-500/20 text-green-300' 
                                    : 'bg-red-500/20 text-red-300'
                            }`}>
                                {oauthStatus.google_oauth_enabled ? '✓ OAuth Ready' : '✗ OAuth Disabled'}
                            </div>
                        </div>
                    )}
                </div>

                <div className="text-center text-slate-500 text-xs mt-8">
                    <p>&copy; {new Date().getFullYear()} SSO App. All rights reserved.</p>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
