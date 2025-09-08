import { config } from '../config/env';
import { AzureAuthService } from './AzureAuthService';

const API_BASE = config.apiBaseUrl;

export interface PlaidAccount {
  account_id: string;
  balances: {
    available: number | null;
    current: number | null;
    iso_currency_code: string;
    limit: number | null;
    unofficial_currency_code: string | null;
  };
  mask: string;
  name: string;
  official_name: string | null;
  subtype: string;
  type: string;
}

export interface InstitutionDetail {
  name: string;
  logo?: string;
  status: string;
  total_balance: number;
  account_count: number;
  accounts: PlaidAccount[];
  last_account_sync?: {
    last_sync?: string;
    status?: string;
  };
}

export interface PlaidAccountsResponse {
  institutions: InstitutionDetail[];
  accounts_count: number;
  banks_count: number;
  // Legacy fields for backward compatibility during transition
  accounts?: PlaidAccount[];
}

export interface PlaidTransaction {
  transaction_id: string;
  account_id: string;
  amount: number;
  iso_currency_code: string;
  unofficial_currency_code: string | null;
  category: string[];
  category_id: string;
  date: string;
  authorized_date: string | null;
  name: string;
  merchant_name: string | null;
  payment_channel: string;
  pending: boolean;
  account_owner: string | null;
  transaction_type: string;
  location: {
    address: string | null;
    city: string | null;
    region: string | null;
    postal_code: string | null;
    country: string | null;
  } | null;
}

export interface PlaidTransactionsResponse {
  transactions: PlaidTransaction[];
}

const getHeaders = (): HeadersInit => {
  return {
    'Content-Type': 'application/json',
  };
};

export const AzurePlaidService = {
  async createLinkToken(products: string[] = ['transactions', 'accounts']): Promise<string> {
    try {
      const response = await fetch(`${API_BASE}/plaid/create_link_token`, {
        method: 'POST',
        headers: getHeaders(),
        credentials: 'include',
        body: JSON.stringify({ products }),
      });

      if (response.status === 401) {
        AzureAuthService.clearAuthData();
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.link_token;
    } catch (error) {
      console.error('Failed to create link token:', error);
      throw new Error('Failed to create link token');
    }
  },

  async exchangePublicToken(
    publicToken: string,
  ): Promise<{ item_id: string; accounts: PlaidAccount[] }> {
    try {
      const headers = getHeaders();
      const response = await fetch(`${API_BASE}/plaid/exchange_public_token`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({ public_token: publicToken }),
      });

      if (response.status === 401) {
        AzureAuthService.clearAuthData();
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Failed to exchange public token:', error);
      throw new Error('Failed to exchange public token');
    }
  },

  async getTransactions(
    startDate?: string,
    endDate?: string,
    count: number = 500,
    offset: number = 0,
  ): Promise<PlaidTransactionsResponse> {
    try {
      const headers = getHeaders();
      const params = new URLSearchParams({
        count: count.toString(),
        offset: offset.toString(),
      });

      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await fetch(`${API_BASE}/plaid/transactions?${params.toString()}`, {
        method: 'GET',
        headers,
        credentials: 'include',
      });

      if (response.status === 401) {
        AzureAuthService.clearAuthData();
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
      throw new Error('Failed to fetch transactions');
    }
  },

  async getTransactionsByDateRange(
    startDate: string,
    endDate: string,
    count: number = 500,
  ): Promise<PlaidTransactionsResponse> {
    return this.getTransactions(startDate, endDate, count, 0);
  },

  async getRecentTransactions(days: number = 30): Promise<PlaidTransactionsResponse> {
    const endDate = new Date().toISOString().split('T')[0];
    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    return this.getTransactions(startDate, endDate);
  },

  // Legacy method for backward compatibility with existing PlaidService
  async getBalance(): Promise<PlaidAccount[]> {
    const accountsResponse = await this.getAccounts();
    return accountsResponse.accounts || [];
  },

  async getTransactionsPaginated(
    page: number = 1,
    pageSize: number = 20,
    filters?: {
      accountId?: string;
      itemId?: string;
      status?: 'posted' | 'pending' | 'removed';
      isPending?: boolean;
      paymentChannel?: 'online' | 'in store' | 'other';
      dateFrom?: string;
      dateTo?: string;
      minAmount?: number;
      maxAmount?: number;
      currency?: string;
      searchTerm?: string;
      category?: string;
    },
    sortBy?: string,
    sortOrder?: 'asc' | 'desc',
  ): Promise<any> {
    try {
      const queryParams = new URLSearchParams({
        page: page.toString(),
        pageSize: pageSize.toString(),
      });

      if (sortBy) queryParams.append('sortBy', sortBy);
      if (sortOrder) queryParams.append('sortOrder', sortOrder);
      if (filters?.accountId) queryParams.append('accountId', filters.accountId);
      if (filters?.itemId) queryParams.append('itemId', filters.itemId);
      if (filters?.status) queryParams.append('status', filters.status);
      if (filters?.isPending !== undefined)
        queryParams.append('isPending', filters.isPending.toString());
      if (filters?.paymentChannel) queryParams.append('paymentChannel', filters.paymentChannel);
      if (filters?.dateFrom) queryParams.append('dateFrom', filters.dateFrom);
      if (filters?.dateTo) queryParams.append('dateTo', filters.dateTo);
      if (filters?.minAmount !== undefined)
        queryParams.append('minAmount', filters.minAmount.toString());
      if (filters?.maxAmount !== undefined)
        queryParams.append('maxAmount', filters.maxAmount.toString());
      if (filters?.currency) queryParams.append('currency', filters.currency);
      if (filters?.searchTerm) queryParams.append('searchTerm', filters.searchTerm);
      if (filters?.category) queryParams.append('category', filters.category);

      const headers = getHeaders();
      const response = await fetch(
        `${API_BASE}/plaid/transactions/paginated?${queryParams.toString()}`,
        {
          method: 'GET',
          headers,
          credentials: 'include',
        },
      );

      if (response.status === 401) {
        AzureAuthService.clearAuthData();
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Failed to fetch paginated transactions:', error);
      throw new Error('Failed to fetch paginated transactions');
    }
  },

  // Health check method
  async checkConnection(): Promise<boolean> {
    try {
      const headers = getHeaders();
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        headers,
        credentials: 'include',
      });
      return response.ok;
    } catch (error) {
      console.error('Connection check failed:', error);
      return false;
    }
  },
};
