"""
Order Model

Database model for storing order information and execution details.
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


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "PENDING"           # Order created, waiting to be submitted
    SUBMITTED = "SUBMITTED"       # Order submitted to exchange
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Order partially executed
    FILLED = "FILLED"             # Order completely executed
    CANCELLED = "CANCELLED"       # Order cancelled
    REJECTED = "REJECTED"         # Order rejected by exchange
    EXPIRED = "EXPIRED"           # Order expired
    FAILED = "FAILED"             # Order submission failed


class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "MARKET"             # Market order
    LIMIT = "LIMIT"               # Limit order
    STOP_LOSS = "STOP_LOSS"       # Stop loss order
    TAKE_PROFIT = "TAKE_PROFIT"   # Take profit order
    STOP_LIMIT = "STOP_LIMIT"     # Stop limit order
    TRAILING_STOP = "TRAILING_STOP"  # Trailing stop order


class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "BUY"                   # Buy order
    SELL = "SELL"                 # Sell order


class TimeInForce(str, Enum):
    """Time in force enumeration"""
    GTC = "GTC"                   # Good Till Cancelled
    IOC = "IOC"                   # Immediate Or Cancel
    FOK = "FOK"                   # Fill Or Kill
    GTD = "GTD"                   # Good Till Date


class Order(Base):
    """Order model for storing order execution details"""
    
    __tablename__ = "autonomous_orders"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Order details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(ENUM(OrderSide), nullable=False)
    order_type = Column(ENUM(OrderType), nullable=False)
    status = Column(ENUM(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    
    # Quantity and pricing
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=True)  # Null for market orders
    stop_price = Column(Numeric(20, 8), nullable=True)  # For stop orders
    trigger_price = Column(Numeric(20, 8), nullable=True)  # For conditional orders
    
    # Execution details
    filled_quantity = Column(Numeric(20, 8), nullable=False, default=0)
    remaining_quantity = Column(Numeric(20, 8), nullable=True)
    average_fill_price = Column(Numeric(20, 8), nullable=True)
    total_fees = Column(Numeric(20, 8), nullable=False, default=0)
    
    # Exchange details
    exchange_order_id = Column(String(100), nullable=True, index=True)
    exchange_client_order_id = Column(String(100), nullable=True)
    exchange_status = Column(String(50), nullable=True)
    exchange_error_message = Column(Text, nullable=True)
    
    # Order configuration
    time_in_force = Column(ENUM(TimeInForce), nullable=False, default=TimeInForce.GTC)
    reduce_only = Column(Boolean, nullable=False, default=False)
    post_only = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    trade_id = Column(String(50), ForeignKey('autonomous_trades.trade_id'), nullable=True, index=True)
    parent_order_id = Column(String(50), ForeignKey('autonomous_orders.order_id'), nullable=True)
    
    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Strategy and metadata
    strategy_name = Column(String(100), nullable=True)
    order_metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    # Flags
    is_paper_trade = Column(Boolean, nullable=False, default=True)
    is_autonomous = Column(Boolean, nullable=False, default=True)
    
    # Self-referential relationship for parent/child orders
    child_orders = relationship("Order", backref="parent_order", remote_side=[order_id])
    
    def __repr__(self):
        return f"<Order(id={self.order_id}, symbol={self.symbol}, side={self.side}, type={self.order_type}, status={self.status})>"
    
    @property
    def is_open(self) -> bool:
        """Check if order is still open"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_closed(self) -> bool:
        """Check if order is closed"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED, OrderStatus.FAILED]
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled"""
        return self.status == OrderStatus.PARTIALLY_FILLED
    
    @property
    def fill_percentage(self) -> float:
        """Get fill percentage"""
        if self.quantity and self.filled_quantity:
            return float(self.filled_quantity) / float(self.quantity) * 100
        return 0.0
    
    @property
    def total_value(self) -> Optional[float]:
        """Calculate total order value"""
        if self.average_fill_price and self.filled_quantity:
            return float(self.average_fill_price) * float(self.filled_quantity)
        elif self.price and self.quantity:
            return float(self.price) * float(self.quantity)
        return None
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get order duration in seconds"""
        if self.submitted_at:
            end_time = self.filled_at or self.cancelled_at or datetime.utcnow()
            return int((end_time - self.submitted_at).total_seconds())
        return None
    
    def update_fill(self, filled_qty: float, fill_price: float, fees: float = 0) -> None:
        """Update order fill information"""
        self.filled_quantity = Decimal(str(filled_qty))
        self.remaining_quantity = self.quantity - self.filled_quantity
        
        # Calculate average fill price
        if self.average_fill_price is None:
            self.average_fill_price = Decimal(str(fill_price))
        else:
            # Weighted average
            total_filled_value = float(self.average_fill_price) * float(self.filled_quantity - Decimal(str(filled_qty)))
            new_fill_value = fill_price * filled_qty
            self.average_fill_price = Decimal(str((total_filled_value + new_fill_value) / float(self.filled_quantity)))
        
        self.total_fees += Decimal(str(fees))
        
        # Update status
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.filled_at = datetime.utcnow()
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.updated_at = datetime.utcnow()
    
    def cancel(self, reason: str = None) -> None:
        """Cancel the order"""
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if reason and self.order_metadata:
            import json
            metadata = json.loads(self.order_metadata) if self.order_metadata else {}
            metadata['cancel_reason'] = reason
            self.order_metadata = json.dumps(metadata)
    
    def to_dict(self) -> dict:
        """Convert order to dictionary"""
        return {
            "id": str(self.id),
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value if self.side else None,
            "order_type": self.order_type.value if self.order_type else None,
            "status": self.status.value if self.status else None,
            "quantity": float(self.quantity) if self.quantity else None,
            "price": float(self.price) if self.price else None,
            "stop_price": float(self.stop_price) if self.stop_price else None,
            "trigger_price": float(self.trigger_price) if self.trigger_price else None,
            "filled_quantity": float(self.filled_quantity) if self.filled_quantity else None,
            "remaining_quantity": float(self.remaining_quantity) if self.remaining_quantity else None,
            "average_fill_price": float(self.average_fill_price) if self.average_fill_price else None,
            "total_fees": float(self.total_fees) if self.total_fees else None,
            "exchange_order_id": self.exchange_order_id,
            "exchange_client_order_id": self.exchange_client_order_id,
            "exchange_status": self.exchange_status,
            "exchange_error_message": self.exchange_error_message,
            "time_in_force": self.time_in_force.value if self.time_in_force else None,
            "reduce_only": self.reduce_only,
            "post_only": self.post_only,
            "trade_id": self.trade_id,
            "parent_order_id": self.parent_order_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "strategy_name": self.strategy_name,
            "order_metadata": self.order_metadata,
            "is_paper_trade": self.is_paper_trade,
            "is_autonomous": self.is_autonomous,
            "is_open": self.is_open,
            "is_closed": self.is_closed,
            "is_filled": self.is_filled,
            "is_partially_filled": self.is_partially_filled,
            "fill_percentage": self.fill_percentage,
            "total_value": self.total_value,
            "duration_seconds": self.duration_seconds
        }


class OrderExecution(Base):
    """Order execution model for tracking individual fills"""
    
    __tablename__ = "autonomous_order_executions"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Order reference
    order_id = Column(String(50), ForeignKey('autonomous_orders.order_id'), nullable=False, index=True)
    
    # Execution details
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    fees = Column(Numeric(20, 8), nullable=False, default=0)
    
    # Exchange details
    exchange_execution_id = Column(String(100), nullable=True)
    exchange_trade_id = Column(String(100), nullable=True)
    
    # Timing
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Flags
    is_maker = Column(Boolean, nullable=True)  # True if maker, False if taker
    
    # Relationship
    order = relationship("Order", backref="executions")
    
    def __repr__(self):
        return f"<OrderExecution(id={self.execution_id}, order_id={self.order_id}, qty={self.quantity}, price={self.price})>"
    
    @property
    def total_value(self) -> float:
        """Calculate execution value"""
        return float(self.quantity) * float(self.price)
    
    def to_dict(self) -> dict:
        """Convert execution to dictionary"""
        return {
            "id": str(self.id),
            "execution_id": self.execution_id,
            "order_id": self.order_id,
            "quantity": float(self.quantity) if self.quantity else None,
            "price": float(self.price) if self.price else None,
            "fees": float(self.fees) if self.fees else None,
            "exchange_execution_id": self.exchange_execution_id,
            "exchange_trade_id": self.exchange_trade_id,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_maker": self.is_maker,
            "total_value": self.total_value
        }

