import { useQuery } from '@tanstack/react-query';
import {
  FirestoreService,
  type PaginatedTransactionsRequest,
  type PaginatedTransactionsResponse,
} from '@/services/FirestoreService';

// Query Keys
export const FIRESTORE_QUERY_KEYS = {
  transactions: 'firestore-transactions',
} as const;

export const useTransactionsPaginatedQuery = (request: PaginatedTransactionsRequest) => {
  console.log('useTransactionsPaginatedQuery: request', request);

  return useQuery<PaginatedTransactionsResponse>({
    queryKey: [FIRESTORE_QUERY_KEYS.transactions, request],
    queryFn: () => {
      console.log('useTransactionsPaginatedQuery: making API call with', request);
      return FirestoreService.getTransactionsPaginated(request);
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchOnMount: true,
    placeholderData: (previousData) => previousData, // Keep previous data while loading
  });
};
