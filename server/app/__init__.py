"""
Sage API

A streamlined production-ready FastAPI application for financial management:
- Microsoft Entra ID OAuth 2.0 authentication
- Plaid financial data integration
- Real-time account balances and transactions
- Secure token management

Optimized for production with unused endpoints and code removed.
"""

import azure.functions as func
from .main import create_app

azure_app = create_app()


async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(azure_app).handle_async(req, context)


__version__ = "2.0.0"
__author__ = "Sage Team"

__all__ = ["azure_app", "main"]
