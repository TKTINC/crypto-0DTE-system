"""
Crypto-0DTE-System Main Application

FastAPI application for the Crypto-0DTE-System, providing AI-powered
cryptocurrency trading capabilities for Delta Exchange.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import settings
from app.database import engine, get_db
from app.models import Base
from app.api.v1 import market_data, signals, portfolio, trading, autonomous, monitoring, metrics, admin, health
from app.services.websocket_manager import WebSocketManager
from app.services.health_service import HealthService

# Import autonomous trading services
from app.services.autonomous_trading_orchestrator import AutonomousTradingOrchestrator
from app.services.trade_execution_engine import TradeExecutionEngine
from app.services.position_manager import PositionManager
from app.services.risk_manager import RiskManager

from app.utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# WebSocket manager for real-time updates
websocket_manager = WebSocketManager()

# Health service
health_service = HealthService()

# Global autonomous trading services
autonomous_orchestrator = None
trade_execution_engine = None
position_manager = None
risk_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global autonomous_orchestrator, trade_execution_engine, position_manager, risk_manager
    
    # Startup
    logger.info("Starting Crypto-0DTE-System...")
    
    # Generate .env.local file from config.py settings
    logger.info("🔧 Generating environment configuration...")
    from app.utils.env_generator import ensure_env_file_exists
    env_generated = ensure_env_file_exists(settings)
    if env_generated:
        logger.info("✅ Environment configuration ready")
    else:
        logger.warning("⚠️ Environment configuration generation failed, using existing settings")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Autonomous Trading System with environment awareness
    try:
        logger.info("🤖 Initializing Autonomous Trading System...")
        
        # Determine paper trading mode from settings
        paper_trading = settings.PAPER_TRADING
        logger.info(f"Trading mode: {'PAPER TRADING' if paper_trading else 'LIVE TRADING'}")
        
        # Initialize Risk Manager (non-blocking for API failures)
        try:
            risk_manager = RiskManager(paper_trading=paper_trading)
            await risk_manager.initialize()
            logger.info("✅ Risk Manager initialized")
        except Exception as e:
            logger.warning(f"⚠️ Risk Manager initialization failed: {e}")
            risk_manager = None
        
        # Initialize Position Manager (non-blocking for API failures)
        try:
            position_manager = PositionManager(paper_trading=paper_trading)
            await position_manager.initialize()
            logger.info("✅ Position Manager initialized")
        except Exception as e:
            logger.warning(f"⚠️ Position Manager initialization failed: {e}")
            position_manager = None
        
        # Initialize Trade Execution Engine (non-blocking for API failures)
        try:
            trade_execution_engine = TradeExecutionEngine(paper_trading=paper_trading)
            await trade_execution_engine.initialize()
            logger.info("✅ Trade Execution Engine initialized")
        except Exception as e:
            logger.warning(f"⚠️ Trade Execution Engine initialization failed: {e}")
            trade_execution_engine = None
        
        # Initialize Autonomous Trading Orchestrator (non-blocking for API failures)
        try:
            autonomous_orchestrator = AutonomousTradingOrchestrator(paper_trading=paper_trading)
            await autonomous_orchestrator.initialize()
            logger.info("✅ Autonomous Trading Orchestrator initialized")
            
            # Start autonomous trading (non-blocking)
            await autonomous_orchestrator.start()
            logger.info("🚀 Autonomous Trading System ACTIVE")
        except Exception as e:
            logger.warning(f"⚠️ Autonomous Trading Orchestrator initialization failed: {e}")
            autonomous_orchestrator = None
        
        logger.info("✅ Autonomous Trading System startup completed (some services may have limited functionality)")
        
    except Exception as e:
        logger.error(f"❌ Critical error during Autonomous Trading System initialization: {e}")
        # Continue without autonomous trading - FastAPI server will still start
    
    logger.info("Crypto-0DTE-System started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Crypto-0DTE-System...")
    
    # Shutdown autonomous trading services
    try:
        if autonomous_orchestrator:
            await autonomous_orchestrator.stop()
            await autonomous_orchestrator.cleanup()
            logger.info("✅ Autonomous Trading Orchestrator stopped")
        
        if trade_execution_engine:
            await trade_execution_engine.cleanup()
            logger.info("✅ Trade Execution Engine stopped")
        
        if position_manager:
            await position_manager.cleanup()
            logger.info("✅ Position Manager stopped")
        
        if risk_manager:
            await risk_manager.cleanup()
            logger.info("✅ Risk Manager stopped")
            
    except Exception as e:
        logger.error(f"Error shutting down autonomous services: {e}")
    
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
    health.router,
    prefix="/api/v1",
    tags=["Health"]
)

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

app.include_router(
    metrics.router,
    prefix="/api/v1/metrics",
    tags=["Metrics"]
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["Admin"]
)

# Simple health endpoint for frontend compatibility
@app.get("/api/v1/health")
async def simple_health_check():
    """Simple health check endpoint that frontend expects"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "crypto-0dte-backend"
    }


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
# AUTONOMOUS TRADING ENDPOINTS
# =============================================================================

@app.get("/api/v1/autonomous/orchestrator/status")
async def get_orchestrator_status():
    """Get autonomous trading orchestrator status"""
    try:
        if autonomous_orchestrator:
            status = await autonomous_orchestrator.get_status()
            return status
        else:
            return {
                "status": "INACTIVE",
                "message": "Autonomous trading orchestrator not initialized",
                "timestamp": "N/A"
            }
    except Exception as e:
        logger.error(f"Failed to get orchestrator status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orchestrator status")


@app.post("/api/v1/autonomous/orchestrator/start")
async def start_orchestrator():
    """Start the autonomous trading orchestrator"""
    try:
        if autonomous_orchestrator:
            await autonomous_orchestrator.start()
            return {"message": "Autonomous trading orchestrator started", "status": "ACTIVE"}
        else:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    except Exception as e:
        logger.error(f"Failed to start orchestrator: {e}")
        raise HTTPException(status_code=500, detail="Failed to start orchestrator")


@app.post("/api/v1/autonomous/orchestrator/stop")
async def stop_orchestrator():
    """Stop the autonomous trading orchestrator"""
    try:
        if autonomous_orchestrator:
            await autonomous_orchestrator.stop()
            return {"message": "Autonomous trading orchestrator stopped", "status": "STOPPED"}
        else:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    except Exception as e:
        logger.error(f"Failed to stop orchestrator: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop orchestrator")


@app.get("/api/v1/autonomous/risk/summary")
async def get_risk_summary():
    """Get comprehensive risk summary"""
    try:
        if risk_manager:
            summary = await risk_manager.get_risk_summary()
            return summary
        else:
            raise HTTPException(status_code=503, detail="Risk manager not initialized")
    except Exception as e:
        logger.error(f"Failed to get risk summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get risk summary")


@app.get("/api/v1/autonomous/positions/analytics/{trade_id}")
async def get_position_analytics(trade_id: str):
    """Get analytics for a specific position"""
    try:
        if position_manager:
            analytics = await position_manager.get_position_analytics(trade_id)
            return analytics
        else:
            raise HTTPException(status_code=503, detail="Position manager not initialized")
    except Exception as e:
        logger.error(f"Failed to get position analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get position analytics")


@app.get("/api/v1/autonomous/positions/states")
async def get_all_position_states():
    """Get all position states for monitoring"""
    try:
        if position_manager:
            states = await position_manager.get_all_position_states()
            return states
        else:
            raise HTTPException(status_code=503, detail="Position manager not initialized")
    except Exception as e:
        logger.error(f"Failed to get position states: {e}")
        raise HTTPException(status_code=500, detail="Failed to get position states")


@app.post("/api/v1/autonomous/positions/{trade_id}/force-exit")
async def force_exit_position(trade_id: str, reason: str = "Manual"):
    """Force exit a position"""
    try:
        if position_manager:
            result = await position_manager.force_exit_position(trade_id, reason)
            return result
        else:
            raise HTTPException(status_code=503, detail="Position manager not initialized")
    except Exception as e:
        logger.error(f"Failed to force exit position: {e}")
        raise HTTPException(status_code=500, detail="Failed to force exit position")


@app.get("/api/v1/autonomous/execution/status")
async def get_execution_status():
    """Get trade execution engine status"""
    try:
        if trade_execution_engine:
            status = await trade_execution_engine.get_execution_status()
            return status
        else:
            raise HTTPException(status_code=503, detail="Trade execution engine not initialized")
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get execution status")


@app.get("/api/v1/autonomous/execution/queue")
async def get_execution_queue():
    """Get current execution queue"""
    try:
        if trade_execution_engine:
            queue = await trade_execution_engine.get_execution_queue()
            return queue
        else:
            raise HTTPException(status_code=503, detail="Trade execution engine not initialized")
    except Exception as e:
        logger.error(f"Failed to get execution queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to get execution queue")


@app.post("/api/v1/autonomous/risk/emergency-shutdown")
async def emergency_risk_shutdown():
    """Emergency risk shutdown - stop all trading"""
    try:
        if risk_manager:
            result = await risk_manager.emergency_risk_shutdown()
            return result
        else:
            raise HTTPException(status_code=503, detail="Risk manager not initialized")
    except Exception as e:
        logger.error(f"Failed to execute emergency shutdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute emergency shutdown")


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
    
    # Run the application with single process (no reload to prevent duplicates)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disabled to prevent multiple worker processes
        workers=1,     # Explicitly set to 1 worker
        log_level="info" if not settings.DEBUG else "debug"
    )

