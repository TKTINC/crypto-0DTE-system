"""
Crypto-0DTE-System Main Application

FastAPI application for the Crypto-0DTE-System, providing AI-powered
cryptocurrency trading capabilities for Delta Exchange.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import settings
from app.database import engine, get_db
from app.models import Base
from app.api.v1 import market_data, signals, portfolio, trading, autonomous, monitoring
from app.services.websocket_manager import WebSocketManager
from app.services.health_service import HealthService
from app.utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# WebSocket manager for real-time updates
websocket_manager = WebSocketManager()

# Health service
health_service = HealthService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Crypto-0DTE-System...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize services
    await health_service.initialize()
    
    logger.info("Crypto-0DTE-System started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Crypto-0DTE-System...")
    await health_service.cleanup()
    logger.info("Crypto-0DTE-System shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Crypto-0DTE-System",
    description="AI-Powered BTC/ETH Trading Platform for Delta Exchange",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS if isinstance(settings.API_CORS_ORIGINS, list) else [settings.API_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "crypto-0dte-system"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status"""
    try:
        health_status = await health_service.get_detailed_health()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        is_ready = await health_service.is_ready()
        if is_ready:
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}


# =============================================================================
# API ROUTES
# =============================================================================

# Include API routers
app.include_router(
    market_data.router,
    prefix="/api/v1/market-data",
    tags=["Market Data"]
)

app.include_router(
    signals.router,
    prefix="/api/v1/signals",
    tags=["Trading Signals"]
)

app.include_router(
    portfolio.router,
    prefix="/api/v1/portfolio",
    tags=["Portfolio Management"]
)

app.include_router(
    trading.router,
    prefix="/api/v1/trading",
    tags=["Trading Execution"]
)

app.include_router(
    autonomous.router,
    prefix="/api/v1/autonomous",
    tags=["Autonomous Trading"]
)

app.include_router(
    monitoring.router,
    prefix="/api/v1/monitoring",
    tags=["System Monitoring"]
)


# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back for now - can be extended for client commands
            await websocket_manager.send_personal_message(
                f"Echo: {data}", websocket
            )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.websocket("/ws/market-data")
async def market_data_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time market data"""
    await websocket_manager.connect(websocket, channel="market_data")
    try:
        while True:
            # Send real-time market data updates
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, channel="market_data")


@app.websocket("/ws/signals")
async def signals_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time trading signals"""
    await websocket_manager.connect(websocket, channel="signals")
    try:
        while True:
            # Send real-time signal updates
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, channel="signals")


@app.websocket("/ws/portfolio")
async def portfolio_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time portfolio updates"""
    await websocket_manager.connect(websocket, channel="portfolio")
    try:
        while True:
            # Send real-time portfolio updates
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, channel="portfolio")


# =============================================================================
# SYSTEM INFORMATION ENDPOINTS
# =============================================================================

@app.get("/info")
async def system_info():
    """Get system information"""
    return {
        "name": "Crypto-0DTE-System",
        "version": "1.0.0",
        "description": "AI-Powered BTC/ETH Trading Platform for Delta Exchange",
        "environment": settings.ENVIRONMENT,
        "features": [
            "24/7 Autonomous Trading",
            "AI-Powered Signal Generation",
            "Multi-Strategy Approach",
            "Delta Exchange Integration",
            "Indian Regulatory Compliance",
            "Real-Time Learning"
        ],
        "supported_assets": ["BTC", "ETH"],
        "supported_strategies": [
            "BTC Lightning Scalp",
            "ETH DeFi Correlation",
            "BTC/ETH Cross-Asset Arbitrage",
            "Funding Rate Arbitrage",
            "Fear & Greed Contrarian"
        ]
    }


@app.get("/metrics")
async def system_metrics():
    """Get system performance metrics"""
    try:
        metrics = await health_service.get_system_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


# =============================================================================
# STATIC FILES (for serving frontend in production)
# =============================================================================

if settings.ENVIRONMENT == "production":
    app.mount("/static", StaticFiles(directory="static"), name="static")


# =============================================================================
# STARTUP EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Additional startup tasks"""
    logger.info("Performing additional startup tasks...")
    
    # Start background services if needed
    # This could include starting the data feed service, signal generator, etc.
    
    logger.info("Startup tasks completed")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this)
    port = int(os.getenv("PORT", 8000))
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )

