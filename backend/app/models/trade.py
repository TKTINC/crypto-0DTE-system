"""
Trade Model

Database model for storing trade information and execution details.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class TradeStatus(str, Enum):
    """Trade status enumeration"""
    PENDING = "PENDING"           # Trade signal generated, waiting for execution
    SUBMITTED = "SUBMITTED"       # Order submitted to exchange
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Order partially executed
    FILLED = "FILLED"             # Order completely executed
    CANCELLED = "CANCELLED"       # Order cancelled
    REJECTED = "REJECTED"         # Order rejected by exchange
    FAILED = "FAILED"             # Trade execution failed
    CLOSED = "CLOSED"             # Position closed


class TradeType(str, Enum):
    """Trade type enumeration"""
    BUY = "BUY"                   # Long position
    SELL = "SELL"                 # Short position


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "MARKET"             # Market order
    LIMIT = "LIMIT"               # Limit order
    STOP_LOSS = "STOP_LOSS"       # Stop loss order
    TAKE_PROFIT = "TAKE_PROFIT"   # Take profit order


class ExitReason(str, Enum):
    """Exit reason enumeration"""
    PROFIT_TARGET = "PROFIT_TARGET"       # Hit profit target
    STOP_LOSS = "STOP_LOSS"               # Hit stop loss
    TRAILING_STOP = "TRAILING_STOP"       # Trailing stop triggered
    TIME_LIMIT = "TIME_LIMIT"             # Maximum time reached
    MANUAL = "MANUAL"                     # Manual exit
    RISK_MANAGEMENT = "RISK_MANAGEMENT"   # Risk management exit
    MARKET_CLOSE = "MARKET_CLOSE"         # Market close exit
    EMERGENCY = "EMERGENCY"               # Emergency exit


class Trade(Base):
    """Trade model for storing trade execution details"""
    
    __tablename__ = "trades"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    trade_type = Column(ENUM(TradeType), nullable=False)
    status = Column(ENUM(TradeStatus), nullable=False, default=TradeStatus.PENDING)
    
    # Signal information
    signal_id = Column(String(50), nullable=True, index=True)
    signal_confidence = Column(Numeric(5, 4), nullable=True)  # 0.0000 to 1.0000
    signal_reasoning = Column(Text, nullable=True)
    
    # Order details
    order_type = Column(ENUM(OrderType), nullable=False, default=OrderType.MARKET)
    quantity = Column(Numeric(20, 8), nullable=False)
    entry_price = Column(Numeric(20, 8), nullable=True)
    target_price = Column(Numeric(20, 8), nullable=True)
    stop_loss_price = Column(Numeric(20, 8), nullable=True)
    
    # Execution details
    exchange_order_id = Column(String(100), nullable=True, index=True)
    filled_quantity = Column(Numeric(20, 8), nullable=True, default=0)
    average_fill_price = Column(Numeric(20, 8), nullable=True)
    total_fees = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Exit details
    exit_price = Column(Numeric(20, 8), nullable=True)
    exit_reason = Column(ENUM(ExitReason), nullable=True)
    exit_order_id = Column(String(100), nullable=True)
    
    # P&L calculation
    realized_pnl = Column(Numeric(20, 8), nullable=True)
    unrealized_pnl = Column(Numeric(20, 8), nullable=True)
    pnl_percentage = Column(Numeric(10, 6), nullable=True)
    
    # Risk management
    risk_amount = Column(Numeric(20, 8), nullable=True)
    position_size_usd = Column(Numeric(20, 8), nullable=True)
    leverage = Column(Numeric(10, 2), nullable=True, default=1.0)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Strategy and metadata
    strategy_name = Column(String(100), nullable=True)
    strategy_version = Column(String(20), nullable=True)
    trade_metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    # Flags
    is_paper_trade = Column(Boolean, nullable=False, default=True)
    is_autonomous = Column(Boolean, nullable=False, default=True)
    
    def __repr__(self):
        return f"<Trade(id={self.trade_id}, symbol={self.symbol}, type={self.trade_type}, status={self.status})>"
    
    @property
    def is_open(self) -> bool:
        """Check if trade is still open"""
        return self.status in [TradeStatus.PENDING, TradeStatus.SUBMITTED, TradeStatus.PARTIALLY_FILLED, TradeStatus.FILLED]
    
    @property
    def is_closed(self) -> bool:
        """Check if trade is closed"""
        return self.status == TradeStatus.CLOSED
    
    @property
    def is_profitable(self) -> bool:
        """Check if trade is profitable"""
        if self.realized_pnl is not None:
            return float(self.realized_pnl) > 0
        return False
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get trade duration in seconds"""
        if self.filled_at and self.closed_at:
            return int((self.closed_at - self.filled_at).total_seconds())
        elif self.filled_at:
            return int((datetime.utcnow() - self.filled_at).total_seconds())
        return None
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary"""
        return {
            "id": str(self.id),
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "trade_type": self.trade_type.value if self.trade_type else None,
            "status": self.status.value if self.status else None,
            "signal_id": self.signal_id,
            "signal_confidence": float(self.signal_confidence) if self.signal_confidence else None,
            "signal_reasoning": self.signal_reasoning,
            "order_type": self.order_type.value if self.order_type else None,
            "quantity": float(self.quantity) if self.quantity else None,
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "target_price": float(self.target_price) if self.target_price else None,
            "stop_loss_price": float(self.stop_loss_price) if self.stop_loss_price else None,
            "exchange_order_id": self.exchange_order_id,
            "filled_quantity": float(self.filled_quantity) if self.filled_quantity else None,
            "average_fill_price": float(self.average_fill_price) if self.average_fill_price else None,
            "total_fees": float(self.total_fees) if self.total_fees else None,
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "exit_reason": self.exit_reason.value if self.exit_reason else None,
            "exit_order_id": self.exit_order_id,
            "realized_pnl": float(self.realized_pnl) if self.realized_pnl else None,
            "unrealized_pnl": float(self.unrealized_pnl) if self.unrealized_pnl else None,
            "pnl_percentage": float(self.pnl_percentage) if self.pnl_percentage else None,
            "risk_amount": float(self.risk_amount) if self.risk_amount else None,
            "position_size_usd": float(self.position_size_usd) if self.position_size_usd else None,
            "leverage": float(self.leverage) if self.leverage else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
            "trade_metadata": self.trade_metadata,
            "is_paper_trade": self.is_paper_trade,
            "is_autonomous": self.is_autonomous,
            "is_open": self.is_open,
            "is_closed": self.is_closed,
            "is_profitable": self.is_profitable,
            "duration_seconds": self.duration_seconds
        }


class Position(Base):
    """Position model for tracking open positions"""
    
    __tablename__ = "positions"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Position details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(ENUM(TradeType), nullable=False)  # LONG or SHORT
    quantity = Column(Numeric(20, 8), nullable=False)
    entry_price = Column(Numeric(20, 8), nullable=False)
    current_price = Column(Numeric(20, 8), nullable=True)
    
    # Risk management
    stop_loss_price = Column(Numeric(20, 8), nullable=True)
    take_profit_price = Column(Numeric(20, 8), nullable=True)
    trailing_stop_price = Column(Numeric(20, 8), nullable=True)
    trailing_stop_distance = Column(Numeric(10, 6), nullable=True)
    
    # P&L tracking
    unrealized_pnl = Column(Numeric(20, 8), nullable=True)
    unrealized_pnl_percentage = Column(Numeric(10, 6), nullable=True)
    max_profit = Column(Numeric(20, 8), nullable=True, default=0)
    max_loss = Column(Numeric(20, 8), nullable=True, default=0)
    
    # Position metadata
    trade_id = Column(String(50), ForeignKey('trades.trade_id'), nullable=False, index=True)
    strategy_name = Column(String(100), nullable=True)
    risk_amount = Column(Numeric(20, 8), nullable=True)
    
    # Timing
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Flags
    is_active = Column(Boolean, nullable=False, default=True)
    is_paper_trade = Column(Boolean, nullable=False, default=True)
    
    # Relationship
    trade = relationship("Trade", backref="position")
    
    def __repr__(self):
        return f"<Position(id={self.position_id}, symbol={self.symbol}, side={self.side}, quantity={self.quantity})>"
    
    @property
    def position_value(self) -> Optional[float]:
        """Calculate current position value"""
        if self.current_price and self.quantity:
            return float(self.quantity) * float(self.current_price)
        return None
    
    @property
    def duration_seconds(self) -> int:
        """Get position duration in seconds"""
        return int((datetime.utcnow() - self.opened_at).total_seconds())
    
    def calculate_pnl(self, current_price: float) -> tuple[float, float]:
        """Calculate unrealized P&L"""
        if self.side == TradeType.BUY:
            pnl = (current_price - float(self.entry_price)) * float(self.quantity)
        else:
            pnl = (float(self.entry_price) - current_price) * float(self.quantity)
        
        pnl_percentage = (pnl / (float(self.entry_price) * float(self.quantity))) * 100
        return pnl, pnl_percentage
    
    def to_dict(self) -> dict:
        """Convert position to dictionary"""
        return {
            "id": str(self.id),
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side.value if self.side else None,
            "quantity": float(self.quantity) if self.quantity else None,
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "current_price": float(self.current_price) if self.current_price else None,
            "stop_loss_price": float(self.stop_loss_price) if self.stop_loss_price else None,
            "take_profit_price": float(self.take_profit_price) if self.take_profit_price else None,
            "trailing_stop_price": float(self.trailing_stop_price) if self.trailing_stop_price else None,
            "trailing_stop_distance": float(self.trailing_stop_distance) if self.trailing_stop_distance else None,
            "unrealized_pnl": float(self.unrealized_pnl) if self.unrealized_pnl else None,
            "unrealized_pnl_percentage": float(self.unrealized_pnl_percentage) if self.unrealized_pnl_percentage else None,
            "max_profit": float(self.max_profit) if self.max_profit else None,
            "max_loss": float(self.max_loss) if self.max_loss else None,
            "trade_id": self.trade_id,
            "strategy_name": self.strategy_name,
            "risk_amount": float(self.risk_amount) if self.risk_amount else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_active": self.is_active,
            "is_paper_trade": self.is_paper_trade,
            "position_value": self.position_value,
            "duration_seconds": self.duration_seconds
        }

