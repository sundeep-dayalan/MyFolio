/**
 * Professional logging service for frontend application
 * Replaces console.log statements with structured logging
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: string;
  data?: any;
  userId?: string;
}

class LoggerService {
  private logLevel: LogLevel;
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = import.meta.env.DEV;
    this.logLevel = this.isDevelopment ? LogLevel.DEBUG : LogLevel.INFO;
  }

  private formatLogEntry(level: LogLevel, message: string, context?: string, data?: any): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      context,
      data,
      userId: this.getCurrentUserId(),
    };
  }

  private getCurrentUserId(): string | undefined {
    try {
      const user = localStorage.getItem('user');
      return user ? JSON.parse(user).id : undefined;
    } catch {
      return undefined;
    }
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.logLevel;
  }

  private writeLog(logEntry: LogEntry): void {
    if (!this.shouldLog(logEntry.level)) return;

    const logMessage = `[${logEntry.timestamp}] ${LogLevel[logEntry.level]} ${logEntry.context ? `[${logEntry.context}]` : ''}: ${logEntry.message}`;

    switch (logEntry.level) {
      case LogLevel.DEBUG:
        if (this.isDevelopment) {
          console.debug(logMessage, logEntry.data || '');
        }
        break;
      case LogLevel.INFO:
        if (this.isDevelopment) {
          console.info(logMessage, logEntry.data || '');
        }
        break;
      case LogLevel.WARN:
        console.warn(logMessage, logEntry.data || '');
        break;
      case LogLevel.ERROR:
        console.error(logMessage, logEntry.data || '');
        // In production, you might want to send errors to a logging service
        if (!this.isDevelopment) {
          this.sendToLoggingService(logEntry);
        }
        break;
    }
  }

  private sendToLoggingService(logEntry: LogEntry): void {
    // In production, send errors to external logging service
    // This is a placeholder for services like Sentry, LogRocket, etc.
    try {
      // Example: window.gtag?.('event', 'exception', { description: logEntry.message });
    } catch {
      // Silently fail if logging service is unavailable
    }
  }

  debug(message: string, context?: string, data?: any): void {
    const logEntry = this.formatLogEntry(LogLevel.DEBUG, message, context, data);
    this.writeLog(logEntry);
  }

  info(message: string, context?: string, data?: any): void {
    const logEntry = this.formatLogEntry(LogLevel.INFO, message, context, data);
    this.writeLog(logEntry);
  }

  warn(message: string, context?: string, data?: any): void {
    const logEntry = this.formatLogEntry(LogLevel.WARN, message, context, data);
    this.writeLog(logEntry);
  }

  error(message: string, context?: string, data?: any): void {
    const logEntry = this.formatLogEntry(LogLevel.ERROR, message, context, data);
    this.writeLog(logEntry);
  }

  // Convenience methods for common use cases
  authEvent(message: string, data?: any): void {
    this.info(message, 'AUTH', data);
  }

  plaidEvent(message: string, data?: any): void {
    this.info(message, 'PLAID', data);
  }

  apiError(message: string, error: any): void {
    this.error(message, 'API', { error: error?.message || error });
  }

  routeChange(from: string, to: string): void {
    this.debug(`Route change: ${from} → ${to}`, 'ROUTER');
  }
}

// Export singleton instance
export const logger = new LoggerService();
export default logger;