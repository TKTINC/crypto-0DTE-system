"""
Risk Event Model

Tracks all risk management decisions and events for audit trail.
"""

from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid
from enum import Enum
from datetime import datetime

class RiskEventType(str, Enum):
    """Types of risk events"""
    SIGNAL_ACCEPTED = "signal_accepted"
    SIGNAL_REJECTED = "signal_rejected"
    ORDER_APPROVED = "order_approved"
    ORDER_DENIED = "order_denied"
    POSITION_LIMIT_BREACH = "position_limit_breach"
    DAILY_LOSS_LIMIT_BREACH = "daily_loss_limit_breach"
    DRAWDOWN_LIMIT_BREACH = "drawdown_limit_breach"
    TRADING_LOCKED = "trading_locked"
    TRADING_UNLOCKED = "trading_unlocked"
    EMERGENCY_STOP = "emergency_stop"

class RiskEvent(Base):
    """Risk event model for audit trail"""
    
    __tablename__ = "risk_events"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(SQLEnum(RiskEventType), nullable=False, index=True)
    correlation_id = Column(String(50), nullable=True, index=True)  # Links to orders/signals
    
    # Risk context
    symbol = Column(String(20), nullable=True, index=True)
    side = Column(String(10), nullable=True)  # buy/sell
    quantity = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    notional_usd = Column(Float, nullable=True)
    
    # Risk metrics at time of event
    portfolio_value_usd = Column(Float, nullable=True)
    daily_pnl_usd = Column(Float, nullable=True)
    total_exposure_usd = Column(Float, nullable=True)
    open_positions_count = Column(Float, nullable=True)
    
    # Decision details
    decision = Column(String(20), nullable=False)  # approved/denied/locked
    reason = Column(String(200), nullable=True)
    risk_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Environment context
    environment = Column(String(20), nullable=False, default="testnet")  # testnet/live
    paper_trading = Column(Boolean, nullable=False, default=True)
    
    # Additional context
    details = Column(Text, nullable=True)  # JSON string for additional context
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RiskEvent(id={self.id}, type={self.event_type}, decision={self.decision})>"

