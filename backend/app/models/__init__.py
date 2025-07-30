"""
Crypto-0DTE-System Database Models

SQLAlchemy models for the Crypto-0DTE-System database.
"""

from app.database import Base

# Import all models to ensure they are registered with SQLAlchemy
from .market_data import MarketData, CryptoPrice, OrderBook, Trade
from .signal import Signal, SignalExecution, SignalPerformance
from .portfolio import Portfolio, Position, Transaction
from .user import User, UserProfile, UserSettings
from .compliance import TaxRecord, TDSRecord, ComplianceLog
from .risk_profile import RiskProfile, RiskMetrics

__all__ = [
    "Base",
    "MarketData",
    "CryptoPrice", 
    "OrderBook",
    "Trade",
    "Signal",
    "SignalExecution",
    "SignalPerformance",
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
    "RiskMetrics"
]

