import React, { useContext, useEffect, useState } from 'react';

import { cn } from '@/lib/utils';
import { GalleryVerticalEnd, Loader2Icon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AuthContext } from '@/context/AuthContext';
import { MicrosoftAuthService } from '@/services/MicrosoftAuthService';
import type { AuthContextType, MicrosoftOAuthStatusResponse } from '@/types/types';

import { useNavigate } from 'react-router-dom';
import config from '@/config/env';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

const LoginPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [oauthStatus, setOauthStatus] = useState<MicrosoftOAuthStatusResponse | null>(null);

  useEffect(() => {
    // Check if user is already authenticated
    if (auth.user) {
      navigate('/home');
      return;
    }

    // Get Microsoft OAuth configuration status
    const checkOAuthStatus = async () => {
      try {
        const status = await MicrosoftAuthService.getOAuthStatus();
        setOauthStatus(status);
      } catch (error) {
        console.error('Failed to get Microsoft OAuth status:', error);
        setError('Server unavailable! Please try again later.');
      }
    };

    checkOAuthStatus();
  }, [auth.user, navigate]);

  const handleMicrosoftLogin = async () => {
    if (!oauthStatus?.microsoft_oauth_enabled) {
      setError('Microsoft OAuth is not configured');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Use Microsoft Auth Service to initiate login
      MicrosoftAuthService.initiateLogin();
    } catch (error) {
      console.error('Failed to initiate Microsoft login:', error);
      setError('Failed to start authentication');
      setIsLoading(false);
    }
  };

  function mailTo(email: string): void {
    window.location.href = `mailto:${email}`;
  }
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
                  <span className="sr-only">Sage</span>
                </a>
                <h1 className="text-xl font-bold">Welcome to Sage</h1>
                <div className="text-center text-sm">
                  Product access is limited to authorised users{' '}
                  <Button variant="link" onClick={() => mailTo('example@example.com')}>
                    Get access
                  </Button>
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
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="outline" type="button" className="w-full">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                        <path
                          d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"
                          fill="currentColor"
                        />
                      </svg>
                      Continue with Apple
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Login with Apple is currently unavailable</AlertDialogTitle>
                      <AlertDialogDescription>
                        We're sorry, but the option to log in with Apple is not available at this
                        time.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogAction>Got it</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>

                <div className="space-y-6">
                  <Button
                    onClick={handleMicrosoftLogin}
                    disabled={!oauthStatus?.microsoft_oauth_enabled || isLoading}
                    variant="outline"
                    type="button"
                    className="w-full"
                  >
                    {isLoading ? (
                      <Loader2Icon className="animate-spin" />
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                        <path
                          d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z"
                          fill="currentColor"
                        />
                      </svg>
                    )}
                    Continue with Microsoft
                  </Button>
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
