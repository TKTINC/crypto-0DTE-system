"""
Middleware package for Crypto-0DTE System

Contains authentication, CORS, rate limiting, and other middleware components.
"""

from .auth import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_permissions,
    require_trading_permission,
    require_admin_permission,
    require_compliance_permission,
    rate_limit_middleware,
    authenticate_user,
    create_user_token,
    hash_password,
    verify_password
)

__all__ = [
    "get_current_user",
    "get_current_active_user", 
    "require_role",
    "require_permissions",
    "require_trading_permission",
    "require_admin_permission",
    "require_compliance_permission",
    "rate_limit_middleware",
    "authenticate_user",
    "create_user_token",
    "hash_password",
    "verify_password"
]

