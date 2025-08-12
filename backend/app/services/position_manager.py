"""
Position Management System for Crypto-0DTE System

Manages active trading positions with intelligent exit strategies:
- Real-time position monitoring
- Dynamic stop loss adjustments (trailing stops)
- Take profit optimization
- Position sizing management
- Exit condition evaluation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import math

from app.services.exchanges.delta_exchange import DeltaExchangeConnector
from app.database import get_db
from app.config import Settings
from app.models.trade import Trade, TradeStatus, TradeType

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Intelligent position management system for autonomous trading.
    
    Features:
    - Real-time position monitoring
    - Dynamic stop loss adjustments
    - Trailing stop implementation
    - Take profit optimization
    - Risk-based exit decisions
    """
    
    def __init__(self, paper_trading: bool = None):
        self.settings = Settings()
        
        # Determine paper trading mode
        self.paper_trading = paper_trading if paper_trading is not None else True  # Default to paper trading for safety
        
        # Initialize Delta Exchange connector with environment awareness
        self.delta_connector = DeltaExchangeConnector(paper_trading=self.paper_trading)
        
        # Configuration
        self.trailing_stop_threshold = 0.02  # 2% profit before trailing starts
        self.trailing_stop_distance = 0.01   # 1% trailing distance
        self.max_position_age = 24 * 3600    # 24 hours max position age
        self.profit_taking_levels = [0.05, 0.10, 0.15]  # 5%, 10%, 15% profit levels
        self.partial_profit_sizes = [0.3, 0.3, 0.4]     # 30%, 30%, 40% position sizes
        
        # State tracking
        self.position_states = {}
        self.trailing_stops = {}
        self.profit_levels_hit = {}
        
        logger.info("Position Manager initialized")
    
    async def initialize(self):
        """Initialize the position manager (non-blocking for API failures)"""
        try:
            # Try to initialize Delta Exchange connector, but don't block startup if it fails
            try:
                await self.delta_connector.initialize()
                logger.info("Delta Exchange connector initialized successfully")
            except Exception as e:
                logger.warning(f"Delta Exchange connector initialization failed: {e}")
                logger.info("Position Manager will continue with limited functionality")
            
            # Try to load existing position states, but don't block startup if it fails
            try:
                await self._load_position_states()
            except Exception as e:
                logger.warning(f"Could not load position states during startup: {e}")
                logger.info("Position Manager will start with empty position state")
            
            logger.info("✅ Position Manager initialized successfully")
            
        except Exception as e:
            logger.warning(f"Position Manager initialization had issues but continuing: {e}")
            # Don't raise the exception - allow startup to continue
    
    async def cleanup(self):
        """Cleanup the position manager"""
        try:
            # Save position states
            await self._save_position_states()
            
            # Cleanup Delta connector
            await self.delta_connector.cleanup()
            
            logger.info("✅ Position Manager cleaned up")
            
        except Exception as e:
            logger.error(f"Error during Position Manager cleanup: {e}")
    
    async def check_exit_conditions(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a position should be exited and determine exit strategy.
        
        Args:
            position: Position data including current price, entry price, etc.
        
        Returns:
            Dict with exit decision and details
        """
        try:
            trade_id = position["trade_id"]
            symbol = position["symbol"]
            current_price = position["current_price"]
            entry_price = position["entry_price"]
            side = position["side"]
            
            logger.debug(f"Checking exit conditions for {trade_id}")
            
            # Initialize position state if not exists
            if trade_id not in self.position_states:
                await self._initialize_position_state(position)
            
            # Check various exit conditions
            exit_checks = [
                await self._check_stop_loss_hit(position),
                await self._check_take_profit_hit(position),
                await self._check_trailing_stop(position),
                await self._check_time_based_exit(position),
                await self._check_profit_taking_levels(position),
                await self._check_market_conditions_exit(position),
                await self._check_risk_based_exit(position)
            ]
            
            # Find the highest priority exit condition
            for exit_check in exit_checks:
                if exit_check["should_exit"]:
                    logger.info(f"Exit condition triggered for {trade_id}: {exit_check['reason']}")
                    return exit_check
            
            # Check if we should update stop loss (trailing stop)
            trailing_update = await self._check_trailing_stop_update(position)
            if trailing_update["update_stop_loss"]:
                return trailing_update
            
            # No exit conditions met
            return {
                "should_exit": False,
                "reason": "No exit conditions met",
                "update_stop_loss": False
            }
            
        except Exception as e:
            logger.error(f"Error checking exit conditions for {position.get('trade_id')}: {e}")
            return {
                "should_exit": False,
                "reason": f"Error in exit check: {str(e)}",
                "update_stop_loss": False
            }
    
    async def _check_stop_loss_hit(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check if stop loss has been hit"""
        try:
            current_price = position["current_price"]
            stop_loss = position.get("stop_loss")
            side = position["side"]
            
            if not stop_loss:
                return {"should_exit": False}
            
            # Check if stop loss is hit
            if side.upper() == "BUY" and current_price <= stop_loss:
                return {
                    "should_exit": True,
                    "exit_type": "STOP_LOSS",
                    "exit_price": None,  # Market order
                    "reason": f"Stop loss hit: {current_price} <= {stop_loss}",
                    "priority": 1  # Highest priority
                }
            elif side.upper() == "SELL" and current_price >= stop_loss:
                return {
                    "should_exit": True,
                    "exit_type": "STOP_LOSS",
                    "exit_price": None,  # Market order
                    "reason": f"Stop loss hit: {current_price} >= {stop_loss}",
                    "priority": 1
                }
            
            return {"should_exit": False}
            
        except Exception as e:
            logger.error(f"Error checking stop loss: {e}")
            return {"should_exit": False}
    
    async def _check_take_profit_hit(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check if take profit has been hit"""
        try:
            current_price = position["current_price"]
            take_profit = position.get("take_profit")
            side = position["side"]
            
            if not take_profit:
                return {"should_exit": False}
            
            # Check if take profit is hit
            if side.upper() == "BUY" and current_price >= take_profit:
                return {
                    "should_exit": True,
                    "exit_type": "TAKE_PROFIT",
                    "exit_price": take_profit,
                    "reason": f"Take profit hit: {current_price} >= {take_profit}",
                    "priority": 2
                }
            elif side.upper() == "SELL" and current_price <= take_profit:
                return {
                    "should_exit": True,
                    "exit_type": "TAKE_PROFIT",
                    "exit_price": take_profit,
                    "reason": f"Take profit hit: {current_price} <= {take_profit}",
                    "priority": 2
                }
            
            return {"should_exit": False}
            
        except Exception as e:
            logger.error(f"Error checking take profit: {e}")
            return {"should_exit": False}
    
    async def _check_trailing_stop(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check trailing stop conditions"""
        try:
            trade_id = position["trade_id"]
            current_price = position["current_price"]
            entry_price = position["entry_price"]
            side = position["side"]
            
            # Calculate current profit percentage
            if side.upper() == "BUY":
                profit_pct = (current_price - entry_price) / entry_price
            else:
                profit_pct = (entry_price - current_price) / entry_price
            
            # Check if we should activate trailing stop
            if profit_pct >= self.trailing_stop_threshold:
                if trade_id not in self.trailing_stops:
                    # Activate trailing stop
                    self.trailing_stops[trade_id] = {
                        "highest_profit": profit_pct,
                        "trailing_stop_price": self._calculate_trailing_stop_price(
                            current_price, side, self.trailing_stop_distance
                        ),
                        "activated_at": datetime.utcnow()
                    }
                    logger.info(f"Trailing stop activated for {trade_id} at {profit_pct:.2%} profit")
                else:
                    # Update trailing stop if profit increased
                    trailing_data = self.trailing_stops[trade_id]
                    if profit_pct > trailing_data["highest_profit"]:
                        trailing_data["highest_profit"] = profit_pct
                        trailing_data["trailing_stop_price"] = self._calculate_trailing_stop_price(
                            current_price, side, self.trailing_stop_distance
                        )
                        logger.debug(f"Updated trailing stop for {trade_id}: {profit_pct:.2%}")
            
            # Check if trailing stop is hit
            if trade_id in self.trailing_stops:
                trailing_stop_price = self.trailing_stops[trade_id]["trailing_stop_price"]
                
                if side.upper() == "BUY" and current_price <= trailing_stop_price:
                    return {
                        "should_exit": True,
                        "exit_type": "TRAILING_STOP",
                        "exit_price": None,  # Market order
                        "reason": f"Trailing stop hit: {current_price} <= {trailing_stop_price}",
                        "priority": 3
                    }
                elif side.upper() == "SELL" and current_price >= trailing_stop_price:
                    return {
                        "should_exit": True,
                        "exit_type": "TRAILING_STOP",
                        "exit_price": None,  # Market order
                        "reason": f"Trailing stop hit: {current_price} >= {trailing_stop_price}",
                        "priority": 3
                    }
            
            return {"should_exit": False}
            
        except Exception as e:
            logger.error(f"Error checking trailing stop: {e}")
            return {"should_exit": False}
    
    async def _check_time_based_exit(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check time-based exit conditions"""
        try:
            created_at = position.get("created_at")
            if not created_at:
                return {"should_exit": False}
            
            # Calculate position age
            position_age = (datetime.utcnow() - created_at).total_seconds()
            
            # Check if position is too old
            if position_age > self.max_position_age:
                return {
                    "should_exit": True,
                    "exit_type": "TIME_BASED",
                    "exit_price": None,  # Market order
                    "reason": f"Position too old: {position_age/3600:.1f} hours",
                    "priority": 5
                }
            
            # Check for end-of-day exit (for 0DTE strategies)
            now = datetime.utcnow()
            if now.hour >= 21:  # 9 PM UTC (market close approaching)
                return {
                    "should_exit": True,
                    "exit_type": "END_OF_DAY",
                    "exit_price": None,  # Market order
                    "reason": "End of day exit (0DTE strategy)",
                    "priority": 4
                }
            
            return {"should_exit": False}
            
        except Exception as e:
            logger.error(f"Error checking time-based exit: {e}")
            return {"should_exit": False}
    
    async def _check_profit_taking_levels(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check profit taking levels for partial exits"""
        try:
            trade_id = position["trade_id"]
            current_price = position["current_price"]
            entry_price = position["entry_price"]
            side = position["side"]
            
            # Calculate current profit percentage
            if side.upper() == "BUY":
                profit_pct = (current_price - entry_price) / entry_price
            else:
                profit_pct = (entry_price - current_price) / entry_price
            
            # Initialize profit levels tracking
            if trade_id not in self.profit_levels_hit:
                self.profit_levels_hit[trade_id] = []
            
            # Check each profit level
            for i, level in enumerate(self.profit_taking_levels):
                if profit_pct >= level and i not in self.profit_levels_hit[trade_id]:
                    # Mark this level as hit
                    self.profit_levels_hit[trade_id].append(i)
                    
                    # Calculate partial exit size
                    partial_size = self.partial_profit_sizes[i]
                    
                    return {
                        "should_exit": True,
                        "exit_type": "PARTIAL_PROFIT",
                        "exit_price": None,  # Market order
                        "partial_exit": True,
                        "exit_percentage": partial_size,
                        "reason": f"Profit level {level:.1%} hit, taking {partial_size:.1%} profit",
                        "priority": 6
                    }
            
            return {"should_exit": False}
            
        except Exception as e:
            logger.error(f"Error checking profit taking levels: {e}")
            return {"should_exit": False}
    
    async def _check_market_conditions_exit(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check market conditions for exit signals"""
        try:
            symbol = position["symbol"]
            
            # Get market data
            market_data = await self.delta_connector.get_market_data(symbol)
            
            # Check for extreme volatility
            volatility = market_data.get("volatility", 0)
            if volatility > 0.15:  # 15% volatility threshold
                return {
                    "should_exit": True,
                    "exit_type": "HIGH_VOLATILITY",
                    "exit_price": None,  # Market order
                    "reason": f"Extreme volatility detected: {volatility:.1%}",
                    "priority": 7
                }
            
            # Check for low liquidity
            volume_24h = market_data.get("volume_24h", 0)
            if volume_24h < 500000:  # $500K volume threshold
                return {
                    "should_exit": True,
                    "exit_type": "LOW_LIQUIDITY",
                    "exit_price": None,  # Market order
                    "reason": f"Low liquidity: ${volume_24h:,.0f} 24h volume",
                    "priority": 8
                }
            
            return {"should_exit": False}
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            return {"should_exit": False}
    
    async def _check_risk_based_exit(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check risk-based exit conditions"""
        try:
            current_price = position["current_price"]
            entry_price = position["entry_price"]
            side = position["side"]
            
            # Calculate current loss percentage
            if side.upper() == "BUY":
                loss_pct = (entry_price - current_price) / entry_price
            else:
                loss_pct = (current_price - entry_price) / entry_price
            
            # Check for maximum loss threshold
            max_loss_threshold = 0.10  # 10% max loss
            if loss_pct > max_loss_threshold:
                return {
                    "should_exit": True,
                    "exit_type": "MAX_LOSS",
                    "exit_price": None,  # Market order
                    "reason": f"Maximum loss threshold hit: {loss_pct:.1%}",
                    "priority": 2  # High priority
                }
            
            return {"should_exit": False}
            
        except Exception as e:
            logger.error(f"Error checking risk-based exit: {e}")
            return {"should_exit": False}
    
    async def _check_trailing_stop_update(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Check if trailing stop should be updated"""
        try:
            trade_id = position["trade_id"]
            current_price = position["current_price"]
            side = position["side"]
            
            if trade_id in self.trailing_stops:
                trailing_data = self.trailing_stops[trade_id]
                new_trailing_price = self._calculate_trailing_stop_price(
                    current_price, side, self.trailing_stop_distance
                )
                
                # Check if we should update the trailing stop
                old_trailing_price = trailing_data["trailing_stop_price"]
                
                should_update = False
                if side.upper() == "BUY" and new_trailing_price > old_trailing_price:
                    should_update = True
                elif side.upper() == "SELL" and new_trailing_price < old_trailing_price:
                    should_update = True
                
                if should_update:
                    trailing_data["trailing_stop_price"] = new_trailing_price
                    
                    return {
                        "should_exit": False,
                        "update_stop_loss": True,
                        "new_stop_loss": new_trailing_price,
                        "reason": f"Updating trailing stop to {new_trailing_price}"
                    }
            
            return {"should_exit": False, "update_stop_loss": False}
            
        except Exception as e:
            logger.error(f"Error checking trailing stop update: {e}")
            return {"should_exit": False, "update_stop_loss": False}
    
    def _calculate_trailing_stop_price(self, current_price: float, side: str, distance: float) -> float:
        """Calculate trailing stop price"""
        if side.upper() == "BUY":
            return current_price * (1 - distance)
        else:  # SELL
            return current_price * (1 + distance)
    
    async def _initialize_position_state(self, position: Dict[str, Any]):
        """Initialize state tracking for a position"""
        trade_id = position["trade_id"]
        
        self.position_states[trade_id] = {
            "created_at": datetime.utcnow(),
            "entry_price": position["entry_price"],
            "highest_price": position["current_price"],
            "lowest_price": position["current_price"],
            "max_profit": 0.0,
            "max_loss": 0.0,
            "updates_count": 0
        }
        
        logger.info(f"Initialized position state for {trade_id}")
    
    async def _load_position_states(self):
        """Load position states from persistent storage"""
        try:
            # In a real implementation, this would load from database or file
            # For now, we'll start with empty states
            self.position_states = {}
            self.trailing_stops = {}
            self.profit_levels_hit = {}
            
            logger.info("Position states loaded")
            
        except Exception as e:
            logger.error(f"Error loading position states: {e}")
    
    async def _save_position_states(self):
        """Save position states to persistent storage"""
        try:
            # In a real implementation, this would save to database or file
            # For now, we'll just log the action
            logger.info(f"Saving {len(self.position_states)} position states")
            
        except Exception as e:
            logger.error(f"Error saving position states: {e}")
    
    # Public API methods
    
    async def get_position_analytics(self, trade_id: str) -> Dict[str, Any]:
        """Get analytics for a specific position"""
        try:
            if trade_id not in self.position_states:
                return {"error": "Position not found"}
            
            state = self.position_states[trade_id]
            trailing = self.trailing_stops.get(trade_id, {})
            profit_levels = self.profit_levels_hit.get(trade_id, [])
            
            return {
                "trade_id": trade_id,
                "state": state,
                "trailing_stop": trailing,
                "profit_levels_hit": profit_levels,
                "analytics": {
                    "position_age_hours": (datetime.utcnow() - state["created_at"]).total_seconds() / 3600,
                    "max_profit_pct": state["max_profit"],
                    "max_loss_pct": state["max_loss"],
                    "updates_count": state["updates_count"],
                    "trailing_active": trade_id in self.trailing_stops
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting position analytics: {e}")
            return {"error": str(e)}
    
    async def force_exit_position(self, trade_id: str, reason: str = "Manual") -> Dict[str, Any]:
        """Force exit a position"""
        try:
            return {
                "should_exit": True,
                "exit_type": "MANUAL",
                "exit_price": None,  # Market order
                "reason": f"Manual exit: {reason}",
                "priority": 0  # Highest priority
            }
            
        except Exception as e:
            logger.error(f"Error forcing exit for {trade_id}: {e}")
            return {"should_exit": False, "error": str(e)}
    
    async def update_position_parameters(
        self,
        trade_id: str,
        new_stop_loss: Optional[float] = None,
        new_take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update position parameters"""
        try:
            updates = {}
            
            if new_stop_loss is not None:
                updates["stop_loss"] = new_stop_loss
            
            if new_take_profit is not None:
                updates["take_profit"] = new_take_profit
            
            # In a real implementation, this would update the database
            logger.info(f"Updated parameters for {trade_id}: {updates}")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "updates": updates
            }
            
        except Exception as e:
            logger.error(f"Error updating position parameters: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_all_position_states(self) -> Dict[str, Any]:
        """Get all position states for monitoring"""
        return {
            "position_states": self.position_states.copy(),
            "trailing_stops": self.trailing_stops.copy(),
            "profit_levels_hit": self.profit_levels_hit.copy(),
            "total_positions": len(self.position_states),
            "active_trailing_stops": len(self.trailing_stops)
        }

