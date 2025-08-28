import { config } from '../config/env';
import { MicrosoftAuthService } from './MicrosoftAuthService';
import { logger } from './LoggerService';

const API_BASE = config.apiBaseUrl;

export interface PlaidConfigurationCreate {
  plaid_client_id: string;
  plaid_secret: string;
  environment: 'sandbox' | 'development' | 'production';
}

export interface PlaidConfigurationValidate {
  plaid_client_id: string;
  plaid_secret: string;
  environment: 'sandbox' | 'development' | 'production';
}

export interface PlaidConfigurationResponse {
  id: string;
  plaid_client_id: string;
  environment: 'sandbox' | 'development' | 'production';
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface PlaidConfigurationStatus {
  is_configured: boolean;
}

export interface PlaidValidationResult {
  is_valid: boolean;
  message: string;
  environment: 'sandbox' | 'development' | 'production' | null;
}

const getAuthHeaders = async (): Promise<HeadersInit> => {
  const token = MicrosoftAuthService.getAuthToken();

  if (!token) {
    logger.warn('No authentication token found', 'PLAID_CONFIG');
    throw new Error('Authentication token required. Please log in.');
  }

  logger.info('Authentication token valid', 'PLAID_CONFIG');
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
};

const handleAuthError = async (response: Response) => {
  if (response.status === 401) {
    // Don't automatically redirect, just throw the error
    // Let the calling component decide whether to redirect
    throw new Error('Authentication required. Please log in.');
  }
};

export const PlaidConfigService = {
  async storeConfiguration(config: PlaidConfigurationCreate): Promise<PlaidConfigurationResponse> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/configuration`, {
        method: 'POST',
        headers,
        body: JSON.stringify(config),
      });

      await handleAuthError(response);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      logger.info('Plaid configuration stored successfully', 'PLAID_CONFIG');
      return data;
    } catch (error) {
      logger.error('Failed to store Plaid configuration:', 'PLAID_CONFIG', error);
      throw error;
    }
  },

  async getConfigurationStatus(): Promise<PlaidConfigurationStatus> {
    try {
      // Now requires authentication to get user-specific configuration status
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/configuration/status`, {
        method: 'GET',
        headers,
      });

      await handleAuthError(response);

      if (!response.ok) {
        // Return default unconfigured status on error
        logger.warn('Failed to get Plaid configuration status, returning default', 'PLAID_CONFIG');
        return { is_configured: false, environment: 'sandbox' };
      }

      const data = await response.json();
      return data;
    } catch (error) {
      logger.error('Failed to fetch Plaid configuration status:', 'PLAID_CONFIG', error);
      // Return default unconfigured status on error
      return { is_configured: false, environment: 'sandbox' };
    }
  },

  async getConfiguration(): Promise<PlaidConfigurationResponse> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/configuration`, {
        method: 'GET',
        headers,
      });

      await handleAuthError(response);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      logger.error('Failed to fetch Plaid configuration:', 'PLAID_CONFIG', error);
      throw error;
    }
  },

  async validateCredentials(
    credentials: PlaidConfigurationValidate,
  ): Promise<PlaidValidationResult> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/configuration/validate`, {
        method: 'POST',
        headers,
        body: JSON.stringify(credentials),
      });

      await handleAuthError(response);

      if (!response.ok) {
        const error = await response.json();
        return {
          is_valid: false,
          message: error.detail || `HTTP error! status: ${response.status}`,
          environment: null,
        };
      }

      const data = await response.json();
      return data;
    } catch (error) {
      logger.error('Failed to validate Plaid credentials:', 'PLAID_CONFIG', error);
      return {
        is_valid: false,
        message: `Validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        environment: null,
      };
    }
  },

  async deleteConfiguration(): Promise<{ message: string }> {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/plaid/configuration`, {
        method: 'DELETE',
        headers,
      });

      await handleAuthError(response);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      logger.info('Plaid configuration deleted successfully', 'PLAID_CONFIG');
      return data;
    } catch (error) {
      logger.error('Failed to delete Plaid configuration:', 'PLAID_CONFIG', error);
      throw error;
    }
  },
};
