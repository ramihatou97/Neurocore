"""
Security Headers Middleware for Phase 16: Production Readiness
Adds comprehensive security headers to all HTTP responses
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Dict, Optional

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware

    Adds comprehensive security headers to all HTTP responses to protect
    against common web vulnerabilities:
    - XSS attacks
    - Clickjacking
    - MIME sniffing
    - Content injection
    - Data leakage

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (or SAMEORIGIN)
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    - X-Permitted-Cross-Domain-Policies: none
    """

    def __init__(
        self,
        app: ASGIApp,
        csp_directives: Optional[Dict[str, str]] = None,
        x_frame_options: str = "SAMEORIGIN",
        enable_hsts: bool = True,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(app)
        self.csp_directives = csp_directives or self._default_csp()
        self.x_frame_options = x_frame_options
        self.enable_hsts = enable_hsts
        self.custom_headers = custom_headers or {}

    def _default_csp(self) -> Dict[str, str]:
        """
        Default Content Security Policy directives

        These are restrictive defaults that should be customized based on
        your application's needs.
        """
        return {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # Relax for React
            "style-src": "'self' 'unsafe-inline'",  # Allow inline styles for React
            "img-src": "'self' data: https:",
            "font-src": "'self' data:",
            "connect-src": f"'self' {settings.API_URL}",
            "frame-ancestors": "'self'",
            "base-uri": "'self'",
            "form-action": "'self'",
            "object-src": "'none'",
            "media-src": "'self'",
        }

    def _build_csp_header(self) -> str:
        """Build CSP header string from directives"""
        return "; ".join(f"{key} {value}" for key, value in self.csp_directives.items())

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""

        # Process the request
        response = await call_next(request)

        # Add security headers

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = self.x_frame_options

        # Enable XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self._build_csp_header()

        # Referrer Policy - prevent leaking sensitive URLs
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - disable sensitive features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Cross-domain policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # HSTS - Force HTTPS (only in production)
        if self.enable_hsts and not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Remove potentially leaky headers
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        # Add custom headers
        for header_name, header_value in self.custom_headers.items():
            response.headers[header_name] = header_value

        # Add security identification header (optional)
        if settings.DEBUG:
            response.headers["X-Security-Headers"] = "enabled"

        return response


def create_security_headers_middleware(
    csp_directives: Optional[Dict[str, str]] = None,
    x_frame_options: str = "SAMEORIGIN",
    enable_hsts: bool = True,
    custom_headers: Optional[Dict[str, str]] = None
):
    """
    Factory function to create configured security headers middleware

    Args:
        csp_directives: Custom CSP directives (overrides defaults)
        x_frame_options: X-Frame-Options value (DENY, SAMEORIGIN, or ALLOW-FROM)
        enable_hsts: Whether to enable HTTP Strict Transport Security
        custom_headers: Additional custom headers to add

    Returns:
        Configured SecurityHeadersMiddleware instance

    Example:
        >>> middleware = create_security_headers_middleware(
        ...     csp_directives={"default-src": "'self'"},
        ...     enable_hsts=True
        ... )
    """
    return SecurityHeadersMiddleware(
        app=None,  # Will be set by FastAPI
        csp_directives=csp_directives,
        x_frame_options=x_frame_options,
        enable_hsts=enable_hsts,
        custom_headers=custom_headers
    )
