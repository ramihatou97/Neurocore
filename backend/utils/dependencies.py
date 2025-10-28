"""
FastAPI dependencies for authentication and authorization
Provides reusable dependencies for protected routes
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.database import get_db, User
# Lazy import of AuthService to avoid circular dependency
# from backend.services import AuthService (moved inside functions)
from backend.utils import get_logger

logger = get_logger(__name__)

# HTTP Bearer scheme for JWT tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user from JWT token

    Args:
        credentials: HTTP Authorization header with Bearer token
        db: Database session

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found

    Usage in FastAPI routes:
        @app.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    # Lazy import to avoid circular dependency
    from backend.services.auth_service import AuthService

    token = credentials.credentials
    auth_service = AuthService(db)

    try:
        user = auth_service.get_current_user(token)
        return user
    except HTTPException:
        # Re-raise HTTP exceptions from auth service
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to get current active user

    This is a convenience dependency that ensures the user is active.
    The get_current_user dependency already checks this, but this makes
    the intent explicit in route signatures.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is not active

    Usage:
        @app.get("/active-only")
        async def active_only_route(user: User = Depends(get_current_active_user)):
            return {"user": user.email}
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    FastAPI dependency to get current admin user

    Ensures the user is both active and has admin privileges.

    Args:
        current_user: User from get_current_active_user dependency

    Returns:
        User: Current admin user

    Raises:
        HTTPException: If user is not an admin

    Usage:
        @app.delete("/admin/user/{user_id}")
        async def delete_user(
            user_id: str,
            admin: User = Depends(get_current_admin_user)
        ):
            # Only admins can access this route
            return {"message": "User deleted"}
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user attempted admin access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency to get current user if token is provided (optional auth)

    This allows routes to work with or without authentication.
    If a token is provided and valid, returns the user.
    If no token is provided, returns None.
    If token is provided but invalid, raises exception.

    Args:
        credentials: Optional HTTP Authorization header
        db: Database session

    Returns:
        Optional[User]: Current user if authenticated, None otherwise

    Raises:
        HTTPException: If token is provided but invalid

    Usage:
        @app.get("/public-or-private")
        async def optional_auth_route(user: Optional[User] = Depends(get_optional_current_user)):
            if user:
                return {"message": f"Hello, {user.email}"}
            else:
                return {"message": "Hello, guest"}
    """
    if credentials is None:
        return None

    # Lazy import to avoid circular dependency
    from backend.services.auth_service import AuthService

    auth_service = AuthService(db)
    try:
        user = auth_service.get_current_user(credentials.credentials)
        return user
    except HTTPException:
        # If token is provided but invalid, raise the exception
        raise
