"""
Signal Models for Crypto-0DTE-System

SQLAlchemy models for trading signals, executions, and performance tracking.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SignalType(str, Enum):
    """Signal type enumeration"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStatus(str, Enum):
    """Signal status enumeration"""
    ACTIVE = "ACTIVE"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RiskLevel(str, Enum):
    """Risk level enumeration"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Signal(Base):
    """
    Trading signal model for storing AI-generated trading recommendations.
    """
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # e.g., "BTC-USDT"
    signal_type = Column(ENUM(SignalType), nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    # AI Analysis
    ai_reasoning = Column(Text, nullable=True)
    market_conditions = Column(Text, nullable=True)
    risk_assessment = Column(ENUM(RiskLevel), nullable=True)  # LOW, MEDIUM, HIGH
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(ENUM(SignalStatus), default=SignalStatus.ACTIVE)  # ACTIVE, EXECUTED, EXPIRED, CANCELLED
    is_active = Column(Boolean, default=True)
    
    # Relationships
    executions = relationship("SignalExecution", back_populates="signal")
    performance = relationship("SignalPerformance", back_populates="signal", uselist=False)

    def __repr__(self):
        return f"<Signal(id={self.id}, symbol={self.symbol}, type={self.signal_type}, confidence={self.confidence})>"


class SignalExecution(Base):
    """
    Signal execution model for tracking when and how signals are executed.
    """
    __tablename__ = "signal_executions"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    
    # Execution Details
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    execution_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    execution_type = Column(String(20), nullable=False)  # "MARKET", "LIMIT", "STOP"
    
    # Exchange Information
    exchange_order_id = Column(String(100), nullable=True)
    exchange_name = Column(String(50), nullable=False, default="DELTA_EXCHANGE")
    
    # Fees and Costs
    commission = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)  # Difference between expected and actual price
    
    # Status
    status = Column(String(20), default="PENDING")  # "PENDING", "FILLED", "PARTIAL", "CANCELLED", "FAILED"
    error_message = Column(Text, nullable=True)
    
    # Relationships
    signal = relationship("Signal", back_populates="executions")

    def __repr__(self):
        return f"<SignalExecution(id={self.id}, signal_id={self.signal_id}, price={self.execution_price}, status={self.status})>"


class SignalPerformance(Base):
    """
    Signal performance tracking model for analyzing signal accuracy and profitability.
    """
    __tablename__ = "signal_performance"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False, unique=True)
    
    # Performance Metrics
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    pnl_absolute = Column(Float, default=0.0)  # Profit/Loss in absolute terms
    pnl_percentage = Column(Float, default=0.0)  # Profit/Loss as percentage
    
    # Timing Metrics
    signal_duration = Column(Integer, nullable=True)  # Duration in minutes
    time_to_execution = Column(Integer, nullable=True)  # Time from signal to execution in minutes
    
    # Accuracy Metrics
    direction_correct = Column(Boolean, nullable=True)  # Was the direction prediction correct?
    target_hit = Column(Boolean, default=False)  # Was the target price reached?
    stop_loss_hit = Column(Boolean, default=False)  # Was the stop loss triggered?
    
    # Risk Metrics
    max_drawdown = Column(Float, default=0.0)  # Maximum adverse movement
    max_favorable = Column(Float, default=0.0)  # Maximum favorable movement
    
    # Analysis
    performance_grade = Column(String(5), nullable=True)  # "A+", "A", "B+", "B", "C+", "C", "D", "F"
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    signal = relationship("Signal", back_populates="performance")

    def __repr__(self):
        return f"<SignalPerformance(id={self.id}, signal_id={self.signal_id}, pnl={self.pnl_percentage}%, grade={self.performance_grade})>"

    def calculate_performance_grade(self):
        """Calculate performance grade based on PnL and accuracy."""
        if self.pnl_percentage is None:
            return None
            
        if self.pnl_percentage >= 5.0 and self.direction_correct:
            return "A+"
        elif self.pnl_percentage >= 3.0 and self.direction_correct:
            return "A"
        elif self.pnl_percentage >= 1.0 and self.direction_correct:
            return "B+"
        elif self.pnl_percentage > 0 and self.direction_correct:
            return "B"
        elif self.pnl_percentage > 0 and not self.direction_correct:
            return "C+"
        elif self.pnl_percentage == 0:
            return "C"
        elif self.pnl_percentage > -2.0:
            return "D"
        else:
            return "F"

