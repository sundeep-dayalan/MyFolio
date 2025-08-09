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
import { TransactionsHeader } from '@/components/custom/transactions/transactions-header';
import { TransactionsBankTabs } from '@/components/custom/transactions/transactions-bank-tabs';
import { TransactionsAccountTabs } from '@/components/custom/transactions/transactions-account-tabs';
import { TransactionsEmptyState } from '@/components/custom/transactions/transactions-empty-state';

const TransactionsPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user } = auth || {};

  // If no user is authenticated, redirect to login
  if (!user) {
    window.location.href = '/login';
    return null;
  }

  // State
  const [days] = useState(30);
  const [activeBankTab, setActiveBankTab] = useState<string | null>(null);
  const [activeAccountTabs, setActiveAccountTabs] = useState<{ [bankName: string]: string }>({});
  const [errorMessage, setErrorMessage] = useState<string>('');

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
    return amount > 0 ? 'text-red-600' : 'text-green-600';
  };

  const handleGoToAccounts = () => {
    window.location.href = '/accounts';
  };

  const handleRefresh = async (bankName: string) => {
    const item = items.find((item) => item.institution_name === bankName);
    if (item) {
      try {
        setErrorMessage('');
        await refreshTransactionsMutation.mutateAsync({ itemId: item.item_id, days });
      } catch (error) {
        console.error('Failed to refresh transactions for bank:', bankName, error);
        setErrorMessage(`Failed to refresh transactions for ${bankName}. Please try again.`);
      }
    }
  };

  const getAccountName = (accountId: string) => {
    const account = accounts.find((acc) => acc.account_id === accountId);
    return account?.name || 'Unknown Account';
  };

  // const getAccountType = (accountId: string) => {
  //   const account = accounts.find((acc) => acc.account_id === accountId);
  //   return account?.type || '';
  // };

  // Main render following HomePage pattern
  return (
    <>
      <div className="flex flex-1 flex-col">
        <div className="@container/main flex flex-1 flex-col gap-2">
          <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
            <TransactionsHeader
              activeBankName={activeBankTab}
              onRefreshBank={handleRefresh}
              isRefreshing={refreshTransactionsMutation.isPending}
              errorMessage={errorMessage}
            />

            <TransactionsEmptyState
              isLoading={transactionsLoading}
              hasError={!!transactionsError}
              hasTransactions={bankNames.length > 0}
              onGoToAccounts={handleGoToAccounts}
            />

            {bankNames.length > 0 && (
              <>
                <TransactionsBankTabs
                  bankNames={bankNames}
                  activeBankTab={activeBankTab}
                  onBankTabChange={setActiveBankTab}
                />

                {activeBankTab && (
                  <TransactionsAccountTabs
                    activeBankName={activeBankTab}
                    accountsByBank={accountsByBank}
                    activeAccountTabs={activeAccountTabs}
                    transactionsByBankAndAccount={transactionsByBankAndAccount}
                    onAccountTabChange={(bankName, accountId) =>
                      setActiveAccountTabs((prev) => ({
                        ...prev,
                        [bankName]: accountId,
                      }))
                    }
                    getAccountName={getAccountName}
                    formatCurrency={formatCurrency}
                    formatDate={formatDate}
                    getCategoryIcon={getCategoryIcon}
                    getTransactionTypeColor={getTransactionTypeColor}
                  />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default TransactionsPage;
