import React, { useState, useContext, useMemo, useEffect } from 'react';
import { AuthContext } from '../context/AuthContext';
import {
  useAccountsQuery,
  useItemsQuery,
  useRefreshTransactionsMutation,
  useForceRefreshTransactionsMutation,
} from '../hooks/usePlaidApi';
import type { AuthContextType } from '@/types/types';
import { TransactionsHeader } from '@/components/custom/transactions/transactions-header';
import { TransactionsEmptyState } from '@/components/custom/transactions/transactions-empty-state';
import { toast } from 'sonner';
import { TransactionsDataTable } from '@/components/custom/transactions/transactions-data-table';
import { columns } from '@/components/custom/transactions/transactions-columns';
import type { PaginatedTransactionsRequest } from '@/services/FirestoreService';

const TransactionsPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user } = auth || {};

  // If no user is authenticated, redirect to login
  if (!user) {
    window.location.href = '/login';
    return null;
  }

  // State for filtering and UI
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [selectedBank, setSelectedBank] = useState<string | null>(null);
  const [transactionType, setTransactionType] = useState<'added' | 'modified' | 'removed' | 'all'>(
    'added',
  );

  // API calls for accounts and items
  const { data: accountsData, isLoading: accountsLoading } = useAccountsQuery();
  const { data: itemsData, isLoading: itemsLoading } = useItemsQuery();
  const refreshTransactionsMutation = useRefreshTransactionsMutation();
  const forceRefreshTransactionsMutation = useForceRefreshTransactionsMutation();

  const accounts = accountsData?.accounts || [];
  const items = itemsData?.items || [];

  // Get unique institution names from accounts
  const availableBanks = useMemo(() => {
    const uniqueInstitutions = new Set<string>();
    accounts.forEach((account) => {
      if (account.institution_name) {
        uniqueInstitutions.add(account.institution_name);
      }
    });
    return Array.from(uniqueInstitutions).sort();
  }, [accounts]);

  // Map institution name to item_id
  const institutionToItemMap = useMemo(() => {
    const map = new Map<string, string>();
    items.forEach((item) => {
      if (item.institution_name && item.item_id) {
        map.set(item.institution_name, item.item_id);
      }
    });
    return map;
  }, [items]);

  // Auto-select first bank if none selected and banks are available
  useEffect(() => {
    if (!selectedBank && availableBanks.length > 0 && !accountsLoading && !itemsLoading) {
      setSelectedBank(availableBanks[0]);
    }
  }, [availableBanks, selectedBank, accountsLoading, itemsLoading]);

  // Initial request for the data table with item_id filter (more efficient than institution_name)
  const initialRequest: PaginatedTransactionsRequest = useMemo(() => {
    const itemId = selectedBank ? institutionToItemMap.get(selectedBank) : null;
    const request: PaginatedTransactionsRequest = {
      page: 1,
      pageSize: 20,
      sortBy: 'date',
      sortOrder: 'desc' as const,
      transactionType: transactionType,
      filters: {
        ...(itemId && { itemId: itemId }),
      },
    };

    return request;
  }, [selectedBank, institutionToItemMap, transactionType]);
  const handleGoToAccounts = () => {
    window.location.href = '/accounts';
  };

  const handleBankChange = (bankName: string | null) => {
    setSelectedBank(bankName);
    setErrorMessage(''); // Clear any previous errors
  };

  const handleRefreshBank = async (bankName: string) => {
    const itemId = institutionToItemMap.get(bankName);
    if (!itemId) {
      setErrorMessage(`Could not find item ID for ${bankName}`);
      return;
    }

    try {
      setErrorMessage('');
      const result = await refreshTransactionsMutation.mutateAsync({ itemId });

      // Show success toast with transaction counts
      if (result.success) {
        if (result.total_processed === 0) {
          toast.success(`No recent transactions found for ${bankName}`, {
            description: 'Your account is up to date',
          });
        } else {
          // Create detailed description with counts
          const details = [];
          if (result.transactions_added > 0) {
            details.push(`${result.transactions_added} added`);
          }
          if (result.transactions_modified > 0) {
            details.push(`${result.transactions_modified} updated`);
          }
          if (result.transactions_removed > 0) {
            details.push(`${result.transactions_removed} removed`);
          }

          toast.success(result.message || 'Transactions updated successfully!', {
            description: `${bankName}: ${details.join(', ')}`,
            duration: 5000, // Show longer for transaction updates
          });
        }
      }

      // The mutation will automatically invalidate the query cache
    } catch (error) {
      setErrorMessage(
        `Failed to refresh transactions: ${error instanceof Error ? error.message : String(error)}`,
      );

      toast.error('Failed to refresh transactions', {
        description: error instanceof Error ? error.message : String(error),
      });
    }
  };

  const handleForceRefreshBank = async (bankName: string) => {
    const itemId = institutionToItemMap.get(bankName);
    if (!itemId) {
      setErrorMessage(`Could not find item ID for ${bankName}`);
      return;
    }

    try {
      setErrorMessage('');
      const result = await forceRefreshTransactionsMutation.mutateAsync({ itemId });

      // Show success toast for async operation
      if (result.success && result.async_operation) {
        toast.success(`Resync transactions request submitted for ${bankName}`, {
          description:
            'Check back later for updated transactions. This process may take a few minutes.',
          duration: 7000, // Show longer for async operations
        });
      }

      // Note: Don't invalidate queries here since processing is async
    } catch (error) {
      setErrorMessage(
        `Failed to submit force refresh request: ${
          error instanceof Error ? error.message : String(error)
        }`,
      );

      toast.error('Failed to submit force refresh request', {
        description: error instanceof Error ? error.message : String(error),
      });
    }
  };

  // Main render with new data table
  return (
    <>
      <div className="flex flex-1 flex-col">
        <div className="@container/main flex flex-1 flex-col gap-2">
          <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
            <TransactionsHeader
              activeBankName={selectedBank}
              availableBanks={availableBanks}
              onBankChange={handleBankChange}
              onRefreshBank={handleRefreshBank}
              isRefreshing={refreshTransactionsMutation.isPending}
              onForceRefreshBank={handleForceRefreshBank}
              isForceRefreshing={forceRefreshTransactionsMutation.isPending}
              errorMessage={errorMessage}
              transactionType={transactionType}
              onTransactionTypeChange={setTransactionType}
            />

            {/* Show empty state only if we have no accounts */}
            <TransactionsEmptyState
              isLoading={accountsLoading || itemsLoading}
              hasError={!!errorMessage}
              hasTransactions={accounts.length > 0}
              onGoToAccounts={handleGoToAccounts}
            />

            {/* Main data table */}
            {accounts.length > 0 && selectedBank && (
              <div className="px-4 lg:px-6">
                <TransactionsDataTable columns={columns} initialRequest={initialRequest} />
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default TransactionsPage;
