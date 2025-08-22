"""
Azure Functions backend for Sage Financial Management App
Replaces FastAPI with Azure Functions HTTP triggers
"""

import logging
import json
import azure.functions as func
from azure.functions import HttpRequest, HttpResponse
from typing import Dict, Any, Optional
import asyncio
import os
import sys

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import initialize_database, get_document_service
from app.services.auth_service import get_auth_service
from app.services.plaid_service import get_plaid_service
from app.utils.security import get_security_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Global initialization flag
_initialized = False


async def initialize_services():
    """Initialize all services"""
    global _initialized
    if not _initialized:
        try:
            await initialize_database()
            logger.info("Services initialized successfully")
            _initialized = True
        except Exception as e:
            logger.error(f"Service initialization failed: {str(e)}")
            raise


def create_error_response(message: str, status_code: int = 400) -> HttpResponse:
    """Create standardized error response"""
    return HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        headers={"Content-Type": "application/json"}
    )


def create_success_response(data: Any, status_code: int = 200) -> HttpResponse:
    """Create standardized success response"""
    return HttpResponse(
        json.dumps(data),
        status_code=status_code,
        headers={"Content-Type": "application/json"}
    )


async def get_current_user(req: HttpRequest) -> Optional[Dict[str, Any]]:
    """Extract and validate user from JWT token"""
    try:
        auth_header = req.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        auth_service = get_auth_service()
        payload = auth_service.verify_jwt_token(token)
        
        user = await auth_service.get_user_by_id(payload['user_id'])
        return user
        
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None


# Health Check Endpoint
@app.route(route="health", methods=["GET"])
async def health_check(req: HttpRequest) -> HttpResponse:
    """Health check endpoint"""
    try:
        await initialize_services()
        
        # Check database connectivity
        document_service = get_document_service()
        db_healthy = document_service.cosmos_client.health_check()
        
        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": func.datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        status_code = 200 if db_healthy else 503
        return create_success_response(health_status, status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_error_response("Health check failed", 503)


# Authentication Endpoints
@app.route(route="auth/google/login", methods=["POST"])
async def google_oauth_login(req: HttpRequest) -> HttpResponse:
    """Google OAuth login endpoint"""
    try:
        await initialize_services()
        
        body = req.get_json()
        if not body or 'code' not in body:
            return create_error_response("Authorization code is required")
        
        auth_service = get_auth_service()
        redirect_uri = body.get('redirect_uri', '')
        
        result = await auth_service.authenticate_google_oauth(
            authorization_code=body['code'],
            redirect_uri=redirect_uri
        )
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Google OAuth login failed: {str(e)}")
        return create_error_response(f"Authentication failed: {str(e)}", 401)


@app.route(route="auth/refresh", methods=["POST"])
async def refresh_token(req: HttpRequest) -> HttpResponse:
    """Refresh JWT token endpoint"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Invalid or expired token", 401)
        
        auth_service = get_auth_service()
        new_token = auth_service.create_jwt_token(user)
        
        return create_success_response({
            "access_token": new_token,
            "token_type": "bearer"
        })
        
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        return create_error_response("Token refresh failed", 401)


# User Management Endpoints
@app.route(route="users/me", methods=["GET"])
async def get_current_user_profile(req: HttpRequest) -> HttpResponse:
    """Get current user profile"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Authentication required", 401)
        
        # Remove sensitive information
        user_profile = {
            key: value for key, value in user.items()
            if key not in ['_rid', '_self', '_etag', '_attachments', '_ts']
        }
        
        return create_success_response(user_profile)
        
    except Exception as e:
        logger.error(f"Get user profile failed: {str(e)}")
        return create_error_response("Failed to get user profile", 500)


@app.route(route="users/me", methods=["PUT"])
async def update_user_profile(req: HttpRequest) -> HttpResponse:
    """Update current user profile"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Authentication required", 401)
        
        body = req.get_json()
        if not body:
            return create_error_response("Request body is required")
        
        # Update allowed fields
        allowed_fields = ['name']
        for field in allowed_fields:
            if field in body:
                user[field] = body[field]
        
        user['updated_at'] = func.datetime.utcnow().isoformat()
        
        document_service = get_document_service()
        updated_user = await document_service.update_document('users', user)
        
        return create_success_response(updated_user)
        
    except Exception as e:
        logger.error(f"Update user profile failed: {str(e)}")
        return create_error_response("Failed to update user profile", 500)


@app.route(route="users/me", methods=["DELETE"])
async def delete_user_account(req: HttpRequest) -> HttpResponse:
    """Delete current user account"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Authentication required", 401)
        
        auth_service = get_auth_service()
        await auth_service.delete_user(user['userId'])
        
        return create_success_response({"message": "Account deleted successfully"})
        
    except Exception as e:
        logger.error(f"Delete user account failed: {str(e)}")
        return create_error_response("Failed to delete account", 500)


# Plaid Integration Endpoints
@app.route(route="plaid/create_link_token", methods=["POST"])
async def create_plaid_link_token(req: HttpRequest) -> HttpResponse:
    """Create Plaid Link token"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Authentication required", 401)
        
        body = req.get_json() or {}
        products = body.get('products', ['transactions', 'accounts'])
        
        plaid_service = get_plaid_service()
        link_token = await plaid_service.create_link_token(
            user_id=user['userId'],
            products=products
        )
        
        return create_success_response({"link_token": link_token})
        
    except Exception as e:
        logger.error(f"Create Plaid link token failed: {str(e)}")
        return create_error_response("Failed to create link token", 500)


@app.route(route="plaid/exchange_public_token", methods=["POST"])
async def exchange_plaid_public_token(req: HttpRequest) -> HttpResponse:
    """Exchange Plaid public token for access token"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Authentication required", 401)
        
        body = req.get_json()
        if not body or 'public_token' not in body:
            return create_error_response("Public token is required")
        
        plaid_service = get_plaid_service()
        result = await plaid_service.exchange_public_token(
            public_token=body['public_token'],
            user_id=user['userId']
        )
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Exchange Plaid public token failed: {str(e)}")
        return create_error_response("Failed to exchange public token", 500)


@app.route(route="plaid/accounts", methods=["GET"])
async def get_plaid_accounts(req: HttpRequest) -> HttpResponse:
    """Get Plaid accounts for user"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Authentication required", 401)
        
        plaid_service = get_plaid_service()
        accounts = await plaid_service.get_accounts(user['userId'])
        
        return create_success_response({"accounts": accounts})
        
    except Exception as e:
        logger.error(f"Get Plaid accounts failed: {str(e)}")
        return create_error_response("Failed to get accounts", 500)


@app.route(route="plaid/transactions", methods=["GET"])
async def get_plaid_transactions(req: HttpRequest) -> HttpResponse:
    """Get Plaid transactions for user"""
    try:
        await initialize_services()
        
        user = await get_current_user(req)
        if not user:
            return create_error_response("Authentication required", 401)
        
        # Parse query parameters
        start_date = req.params.get('start_date')
        end_date = req.params.get('end_date')
        count = int(req.params.get('count', 500))
        offset = int(req.params.get('offset', 0))
        
        plaid_service = get_plaid_service()
        transactions = await plaid_service.get_transactions(
            user_id=user['userId'],
            start_date=start_date,
            end_date=end_date,
            count=count,
            offset=offset
        )
        
        return create_success_response({"transactions": transactions})
        
    except Exception as e:
        logger.error(f"Get Plaid transactions failed: {str(e)}")
        return create_error_response("Failed to get transactions", 500)


# CORS preflight handler
@app.route(route="{*route}", methods=["OPTIONS"])
async def handle_cors_preflight(req: HttpRequest) -> HttpResponse:
    """Handle CORS preflight requests"""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400"
    }
    return HttpResponse("", status_code=200, headers=headers)


# Add CORS headers to all responses
@app.middleware
async def add_cors_headers(req: HttpRequest, context) -> HttpResponse:
    """Add CORS headers to all responses"""
    response = await context.next(req)
    response.headers.update({
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    })
    return response