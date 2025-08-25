import './App.css';
import { Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import { Layout } from './components/layout/layout';
import LoginPage from './pages/LoginPage';
import ProtectedRoute from './components/ProtectedRoute';
import { OAuthCallback } from './pages/OAuthCallback';
import AccountsPage from './pages/AccountsPage';
import TransactionsPage from './pages/TransactionsPage';
import SettingsPage from './pages/SettingsPage';
import { Toaster } from './components/ui/sonner';
function App() {
  return (
    <>
      <Routes>
        <Route
          path="/home"
          element={
            <Layout>
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            </Layout>
          }
        />
        <Route
          path="/accounts"
          element={
            <Layout>
              <ProtectedRoute>
                <AccountsPage />
              </ProtectedRoute>
            </Layout>
          }
        />
        <Route
          path="/transactions"
          element={
            <Layout>
              <ProtectedRoute>
                <TransactionsPage />
              </ProtectedRoute>
            </Layout>
          }
        />
        <Route
          path="/settings"
          element={
            <Layout>
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            </Layout>
          }
        />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<OAuthCallback />} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}

export default App;
