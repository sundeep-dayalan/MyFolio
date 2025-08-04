
import React, { useEffect, useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { AuthContextType, OAuthStatusResponse } from '../types';
import GoogleIcon from '../components/icons/GoogleIcon';
import Spinner from '../components/Spinner';
import { config } from '../config/env';

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
                setError('Server unavailable! Please try again later.');
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
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
            {/* Animated background elements */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl animate-pulse"></div>
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-pulse delay-500"></div>
            </div>

            {/* Main login container */}
            <div className="relative w-full max-w-md mx-auto">
                {/* Glassmorphism card */}
                <div className="bg-white/10 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 relative">
                    {/* Header section */}
                    <div className="text-center mb-8">
                        {/* Logo/Icon */}
                        <div className="w-20 h-20 bg-gradient-to-r from-emerald-400 to-blue-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        
                        <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
                            Welcome to{' '}
                            <span className="bg-gradient-to-r from-emerald-400 to-blue-500 bg-clip-text text-transparent">
                                MyFolio
                            </span>
                        </h1>
                        <p className="text-slate-300 text-lg">Your personal wealth management platform</p>
                    </div>
                    
                    {/* Error message */}
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/20 text-red-300 p-4 rounded-xl mb-6 text-center backdrop-blur-sm">
                            <div className="flex items-center justify-center space-x-2">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span className="text-sm font-medium">{error}</span>
                            </div>
                        </div>
                    )}

                    {/* Authentication section */}
                    <div className="space-y-6">
                        {isLoading ? (
                            <div className="text-center py-8">
                                <div className="relative">
                                    <div className="w-16 h-16 mx-auto mb-4">
                                        <div className="w-full h-full border-4 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin"></div>
                                    </div>
                                    <p className="text-slate-300 text-lg font-medium">Connecting to Google...</p>
                                    <p className="text-slate-400 text-sm mt-1">This may take a few moments</p>
                                </div>
                            </div>
                        ) : (
                            <>
                                {/* Google Sign In Button */}
                                <button
                                    onClick={handleGoogleLogin}
                                    disabled={!oauthStatus?.google_oauth_enabled}
                                    className={`group relative w-full py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 transform ${
                                        !oauthStatus?.google_oauth_enabled
                                            ? 'bg-slate-700/50 cursor-not-allowed opacity-50 text-slate-400'
                                            : 'bg-white/10 hover:bg-white/20 active:bg-white/30 text-white hover:scale-105 active:scale-95 border border-white/20 hover:border-white/30 shadow-lg hover:shadow-xl'
                                    }`}
                                >
                                    <div className="flex items-center justify-center space-x-3">
                                        <div className="w-6 h-6">
                                            <GoogleIcon />
                                        </div>
                                        <span>Continue with Google</span>
                                    </div>
                                    
                                    {/* {!oauthStatus?.google_oauth_enabled && (
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <div className="bg-slate-800/90 backdrop-blur-sm rounded-lg px-3 py-1">
                                                <span className="text-xs text-slate-400">OAuth Disabled</span>
                                            </div>
                                        </div>
                                    )} */}
                                </button>

                                {/* Divider */}
                                <div className="relative my-8">
                                    <div className="absolute inset-0 flex items-center">
                                        <div className="w-full border-t border-white/20"></div>
                                    </div>
                                    <div className="relative flex justify-center text-sm">
                                        <span className="px-4 bg-slate-900/50 text-slate-400 rounded-full">Secure Authentication</span>
                                    </div>
                                </div>

                                {/* Features list */}
                                <div className="space-y-3">
                                    <div className="flex items-center space-x-3 text-slate-300">
                                        <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                                        <span className="text-sm">Track your investment portfolio</span>
                                    </div>
                                    <div className="flex items-center space-x-3 text-slate-300">
                                        <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                                        <span className="text-sm">Monitor performance analytics</span>
                                    </div>
                                    <div className="flex items-center space-x-3 text-slate-300">
                                        <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                                        <span className="text-sm">Set financial goals and targets</span>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>

                    {/* OAuth Status Indicator */}
                    {oauthStatus && (
                        <div className="mt-8 text-center">
                            <div className={`inline-flex items-center px-3 py-2 rounded-full text-xs font-medium backdrop-blur-sm ${
                                oauthStatus.google_oauth_enabled 
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                                    : 'bg-red-500/20 text-red-300 border border-red-500/30'
                            }`}>
                                <div className={`w-2 h-2 rounded-full mr-2 ${
                                    oauthStatus.google_oauth_enabled ? 'bg-emerald-400' : 'bg-red-400'
                                }`}></div>
                                {oauthStatus.google_oauth_enabled ? 'System Ready' : 'Configuration Required'}
                            </div>
                        </div>
                    )}

                    {/* Footer */}
                    <div className="text-center text-slate-400 text-xs mt-8 pt-6 border-t border-white/10">
                        <p>© {new Date().getFullYear()} MyFolio. Secure & Private.</p>
                        <p className="mt-1">Your financial data is protected</p>
                    </div>
                </div>

                {/* Additional decorative elements */}
                <div className="absolute -inset-1 bg-gradient-to-r from-emerald-600/20 to-blue-600/20 rounded-3xl blur-xl -z-10 opacity-70"></div>
            </div>
        </div>
    );
};

export default LoginPage;
