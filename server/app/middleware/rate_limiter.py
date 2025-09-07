"""
Rate limiting middleware to prevent abuse and improve security.
"""

import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from threading import Lock
import asyncio

from ..utils.logger import get_logger

logger = get_logger(__name__)


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    For production, consider using Redis for distributed rate limiting.
    """

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()

    def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed based on rate limit.

        Args:
            key: Unique identifier for the client (IP, user ID, etc.)
            max_requests: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        window_start = current_time - window_seconds

        with self.lock:
            # Remove old requests outside the window
            while self.requests[key] and self.requests[key][0] < window_start:
                self.requests[key].popleft()

            # Check if we're within the limit
            if len(self.requests[key]) < max_requests:
                self.requests[key].append(current_time)
                return True, 0
            else:
                # Calculate retry after time
                oldest_request = self.requests[key][0]
                retry_after = int(oldest_request + window_seconds - current_time) + 1
                return False, max(retry_after, 1)


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def get_client_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Priority: user_id > api_key > ip_address
    """
    # Try to get user ID from session or token
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    # Try to get from session
    session = getattr(request, "session", {})
    if session and "user_id" in session:
        return f"user:{session['user_id']}"

    # Try to get API key from headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key[:10]}..."  # Only use first 10 chars for privacy

    # Fall back to IP address
    # Handle proxy headers for real IP
    real_ip = (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
        if request.client
        else "unknown"
    )

    return f"ip:{real_ip}"


class RateLimitMiddleware:
    """
    Rate limiting middleware with different limits for different endpoints.
    """

    def __init__(self):
        # Rate limits: (max_requests, window_seconds)
        self.limits = {
            # Authentication endpoints - more restrictive
            "/auth/": (5, 60),  # 5 requests per minute
            "/auth/oauth/": (3, 60),  # 3 OAuth attempts per minute
            # Plaid endpoints - moderate limits
            "/plaid/create_link_token": (100, 60),  # 10 link tokens per minute
            "/plaid/exchange_public_token": (5, 60),  # 5 exchanges per minute
            "/plaid/account": (100, 60),  # 30 account fetches per minute
            "/plaid/transactions": (100, 60),  # 20 transaction fetches per minute
            # General API endpoints
            "/api/v1/": (100, 60),  # 100 requests per minute for general API
            # Health check - unlimited
            "/health": (1000, 60),  # Effectively unlimited
        }

        # Global rate limit as fallback
        self.global_limit = (200, 60)  # 200 requests per minute

    def get_rate_limit_for_path(self, path: str) -> Tuple[int, int]:
        """Get rate limit for specific path."""
        for pattern, limit in self.limits.items():
            if path.startswith(pattern):
                return limit
        return self.global_limit

    async def __call__(self, request: Request, call_next):
        """Process rate limiting for request."""

        # Skip rate limiting for health checks in production
        if request.url.path == "/health":
            return await call_next(request)

        try:
            client_id = get_client_identifier(request)
            max_requests, window_seconds = self.get_rate_limit_for_path(
                request.url.path
            )

            is_allowed, retry_after = rate_limiter.is_allowed(
                client_id, max_requests, window_seconds
            )

            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {client_id} on {request.url.path}. "
                    f"Limit: {max_requests}/{window_seconds}s, Retry after: {retry_after}s"
                )

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded. Please try again later.",
                        "retry_after": retry_after,
                        "limit": max_requests,
                        "window": window_seconds,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Window": str(window_seconds),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            # Add rate limit headers to response
            response = await call_next(request)

            # Calculate remaining requests
            current_count = len(rate_limiter.requests[client_id])
            remaining = max(0, max_requests - current_count)

            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Window"] = str(window_seconds)

            return response

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # If rate limiter fails, allow the request to continue
            return await call_next(request)
