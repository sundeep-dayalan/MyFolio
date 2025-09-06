import React, { createContext, useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { config } from '../config/env';
import type { AuthContextType, UserResponse } from '@/types/types';

export const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const navigate = useNavigate();

  // Check for existing authentication on app load
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const response = await fetch(`${config.apiBaseUrl}/auth/oauth/microsoft/session/me`, {
          method: 'GET',
          credentials: 'include', // This ensures cookies are sent
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          setUser(null);
        }
      } catch (error) {
        console.error('Auth status check failed:', error);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  const login = useCallback(() => {
    // Redirect to backend OAuth endpoint
    window.location.href = `${config.apiBaseUrl}/auth/oauth/microsoft`;
  }, []);

  const logout = useCallback(async () => {
    try {
      const response = await fetch(`${config.apiBaseUrl}/auth/oauth/microsoft/logout`, {
        method: 'POST',
        credentials: 'include', // This ensures cookies are sent
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        setUser(null);
        navigate('/login');
      } else {
        console.error('Logout failed');
        // Still clear local state even if server logout fails
        setUser(null);
        navigate('/login');
      }
    } catch (error) {
      console.error('Logout error:', error);
      // Still clear local state even if network error
      setUser(null);
      navigate('/login');
    }
  }, [navigate]);

  const isAuthenticated = useMemo(() => {
    return !!user;
  }, [user]);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      isAuthenticated,
      setUser, // Direct setter for user data
    }),
    [user, loading, login, logout, isAuthenticated],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
