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

export interface PlaidAccountsResponse {
  accounts: PlaidAccount[];
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

const getAuthHeaders = async (): Promise<HeadersInit> => {
  const token = AzureAuthService.getAuthToken();

  if (!token) {
    throw new Error('Authentication token required. Please log in.');
  }

  // Refresh token if needed
  await AzureAuthService.refreshTokenIfNeeded();

  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
};

export const AzurePlaidService = {
  async createLinkToken(products: string[] = ['transactions', 'accounts']): Promise<string> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/create_link_token`, {
        method: 'POST',
        headers,
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

  async exchangePublicToken(publicToken: string): Promise<{ item_id: string; accounts: PlaidAccount[] }> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/exchange_public_token`, {
        method: 'POST',
        headers,
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

  async getAccounts(): Promise<PlaidAccountsResponse> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/accounts`, {
        method: 'GET',
        headers,
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
      console.error('Failed to fetch accounts:', error);
      throw new Error('Failed to fetch accounts');
    }
  },

  async getTransactions(
    startDate?: string,
    endDate?: string,
    count: number = 500,
    offset: number = 0
  ): Promise<PlaidTransactionsResponse> {
    try {
      const headers = await getAuthHeaders();
      const params = new URLSearchParams({
        count: count.toString(),
        offset: offset.toString(),
      });

      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await fetch(`${API_BASE}/plaid/transactions?${params.toString()}`, {
        method: 'GET',
        headers,
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
    count: number = 500
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
    return accountsResponse.accounts;
  },

  // Health check method
  async checkConnection(): Promise<boolean> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        headers,
      });
      return response.ok;
    } catch (error) {
      console.error('Connection check failed:', error);
      return false;
    }
  },
};