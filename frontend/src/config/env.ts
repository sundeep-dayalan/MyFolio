/**
 * Environment Configuration
 * 
 * This file centralizes access to environment variables for the React application.
 * Vite exposes environment variables that start with VITE_ prefix.
 */

export const config = {
  // API Configuration - Updated for Azure Functions
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:7071/api',
  
  // App Environment
  environment: import.meta.env.VITE_APP_ENV || 'development',
  
  // Microsoft OAuth Configuration
  microsoftClientId: import.meta.env.VITE_MICROSOFT_CLIENT_ID || '',
  
  // Environment checks
  isDevelopment: import.meta.env.VITE_APP_ENV === 'development' || import.meta.env.DEV,
  isProduction: import.meta.env.VITE_APP_ENV === 'production' || import.meta.env.PROD,
  
  // Mode (from Vite)
  mode: import.meta.env.MODE,
} as const;

// Validation function to ensure required environment variables are set
export const validateConfig = () => {
  const requiredVars = ['VITE_API_BASE_URL'];
  const optionalVars = ['VITE_MICROSOFT_CLIENT_ID'];
  
  const missing = requiredVars.filter(varName => !import.meta.env[varName]);
  const missingOptional = optionalVars.filter(varName => !import.meta.env[varName]);
  
  if (missing.length > 0) {
    console.error('Missing required environment variables:', missing);
  }
  
  if (missingOptional.length > 0) {
    console.warn('Missing optional environment variables (OAuth may not work):', missingOptional);
  }
  
  return missing.length === 0;
};

export default config;
