import { config } from '../config/env';

const API_BASE = config.apiBaseUrl;

const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem('authToken');

  if (!token) {
    throw new Error('Authentication token required. Please log in.');
  }

  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
};

export interface PaginatedTransactionsRequest {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  transactionType?: 'added' | 'modified' | 'removed' | 'all'; // New field
  filters?: {
    accountId?: string;
    itemId?: string;
    institutionName?: string;
    category?: string;
    dateFrom?: string;
    dateTo?: string;
    searchTerm?: string;
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
  transaction_id: string;
  account_id: string;
  amount: number;
  iso_currency_code: string;
  unofficial_currency_code: string | null;
  category: string[] | null;
  category_id: string;
  date: string;
  authorized_date: string | null;
  name: string;
  merchant_name: string | null;
  payment_channel: string;
  pending: boolean;
  account_owner: string | null;
  transaction_type: string;
  check_number?: string | null;
  merchant_entity_id?: string | null;
  location: {
    address: string | null;
    city: string | null;
    region: string | null;
    postal_code: string | null;
    country: string | null;
    store_number?: string | null;
  } | null;
  payment_meta: {
    reference_number: string | null;
    ppd_id: string | null;
    payee: string | null;
  } | null;
  // Additional fields added by our backend
  institution_name: string;
  institution_id: string;
  account_name: string;
  account_type: string;
  account_subtype: string;
  logo_url?: string;
  personal_finance_category?: {
    primary: string;
    confidence_level: string;
    detailed: string;
  };
  personal_finance_category_icon_url?: string;
}

class FirestoreServiceClass {
  private async makeRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        ...getAuthHeaders(),
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

    // Add transaction type parameter (default to 'added')
    queryParams.append('transactionType', request.transactionType || 'added');

    if (request.sortBy) {
      queryParams.append('sortBy', request.sortBy);
    }
    if (request.sortOrder) {
      queryParams.append('sortOrder', request.sortOrder);
    }
    if (request.filters?.accountId) {
      queryParams.append('accountId', request.filters.accountId);
    }
    if (request.filters?.itemId) {
      queryParams.append('itemId', request.filters.itemId);
    }

    if (request.filters?.institutionName) {
      queryParams.append('institutionName', request.filters.institutionName);
    }
    if (request.filters?.category) {
      queryParams.append('category', request.filters.category);
    }
    if (request.filters?.dateFrom) {
      queryParams.append('dateFrom', request.filters.dateFrom);
    }
    if (request.filters?.dateTo) {
      queryParams.append('dateTo', request.filters.dateTo);
    }
    if (request.filters?.searchTerm) {
      queryParams.append('searchTerm', request.filters.searchTerm);
    }

    return this.makeRequest<PaginatedTransactionsResponse>(
      `/firestore/transactions/paginated?${queryParams}`,
    );
  }
}

export const FirestoreService = new FirestoreServiceClass();
