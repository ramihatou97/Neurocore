"""
Authentication service for user registration, login, and JWT token management
Implements secure password hashing with bcrypt and JWT token generation
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from backend.database.models import User
from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Authentication service handling all auth-related operations

    Features:
    - Secure password hashing with bcrypt
    - JWT token generation with expiry
    - Token validation and decoding
    - User registration with validation
    - User authentication (login)
    - Current user retrieval from token
    """

    def __init__(self, db_session: Session):
        """
        Initialize AuthService

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    # ==================== Password Operations ====================

    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt

        Args:
            password: Plain text password

        Returns:
            str: Hashed password

        Security:
            - Uses bcrypt algorithm (computationally expensive)
            - Automatic salt generation
            - Resistant to rainbow table attacks
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password from database

        Returns:
            bool: True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    def validate_password_strength(self, password: str) -> None:
        """
        Validate password meets strength requirements

        Args:
            password: Password to validate

        Raises:
            HTTPException: If password doesn't meet requirements

        Requirements (from settings):
            - Minimum length: PASSWORD_MIN_LENGTH (default: 8)
            - At least one uppercase letter (if PASSWORD_REQUIRE_UPPERCASE)
            - At least one lowercase letter (if PASSWORD_REQUIRE_LOWERCASE)
            - At least one digit (if PASSWORD_REQUIRE_DIGIT)
        """
        errors = []

        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")

        if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if settings.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if errors:
            logger.warning(f"Password validation failed: {', '.join(errors)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Password does not meet requirements", "requirements": errors}
            )

    # ==================== JWT Token Operations ====================

    def create_access_token(
        self,
        user_id: str,
        email: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a JWT access token for a user

        Args:
            user_id: User's unique identifier
            email: User's email address
            additional_claims: Optional additional claims to include in token

        Returns:
            str: Encoded JWT token

        Token payload includes:
            - user_id: User identifier
            - email: User email
            - exp: Expiration timestamp
            - iat: Issued at timestamp
            - Additional claims (if provided)
        """
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)

        payload = {
            "user_id": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow()
        }

        # Add additional claims if provided
        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )

        logger.info(f"Access token created for user: {email}")
        return token

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token

        Args:
            token: JWT token to decode

        Returns:
            Dict[str, Any]: Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )

        except JWTError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # ==================== User Operations ====================

    def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> User:
        """
        Register a new user

        Args:
            email: User's email address
            password: User's plain text password
            full_name: User's full name (optional)

        Returns:
            User: Created user object

        Raises:
            HTTPException: If email already exists or validation fails

        Process:
            1. Check if email already exists
            2. Validate password strength
            3. Hash password
            4. Create user in database
            5. Return user object
        """
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            logger.warning(f"Registration failed: Email already exists: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Validate password strength
        self.validate_password_strength(password)

        # Hash password
        hashed_password = self.hash_password(password)

        # Create user
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_admin=False
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(f"User registered successfully: {email}")
        return user

    def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate a user with email and password

        Args:
            email: User's email address
            password: User's plain text password

        Returns:
            User: Authenticated user object

        Raises:
            HTTPException: If credentials are invalid or account is inactive

        Security:
            - Returns same error for invalid email and invalid password
              to prevent email enumeration attacks
        """
        # Get user by email
        user = self.db.query(User).filter(User.email == email).first()

        # Check if user exists and password is correct
        if not user or not self.verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid credentials for {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Authentication failed: Inactive account: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Please contact support."
            )

        logger.info(f"User authenticated successfully: {email}")
        return user

    def get_current_user(self, token: str) -> User:
        """
        Get current user from JWT token

        Args:
            token: JWT access token

        Returns:
            User: Current authenticated user

        Raises:
            HTTPException: If token is invalid or user not found

        Usage in FastAPI routes:
            current_user = auth_service.get_current_user(token)
        """
        # Decode token
        payload = self.decode_token(token)

        # Extract user_id from payload
        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Token payload missing user_id")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Get user from database
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User not found for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )

        return user

    def refresh_token(self, old_token: str) -> str:
        """
        Refresh an access token

        Args:
            old_token: Current JWT token

        Returns:
            str: New JWT token with extended expiry

        Raises:
            HTTPException: If token is invalid

        Note: This creates a new token with the same claims but fresh expiry
        """
        # Decode and validate old token
        payload = self.decode_token(old_token)

        # Get user to ensure they still exist and are active
        user = self.get_current_user(old_token)

        # Create new token
        new_token = self.create_access_token(
            user_id=str(user.id),
            email=user.email
        )

        logger.info(f"Token refreshed for user: {user.email}")
        return new_token
