"""
Crypto-0DTE-System Database Models

SQLAlchemy models for the Crypto-0DTE-System database.
"""

from app.database import Base

# Import all models to ensure they are registered with SQLAlchemy
from .market_data import MarketData, CryptoPrice, OrderBook
from .signal import Signal, SignalExecution, SignalPerformance, SignalType, SignalStatus, RiskLevel
from .portfolio import Portfolio, Position, Transaction
from .user import User, UserProfile, UserSettings
from .compliance import TaxRecord, TDSRecord, ComplianceLog
from .risk_profile import RiskProfile, RiskMetrics

# Import autonomous trading models
from .trade import (
    Trade as AutonomousTrade, 
    Position as AutonomousPosition,
    TradeStatus, 
    TradeType, 
    ExitReason
)

from .order import (
    Order,
    OrderExecution,
    OrderStatus,
    OrderType,
    OrderSide,
    TimeInForce
)

# Import risk and signal event models
from .risk_event import RiskEvent, RiskEventType
from .signal_event import SignalEvent, SignalEventType

__all__ = [
    "Base",
    "MarketData",
    "CryptoPrice", 
    "OrderBook",
    "Signal",
    "SignalExecution",
    "SignalPerformance",
    "SignalType",
    "SignalStatus", 
    "RiskLevel",
    "Portfolio",
    "Position",
    "Transaction",
    "User",
    "UserProfile",
    "UserSettings",
    "TaxRecord",
    "TDSRecord",
    "ComplianceLog",
    "RiskProfile",
    "RiskMetrics",
    # Autonomous trading models
    "AutonomousTrade",
    "AutonomousPosition", 
    "TradeStatus",
    "TradeType",
    "ExitReason",
    # Order models
    "Order",
    "OrderExecution",
    "OrderStatus",
    "OrderType", 
    "OrderSide",
    "TimeInForce",
    # Risk and signal event models
    "RiskEvent",
    "RiskEventType",
    "SignalEvent",
    "SignalEventType"
]

