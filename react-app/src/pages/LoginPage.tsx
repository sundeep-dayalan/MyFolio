import React, { useContext, useEffect, useState } from 'react';

import { cn } from '@/lib/utils';
import { GalleryVerticalEnd } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthContext } from '@/context/AuthContext';
import type { AuthContextType, OAuthStatusResponse } from '@/types/types';

import { useNavigate } from 'react-router-dom';
import config from '@/config/env';

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
    <div className="bg-background flex min-h-svh flex-col items-center justify-center gap-6 p-6 md:p-10">
      <div className="w-full max-w-sm">
        <div className={cn('flex flex-col gap-6')}>
          <form>
            <div className="flex flex-col gap-6">
              <div className="flex flex-col items-center gap-2">
                <a href="#" className="flex flex-col items-center gap-2 font-medium">
                  <div className="flex size-8 items-center justify-center rounded-md">
                    <GalleryVerticalEnd className="size-6" />
                  </div>
                  <span className="sr-only">MyFolio</span>
                </a>
                <h1 className="text-xl font-bold">Welcome to MyFolio</h1>
                <div className="text-center text-sm">
                  Don&apos;t have an account?{' '}
                  <a href="#" className="underline underline-offset-4">
                    Sign up
                  </a>
                </div>
              </div>
              {/* <div className="flex flex-col gap-6">
                <div className="grid gap-3">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" placeholder="m@example.com" required />
                </div>
                <Button type="submit" className="w-full">
                  Login
                </Button>
              </div> */}
              <div className="after:border-border relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t">
                <span className="bg-background text-muted-foreground relative z-10 px-2">SSO</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Button variant="outline" type="button" className="w-full">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path
                      d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"
                      fill="currentColor"
                    />
                  </svg>
                  Continue with Apple
                </Button>
                <div className="space-y-6">
                  {isLoading ? (
                    <div className="text-center py-8">
                      <div className="relative">
                        <div className="w-16 h-16 mx-auto mb-4">
                          <div className="w-full h-full border-4 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin"></div>
                        </div>
                        <p className="text-slate-300 text-lg font-medium">
                          Connecting to Google...
                        </p>
                        <p className="text-slate-400 text-sm mt-1">This may take a few moments</p>
                      </div>
                    </div>
                  ) : (
                    <Button
                      onClick={handleGoogleLogin}
                      disabled={!oauthStatus?.google_oauth_enabled}
                      variant="outline"
                      type="button"
                      className="w-full"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                        <path
                          d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"
                          fill="currentColor"
                        />
                      </svg>
                      Continue with Google
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </form>
          {/* Error message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-300 p-4 rounded-xl mb-6 text-center backdrop-blur-sm">
              <div className="flex items-center justify-center space-x-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-sm font-medium">{error}</span>
              </div>
            </div>
          )}
          <div className="text-muted-foreground *:[a]:hover:text-primary text-center text-xs text-balance *:[a]:underline *:[a]:underline-offset-4">
            By clicking continue, you agree to our <a href="#">Terms of Service</a> and{' '}
            <a href="#">Privacy Policy</a>.
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
