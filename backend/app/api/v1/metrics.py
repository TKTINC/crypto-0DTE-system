"""
Metrics API

Provides Prometheus metrics endpoint for monitoring and observability.
"""

from fastapi import APIRouter, Response
from app.services.metrics_service import metrics_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/metrics")
async def get_metrics():
    """
    Export Prometheus metrics
    
    Returns metrics in Prometheus format for scraping by monitoring systems.
    """
    try:
        metrics_data = metrics_service.export_metrics()
        content_type = metrics_service.get_content_type()
        
        return Response(
            content=metrics_data,
            media_type=content_type
        )
        
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        return Response(
            content=f"# Error exporting metrics: {e}\n",
            media_type="text/plain",
            status_code=500
        )

@router.get("/metrics/summary")
async def get_metrics_summary():
    """
    Get a summary of key metrics in JSON format for UI consumption
    """
    try:
        # This would typically query the metrics registry for current values
        # For now, return a basic summary structure
        return {
            "trading": {
                "orders_today": 0,
                "fills_today": 0,
                "avg_slippage_bps": 0.0
            },
            "risk": {
                "portfolio_value_usd": 0.0,
                "daily_pnl_usd": 0.0,
                "open_positions": 0,
                "trading_locked": False
            },
            "system": {
                "health_status": "unknown",
                "uptime_seconds": 0
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        return {
            "error": str(e),
            "message": "Failed to retrieve metrics summary"
        }

