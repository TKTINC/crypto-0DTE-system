"""
Health Check API Endpoints
Provides health monitoring and system status for Railway deployment
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import os
from datetime import datetime
from typing import Dict, Any
import asyncio
import aiohttp

from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint for Railway deployment monitoring
    Returns 200 if service is running
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "crypto-0dte-backend",
        "version": "1.0.0"
    }

@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with dependency verification
    Checks database, Redis, and external API connectivity
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "crypto-0dte-backend",
        "version": "1.0.0",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database connectivity check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Redis connectivity check
    try:
        redis_client = redis.Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Delta Exchange API connectivity check
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.delta.exchange/v2/products",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    health_status["checks"]["delta_exchange"] = {
                        "status": "healthy",
                        "message": "Delta Exchange API accessible"
                    }
                else:
                    health_status["checks"]["delta_exchange"] = {
                        "status": "degraded",
                        "message": f"Delta Exchange API returned status {response.status}"
                    }
    except Exception as e:
        health_status["checks"]["delta_exchange"] = {
            "status": "unhealthy",
            "message": f"Delta Exchange API connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Environment variables check
    required_env_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET_KEY",
        "DELTA_EXCHANGE_API_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        health_status["checks"]["environment"] = {
            "status": "unhealthy",
            "message": f"Missing environment variables: {', '.join(missing_vars)}"
        }
        overall_healthy = False
    else:
        health_status["checks"]["environment"] = {
            "status": "healthy",
            "message": "All required environment variables present"
        }
    
    # Update overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check for Railway deployment
    Verifies service is ready to accept traffic
    """
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        
        # Check if required tables exist
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'portfolios', 'signals')
        """))
        
        tables = [row[0] for row in result.fetchall()]
        required_tables = ['users', 'portfolios', 'signals']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            return {
                "status": "not_ready",
                "message": f"Missing database tables: {', '.join(missing_tables)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "ready",
            "message": "Service is ready to accept traffic",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "message": f"Service not ready: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for Railway deployment
    Simple check to verify service is alive
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "unknown"  # Could be enhanced with actual uptime tracking
    }

