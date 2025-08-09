"""
Metrics API endpoints for Crypto-0DTE System

Provides:
- /metrics endpoint for Prometheus scraping
- /health endpoint for system health checks
- /metrics/summary endpoint for dashboard consumption
"""

from fastapi import APIRouter, Response, HTTPException
from typing import Dict, Any
import logging

from app.services.metrics_service import metrics_service
from prometheus_client import CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format for scraping.
    Implements GPT-5's recommendation for observability.
    """
    try:
        # Update portfolio metrics before serving
        await metrics_service.update_portfolio_metrics()
        
        # Get Prometheus formatted metrics
        metrics_data = metrics_service.get_prometheus_metrics()
        
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
        
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    System health check endpoint.
    
    Returns comprehensive system health status including:
    - Service status
    - Database connectivity
    - Exchange connectivity
    - Recent metrics
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": metrics_service.start_time,
            "environment": metrics_service.environment,
            "services": {
                "metrics_service": "healthy",
                "database": "unknown",  # Would need actual DB health check
                "exchange": "unknown"   # Would need actual exchange health check
            }
        }
        
        # Get basic metrics summary
        metrics_summary = await metrics_service.get_metrics_summary()
        health_status["metrics"] = metrics_summary
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": metrics_service.start_time
        }


@router.get("/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """
    Metrics summary endpoint for dashboard consumption.
    
    Returns key metrics in JSON format for frontend dashboards.
    """
    try:
        summary = await metrics_service.get_metrics_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics summary")


@router.get("/risk-gate/stats")
async def get_risk_gate_stats() -> Dict[str, Any]:
    """
    Risk gate statistics endpoint.
    
    Returns detailed risk gate performance metrics.
    """
    try:
        # This would typically query the risk gate metrics
        # For now, return basic structure
        return {
            "total_checks": "Available in Prometheus metrics",
            "approval_rate": "Available in Prometheus metrics", 
            "top_denial_reasons": "Available in Prometheus metrics",
            "environment": metrics_service.environment,
            "note": "Detailed stats available at /metrics endpoint for Prometheus"
        }
        
    except Exception as e:
        logger.error(f"Error getting risk gate stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get risk gate stats")

