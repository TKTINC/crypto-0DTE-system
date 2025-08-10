"""
Portfolio Models for Crypto-0DTE-System

SQLAlchemy models for portfolio management, positions, and transactions.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, DECIMAL
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
    
    # Portfolio Metrics (using DECIMAL for financial precision)
    total_value = Column(DECIMAL(20, 8), default=0.0)  # Current total portfolio value in USDT
    cash_balance = Column(DECIMAL(20, 8), default=0.0)  # Available cash in USDT
    invested_amount = Column(DECIMAL(20, 8), default=0.0)  # Total amount invested
    
    # Performance Metrics (using DECIMAL for financial precision)
    total_pnl = Column(DECIMAL(20, 8), default=0.0)  # Total profit/loss
    total_pnl_percentage = Column(DECIMAL(10, 4), default=0.0)  # Total P&L as percentage
    daily_pnl = Column(DECIMAL(20, 8), default=0.0)  # Today's P&L
    daily_pnl_percentage = Column(DECIMAL(10, 4), default=0.0)  # Today's P&L percentage
    
    # Risk Metrics (using DECIMAL for financial precision)
    max_drawdown = Column(DECIMAL(10, 4), default=0.0)  # Maximum drawdown experienced
    sharpe_ratio = Column(DECIMAL(10, 4), nullable=True)  # Risk-adjusted return metric
    volatility = Column(DECIMAL(10, 4), nullable=True)  # Portfolio volatility
    
    # Trading Metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(DECIMAL(10, 4), default=0.0)  # Percentage of winning trades
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_rebalanced = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    auto_trading_enabled = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    positions = relationship("PortfolioPosition", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")

    def __repr__(self):
        return f"<Portfolio(id={self.id}, name={self.name}, value={self.total_value}, pnl={self.total_pnl_percentage}%)>"


class PortfolioPosition(Base):
    """
    Portfolio position model for tracking individual cryptocurrency positions.
    """
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)  # e.g., "BTC-USDT"
    
    # Position Details (using DECIMAL for financial precision)
    quantity = Column(DECIMAL(20, 8), nullable=False)  # Current quantity held
    average_price = Column(DECIMAL(20, 8), nullable=False)  # Average entry price
    current_price = Column(DECIMAL(20, 8), nullable=False)  # Current market price
    
    # Cost Basis (using DECIMAL for financial precision)
    total_cost = Column(DECIMAL(20, 8), nullable=False)  # Total amount invested
    market_value = Column(DECIMAL(20, 8), nullable=False)  # Current market value
    
    # P&L Metrics (using DECIMAL for financial precision)
    unrealized_pnl = Column(DECIMAL(20, 8), default=0.0)  # Unrealized profit/loss
    unrealized_pnl_percentage = Column(DECIMAL(10, 4), default=0.0)  # Unrealized P&L percentage
    realized_pnl = Column(DECIMAL(20, 8), default=0.0)  # Realized profit/loss from partial sales
    
    # Position Metrics (using DECIMAL for financial precision)
    allocation_percentage = Column(DECIMAL(10, 4), default=0.0)  # Percentage of portfolio
    days_held = Column(Integer, default=0)  # Number of days position has been held
    
    # Risk Metrics (using DECIMAL for financial precision)
    stop_loss_price = Column(DECIMAL(20, 8), nullable=True)
    take_profit_price = Column(DECIMAL(20, 8), nullable=True)
    max_loss_percentage = Column(DECIMAL(10, 4), default=0.0)  # Maximum loss experienced
    max_gain_percentage = Column(DECIMAL(10, 4), default=0.0)  # Maximum gain experienced
    
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
    
    # Transaction Details (using DECIMAL for financial precision)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    symbol = Column(String(20), nullable=True, index=True)  # Null for cash transactions
    quantity = Column(DECIMAL(20, 8), nullable=False)
    price = Column(DECIMAL(20, 8), nullable=False)
    total_amount = Column(DECIMAL(20, 8), nullable=False)  # quantity * price
    
    # Fees and Costs (using DECIMAL for financial precision)
    commission = Column(DECIMAL(20, 8), default=0.0)
    exchange_fee = Column(DECIMAL(20, 8), default=0.0)
    other_fees = Column(DECIMAL(20, 8), default=0.0)
    total_fees = Column(DECIMAL(20, 8), default=0.0)
    
    # Exchange Information
    exchange_order_id = Column(String(100), nullable=True)
    exchange_name = Column(String(50), nullable=False, default="DELTA_EXCHANGE")
    
    # P&L (for sell transactions) (using DECIMAL for financial precision)
    realized_pnl = Column(DECIMAL(20, 8), nullable=True)  # Profit/loss realized from this transaction
    cost_basis = Column(DECIMAL(20, 8), nullable=True)  # Original cost basis for sold shares
    
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
    position = relationship("PortfolioPosition", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type.value}, symbol={self.symbol}, amount={self.total_amount})>"

