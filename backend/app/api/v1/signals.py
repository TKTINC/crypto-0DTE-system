"""
Trading Signals API Endpoints

Provides AI-generated trading signals and signal management functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.signal import Signal, SignalExecution, SignalPerformance
from app.services.ai_engine.signal_generator import SignalGeneratorService

router = APIRouter(prefix="/signals", tags=["signals"])

# Pydantic models for API responses
class SignalResponse(BaseModel):
    id: int
    symbol: str
    signal_type: str
    confidence: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    ai_reasoning: Optional[str]
    market_conditions: Optional[str]
    risk_assessment: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    status: str
    is_active: bool
    
    class Config:
        from_attributes = True

class SignalExecutionResponse(BaseModel):
    id: int
    signal_id: int
    execution_price: float
    quantity: float
    execution_type: str
    executed_at: datetime
    fees: Optional[float]
    pnl: Optional[float]
    
    class Config:
        from_attributes = True

class SignalPerformanceResponse(BaseModel):
    signal_id: int
    total_pnl: float
    win_rate: float
    total_trades: int
    avg_holding_time: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    
    class Config:
        from_attributes = True

class CreateSignalRequest(BaseModel):
    symbol: str
    signal_type: str
    confidence: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    expires_at: Optional[datetime] = None

@router.get("/", response_model=List[SignalResponse])
async def get_signals(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type (BUY, SELL, HOLD)"),
    status: Optional[str] = Query("ACTIVE", description="Filter by status"),
    limit: int = Query(50, description="Number of signals to return"),
    db: Session = Depends(get_db)
):
    """Get trading signals with optional filters"""
    try:
        query = db.query(Signal)
        
        if symbol:
            query = query.filter(Signal.symbol == symbol)
        if signal_type:
            query = query.filter(Signal.signal_type == signal_type)
        if status:
            query = query.filter(Signal.status == status)
        
        signals = query.order_by(Signal.created_at.desc()).limit(limit).all()
        return [SignalResponse.from_orm(signal) for signal in signals]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch signals: {str(e)}")

@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific signal by ID"""
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        return SignalResponse.from_orm(signal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch signal: {str(e)}")

@router.post("/", response_model=SignalResponse)
async def create_signal(
    signal_request: CreateSignalRequest,
    db: Session = Depends(get_db)
):
    """Create a new trading signal"""
    try:
        signal = Signal(
            symbol=signal_request.symbol,
            signal_type=signal_request.signal_type,
            confidence=signal_request.confidence,
            target_price=signal_request.target_price,
            stop_loss=signal_request.stop_loss,
            take_profit=signal_request.take_profit,
            expires_at=signal_request.expires_at,
            created_at=datetime.utcnow(),
            status="ACTIVE",
            is_active=True
        )
        
        db.add(signal)
        db.commit()
        db.refresh(signal)
        
        return SignalResponse.from_orm(signal)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create signal: {str(e)}")

@router.post("/generate/{symbol}")
async def generate_ai_signal(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Generate AI-powered trading signal for a symbol"""
    try:
        signal_generator = SignalGeneratorService()
        signal_data = await signal_generator.generate_signal(symbol)
        
        signal = Signal(
            symbol=symbol,
            signal_type=signal_data['signal_type'],
            confidence=signal_data['confidence'],
            target_price=signal_data.get('target_price'),
            stop_loss=signal_data.get('stop_loss'),
            take_profit=signal_data.get('take_profit'),
            ai_reasoning=signal_data.get('reasoning'),
            market_conditions=signal_data.get('market_conditions'),
            risk_assessment=signal_data.get('risk_assessment'),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            status="ACTIVE",
            is_active=True
        )
        
        db.add(signal)
        db.commit()
        db.refresh(signal)
        
        return SignalResponse.from_orm(signal)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate signal: {str(e)}")

@router.get("/{signal_id}/executions", response_model=List[SignalExecutionResponse])
async def get_signal_executions(
    signal_id: int,
    db: Session = Depends(get_db)
):
    """Get executions for a specific signal"""
    try:
        executions = db.query(SignalExecution).filter(
            SignalExecution.signal_id == signal_id
        ).order_by(SignalExecution.executed_at.desc()).all()
        
        return [SignalExecutionResponse.from_orm(execution) for execution in executions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch executions: {str(e)}")

@router.get("/{signal_id}/performance", response_model=SignalPerformanceResponse)
async def get_signal_performance(
    signal_id: int,
    db: Session = Depends(get_db)
):
    """Get performance metrics for a specific signal"""
    try:
        performance = db.query(SignalPerformance).filter(
            SignalPerformance.signal_id == signal_id
        ).first()
        
        if not performance:
            raise HTTPException(status_code=404, detail="Performance data not found")
        
        return SignalPerformanceResponse.from_orm(performance)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance: {str(e)}")

@router.put("/{signal_id}/status")
async def update_signal_status(
    signal_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """Update signal status (ACTIVE, EXECUTED, EXPIRED, CANCELLED)"""
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        valid_statuses = ["ACTIVE", "EXECUTED", "EXPIRED", "CANCELLED"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        signal.status = status
        signal.is_active = status == "ACTIVE"
        
        db.commit()
        
        return {"message": f"Signal {signal_id} status updated to {status}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update signal: {str(e)}")

@router.get("/performance/summary")
async def get_performance_summary(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get overall signal performance summary"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(Signal).filter(Signal.created_at >= start_date)
        if symbol:
            query = query.filter(Signal.symbol == symbol)
        
        signals = query.all()
        
        total_signals = len(signals)
        active_signals = len([s for s in signals if s.status == "ACTIVE"])
        executed_signals = len([s for s in signals if s.status == "EXECUTED"])
        
        # Calculate basic metrics
        avg_confidence = sum(s.confidence for s in signals) / total_signals if total_signals > 0 else 0
        
        return {
            "total_signals": total_signals,
            "active_signals": active_signals,
            "executed_signals": executed_signals,
            "avg_confidence": round(avg_confidence, 3),
            "period_days": days,
            "symbol": symbol or "ALL"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance summary: {str(e)}")

@router.get("/health")
async def signals_health():
    """Health check for signals service"""
    return {
        "status": "healthy",
        "service": "signals",
        "timestamp": datetime.utcnow()
    }

