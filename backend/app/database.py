"""
Crypto-0DTE-System Database Configuration

Database connection management for PostgreSQL, Redis, and InfluxDB.
Provides async database sessions and connection pooling.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

from app.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# POSTGRESQL DATABASE
# =============================================================================

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    poolclass=NullPool if getattr(settings, 'TESTING', False) else None
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session():
    """
    Context manager to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# REDIS DATABASE
# =============================================================================

class RedisManager:
    """Redis connection manager"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def get_client(self) -> redis.Redis:
        """Get Redis client"""
        if not self.redis_client:
            await self.connect()
        return self.redis_client
    
    async def set_cache(self, key: str, value: str, ttl: int = None):
        """Set cache value"""
        client = await self.get_client()
        if ttl:
            await client.setex(key, ttl, value)
        else:
            await client.set(key, value)
    
    async def get_cache(self, key: str) -> Optional[str]:
        """Get cache value"""
        client = await self.get_client()
        return await client.get(key)
    
    async def delete_cache(self, key: str):
        """Delete cache value"""
        client = await self.get_client()
        await client.delete(key)
    
    async def publish(self, channel: str, message: str):
        """Publish message to channel"""
        client = await self.get_client()
        await client.publish(channel, message)
    
    async def subscribe(self, channel: str):
        """Subscribe to channel"""
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis() -> redis.Redis:
    """
    Dependency to get Redis client.
    
    Returns:
        redis.Redis: Redis client
    """
    return await redis_manager.get_client()


# =============================================================================
# INFLUXDB DATABASE
# =============================================================================

class InfluxDBManager:
    """InfluxDB connection manager"""
    
    def __init__(self):
        self.client: Optional[InfluxDBClientAsync] = None
        self.write_api = None
        self.query_api = None
    
    async def connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClientAsync(
                url=settings.INFLUXDB_URL,
                token=settings.INFLUXDB_TOKEN,
                org=settings.INFLUXDB_ORG
            )
            
            # Get APIs
            self.write_api = self.client.write_api()
            self.query_api = self.client.query_api()
            
            # Test connection
            health = await self.client.health()
            if health.status == "pass":
                logger.info("Connected to InfluxDB successfully")
            else:
                raise Exception(f"InfluxDB health check failed: {health.message}")
                
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from InfluxDB"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from InfluxDB")
    
    async def get_client(self) -> InfluxDBClientAsync:
        """Get InfluxDB client"""
        if not self.client:
            await self.connect()
        return self.client
    
    async def write_point(self, point):
        """Write a single point to InfluxDB"""
        if not self.write_api:
            await self.connect()
        await self.write_api.write(
            bucket=settings.INFLUXDB_BUCKET,
            org=settings.INFLUXDB_ORG,
            record=point
        )
    
    async def write_points(self, points):
        """Write multiple points to InfluxDB"""
        if not self.write_api:
            await self.connect()
        await self.write_api.write(
            bucket=settings.INFLUXDB_BUCKET,
            org=settings.INFLUXDB_ORG,
            record=points
        )
    
    async def query(self, query: str):
        """Execute query on InfluxDB"""
        if not self.query_api:
            await self.connect()
        return await self.query_api.query(query, org=settings.INFLUXDB_ORG)


# Global InfluxDB manager instance
influxdb_manager = InfluxDBManager()


async def get_influxdb() -> InfluxDBClientAsync:
    """
    Dependency to get InfluxDB client.
    
    Returns:
        InfluxDBClientAsync: InfluxDB client
    """
    return await influxdb_manager.get_client()


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

async def init_databases():
    """Initialize all database connections"""
    logger.info("Initializing database connections...")
    
    try:
        # Test PostgreSQL connection
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL connection established")
        
        # Connect to Redis
        await redis_manager.connect()
        
        # Connect to InfluxDB
        await influxdb_manager.connect()
        
        logger.info("All database connections initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
        raise


async def close_databases():
    """Close all database connections"""
    logger.info("Closing database connections...")
    
    try:
        # Close PostgreSQL engine
        await engine.dispose()
        logger.info("PostgreSQL connection closed")
        
        # Disconnect from Redis
        await redis_manager.disconnect()
        
        # Disconnect from InfluxDB
        await influxdb_manager.disconnect()
        
        logger.info("All database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing databases: {e}")


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

async def check_postgresql_health() -> bool:
    """Check PostgreSQL health"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False


async def check_redis_health() -> bool:
    """Check Redis health"""
    try:
        client = await redis_manager.get_client()
        await client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


async def check_influxdb_health() -> bool:
    """Check InfluxDB health"""
    try:
        client = await influxdb_manager.get_client()
        health = await client.health()
        return health.status == "pass"
    except Exception as e:
        logger.error(f"InfluxDB health check failed: {e}")
        return False


async def get_database_health() -> dict:
    """Get health status of all databases"""
    return {
        "postgresql": await check_postgresql_health(),
        "redis": await check_redis_health(),
        "influxdb": await check_influxdb_health()
    }

