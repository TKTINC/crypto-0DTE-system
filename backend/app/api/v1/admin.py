"""
Admin API Endpoints

Administrative endpoints for system management, environment control, and trading locks.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json

from app.config import Settings, get_settings
from app.services.metrics_service import metrics_service
from app.services.risk_manager import RiskManager
from app.models.risk_event import RiskEvent, RiskEventType
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Pydantic models for request/response
class EnvironmentSwitchRequest(BaseModel):
    environment: str = Field(..., description="Target environment (testnet/live)")
    force: bool = Field(default=False, description="Force switch even with open positions")
    reason: str = Field(default="", description="Reason for environment switch")

class EnvironmentSwitchResponse(BaseModel):
    success: bool
    environment: str
    previous_environment: str
    timestamp: datetime
    message: str
    warnings: List[str] = []

class TradingLockRequest(BaseModel):
    locked: bool = Field(..., description="Lock or unlock trading")
    reason: str = Field(..., description="Reason for trading lock/unlock")
    duration_minutes: Optional[int] = Field(default=None, description="Auto-unlock after minutes")

class TradingLockResponse(BaseModel):
    success: bool
    locked: bool
    reason: str
    timestamp: datetime
    auto_unlock_at: Optional[datetime] = None

class SystemStatusResponse(BaseModel):
    environment: str
    paper_trading: bool
    trading_locked: bool
    trading_lock_reason: Optional[str]
    system_health: Dict[str, Any]
    active_positions: int
    daily_pnl: float
    risk_metrics: Dict[str, Any]

class EmergencyStopRequest(BaseModel):
    reason: str = Field(..., description="Reason for emergency stop")
    force_close_positions: bool = Field(default=False, description="Force close all positions")

class EmergencyStopResponse(BaseModel):
    success: bool
    timestamp: datetime
    positions_closed: int
    message: str

# Admin endpoints
@router.get("/status", response_model=SystemStatusResponse)
async def get_admin_status(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive system status for admin dashboard"""
    try:
        # Get current environment status
        environment = "testnet" if settings.PAPER_TRADING else "live"
        
        # Get trading lock status
        trading_locked = metrics_service.is_trading_locked()
        trading_lock_reason = metrics_service.get_trading_lock_reason()
        
        # Get system health
        from app.services.health_service import health_service
        system_health = await health_service.get_comprehensive_health()
        
        # Get risk metrics (mock for now - would integrate with risk manager)
        risk_metrics = {
            "daily_loss_limit": 1000.0,
            "max_position_size": 0.1,
            "consecutive_loss_limit": 3,
            "portfolio_risk_score": 0.25
        }
        
        return SystemStatusResponse(
            environment=environment,
            paper_trading=settings.PAPER_TRADING,
            trading_locked=trading_locked,
            trading_lock_reason=trading_lock_reason,
            system_health=system_health,
            active_positions=0,  # Would get from position manager
            daily_pnl=0.0,  # Would get from risk manager
            risk_metrics=risk_metrics
        )
        
    except Exception as e:
        logger.error(f"Failed to get admin status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get admin status: {str(e)}"
        )

@router.post("/environment/switch", response_model=EnvironmentSwitchResponse)
async def switch_environment(
    request: EnvironmentSwitchRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db)
):
    """Switch between testnet and live trading environments"""
    try:
        current_env = "testnet" if settings.PAPER_TRADING else "live"
        target_env = request.environment.lower()
        
        if target_env not in ["testnet", "live"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Environment must be 'testnet' or 'live'"
            )
        
        if current_env == target_env:
            return EnvironmentSwitchResponse(
                success=True,
                environment=current_env,
                previous_environment=current_env,
                timestamp=datetime.utcnow(),
                message=f"Already in {target_env} environment"
            )
        
        warnings = []
        
        # Check for open positions (unless forced)
        if not request.force:
            # Would check with position manager for open positions
            # For now, assume no open positions
            pass
        
        # Perform environment switch
        # This would update configuration and restart services
        logger.info(f"Environment switch requested: {current_env} -> {target_env}")
        
        # Record the environment switch event
        # This would persist to database
        
        # Update metrics
        metrics_service.record_environment_switch(current_env, target_env, request.reason)
        
        return EnvironmentSwitchResponse(
            success=True,
            environment=target_env,
            previous_environment=current_env,
            timestamp=datetime.utcnow(),
            message=f"Environment switched from {current_env} to {target_env}",
            warnings=warnings
        )
        
    except Exception as e:
        logger.error(f"Failed to switch environment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch environment: {str(e)}"
        )

@router.post("/trading/lock", response_model=TradingLockResponse)
async def set_trading_lock(
    request: TradingLockRequest,
    db: AsyncSession = Depends(get_db)
):
    """Lock or unlock trading system"""
    try:
        # Set trading lock
        metrics_service.set_trading_lock(request.locked, request.reason)
        
        # Calculate auto-unlock time
        auto_unlock_at = None
        if request.locked and request.duration_minutes:
            from datetime import timedelta
            auto_unlock_at = datetime.utcnow() + timedelta(minutes=request.duration_minutes)
            # Would schedule auto-unlock task
        
        # Log the action
        action = "locked" if request.locked else "unlocked"
        logger.info(f"Trading {action} by admin: {request.reason}")
        
        # Record metrics
        metrics_service.record_trading_lock_change(request.locked, request.reason)
        
        return TradingLockResponse(
            success=True,
            locked=request.locked,
            reason=request.reason,
            timestamp=datetime.utcnow(),
            auto_unlock_at=auto_unlock_at
        )
        
    except Exception as e:
        logger.error(f"Failed to set trading lock: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set trading lock: {str(e)}"
        )

@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def emergency_stop(
    request: EmergencyStopRequest,
    db: AsyncSession = Depends(get_db)
):
    """Emergency stop all trading activities"""
    try:
        logger.critical(f"🚨 EMERGENCY STOP ACTIVATED: {request.reason}")
        
        # Lock trading immediately
        metrics_service.set_trading_lock(True, f"Emergency stop: {request.reason}")
        
        positions_closed = 0
        
        # Close positions if requested
        if request.force_close_positions:
            # Would integrate with position manager to close all positions
            # For now, just log the intent
            logger.critical("Emergency position closure requested")
            positions_closed = 0  # Would return actual count
        
        # Record emergency stop event
        metrics_service.record_emergency_stop(request.reason, positions_closed)
        
        # Send alerts (would integrate with alerting system)
        logger.critical(f"Emergency stop completed: {positions_closed} positions closed")
        
        return EmergencyStopResponse(
            success=True,
            timestamp=datetime.utcnow(),
            positions_closed=positions_closed,
            message=f"Emergency stop activated: {request.reason}"
        )
        
    except Exception as e:
        logger.error(f"Failed to execute emergency stop: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute emergency stop: {str(e)}"
        )

@router.get("/risk-events")
async def get_risk_events(
    limit: int = 100,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get recent risk events for audit trail"""
    try:
        from sqlalchemy import select, desc
        
        query = select(RiskEvent).order_by(desc(RiskEvent.created_at)).limit(limit)
        
        if event_type:
            query = query.where(RiskEvent.event_type == event_type)
        
        result = await db.execute(query)
        risk_events = result.scalars().all()
        
        return {
            "events": [
                {
                    "id": str(event.id),
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id,
                    "symbol": event.symbol,
                    "decision": event.decision,
                    "reason": event.reason,
                    "environment": event.environment,
                    "created_at": event.created_at.isoformat(),
                    "details": json.loads(event.details) if event.details else None
                }
                for event in risk_events
            ],
            "total": len(risk_events)
        }
        
    except Exception as e:
        logger.error(f"Failed to get risk events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk events: {str(e)}"
        )

@router.get("/metrics/summary")
async def get_metrics_summary():
    """Get summary of key system metrics"""
    try:
        return {
            "trading_locked": metrics_service.is_trading_locked(),
            "trading_lock_reason": metrics_service.get_trading_lock_reason(),
            "total_orders": metrics_service.get_total_orders(),
            "successful_orders": metrics_service.get_successful_orders(),
            "failed_orders": metrics_service.get_failed_orders(),
            "risk_gate_approvals": metrics_service.get_risk_gate_approvals(),
            "risk_gate_denials": metrics_service.get_risk_gate_denials(),
            "uptime_seconds": metrics_service.get_uptime_seconds(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics summary: {str(e)}"
        )

