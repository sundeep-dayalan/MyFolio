import {
  PlaidService,
  type ForceRefreshTransactionsResponse,
  type PlaidAccountsResponse,
  type PlaidDataInfo,
  type PlaidItemsResponse,
  type PlaidTransactionsResponse,
  type RefreshTransactionsResponse,
} from '@/services/PlaidService';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

// Query Keys
export const QUERY_KEYS = {
  accounts: 'accounts',
  accountsDataInfo: 'accountsDataInfo',
  linkToken: 'linkToken',
  items: 'items',
  transactions: 'transactions',
} as const;

// Get Accounts Query - Now uses cached data by default
export const useAccountsQuery = () => {
  return useQuery<PlaidAccountsResponse>({
    queryKey: [QUERY_KEYS.accounts],
    queryFn: PlaidService.getAccounts,
    staleTime: 5 * 60 * 1000, // 5 minutes - cache is managed server-side
    refetchOnMount: true,
  });
};

// Get Accounts Data Info Query
export const useAccountsDataInfoQuery = () => {
  return useQuery<PlaidDataInfo>({
    queryKey: [QUERY_KEYS.accountsDataInfo],
    queryFn: PlaidService.getAccountsDataInfo,
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchOnMount: true,
  });
};

// Create Link Token Mutation
export const useCreateLinkTokenMutation = () => {
  return useMutation<string, Error>({
    mutationFn: PlaidService.createLinkToken,
    onSuccess: () => {},
    onError: () => {},
  });
};

// Exchange Public Token Mutation
export const useExchangePublicTokenMutation = () => {
  const queryClient = useQueryClient();

  return useMutation<
    { success: boolean; item_id: string; institution_name?: string },
    Error,
    string
  >({
    mutationFn: PlaidService.exchangePublicToken,
    onSuccess: () => {
      // Invalidate and refetch accounts after successful token exchange
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.accounts] });
    },
    onError: () => {},
  });
};

// Refresh Accounts Mutation (for manual refresh from Plaid API)
export const useRefreshAccountsMutation = () => {
  const queryClient = useQueryClient();

  return useMutation<PlaidAccountsResponse, Error>({
    mutationFn: PlaidService.refreshAccounts,
    onSuccess: (data) => {
      // Update the cache with fresh data
      queryClient.setQueryData([QUERY_KEYS.accounts], data);
      // Also refresh data info
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.accountsDataInfo] });
    },
    onError: () => {},
  });
};

// Get Plaid Items Query
export const useItemsQuery = (enabled: boolean = true) => {
  return useQuery<PlaidItemsResponse>({
    queryKey: [QUERY_KEYS.items],
    queryFn: PlaidService.getPlaidItems,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnMount: true,
    enabled: enabled, // Only run when explicitly enabled
  });
};

// Revoke Item Mutation
export const useRevokeItemMutation = () => {
  const queryClient = useQueryClient();

  return useMutation<{ message: string; success_count: number }, Error, string>({
    mutationFn: PlaidService.revokeItem,
    onSuccess: (data, itemId) => {
      console.log(`Successfully revoked item ${itemId}:`, data);
      // Invalidate both accounts and items queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.accounts] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.items] });
    },
    onError: (error, itemId) => {
      console.error(`Failed to revoke item ${itemId}:`, error);
    },
  });
};

// Revoke All Items Mutation
export const useRevokeAllItemsMutation = () => {
  const queryClient = useQueryClient();

  return useMutation<{ message: string; success_count: number }, Error>({
    mutationFn: PlaidService.revokeAllItems,
    onSuccess: (data) => {
      console.log('Successfully revoked all items:', data);
      // Invalidate both accounts and items queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.accounts] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.items] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.transactions] });
    },
    onError: (error) => {
      console.error('Failed to revoke all items:', error);
    },
  });
};

// Get Transactions Query
export const useTransactionsQuery = (days: number = 30, enabled: boolean = true) => {
  return useQuery<PlaidTransactionsResponse>({
    queryKey: [QUERY_KEYS.transactions, days],
    queryFn: () => PlaidService.getTransactions(days),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnMount: true,
    enabled: enabled,
  });
};

// Get Transactions by Account Query
export const useTransactionsByAccountQuery = (
  accountId: string,
  days: number = 30,
  enabled: boolean = true,
) => {
  return useQuery<PlaidTransactionsResponse>({
    queryKey: [QUERY_KEYS.transactions, 'account', accountId, days],
    queryFn: () => PlaidService.getTransactionsByAccount(accountId, days),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnMount: true,
    enabled: enabled && !!accountId,
  });
};

// Refresh Transactions Mutation
export const useRefreshTransactionsMutation = () => {
  const queryClient = useQueryClient();

  return useMutation<RefreshTransactionsResponse, Error, { itemId: string }>({
    mutationFn: ({ itemId }) => PlaidService.refreshTransactions(itemId),
    onSuccess: () => {
      // Invalidate transactions queries to refetch with fresh data
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.transactions] });
      // Also invalidate Firestore transactions queries
      queryClient.invalidateQueries({ queryKey: ['firestore-transactions'] });
    },
    onError: () => {},
  });
};

// Force Refresh Transactions Mutation
export const useForceRefreshTransactionsMutation = () => {
  return useMutation<ForceRefreshTransactionsResponse, Error, { itemId: string }>({
    mutationFn: ({ itemId }) => PlaidService.forceRefreshTransactions(itemId),
    onSuccess: () => {
      // Note: Don't invalidate queries immediately since this is async processing
      // The user will need to manually refresh later to see results
    },
    onError: () => {},
  });
};
