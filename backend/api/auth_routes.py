"""
Authentication API routes for user registration, login, and profile management
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.database import get_db, User
from backend.services.auth_service import AuthService
from backend.utils import get_logger, get_current_user, get_current_active_user

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])


# ==================== Request/Response Models ====================

class RegisterRequest(BaseModel):
    """Request model for user registration"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password (min 8 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123",
                "full_name": "John Doe"
            }
        }


class LoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123"
            }
        }


class TokenResponse(BaseModel):
    """Response model for successful authentication"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    user: dict = Field(..., description="User information")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_admin": False
                }
            }
        }


class UserResponse(BaseModel):
    """Response model for user information"""
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_admin": False,
                "created_at": "2025-10-27T12:00:00",
                "updated_at": "2025-10-27T12:00:00"
            }
        }


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


# ==================== Authentication Routes ====================

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Register a new user account with email and password.

    Password requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Returns a JWT access token that can be used for authenticated requests.
    """
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Register a new user and return JWT token

    Process:
    1. Validate password strength
    2. Check if email already exists
    3. Hash password with bcrypt
    4. Create user in database
    5. Generate JWT token
    6. Return token and user info
    """
    auth_service = AuthService(db)

    try:
        # Register user
        user = auth_service.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )

        # Create access token
        token = auth_service.create_access_token(
            user_id=str(user.id),
            email=user.email
        )

        logger.info(f"User registered successfully: {user.email}")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user.to_dict()
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like duplicate email)
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="""
    Authenticate a user with email and password.

    Returns a JWT access token that expires after 24 hours (configurable).
    The token should be included in the Authorization header as: Bearer <token>
    """
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return JWT token

    Process:
    1. Verify email exists
    2. Verify password matches
    3. Check account is active
    4. Generate JWT token
    5. Return token and user info
    """
    auth_service = AuthService(db)

    try:
        # Authenticate user
        user = auth_service.authenticate_user(
            email=request.email,
            password=request.password
        )

        # Create access token
        token = auth_service.create_access_token(
            user_id=str(user.id),
            email=user.email
        )

        logger.info(f"User logged in successfully: {user.email}")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user.to_dict()
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like invalid credentials)
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
    description="""
    Get information about the currently authenticated user.

    Requires a valid JWT token in the Authorization header: Bearer <token>
    """
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current authenticated user's information

    This is a protected route that requires authentication.
    Returns the full user profile of the currently logged-in user.
    """
    logger.debug(f"User info retrieved: {current_user.email}")

    return UserResponse(**current_user.to_dict())


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
    Refresh an existing JWT token to extend its validity.

    Requires a valid (but possibly expiring soon) JWT token.
    Returns a new token with extended expiry.
    """
)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Refresh JWT token for current user

    This allows users to get a new token without re-entering credentials.
    Useful for maintaining long sessions.
    """
    auth_service = AuthService(db)

    try:
        # Create new access token
        new_token = auth_service.create_access_token(
            user_id=str(current_user.id),
            email=current_user.email
        )

        logger.info(f"Token refreshed for user: {current_user.email}")

        return TokenResponse(
            access_token=new_token,
            token_type="bearer",
            user=current_user.to_dict()
        )

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh"
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (client-side only)",
    description="""
    Logout endpoint (informational only).

    Since JWTs are stateless, actual logout must be handled client-side
    by deleting the token. This endpoint exists for API consistency
    and can be extended with token blacklisting if needed.
    """
)
async def logout(
    current_user: User = Depends(get_current_user)
) -> MessageResponse:
    """
    Logout user (informational endpoint)

    JWT tokens are stateless, so logout is primarily client-side.
    Client should:
    1. Delete the token from storage
    2. Clear any cached user data
    3. Redirect to login page

    For enhanced security, implement token blacklisting in production.
    """
    logger.info(f"User logged out: {current_user.email}")

    return MessageResponse(
        message="Logged out successfully. Please delete the token from client storage."
    )


# ==================== Health Check for Auth System ====================

@router.get(
    "/health",
    response_model=MessageResponse,
    summary="Authentication system health check",
    description="Check if the authentication system is operational"
)
async def auth_health_check() -> MessageResponse:
    """
    Health check endpoint for authentication system

    Returns a simple message indicating the auth system is operational.
    No authentication required.
    """
    return MessageResponse(message="Authentication system is healthy")
