"""
Trade Execution Engine for Crypto-0DTE System

Handles automated trade execution, order management, and position lifecycle:
- Automated order placement on Delta Exchange
- Position sizing and risk management
- Stop loss and take profit automation
- Order status monitoring and management
- Emergency position closure capabilities
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.services.exchanges.delta_exchange import DeltaExchangeConnector
from app.services.risk_manager import RiskManager
from app.database import get_db
from app.config import Settings
from app.models.trade import Trade, TradeStatus, TradeType
from app.models.order import Order, OrderStatus, OrderType
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TradeExecutionError(Exception):
    """Custom exception for trade execution errors"""
    pass


class TradeExecutionEngine:
    """
    Engine for executing and managing trades on Delta Exchange.
    
    Handles the complete trade lifecycle:
    - Order placement and validation
    - Position monitoring and management
    - Stop loss and take profit execution
    - Emergency position closure
    """
    
    def __init__(self, paper_trading: bool = None):
        self.settings = Settings()
        
        # Determine paper trading mode
        self.paper_trading = paper_trading if paper_trading is not None else True  # Default to paper trading for safety
        
        # Initialize Delta Exchange connector with environment awareness
        self.delta_connector = DeltaExchangeConnector(paper_trading=self.paper_trading)
        
        # Initialize Risk Manager for risk gate checks
        self.risk_manager = RiskManager(paper_trading=self.paper_trading)
        
        self.active_orders = {}
        self.order_monitoring_tasks = {}
        
        # Configuration
        self.max_slippage = 0.005  # 0.5% max slippage
        self.order_timeout = 300   # 5 minutes order timeout
        self.retry_attempts = 3    # Max retry attempts
        
        logger.info("Trade Execution Engine initialized")
    
    async def initialize(self):
        """Initialize the trade execution engine"""
        try:
            # Initialize Delta Exchange connector
            await self.delta_connector.initialize()
            
            # Initialize Risk Manager
            await self.risk_manager.initialize()
            
            # Load existing orders
            await self._load_existing_orders()
            
            logger.info("✅ Trade Execution Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Trade Execution Engine: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup the trade execution engine"""
        try:
            # Cancel monitoring tasks
            for task in self.order_monitoring_tasks.values():
                task.cancel()
            
            # Cleanup Delta connector
            await self.delta_connector.cleanup()
            
            # Cleanup Risk Manager
            await self.risk_manager.cleanup()
            
            logger.info("✅ Trade Execution Engine cleaned up")
            
        except Exception as e:
            logger.error(f"Error during Trade Execution Engine cleanup: {e}")
    
    async def execute_trade(
        self,
        symbol: str,
        side: str,
        size: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        reasoning: str = "Autonomous trade",
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """
        Execute a trade with full position management setup.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            side: "BUY" or "SELL"
            size: Position size
            entry_price: Target entry price (for limit orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            reasoning: Trade reasoning/strategy
            order_type: "MARKET" or "LIMIT"
        
        Returns:
            Dict with execution results
        """
        try:
            logger.info(f"🎯 Executing trade: {side} {size} {symbol}")
            
            # Validate trade parameters
            validation_result = await self._validate_trade_parameters(
                symbol, side, size, entry_price, stop_loss, take_profit
            )
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Trade validation failed: {validation_result['reason']}"
                }
            
            # Create trade record
            trade_id = str(uuid.uuid4())
            trade_record = await self._create_trade_record(
                trade_id, symbol, side, size, entry_price, stop_loss, take_profit, reasoning
            )
            
            # Execute main order
            main_order_result = await self._execute_main_order(
                trade_id, symbol, side, size, entry_price, order_type
            )
            
            if not main_order_result["success"]:
                await self._update_trade_status(trade_id, TradeStatus.FAILED)
                return {
                    "success": False,
                    "error": f"Main order execution failed: {main_order_result['error']}"
                }
            
            # Set up stop loss and take profit orders
            if stop_loss:
                await self._setup_stop_loss_order(trade_id, symbol, side, size, stop_loss)
            
            if take_profit:
                await self._setup_take_profit_order(trade_id, symbol, side, size, take_profit)
            
            # Start monitoring the trade
            await self._start_trade_monitoring(trade_id)
            
            # Update trade status
            await self._update_trade_status(trade_id, TradeStatus.OPEN)
            
            result = {
                "success": True,
                "trade_id": trade_id,
                "symbol": symbol,
                "side": side,
                "size": size,
                "entry_price": main_order_result.get("fill_price", entry_price),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "order_id": main_order_result["order_id"],
                "timestamp": datetime.utcnow()
            }
            
            logger.info(f"✅ Trade executed successfully: {trade_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_position(
        self,
        trade_id: str,
        exit_type: str = "MANUAL",
        exit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Close an existing position.
        
        Args:
            trade_id: ID of the trade to close
            exit_type: Reason for exit ("MANUAL", "STOP_LOSS", "TAKE_PROFIT", "RISK_MANAGEMENT")
            exit_price: Specific exit price (for limit orders)
        
        Returns:
            Dict with closure results
        """
        try:
            logger.info(f"🚪 Closing position: {trade_id} ({exit_type})")
            
            # Get trade record
            trade = await self._get_trade_record(trade_id)
            if not trade:
                return {"success": False, "error": "Trade not found"}
            
            # Cancel existing stop loss and take profit orders
            await self._cancel_related_orders(trade_id)
            
            # Determine exit side (opposite of entry)
            exit_side = "SELL" if trade.trade_type == TradeType.BUY else "BUY"
            
            # Execute exit order
            exit_order_result = await self._execute_main_order(
                trade_id,
                trade.symbol,
                exit_side,
                float(trade.size),
                exit_price,
                "MARKET" if exit_price is None else "LIMIT"
            )
            
            if not exit_order_result["success"]:
                return {
                    "success": False,
                    "error": f"Exit order failed: {exit_order_result['error']}"
                }
            
            # Calculate realized PnL
            realized_pnl = await self._calculate_realized_pnl(
                trade,
                exit_order_result.get("fill_price", exit_price)
            )
            
            # Update trade record
            await self._update_trade_closure(
                trade_id,
                exit_order_result.get("fill_price", exit_price),
                realized_pnl,
                exit_type
            )
            
            # Stop monitoring
            await self._stop_trade_monitoring(trade_id)
            
            result = {
                "success": True,
                "trade_id": trade_id,
                "exit_price": exit_order_result.get("fill_price", exit_price),
                "realized_pnl": realized_pnl,
                "exit_type": exit_type,
                "timestamp": datetime.utcnow()
            }
            
            logger.info(f"✅ Position closed: {trade_id}, PnL: {realized_pnl:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error closing position {trade_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def emergency_close_position(self, trade_id: str) -> Dict[str, Any]:
        """Emergency close position with market orders"""
        logger.critical(f"🚨 Emergency closing position: {trade_id}")
        
        return await self.close_position(
            trade_id,
            exit_type="EMERGENCY",
            exit_price=None  # Use market order for immediate execution
        )
    
    async def update_stop_loss(self, trade_id: str, new_stop_loss: float) -> Dict[str, Any]:
        """Update stop loss for an existing position"""
        try:
            logger.info(f"🛡️ Updating stop loss for {trade_id}: {new_stop_loss}")
            
            # Cancel existing stop loss order
            await self._cancel_stop_loss_order(trade_id)
            
            # Get trade record
            trade = await self._get_trade_record(trade_id)
            if not trade:
                return {"success": False, "error": "Trade not found"}
            
            # Create new stop loss order
            await self._setup_stop_loss_order(
                trade_id,
                trade.symbol,
                trade.trade_type.value,
                float(trade.size),
                new_stop_loss
            )
            
            # Update trade record
            await self._update_trade_stop_loss(trade_id, new_stop_loss)
            
            return {
                "success": True,
                "trade_id": trade_id,
                "new_stop_loss": new_stop_loss
            }
            
        except Exception as e:
            logger.error(f"Error updating stop loss for {trade_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def reduce_position_size(self, trade_id: str, new_size: float) -> Dict[str, Any]:
        """Reduce position size by partially closing"""
        try:
            logger.info(f"📉 Reducing position size for {trade_id}: {new_size}")
            
            # Get trade record
            trade = await self._get_trade_record(trade_id)
            if not trade:
                return {"success": False, "error": "Trade not found"}
            
            current_size = float(trade.size)
            if new_size >= current_size:
                return {"success": False, "error": "New size must be smaller than current size"}
            
            # Calculate size to close
            size_to_close = current_size - new_size
            
            # Execute partial close
            exit_side = "SELL" if trade.trade_type == TradeType.BUY else "BUY"
            
            partial_close_result = await self._execute_main_order(
                trade_id,
                trade.symbol,
                exit_side,
                size_to_close,
                None,  # Market order
                "MARKET"
            )
            
            if not partial_close_result["success"]:
                return {
                    "success": False,
                    "error": f"Partial close failed: {partial_close_result['error']}"
                }
            
            # Update trade size
            await self._update_trade_size(trade_id, new_size)
            
            # Update stop loss and take profit orders for new size
            if trade.stop_loss:
                await self._cancel_stop_loss_order(trade_id)
                await self._setup_stop_loss_order(
                    trade_id, trade.symbol, trade.trade_type.value, new_size, float(trade.stop_loss)
                )
            
            if trade.take_profit:
                await self._cancel_take_profit_order(trade_id)
                await self._setup_take_profit_order(
                    trade_id, trade.symbol, trade.trade_type.value, new_size, float(trade.take_profit)
                )
            
            return {
                "success": True,
                "trade_id": trade_id,
                "old_size": current_size,
                "new_size": new_size,
                "closed_size": size_to_close
            }
            
        except Exception as e:
            logger.error(f"Error reducing position size for {trade_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _validate_trade_parameters(
        self,
        symbol: str,
        side: str,
        size: float,
        entry_price: Optional[float],
        stop_loss: Optional[float],
        take_profit: Optional[float]
    ) -> Dict[str, Any]:
        """Validate trade parameters before execution"""
        try:
            # Check symbol validity
            if not await self.delta_connector.is_valid_symbol(symbol):
                return {"valid": False, "reason": f"Invalid symbol: {symbol}"}
            
            # Check side validity
            if side.upper() not in ["BUY", "SELL"]:
                return {"valid": False, "reason": f"Invalid side: {side}"}
            
            # Check size validity
            if size <= 0:
                return {"valid": False, "reason": f"Invalid size: {size}"}
            
            # Check minimum size requirements
            min_size = await self.delta_connector.get_minimum_order_size(symbol)
            if size < min_size:
                return {"valid": False, "reason": f"Size below minimum: {size} < {min_size}"}
            
            # Validate stop loss
            if stop_loss:
                current_price = await self.delta_connector.get_current_price(symbol)
                
                if side.upper() == "BUY" and stop_loss >= current_price:
                    return {"valid": False, "reason": "Stop loss must be below current price for BUY orders"}
                
                if side.upper() == "SELL" and stop_loss <= current_price:
                    return {"valid": False, "reason": "Stop loss must be above current price for SELL orders"}
            
            # Validate take profit
            if take_profit:
                current_price = await self.delta_connector.get_current_price(symbol)
                
                if side.upper() == "BUY" and take_profit <= current_price:
                    return {"valid": False, "reason": "Take profit must be above current price for BUY orders"}
                
                if side.upper() == "SELL" and take_profit >= current_price:
                    return {"valid": False, "reason": "Take profit must be below current price for SELL orders"}
            
            # Check account balance
            balance_check = await self._check_account_balance(symbol, side, size, entry_price)
            if not balance_check["sufficient"]:
                return {"valid": False, "reason": balance_check["reason"]}
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Error validating trade parameters: {e}")
            return {"valid": False, "reason": f"Validation error: {str(e)}"}
    
    async def _execute_main_order(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float],
        order_type: str
    ) -> Dict[str, Any]:
        """Execute the main entry or exit order"""
        try:
            # 🛡️ CRITICAL RISK GATE: Check all risk criteria before order placement
            risk_allowed, risk_reason = await self.risk_manager.check_order_risk_gate(
                symbol=symbol,
                side=side,
                size=size,
                price=price,
                order_type=order_type
            )
            
            if not risk_allowed:
                logger.warning(f"🚫 ORDER BLOCKED BY RISK GATE: {risk_reason}")
                return {
                    "success": False,
                    "error": f"Risk gate denied: {risk_reason}",
                    "risk_denied": True
                }
            
            # Prepare order parameters
            order_params = {
                "symbol": symbol,
                "side": side.upper(),
                "size": size,
                "type": order_type.upper()
            }
            
            if order_type.upper() == "LIMIT" and price:
                order_params["price"] = price
            
            # Execute order on Delta Exchange (only after risk gate approval)
            order_result = await self.delta_connector.place_order(**order_params)
            
            if not order_result["success"]:
                return {
                    "success": False,
                    "error": order_result["error"]
                }
            
            order_id = order_result["order_id"]
            
            # Create order record
            await self._create_order_record(
                order_id, trade_id, symbol, side, size, price, order_type
            )
            
            # Monitor order execution
            fill_result = await self._monitor_order_execution(order_id)
            
            return {
                "success": True,
                "order_id": order_id,
                "fill_price": fill_result.get("fill_price"),
                "fill_size": fill_result.get("fill_size", size)
            }
            
        except Exception as e:
            logger.error(f"Error executing main order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _setup_stop_loss_order(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        size: float,
        stop_loss_price: float
    ):
        """Set up stop loss order for a position"""
        try:
            # Determine stop loss side (opposite of main position)
            stop_side = "SELL" if side.upper() == "BUY" else "BUY"
            
            # 🛡️ RISK GATE: Check risk criteria for stop loss order
            risk_allowed, risk_reason = await self.risk_manager.check_order_risk_gate(
                symbol=symbol,
                side=stop_side,
                size=size,
                price=stop_loss_price,
                order_type="stop_market"
            )
            
            if not risk_allowed:
                logger.warning(f"🚫 STOP LOSS BLOCKED BY RISK GATE: {risk_reason}")
                return
            
            # Create stop loss order
            stop_order_result = await self.delta_connector.place_stop_order(
                symbol=symbol,
                side=stop_side,
                size=size,
                stop_price=stop_loss_price,
                order_type="STOP_MARKET"
            )
            
            if stop_order_result["success"]:
                # Record stop loss order
                await self._create_order_record(
                    stop_order_result["order_id"],
                    trade_id,
                    symbol,
                    stop_side,
                    size,
                    stop_loss_price,
                    "STOP_LOSS"
                )
                
                logger.info(f"✅ Stop loss set: {stop_loss_price} for trade {trade_id}")
            else:
                logger.error(f"Failed to set stop loss: {stop_order_result['error']}")
                
        except Exception as e:
            logger.error(f"Error setting up stop loss: {e}")
    
    async def _setup_take_profit_order(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        size: float,
        take_profit_price: float
    ):
        """Set up take profit order for a position"""
        try:
            # Determine take profit side (opposite of main position)
            tp_side = "SELL" if side.upper() == "BUY" else "BUY"
            
            # 🛡️ RISK GATE: Check risk criteria for take profit order
            risk_allowed, risk_reason = await self.risk_manager.check_order_risk_gate(
                symbol=symbol,
                side=tp_side,
                size=size,
                price=take_profit_price,
                order_type="limit"
            )
            
            if not risk_allowed:
                logger.warning(f"🚫 TAKE PROFIT BLOCKED BY RISK GATE: {risk_reason}")
                return
            
            # Create take profit order
            tp_order_result = await self.delta_connector.place_order(
                symbol=symbol,
                side=tp_side,
                size=size,
                price=take_profit_price,
                type="LIMIT"
            )
            
            if tp_order_result["success"]:
                # Record take profit order
                await self._create_order_record(
                    tp_order_result["order_id"],
                    trade_id,
                    symbol,
                    tp_side,
                    size,
                    take_profit_price,
                    "TAKE_PROFIT"
                )
                
                logger.info(f"✅ Take profit set: {take_profit_price} for trade {trade_id}")
            else:
                logger.error(f"Failed to set take profit: {tp_order_result['error']}")
                
        except Exception as e:
            logger.error(f"Error setting up take profit: {e}")
    
    async def _monitor_order_execution(self, order_id: str) -> Dict[str, Any]:
        """Monitor order execution until filled or timeout"""
        try:
            start_time = datetime.utcnow()
            timeout = timedelta(seconds=self.order_timeout)
            
            while datetime.utcnow() - start_time < timeout:
                # Check order status
                order_status = await self.delta_connector.get_order_status(order_id)
                
                if order_status["status"] == "FILLED":
                    return {
                        "filled": True,
                        "fill_price": order_status["fill_price"],
                        "fill_size": order_status["fill_size"]
                    }
                elif order_status["status"] in ["CANCELLED", "REJECTED"]:
                    return {
                        "filled": False,
                        "error": f"Order {order_status['status']}"
                    }
                
                # Wait before next check
                await asyncio.sleep(5)
            
            # Timeout reached
            logger.warning(f"Order {order_id} monitoring timeout")
            return {
                "filled": False,
                "error": "Order monitoring timeout"
            }
            
        except Exception as e:
            logger.error(f"Error monitoring order {order_id}: {e}")
            return {
                "filled": False,
                "error": str(e)
            }
    
    async def _start_trade_monitoring(self, trade_id: str):
        """Start monitoring a trade for management"""
        if trade_id not in self.order_monitoring_tasks:
            task = asyncio.create_task(self._trade_monitoring_loop(trade_id))
            self.order_monitoring_tasks[trade_id] = task
            logger.info(f"Started monitoring trade: {trade_id}")
    
    async def _stop_trade_monitoring(self, trade_id: str):
        """Stop monitoring a trade"""
        if trade_id in self.order_monitoring_tasks:
            self.order_monitoring_tasks[trade_id].cancel()
            del self.order_monitoring_tasks[trade_id]
            logger.info(f"Stopped monitoring trade: {trade_id}")
    
    async def _trade_monitoring_loop(self, trade_id: str):
        """Monitor a trade for stop loss/take profit execution"""
        try:
            while True:
                # Check if related orders (stop loss, take profit) have been filled
                related_orders = await self._get_related_orders(trade_id)
                
                for order in related_orders:
                    order_status = await self.delta_connector.get_order_status(order["order_id"])
                    
                    if order_status["status"] == "FILLED":
                        # Order filled, close the trade
                        exit_type = "STOP_LOSS" if order["order_type"] == "STOP_LOSS" else "TAKE_PROFIT"
                        
                        await self.close_position(
                            trade_id,
                            exit_type=exit_type,
                            exit_price=order_status["fill_price"]
                        )
                        
                        return  # Exit monitoring loop
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info(f"Trade monitoring cancelled for {trade_id}")
        except Exception as e:
            logger.error(f"Error in trade monitoring loop for {trade_id}: {e}")
    
    # Database operations
    
    async def _create_trade_record(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        size: float,
        entry_price: Optional[float],
        stop_loss: Optional[float],
        take_profit: Optional[float],
        reasoning: str
    ) -> Trade:
        """Create a trade record in the database"""
        try:
            db = next(get_db())
            
            trade = Trade(
                id=trade_id,
                symbol=symbol,
                trade_type=TradeType.BUY if side.upper() == "BUY" else TradeType.SELL,
                size=Decimal(str(size)),
                entry_price=Decimal(str(entry_price)) if entry_price else None,
                stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                take_profit=Decimal(str(take_profit)) if take_profit else None,
                reasoning=reasoning,
                status=TradeStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            db.add(trade)
            db.commit()
            db.refresh(trade)
            
            logger.info(f"Created trade record: {trade_id}")
            return trade
            
        except Exception as e:
            logger.error(f"Error creating trade record: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    async def _create_order_record(
        self,
        order_id: str,
        trade_id: str,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float],
        order_type: str
    ):
        """Create an order record in the database"""
        try:
            db = next(get_db())
            
            order = Order(
                id=order_id,
                trade_id=trade_id,
                symbol=symbol,
                side=side.upper(),
                size=Decimal(str(size)),
                price=Decimal(str(price)) if price else None,
                order_type=OrderType(order_type.upper()),
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            db.add(order)
            db.commit()
            
            logger.info(f"Created order record: {order_id}")
            
        except Exception as e:
            logger.error(f"Error creating order record: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _get_trade_record(self, trade_id: str) -> Optional[Trade]:
        """Get trade record from database"""
        try:
            db = next(get_db())
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            return trade
        except Exception as e:
            logger.error(f"Error getting trade record: {e}")
            return None
        finally:
            db.close()
    
    async def _update_trade_status(self, trade_id: str, status: TradeStatus):
        """Update trade status in database"""
        try:
            db = next(get_db())
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.status = status
                trade.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Updated trade {trade_id} status to {status.value}")
        except Exception as e:
            logger.error(f"Error updating trade status: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _update_trade_closure(
        self,
        trade_id: str,
        exit_price: float,
        realized_pnl: float,
        exit_type: str
    ):
        """Update trade with closure information"""
        try:
            db = next(get_db())
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.exit_price = Decimal(str(exit_price))
                trade.realized_pnl = Decimal(str(realized_pnl))
                trade.exit_reason = exit_type
                trade.status = TradeStatus.CLOSED
                trade.closed_at = datetime.utcnow()
                trade.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Updated trade {trade_id} closure")
        except Exception as e:
            logger.error(f"Error updating trade closure: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _calculate_realized_pnl(self, trade: Trade, exit_price: float) -> float:
        """Calculate realized PnL for a trade"""
        try:
            entry_price = float(trade.entry_price) if trade.entry_price else 0
            size = float(trade.size)
            
            if trade.trade_type == TradeType.BUY:
                return (exit_price - entry_price) * size
            else:  # SELL
                return (entry_price - exit_price) * size
                
        except Exception as e:
            logger.error(f"Error calculating realized PnL: {e}")
            return 0.0
    
    async def _check_account_balance(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float]
    ) -> Dict[str, Any]:
        """Check if account has sufficient balance for the trade"""
        try:
            # Get account balance
            balance = await self.delta_connector.get_account_balance()
            
            # Calculate required margin/balance
            current_price = price or await self.delta_connector.get_current_price(symbol)
            required_balance = size * current_price
            
            # For margin trading, check available margin
            if side.upper() == "BUY":
                available = balance.get("available_balance", 0)
            else:
                # For short selling, check if symbol can be borrowed
                available = balance.get("available_balance", 0)
            
            if available >= required_balance:
                return {"sufficient": True}
            else:
                return {
                    "sufficient": False,
                    "reason": f"Insufficient balance: {available} < {required_balance}"
                }
                
        except Exception as e:
            logger.error(f"Error checking account balance: {e}")
            return {
                "sufficient": False,
                "reason": f"Balance check error: {str(e)}"
            }
    
    async def _load_existing_orders(self):
        """Load existing orders from database"""
        try:
            async for db in get_db():
                active_orders = db.query(Order).filter(
                    Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
                ).all()
                
                for order in active_orders:
                    self.active_orders[order.id] = {
                        "order_id": order.id,
                        "trade_id": order.trade_id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "size": float(order.size),
                        "price": float(order.price) if order.price else None,
                        "order_type": order.order_type.value,
                        "status": order.status.value
                    }
                
                logger.info(f"Loaded {len(self.active_orders)} existing orders")
                break  # Exit after getting the data
                
        except Exception as e:
            logger.error(f"Error loading existing orders: {e}")
    
    async def _cancel_related_orders(self, trade_id: str):
        """Cancel all orders related to a trade"""
        try:
            related_orders = await self._get_related_orders(trade_id)
            
            for order in related_orders:
                await self.delta_connector.cancel_order(order["order_id"])
                logger.info(f"Cancelled order {order['order_id']} for trade {trade_id}")
                
        except Exception as e:
            logger.error(f"Error cancelling related orders for {trade_id}: {e}")
    
    async def _get_related_orders(self, trade_id: str) -> List[Dict[str, Any]]:
        """Get all orders related to a trade"""
        db = None
        try:
            db = next(get_db())
            orders = db.query(Order).filter(
                Order.trade_id == trade_id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
            ).all()
            
            return [
                {
                    "order_id": order.id,
                    "order_type": order.order_type.value,
                    "symbol": order.symbol,
                    "side": order.side,
                    "size": float(order.size),
                    "price": float(order.price) if order.price else None
                }
                for order in orders
            ]
            
        except Exception as e:
            logger.error(f"Error getting related orders: {e}")
            return []
        finally:
            if db:
                db.close()
    
    async def _cancel_stop_loss_order(self, trade_id: str):
        """Cancel stop loss order for a trade"""
        db = None
        try:
            db = next(get_db())
            stop_order = db.query(Order).filter(
                Order.trade_id == trade_id,
                Order.order_type == OrderType.STOP_LOSS,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
            ).first()
            
            if stop_order:
                await self.delta_connector.cancel_order(stop_order.id)
                logger.info(f"Cancelled stop loss order for trade {trade_id}")
                
        except Exception as e:
            logger.error(f"Error cancelling stop loss order: {e}")
        finally:
            if db:
                db.close()
    
    async def _cancel_take_profit_order(self, trade_id: str):
        """Cancel take profit order for a trade"""
        db = None
        try:
            db = next(get_db())
            tp_order = db.query(Order).filter(
                Order.trade_id == trade_id,
                Order.order_type == OrderType.TAKE_PROFIT,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
            ).first()
            
            if tp_order:
                await self.delta_connector.cancel_order(tp_order.id)
                logger.info(f"Cancelled take profit order for trade {trade_id}")
                
        except Exception as e:
            logger.error(f"Error cancelling take profit order: {e}")
        finally:
            if db:
                db.close()
    
    async def _update_trade_stop_loss(self, trade_id: str, new_stop_loss: float):
        """Update stop loss in trade record"""
        db = None
        try:
            db = next(get_db())
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.stop_loss = Decimal(str(new_stop_loss))
                trade.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Error updating trade stop loss: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()
    
    async def _update_trade_size(self, trade_id: str, new_size: float):
        """Update trade size in record"""
        db = None
        try:
            db = next(get_db())
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.size = Decimal(str(new_size))
                trade.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Error updating trade size: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()

