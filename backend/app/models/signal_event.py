"""
Signal Event Model

Tracks all signal generation and processing events for audit trail.
"""

from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid
from enum import Enum
from datetime import datetime

class SignalEventType(str, Enum):
    """Types of signal events"""
    SIGNAL_GENERATED = "signal_generated"
    SIGNAL_PROCESSED = "signal_processed"
    SIGNAL_ACCEPTED = "signal_accepted"
    SIGNAL_REJECTED = "signal_rejected"
    SIGNAL_EXPIRED = "signal_expired"
    SIGNAL_CANCELLED = "signal_cancelled"

class SignalEvent(Base):
    """Signal event model for audit trail"""
    
    __tablename__ = "signal_events"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(SQLEnum(SignalEventType), nullable=False, index=True)
    signal_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Links to Signal model
    correlation_id = Column(String(50), nullable=True, index=True)  # Links across events
    
    # Signal details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # buy/sell
    signal_type = Column(String(20), nullable=True)  # momentum/reversal/breakout
    
    # Signal strength
    confidence = Column(Float, nullable=True)
    strength = Column(Float, nullable=True)
    probability = Column(Float, nullable=True)
    
    # Market context
    price = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    
    # Processing details
    processing_time_ms = Column(Float, nullable=True)
    source = Column(String(50), nullable=True)  # ai/technical/fundamental
    
    # Decision context
    decision = Column(String(20), nullable=True)  # accepted/rejected/expired
    rejection_reason = Column(String(200), nullable=True)
    
    # Risk context
    portfolio_exposure_pct = Column(Float, nullable=True)
    symbol_exposure_pct = Column(Float, nullable=True)
    cooldown_remaining_seconds = Column(Float, nullable=True)
    
    # Environment context
    environment = Column(String(20), nullable=False, default="testnet")  # testnet/live
    paper_trading = Column(Boolean, nullable=False, default=True)
    
    # Additional context
    details = Column(Text, nullable=True)  # JSON string for additional context
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<SignalEvent(id={self.id}, type={self.event_type}, symbol={self.symbol})>"

