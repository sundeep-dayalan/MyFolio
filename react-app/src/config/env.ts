/**
 * Environment Configuration
 * 
 * This file centralizes access to environment variables for the React application.
 * Vite exposes environment variables that start with VITE_ prefix.
 */

export const config = {
  // API Configuration
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  
  // App Environment
  environment: import.meta.env.VITE_APP_ENV || 'development',
  
  // Environment checks
  isDevelopment: import.meta.env.VITE_APP_ENV === 'development' || import.meta.env.DEV,
  isProduction: import.meta.env.VITE_APP_ENV === 'production' || import.meta.env.PROD,
  
  // Mode (from Vite)
  mode: import.meta.env.MODE,
} as const;

// Validation function to ensure required environment variables are set
export const validateConfig = () => {
  const requiredVars = ['VITE_API_BASE_URL'];
  const missing = requiredVars.filter(varName => !import.meta.env[varName]);
  
  if (missing.length > 0) {
    console.warn('Missing environment variables:', missing);
  }
  
  return missing.length === 0;
};

export default config;
