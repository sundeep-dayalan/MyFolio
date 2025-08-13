import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { Spinner } from './ui/spinner';
import { logger } from '../services/LoggerService';
import type { AuthContextType } from '@/types/types';
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const auth = useContext(AuthContext) as AuthContextType;

  logger.debug('Current auth state', 'PROTECTED_ROUTE', {
    loading: auth.loading,
    user: auth.user ? 'present' : 'missing',
    isAuthenticated: auth.isAuthenticated,
  });

  if (auth.loading) {
    logger.debug('Still loading, showing spinner', 'PROTECTED_ROUTE');
    return (
      <div className="flex items-center justify-center min-h-screen ">
        <div className="text-center">
          <Spinner />
          <p className="mt-4 text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (!auth.user) {
    logger.info('No user found, redirecting to login', 'PROTECTED_ROUTE');
    return <Navigate to="/login" replace />;
  }

  logger.debug('User authenticated, rendering children', 'PROTECTED_ROUTE');
  return <>{children}</>;
};

export default ProtectedRoute;
