"""
Market Data API Endpoints

Provides real-time and historical market data from Delta Exchange
and other cryptocurrency exchanges.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.market_data import MarketData, OHLCV, OrderBook
from app.services.exchanges.delta_exchange import DeltaExchangeService

router = APIRouter(prefix="/market-data", tags=["market-data"])

# Pydantic models for API responses
class MarketDataResponse(BaseModel):
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    timestamp: datetime
    
    class Config:
        from_attributes = True

class OHLCVResponse(BaseModel):
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    
    class Config:
        from_attributes = True

class OrderBookResponse(BaseModel):
    symbol: str
    bids: List[List[float]]
    asks: List[List[float]]
    timestamp: datetime
    
    class Config:
        from_attributes = True

@router.get("/symbols", response_model=List[str])
async def get_available_symbols():
    """Get list of available trading symbols"""
    try:
        delta_service = DeltaExchangeService()
        symbols = await delta_service.get_symbols()
        return symbols
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch symbols: {str(e)}")

@router.get("/price/{symbol}", response_model=MarketDataResponse)
async def get_current_price(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get current price for a symbol"""
    try:
        # Try to get from database first
        market_data = db.query(MarketData).filter(
            MarketData.symbol == symbol
        ).order_by(MarketData.timestamp.desc()).first()
        
        if market_data:
            return MarketDataResponse.from_orm(market_data)
        
        # If not in database, fetch from exchange
        delta_service = DeltaExchangeService()
        price_data = await delta_service.get_ticker(symbol)
        
        return MarketDataResponse(
            symbol=symbol,
            price=price_data.get('price', 0.0),
            volume_24h=price_data.get('volume_24h', 0.0),
            change_24h=price_data.get('change_24h', 0.0),
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price: {str(e)}")

@router.get("/ohlcv/{symbol}", response_model=List[OHLCVResponse])
async def get_ohlcv_data(
    symbol: str,
    interval: str = Query("1h", description="Time interval (1m, 5m, 15m, 1h, 4h, 1d)"),
    limit: int = Query(100, description="Number of candles to return"),
    db: Session = Depends(get_db)
):
    """Get OHLCV (candlestick) data for a symbol"""
    try:
        # Calculate start time based on limit and interval
        interval_minutes = {
            "1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440
        }
        
        if interval not in interval_minutes:
            raise HTTPException(status_code=400, detail="Invalid interval")
        
        start_time = datetime.utcnow() - timedelta(
            minutes=interval_minutes[interval] * limit
        )
        
        # Query database
        ohlcv_data = db.query(OHLCV).filter(
            OHLCV.symbol == symbol,
            OHLCV.interval == interval,
            OHLCV.timestamp >= start_time
        ).order_by(OHLCV.timestamp.desc()).limit(limit).all()
        
        if ohlcv_data:
            return [OHLCVResponse.from_orm(candle) for candle in ohlcv_data]
        
        # If not in database, fetch from exchange
        delta_service = DeltaExchangeService()
        candles = await delta_service.get_ohlcv(symbol, interval, limit)
        
        return [
            OHLCVResponse(
                symbol=symbol,
                open=candle[1],
                high=candle[2],
                low=candle[3],
                close=candle[4],
                volume=candle[5],
                timestamp=datetime.fromtimestamp(candle[0] / 1000)
            ) for candle in candles
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch OHLCV data: {str(e)}")

@router.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_order_book(
    symbol: str,
    depth: int = Query(20, description="Order book depth")
):
    """Get order book data for a symbol"""
    try:
        delta_service = DeltaExchangeService()
        orderbook = await delta_service.get_orderbook(symbol, depth)
        
        return OrderBookResponse(
            symbol=symbol,
            bids=orderbook.get('bids', []),
            asks=orderbook.get('asks', []),
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch order book: {str(e)}")

@router.get("/health")
async def market_data_health():
    """Health check for market data service"""
    try:
        delta_service = DeltaExchangeService()
        status = await delta_service.health_check()
        return {
            "status": "healthy",
            "exchange_status": status,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

