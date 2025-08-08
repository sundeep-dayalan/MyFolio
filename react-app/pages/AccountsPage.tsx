import React, { useState, useEffect, useContext } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import { AuthContext } from '../context/AuthContext';
import { AuthContextType } from '../types';
import { PlaidAccount } from '../services/PlaidService';
import {
  useAccountsQuery,
  useCreateLinkTokenMutation,
  useExchangePublicTokenMutation,
  useItemsQuery,
  useRevokeItemMutation,
  useRevokeAllItemsMutation,
} from '../hooks/usePlaidApi';

const AccountsPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user, logout } = auth || {};

  // If no user is authenticated, redirect to login
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-4">Authentication Required</h2>
          <p className="text-slate-300 mb-6">Please log in to access your bank accounts.</p>
          <button
            onClick={() => (window.location.href = '/login')}
            className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-blue-600 text-white font-semibold rounded-xl hover:from-emerald-600 hover:to-blue-700 transition-all duration-200"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  // State
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'ready' | 'success' | 'error'>(
    'idle',
  );
  const [viewMode, setViewMode] = useState<'all' | 'by-bank'>('all');

  // TanStack Query hooks
  const {
    data: accountsData,
    isLoading,
    error: accountsError,
    isError: isAccountsError,
  } = useAccountsQuery();

  const createLinkTokenMutation = useCreateLinkTokenMutation();
  const exchangePublicTokenMutation = useExchangePublicTokenMutation();

  // Derived data first
  const accounts = accountsData?.accounts || [];

  // Items and revoke mutations (now that accounts is available)
  const {
    data: itemsData,
    isLoading: itemsLoading,
    error: itemsError,
  } = useItemsQuery(accounts.length > 0); // Only fetch items if we have accounts

  const revokeItemMutation = useRevokeItemMutation();
  const revokeAllItemsMutation = useRevokeAllItemsMutation();

  // State for confirmation dialogs
  const [showConfirmDialog, setShowConfirmDialog] = useState<{
    type: 'single' | 'all';
    bankName?: string;
  } | null>(null);

  // More derived data
  const isConnecting = createLinkTokenMutation.isPending || exchangePublicTokenMutation.isPending;
  const errorMessage = isAccountsError
    ? `Failed to load accounts: ${accountsError?.message}`
    : createLinkTokenMutation.error?.message
    ? `Failed to initialize bank connection: ${createLinkTokenMutation.error.message}`
    : exchangePublicTokenMutation.error?.message
    ? `Failed to connect your bank account: ${exchangePublicTokenMutation.error.message}`
    : '';

  const initializePlaidConnection = async () => {
    setConnectionStatus('idle');

    try {
      console.log('Fetching Plaid link token for user:', user.id);
      const token = await createLinkTokenMutation.mutateAsync();
      console.log('Obtained Plaid linkToken:', token);
      setLinkToken(token);
      setConnectionStatus('ready');
      console.log('Connection initialized, ready to open Plaid Link');
    } catch (err) {
      console.error('Error fetching Plaid link token:', err);
      setConnectionStatus('error');
    }
  };

  const { open, ready } = usePlaidLink({
    token: linkToken || '',
    onSuccess: async (publicToken: string, metadata: any) => {
      try {
        console.log('Plaid connection successful! Public token:', publicToken);
        console.log('Plaid metadata:', metadata);

        await exchangePublicTokenMutation.mutateAsync(publicToken);
        setConnectionStatus('success');
        console.log('Bank connection completed successfully');
      } catch (err) {
        console.error('Plaid onSuccess error:', err);
        setConnectionStatus('error');
      }
    },
    onExit: (err, metadata) => {
      if (err) {
        console.error('Plaid Link exited with error:', err);
        setConnectionStatus('error');
      }
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

  const groupAccountsByBank = (accounts: PlaidAccount[]) => {
    const grouped: { [bankName: string]: PlaidAccount[] } = {};

    accounts.forEach((account) => {
      const bankName = account.institution_name || 'Unknown Bank';
      if (!grouped[bankName]) {
        grouped[bankName] = [];
      }
      grouped[bankName].push(account);
    });

    return grouped;
  };

  // Helper function to find item_id for a bank
  const getItemIdForBank = (bankName: string): string | null => {
    if (!itemsData?.items) return null;

    const item = itemsData.items.find((item) => item.institution_name === bankName);
    return item?.item_id || null;
  };

  // Handle single bank unlink
  const handleUnlinkBank = async (bankName: string) => {
    const itemId = getItemIdForBank(bankName);
    if (!itemId) {
      console.error('Could not find item_id for bank:', bankName);
      return;
    }

    try {
      await revokeItemMutation.mutateAsync(itemId);
      setShowConfirmDialog(null);
    } catch (error) {
      console.error('Failed to unlink bank:', error);
    }
  };

  // Handle all banks unlink
  const handleUnlinkAllBanks = async () => {
    try {
      await revokeAllItemsMutation.mutateAsync();
      setShowConfirmDialog(null);
    } catch (error) {
      console.error('Failed to unlink all banks:', error);
    }
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
              href="/home"
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
          </div>

          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="space-y-2">
              <a
                href="/accounts"
                className="flex items-center space-x-3 px-4 py-3 text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
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
                <button
                  onClick={logout}
                  className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors duration-200 flex items-center space-x-1"
                  title="Logout"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6 xl:p-8 overflow-y-auto relative z-10">
          <div className="max-w-7xl mx-auto">
            {/* Add Account Button */}
            <div className="mb-6 lg:mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
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

              {/* View Mode Toggle */}
              {accounts.length > 0 && (
                <div className="flex items-center space-x-3">
                  <div className="flex bg-black/20 backdrop-blur-sm rounded-xl p-1 border border-white/10">
                    <button
                      onClick={() => setViewMode('all')}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                        viewMode === 'all'
                          ? 'bg-emerald-500 text-white shadow-lg'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      All Accounts
                    </button>
                    <button
                      onClick={() => setViewMode('by-bank')}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                        viewMode === 'by-bank'
                          ? 'bg-emerald-500 text-white shadow-lg'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      By Bank
                    </button>
                  </div>

                  {/* Disconnect All Banks Button */}
                  <button
                    onClick={() => setShowConfirmDialog({ type: 'all' })}
                    disabled={revokeAllItemsMutation.isPending}
                    className="flex items-center space-x-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 rounded-xl border border-red-500/30 hover:border-red-500/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    title="Disconnect all bank connections"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L12 12l6.364 6.364M12 12l-6.364-6.364M12 12l6.364-6.364M12 12l-6.364 6.364"
                      />
                    </svg>
                    <span>Disconnect All</span>
                  </button>
                </div>
              )}
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
                {accountsData && accounts.length > 0 && (
                  <div className="mb-8">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
                      <div className="bg-black/20 backdrop-blur-sm rounded-xl p-4 lg:p-6 border border-white/10">
                        <h3 className="text-slate-400 text-sm font-medium mb-2">Total Accounts</h3>
                        <p className="text-xl lg:text-2xl font-bold text-white">
                          {accountsData.account_count}
                        </p>
                      </div>
                      <div className="bg-black/20 backdrop-blur-sm rounded-xl p-4 lg:p-6 border border-white/10">
                        <h3 className="text-slate-400 text-sm font-medium mb-2">Total Balance</h3>
                        <p className="text-xl lg:text-2xl font-bold text-emerald-400">
                          {formatCurrency(accountsData.total_balance)}
                        </p>
                      </div>
                      <div className="bg-black/20 backdrop-blur-sm rounded-xl p-4 lg:p-6 border border-white/10 sm:col-span-2 lg:col-span-1">
                        <h3 className="text-slate-400 text-sm font-medium mb-2">Connected Banks</h3>
                        <p className="text-xl lg:text-2xl font-bold text-white">
                          {Array.from(
                            new Set(accounts.map((acc) => acc.institution_name).filter(Boolean)),
                          ).length ||
                            Array.from(new Set(accounts.map((acc) => acc.name.split(' ')[0])))
                              .length}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Accounts List */}
                {accounts.length > 0 ? (
                  <div>
                    <h2 className="text-xl font-bold text-white mb-6">
                      {viewMode === 'by-bank' ? 'Your Accounts by Bank' : 'Your Accounts'}
                    </h2>

                    {viewMode === 'all' ? (
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
                                  {account.institution_name && (
                                    <p className="text-emerald-400 text-xs font-medium mb-1">
                                      {account.institution_name}
                                    </p>
                                  )}
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
                    ) : (
                      <div className="space-y-8">
                        {Object.entries(groupAccountsByBank(accounts)).map(
                          ([bankName, bankAccounts]) => {
                            const bankTotal = bankAccounts.reduce(
                              (sum, acc) => sum + (acc.balances.current || 0),
                              0,
                            );

                            return (
                              <div
                                key={bankName}
                                className="bg-black/10 backdrop-blur-sm rounded-2xl p-6 border border-white/5"
                              >
                                <div className="flex items-center justify-between mb-6">
                                  <div className="flex items-center space-x-3">
                                    <h3 className="text-lg font-bold text-emerald-400">
                                      {bankName}
                                    </h3>
                                    <div className="bg-emerald-500/20 px-3 py-1 rounded-full">
                                      <span className="text-emerald-400 text-sm font-medium">
                                        {bankAccounts.length} account
                                        {bankAccounts.length !== 1 ? 's' : ''}
                                      </span>
                                    </div>
                                  </div>
                                  <div className="flex items-center space-x-4">
                                    <div className="text-right">
                                      <p className="text-slate-400 text-sm">Total Balance</p>
                                      <p className="text-xl font-bold text-white">
                                        {formatCurrency(bankTotal)}
                                      </p>
                                    </div>
                                    <button
                                      onClick={() =>
                                        setShowConfirmDialog({
                                          type: 'single',
                                          itemId: getItemIdForBank(bankName) || '',
                                          bankName,
                                        })
                                      }
                                      disabled={revokeItemMutation.isPending}
                                      className="flex items-center space-x-2 px-3 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 rounded-lg border border-red-500/30 hover:border-red-500/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                                      title={`Unlink ${bankName}`}
                                    >
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
                                          d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L12 12l-2.122-2.122m0 0L7.76 7.76m2.122 2.122L12 12m0 0l2.878-2.878M12 12l-2.122 2.122"
                                        />
                                      </svg>
                                      <span>Unlink</span>
                                    </button>
                                  </div>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 lg:gap-6">
                                  {bankAccounts.map((account) => (
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
                            );
                          },
                        )}
                      </div>
                    )}
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

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div
              className="fixed inset-0 bg-black bg-opacity-75 transition-opacity"
              onClick={() => setShowConfirmDialog(null)}
            ></div>

            {/* Modal panel */}
            <div className="inline-block align-bottom bg-slate-800 rounded-2xl px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6 border border-white/10">
              <div className="sm:flex sm:items-start">
                <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-500/20 sm:mx-0 sm:h-10 sm:w-10">
                  <svg
                    className="h-6 w-6 text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                    />
                  </svg>
                </div>
                <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                  <h3 className="text-lg leading-6 font-medium text-white">
                    {showConfirmDialog.type === 'all'
                      ? 'Disconnect All Banks?'
                      : `Disconnect ${showConfirmDialog.bankName}?`}
                  </h3>
                  <div className="mt-2">
                    <p className="text-sm text-slate-300">
                      {showConfirmDialog.type === 'all'
                        ? 'This will permanently disconnect all your bank connections. You will need to reconnect them to access your account data again.'
                        : `This will permanently disconnect ${showConfirmDialog.bankName} from your account. You will need to reconnect it to access this bank's data again.`}
                    </p>
                  </div>
                </div>
              </div>
              <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={
                    showConfirmDialog.type === 'all'
                      ? handleUnlinkAllBanks
                      : () => handleUnlinkBank(showConfirmDialog.bankName!)
                  }
                  disabled={revokeItemMutation.isPending || revokeAllItemsMutation.isPending}
                  className="w-full inline-flex justify-center rounded-xl border border-transparent shadow-sm px-4 py-2 text-base font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors bg-red-600 hover:bg-red-700 focus:ring-red-500"
                >
                  {revokeItemMutation.isPending || revokeAllItemsMutation.isPending
                    ? 'Disconnecting...'
                    : 'Yes, Disconnect'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowConfirmDialog(null)}
                  disabled={revokeItemMutation.isPending || revokeAllItemsMutation.isPending}
                  className="mt-3 w-full inline-flex justify-center rounded-xl border border-slate-600 shadow-sm px-4 py-2 bg-slate-700 text-base font-medium text-slate-300 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 sm:mt-0 sm:w-auto sm:text-sm disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AccountsPage;
