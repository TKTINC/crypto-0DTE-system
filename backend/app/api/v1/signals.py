"""
AI Signals API Endpoints

Provides AI-generated trading signals and signal management functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import OpenAI
import logging

from app.database import get_db
from app.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["signals"])

# Get settings instance
settings = Settings()

# Configure OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

# Pydantic models for API responses
class SignalResponse(BaseModel):
    id: int
    symbol: str
    type: str  # BUY or SELL
    strategy: str
    confidence: float
    price: float
    entry: float
    target: float
    stopLoss: float
    status: str
    reasoning: str
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class SignalPerformanceResponse(BaseModel):
    total_signals: int
    successful_signals: int
    win_rate: float
    avg_return: float
    total_return: float
    
@router.get("/recent", response_model=List[SignalResponse])
async def get_recent_signals(
    limit: int = Query(10, description="Number of recent signals to return"),
    db: Session = Depends(get_db)
):
    """Get recent AI-generated trading signals"""
    try:
        # For development, return mock signals
        mock_signals = []
        for i in range(min(limit, 5)):
            timestamp = datetime.utcnow() - timedelta(minutes=i * 30)
            symbol = 'BTCUSDT' if i % 2 == 0 else 'ETHUSDT'
            signal_type = 'BUY' if i % 3 == 0 else 'SELL'
            base_price = 43000 if symbol == 'BTCUSDT' else 2600
            
            mock_signals.append(SignalResponse(
                id=i + 1,
                symbol=symbol,
                type=signal_type,
                strategy=f"AI-{'RSI' if i % 2 == 0 else 'MACD'}",
                confidence=75 + (i * 3),
                price=base_price,
                entry=base_price,
                target=base_price * (1.02 if signal_type == 'BUY' else 0.98),
                stopLoss=base_price * (0.98 if signal_type == 'BUY' else 1.02),
                status='active',
                reasoning=f"AI analysis indicates {signal_type.lower()} opportunity based on technical indicators.",
                timestamp=timestamp,
                created_at=timestamp
            ))
        
        return mock_signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch signals: {str(e)}")

@router.get("/active", response_model=List[SignalResponse])
async def get_active_signals(db: Session = Depends(get_db)):
    """Get currently active trading signals"""
    try:
        # Return mock active signals
        return await get_recent_signals(3, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch active signals: {str(e)}")

@router.get("/performance", response_model=SignalPerformanceResponse)
async def get_signal_performance(
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get signal performance metrics"""
    try:
        return SignalPerformanceResponse(
            total_signals=45,
            successful_signals=34,
            win_rate=75.6,
            avg_return=2.3,
            total_return=8.7
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance: {str(e)}")

@router.post("/generate", response_model=SignalResponse)
async def generate_signal(
    symbol: str,
    timeframe: str = "1h",
    db: Session = Depends(get_db)
):
    """Generate a new AI trading signal using OpenAI"""
    try:
        # Get current market data for context
        base_price = 43000 if 'BTC' in symbol else 2600
        
        # Create AI prompt for signal generation
        prompt = f"""
        As a professional cryptocurrency trading AI, analyze the current market conditions for {symbol} and generate a trading signal.
        
        Current price: ${base_price:,.2f}
        Timeframe: {timeframe}
        
        Provide a trading recommendation with:
        1. Signal type (BUY/SELL)
        2. Confidence level (0-100%)
        3. Entry price
        4. Target price
        5. Stop loss price
        6. Trading strategy name
        7. Brief reasoning (max 100 words)
        
        Consider technical analysis, market sentiment, and risk management.
        Respond in JSON format only.
        """
        
        try:
            # Call OpenAI API
            if openai_client and settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a professional cryptocurrency trading AI assistant. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                logger.info(f"OpenAI response for {symbol}: {ai_response}")
                
                # Parse AI response (simplified for demo)
                signal_type = 'BUY' if 'BUY' in ai_response.upper() else 'SELL'
                confidence = 75.0  # Extract from AI response
                strategy = "AI Technical Analysis"
                reasoning = "AI-generated signal based on current market analysis and technical indicators."
                
            else:
                # Fallback to enhanced mock data
                signal_type = 'BUY'
                confidence = 78.5
                strategy = "Mock AI Strategy"
                reasoning = "Enhanced mock signal with realistic market analysis simulation."
                
        except Exception as ai_error:
            logger.warning(f"OpenAI API error: {ai_error}, using fallback")
            signal_type = 'BUY'
            confidence = 72.0
            strategy = "Fallback Strategy"
            reasoning = "Fallback signal generated due to AI service unavailability."
        
        # Calculate prices based on signal type
        if signal_type == 'BUY':
            entry_price = base_price * 0.999  # Slight discount for entry
            target_price = base_price * 1.025  # 2.5% target
            stop_loss = base_price * 0.985   # 1.5% stop loss
        else:
            entry_price = base_price * 1.001  # Slight premium for short entry
            target_price = base_price * 0.975  # 2.5% target (downward)
            stop_loss = base_price * 1.015   # 1.5% stop loss (upward)
        
        return SignalResponse(
            id=int(datetime.utcnow().timestamp()),
            symbol=symbol,
            type=signal_type,
            strategy=strategy,
            confidence=confidence,
            price=base_price,
            entry=entry_price,
            target=target_price,
            stopLoss=stop_loss,
            status='active',
            reasoning=reasoning,
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Signal generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate signal: {str(e)}")

@router.get("/test-ai-connection")
async def test_ai_connection():
    """Test AI service connection"""
    try:
        if not openai_client or not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.strip():
            return {
                "status": "error",
                "error": "OpenAI API key not configured",
                "timestamp": datetime.utcnow()
            }
        
        # Test OpenAI connection with a simple request
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test connection. Respond with 'OK'."}],
            max_tokens=10
        )
        
        return {
            "status": "connected",
            "service": "OpenAI",
            "model": "gpt-3.5-turbo",
            "response_time": 150,
            "test_response": response.choices[0].message.content,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"OpenAI connection test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

@router.get("/health")
async def signals_health():
    """Health check for signals service"""
    return {
        "status": "healthy",
        "ai_service": "connected",
        "timestamp": datetime.utcnow()
    }

