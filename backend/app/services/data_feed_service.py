"""
Real-Time Data Feed Service

Collects and processes real-time cryptocurrency market data from multiple sources.
Stores data in InfluxDB for time-series analysis and Redis for caching.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import traceback

from sqlalchemy.ext.asyncio import AsyncSession
from influxdb_client import Point
import aioredis

from app.config import settings
from app.database import get_db_session, influxdb_manager, redis_manager
from app.models.market_data import CryptoPrice, OrderBook, MarketTrade, FundingRate, MarketSentiment, DeFiMetrics
from app.services.exchanges.delta_exchange import DeltaExchangeConnector
# from app.services.external_data_service import ExternalDataService  # TODO: Create this service
from app.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class DataFeedService:
    """Real-time data feed service"""
    
    def __init__(self):
        # Use paper trading mode from settings
        from app.config import settings
        self.delta_connector = DeltaExchangeConnector(paper_trading=settings.PAPER_TRADING)
        # self.external_data = ExternalDataService()  # TODO: Create this service
        
        # Symbols to track
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        self.options_symbols = []
        
        # Data collection intervals
        self.price_interval = 1  # 1 second
        self.orderbook_interval = 1  # 1 second
        self.funding_interval = 300  # 5 minutes
        self.sentiment_interval = 3600  # 1 hour
        self.defi_interval = 1800  # 30 minutes
        
        # Running flags
        self.running = False
        self.tasks: List[asyncio.Task] = []
        
        # Data buffers for batch processing
        self.price_buffer: List[Dict] = []
        self.trade_buffer: List[Dict] = []
        self.orderbook_buffer: List[Dict] = []
        
        # Buffer limits
        self.buffer_size = 100
        self.buffer_flush_interval = 10  # seconds
    
    async def start(self):
        """Start the data feed service"""
        logger.info("Starting Data Feed Service...")
        
        try:
            # Connect to Delta Exchange
            await self.delta_connector.connect()
            
            # Initialize external data service
            # await self.external_data.initialize()  # TODO: Create external data service
            
            self.running = True
            
            # Start data collection tasks
            self.tasks = [
                asyncio.create_task(self._collect_price_data()),
                asyncio.create_task(self._collect_orderbook_data()),
                asyncio.create_task(self._collect_trade_data()),
                asyncio.create_task(self._collect_funding_rates()),
                asyncio.create_task(self._collect_sentiment_data()),
                asyncio.create_task(self._collect_defi_data()),
                asyncio.create_task(self._flush_buffers()),
                asyncio.create_task(self._websocket_listener())
            ]
            
            logger.info("Data Feed Service started successfully")
            
            # Wait for all tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error starting Data Feed Service: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the data feed service"""
        logger.info("Stopping Data Feed Service...")
        
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Flush remaining data
        await self._flush_all_buffers()
        
        # Disconnect from exchanges
        await self.delta_connector.disconnect()
        
        logger.info("Data Feed Service stopped")
    
    # =============================================================================
    # PRICE DATA COLLECTION
    # =============================================================================
    
    async def _collect_price_data(self):
        """Collect real-time price data"""
        logger.info("Starting price data collection...")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    ticker = await self.delta_connector.get_ticker(symbol)
                    
                    # Check if ticker data is valid
                    if ticker is None or not isinstance(ticker, dict):
                        logger.warning(f"No ticker data received for {symbol}, skipping...")
                        continue
                    
                    price_data = {
                        "symbol": symbol,
                        "exchange": "delta",
                        "timestamp": datetime.utcnow(),
                        "open_price": Decimal(str(ticker.get("open", 0))),
                        "high_price": Decimal(str(ticker.get("high", 0))),
                        "low_price": Decimal(str(ticker.get("low", 0))),
                        "close_price": Decimal(str(ticker.get("close", 0))),
                        "volume": Decimal(str(ticker.get("volume", 0))),
                        "price_change": Decimal(str(ticker.get("change_24h", 0))),
                        "volume_change": Decimal(str(ticker.get("volume_change_24h", 0)))
                    }
                    
                    # Add to buffer
                    self.price_buffer.append(price_data)
                    
                    # Cache latest price in Redis
                    await self._cache_latest_price(symbol, price_data)
                
                await asyncio.sleep(self.price_interval)
                
            except Exception as e:
                logger.error(f"Error collecting price data: {e}")
                await asyncio.sleep(5)
    
    async def _cache_latest_price(self, symbol: str, price_data: Dict):
        """Cache latest price in Redis"""
        try:
            cache_key = f"price:{symbol}:latest"
            cache_data = {
                "price": float(price_data["close_price"]),
                "volume": float(price_data["volume"]),
                "change": float(price_data["price_change"]),
                "timestamp": price_data["timestamp"].isoformat()
            }
            
            await redis_manager.set_cache(
                cache_key,
                json.dumps(cache_data),
                ttl=settings.MARKET_DATA_CACHE_TTL
            )
            
        except Exception as e:
            logger.error(f"Error caching price data: {e}")
    
    # =============================================================================
    # ORDER BOOK DATA COLLECTION
    # =============================================================================
    
    async def _collect_orderbook_data(self):
        """Collect real-time order book data"""
        logger.info("Starting order book data collection...")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    orderbook = await self.delta_connector.get_orderbook(symbol, depth=10)
                    
                    # Check if orderbook data is valid
                    if orderbook is None or not isinstance(orderbook, dict):
                        logger.warning(f"No orderbook data received for {symbol}, skipping...")
                        continue
                    
                    bids = orderbook.get("buy", [])
                    asks = orderbook.get("sell", [])
                    
                    if bids and asks:
                        best_bid = Decimal(str(bids[0]["price"]))
                        best_ask = Decimal(str(asks[0]["price"]))
                        bid_size = Decimal(str(bids[0]["size"]))
                        ask_size = Decimal(str(asks[0]["size"]))
                        
                        spread = best_ask - best_bid
                        spread_percentage = (spread / best_ask) * 100
                        
                        # Calculate liquidity
                        bid_liquidity = sum(Decimal(str(bid["size"])) for bid in bids)
                        ask_liquidity = sum(Decimal(str(ask["size"])) for ask in asks)
                        
                        orderbook_data = {
                            "symbol": symbol,
                            "exchange": "delta",
                            "timestamp": datetime.utcnow(),
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "bid_size": bid_size,
                            "ask_size": ask_size,
                            "spread": spread,
                            "spread_percentage": spread_percentage,
                            "bids": [{"price": b["price"], "size": b["size"]} for b in bids],
                            "asks": [{"price": a["price"], "size": a["size"]} for a in asks],
                            "bid_liquidity_10": bid_liquidity,
                            "ask_liquidity_10": ask_liquidity
                        }
                        
                        # Add to buffer
                        self.orderbook_buffer.append(orderbook_data)
                        
                        # Cache latest orderbook
                        await self._cache_latest_orderbook(symbol, orderbook_data)
                
                await asyncio.sleep(self.orderbook_interval)
                
            except Exception as e:
                logger.error(f"Error collecting orderbook data: {e}")
                await asyncio.sleep(5)
    
    async def _cache_latest_orderbook(self, symbol: str, orderbook_data: Dict):
        """Cache latest orderbook in Redis"""
        try:
            cache_key = f"orderbook:{symbol}:latest"
            cache_data = {
                "best_bid": float(orderbook_data["best_bid"]),
                "best_ask": float(orderbook_data["best_ask"]),
                "spread": float(orderbook_data["spread"]),
                "spread_percentage": float(orderbook_data["spread_percentage"]),
                "timestamp": orderbook_data["timestamp"].isoformat()
            }
            
            await redis_manager.set_cache(
                cache_key,
                json.dumps(cache_data),
                ttl=settings.MARKET_DATA_CACHE_TTL
            )
            
        except Exception as e:
            logger.error(f"Error caching orderbook data: {e}")
    
    # =============================================================================
    # TRADE DATA COLLECTION
    # =============================================================================
    
    async def _collect_trade_data(self):
        """Collect real-time trade data"""
        logger.info("Starting trade data collection...")
        
        last_trade_ids = {symbol: None for symbol in self.symbols}
        
        while self.running:
            try:
                for symbol in self.symbols:
                    trades = await self.delta_connector.get_trades(symbol, limit=50)
                    
                    new_trades = []
                    for trade in trades:
                        trade_id = trade.get("id")
                        
                        # Skip if we've already processed this trade
                        if trade_id == last_trade_ids[symbol]:
                            break
                        
                        new_trades.append(trade)
                    
                    # Update last trade ID
                    if trades:
                        last_trade_ids[symbol] = trades[0].get("id")
                    
                    # Process new trades
                    for trade in reversed(new_trades):  # Process in chronological order
                        trade_data = {
                            "symbol": symbol,
                            "exchange": "delta",
                            "timestamp": datetime.fromisoformat(trade["created_at"].replace("Z", "+00:00")),
                            "trade_id": trade["id"],
                            "price": Decimal(str(trade["price"])),
                            "size": Decimal(str(trade["size"])),
                            "side": trade["side"],
                            "is_maker": trade.get("is_maker", False)
                        }
                        
                        # Add to buffer
                        self.trade_buffer.append(trade_data)
                
                await asyncio.sleep(2)  # Check for new trades every 2 seconds
                
            except Exception as e:
                logger.error(f"Error collecting trade data: {e}")
                await asyncio.sleep(5)
    
    # =============================================================================
    # FUNDING RATE COLLECTION
    # =============================================================================
    
    async def _collect_funding_rates(self):
        """Collect funding rate data"""
        logger.info("Starting funding rate collection...")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    # Only collect for perpetual contracts
                    if "USDT" in symbol and not symbol.endswith("_SPOT"):
                        funding_data = await self.delta_connector.get_funding_rate(symbol)
                        
                        if funding_data:
                            await self._store_funding_rate(symbol, funding_data)
                
                await asyncio.sleep(self.funding_interval)
                
            except Exception as e:
                logger.error(f"Error collecting funding rates: {e}")
                await asyncio.sleep(60)
    
    async def _store_funding_rate(self, symbol: str, funding_data: Dict):
        """Store funding rate data"""
        try:
            async with get_db_session() as session:
                funding_rate = FundingRate(
                    symbol=symbol,
                    exchange="delta",
                    timestamp=datetime.utcnow(),
                    funding_rate=Decimal(str(funding_data.get("funding_rate", 0))),
                    predicted_rate=Decimal(str(funding_data.get("predicted_rate", 0))),
                    funding_interval=funding_data.get("funding_interval", 8),
                    next_funding_time=datetime.fromisoformat(
                        funding_data.get("next_funding_time", datetime.utcnow().isoformat())
                    ),
                    open_interest=Decimal(str(funding_data.get("open_interest", 0))),
                    open_interest_usd=Decimal(str(funding_data.get("open_interest_usd", 0)))
                )
                
                session.add(funding_rate)
                await session.commit()
                
                logger.debug(f"Stored funding rate for {symbol}: {funding_data['funding_rate']}")
                
        except Exception as e:
            logger.error(f"Error storing funding rate: {e}")
    
    # =============================================================================
    # SENTIMENT DATA COLLECTION
    # =============================================================================
    
    async def _collect_sentiment_data(self):
        """Collect market sentiment data"""
        logger.info("Starting sentiment data collection...")
        
        while self.running:
            try:
                # TODO: Implement external data service
                # Get Fear & Greed Index
                # fear_greed_data = await self.external_data.get_fear_greed_index()
                
                # Get social sentiment
                # social_sentiment = await self.external_data.get_social_sentiment()
                
                # Get market metrics
                # market_metrics = await self.external_data.get_market_metrics()
                
                # Store sentiment data
                # await self._store_sentiment_data(fear_greed_data, social_sentiment, market_metrics)
                
                await asyncio.sleep(self.sentiment_interval)
                
            except Exception as e:
                logger.error(f"Error collecting sentiment data: {e}")
                await asyncio.sleep(300)
    
    async def _store_sentiment_data(self, fear_greed: Dict, social: Dict, market: Dict):
        """Store sentiment data"""
        try:
            async with get_db_session() as session:
                sentiment = MarketSentiment(
                    timestamp=datetime.utcnow(),
                    fear_greed_index=fear_greed.get("value"),
                    fear_greed_classification=fear_greed.get("value_classification"),
                    twitter_sentiment=Decimal(str(social.get("twitter", 0))),
                    reddit_sentiment=Decimal(str(social.get("reddit", 0))),
                    news_sentiment=Decimal(str(social.get("news", 0))),
                    btc_dominance=Decimal(str(market.get("btc_dominance", 0))),
                    total_market_cap=Decimal(str(market.get("total_market_cap", 0))),
                    btc_volatility_index=Decimal(str(market.get("btc_volatility", 0))),
                    eth_volatility_index=Decimal(str(market.get("eth_volatility", 0)))
                )
                
                session.add(sentiment)
                await session.commit()
                
                logger.debug(f"Stored sentiment data: F&G={fear_greed.get('value')}")
                
        except Exception as e:
            logger.error(f"Error storing sentiment data: {e}")
    
    # =============================================================================
    # DEFI DATA COLLECTION
    # =============================================================================
    
    async def _collect_defi_data(self):
        """Collect DeFi ecosystem data"""
        logger.info("Starting DeFi data collection...")
        
        while self.running:
            try:
                # TODO: Implement external data service
                # Get DeFi metrics
                # defi_data = await self.external_data.get_defi_metrics()
                
                # Store DeFi data
                # await self._store_defi_data(defi_data)
                
                await asyncio.sleep(self.defi_interval)
                
            except Exception as e:
                logger.error(f"Error collecting DeFi data: {e}")
                await asyncio.sleep(300)
    
    async def _store_defi_data(self, defi_data: Dict):
        """Store DeFi data"""
        try:
            async with get_db_session() as session:
                defi_metrics = DeFiMetrics(
                    timestamp=datetime.utcnow(),
                    total_tvl=Decimal(str(defi_data.get("total_tvl", 0))),
                    uniswap_tvl=Decimal(str(defi_data.get("uniswap_tvl", 0))),
                    aave_tvl=Decimal(str(defi_data.get("aave_tvl", 0))),
                    compound_tvl=Decimal(str(defi_data.get("compound_tvl", 0))),
                    makerdao_tvl=Decimal(str(defi_data.get("makerdao_tvl", 0))),
                    uni_price=Decimal(str(defi_data.get("uni_price", 0))),
                    aave_price=Decimal(str(defi_data.get("aave_price", 0))),
                    comp_price=Decimal(str(defi_data.get("comp_price", 0))),
                    mkr_price=Decimal(str(defi_data.get("mkr_price", 0))),
                    avg_gas_price=Decimal(str(defi_data.get("avg_gas_price", 0))),
                    gas_used_24h=Decimal(str(defi_data.get("gas_used_24h", 0))),
                    dex_volume_24h=Decimal(str(defi_data.get("dex_volume_24h", 0))),
                    lending_volume_24h=Decimal(str(defi_data.get("lending_volume_24h", 0)))
                )
                
                session.add(defi_metrics)
                await session.commit()
                
                logger.debug(f"Stored DeFi data: TVL=${defi_data.get('total_tvl', 0):,.0f}")
                
        except Exception as e:
            logger.error(f"Error storing DeFi data: {e}")
    
    # =============================================================================
    # WEBSOCKET LISTENER
    # =============================================================================
    
    async def _websocket_listener(self):
        """Listen to WebSocket for real-time updates"""
        logger.info("Starting WebSocket listener...")
        
        try:
            # Connect to WebSocket
            await self.delta_connector.connect_websocket()
            
            # Subscribe to channels
            await self.delta_connector.subscribe_to_ticker(self.symbols)
            await self.delta_connector.subscribe_to_orderbook(self.symbols)
            await self.delta_connector.subscribe_to_trades(self.symbols)
            
            # Listen for messages
            await self.delta_connector.listen_to_websocket(self._handle_websocket_message)
            
        except Exception as e:
            logger.error(f"WebSocket listener error: {e}")
            # Reconnect after delay
            await asyncio.sleep(10)
            if self.running:
                await self._websocket_listener()
    
    async def _handle_websocket_message(self, message: Dict):
        """Handle incoming WebSocket message"""
        try:
            message_type = message.get("type")
            channel = message.get("channel")
            data = message.get("data", {})
            
            if message_type == "ticker":
                await self._handle_ticker_update(data)
            elif message_type == "l2_orderbook":
                await self._handle_orderbook_update(data)
            elif message_type == "recent_trades":
                await self._handle_trade_update(data)
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_ticker_update(self, data: Dict):
        """Handle ticker update from WebSocket"""
        # Update Redis cache with latest ticker data
        symbol = data.get("symbol")
        if symbol:
            cache_key = f"ticker:{symbol}:latest"
            await redis_manager.set_cache(
                cache_key,
                json.dumps(data),
                ttl=settings.MARKET_DATA_CACHE_TTL
            )
    
    async def _handle_orderbook_update(self, data: Dict):
        """Handle orderbook update from WebSocket"""
        # Update Redis cache with latest orderbook data
        symbol = data.get("symbol")
        if symbol:
            cache_key = f"orderbook:{symbol}:latest"
            await redis_manager.set_cache(
                cache_key,
                json.dumps(data),
                ttl=settings.MARKET_DATA_CACHE_TTL
            )
    
    async def _handle_trade_update(self, data: Dict):
        """Handle trade update from WebSocket"""
        # Process real-time trade data
        symbol = data.get("symbol")
        if symbol and isinstance(data.get("trades"), list):
            for trade in data["trades"]:
                trade_data = {
                    "symbol": symbol,
                    "exchange": "delta",
                    "timestamp": datetime.fromisoformat(trade["timestamp"]),
                    "trade_id": trade["id"],
                    "price": Decimal(str(trade["price"])),
                    "size": Decimal(str(trade["size"])),
                    "side": trade["side"]
                }
                
                self.trade_buffer.append(trade_data)
    
    # =============================================================================
    # BUFFER MANAGEMENT
    # =============================================================================
    
    async def _flush_buffers(self):
        """Periodically flush data buffers"""
        while self.running:
            try:
                await asyncio.sleep(self.buffer_flush_interval)
                await self._flush_all_buffers()
                
            except Exception as e:
                logger.error(f"Error flushing buffers: {e}")
    
    async def _flush_all_buffers(self):
        """Flush all data buffers"""
        await asyncio.gather(
            self._flush_price_buffer(),
            self._flush_orderbook_buffer(),
            self._flush_trade_buffer(),
            return_exceptions=True
        )
    
    async def _flush_price_buffer(self):
        """Flush price data buffer"""
        if not self.price_buffer:
            return
        
        try:
            # Store in PostgreSQL
            async with get_db_session() as session:
                for price_data in self.price_buffer:
                    crypto_price = CryptoPrice(**price_data)
                    session.add(crypto_price)
                
                await session.commit()
            
            # Store in InfluxDB
            points = []
            for price_data in self.price_buffer:
                point = Point("crypto_prices") \
                    .tag("symbol", price_data["symbol"]) \
                    .tag("exchange", price_data["exchange"]) \
                    .field("close_price", float(price_data["close_price"])) \
                    .field("volume", float(price_data["volume"])) \
                    .field("price_change", float(price_data["price_change"])) \
                    .time(price_data["timestamp"])
                
                points.append(point)
            
            await influxdb_manager.write_points(points)
            
            logger.debug(f"Flushed {len(self.price_buffer)} price records")
            self.price_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error flushing price buffer: {e}")
    
    async def _flush_orderbook_buffer(self):
        """Flush orderbook data buffer"""
        if not self.orderbook_buffer:
            return
        
        try:
            # Store in PostgreSQL
            async with get_db_session() as session:
                for orderbook_data in self.orderbook_buffer:
                    orderbook = OrderBook(**orderbook_data)
                    session.add(orderbook)
                
                await session.commit()
            
            # Store in InfluxDB
            points = []
            for orderbook_data in self.orderbook_buffer:
                point = Point("orderbooks") \
                    .tag("symbol", orderbook_data["symbol"]) \
                    .tag("exchange", orderbook_data["exchange"]) \
                    .field("best_bid", float(orderbook_data["best_bid"])) \
                    .field("best_ask", float(orderbook_data["best_ask"])) \
                    .field("spread", float(orderbook_data["spread"])) \
                    .field("spread_percentage", float(orderbook_data["spread_percentage"])) \
                    .time(orderbook_data["timestamp"])
                
                points.append(point)
            
            await influxdb_manager.write_points(points)
            
            logger.debug(f"Flushed {len(self.orderbook_buffer)} orderbook records")
            self.orderbook_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error flushing orderbook buffer: {e}")
    
    async def _flush_trade_buffer(self):
        """Flush trade data buffer"""
        if not self.trade_buffer:
            return
        
        try:
            # Store in PostgreSQL
            async with get_db_session() as session:
                for trade_data in self.trade_buffer:
                    trade = MarketTrade(**trade_data)
                    session.add(trade)
                
                await session.commit()
            
            # Store in InfluxDB
            points = []
            for trade_data in self.trade_buffer:
                point = Point("trades") \
                    .tag("symbol", trade_data["symbol"]) \
                    .tag("exchange", trade_data["exchange"]) \
                    .tag("side", trade_data["side"]) \
                    .field("price", float(trade_data["price"])) \
                    .field("size", float(trade_data["size"])) \
                    .time(trade_data["timestamp"])
                
                points.append(point)
            
            await influxdb_manager.write_points(points)
            
            logger.debug(f"Flushed {len(self.trade_buffer)} trade records")
            self.trade_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error flushing trade buffer: {e}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for data feed service"""
    data_feed = DataFeedService()
    
    try:
        await data_feed.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Data feed service error: {e}")
        logger.error(traceback.format_exc())
    finally:
        await data_feed.stop()


if __name__ == "__main__":
    asyncio.run(main())

