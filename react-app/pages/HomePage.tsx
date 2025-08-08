import React, { useContext, useState, useEffect } from 'react';
import { AuthContext } from '../context/AuthContext';
import { AuthContextType } from '../types';
import { usePlaidLink } from 'react-plaid-link';
import { PlaidService, PlaidAccount, PlaidAccountsResponse } from '../services/PlaidService';

const HomePage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user: authUser, logout } = auth || {};

  // Development mode mock user for testing Plaid integration
  const DEV_MODE = true;
  const mockUser = DEV_MODE
    ? {
        id: 'dev-user-123',
        email: 'test@example.com',
        name: 'Test User',
        given_name: 'Test',
        family_name: 'User',
        picture: 'https://via.placeholder.com/40',
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      }
    : null;

  const user = authUser || mockUser;
  const [currentTime, setCurrentTime] = useState(new Date());
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<PlaidAccount[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'ready' | 'success' | 'error'>(
    'idle',
  );
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [plaidData, setPlaidData] = useState<PlaidAccountsResponse | null>(null);

  // Mock financial data - in a real app, this would come from your API
  const [portfolioValue] = useState(142740);
  const [totalGain] = useState(3852.75);
  const [gainPercentage] = useState(2.842);
  const [totalAvailable] = useState(26350);

  // Calculate total value including bank account balances
  const getTotalValue = () => {
    const bankBalance = plaidData?.total_balance || 0;
    return portfolioValue + bankBalance;
  };

  // Calculate total cash available including bank balances
  const getTotalAvailable = () => {
    const bankBalance = plaidData?.total_balance || 0;
    return totalAvailable + bankBalance;
  };

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Only try to load existing accounts if user is authenticated
    if (user) {
      loadAccounts();
    }
  }, [user]);

  const initializePlaidConnection = async () => {
    if (!user) {
      setErrorMessage('Please log in to connect your bank account');
      setConnectionStatus('error');
      return;
    }

    setIsConnecting(true);
    setErrorMessage('');

    try {
      console.log('Fetching Plaid link token for user:', user.id);
      const token = await PlaidService.createLinkToken();
      console.log('Obtained Plaid linkToken:', token);
      setLinkToken(token);
      setConnectionStatus('ready'); // Set to ready so button knows to open
      console.log('Connection initialized, ready to open Plaid Link');
    } catch (err) {
      console.error('Error fetching Plaid link token:', err);
      setErrorMessage('Failed to initialize bank connection: ' + String(err));
      setConnectionStatus('error');
    } finally {
      setIsConnecting(false);
    }
  };

  const loadAccounts = async () => {
    try {
      console.log('Loading accounts from backend...');
      const accountData = await PlaidService.getAccounts();
      console.log('Account data received:', accountData);
      setPlaidData(accountData);
      setAccounts(accountData.accounts);
      if (accountData.accounts.length > 0) {
        setConnectionStatus('success');
        console.log(`Successfully loaded ${accountData.accounts.length} accounts`);
      } else {
        console.log('No accounts found after loading');
      }
    } catch (err) {
      console.error('Error loading accounts:', err);
      // Don't set error status here as user might not have connected yet
    }
  };

  const { open, ready } = usePlaidLink({
    token: linkToken || '',
    onSuccess: async (publicToken: string, metadata: any) => {
      setIsConnecting(true);
      setErrorMessage('');

      try {
        console.log('Plaid connection successful! Public token:', publicToken);
        console.log('Plaid metadata:', metadata);
        console.log('Exchanging token...');
        const exchangeResult = await PlaidService.exchangePublicToken(publicToken);
        console.log('Token exchange result:', exchangeResult);

        console.log('Token exchanged successfully, loading accounts...');
        await loadAccounts();

        setConnectionStatus('success');
        console.log('Bank connection completed successfully');
      } catch (err) {
        console.error('Plaid onSuccess error:', err);
        setErrorMessage('Failed to connect your bank account: ' + String(err));
        setConnectionStatus('error');
      } finally {
        setIsConnecting(false);
      }
    },
    onExit: (err, metadata) => {
      if (err) {
        console.error('Plaid Link exited with error:', err);
        console.log('Exit metadata:', metadata);
        
        // Provide specific guidance for common exit scenarios
        let errorMsg = 'Bank connection was cancelled or failed: ' + String(err);
        
        const errorObj = err as any; // Type assertion for Plaid error properties
        if (errorObj.error_code === 'INVALID_CREDENTIALS') {
          errorMsg = 'Invalid credentials. In sandbox mode, use: Username: user_good, Password: pass_good';
        } else if (errorObj.error_code === 'INVALID_MFA') {
          errorMsg = 'Phone verification failed. In sandbox mode, use: 5551234567 (no spaces/dashes)';
        } else if (errorObj.error_type === 'EXIT_ERROR') {
          errorMsg = 'Connection process was interrupted. Please try again.';
        }
        
        setErrorMessage(errorMsg);
        setConnectionStatus('error');
      } else {
        console.log('Plaid Link was closed by user');
        console.log('Exit metadata:', metadata);
      }
      setIsConnecting(false);
    },
  });

  // Auto-open Plaid Link when token is ready and we're in 'ready' status
  useEffect(() => {
    if (linkToken && ready && connectionStatus === 'ready') {
      console.log('Opening Plaid Link with token:', linkToken);
      setConnectionStatus('idle'); // Reset status to prevent repeated opens
      open();
    }
  }, [linkToken, ready, connectionStatus, open]);

  if (!user) {
    console.log('HomePage: No user data, showing loading state');
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto"></div>
          <p className="mt-4 text-slate-300 text-lg">Loading your financial universe...</p>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatLargeNumber = (num: number) => {
    if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
    return num.toString();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -inset-10 opacity-20">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse"></div>
          <div className="absolute top-3/4 right-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse delay-700"></div>
          <div className="absolute bottom-1/4 left-1/3 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse delay-1000"></div>
        </div>
      </div>

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-black/30 backdrop-blur-md border-r border-white/10 transform ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:flex-shrink-0`}
      >
        <div className="flex items-center justify-between h-16 px-6 border-b border-white/10">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-emerald-400 to-blue-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">₱</span>
            </div>
            <span className="text-white font-bold text-xl">MyFolio</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-slate-400 hover:text-white"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <nav className="mt-8 px-4">
          <div className="space-y-2">
            <a
              href="#"
              className="flex items-center space-x-3 px-4 py-3 text-white bg-white/10 rounded-xl"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 5a2 2 0 012-2h4a2 2 0 012 2v6H8V5z"
                />
              </svg>
              <span>Dashboard</span>
            </a>

            <a
              href="#"
              className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              <span>Portfolio</span>
            </a>

            <a
              href="#"
              className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
                />
              </svg>
              <span>Investments</span>
            </a>

            <a
              href="#"
              className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                />
              </svg>
              <span>Analytics</span>
            </a>

            <a
              href="#"
              className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>Goals</span>
            </a>

            <a
              href="#"
              className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"
                />
              </svg>
              <span>Watchlist</span>
            </a>
          </div>

          <div className="mt-8 pt-8 border-t border-white/10">
            <div className="space-y-2">
              <a
                href="#"
                className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                <span>Settings</span>
              </a>

              <a
                href="#"
                className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>Help & Support</span>
              </a>
            </div>
          </div>
        </nav>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navigation Bar */}
        <nav className="bg-black/30 backdrop-blur-md border-b border-white/10 flex-shrink-0">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden text-slate-300 hover:text-white"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 6h16M4 12h16M4 18h16"
                    />
                  </svg>
                </button>

                <div className="hidden md:flex items-center space-x-6">
                  <div className="relative">
                    <svg
                      className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                      />
                    </svg>
                    <input
                      type="text"
                      placeholder="Search investments..."
                      className="bg-white/10 border border-white/20 rounded-lg pl-10 pr-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                {/* Quick stats */}
                <div className="hidden lg:flex items-center space-x-6 mr-6">
                  <div className="text-center">
                    <p className="text-xs text-slate-400 uppercase tracking-wide">Total Value</p>
                    <p className="text-sm font-semibold text-white">
                      {formatCurrency(getTotalValue())}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 uppercase tracking-wide">Today's Gain</p>
                    <p className="text-sm font-semibold text-emerald-400">+{gainPercentage}%</p>
                  </div>
                </div>

                {/* Notifications */}
                <button className="relative p-2 text-slate-300 hover:text-white transition-colors">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                    />
                  </svg>
                  <span className="absolute top-1 right-1 w-2 h-2 bg-emerald-400 rounded-full"></span>
                </button>

                {/* User menu */}
                <div className="flex items-center space-x-3 bg-white/10 backdrop-blur-md rounded-xl p-2 border border-white/20">
                  <img
                    src={user.picture}
                    alt="Profile"
                    className="w-8 h-8 rounded-full border border-emerald-400"
                  />
                  <div className="hidden md:block text-right">
                    <p className="text-white text-sm font-medium">{user.given_name || user.name}</p>
                    <p className="text-slate-400 text-xs">{user.email}</p>
                  </div>
                  <button
                    onClick={logout}
                    className="p-1 text-slate-300 hover:text-white transition-colors"
                    title="Logout"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <main className="flex-1 p-6 overflow-auto">
          {/* Hero section */}
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-4xl md:text-6xl font-bold text-white mb-4 leading-tight">
                Welcome back,
                <br />
                <span className="bg-gradient-to-r from-emerald-400 to-blue-500 bg-clip-text text-transparent">
                  {user.given_name || user.name}
                </span>
              </h2>
              <p className="text-lg text-slate-300 max-w-xl mx-auto mb-6">
                Track your investments, monitor performance, and grow your wealth. Your personal
                financial dashboard shows everything you need to make informed decisions.
              </p>
              <div className="flex items-center justify-center space-x-4">
                <button className="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-2 rounded-lg font-semibold transition-all transform hover:scale-105">
                  Add Investment
                </button>
                <button className="text-white hover:text-emerald-400 font-semibold flex items-center space-x-2 transition-colors">
                  <span>View Analytics</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </button>
              </div>
            </div>

            {/* Dashboard cards */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* Portfolio overview */}
              <div className="lg:col-span-2 bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <p className="text-slate-300 text-sm uppercase tracking-wide">
                      Your Portfolio Value
                    </p>
                    <h3 className="text-3xl font-bold text-white mt-2">
                      {formatCurrency(getTotalValue())}
                    </h3>
                    <p className="text-emerald-400 text-lg mt-1">
                      +{formatCurrency(totalGain)} (+{gainPercentage}%)
                    </p>
                    {plaidData && plaidData.total_balance > 0 && (
                      <p className="text-slate-300 text-sm mt-2">
                        Includes {formatCurrency(plaidData.total_balance)} from{' '}
                        {plaidData.account_count} bank account
                        {plaidData.account_count !== 1 ? 's' : ''}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-slate-300 text-sm">Last updated</p>
                    <p className="text-white text-sm">{currentTime.toLocaleDateString()}</p>
                    <p className="text-slate-400 text-xs">{currentTime.toLocaleTimeString()}</p>
                  </div>
                </div>

                {/* Mock chart area */}
                <div className="relative h-32 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-xl p-4">
                  <div className="absolute inset-0 flex items-end justify-center">
                    <svg className="w-full h-full" viewBox="0 0 400 160">
                      <path
                        d="M0,120 Q100,80 200,100 T400,60"
                        stroke="url(#gradient)"
                        strokeWidth="3"
                        fill="none"
                        className="drop-shadow-lg"
                      />
                      <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#10b981" />
                          <stop offset="100%" stopColor="#3b82f6" />
                        </linearGradient>
                      </defs>
                      <circle cx="350" cy="70" r="4" fill="#10b981" className="animate-pulse" />
                    </svg>
                  </div>
                  <div className="absolute bottom-4 left-4 text-xs text-slate-300 space-x-4">
                    <span>1D</span> <span>1W</span> <span className="text-emerald-400">1M</span>{' '}
                    <span>3M</span> <span>1Y</span> <span>ALL</span>
                  </div>
                  <div className="absolute top-4 right-4">
                    <div className="flex items-center space-x-2 text-xs text-slate-300">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                      <span>Portfolio Growth</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Available funds */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="flex items-center justify-between mb-6">
                  <h4 className="text-white font-semibold">Asset Allocation</h4>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-emerald-400 rounded-full"></div>
                    <div className="w-3 h-3 bg-purple-400 rounded-full"></div>
                    <div className="w-3 h-3 bg-orange-400 rounded-full"></div>
                  </div>
                </div>
                <p className="text-slate-300 text-sm uppercase tracking-wide mb-2">
                  Available Cash
                </p>
                <h3 className="text-2xl font-bold text-white mb-4">
                  {formatCurrency(getTotalAvailable())}
                </h3>
                <p className="text-slate-300 text-sm mb-4">
                  Ready to invest
                  {plaidData && plaidData.total_balance > 0 && (
                    <span className="block text-xs mt-1">
                      Including {formatCurrency(plaidData.total_balance)} from bank accounts
                    </span>
                  )}
                </p>

                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 bg-emerald-400 rounded-full"></div>
                      <span className="text-slate-300 text-sm">Stocks</span>
                    </div>
                    <div className="text-right">
                      <span className="text-white font-semibold">$12,453.53</span>
                      <p className="text-xs text-emerald-400">+2.4%</p>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 bg-purple-400 rounded-full"></div>
                      <span className="text-slate-300 text-sm">Crypto</span>
                    </div>
                    <div className="text-right">
                      <span className="text-white font-semibold">$8,233.25</span>
                      <p className="text-xs text-red-400">-1.2%</p>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 bg-orange-400 rounded-full"></div>
                      <span className="text-slate-300 text-sm">Bonds</span>
                    </div>
                    <div className="text-right">
                      <span className="text-white font-semibold">$15,423.47</span>
                      <p className="text-xs text-emerald-400">+0.8%</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20 max-w-4xl mx-auto">
              <h3 className="text-xl font-bold text-white mb-4 text-center">Quick Actions</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white/5 rounded-xl p-4 text-center hover:bg-white/10 transition-all cursor-pointer">
                  <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <svg
                      className="w-5 h-5 text-emerald-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                      />
                    </svg>
                  </div>
                  <h4 className="text-white font-semibold mb-1">Add Investment</h4>
                  <p className="text-slate-400 text-xs">Record a new investment or purchase</p>
                </div>

                <div className="bg-white/5 rounded-xl p-4 text-center hover:bg-white/10 transition-all cursor-pointer">
                  <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <svg
                      className="w-5 h-5 text-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                      />
                    </svg>
                  </div>
                  <h4 className="text-white font-semibold mb-1">Portfolio Analysis</h4>
                  <p className="text-slate-400 text-xs">View detailed performance analytics</p>
                </div>

                <div className="bg-white/5 rounded-xl p-4 text-center hover:bg-white/10 transition-all cursor-pointer">
                  <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <svg
                      className="w-5 h-5 text-purple-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <h4 className="text-white font-semibold mb-1">Goals & Targets</h4>
                  <p className="text-slate-400 text-xs">Track financial goals and milestones</p>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-white/10">
                <p className="text-slate-400 text-xs text-center">
                  Portfolio last updated: {currentTime.toLocaleDateString()} at{' '}
                  {currentTime.toLocaleTimeString()}
                </p>
              </div>
            </div>

            {/* Connect Bank Section */}
            <div className="mt-8 bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
              <div className="flex items-center justify-center space-x-3 mb-4">
                <svg
                  className="w-6 h-6 text-emerald-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0-2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
                  />
                </svg>
                <h3 className="text-xl font-bold text-white text-center">Bank Connections</h3>
              </div>

              {/* Status Messages */}
              {connectionStatus === 'success' && accounts.length > 0 && (
                <div className="mb-4 p-3 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-center">
                  <p className="text-emerald-400 text-sm">
                    ✅ Successfully connected {accounts.length} account
                    {accounts.length !== 1 ? 's' : ''}
                  </p>
                </div>
              )}

              {connectionStatus === 'error' && errorMessage && (
                <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-center">
                  <p className="text-red-400 text-sm">❌ {errorMessage}</p>
                </div>
              )}

              {isConnecting && (
                <div className="mb-4 p-3 bg-blue-500/20 border border-blue-500/30 rounded-lg text-center">
                  <p className="text-blue-400 text-sm">🔄 Connecting your bank account...</p>
                </div>
              )}

            {/* Connect Button */}
            {accounts.length === 0 && (
              <div>
                <div className="mb-6 p-4 bg-blue-500/20 border border-blue-500/30 rounded-lg">
                  <h4 className="text-blue-400 font-semibold mb-2 text-center">🧪 Sandbox Test Credentials</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-blue-300 font-medium">Login Credentials:</p>
                      <p className="text-slate-300">Username: <code className="bg-slate-700 px-1 rounded">user_good</code></p>
                      <p className="text-slate-300">Password: <code className="bg-slate-700 px-1 rounded">pass_good</code></p>
                    </div>
                    <div>
                      <p className="text-blue-300 font-medium">Phone Verification:</p>
                      <p className="text-slate-300">Phone: <code className="bg-slate-700 px-1 rounded">5551234567</code></p>
                      <p className="text-slate-400 text-xs">No spaces/dashes, just digits</p>
                      <p className="text-slate-400 text-xs">Alternative: 15551234567</p>
                    </div>
                  </div>
                </div>
                
                <p className="text-slate-300 text-sm mb-6 text-center">
                  Link your bank account to automatically import balances and transactions.
                </p>
                <div className="flex items-center justify-center">
                  <button
                    onClick={() => {
                      if (connectionStatus === 'ready' && linkToken && ready) {
                        open();
                      } else {
                        initializePlaidConnection();
                      }
                    }}
                    disabled={isConnecting}
                    className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-600 text-white rounded-lg font-medium transition-colors disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {isConnecting ? (
                      <>
                        <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                        <span>Initializing...</span>
                      </>
                    ) : connectionStatus === 'ready' && linkToken && ready ? (
                      <>
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                          />
                        </svg>
                        <span>Open Bank Connection</span>
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                          />
                        </svg>
                        <span>Connect Bank Account</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}              {/* Connected Accounts Display */}
              {accounts.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-white text-lg font-semibold">Connected Accounts</h4>
                    <button
                      onClick={() => open()}
                      disabled={!linkToken || !ready || isConnecting}
                      className="px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 text-sm rounded-lg border border-emerald-500/30 transition-colors disabled:opacity-50"
                    >
                      + Add Account
                    </button>
                  </div>

                  <div className="grid gap-3">
                    {accounts.map((account, idx) => (
                      <div key={idx} className="bg-white/5 rounded-lg p-4 border border-white/10">
                        <div className="flex items-center justify-between">
                          <div>
                            <h5 className="text-white font-medium">{account.name}</h5>
                            <p className="text-slate-400 text-sm">
                              {account.subtype} • ••••{account.mask}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-white font-semibold text-lg">
                              {formatCurrency(account.balances.current || 0)}
                            </p>
                            {account.balances.available &&
                              account.balances.available !== account.balances.current && (
                                <p className="text-slate-400 text-sm">
                                  Available: {formatCurrency(account.balances.available)}
                                </p>
                              )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {plaidData && (
                    <div className="pt-4 border-t border-white/10">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-300">Total Bank Balance:</span>
                        <span className="text-white font-semibold text-lg">
                          {formatCurrency(plaidData.total_balance)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default HomePage;
