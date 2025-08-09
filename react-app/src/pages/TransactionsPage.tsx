import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import {
  useTransactionsQuery,
  useRefreshTransactionsMutation,
  useAccountsQuery,
  useItemsQuery,
} from '../hooks/usePlaidApi';
import type { AuthContextType } from '@/types/types';
import type { PlaidTransaction } from '@/services/PlaidService';

const TransactionsPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user, logout } = auth || {};

  // If no user is authenticated, redirect to login
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-4">Authentication Required</h2>
          <p className="text-slate-300 mb-6">Please log in to access your transactions.</p>
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
  const [days, setDays] = useState(30);
  const [activeBankTab, setActiveBankTab] = useState<string | null>(null);
  const [activeAccountTabs, setActiveAccountTabs] = useState<{ [bankName: string]: string }>({});

  // API calls
  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    error: transactionsError,
  } = useTransactionsQuery(days);
  const { data: accountsData } = useAccountsQuery();
  const { data: itemsData } = useItemsQuery();
  const refreshTransactionsMutation = useRefreshTransactionsMutation();

  const transactions = transactionsData?.transactions || [];
  const accounts = accountsData?.accounts || [];
  const items = itemsData?.items || [];

  // Group transactions by bank and then by account
  const groupTransactionsByBankAndAccount = () => {
    const grouped: { [bankName: string]: { [accountId: string]: PlaidTransaction[] } } = {};

    transactions.forEach((transaction) => {
      const bankName = transaction.institution_name || 'Unknown Bank';
      const accountId = transaction.account_id;

      if (!grouped[bankName]) {
        grouped[bankName] = {};
      }
      if (!grouped[bankName][accountId]) {
        grouped[bankName][accountId] = [];
      }
      grouped[bankName][accountId].push(transaction);
    });

    return grouped;
  };

  // Group accounts by bank
  const groupAccountsByBank = () => {
    const grouped: { [bankName: string]: typeof accounts } = {};
    accounts.forEach((account) => {
      const bankName = account.institution_name || 'Unknown Bank';
      if (!grouped[bankName]) {
        grouped[bankName] = [];
      }
      grouped[bankName].push(account);
    });
    return grouped;
  };

  const transactionsByBankAndAccount = groupTransactionsByBankAndAccount();
  const accountsByBank = groupAccountsByBank();
  const bankNames = Object.keys(transactionsByBankAndAccount);

  // Set initial active tab
  useEffect(() => {
    if (bankNames.length > 0 && !activeBankTab) {
      setActiveBankTab(bankNames[0]);
    }
  }, [bankNames, activeBankTab]);

  // Set initial account tab for each bank
  useEffect(() => {
    const newActiveAccountTabs = { ...activeAccountTabs };
    let hasChanges = false;

    bankNames.forEach((bankName) => {
      if (!newActiveAccountTabs[bankName]) {
        const bankAccounts = accountsByBank[bankName] || [];
        if (bankAccounts.length > 0) {
          newActiveAccountTabs[bankName] = bankAccounts[0].account_id;
          hasChanges = true;
        }
      }
    });

    if (hasChanges) {
      setActiveAccountTabs(newActiveAccountTabs);
    }
  }, [bankNames, accountsByBank, activeAccountTabs]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Math.abs(amount));
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getCategoryIcon = (categories: string[]) => {
    const category = categories[0]?.toLowerCase() || '';
    if (category.includes('food')) return '🍕';
    if (category.includes('transfer')) return '🔄';
    if (category.includes('payment')) return '💳';
    if (category.includes('deposit')) return '💰';
    if (category.includes('gas') || category.includes('automotive')) return '⛽';
    if (category.includes('shopping') || category.includes('general merchandise')) return '🛍️';
    if (category.includes('entertainment')) return '🎬';
    if (category.includes('healthcare')) return '🏥';
    if (category.includes('travel')) return '✈️';
    if (category.includes('bills') || category.includes('utilities')) return '📋';
    return '💼';
  };

  const getTransactionTypeColor = (amount: number) => {
    return amount > 0 ? 'text-red-400' : 'text-emerald-400';
  };

  const handleRefresh = async (bankName: string) => {
    const item = items.find((item) => item.institution_name === bankName);
    if (item) {
      try {
        await refreshTransactionsMutation.mutateAsync({ itemId: item.item_id, days });
      } catch (error) {
        console.error('Failed to refresh transactions for bank:', bankName, error);
      }
    }
  };

  const getAccountName = (accountId: string) => {
    const account = accounts.find((acc) => acc.account_id === accountId);
    return account?.name || 'Unknown Account';
  };

  const getAccountType = (accountId: string) => {
    const account = accounts.find((acc) => acc.account_id === accountId);
    return account?.type || '';
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto"></div>
          <p className="mt-4 text-slate-300 text-lg">Loading your transactions...</p>
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
              <a
                href="/transactions"
                className="flex items-center space-x-3 px-4 py-3 text-white bg-white/10 rounded-xl"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                <span>Transactions</span>
              </a>
            </div>
          </div>
        </nav>

        <div className="absolute bottom-8 left-4 right-4">
          <div className="bg-white/5 backdrop-blur-sm rounded-xl p-4 border border-white/10">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-emerald-400 to-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium truncate">{user?.name || 'User'}</p>
                <p className="text-slate-300 text-sm truncate">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="mt-3 w-full px-3 py-2 text-sm text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}

      {/* Main content */}
      <div className="flex-1 lg:ml-0 min-h-screen">
        {/* Top bar */}
        <div className="bg-black/20 backdrop-blur-md border-b border-white/10 px-4 lg:px-8 py-4">
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
                <h1 className="text-2xl font-bold text-white">Transactions</h1>
                <p className="text-slate-300 text-sm mt-1">
                  {transactionsData
                    ? `${transactionsData.transaction_count} transactions`
                    : 'Loading...'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Days filter */}
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-emerald-400"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
              </select>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 lg:p-8 space-y-6">
          {transactionsLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto"></div>
              <p className="mt-4 text-slate-300">Loading transactions...</p>
            </div>
          ) : transactionsError ? (
            <div className="text-center py-12">
              <div className="text-red-400 mb-4">
                <svg
                  className="w-16 h-16 mx-auto"
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
              </div>
              <p className="text-slate-300">Failed to load transactions</p>
            </div>
          ) : bankNames.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-slate-400 mb-4">
                <svg
                  className="w-16 h-16 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
              </div>
              <p className="text-slate-300 text-lg">No transactions found</p>
              <p className="text-slate-400 mt-2">
                Connect your bank accounts to see transaction history
              </p>
              <button
                onClick={() => (window.location.href = '/accounts')}
                className="mt-4 px-6 py-3 bg-gradient-to-r from-emerald-500 to-blue-600 text-white font-semibold rounded-xl hover:from-emerald-600 hover:to-blue-700 transition-all duration-200"
              >
                Connect Bank Accounts
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Bank Tabs */}
              <div className="border-b border-white/10">
                <nav className="flex space-x-8">
                  {bankNames.map((bankName) => (
                    <button
                      key={bankName}
                      onClick={() => setActiveBankTab(bankName)}
                      className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                        activeBankTab === bankName
                          ? 'border-emerald-400 text-emerald-400'
                          : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-300'
                      }`}
                    >
                      {bankName}
                    </button>
                  ))}
                </nav>
              </div>

              {/* Active Bank Content */}
              {activeBankTab && transactionsByBankAndAccount[activeBankTab] && (
                <div className="space-y-6">
                  {/* Bank Header with Refresh Button */}
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">{activeBankTab}</h2>
                    <button
                      onClick={() => handleRefresh(activeBankTab)}
                      disabled={refreshTransactionsMutation.isPending}
                      className="flex items-center space-x-2 px-4 py-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-white transition-colors"
                    >
                      <svg
                        className={`w-4 h-4 ${
                          refreshTransactionsMutation.isPending ? 'animate-spin' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      <span>Refresh</span>
                    </button>
                  </div>

                  {/* Account Tabs */}
                  <div className="border-b border-white/20">
                    <nav className="flex space-x-8">
                      {(accountsByBank[activeBankTab] || []).map((account) => (
                        <button
                          key={account.account_id}
                          onClick={() =>
                            setActiveAccountTabs((prev) => ({
                              ...prev,
                              [activeBankTab]: account.account_id,
                            }))
                          }
                          className={`py-2 px-2 border-b-2 font-medium text-xs transition-colors ${
                            activeAccountTabs[activeBankTab] === account.account_id
                              ? 'border-blue-400 text-blue-400'
                              : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-400'
                          }`}
                        >
                          {account.name} ({account.subtype})
                        </button>
                      ))}
                    </nav>
                  </div>

                  {/* Transactions List */}
                  {activeAccountTabs[activeBankTab] &&
                    transactionsByBankAndAccount[activeBankTab][
                      activeAccountTabs[activeBankTab]
                    ] && (
                      <div className="bg-white/5 backdrop-blur-md rounded-xl border border-white/10">
                        <div className="p-6">
                          <h3 className="text-lg font-semibold text-white mb-4">
                            {getAccountName(activeAccountTabs[activeBankTab])} Transactions
                          </h3>
                          <div className="space-y-3">
                            {transactionsByBankAndAccount[activeBankTab][
                              activeAccountTabs[activeBankTab]
                            ].map((transaction) => (
                              <div
                                key={transaction.transaction_id}
                                className="flex items-center justify-between p-4 bg-white/5 rounded-lg hover:bg-white/10 transition-colors"
                              >
                                <div className="flex items-center space-x-4">
                                  <div className="text-2xl">
                                    {getCategoryIcon(transaction.category || [])}
                                  </div>
                                  <div>
                                    <p className="font-medium text-white">{transaction.name}</p>
                                    <div className="flex items-center space-x-2 text-sm text-slate-400">
                                      <span>{formatDate(transaction.date)}</span>
                                      {transaction.category && transaction.category[0] && (
                                        <>
                                          <span>•</span>
                                          <span>{transaction.category[0]}</span>
                                        </>
                                      )}
                                      {transaction.pending && (
                                        <>
                                          <span>•</span>
                                          <span className="text-yellow-400">Pending</span>
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div
                                  className={`text-lg font-semibold ${getTransactionTypeColor(
                                    transaction.amount,
                                  )}`}
                                >
                                  {transaction.amount > 0 ? '-' : '+'}
                                  {formatCurrency(transaction.amount)}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransactionsPage;
