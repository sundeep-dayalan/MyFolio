"""
Azure Functions wrapper for FastAPI application.
This file bridges Azure Functions runtime with the FastAPI application.
"""

import azure.functions as func
from azure.functions import AsgiMiddleware

from app.main import app

# Create the Azure Functions app
azure_app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Route all HTTP requests through FastAPI
@azure_app.function_name(name="HttpTrigger")
@azure_app.route(route="{*route}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Route all HTTP requests to FastAPI application."""
    return await AsgiMiddleware(app).handle_async(req)