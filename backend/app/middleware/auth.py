"""
Authentication Middleware for Crypto-0DTE System

Provides JWT-based authentication and authorization for API endpoints.
Implements secure token validation and user session management.
"""

import jwt
import time
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.config import settings
from app.models.user import User
from app.database import get_db
from sqlalchemy.orm import Session


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


class AuthorizationError(Exception):
    """Custom authorization error"""
    pass


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY must be set in environment variables")
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise AuthenticationError(f"Failed to create access token: {str(e)}")


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token"""
    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY must be set in environment variables")
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user"""
    try:
        # Verify the token
        payload = verify_token(credentials.credentials)
        user_id: int = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise AuthenticationError("User not found")
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: str):
    """Decorator to require specific user role"""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role} role"
            )
        return current_user
    return role_checker


def require_permissions(required_permissions: list):
    """Decorator to require specific permissions"""
    def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_permissions = current_user.permissions or []
        
        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Operation requires {permission} permission"
                )
        return current_user
    return permission_checker


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if request is allowed based on rate limit"""
        now = time.time()
        
        # Clean old entries
        self.requests = {
            k: v for k, v in self.requests.items() 
            if now - v['timestamp'] < window
        }
        
        # Check current key
        if key not in self.requests:
            self.requests[key] = {'count': 1, 'timestamp': now}
            return True
        
        request_data = self.requests[key]
        if now - request_data['timestamp'] >= window:
            # Reset window
            self.requests[key] = {'count': 1, 'timestamp': now}
            return True
        
        if request_data['count'] >= limit:
            return False
        
        request_data['count'] += 1
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Get client IP
    client_ip = request.client.host
    
    # Check rate limit
    if not rate_limiter.is_allowed(client_ip, settings.API_RATE_LIMIT):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    response = await call_next(request)
    return response


def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """Authenticate a user with email and password"""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def create_user_token(user: User) -> str:
    """Create a JWT token for a user"""
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions or []
    }
    
    return create_access_token(token_data)


# Trading-specific authorization functions
def require_trading_permission(current_user: User = Depends(get_current_active_user)) -> User:
    """Require trading permission"""
    if not current_user.can_trade:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trading permission required"
        )
    return current_user


def require_admin_permission(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin permission"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    return current_user


def require_compliance_permission(current_user: User = Depends(get_current_active_user)) -> User:
    """Require compliance permission"""
    if current_user.role not in ["admin", "compliance"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compliance permission required"
        )
    return current_user

