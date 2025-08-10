"""
User Models for Crypto-0DTE-System

SQLAlchemy models for user management, profiles, and settings.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserStatus(enum.Enum):
    """User status enumeration."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class RiskTolerance(enum.Enum):
    """Risk tolerance enumeration."""
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"
    VERY_AGGRESSIVE = "VERY_AGGRESSIVE"


class User(Base):
    """
    User model for authentication and basic user information.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Personal Information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Verification
    email_verification_token = Column(String(255), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    portfolios = relationship("Portfolio", back_populates="user")
    risk_profile = relationship("RiskProfile", foreign_keys="RiskProfile.user_id", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"

    @property
    def full_name(self):
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username or self.email


class UserProfile(Base):
    """
    User profile model for extended user information and preferences.
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Personal Details
    date_of_birth = Column(DateTime, nullable=True)
    country = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # Financial Information
    annual_income = Column(Float, nullable=True)
    net_worth = Column(Float, nullable=True)
    investment_experience_years = Column(Integer, nullable=True)
    
    # Trading Preferences
    preferred_trading_style = Column(String(50), nullable=True)  # "SCALPING", "DAY_TRADING", "SWING", "LONG_TERM"
    risk_tolerance = Column(String(20), nullable=True)  # "LOW", "MEDIUM", "HIGH"
    max_position_size_percentage = Column(Float, default=10.0)  # Max % of portfolio per position
    
    # Notification Preferences
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    
    # Trading Hours (JSON format for flexibility)
    trading_hours = Column(JSON, nullable=True)  # {"start": "09:00", "end": "17:00", "timezone": "UTC"}
    
    # KYC Information
    kyc_status = Column(String(20), default="PENDING")  # "PENDING", "APPROVED", "REJECTED"
    kyc_documents = Column(JSON, nullable=True)  # Store document references
    kyc_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Profile Picture
    avatar_url = Column(String(500), nullable=True)
    
    # Bio and Notes
    bio = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id}, risk_tolerance={self.risk_tolerance})>"


class UserSettings(Base):
    """
    User settings model for application preferences and configurations.
    """
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Trading Settings
    auto_trading_enabled = Column(Boolean, default=False)
    max_daily_trades = Column(Integer, default=10)
    max_daily_loss_percentage = Column(Float, default=5.0)  # Stop trading if daily loss exceeds this
    
    # Risk Management
    use_stop_loss = Column(Boolean, default=True)
    default_stop_loss_percentage = Column(Float, default=2.0)
    use_take_profit = Column(Boolean, default=True)
    default_take_profit_percentage = Column(Float, default=5.0)
    
    # Signal Settings
    minimum_signal_confidence = Column(Float, default=0.7)  # Only execute signals above this confidence
    signal_notifications = Column(Boolean, default=True)
    auto_execute_signals = Column(Boolean, default=False)
    
    # Display Settings
    preferred_currency = Column(String(10), default="USDT")
    theme = Column(String(20), default="LIGHT")  # "LIGHT", "DARK"
    language = Column(String(10), default="EN")
    timezone = Column(String(50), default="UTC")
    
    # Dashboard Settings
    dashboard_layout = Column(JSON, nullable=True)  # Store custom dashboard configuration
    favorite_symbols = Column(JSON, nullable=True)  # Array of favorite trading pairs
    
    # API Settings
    api_rate_limit = Column(Integer, default=100)  # Requests per minute
    webhook_url = Column(String(500), nullable=True)  # For external notifications
    
    # Privacy Settings
    profile_visibility = Column(String(20), default="PRIVATE")  # "PUBLIC", "PRIVATE", "FRIENDS"
    share_performance = Column(Boolean, default=False)
    
    # Backup and Security
    two_factor_enabled = Column(Boolean, default=False)
    backup_email = Column(String(255), nullable=True)
    session_timeout_minutes = Column(Integer, default=60)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(id={self.id}, user_id={self.user_id}, auto_trading={self.auto_trading_enabled})>"

