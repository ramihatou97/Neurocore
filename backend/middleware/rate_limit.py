"""
Rate Limiting Middleware for FastAPI
Enforces rate limits on API requests using RateLimitService
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import time

from backend.services.rate_limit_service import RateLimitService, RateLimitStrategy
from backend.database import get_db
from backend.utils import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware

    Features:
    - Per-user and per-IP rate limiting
    - Configurable limits per endpoint
    - Automatic violation tracking
    - Rate limit headers in response
    - Bypass for whitelisted users
    """

    def __init__(self, app, strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW):
        super().__init__(app)
        self.strategy = strategy
        self.exempt_paths = [
            '/health',
            '/api/docs',
            '/api/redoc',
            '/api/openapi.json'
            # NOTE: Auth endpoints are NOT exempted - they need rate limiting for security
        ]

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Extract identifier information
        identifier, identifier_type = self._extract_identifier(request)
        endpoint = self._normalize_endpoint(request.url.path)

        # Check rate limit
        try:
            # Get database session
            db = next(get_db())
            rate_limit_service = RateLimitService(db)

            result = rate_limit_service.check_rate_limit(
                identifier=identifier,
                identifier_type=identifier_type,
                endpoint=endpoint,
                strategy=self.strategy
            )

            # Add rate limit headers to response
            response = await call_next(request) if result.allowed else None

            if result.allowed:
                # Record successful request
                rate_limit_service.record_request(identifier, identifier_type, endpoint)

                # Add rate limit headers
                response.headers['X-RateLimit-Limit'] = str(result.limit)
                response.headers['X-RateLimit-Remaining'] = str(result.remaining)
                response.headers['X-RateLimit-Reset'] = result.reset_at.isoformat()

                return response
            else:
                # Rate limit exceeded
                logger.warning(
                    f"Rate limit exceeded: {identifier_type}={identifier}, "
                    f"endpoint={endpoint}, retry_after={result.retry_after}s"
                )

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        'error': 'rate_limit_exceeded',
                        'message': 'Too many requests. Please try again later.',
                        'limit': result.limit,
                        'remaining': result.remaining,
                        'reset_at': result.reset_at.isoformat(),
                        'retry_after': result.retry_after
                    },
                    headers={
                        'X-RateLimit-Limit': str(result.limit),
                        'X-RateLimit-Remaining': str(result.remaining),
                        'X-RateLimit-Reset': result.reset_at.isoformat(),
                        'Retry-After': str(result.retry_after) if result.retry_after else '60'
                    }
                )

        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # Fail open - allow request if rate limiting fails
            return await call_next(request)

    def _extract_identifier(self, request: Request) -> tuple[str, str]:
        """
        Extract identifier from request

        Returns:
            Tuple of (identifier, identifier_type)
        """
        # Try to get user from token
        user = getattr(request.state, 'user', None)
        if user and hasattr(user, 'id'):
            return str(user.id), 'user'

        # Try API key from header
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return api_key, 'api_key'

        # Fall back to IP address
        # Check for forwarded IP first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.client.host if request.client else 'unknown'

        return ip, 'ip'

    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for rate limiting

        Groups similar endpoints together (e.g., /api/v1/chapters/123 -> /api/v1/chapters/:id)
        """
        # Remove trailing slash
        path = path.rstrip('/')

        # Replace UUIDs and numeric IDs with placeholders
        import re
        # UUID pattern
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/:id',
            path,
            flags=re.IGNORECASE
        )
        # Numeric IDs
        path = re.sub(r'/\d+', '/:id', path)

        return path


def create_rate_limit_middleware(strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW):
    """
    Factory function to create rate limit middleware

    Usage:
        app.add_middleware(RateLimitMiddleware, strategy=RateLimitStrategy.SLIDING_WINDOW)
    """
    return lambda app: RateLimitMiddleware(app, strategy=strategy)
