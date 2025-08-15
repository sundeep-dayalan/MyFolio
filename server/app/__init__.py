"""
Sage API

A streamlined production-ready FastAPI application for financial management:
- Google OAuth 2.0 authentication
- Plaid financial data integration
- Real-time account balances and transactions
- Secure token management

Optimized for production with unused endpoints and code removed.
"""

__version__ = "2.0.0"
__author__ = "Sage Team"

from .main import app

__all__ = ["app"]
