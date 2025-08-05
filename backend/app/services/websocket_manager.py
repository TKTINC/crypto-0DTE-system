"""
WebSocket Manager Service

Manages WebSocket connections for real-time data streaming.
"""

import json
import asyncio
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, subscription_type: str = "general"):
        """Accept a WebSocket connection and add to active connections"""
        await websocket.accept()
        
        if subscription_type not in self.active_connections:
            self.active_connections[subscription_type] = set()
        
        self.active_connections[subscription_type].add(websocket)
        self.connection_metadata[websocket] = {
            "client_id": client_id,
            "subscription_type": subscription_type,
            "connected_at": asyncio.get_event_loop().time()
        }
        
        logger.info(f"WebSocket connected: {client_id} to {subscription_type}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            subscription_type = metadata["subscription_type"]
            client_id = metadata["client_id"]
            
            if subscription_type in self.active_connections:
                self.active_connections[subscription_type].discard(websocket)
                
                # Clean up empty subscription types
                if not self.active_connections[subscription_type]:
                    del self.active_connections[subscription_type]
            
            del self.connection_metadata[websocket]
            logger.info(f"WebSocket disconnected: {client_id} from {subscription_type}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_subscription(self, message: str, subscription_type: str):
        """Broadcast a message to all connections of a specific subscription type"""
        if subscription_type not in self.active_connections:
            return
        
        disconnected_connections = []
        
        for connection in self.active_connections[subscription_type].copy():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected_connections.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection)
    
    async def broadcast_to_all(self, message: str):
        """Broadcast a message to all active connections"""
        for subscription_type in self.active_connections:
            await self.broadcast_to_subscription(message, subscription_type)
    
    async def send_market_data(self, symbol: str, data: Dict):
        """Send market data update to relevant subscribers"""
        message = json.dumps({
            "type": "market_data",
            "symbol": symbol,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        await self.broadcast_to_subscription(message, "market_data")
        await self.broadcast_to_subscription(message, f"market_data_{symbol}")
    
    async def send_signal_update(self, signal_data: Dict):
        """Send trading signal update to subscribers"""
        message = json.dumps({
            "type": "signal_update",
            "data": signal_data,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        await self.broadcast_to_subscription(message, "signals")
    
    async def send_portfolio_update(self, portfolio_id: int, data: Dict):
        """Send portfolio update to relevant subscribers"""
        message = json.dumps({
            "type": "portfolio_update",
            "portfolio_id": portfolio_id,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        await self.broadcast_to_subscription(message, f"portfolio_{portfolio_id}")
    
    async def send_trade_execution(self, trade_data: Dict):
        """Send trade execution update to subscribers"""
        message = json.dumps({
            "type": "trade_execution",
            "data": trade_data,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        await self.broadcast_to_subscription(message, "trades")
    
    def get_connection_count(self, subscription_type: str = None) -> int:
        """Get the number of active connections"""
        if subscription_type:
            return len(self.active_connections.get(subscription_type, set()))
        else:
            return sum(len(connections) for connections in self.active_connections.values())
    
    def get_subscription_types(self) -> List[str]:
        """Get list of active subscription types"""
        return list(self.active_connections.keys())
    
    def get_connection_info(self) -> Dict:
        """Get information about all active connections"""
        info = {
            "total_connections": self.get_connection_count(),
            "subscription_types": {}
        }
        
        for subscription_type, connections in self.active_connections.items():
            info["subscription_types"][subscription_type] = {
                "connection_count": len(connections),
                "clients": []
            }
            
            for connection in connections:
                if connection in self.connection_metadata:
                    metadata = self.connection_metadata[connection]
                    info["subscription_types"][subscription_type]["clients"].append({
                        "client_id": metadata["client_id"],
                        "connected_at": metadata["connected_at"]
                    })
        
        return info

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

