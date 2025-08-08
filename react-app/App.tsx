import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import NoPermissionPage from './pages/NoPermissionPage';
import OAuthCallbackPage from './pages/OAuthCallbackPage';

function App() {
  // Temporary development mode - bypass auth to test Plaid integration
  const DEV_MODE = true; // Set to false to re-enable authentication

  return (
    <div className="bg-slate-900 text-slate-100 min-h-screen font-sans">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
        <Route path="/no-permission" element={<NoPermissionPage />} />
        <Route
          path="/home"
          element={
            DEV_MODE ? (
              <HomePage />
            ) : (
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            )
          }
        />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </div>
  );
}

export default App;
