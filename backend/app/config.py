"""
Crypto-0DTE-System Configuration

Centralized configuration management using Pydantic settings.
Loads configuration from environment variables and .env files.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # =============================================================================
    # BASIC APPLICATION SETTINGS
    # =============================================================================
    
    APP_NAME: str = "Crypto-0DTE-System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    TESTING: bool = Field(default=False, env="TESTING")
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    
    # PostgreSQL
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/database",
        env="DATABASE_URL"
    )
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # InfluxDB
    INFLUXDB_URL: str = Field(default="http://localhost:8086", env="INFLUXDB_URL")
    INFLUXDB_TOKEN: str = Field(default="", env="INFLUXDB_TOKEN")
    INFLUXDB_ORG: str = Field(default="", env="INFLUXDB_ORG")
    INFLUXDB_BUCKET: str = Field(default="market_data", env="INFLUXDB_BUCKET")
    
    # =============================================================================
    # DELTA EXCHANGE API CONFIGURATION
    # =============================================================================
    
    DELTA_API_KEY: str = Field(default="", env="DELTA_API_KEY")
    DELTA_API_SECRET: str = Field(default="", env="DELTA_API_SECRET")
    DELTA_API_PASSPHRASE: str = Field(default="", env="DELTA_API_PASSPHRASE")
    DELTA_BASE_URL: str = Field(default="https://api.delta.exchange", env="DELTA_BASE_URL")
    DELTA_WEBSOCKET_URL: str = Field(default="wss://socket.delta.exchange", env="DELTA_WEBSOCKET_URL")
    
    # =============================================================================
    # REFERENCE EXCHANGES (for arbitrage and data validation)
    # =============================================================================
    
    # Binance
    BINANCE_API_KEY: Optional[str] = Field(default=None, env="BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = Field(default=None, env="BINANCE_API_SECRET")
    
    # Coinbase
    COINBASE_API_KEY: Optional[str] = Field(default=None, env="COINBASE_API_KEY")
    COINBASE_API_SECRET: Optional[str] = Field(default=None, env="COINBASE_API_SECRET")
    COINBASE_PASSPHRASE: Optional[str] = Field(default=None, env="COINBASE_PASSPHRASE")
    
    # =============================================================================
    # AI/ML CONFIGURATION
    # =============================================================================
    
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1", env="OPENAI_API_BASE")
    
    MODEL_UPDATE_FREQUENCY: int = Field(default=3600, env="MODEL_UPDATE_FREQUENCY")  # 1 hour
    AI_CONFIDENCE_THRESHOLD: float = Field(default=0.75, env="AI_CONFIDENCE_THRESHOLD")
    LEARNING_RATE: float = Field(default=0.001, env="LEARNING_RATE")
    
    # =============================================================================
    # TRADING CONFIGURATION
    # =============================================================================
    
    # Account settings
    ACCOUNT_SIZE: float = Field(default=100000.0, env="ACCOUNT_SIZE")  # $100K default
    BASE_CURRENCY: str = Field(default="USDT", env="BASE_CURRENCY")
    
    # Position sizing
    MAX_POSITION_SIZE: float = Field(default=0.30, env="MAX_POSITION_SIZE")  # 30%
    MIN_POSITION_SIZE: float = Field(default=0.02, env="MIN_POSITION_SIZE")  # 2%
    CORRELATION_LIMIT: float = Field(default=0.60, env="CORRELATION_LIMIT")  # 60%
    
    # Risk management
    DAILY_LOSS_LIMIT: float = Field(default=0.03, env="DAILY_LOSS_LIMIT")  # 3%
    WEEKLY_LOSS_LIMIT: float = Field(default=0.08, env="WEEKLY_LOSS_LIMIT")  # 8%
    MAX_DRAWDOWN: float = Field(default=0.15, env="MAX_DRAWDOWN")  # 15%
    STOP_LOSS_MULTIPLIER: float = Field(default=0.5, env="STOP_LOSS_MULTIPLIER")
    
    # =============================================================================
    # STRATEGY CONFIGURATION
    # =============================================================================
    
    # BTC Lightning Scalp
    BTC_SCALP_ENABLED: bool = Field(default=True, env="BTC_SCALP_ENABLED")
    BTC_SCALP_POSITION_SIZE: float = Field(default=0.08, env="BTC_SCALP_POSITION_SIZE")
    BTC_MOMENTUM_THRESHOLD: float = Field(default=0.005, env="BTC_MOMENTUM_THRESHOLD")
    BTC_VOLUME_CONFIRMATION: float = Field(default=1.5, env="BTC_VOLUME_CONFIRMATION")
    
    # ETH DeFi Correlation
    ETH_DEFI_ENABLED: bool = Field(default=True, env="ETH_DEFI_ENABLED")
    ETH_DEFI_POSITION_SIZE: float = Field(default=0.10, env="ETH_DEFI_POSITION_SIZE")
    ETH_CORRELATION_THRESHOLD: float = Field(default=0.7, env="ETH_CORRELATION_THRESHOLD")
    DEFI_TOKENS: str = Field(default="UNI,AAVE,COMP,MKR", env="DEFI_TOKENS")
    
    # Cross-Asset Arbitrage
    ARBITRAGE_ENABLED: bool = Field(default=True, env="ARBITRAGE_ENABLED")
    ARBITRAGE_POSITION_SIZE: float = Field(default=0.12, env="ARBITRAGE_POSITION_SIZE")
    CORRELATION_DEVIATION_THRESHOLD: float = Field(default=0.15, env="CORRELATION_DEVIATION_THRESHOLD")
    
    # Funding Rate Arbitrage
    FUNDING_ARBITRAGE_ENABLED: bool = Field(default=True, env="FUNDING_ARBITRAGE_ENABLED")
    FUNDING_POSITION_SIZE: float = Field(default=0.12, env="FUNDING_POSITION_SIZE")
    FUNDING_RATE_THRESHOLD: float = Field(default=0.01, env="FUNDING_RATE_THRESHOLD")
    
    # Fear & Greed Contrarian
    SENTIMENT_ENABLED: bool = Field(default=True, env="SENTIMENT_ENABLED")
    SENTIMENT_POSITION_SIZE: float = Field(default=0.15, env="SENTIMENT_POSITION_SIZE")
    FEAR_THRESHOLD: int = Field(default=20, env="FEAR_THRESHOLD")
    GREED_THRESHOLD: int = Field(default=80, env="GREED_THRESHOLD")
    
    # =============================================================================
    # INDIAN REGULATORY COMPLIANCE
    # =============================================================================
    
    # Tax configuration
    CRYPTO_TAX_RATE: float = Field(default=0.30, env="CRYPTO_TAX_RATE")  # 30%
    TDS_RATE: float = Field(default=0.01, env="TDS_RATE")  # 1%
    TDS_THRESHOLD: float = Field(default=10000.0, env="TDS_THRESHOLD")  # ₹10,000
    
    # Trading limits (in INR)
    DAILY_TRADING_LIMIT: float = Field(default=1000000.0, env="DAILY_TRADING_LIMIT")  # ₹10 Lakh
    MONTHLY_TRADING_LIMIT: float = Field(default=10000000.0, env="MONTHLY_TRADING_LIMIT")  # ₹1 Crore
    
    # KYC/AML
    KYC_VERIFICATION_REQUIRED: bool = Field(default=True, env="KYC_VERIFICATION_REQUIRED")
    AML_MONITORING_ENABLED: bool = Field(default=True, env="AML_MONITORING_ENABLED")
    
    # =============================================================================
    # EXTERNAL DATA SOURCES
    # =============================================================================
    
    # Fear & Greed Index
    FEAR_GREED_API_URL: str = Field(default="https://api.alternative.me/fng/", env="FEAR_GREED_API_URL")
    FEAR_GREED_UPDATE_INTERVAL: int = Field(default=3600, env="FEAR_GREED_UPDATE_INTERVAL")
    
    # DeFi data
    DEFI_PULSE_API_KEY: Optional[str] = Field(default=None, env="DEFI_PULSE_API_KEY")
    COINGECKO_API_KEY: Optional[str] = Field(default=None, env="COINGECKO_API_KEY")
    
    # News sentiment
    NEWS_API_KEY: Optional[str] = Field(default=None, env="NEWS_API_KEY")
    SENTIMENT_UPDATE_INTERVAL: int = Field(default=1800, env="SENTIMENT_UPDATE_INTERVAL")
    
    # =============================================================================
    # MONITORING & LOGGING
    # =============================================================================
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE_PATH: str = Field(default="/var/log/crypto-0dte/app.log", env="LOG_FILE_PATH")
    LOG_ROTATION_SIZE: str = Field(default="100MB", env="LOG_ROTATION_SIZE")
    LOG_RETENTION_DAYS: int = Field(default=30, env="LOG_RETENTION_DAYS")
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    GRAFANA_ENABLED: bool = Field(default=True, env="GRAFANA_ENABLED")
    GRAFANA_PORT: int = Field(default=3001, env="GRAFANA_PORT")
    
    # =============================================================================
    # SECURITY CONFIGURATION
    # =============================================================================
    
    # JWT tokens
    JWT_SECRET_KEY: str = Field(default="", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # API security
    API_RATE_LIMIT: int = Field(default=1000, env="API_RATE_LIMIT")  # per minute
    API_CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        env="API_CORS_ORIGINS"
    )
    
    # Encryption
    ENCRYPTION_KEY: str = Field(default="", env="ENCRYPTION_KEY")
    
    # =============================================================================
    # PERFORMANCE TUNING
    # =============================================================================
    
    # Worker processes
    WORKER_PROCESSES: int = Field(default=4, env="WORKER_PROCESSES")
    WORKER_CONNECTIONS: int = Field(default=1000, env="WORKER_CONNECTIONS")
    WORKER_TIMEOUT: int = Field(default=30, env="WORKER_TIMEOUT")
    
    # Caching
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")  # 5 minutes
    MARKET_DATA_CACHE_TTL: int = Field(default=5, env="MARKET_DATA_CACHE_TTL")  # 5 seconds
    
    # Database connection pooling
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=30, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    # =============================================================================
    # VALIDATORS
    # =============================================================================
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment setting"""
        allowed_environments = ["development", "staging", "production"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of {allowed_environments}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()
    
    @validator("API_CORS_ORIGINS")
    def validate_cors_origins(cls, v):
        """Convert CORS origins string to list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("DEFI_TOKENS")
    def validate_defi_tokens(cls, v):
        """Convert DeFi tokens string to list"""
        if isinstance(v, str):
            return [token.strip() for token in v.split(",")]
        return v
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key for production security"""
        if not v:
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError("JWT_SECRET_KEY is required in production")
            return "development-only-secret-key-not-for-production-use"
        
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters for security")
        
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v or v == "postgresql://user:password@localhost:5432/database":
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError("DATABASE_URL must be configured for production")
        
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        
        return v
    
    @validator("DELTA_API_KEY")
    def validate_delta_api_key(cls, v):
        """Validate Delta Exchange API key"""
        if not v and os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError("DELTA_API_KEY is required for production trading")
        return v
    
    @validator("DELTA_API_SECRET")
    def validate_delta_api_secret(cls, v):
        """Validate Delta Exchange API secret"""
        if not v and os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError("DELTA_API_SECRET is required for production trading")
        return v
    
    # =============================================================================
    # COMPUTED PROPERTIES
    # =============================================================================
    
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """Get allowed hosts for production"""
        if self.ENVIRONMENT == "production":
            return ["crypto-0dte.tktinc.com", "api.crypto-0dte.tktinc.com"]
        return ["*"]
    
    @property
    def DATABASE_CONFIG(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            "url": self.DATABASE_URL,
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "echo": self.DEBUG
        }
    
    @property
    def REDIS_CONFIG(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        config = {"url": self.REDIS_URL}
        if self.REDIS_PASSWORD:
            config["password"] = self.REDIS_PASSWORD
        return config
    
    @property
    def STRATEGY_CONFIG(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        return {
            "btc_lightning_scalp": {
                "enabled": self.BTC_SCALP_ENABLED,
                "position_size": self.BTC_SCALP_POSITION_SIZE,
                "momentum_threshold": self.BTC_MOMENTUM_THRESHOLD,
                "volume_confirmation": self.BTC_VOLUME_CONFIRMATION
            },
            "eth_defi_correlation": {
                "enabled": self.ETH_DEFI_ENABLED,
                "position_size": self.ETH_DEFI_POSITION_SIZE,
                "correlation_threshold": self.ETH_CORRELATION_THRESHOLD,
                "defi_tokens": self.DEFI_TOKENS
            },
            "cross_asset_arbitrage": {
                "enabled": self.ARBITRAGE_ENABLED,
                "position_size": self.ARBITRAGE_POSITION_SIZE,
                "correlation_deviation_threshold": self.CORRELATION_DEVIATION_THRESHOLD
            },
            "funding_rate_arbitrage": {
                "enabled": self.FUNDING_ARBITRAGE_ENABLED,
                "position_size": self.FUNDING_POSITION_SIZE,
                "funding_rate_threshold": self.FUNDING_RATE_THRESHOLD
            },
            "fear_greed_contrarian": {
                "enabled": self.SENTIMENT_ENABLED,
                "position_size": self.SENTIMENT_POSITION_SIZE,
                "fear_threshold": self.FEAR_THRESHOLD,
                "greed_threshold": self.GREED_THRESHOLD
            }
        }
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()

