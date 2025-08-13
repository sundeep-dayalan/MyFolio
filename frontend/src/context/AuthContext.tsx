import React, { createContext, useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { config } from '../config/env';
import type { AuthContextType, UserResponse } from '@/types/types';

export const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [token, setAuthToken] = useState<string | null>(null);
  const navigate = useNavigate();

  // Check for existing authentication on app load
  useEffect(() => {
    const checkStoredAuth = () => {
      const storedToken = localStorage.getItem('authToken');
      const storedUser = localStorage.getItem('user');

      if (storedToken && storedUser) {
        try {
          const userData = JSON.parse(storedUser);
          setUser(userData);
          setAuthToken(storedToken);
        } catch (error) {
          // Clear invalid data
          localStorage.removeItem('authToken');
          localStorage.removeItem('user');
        }
      }

      setLoading(false);
    };

    // Add a small delay to ensure localStorage operations are complete
    setTimeout(checkStoredAuth, 10);
  }, []);

  const login = useCallback(() => {
    // Redirect to server-side OAuth endpoint
    window.location.href = `${config.apiBaseUrl}/auth/oauth/google`;
  }, []);

  const setUserAndToken = useCallback((userData: UserResponse, authToken: string) => {
    setUser(userData);
    setAuthToken(authToken);
    localStorage.setItem('authToken', authToken);
    localStorage.setItem('user', JSON.stringify(userData));
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setAuthToken(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    navigate('/login');
  }, [navigate]);

  const isAuthenticated = useMemo(() => {
    return !!(user && token);
  }, [user, token]);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      isAuthenticated,
      setUser: setUserAndToken, // Map to the expected interface name
      setToken: setAuthToken,
    }),
    [user, loading, login, logout, isAuthenticated, setUserAndToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
