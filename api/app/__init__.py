"""
Personal Wealth Management API

A streamlined production-ready FastAPI application for personal finance management:
- Google OAuth 2.0 authentication
- Plaid financial data integration
- Real-time account balances and transactions
- Secure token management

Optimized for production with unused endpoints and code removed.
"""

__version__ = "2.0.0"
__author__ = "Personal Wealth Management Team"

from .main import app

__all__ = ["app"]
