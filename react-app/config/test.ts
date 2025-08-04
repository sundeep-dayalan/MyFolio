/**
 * Environment Configuration Test
 * 
 * This file can be used to test that environment variables are being loaded correctly.
 * Run this in the browser console or import it temporarily to verify configuration.
 */

import config, { validateConfig } from './env';

export const testEnvironmentConfig = () => {
  console.group('🔧 Environment Configuration Test');
  
  console.log('Current Configuration:', {
    apiBaseUrl: config.apiBaseUrl,
    environment: config.environment,
    mode: config.mode,
    isDevelopment: config.isDevelopment,
    isProduction: config.isProduction,
  });
  
  console.log('Raw Environment Variables:', {
    VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
    VITE_APP_ENV: import.meta.env.VITE_APP_ENV,
    MODE: import.meta.env.MODE,
    DEV: import.meta.env.DEV,
    PROD: import.meta.env.PROD,
  });
  
  const isValid = validateConfig();
  console.log('Configuration Valid:', isValid);
  
  if (!isValid) {
    console.warn('❌ Configuration validation failed!');
  } else {
    console.log('✅ Configuration validation passed!');
  }
  
  console.groupEnd();
  
  return {
    config,
    isValid,
    environment: config.environment,
    apiBaseUrl: config.apiBaseUrl,
  };
};

// Auto-run in development
if (config.isDevelopment) {
  testEnvironmentConfig();
}

export default testEnvironmentConfig;
