"""
Delta Exchange API Connector

Comprehensive integration with Delta Exchange API for cryptocurrency trading.
Supports spot, options, and perpetual contracts for BTC and ETH.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode

import aiohttp
import websockets
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class DeltaExchangeError(Exception):
    """Delta Exchange API error"""
    pass


class OrderResponse(BaseModel):
    """Order response model"""
    id: str
    symbol: str
    side: str
    size: Decimal
    price: Optional[Decimal]
    status: str
    order_type: str
    created_at: datetime


class PositionResponse(BaseModel):
    """Position response model"""
    symbol: str
    size: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    margin: Decimal


class DeltaExchangeConnector:
    """Delta Exchange API connector"""
    
    def __init__(self):
        self.api_key = settings.DELTA_API_KEY
        self.api_secret = settings.DELTA_API_SECRET
        self.passphrase = settings.DELTA_API_PASSPHRASE
        self.base_url = settings.DELTA_BASE_URL
        self.websocket_url = settings.DELTA_WEBSOCKET_URL
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        
        # Rate limiting
        self.rate_limit_calls = 0
        self.rate_limit_window = 60  # 1 minute
        self.max_calls_per_window = 1000
        
        # Product cache
        self.products_cache: Dict[str, Any] = {}
        self.cache_expiry = 0
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Initialize HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Delta Exchange HTTP session initialized")
    
    async def disconnect(self):
        """Close HTTP session and WebSocket"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Delta Exchange HTTP session closed")
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Delta Exchange WebSocket closed")
    
    def _generate_signature(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate authentication signature"""
        timestamp = str(int(time.time()))
        message = timestamp + method + path + body
        
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "api-key": self.api_key,
            "signature": signature,
            "timestamp": timestamp,
            "passphrase": self.passphrase
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request"""
        if not self.session:
            await self.connect()
        
        # Rate limiting check
        if self.rate_limit_calls >= self.max_calls_per_window:
            logger.warning("Rate limit reached, waiting...")
            await asyncio.sleep(60)
            self.rate_limit_calls = 0
        
        url = f"{self.base_url}{endpoint}"
        
        # Prepare request body
        body = ""
        if data:
            body = json.dumps(data)
        
        # Add query parameters
        if params:
            url += "?" + urlencode(params)
            endpoint += "?" + urlencode(params)
        
        # Generate signature
        headers = self._generate_signature(method, endpoint, body)
        headers["Content-Type"] = "application/json"
        
        try:
            async with self.session.request(
                method, url, headers=headers, data=body
            ) as response:
                self.rate_limit_calls += 1
                
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        return result.get("result", {})
                    else:
                        raise DeltaExchangeError(f"API error: {result.get('error')}")
                else:
                    error_text = await response.text()
                    raise DeltaExchangeError(f"HTTP {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            raise DeltaExchangeError(f"Connection error: {e}")
    
    # =============================================================================
    # MARKET DATA METHODS
    # =============================================================================
    
    async def get_products(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get all available products"""
        current_time = time.time()
        
        if not force_refresh and self.products_cache and current_time < self.cache_expiry:
            return list(self.products_cache.values())
        
        products = await self._make_request("GET", "/products")
        
        # Cache products for 1 hour
        self.products_cache = {p["symbol"]: p for p in products}
        self.cache_expiry = current_time + 3600
        
        return products
    
    async def get_product(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get specific product details"""
        products = await self.get_products()
        return self.products_cache.get(symbol)
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data for symbol"""
        return await self._make_request("GET", f"/v2/tickers/{symbol}")
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """Get order book for symbol"""
        params = {"depth": depth}
        return await self._make_request("GET", f"/v2/l2orderbook/{symbol}", params=params)
    
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades for symbol"""
        params = {"limit": limit}
        return await self._make_request("GET", f"/trades/{symbol}", params=params)
    
    async def get_candles(
        self,
        symbol: str,
        resolution: str = "1m",
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get candlestick data"""
        # Delta Exchange uses v2 API and requires product_id
        # First get the product_id for the symbol
        try:
            products_response = await self._make_request("GET", "/v2/products")
            product_id = None
            
            # Handle the response format: {"result": [...], "success": true}
            products = products_response.get('result', []) if isinstance(products_response, dict) else products_response
            
            # Find the product_id for the symbol (e.g., BTCUSDT)
            for product in products:
                if product.get('symbol') == symbol:
                    product_id = product.get('id')
                    break
            
            if not product_id:
                # Try common perpetual contract symbols
                symbol_map = {
                    'BTCUSDT': 'BTCUSDT',
                    'BTC-USDT': 'BTCUSDT', 
                    'ETHUSDT': 'ETHUSDT',
                    'ETH-USDT': 'ETHUSDT'
                }
                mapped_symbol = symbol_map.get(symbol, symbol)
                
                # First try exact match for perpetual futures
                for product in products:
                    if product.get('symbol') == mapped_symbol and product.get('contract_type') == 'perpetual_futures':
                        product_id = product.get('id')
                        logger.info(f"Found perpetual futures for {symbol}: {mapped_symbol} (ID: {product_id})")
                        break
                
                # If no perpetual futures found, try spot market as fallback
                if not product_id:
                    spot_symbol_map = {
                        'ETH-USDT': 'ETH_USDT',
                        'BTC-USDT': 'BTC_USDT'
                    }
                    spot_symbol = spot_symbol_map.get(symbol, symbol)
                    for product in products:
                        if product.get('symbol') == spot_symbol and product.get('contract_type') == 'spot':
                            product_id = product.get('id')
                            logger.info(f"Using spot market for {symbol}: {spot_symbol} (ID: {product_id})")
                            break
            
            if not product_id:
                logger.warning(f"Product not found for symbol: {symbol}. Available symbols: {[p.get('symbol') for p in products[:5]]}")
                raise DeltaExchangeError(f"Product not found for symbol: {symbol}")
            
            # Set default time range if not provided (last 24 hours)
            import time
            if not end:
                end = int(time.time())
            if not start:
                start = end - 86400  # 24 hours ago
            
            params = {
                "symbol": symbol,
                "product_id": product_id,
                "resolution": resolution,
                "from": start,
                "to": end
            }
            
            chart_response = await self._make_request("GET", "/v2/chart/history", params=params)
            
            # Handle chart response format - Delta Exchange returns TradingView format
            if isinstance(chart_response, dict):
                # Check if it's the wrapped format with 'result'
                if 'result' in chart_response and chart_response.get('success'):
                    result = chart_response.get('result', {})
                else:
                    # Direct TradingView format response
                    result = chart_response
                
                # Convert TradingView format to our format
                times = result.get('t', [])
                opens = result.get('o', [])
                highs = result.get('h', [])
                lows = result.get('l', [])
                closes = result.get('c', [])
                volumes = result.get('v', [])
                
                # Check if we have valid data
                if not times or result.get('s') != 'ok':
                    logger.warning(f"No valid chart data for {symbol}: {result}")
                    return []
                
                candles = []
                for i in range(len(times)):
                    candles.append({
                        'time': times[i] * 1000,  # Convert to milliseconds
                        'open': opens[i] if i < len(opens) else 0,
                        'high': highs[i] if i < len(highs) else 0,
                        'low': lows[i] if i < len(lows) else 0,
                        'close': closes[i] if i < len(closes) else 0,
                        'volume': volumes[i] if i < len(volumes) else 0
                    })
                
                logger.info(f"Successfully retrieved {len(candles)} candles for {symbol}")
                return candles
            else:
                logger.warning(f"Unexpected chart response type: {type(chart_response)}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            raise DeltaExchangeError(f"Failed to get candles: {e}")
    
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate for perpetual contract"""
        return await self._make_request("GET", f"/funding_rate/{symbol}")
    
    async def get_options_chain(self, underlying: str) -> List[Dict[str, Any]]:
        """Get options chain for underlying asset"""
        params = {"underlying": underlying}
        return await self._make_request("GET", "/options", params=params)
    
    # =============================================================================
    # ACCOUNT METHODS
    # =============================================================================
    
    async def get_account(self) -> Dict[str, Any]:
        """Get account information"""
        return await self._make_request("GET", "/account")
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance information"""
        try:
            response = await self._make_request("GET", "/v2/wallet/balances")
            if isinstance(response, dict) and 'result' in response:
                balances = response.get('result', [])
                # Find USDT balance for main account balance
                for balance in balances:
                    if balance.get('asset_symbol') == 'USDT':
                        return {
                            'available_balance': float(balance.get('available_balance', 0)),
                            'total_balance': float(balance.get('balance', 0)),
                            'currency': 'USDT'
                        }
                return {'available_balance': 0, 'total_balance': 0, 'currency': 'USDT'}
            return {'available_balance': 0, 'total_balance': 0, 'currency': 'USDT'}
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            return {'available_balance': 0, 'total_balance': 0, 'currency': 'USDT'}
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        try:
            response = await self._make_request("GET", "/v2/positions")
            if isinstance(response, dict) and 'result' in response:
                return response.get('result', [])
            elif isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def get_position(self, symbol: str) -> Optional[PositionResponse]:
        """Get specific position"""
        positions = await self.get_positions()
        for position in positions:
            if position.symbol == symbol:
                return position
        return None
    
    # =============================================================================
    # TRADING METHODS
    # =============================================================================
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        size: Union[Decimal, float, str],
        order_type: str = "market",
        price: Optional[Union[Decimal, float, str]] = None,
        time_in_force: str = "gtc",
        reduce_only: bool = False,
        post_only: bool = False
    ) -> OrderResponse:
        """Place a new order"""
        
        order_data = {
            "product_id": symbol,
            "side": side.lower(),
            "size": str(size),
            "order_type": order_type.lower(),
            "time_in_force": time_in_force.lower(),
            "reduce_only": reduce_only,
            "post_only": post_only
        }
        
        if price and order_type.lower() in ["limit", "stop_limit"]:
            order_data["limit_price"] = str(price)
        
        response = await self._make_request("POST", "/orders", data=order_data)
        return OrderResponse(**response)
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        return await self._make_request("DELETE", f"/orders/{order_id}")
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel all orders"""
        data = {}
        if symbol:
            data["product_id"] = symbol
        
        return await self._make_request("DELETE", "/orders/all", data=data)
    
    async def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[OrderResponse]:
        """Get orders"""
        params = {"limit": limit}
        if symbol:
            params["product_id"] = symbol
        if status:
            params["state"] = status
        
        orders_data = await self._make_request("GET", "/orders", params=params)
        return [OrderResponse(**order) for order in orders_data]
    
    async def get_order(self, order_id: str) -> OrderResponse:
        """Get specific order"""
        order_data = await self._make_request("GET", f"/orders/{order_id}")
        return OrderResponse(**order_data)
    
    # =============================================================================
    # OPTIONS TRADING METHODS
    # =============================================================================
    
    async def place_options_order(
        self,
        symbol: str,
        option_type: str,
        strike: Union[Decimal, float, str],
        expiry: str,
        side: str,
        size: Union[Decimal, float, str],
        order_type: str = "market",
        price: Optional[Union[Decimal, float, str]] = None
    ) -> OrderResponse:
        """Place options order"""
        
        # Construct options symbol
        options_symbol = f"{symbol}_{strike}_{option_type.upper()}_{expiry}"
        
        return await self.place_order(
            symbol=options_symbol,
            side=side,
            size=size,
            order_type=order_type,
            price=price
        )
    
    async def place_straddle(
        self,
        symbol: str,
        strike: Union[Decimal, float, str],
        expiry: str,
        size: Union[Decimal, float, str],
        order_type: str = "market"
    ) -> List[OrderResponse]:
        """Place straddle (buy call and put at same strike)"""
        
        call_order = await self.place_options_order(
            symbol=symbol,
            option_type="CALL",
            strike=strike,
            expiry=expiry,
            side="buy",
            size=size,
            order_type=order_type
        )
        
        put_order = await self.place_options_order(
            symbol=symbol,
            option_type="PUT",
            strike=strike,
            expiry=expiry,
            side="buy",
            size=size,
            order_type=order_type
        )
        
        return [call_order, put_order]
    
    async def place_iron_condor(
        self,
        symbol: str,
        expiry: str,
        size: Union[Decimal, float, str],
        call_strikes: tuple,  # (short_strike, long_strike)
        put_strikes: tuple,   # (short_strike, long_strike)
        order_type: str = "market"
    ) -> List[OrderResponse]:
        """Place iron condor strategy"""
        
        orders = []
        
        # Sell call spread
        orders.append(await self.place_options_order(
            symbol=symbol, option_type="CALL", strike=call_strikes[0],
            expiry=expiry, side="sell", size=size, order_type=order_type
        ))
        orders.append(await self.place_options_order(
            symbol=symbol, option_type="CALL", strike=call_strikes[1],
            expiry=expiry, side="buy", size=size, order_type=order_type
        ))
        
        # Sell put spread
        orders.append(await self.place_options_order(
            symbol=symbol, option_type="PUT", strike=put_strikes[0],
            expiry=expiry, side="sell", size=size, order_type=order_type
        ))
        orders.append(await self.place_options_order(
            symbol=symbol, option_type="PUT", strike=put_strikes[1],
            expiry=expiry, side="buy", size=size, order_type=order_type
        ))
        
        return orders
    
    # =============================================================================
    # WEBSOCKET METHODS
    # =============================================================================
    
    async def connect_websocket(self):
        """Connect to Delta Exchange WebSocket"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info("Connected to Delta Exchange WebSocket")
            
            # Authenticate WebSocket
            auth_message = {
                "type": "auth",
                "payload": {
                    "api-key": self.api_key,
                    "signature": self._generate_websocket_signature(),
                    "timestamp": str(int(time.time())),
                    "passphrase": self.passphrase
                }
            }
            
            await self.websocket.send(json.dumps(auth_message))
            response = await self.websocket.recv()
            auth_response = json.loads(response)
            
            if auth_response.get("type") == "auth" and auth_response.get("success"):
                logger.info("WebSocket authentication successful")
            else:
                raise DeltaExchangeError("WebSocket authentication failed")
                
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise DeltaExchangeError(f"WebSocket connection failed: {e}")
    
    def _generate_websocket_signature(self) -> str:
        """Generate WebSocket authentication signature"""
        timestamp = str(int(time.time()))
        message = timestamp + "GET" + "/live"
        
        return hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def subscribe_to_ticker(self, symbols: List[str]):
        """Subscribe to ticker updates"""
        if not self.websocket:
            await self.connect_websocket()
        
        subscribe_message = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {"name": "ticker", "symbols": symbols}
                ]
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to ticker for symbols: {symbols}")
    
    async def subscribe_to_orderbook(self, symbols: List[str]):
        """Subscribe to order book updates"""
        if not self.websocket:
            await self.connect_websocket()
        
        subscribe_message = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {"name": "l2_orderbook", "symbols": symbols}
                ]
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to orderbook for symbols: {symbols}")
    
    async def subscribe_to_trades(self, symbols: List[str]):
        """Subscribe to trade updates"""
        if not self.websocket:
            await self.connect_websocket()
        
        subscribe_message = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {"name": "recent_trades", "symbols": symbols}
                ]
            }
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to trades for symbols: {symbols}")
    
    async def listen_to_websocket(self, callback):
        """Listen to WebSocket messages"""
        if not self.websocket:
            await self.connect_websocket()
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await callback(data)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.websocket = None
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise DeltaExchangeError(f"WebSocket error: {e}")
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    async def get_server_time(self) -> int:
        """Get server timestamp"""
        response = await self._make_request("GET", "/time")
        return response["timestamp"]
    
    async def health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            await self.get_server_time()
            return True
        except Exception:
            return False
    
    def format_symbol(self, base: str, quote: str = "USDT", contract_type: str = "spot") -> str:
        """Format symbol for Delta Exchange"""
        if contract_type == "spot":
            return f"{base}_{quote}"
        elif contract_type == "perpetual":
            return f"{base}USDT"
        else:
            return f"{base}_{quote}"



# Alias for backward compatibility
DeltaExchangeService = DeltaExchangeConnector

