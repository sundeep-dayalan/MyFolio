import { config } from '../config/env';

const API_BASE = config.apiBaseUrl;

const getHeaders = (): HeadersInit => {
  return {
    'Content-Type': 'application/json',
  };
};

export interface PaginatedTransactionsRequest {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  filters?: {
    // Core Identity Filters
    accountId?: string;
    itemId?: string;
    
    // State & Type Filters  
    status?: 'posted' | 'pending' | 'removed';
    isPending?: boolean;
    paymentChannel?: 'online' | 'in store' | 'other';
    
    // Date & Financial Filters
    dateFrom?: string;
    dateTo?: string;
    minAmount?: number;
    maxAmount?: number;
    currency?: string;
    
    // Content & Category Filters
    searchTerm?: string;
    category?: string;
  };
}

export interface PaginatedTransactionsResponse {
  transactions: Transaction[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  transactionType: string; // New field to show which type was queried
}

export interface Transaction {
  // Core Identifiers
  id: string;
  userId: string;
  type: 'transaction';
  
  // Plaid-Specific Foreign Keys
  plaidTransactionId: string;
  plaidAccountId: string;
  plaidItemId: string;
  
  // System Metadata
  _meta: {
    createdAt: string;
    updatedAt: string;
    isRemoved: boolean;
    sourceSyncCursor: string;
  };
  
  // Primary Transaction Data
  description: string;
  amount: number;
  currency: string;
  date: string;
  authorizedDate?: string;
  isPending: boolean;
  
  // Enrichment & Categorization Data
  category: {
    primary: string;
    detailed: string;
    confidence?: string;
  };
  paymentChannel: string;
  location?: {
    address?: string;
    city?: string;
    region?: string;
    postal_code?: string;
    country?: string;
    lat?: number;
    lon?: number;
    store_number?: string;
  };
  counterparties: Array<{
    name: string;
    entityId?: string;
    type: string;
    website?: string;
    logoUrl?: string;
    confidenceLevel?: string;
  }>;
  
  // Reconciliation & Auxiliary Data
  pendingTransactionId?: string;
  originalDescription?: string;
}

class CosmosDBServiceClass {
  private async makeRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        ...getHeaders(),
        ...options?.headers,
      },
      credentials: 'include',
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json() as Promise<T>;
  }

  async getTransactionsPaginated(
    request: PaginatedTransactionsRequest,
  ): Promise<PaginatedTransactionsResponse> {
    const queryParams = new URLSearchParams({
      page: request.page.toString(),
      pageSize: request.pageSize.toString(),
    });

    // Pagination & Sorting Parameters
    if (request.sortBy) {
      queryParams.append('sortBy', request.sortBy);
    }
    if (request.sortOrder) {
      queryParams.append('sortOrder', request.sortOrder);
    }

    // Core Identity Filters
    if (request.filters?.accountId) {
      queryParams.append('accountId', request.filters.accountId);
    }
    if (request.filters?.itemId) {
      queryParams.append('itemId', request.filters.itemId);
    }

    // State & Type Filters
    if (request.filters?.status) {
      queryParams.append('status', request.filters.status);
    }
    if (request.filters?.isPending !== undefined) {
      queryParams.append('isPending', request.filters.isPending.toString());
    }
    if (request.filters?.paymentChannel) {
      queryParams.append('paymentChannel', request.filters.paymentChannel);
    }

    // Date & Financial Filters
    if (request.filters?.dateFrom) {
      queryParams.append('dateFrom', request.filters.dateFrom);
    }
    if (request.filters?.dateTo) {
      queryParams.append('dateTo', request.filters.dateTo);
    }
    if (request.filters?.minAmount !== undefined) {
      queryParams.append('minAmount', request.filters.minAmount.toString());
    }
    if (request.filters?.maxAmount !== undefined) {
      queryParams.append('maxAmount', request.filters.maxAmount.toString());
    }
    if (request.filters?.currency) {
      queryParams.append('currency', request.filters.currency);
    }

    // Content & Category Filters
    if (request.filters?.searchTerm) {
      queryParams.append('searchTerm', request.filters.searchTerm);
    }
    if (request.filters?.category) {
      queryParams.append('category', request.filters.category);
    }

    return this.makeRequest<PaginatedTransactionsResponse>(
      `/plaid/transactions/paginated?${queryParams}`,
    );
  }
}

export const CosmosDBService = new CosmosDBServiceClass();
