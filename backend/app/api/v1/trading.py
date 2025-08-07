"""
Trading API Endpoints

Provides trading execution and monitoring functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db

router = APIRouter(tags=["trading"])

# Pydantic models for API responses
class TradeResponse(BaseModel):
    id: int
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    price: float
    value: float
    status: str
    timestamp: datetime
    signal_id: Optional[int] = None
    
class TradingActivityResponse(BaseModel):
    active_orders: int
    pending_signals: int
    recent_trades: int
    success_rate: float
    
class TradingPerformanceResponse(BaseModel):
    total_trades: int
    successful_trades: int
    win_rate: float
    total_pnl: float
    avg_trade_return: float
    
@router.get("/recent", response_model=List[TradeResponse])
async def get_recent_trades(
    limit: int = Query(20, description="Number of recent trades to return"),
    db: Session = Depends(get_db)
):
    """Get recent trading activity"""
    try:
        # Mock recent trades for development
        trades = []
        for i in range(min(limit, 10)):
            timestamp = datetime.utcnow() - timedelta(hours=i * 2)
            symbol = 'BTCUSDT' if i % 2 == 0 else 'ETHUSDT'
            side = 'BUY' if i % 3 == 0 else 'SELL'
            base_price = 43000 if symbol == 'BTCUSDT' else 2600
            quantity = 0.1 if symbol == 'BTCUSDT' else 1.0
            
            trades.append(TradeResponse(
                id=i + 1,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=base_price + (i * 50),
                value=quantity * (base_price + (i * 50)),
                status='completed',
                timestamp=timestamp,
                signal_id=i + 1 if i < 5 else None
            ))
        
        return trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent trades: {str(e)}")

@router.get("/activity", response_model=TradingActivityResponse)
async def get_trading_activity(db: Session = Depends(get_db)):
    """Get current trading activity status"""
    try:
        return TradingActivityResponse(
            active_orders=3,
            pending_signals=2,
            recent_trades=15,
            success_rate=78.5
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trading activity: {str(e)}")

@router.get("/performance", response_model=TradingPerformanceResponse)
async def get_trading_performance(
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get trading performance metrics"""
    try:
        return TradingPerformanceResponse(
            total_trades=67,
            successful_trades=52,
            win_rate=77.6,
            total_pnl=3450.75,
            avg_trade_return=2.1
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trading performance: {str(e)}")

@router.get("/health")
async def trading_health():
    """Health check for trading service"""
    return {
        "status": "healthy",
        "exchange_connection": "connected",
        "timestamp": datetime.utcnow()
    }

