"""
Portfolio Models for Crypto-0DTE-System

SQLAlchemy models for portfolio management, positions, and transactions.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class TransactionType(enum.Enum):
    """Transaction type enumeration."""
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FEE = "FEE"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"


class PositionStatus(enum.Enum):
    """Position status enumeration."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"


class Portfolio(Base):
    """
    Portfolio model for tracking overall portfolio performance and metrics.
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False, default="Main Portfolio")
    
    # Portfolio Metrics
    total_value = Column(Float, default=0.0)  # Current total portfolio value in USDT
    cash_balance = Column(Float, default=0.0)  # Available cash in USDT
    invested_amount = Column(Float, default=0.0)  # Total amount invested
    
    # Performance Metrics
    total_pnl = Column(Float, default=0.0)  # Total profit/loss
    total_pnl_percentage = Column(Float, default=0.0)  # Total P&L as percentage
    daily_pnl = Column(Float, default=0.0)  # Today's P&L
    daily_pnl_percentage = Column(Float, default=0.0)  # Today's P&L percentage
    
    # Risk Metrics
    max_drawdown = Column(Float, default=0.0)  # Maximum drawdown experienced
    sharpe_ratio = Column(Float, nullable=True)  # Risk-adjusted return metric
    volatility = Column(Float, nullable=True)  # Portfolio volatility
    
    # Trading Metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)  # Percentage of winning trades
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_rebalanced = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    auto_trading_enabled = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")

    def __repr__(self):
        return f"<Portfolio(id={self.id}, name={self.name}, value={self.total_value}, pnl={self.total_pnl_percentage}%)>"


class Position(Base):
    """
    Position model for tracking individual cryptocurrency positions.
    """
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)  # e.g., "BTC-USDT"
    
    # Position Details
    quantity = Column(Float, nullable=False)  # Current quantity held
    average_price = Column(Float, nullable=False)  # Average entry price
    current_price = Column(Float, nullable=False)  # Current market price
    
    # Cost Basis
    total_cost = Column(Float, nullable=False)  # Total amount invested
    market_value = Column(Float, nullable=False)  # Current market value
    
    # P&L Metrics
    unrealized_pnl = Column(Float, default=0.0)  # Unrealized profit/loss
    unrealized_pnl_percentage = Column(Float, default=0.0)  # Unrealized P&L percentage
    realized_pnl = Column(Float, default=0.0)  # Realized profit/loss from partial sales
    
    # Position Metrics
    allocation_percentage = Column(Float, default=0.0)  # Percentage of portfolio
    days_held = Column(Integer, default=0)  # Number of days position has been held
    
    # Risk Metrics
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    max_loss_percentage = Column(Float, default=0.0)  # Maximum loss experienced
    max_gain_percentage = Column(Float, default=0.0)  # Maximum gain experienced
    
    # Status
    status = Column(SQLEnum(PositionStatus), default=PositionStatus.OPEN)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    transactions = relationship("Transaction", back_populates="position")

    def __repr__(self):
        return f"<Position(id={self.id}, symbol={self.symbol}, qty={self.quantity}, pnl={self.unrealized_pnl_percentage}%)>"


class Transaction(Base):
    """
    Transaction model for tracking all portfolio transactions.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)  # Null for cash transactions
    
    # Transaction Details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    symbol = Column(String(20), nullable=True, index=True)  # Null for cash transactions
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)  # quantity * price
    
    # Fees and Costs
    commission = Column(Float, default=0.0)
    exchange_fee = Column(Float, default=0.0)
    other_fees = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    
    # Exchange Information
    exchange_order_id = Column(String(100), nullable=True)
    exchange_name = Column(String(50), nullable=False, default="DELTA_EXCHANGE")
    
    # P&L (for sell transactions)
    realized_pnl = Column(Float, nullable=True)  # Profit/loss realized from this transaction
    cost_basis = Column(Float, nullable=True)  # Original cost basis for sold shares
    
    # Metadata
    notes = Column(Text, nullable=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)  # If transaction was from a signal
    
    # Timestamps
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    settlement_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Status
    status = Column(String(20), default="COMPLETED")  # "PENDING", "COMPLETED", "FAILED", "CANCELLED"
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
    position = relationship("Position", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type.value}, symbol={self.symbol}, amount={self.total_amount})>"

