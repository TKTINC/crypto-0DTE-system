"""
WebSocket Reconnection Service for Crypto-0DTE System

Provides automatic reconnection logic for WebSocket connections
to ensure continuous market data streaming.
"""

import asyncio
import logging
import websockets
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
import json
import time


logger = logging.getLogger(__name__)


class WebSocketReconnectionManager:
    """Manages WebSocket connections with automatic reconnection"""
    
    def __init__(
        self,
        url: str,
        on_message: Callable[[str], None],
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        max_reconnect_attempts: int = 10,
        reconnect_delay: float = 5.0,
        max_reconnect_delay: float = 300.0,
        ping_interval: float = 30.0,
        ping_timeout: float = 10.0
    ):
        self.url = url
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_error = on_error
        
        # Reconnection settings
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.current_reconnect_delay = reconnect_delay
        
        # Connection settings
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        
        # State management
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.last_ping_time = None
        self.last_pong_time = None
        
        # Statistics
        self.connection_count = 0
        self.total_messages_received = 0
        self.total_reconnections = 0
        self.last_connection_time = None
        self.last_disconnection_time = None
    
    async def start(self):
        """Start the WebSocket connection with reconnection logic"""
        if self.is_running:
            logger.warning("WebSocket manager is already running")
            return
        
        self.is_running = True
        logger.info(f"Starting WebSocket connection to {self.url}")
        
        while self.is_running:
            try:
                await self._connect_and_listen()
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                if self.on_error:
                    try:
                        self.on_error(e)
                    except Exception as callback_error:
                        logger.error(f"Error in error callback: {callback_error}")
                
                if self.is_running:
                    await self._handle_reconnection()
                else:
                    break
    
    async def stop(self):
        """Stop the WebSocket connection"""
        logger.info("Stopping WebSocket connection")
        self.is_running = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            finally:
                self.websocket = None
    
    async def send_message(self, message: str) -> bool:
        """Send a message through the WebSocket connection"""
        if not self.websocket or self.websocket.closed:
            logger.warning("Cannot send message: WebSocket not connected")
            return False
        
        try:
            await self.websocket.send(message)
            logger.debug(f"Sent message: {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def send_json(self, data: Dict[str, Any]) -> bool:
        """Send JSON data through the WebSocket connection"""
        try:
            message = json.dumps(data)
            return await self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending JSON: {e}")
            return False
    
    async def _connect_and_listen(self):
        """Establish connection and listen for messages"""
        try:
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.url,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
                close_timeout=10
            )
            
            # Update connection statistics
            self.connection_count += 1
            self.last_connection_time = datetime.utcnow()
            self.reconnect_attempts = 0
            self.current_reconnect_delay = self.reconnect_delay
            
            logger.info(f"WebSocket connected successfully (connection #{self.connection_count})")
            
            # Call connection callback
            if self.on_connect:
                try:
                    await self._safe_callback(self.on_connect)
                except Exception as e:
                    logger.error(f"Error in connect callback: {e}")
            
            # Listen for messages
            async for message in self.websocket:
                try:
                    self.total_messages_received += 1
                    
                    # Call message callback
                    if self.on_message:
                        await self._safe_callback(self.on_message, message)
                    
                    # Update ping/pong tracking
                    if message == "pong":
                        self.last_pong_time = datetime.utcnow()
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            self.last_disconnection_time = datetime.utcnow()
            
            if self.on_disconnect:
                try:
                    await self._safe_callback(self.on_disconnect)
                except Exception as callback_error:
                    logger.error(f"Error in disconnect callback: {callback_error}")
        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            raise
        
        finally:
            if self.websocket:
                self.websocket = None
    
    async def _handle_reconnection(self):
        """Handle reconnection logic with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached. Stopping.")
            self.is_running = False
            return
        
        self.reconnect_attempts += 1
        self.total_reconnections += 1
        
        logger.info(f"Attempting reconnection #{self.reconnect_attempts} in {self.current_reconnect_delay} seconds")
        
        # Wait before reconnecting
        await asyncio.sleep(self.current_reconnect_delay)
        
        # Exponential backoff
        self.current_reconnect_delay = min(
            self.current_reconnect_delay * 2,
            self.max_reconnect_delay
        )
    
    async def _safe_callback(self, callback: Callable, *args):
        """Safely execute callback function"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Error in callback: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on WebSocket connection"""
        is_connected = self.websocket is not None and not self.websocket.closed
        
        # Calculate uptime
        uptime_seconds = 0
        if self.last_connection_time:
            uptime_seconds = (datetime.utcnow() - self.last_connection_time).total_seconds()
        
        return {
            "status": "connected" if is_connected else "disconnected",
            "is_connected": is_connected,
            "is_running": self.is_running,
            "url": self.url,
            "connection_count": self.connection_count,
            "total_messages_received": self.total_messages_received,
            "total_reconnections": self.total_reconnections,
            "reconnect_attempts": self.reconnect_attempts,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "current_reconnect_delay": self.current_reconnect_delay,
            "uptime_seconds": uptime_seconds,
            "last_connection_time": self.last_connection_time.isoformat() if self.last_connection_time else None,
            "last_disconnection_time": self.last_disconnection_time.isoformat() if self.last_disconnection_time else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "connection_count": self.connection_count,
            "total_messages_received": self.total_messages_received,
            "total_reconnections": self.total_reconnections,
            "current_reconnect_attempts": self.reconnect_attempts,
            "is_connected": self.websocket is not None and not self.websocket.closed,
            "uptime_seconds": (
                (datetime.utcnow() - self.last_connection_time).total_seconds()
                if self.last_connection_time else 0
            )
        }


class DeltaExchangeWebSocketManager(WebSocketReconnectionManager):
    """Specialized WebSocket manager for Delta Exchange"""
    
    def __init__(self, on_market_data: Callable[[Dict[str, Any]], None]):
        self.on_market_data = on_market_data
        self.subscribed_channels = set()
        
        super().__init__(
            url="wss://socket.delta.exchange",
            on_message=self._handle_delta_message,
            on_connect=self._on_delta_connect,
            on_disconnect=self._on_delta_disconnect,
            max_reconnect_attempts=20,
            reconnect_delay=2.0,
            max_reconnect_delay=60.0,
            ping_interval=20.0
        )
    
    async def _handle_delta_message(self, message: str):
        """Handle Delta Exchange WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if data.get("type") == "ticker":
                await self._handle_ticker_data(data)
            elif data.get("type") == "l2_orderbook":
                await self._handle_orderbook_data(data)
            elif data.get("type") == "trade":
                await self._handle_trade_data(data)
            elif data.get("type") == "subscriptions":
                await self._handle_subscription_response(data)
            else:
                logger.debug(f"Unhandled message type: {data.get('type')}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON message: {e}")
        except Exception as e:
            logger.error(f"Error handling Delta message: {e}")
    
    async def _handle_ticker_data(self, data: Dict[str, Any]):
        """Handle ticker data from Delta Exchange"""
        try:
            if self.on_market_data:
                market_data = {
                    "type": "ticker",
                    "symbol": data.get("symbol"),
                    "price": float(data.get("close", 0)),
                    "volume": float(data.get("volume", 0)),
                    "change_24h": float(data.get("change_24h", 0)),
                    "high_24h": float(data.get("high", 0)),
                    "low_24h": float(data.get("low", 0)),
                    "timestamp": datetime.utcnow()
                }
                
                await self._safe_callback(self.on_market_data, market_data)
        
        except Exception as e:
            logger.error(f"Error processing ticker data: {e}")
    
    async def _handle_orderbook_data(self, data: Dict[str, Any]):
        """Handle orderbook data from Delta Exchange"""
        try:
            if self.on_market_data:
                market_data = {
                    "type": "orderbook",
                    "symbol": data.get("symbol"),
                    "bids": data.get("buy", []),
                    "asks": data.get("sell", []),
                    "timestamp": datetime.utcnow()
                }
                
                await self._safe_callback(self.on_market_data, market_data)
        
        except Exception as e:
            logger.error(f"Error processing orderbook data: {e}")
    
    async def _handle_trade_data(self, data: Dict[str, Any]):
        """Handle trade data from Delta Exchange"""
        try:
            if self.on_market_data:
                market_data = {
                    "type": "trade",
                    "symbol": data.get("symbol"),
                    "price": float(data.get("price", 0)),
                    "size": float(data.get("size", 0)),
                    "side": data.get("buyer_role"),
                    "timestamp": datetime.utcnow()
                }
                
                await self._safe_callback(self.on_market_data, market_data)
        
        except Exception as e:
            logger.error(f"Error processing trade data: {e}")
    
    async def _handle_subscription_response(self, data: Dict[str, Any]):
        """Handle subscription response from Delta Exchange"""
        try:
            success = data.get("success", False)
            channels = data.get("channels", [])
            
            if success:
                for channel in channels:
                    self.subscribed_channels.add(channel)
                    logger.info(f"Successfully subscribed to channel: {channel}")
            else:
                error = data.get("error", "Unknown error")
                logger.error(f"Subscription failed: {error}")
        
        except Exception as e:
            logger.error(f"Error processing subscription response: {e}")
    
    async def _on_delta_connect(self):
        """Handle Delta Exchange connection"""
        logger.info("Connected to Delta Exchange WebSocket")
        
        # Re-subscribe to channels after reconnection
        if self.subscribed_channels:
            await self._resubscribe_channels()
    
    async def _on_delta_disconnect(self):
        """Handle Delta Exchange disconnection"""
        logger.warning("Disconnected from Delta Exchange WebSocket")
    
    async def subscribe_to_ticker(self, symbol: str) -> bool:
        """Subscribe to ticker updates for a symbol"""
        channel = f"ticker.{symbol}"
        subscription_message = {
            "type": "subscribe",
            "payload": {
                "channels": [{"name": channel}]
            }
        }
        
        success = await self.send_json(subscription_message)
        if success:
            self.subscribed_channels.add(channel)
            logger.info(f"Subscribed to ticker for {symbol}")
        
        return success
    
    async def subscribe_to_orderbook(self, symbol: str) -> bool:
        """Subscribe to orderbook updates for a symbol"""
        channel = f"l2_orderbook.{symbol}"
        subscription_message = {
            "type": "subscribe",
            "payload": {
                "channels": [{"name": channel}]
            }
        }
        
        success = await self.send_json(subscription_message)
        if success:
            self.subscribed_channels.add(channel)
            logger.info(f"Subscribed to orderbook for {symbol}")
        
        return success
    
    async def subscribe_to_trades(self, symbol: str) -> bool:
        """Subscribe to trade updates for a symbol"""
        channel = f"trade.{symbol}"
        subscription_message = {
            "type": "subscribe",
            "payload": {
                "channels": [{"name": channel}]
            }
        }
        
        success = await self.send_json(subscription_message)
        if success:
            self.subscribed_channels.add(channel)
            logger.info(f"Subscribed to trades for {symbol}")
        
        return success
    
    async def _resubscribe_channels(self):
        """Re-subscribe to all previously subscribed channels"""
        if not self.subscribed_channels:
            return
        
        logger.info(f"Re-subscribing to {len(self.subscribed_channels)} channels")
        
        subscription_message = {
            "type": "subscribe",
            "payload": {
                "channels": [{"name": channel} for channel in self.subscribed_channels]
            }
        }
        
        await self.send_json(subscription_message)
    
    async def unsubscribe_from_channel(self, channel: str) -> bool:
        """Unsubscribe from a specific channel"""
        unsubscription_message = {
            "type": "unsubscribe",
            "payload": {
                "channels": [{"name": channel}]
            }
        }
        
        success = await self.send_json(unsubscription_message)
        if success:
            self.subscribed_channels.discard(channel)
            logger.info(f"Unsubscribed from channel: {channel}")
        
        return success


# Example usage
async def example_usage():
    """Example of how to use the WebSocket reconnection manager"""
    
    def handle_market_data(data: Dict[str, Any]):
        """Handle incoming market data"""
        print(f"Received market data: {data}")
    
    # Create Delta Exchange WebSocket manager
    ws_manager = DeltaExchangeWebSocketManager(on_market_data=handle_market_data)
    
    try:
        # Start the connection
        await ws_manager.start()
        
        # Subscribe to some channels
        await ws_manager.subscribe_to_ticker("BTCUSDT")
        await ws_manager.subscribe_to_orderbook("BTCUSDT")
        
        # Keep running
        while ws_manager.is_running:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print("Shutting down...")
    
    finally:
        await ws_manager.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())

