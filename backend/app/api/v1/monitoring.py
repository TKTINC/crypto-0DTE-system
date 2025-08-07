"""
Monitoring API Endpoints

Provides system monitoring and metrics functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import psutil
import time

from app.database import get_db

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Pydantic models for API responses
class SystemMetricsResponse(BaseModel):
    cpu_usage: float
    memory_usage: float
    api_response_time: float
    db_connections: int
    active_threads: int
    disk_usage: float
    network_io: Dict[str, float]
    
class ConnectionStatusResponse(BaseModel):
    database: bool
    redis: bool
    delta_exchange: bool
    openai: bool
    
@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(db: Session = Depends(get_db)):
    """Get current system performance metrics"""
    try:
        # Get actual system metrics where possible
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Mock some metrics for development
        return SystemMetricsResponse(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            api_response_time=125.5,
            db_connections=5,
            active_threads=12,
            disk_usage=disk.percent,
            network_io={
                "bytes_sent": 1024000,
                "bytes_recv": 2048000
            }
        )
    except Exception as e:
        # Fallback to mock data if psutil fails
        return SystemMetricsResponse(
            cpu_usage=25.5,
            memory_usage=45.2,
            api_response_time=125.5,
            db_connections=5,
            active_threads=12,
            disk_usage=35.8,
            network_io={
                "bytes_sent": 1024000,
                "bytes_recv": 2048000
            }
        )

@router.get("/connections", response_model=ConnectionStatusResponse)
async def get_connection_status(db: Session = Depends(get_db)):
    """Get status of external service connections"""
    try:
        # Test database connection
        db_status = True
        try:
            db.execute("SELECT 1")
        except:
            db_status = False
        
        return ConnectionStatusResponse(
            database=db_status,
            redis=True,  # Mock for now
            delta_exchange=True,  # Mock for now
            openai=True  # Mock for now
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check connections: {str(e)}")

@router.get("/health")
async def monitoring_health():
    """Health check for monitoring service"""
    return {
        "status": "healthy",
        "monitoring_active": True,
        "timestamp": datetime.utcnow()
    }

