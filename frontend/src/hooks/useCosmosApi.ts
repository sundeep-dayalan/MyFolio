import { useQuery } from '@tanstack/react-query';
import {
  CosmosDBService,
  type PaginatedTransactionsRequest,
  type PaginatedTransactionsResponse,
} from '@/services/FirestoreService';

export const COSMOSDB_QUERY_KEYS = {
  transactions: 'cosmosdb-transactions',
} as const;

export const useTransactionsPaginatedQuery = (request: PaginatedTransactionsRequest) => {
  return useQuery<PaginatedTransactionsResponse>({
    queryKey: [COSMOSDB_QUERY_KEYS.transactions, request],
    queryFn: () => CosmosDBService.getTransactionsPaginated(request),
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchOnMount: true,
    placeholderData: (previousData) => previousData, // Keep previous data while loading
  });
};
