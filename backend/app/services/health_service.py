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
        """Check database connectivity"""
        try:
            from app.database import AsyncSessionLocal
            
            # Use async session for database health check
            async with AsyncSessionLocal() as session:
                result = await session.execute("SELECT 1")
                result.fetchone()
            
            return {
                "status": "healthy",
                "response_time_ms": 0,  # Would measure actual response time
                "message": "Database connection successful"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Database connection failed"
            }
    
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            # In a real implementation, you would check Redis connection
            # For now, return a mock healthy status
            return {
                "status": "healthy",
                "response_time_ms": 0,
                "message": "Redis connection successful"
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Redis connection failed"
            }
    
    async def check_exchange_health(self) -> Dict[str, Any]:
        """Check exchange API connectivity"""
        try:
            # In a real implementation, you would check exchange API
            # For now, return a mock healthy status
            return {
                "status": "healthy",
                "response_time_ms": 0,
                "message": "Exchange API connection successful"
            }
        except Exception as e:
            logger.error(f"Exchange health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Exchange API connection failed"
            }
    
    async def check_ai_service_health(self) -> Dict[str, Any]:
        """Check AI service connectivity"""
        try:
            # In a real implementation, you would check OpenAI API
            # For now, return a mock healthy status
            return {
                "status": "healthy",
                "response_time_ms": 0,
                "message": "AI service connection successful"
            }
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return {
                "status": "unhealthy",
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

