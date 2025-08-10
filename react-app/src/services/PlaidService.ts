import { config } from '../config/env';

const API_BASE = config.apiBaseUrl;

export interface PlaidItem {
  item_id: string;
  institution_name: string;
  status: string;
  created_at: string;
  last_used_at: string | null;
}

export interface PlaidItemsResponse {
  items: PlaidItem[];
}

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
  persistent_account_id: string;
  subtype: string;
  type: string;
  institution_name?: string;
  institution_id?: string;
}

export interface PlaidAccountsResponse {
  accounts: PlaidAccount[];
  total_balance: number;
  account_count: number;
  last_updated?: string;
  from_stored?: boolean;
  refreshed?: boolean;
  message?: string;
}

export interface PlaidDataInfo {
  has_data: boolean;
  last_updated?: string;
  age_hours?: number;
  account_count?: number;
  total_balance?: number;
  is_expired?: boolean;
  error?: string;
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
}

export interface PlaidTransactionsResponse {
  transactions: PlaidTransaction[];
  transaction_count: number;
  account_count: number;
  items: {
    item_id: string;
    institution_name: string;
    transaction_count: number;
  }[];
  date_range: {
    start_date: string;
    end_date: string;
    days: number;
  };
}

export interface PlaidTransactionsByItemResponse {
  transactions: PlaidTransaction[];
  transaction_count: number;
  institution_name: string;
  item_id: string;
  date_range: {
    start_date: string;
    end_date: string;
    days: number;
  };
}

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

export const PlaidService = {
  async createLinkToken(): Promise<string> {
    try {
      const response = await fetch(`${API_BASE}/plaid/create_link_token`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as { link_token: string };
      return data.link_token;
    } catch (error) {
      throw new Error('Failed to create link token');
    }
  },

  async exchangePublicToken(publicToken: string): Promise<{ success: boolean; item_id: string }> {
    try {
      const response = await fetch(`${API_BASE}/plaid/exchange_public_token`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ public_token: publicToken }),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as { success: boolean; item_id: string };
      return data;
    } catch (error) {
      throw new Error('Failed to exchange public token');
    }
  },

  async getAccounts(): Promise<PlaidAccountsResponse> {
    try {
      const response = await fetch(`${API_BASE}/plaid/accounts`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as PlaidAccountsResponse;
      return data;
    } catch (error) {
      throw new Error('Failed to fetch stored account data');
    }
  },

  async refreshAccounts(): Promise<PlaidAccountsResponse> {
    try {
      const response = await fetch(`${API_BASE}/plaid/accounts/refresh`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as PlaidAccountsResponse;
      return data;
    } catch (error) {
      throw new Error('Failed to refresh account data from Plaid API');
    }
  },

  async getAccountsDataInfo(): Promise<PlaidDataInfo> {
    try {
      const response = await fetch(`${API_BASE}/plaid/accounts/data-info`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as PlaidDataInfo;
      return data;
    } catch (error) {
      throw new Error('Failed to fetch data information');
    }
  },

  // Legacy method for backward compatibility
  async getBalance(accessToken: string): Promise<PlaidAccount[]> {
    try {
      const response = await fetch(
        `${API_BASE}/plaid/balance?access_token=${encodeURIComponent(accessToken)}`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        },
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as { accounts: PlaidAccount[] };
      return data.accounts;
    } catch (error) {
      throw new Error('Failed to fetch balances');
    }
  },

  async getPlaidItems(): Promise<PlaidItemsResponse> {
    try {
      const response = await fetch(`${API_BASE}/plaid/items`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as PlaidItemsResponse;
      return data;
    } catch (error) {
      throw new Error('Failed to fetch Plaid items');
    }
  },

  async revokeItem(itemId: string): Promise<{ message: string }> {
    try {
      const response = await fetch(`${API_BASE}/plaid/items/${itemId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as { message: string };
      return data;
    } catch (error) {
      throw new Error('Failed to revoke bank connection');
    }
  },

  async revokeAllItems(): Promise<{ message: string; revoked_count: number }> {
    try {
      const response = await fetch(`${API_BASE}/plaid/tokens/revoke-all`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as { message: string; revoked_count: number };
      return data;
    } catch (error) {
      throw new Error('Failed to revoke all bank connections');
    }
  },

  async getTransactions(days: number = 30): Promise<PlaidTransactionsResponse> {
    try {
      const response = await fetch(`${API_BASE}/plaid/transactions?days=${days}`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as PlaidTransactionsResponse;
      return data;
    } catch (error) {
      throw new Error('Failed to fetch transactions');
    }
  },

  async getTransactionsByAccount(
    accountId: string,
    days: number = 30,
  ): Promise<PlaidTransactionsResponse> {
    try {
      const response = await fetch(
        `${API_BASE}/plaid/transactions/account/${accountId}?days=${days}`,
        {
          method: 'GET',
          headers: getAuthHeaders(),
        },
      );

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as PlaidTransactionsResponse;
      return data;
    } catch (error) {
      throw new Error('Failed to fetch account transactions');
    }
  },

  async refreshTransactions(
    itemId: string,
    days: number = 30,
  ): Promise<PlaidTransactionsByItemResponse> {
    try {
      const response = await fetch(
        `${API_BASE}/plaid/transactions/refresh/${itemId}?days=${days}`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
        },
      );

      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        throw new Error('Authentication required. Redirecting to login.');
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as PlaidTransactionsByItemResponse;
      return data;
    } catch (error) {
      throw new Error('Failed to refresh transactions');
    }
  },
};
