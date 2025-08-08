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
      console.error('Error creating link token:', error);
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
      console.error('Error exchanging public token:', error);
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
      console.error('Error fetching accounts:', error);
      throw new Error('Failed to fetch account data');
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
      console.error('Error fetching balances:', error);
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
      console.error('Error fetching Plaid items:', error);
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
      console.error('Error revoking item:', error);
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
      console.error('Error revoking all items:', error);
      throw new Error('Failed to revoke all bank connections');
    }
  },
};
