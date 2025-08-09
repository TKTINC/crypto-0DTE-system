"""
Health Service

Provides health check functionality for the application and its dependencies.
"""

import asyncio
import time
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HealthService:
    """Service for monitoring application health"""
    
    def __init__(self):
        self.start_time = time.time()
        self.health_checks = {}
    
    async def initialize(self):
        """Initialize the health service"""
        logger.info("Initializing HealthService...")
        
        # Perform initial health checks
        try:
            # Test database connectivity
            db_health = await self.check_database_health()
            self.health_checks['database'] = db_health
            
            # Test Redis connectivity  
            redis_health = await self.check_redis_health()
            self.health_checks['redis'] = redis_health
            
            logger.info("HealthService initialized successfully")
            
        except Exception as e:
            logger.warning(f"Some health checks failed during initialization: {e}")
            # Don't fail initialization if health checks fail
            pass
    
    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity with real implementation"""
        start_time = time.time()
        try:
            from app.database import get_db
            from sqlalchemy import text
            
            # Use async session for database health check
            async for db in get_db():
                try:
                    # Execute a simple query and measure latency
                    result = await db.execute(text("SELECT 1 as health_check, version() as db_version"))
                    row = result.fetchone()
                    
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    return {
                        "status": "healthy",
                        "response_time_ms": round(response_time_ms, 2),
                        "message": "Database connection successful",
                        "details": {
                            "version": str(row.db_version) if row else "unknown",
                            "dialect": str(db.bind.dialect.name) if db.bind else "unknown"
                        }
                    }
                finally:
                    # Ensure session is closed
                    await db.close()
                    
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time_ms": round(response_time_ms, 2),
                "error": str(e),
                "message": "Database connection failed"
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity with real implementation"""
        start_time = time.time()
        try:
            import aioredis
            from app.config import settings
            
            # Create a short-lived Redis client
            redis = aioredis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            
            try:
                # Test basic connectivity with PING
                await redis.ping()
                
                # Test SET/GET/DEL operations with namespaced key
                test_key = "health_check:test"
                test_value = f"health_check_{int(time.time())}"
                
                # SET with 5 second TTL
                await redis.setex(test_key, 5, test_value)
                
                # GET to verify
                retrieved_value = await redis.get(test_key)
                if retrieved_value != test_value:
                    raise Exception("SET/GET operation failed")
                
                # DEL to cleanup
                await redis.delete(test_key)
                
                response_time_ms = (time.time() - start_time) * 1000
                
                # Get Redis info
                info = await redis.info()
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time_ms, 2),
                    "message": "Redis connection successful",
                    "details": {
                        "version": info.get("redis_version", "unknown"),
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory_human": info.get("used_memory_human", "unknown")
                    }
                }
                
            finally:
                await redis.close()
                
        except ImportError:
            # Redis not installed, return degraded status
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "status": "degraded",
                "response_time_ms": round(response_time_ms, 2),
                "message": "Redis client not installed",
                "details": {"note": "Install aioredis for Redis health checks"}
            }
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time_ms": round(response_time_ms, 2),
                "error": str(e),
                "message": "Redis connection failed"
            }
    
    async def check_exchange_health(self) -> Dict[str, Any]:
        """Check exchange API connectivity with real implementation"""
        start_time = time.time()
        try:
            from app.services.exchanges.delta_exchange import DeltaExchangeConnector
            from app.config import settings
            
            # Create Delta Exchange connector
            connector = DeltaExchangeConnector(paper_trading=True)  # Use testnet for health checks
            
            try:
                # Test unauthenticated endpoint first (instruments/heartbeat)
                instruments_response = await connector._make_request("GET", "/products")
                
                response_time_ms = (time.time() - start_time) * 1000
                
                # If we have valid API keys, test authenticated endpoint
                auth_status = "not_tested"
                if settings.DELTA_TESTNET_API_KEY and settings.DELTA_TESTNET_API_SECRET:
                    try:
                        account_response = await connector.get_account_balance()
                        auth_status = "authenticated" if account_response.get("success") else "auth_failed"
                    except Exception as auth_e:
                        auth_status = f"auth_error: {str(auth_e)[:50]}"
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time_ms, 2),
                    "message": "Exchange API connection successful",
                    "details": {
                        "exchange": "Delta Exchange",
                        "environment": "testnet",
                        "instruments_count": len(instruments_response.get("result", [])) if isinstance(instruments_response, dict) else 0,
                        "authentication": auth_status
                    }
                }
                
            finally:
                await connector.cleanup()
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Exchange health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time_ms": round(response_time_ms, 2),
                "error": str(e),
                "message": "Exchange API connection failed"
            }
    
    async def check_ai_service_health(self) -> Dict[str, Any]:
        """Check AI service connectivity with real implementation"""
        start_time = time.time()
        try:
            import openai
            from app.config import settings
            
            # Only test in non-production environments to avoid costs
            if settings.ENVIRONMENT == "production":
                return {
                    "status": "skipped",
                    "response_time_ms": 0,
                    "message": "AI service health check skipped in production",
                    "details": {"note": "Enable with ENABLE_AI_HEALTH_CHECK=true"}
                }
            
            # Test with a minimal request to avoid costs
            client = openai.AsyncOpenAI()
            
            try:
                # Use the models endpoint which is typically free/cheap
                models_response = await client.models.list()
                
                response_time_ms = (time.time() - start_time) * 1000
                
                # Count available models
                model_count = len(models_response.data) if hasattr(models_response, 'data') else 0
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time_ms, 2),
                    "message": "AI service connection successful",
                    "details": {
                        "provider": "OpenAI",
                        "models_available": model_count,
                        "api_version": getattr(client, '_version', 'unknown')
                    }
                }
                
            finally:
                await client.close()
                
        except ImportError:
            # OpenAI not installed, return degraded status
            response_time_ms = (time.time() - start_time) * 1000
            return {
                "status": "degraded",
                "response_time_ms": round(response_time_ms, 2),
                "message": "OpenAI client not installed",
                "details": {"note": "Install openai for AI health checks"}
            }
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"AI service health check failed: {e}")
            return {
                "status": "unhealthy",
                "response_time_ms": round(response_time_ms, 2),
                "error": str(e),
                "message": "AI service connection failed"
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        uptime_seconds = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime_seconds,
            "uptime_human": self._format_uptime(uptime_seconds),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": "production"  # Would get from config
        }
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.check_exchange_health(),
            self.check_ai_service_health(),
            return_exceptions=True
        )
        
        database_health, redis_health, exchange_health, ai_health = health_checks
        
        # Determine overall status
        all_healthy = all(
            isinstance(check, dict) and check.get("status") == "healthy"
            for check in health_checks
        )
        
        overall_status = "healthy" if all_healthy else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "system": self.get_system_info(),
            "dependencies": {
                "database": database_health if isinstance(database_health, dict) else {"status": "error", "error": str(database_health)},
                "redis": redis_health if isinstance(redis_health, dict) else {"status": "error", "error": str(redis_health)},
                "exchange": exchange_health if isinstance(exchange_health, dict) else {"status": "error", "error": str(exchange_health)},
                "ai_service": ai_health if isinstance(ai_health, dict) else {"status": "error", "error": str(ai_health)}
            }
        }
    
    async def is_ready(self) -> bool:
        """Check if the service is ready to handle requests"""
        try:
            # Check critical dependencies
            db_health = await self.check_database_health()
            
            # Service is ready if database is healthy
            # You can add more critical checks here
            return db_health.get("status") == "healthy"
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return False
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

# Global health service instance
health_service = HealthService()

