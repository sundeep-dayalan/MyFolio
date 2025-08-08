import React, { useState, useEffect, useContext } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import { AuthContext } from '../context/AuthContext';
import { AuthContextType } from '../types';
import { PlaidService, PlaidAccount, PlaidAccountsResponse } from '../services/PlaidService';

const AccountsPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user: authUser } = auth || {};

  // Development mode mock user
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

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<PlaidAccount[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'ready' | 'success' | 'error'>(
    'idle',
  );
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [plaidData, setPlaidData] = useState<PlaidAccountsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (user) {
      loadAccounts();
    }
  }, [user]);

  const loadAccounts = async () => {
    setIsLoading(true);
    try {
      console.log('Loading accounts from backend...');
      const accountData = await PlaidService.getAccounts();
      console.log('Account data received:', accountData);
      setPlaidData(accountData);
      setAccounts(accountData.accounts);
      if (accountData.accounts.length > 0) {
        setConnectionStatus('success');
        console.log(`Successfully loaded ${accountData.accounts.length} accounts`);
      }
    } catch (err) {
      console.error('Error loading accounts:', err);
      setErrorMessage('Failed to load accounts');
    } finally {
      setIsLoading(false);
    }
  };

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
      setConnectionStatus('ready');
      console.log('Connection initialized, ready to open Plaid Link');
    } catch (err) {
      console.error('Error fetching Plaid link token:', err);
      setErrorMessage('Failed to initialize bank connection: ' + String(err));
      setConnectionStatus('error');
    } finally {
      setIsConnecting(false);
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
        const exchangeResult = await PlaidService.exchangePublicToken(publicToken);
        console.log('Token exchange result:', exchangeResult);

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
        setErrorMessage('Bank connection was cancelled or failed: ' + String(err));
        setConnectionStatus('error');
      }
      setIsConnecting(false);
    },
  });

  useEffect(() => {
    if (linkToken && ready && connectionStatus === 'ready') {
      console.log('Opening Plaid Link with token:', linkToken);
      setConnectionStatus('idle');
      open();
    }
  }, [linkToken, ready, connectionStatus, open]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const getAccountIcon = (type: string, subtype?: string) => {
    if (type === 'depository') {
      if (subtype === 'checking') return '🏦';
      if (subtype === 'savings') return '💰';
      return '🏛️';
    }
    if (type === 'credit') return '💳';
    if (type === 'loan') return '🏠';
    if (type === 'investment') return '📈';
    return '🏦';
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto"></div>
          <p className="mt-4 text-slate-300 text-lg">Loading your financial universe...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white flex">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-emerald-500 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
      </div>

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-black/30 backdrop-blur-md border-r border-white/10 transform ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 lg:flex-shrink-0`}
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
              href="/home"
              className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
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
              href="/accounts"
              className="flex items-center space-x-3 px-4 py-3 text-white bg-white/10 rounded-xl"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
                />
              </svg>
              <span>Accounts</span>
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
          </div>

          <div className="mt-8 pt-8 border-t border-white/10">
            <div className="space-y-2">
              <button
                onClick={() => (window.location.href = '/login')}
                className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors w-full"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
                <span>Logout</span>
              </button>
            </div>
          </div>
        </nav>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="bg-black/20 backdrop-blur-md border-b border-white/10 relative z-10">
          <div className="px-4 lg:px-6 xl:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden text-slate-400 hover:text-white"
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
                <div>
                  <h1 className="text-xl lg:text-2xl font-bold text-white">Bank Accounts</h1>
                  <p className="text-slate-400 text-sm lg:text-base">
                    Manage your connected bank accounts
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <img
                    src={user?.picture || 'https://via.placeholder.com/40'}
                    alt={user?.name || 'User'}
                    className="w-8 h-8 rounded-full"
                  />
                  <span className="text-slate-300 hidden sm:inline-block text-sm lg:text-base">
                    {user?.name || 'Guest'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6 xl:p-8 overflow-y-auto relative z-10">
          <div className="max-w-7xl mx-auto">
            {/* Add Account Button */}
            <div className="mb-6 lg:mb-8">
              <button
                onClick={initializePlaidConnection}
                disabled={isConnecting}
                className="inline-flex items-center px-4 lg:px-6 py-3 bg-gradient-to-r from-emerald-500 to-blue-600 text-white font-semibold rounded-xl hover:from-emerald-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-opacity-50 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isConnecting ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Connecting...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-5 h-5 mr-2"
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
                    Connect Bank Account
                  </>
                )}
              </button>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="mb-4 lg:mb-6 p-4 bg-red-900/30 border border-red-500/50 rounded-xl max-w-4xl">
                <div className="flex items-center">
                  <svg
                    className="w-5 h-5 text-red-400 mr-2 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span className="text-red-300 text-sm lg:text-base">{errorMessage}</span>
                </div>
              </div>
            )}

            {/* Loading State */}
            {isLoading ? (
              <div className="text-center py-8 lg:py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto"></div>
                <p className="mt-4 text-slate-300 text-base lg:text-lg">Loading your accounts...</p>
              </div>
            ) : (
              <>
                {/* Accounts Summary */}
                {plaidData && accounts.length > 0 && (
                  <div className="mb-8">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
                      <div className="bg-black/20 backdrop-blur-sm rounded-xl p-4 lg:p-6 border border-white/10">
                        <h3 className="text-slate-400 text-sm font-medium mb-2">Total Accounts</h3>
                        <p className="text-xl lg:text-2xl font-bold text-white">
                          {plaidData.account_count}
                        </p>
                      </div>
                      <div className="bg-black/20 backdrop-blur-sm rounded-xl p-4 lg:p-6 border border-white/10">
                        <h3 className="text-slate-400 text-sm font-medium mb-2">Total Balance</h3>
                        <p className="text-xl lg:text-2xl font-bold text-emerald-400">
                          {formatCurrency(plaidData.total_balance)}
                        </p>
                      </div>
                      <div className="bg-black/20 backdrop-blur-sm rounded-xl p-4 lg:p-6 border border-white/10 sm:col-span-2 lg:col-span-1">
                        <h3 className="text-slate-400 text-sm font-medium mb-2">Connected Banks</h3>
                        <p className="text-xl lg:text-2xl font-bold text-white">
                          {
                            Array.from(new Set(accounts.map((acc) => acc.name.split(' ')[0])))
                              .length
                          }
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Accounts List */}
                {accounts.length > 0 ? (
                  <div>
                    <h2 className="text-xl font-bold text-white mb-6">Your Accounts</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 lg:gap-6">
                      {accounts.map((account) => (
                        <div
                          key={account.account_id}
                          className="bg-black/20 backdrop-blur-sm rounded-xl p-4 lg:p-6 border border-white/10 hover:border-white/20 transition-all duration-200 hover:bg-black/30"
                        >
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center space-x-3">
                              <div className="text-2xl">
                                {getAccountIcon(account.type, account.subtype)}
                              </div>
                              <div className="min-w-0 flex-1">
                                <h3 className="font-semibold text-white truncate">
                                  {account.name}
                                </h3>
                                <p className="text-slate-400 text-sm capitalize truncate">
                                  {account.subtype || account.type}{' '}
                                  {account.mask && `•••• ${account.mask}`}
                                </p>
                              </div>
                            </div>
                          </div>
                          <div className="space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="text-slate-400 text-sm">Available:</span>
                              <span className="text-white font-medium text-sm lg:text-base">
                                {formatCurrency(account.balances.available || 0)}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-slate-400 text-sm">Current:</span>
                              <span className="text-emerald-400 font-semibold text-sm lg:text-base">
                                {formatCurrency(account.balances.current || 0)}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 lg:py-12 max-w-2xl mx-auto">
                    <div className="mx-auto w-20 h-20 lg:w-24 lg:h-24 bg-slate-800 rounded-full flex items-center justify-center mb-6">
                      <svg
                        className="w-10 h-10 lg:w-12 lg:h-12 text-slate-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
                        />
                      </svg>
                    </div>
                    <h3 className="text-lg lg:text-xl font-semibold text-white mb-2">
                      No accounts connected
                    </h3>
                    <p className="text-slate-400 mb-6 text-sm lg:text-base">
                      Connect your first bank account to start managing your finances
                    </p>
                    <button
                      onClick={initializePlaidConnection}
                      disabled={isConnecting}
                      className="inline-flex items-center px-4 lg:px-6 py-3 bg-gradient-to-r from-emerald-500 to-blue-600 text-white font-semibold rounded-xl hover:from-emerald-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-opacity-50 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg
                        className="w-5 h-5 mr-2"
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
                      Get Started
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default AccountsPage;
