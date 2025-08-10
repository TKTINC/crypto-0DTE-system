"""
Market Data Models

SQLAlchemy models for storing cryptocurrency market data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, Text, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class MarketData(Base):
    """Base market data model"""
    
    __tablename__ = "market_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    data_type = Column(String(50), nullable=False)  # price, volume, orderbook, etc.
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_market_data_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_market_data_exchange_timestamp', 'exchange', 'timestamp'),
    )


class CryptoPrice(Base):
    """Cryptocurrency price data"""
    
    __tablename__ = "crypto_prices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)  # BTC, ETH
    exchange = Column(String(50), nullable=False, index=True)  # delta, binance, coinbase
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # OHLCV data
    open_price = Column(Numeric(20, 8), nullable=False)
    high_price = Column(Numeric(20, 8), nullable=False)
    low_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    
    # Additional metrics
    vwap = Column(Numeric(20, 8))  # Volume Weighted Average Price
    trades_count = Column(Integer)
    
    # Calculated fields
    price_change = Column(Numeric(10, 4))  # Percentage change
    volume_change = Column(Numeric(10, 4))  # Volume change percentage
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_crypto_prices_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_crypto_prices_exchange_symbol', 'exchange', 'symbol'),
    )


class OHLCV(Base):
    """OHLCV (Open, High, Low, Close, Volume) candlestick data"""
    
    __tablename__ = "ohlcv_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)  # 1m, 5m, 15m, 1h, 4h, 1d
    
    # OHLCV data
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    
    # Additional metrics
    vwap = Column(Numeric(20, 8))  # Volume Weighted Average Price
    trades_count = Column(Integer)
    quote_volume = Column(Numeric(20, 8))  # Volume in quote currency
    
    # Technical indicators (can be calculated and stored)
    sma_20 = Column(Numeric(20, 8))  # 20-period Simple Moving Average
    ema_20 = Column(Numeric(20, 8))  # 20-period Exponential Moving Average
    rsi_14 = Column(Numeric(5, 2))   # 14-period RSI
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_ohlcv_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp'),
        Index('idx_ohlcv_exchange_symbol_timeframe', 'exchange', 'symbol', 'timeframe'),
    )


class OrderBook(Base):
    """Order book data"""
    
    __tablename__ = "order_books"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Best bid/ask
    best_bid = Column(Numeric(20, 8), nullable=False)
    best_ask = Column(Numeric(20, 8), nullable=False)
    bid_size = Column(Numeric(20, 8), nullable=False)
    ask_size = Column(Numeric(20, 8), nullable=False)
    
    # Spread metrics
    spread = Column(Numeric(20, 8), nullable=False)
    spread_percentage = Column(Numeric(10, 4), nullable=False)
    
    # Depth data (top 10 levels)
    bids = Column(JSON)  # [{"price": 50000, "size": 1.5}, ...]
    asks = Column(JSON)  # [{"price": 50100, "size": 2.0}, ...]
    
    # Liquidity metrics
    bid_liquidity_10 = Column(Numeric(20, 8))  # Total bid liquidity in top 10 levels
    ask_liquidity_10 = Column(Numeric(20, 8))  # Total ask liquidity in top 10 levels
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_orderbook_symbol_timestamp', 'symbol', 'timestamp'),
    )


class MarketTrade(Base):
    """Individual trade data"""
    
    __tablename__ = "market_trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Trade details
    trade_id = Column(String(100), nullable=False)  # Exchange trade ID
    price = Column(Numeric(20, 8), nullable=False)
    size = Column(Numeric(20, 8), nullable=False)
    side = Column(String(10), nullable=False)  # buy, sell
    
    # Trade classification
    is_maker = Column(Boolean)  # True if maker, False if taker
    is_block_trade = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_market_trades_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_market_trades_exchange_trade_id', 'exchange', 'trade_id'),
    )


class FundingRate(Base):
    """Funding rate data for perpetual contracts"""
    
    __tablename__ = "funding_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Funding rate data
    funding_rate = Column(Numeric(10, 6), nullable=False)  # Current funding rate
    predicted_rate = Column(Numeric(10, 6))  # Predicted next funding rate
    
    # Funding interval
    funding_interval = Column(Integer, nullable=False)  # Hours between funding
    next_funding_time = Column(DateTime, nullable=False)
    
    # Open interest
    open_interest = Column(Numeric(20, 8))
    open_interest_usd = Column(Numeric(20, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_funding_rates_symbol_timestamp', 'symbol', 'timestamp'),
    )


class OptionsData(Base):
    """Options market data"""
    
    __tablename__ = "options_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)  # BTC, ETH
    exchange = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Option details
    strike_price = Column(Numeric(20, 8), nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    option_type = Column(String(10), nullable=False)  # CALL, PUT
    
    # Pricing data
    mark_price = Column(Numeric(20, 8))
    bid_price = Column(Numeric(20, 8))
    ask_price = Column(Numeric(20, 8))
    last_price = Column(Numeric(20, 8))
    
    # Volume and open interest
    volume_24h = Column(Numeric(20, 8), default=0)
    open_interest = Column(Numeric(20, 8), default=0)
    
    # Greeks
    delta = Column(Numeric(10, 6))
    gamma = Column(Numeric(10, 6))
    theta = Column(Numeric(10, 6))
    vega = Column(Numeric(10, 6))
    rho = Column(Numeric(10, 6))
    
    # Implied volatility
    implied_volatility = Column(Numeric(10, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_options_symbol_expiry', 'symbol', 'expiry_date'),
        Index('idx_options_strike_type', 'strike_price', 'option_type'),
    )


class MarketSentiment(Base):
    """Market sentiment indicators"""
    
    __tablename__ = "market_sentiment"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Fear & Greed Index
    fear_greed_index = Column(Integer)  # 0-100
    fear_greed_classification = Column(String(20))  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed
    
    # Social sentiment
    twitter_sentiment = Column(Numeric(5, 2))  # -1 to 1
    reddit_sentiment = Column(Numeric(5, 2))  # -1 to 1
    news_sentiment = Column(Numeric(5, 2))  # -1 to 1
    
    # Market metrics
    btc_dominance = Column(Numeric(5, 2))  # Bitcoin dominance percentage
    total_market_cap = Column(Numeric(20, 2))  # Total crypto market cap
    
    # Volatility indices
    btc_volatility_index = Column(Numeric(10, 4))
    eth_volatility_index = Column(Numeric(10, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class DeFiMetrics(Base):
    """DeFi ecosystem metrics for ETH correlation analysis"""
    
    __tablename__ = "defi_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Total Value Locked
    total_tvl = Column(Numeric(20, 2), nullable=False)
    
    # Individual protocol TVL
    uniswap_tvl = Column(Numeric(20, 2))
    aave_tvl = Column(Numeric(20, 2))
    compound_tvl = Column(Numeric(20, 2))
    makerdao_tvl = Column(Numeric(20, 2))
    
    # Token prices
    uni_price = Column(Numeric(20, 8))
    aave_price = Column(Numeric(20, 8))
    comp_price = Column(Numeric(20, 8))
    mkr_price = Column(Numeric(20, 8))
    
    # Gas metrics
    avg_gas_price = Column(Numeric(20, 8))  # in gwei
    gas_used_24h = Column(Numeric(20, 0))
    
    # DeFi activity
    dex_volume_24h = Column(Numeric(20, 2))
    lending_volume_24h = Column(Numeric(20, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)

