"""
Environment File Generator

Generates .env.local file from config.py settings during backend startup.
This ensures the environment file is always in sync with the configuration.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def generate_env_local_from_config(settings) -> bool:
    """
    Generate .env.local file from current settings configuration
    
    Args:
        settings: The settings instance from config.py
        
    Returns:
        bool: True if file was generated successfully, False otherwise
    """
    try:
        # Determine the backend directory path
        backend_dir = Path(__file__).parent.parent
        env_file_path = backend_dir / ".env.local"
        
        logger.info(f"Generating .env.local file at: {env_file_path}")
        
        # Generate environment file content based on current settings
        env_content = f"""# Auto-generated .env.local file from config.py
# Generated at startup to ensure configuration consistency
# DO NOT EDIT MANUALLY - This file is regenerated on each backend restart

# Database Configuration
DATABASE_URL={settings.DATABASE_URL}

# Redis Configuration
REDIS_URL={settings.REDIS_URL}

# Application Configuration
ENVIRONMENT={settings.ENVIRONMENT}
DEBUG={str(settings.DEBUG).lower()}
JWT_SECRET_KEY={settings.JWT_SECRET_KEY}
API_CORS_ORIGINS={','.join(settings.API_CORS_ORIGINS) if isinstance(settings.API_CORS_ORIGINS, list) else settings.API_CORS_ORIGINS}

# Server Configuration
HOST={settings.HOST}
PORT={settings.PORT}

# Delta Exchange Configuration - Production API Keys (for live trading)
DELTA_API_KEY={settings.DELTA_API_KEY}
DELTA_API_SECRET={settings.DELTA_API_SECRET}
DELTA_API_PASSPHRASE={settings.DELTA_API_PASSPHRASE}

# Delta Exchange Configuration - Testnet API Keys (for paper trading)
DELTA_TESTNET_API_KEY={settings.DELTA_TESTNET_API_KEY}
DELTA_TESTNET_API_SECRET={settings.DELTA_TESTNET_API_SECRET}
DELTA_TESTNET_PASSPHRASE={settings.DELTA_TESTNET_PASSPHRASE}

# Environment Configuration
PAPER_TRADING={str(settings.PAPER_TRADING).lower()}
DELTA_EXCHANGE_TESTNET={str(settings.DELTA_EXCHANGE_TESTNET).lower()}

# OpenAI Configuration
OPENAI_API_KEY={settings.OPENAI_API_KEY}
OPENAI_API_BASE={settings.OPENAI_API_BASE}

# Logging Configuration
LOG_LEVEL={settings.LOG_LEVEL}
LOG_FILE={settings.LOG_FILE}

# Security Configuration
SECRET_KEY={settings.SECRET_KEY}
ALGORITHM={settings.ALGORITHM}
ACCESS_TOKEN_EXPIRE_MINUTES={settings.ACCESS_TOKEN_EXPIRE_MINUTES}

# Current Environment URLs (Auto-selected based on PAPER_TRADING)
# Testnet URL: {settings.DELTA_TESTNET_BASE_URL}
# Live URL: {settings.DELTA_LIVE_BASE_URL}
# Current URL: {settings.current_delta_base_url}
"""

        # Write the environment file
        with open(env_file_path, 'w') as f:
            f.write(env_content)
        
        logger.info("✅ .env.local file generated successfully")
        logger.info(f"   Environment: {'TESTNET' if settings.PAPER_TRADING else 'LIVE'}")
        logger.info(f"   Base URL: {settings.current_delta_base_url}")
        logger.info(f"   API Key: {settings.current_delta_api_key[:8]}..." if settings.current_delta_api_key else "   API Key: Not configured")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to generate .env.local file: {e}")
        return False


def ensure_env_file_exists(settings) -> bool:
    """
    Ensure .env.local file exists and is up to date
    
    Args:
        settings: The settings instance from config.py
        
    Returns:
        bool: True if file exists or was created successfully
    """
    backend_dir = Path(__file__).parent.parent
    env_file_path = backend_dir / ".env.local"
    
    if not env_file_path.exists():
        logger.info(".env.local file not found, generating from config.py...")
        return generate_env_local_from_config(settings)
    else:
        logger.info(f".env.local file exists at: {env_file_path}")
        # Optionally regenerate to ensure it's up to date
        logger.info("Regenerating .env.local to ensure consistency with config.py...")
        return generate_env_local_from_config(settings)

