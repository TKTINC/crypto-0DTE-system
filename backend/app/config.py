"""
Configuration settings for the Crypto 0DTE Trading System.

This module contains all configuration settings for the application,
including database, API keys, and service configurations.
"""

import os
from typing import List, Union, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application Settings
    APP_NAME: str = "Crypto 0DTE Trading System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # API Configuration (FIXED - Added missing fields)
    API_V1_STR: str = "/api/v1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    HOST: str = "0.0.0.0"  # Added for .env.local compatibility
    PORT: int = 8000       # Added for .env.local compatibility
    
    # CORS Configuration (FIXED - Added proper parsing)
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    API_CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    # Trusted Host Configuration
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "*.localhost"
    ]
    
    # Database Configuration (PostgreSQL Only)
    DATABASE_URL: str = "postgresql+asyncpg://crypto_user:crypto_password@localhost:5432/crypto_0dte_local"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # InfluxDB Configuration (for time-series data)
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: Optional[str] = None
    INFLUXDB_ORG: str = "crypto-trading"
    INFLUXDB_BUCKET: str = "market-data"
    
    # Delta Exchange API Configuration - COMPREHENSIVE ENVIRONMENT SUPPORT
    
    # Production API Keys (for live trading - from main delta.exchange account)
    DELTA_API_KEY: str = Field(default="", env="DELTA_API_KEY")
    DELTA_API_SECRET: str = Field(default="", env="DELTA_API_SECRET")
    DELTA_API_PASSPHRASE: str = Field(default="", env="DELTA_API_PASSPHRASE")
    
    # Testnet API Keys (for paper trading - from demo.delta.exchange account)
    DELTA_TESTNET_API_KEY: str = Field(default="", env="DELTA_TESTNET_API_KEY")
    DELTA_TESTNET_API_SECRET: str = Field(default="", env="DELTA_TESTNET_API_SECRET")
    DELTA_TESTNET_PASSPHRASE: str = Field(default="", env="DELTA_TESTNET_PASSPHRASE")
    
    # Environment switching - defaults to testnet for safety
    DELTA_EXCHANGE_TESTNET: bool = Field(default=True, env="DELTA_EXCHANGE_TESTNET")
    PAPER_TRADING: bool = Field(default=True, env="PAPER_TRADING")
    
    # Testnet URLs (for paper trading - demo account)
    DELTA_TESTNET_BASE_URL: str = "https://cdn-ind.testnet.deltaex.org"
    DELTA_TESTNET_WEBSOCKET_URL: str = "wss://testnet-socket.delta.exchange"
    
    # Live URLs (for real trading - production account)  
    DELTA_LIVE_BASE_URL: str = "https://api.india.delta.exchange"
    DELTA_LIVE_WEBSOCKET_URL: str = "wss://socket.delta.exchange"
    
    # Dynamic properties for current environment
    @property
    def current_delta_api_key(self) -> str:
        """Get API key for current environment"""
        return self.DELTA_TESTNET_API_KEY if self.PAPER_TRADING else self.DELTA_API_KEY
    
    @property
    def current_delta_api_secret(self) -> str:
        """Get API secret for current environment"""
        return self.DELTA_TESTNET_API_SECRET if self.PAPER_TRADING else self.DELTA_API_SECRET
    
    @property
    def current_delta_passphrase(self) -> str:
        """Get API passphrase for current environment"""
        return self.DELTA_TESTNET_PASSPHRASE if self.PAPER_TRADING else self.DELTA_API_PASSPHRASE
    
    @property
    def current_delta_base_url(self) -> str:
        """Get base URL for current environment"""
        return self.DELTA_TESTNET_BASE_URL if self.PAPER_TRADING else self.DELTA_LIVE_BASE_URL
    
    @property
    def current_delta_websocket_url(self) -> str:
        """Get WebSocket URL for current environment"""
        return self.DELTA_TESTNET_WEBSOCKET_URL if self.PAPER_TRADING else self.DELTA_LIVE_WEBSOCKET_URL
    
    # OpenAI API Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7
    
    # JWT Configuration (FIXED - Added missing fields)
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"  # Added for .env.local compatibility
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Added for .env.local compatibility
    
    # Security Configuration
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    BCRYPT_ROUNDS: int = 12
    
    # Logging Configuration (FIXED - Added missing fields)
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_FILE: str = "/Users/balu/crypto-0DTE-system/logs/backend.log"  # Added for .env.local compatibility
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # WebSocket Configuration
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    WEBSOCKET_MAX_CONNECTIONS: int = 1000
    
    # Trading Configuration
    MAX_POSITION_SIZE: float = 1000.0  # USD
    MAX_DAILY_LOSS: float = 500.0  # USD
    RISK_PERCENTAGE: float = 0.02  # 2% risk per trade
    
    # AI/ML Configuration
    MODEL_UPDATE_INTERVAL: int = 3600  # seconds
    FEATURE_WINDOW_SIZE: int = 100  # number of data points
    PREDICTION_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Monitoring and Logging
    METRICS_ENABLED: bool = True
    HEALTH_CHECK_INTERVAL: int = 60  # seconds
    
    # Market Data Configuration
    MARKET_DATA_SYMBOLS: Union[str, List[str]] = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
    MARKET_DATA_TIMEFRAMES: Union[str, List[str]] = ["1m", "5m", "15m", "1h"]
    MARKET_DATA_HISTORY_DAYS: int = 30
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format"""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        
        # Ensure PostgreSQL URL format
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        
        return v
    
    @field_validator("CORS_ORIGINS", "API_CORS_ORIGINS", "MARKET_DATA_SYMBOLS", "MARKET_DATA_TIMEFRAMES")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # Handle comma-separated string from environment variables
            if ',' in v:
                return [origin.strip() for origin in v.split(',')]
            # Handle single string
            return [v.strip()]
        elif isinstance(v, list):
            # Already a list, ensure all items are strings
            return [str(item).strip() for item in v]
        else:
            # Fallback to default
            return ["http://localhost:3000"]
    
    @field_validator("DELTA_API_KEY", "OPENAI_API_KEY")
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        """Validate API keys (allow empty for development)"""
        field_name = info.field_name
        
        # Allow empty keys in development/testing
        if not v:
            print(f"Warning: {field_name} is empty - some features may not work")
        
        return v
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations"""
        return self.DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql://")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() in ["production", "prod"]
    
    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Allow extra fields to prevent validation errors
        extra = "ignore"


# Global settings instance
settings = Settings()

# Export commonly used settings
__all__ = ["settings", "Settings"]

