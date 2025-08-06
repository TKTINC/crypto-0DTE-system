"""
Delta Exchange Service for Crypto-0DTE System

Provides real integration with Delta Exchange API for market data,
order execution, and portfolio management.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import hmac
import time
import json

from app.utils.financial import FinancialCalculator
from app.config import settings


logger = logging.getLogger(__name__)


class DeltaExchangeError(Exception):
    """Custom exception for Delta Exchange API errors"""
    pass


class DeltaExchangeService:
    """Service for interacting with Delta Exchange API"""
    
    def __init__(self):
        self.base_url = "https://api.delta.exchange"
        self.api_key = settings.DELTA_EXCHANGE_API_KEY
        self.api_secret = settings.DELTA_EXCHANGE_API_SECRET
        self.calculator = FinancialCalculator()
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, method: str, endpoint: str, payload: str = "") -> str:
        """Generate HMAC signature for Delta Exchange API"""
        try:
            timestamp = str(int(time.time()))
            message = method + timestamp + endpoint + payload
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return signature, timestamp
        except Exception as e:
            logger.error(f"Error generating signature: {e}")
            raise DeltaExchangeError(f"Signature generation failed: {e}")
    
    def _get_headers(self, method: str, endpoint: str, payload: str = "") -> Dict[str, str]:
        """Get headers for Delta Exchange API request"""
        try:
            signature, timestamp = self._generate_signature(method, endpoint, payload)
            
            headers = {
                "api-key": self.api_key,
                "signature": signature,
                "timestamp": timestamp,
                "Content-Type": "application/json"
            }
            
            return headers
        except Exception as e:
            logger.error(f"Error creating headers: {e}")
            raise DeltaExchangeError(f"Header creation failed: {e}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Delta Exchange API"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.base_url}{endpoint}"
            payload = json.dumps(data) if data else ""
            headers = self._get_headers(method, endpoint, payload)
            
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=payload if data else None,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                response_data = await response.json()
                
                if response.status != 200:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise DeltaExchangeError(f"API request failed: {error_msg}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error in Delta Exchange request: {e}")
            raise DeltaExchangeError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error in Delta Exchange request: {e}")
            raise DeltaExchangeError(f"Request failed: {e}")
    
    async def get_products(self) -> List[Dict[str, Any]]:
        """Get all available trading products"""
        try:
            response = await self._make_request("GET", "/v2/products")
            return response.get("result", [])
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []
    
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for a symbol"""
        try:
            # Convert symbol format (BTC-USDT -> BTCUSDT)
            delta_symbol = symbol.replace("-", "")
            
            response = await self._make_request("GET", f"/v2/tickers/{delta_symbol}")
            return response.get("result")
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Optional[Dict[str, Any]]:
        """Get orderbook data for a symbol"""
        try:
            delta_symbol = symbol.replace("-", "")
            params = {"depth": depth}
            
            response = await self._make_request("GET", f"/v2/l2orderbook/{delta_symbol}", params=params)
            return response.get("result")
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            return None
    
    async def get_candles(
        self,
        symbol: str,
        resolution: str = "1m",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Get candlestick data for a symbol"""
        try:
            delta_symbol = symbol.replace("-", "")
            
            params = {
                "resolution": resolution,
                "limit": limit
            }
            
            if start:
                params["start"] = int(start.timestamp())
            if end:
                params["end"] = int(end.timestamp())
            
            response = await self._make_request("GET", f"/v2/history/candles", params={
                **params,
                "symbol": delta_symbol
            })
            
            return response.get("result", [])
        except Exception as e:
            logger.error(f"Error getting candles for {symbol}: {e}")
            return None
    
    async def get_market_data(self, symbol: str, lookback_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive market data for technical analysis"""
        try:
            # Get current ticker
            ticker = await self.get_ticker(symbol)
            if not ticker:
                return {}
            
            # Get historical candles
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=lookback_hours)
            
            candles = await self.get_candles(
                symbol=symbol,
                resolution="1h",  # 1-hour candles
                start=start_time,
                end=end_time,
                limit=100
            )
            
            if not candles:
                return {}
            
            # Extract OHLCV data
            prices = [float(candle["close"]) for candle in candles]
            volumes = [float(candle["volume"]) for candle in candles]
            highs = [float(candle["high"]) for candle in candles]
            lows = [float(candle["low"]) for candle in candles]
            opens = [float(candle["open"]) for candle in candles]
            
            # Get current price from ticker
            current_price = float(ticker.get("close", prices[-1] if prices else 0))
            
            market_data = {
                "symbol": symbol,
                "current_price": current_price,
                "prices": prices,
                "volumes": volumes,
                "highs": highs,
                "lows": lows,
                "opens": opens,
                "24h_change": float(ticker.get("change_24h", 0)),
                "24h_volume": float(ticker.get("volume", 0)),
                "bid": float(ticker.get("bid", current_price)),
                "ask": float(ticker.get("ask", current_price)),
                "timestamp": datetime.utcnow(),
                "data_points": len(prices)
            }
            
            logger.info(f"Retrieved market data for {symbol}: {len(prices)} data points")
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {}
    
    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance information"""
        try:
            response = await self._make_request("GET", "/v2/wallet/balances")
            return response.get("result")
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            response = await self._make_request("GET", "/v2/positions")
            return response.get("result", [])
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def place_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        order_type: str,  # "market" or "limit"
        size: Decimal,
        price: Optional[Decimal] = None,
        reduce_only: bool = False,
        post_only: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Place a trading order"""
        try:
            delta_symbol = symbol.replace("-", "")
            
            order_data = {
                "product_id": delta_symbol,
                "side": side,
                "order_type": order_type,
                "size": str(size),
                "reduce_only": reduce_only,
                "post_only": post_only
            }
            
            if price and order_type == "limit":
                order_data["limit_price"] = str(price)
            
            response = await self._make_request("POST", "/v2/orders", data=order_data)
            
            order_result = response.get("result")
            if order_result:
                logger.info(f"Order placed: {symbol} {side} {size} @ {price or 'market'}")
            
            return order_result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            response = await self._make_request("DELETE", f"/v2/orders/{order_id}")
            success = response.get("success", False)
            
            if success:
                logger.info(f"Order cancelled: {order_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific order"""
        try:
            response = await self._make_request("GET", f"/v2/orders/{order_id}")
            return response.get("result")
        except Exception as e:
            logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get trade history"""
        try:
            params = {"limit": limit}
            
            if symbol:
                params["product_id"] = symbol.replace("-", "")
            if start_time:
                params["start_time"] = int(start_time.timestamp())
            if end_time:
                params["end_time"] = int(end_time.timestamp())
            
            response = await self._make_request("GET", "/v2/fills", params=params)
            return response.get("result", [])
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get funding rate for a perpetual contract"""
        try:
            delta_symbol = symbol.replace("-", "")
            response = await self._make_request("GET", f"/v2/products/{delta_symbol}/funding_rate")
            return response.get("result")
        except Exception as e:
            logger.error(f"Error getting funding rate for {symbol}: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Delta Exchange connection"""
        try:
            # Try to get server time
            response = await self._make_request("GET", "/v2/time")
            server_time = response.get("result", {}).get("iso")
            
            return {
                "status": "healthy",
                "server_time": server_time,
                "api_connected": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Delta Exchange health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_connected": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get market summary for all major pairs"""
        try:
            major_pairs = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "AVAX-USDT", "MATIC-USDT"]
            summary = {}
            
            for symbol in major_pairs:
                ticker = await self.get_ticker(symbol)
                if ticker:
                    summary[symbol] = {
                        "price": float(ticker.get("close", 0)),
                        "change_24h": float(ticker.get("change_24h", 0)),
                        "volume_24h": float(ticker.get("volume", 0)),
                        "high_24h": float(ticker.get("high", 0)),
                        "low_24h": float(ticker.get("low", 0))
                    }
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "markets": summary
            }
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Utility functions for easy access
async def get_delta_service() -> DeltaExchangeService:
    """Get Delta Exchange service instance"""
    return DeltaExchangeService()


async def get_market_data_for_symbol(symbol: str) -> Dict[str, Any]:
    """Quick function to get market data for a symbol"""
    async with DeltaExchangeService() as service:
        return await service.get_market_data(symbol)


async def place_market_order(symbol: str, side: str, size: Decimal) -> Optional[Dict[str, Any]]:
    """Quick function to place a market order"""
    async with DeltaExchangeService() as service:
        return await service.place_order(
            symbol=symbol,
            side=side,
            order_type="market",
            size=size
        )

