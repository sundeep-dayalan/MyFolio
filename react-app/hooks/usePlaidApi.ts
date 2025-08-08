import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PlaidService, PlaidAccount, PlaidAccountsResponse, PlaidItemsResponse } from '../services/PlaidService';

// Query Keys
export const QUERY_KEYS = {
  accounts: 'accounts',
  linkToken: 'linkToken',
  items: 'items',
} as const;

// Get Accounts Query
export const useAccountsQuery = () => {
  return useQuery<PlaidAccountsResponse>({
    queryKey: [QUERY_KEYS.accounts],
    queryFn: PlaidService.getAccounts,
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchOnMount: true,
  });
};

// Create Link Token Mutation
export const useCreateLinkTokenMutation = () => {
  return useMutation<string, Error>({
    mutationFn: PlaidService.createLinkToken,
    onSuccess: (data) => {
      console.log('Link token created successfully:', data);
    },
    onError: (error) => {
      console.error('Failed to create link token:', error);
    },
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
    onSuccess: (data) => {
      console.log('Token exchange successful:', data);
      // Invalidate and refetch accounts after successful token exchange
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.accounts] });
    },
    onError: (error) => {
      console.error('Failed to exchange public token:', error);
    },
  });
};

// Refresh Accounts Mutation (for manual refresh)
export const useRefreshAccountsMutation = () => {
  const queryClient = useQueryClient();

  return useMutation<PlaidAccountsResponse, Error>({
    mutationFn: PlaidService.getAccounts,
    onSuccess: (data) => {
      console.log('Accounts refreshed successfully:', data);
      // Update the cache with fresh data
      queryClient.setQueryData([QUERY_KEYS.accounts], data);
    },
    onError: (error) => {
      console.error('Failed to refresh accounts:', error);
    },
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

  return useMutation<{ message: string }, Error, string>({
    mutationFn: PlaidService.revokeItem,
    onSuccess: (data, itemId) => {
      console.log('Item revoked successfully:', data);
      // Invalidate both accounts and items queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.accounts] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.items] });
    },
    onError: (error) => {
      console.error('Failed to revoke item:', error);
    },
  });
};

// Revoke All Items Mutation
export const useRevokeAllItemsMutation = () => {
  const queryClient = useQueryClient();

  return useMutation<{ message: string; revoked_count: number }, Error>({
    mutationFn: PlaidService.revokeAllItems,
    onSuccess: (data) => {
      console.log('All items revoked successfully:', data);
      // Invalidate both accounts and items queries
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.accounts] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.items] });
    },
    onError: (error) => {
      console.error('Failed to revoke all items:', error);
    },
  });
};
