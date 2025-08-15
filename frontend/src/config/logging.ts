/**
 * Production-ready logging configuration
 * Automatically configures logging based on environment
 */

import { logger, LogLevel } from '../services/LoggerService';

// Configure logging based on environment
export function initializeLogging(): void {
  const environment = import.meta.env.VITE_APP_ENV || 'development';
  
  // Set log level based on environment
  switch (environment) {
    case 'production':
      // In production, only log warnings and errors
      logger.info('Initializing production logging', 'CONFIG');
      break;
    case 'staging':
      // In staging, log info and above
      logger.info('Initializing staging logging', 'CONFIG');
      break;
    case 'development':
    default:
      // In development, log everything
      logger.debug('Initializing development logging', 'CONFIG');
      break;
  }
  
  // Log environment information
  logger.info(`Application started in ${environment} mode`, 'CONFIG', {
    environment,
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
    version: import.meta.env.VITE_APP_VERSION || 'unknown',
  });
}

// Export for use in main.tsx
export { logger } from '../services/LoggerService';