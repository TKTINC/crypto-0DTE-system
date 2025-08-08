"""
Autonomous Trading Orchestrator for Crypto-0DTE System

The central orchestrator that manages the complete autonomous trading lifecycle:
- Continuous market monitoring
- Automated signal generation
- Risk-managed trade execution
- Position management and monitoring
- Automated exit strategies

This is the core engine that makes the system truly autonomous.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json

from app.services.exchanges.delta_exchange import DeltaExchangeConnector
from app.services.trade_execution_engine import TradeExecutionEngine
from app.services.position_manager import PositionManager
from app.services.risk_manager import RiskManager
from app.api.v1.signals import generate_signal
from app.database import get_db
from app.config import Settings
from app.models.signal import Signal, SignalType, SignalStatus
from app.models.trade import Trade, TradeStatus, TradeType

logger = logging.getLogger(__name__)


class AutonomousTradingOrchestrator:
    """
    Central orchestrator for autonomous trading operations.
    
    This service runs continuously in the background and manages:
    - Market data monitoring
    - Signal generation and validation
    - Trade execution and management
    - Risk management and position sizing
    - Automated profit taking and stop losses
    """
    
    def __init__(self):
        self.settings = Settings()
        self.is_running = False
        self.is_trading_enabled = True
        
        # Core services
        self.delta_connector = DeltaExchangeConnector()
        self.trade_executor = TradeExecutionEngine()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager()
        
        # Configuration
        self.trading_pairs = ["BTC-USDT", "ETH-USDT"]
        self.signal_generation_interval = 300  # 5 minutes
        self.position_check_interval = 30      # 30 seconds
        self.market_check_interval = 60        # 1 minute
        
        # State tracking
        self.last_signal_generation = {}
        self.active_positions = {}
        self.system_metrics = {
            "signals_generated": 0,
            "trades_executed": 0,
            "positions_managed": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "uptime_start": datetime.utcnow()
        }
        
        logger.info("Autonomous Trading Orchestrator initialized")
    
    async def start(self):
        """Start the autonomous trading orchestrator"""
        if self.is_running:
            logger.warning("Orchestrator is already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting Autonomous Trading Orchestrator")
        
        # Initialize services
        await self._initialize_services()
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._market_monitoring_loop()),
            asyncio.create_task(self._signal_generation_loop()),
            asyncio.create_task(self._position_management_loop()),
            asyncio.create_task(self._risk_monitoring_loop()),
            asyncio.create_task(self._system_health_loop())
        ]
        
        logger.info("✅ All autonomous trading loops started")
        
        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in orchestrator tasks: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the autonomous trading orchestrator"""
        self.is_running = False
        logger.info("🛑 Stopping Autonomous Trading Orchestrator")
        
        # Close all positions if configured to do so
        if self.settings.CLOSE_POSITIONS_ON_SHUTDOWN:
            await self._emergency_close_all_positions()
        
        # Cleanup services
        await self._cleanup_services()
        
        logger.info("✅ Autonomous Trading Orchestrator stopped")
    
    async def _initialize_services(self):
        """Initialize all required services"""
        try:
            # Initialize Delta Exchange connection
            await self.delta_connector.initialize()
            
            # Initialize trade executor
            await self.trade_executor.initialize()
            
            # Initialize position manager
            await self.position_manager.initialize()
            
            # Initialize risk manager
            await self.risk_manager.initialize()
            
            # Load existing positions
            await self._load_existing_positions()
            
            logger.info("✅ All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def _cleanup_services(self):
        """Cleanup all services"""
        try:
            await self.delta_connector.cleanup()
            await self.trade_executor.cleanup()
            await self.position_manager.cleanup()
            await self.risk_manager.cleanup()
            
            logger.info("✅ All services cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _market_monitoring_loop(self):
        """Continuously monitor market conditions"""
        logger.info("📊 Starting market monitoring loop")
        
        while self.is_running:
            try:
                # Monitor market conditions for each trading pair
                for symbol in self.trading_pairs:
                    await self._check_market_conditions(symbol)
                
                # Check for emergency market conditions
                await self._check_emergency_conditions()
                
                await asyncio.sleep(self.market_check_interval)
                
            except Exception as e:
                logger.error(f"Error in market monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _signal_generation_loop(self):
        """Continuously generate and process trading signals"""
        logger.info("🧠 Starting signal generation loop")
        
        while self.is_running:
            try:
                # Generate signals for each trading pair
                for symbol in self.trading_pairs:
                    await self._generate_and_process_signal(symbol)
                
                await asyncio.sleep(self.signal_generation_interval)
                
            except Exception as e:
                logger.error(f"Error in signal generation loop: {e}")
                await asyncio.sleep(60)
    
    async def _position_management_loop(self):
        """Continuously manage active positions"""
        logger.info("📈 Starting position management loop")
        
        while self.is_running:
            try:
                # Update position data from exchange
                await self._update_positions_from_exchange()
                
                # Manage each active position
                for position_id, position in self.active_positions.items():
                    await self._manage_position(position)
                
                # Update system metrics
                await self._update_system_metrics()
                
                await asyncio.sleep(self.position_check_interval)
                
            except Exception as e:
                logger.error(f"Error in position management loop: {e}")
                await asyncio.sleep(30)
    
    async def _risk_monitoring_loop(self):
        """Continuously monitor risk levels"""
        logger.info("🛡️ Starting risk monitoring loop")
        
        while self.is_running:
            try:
                # Check portfolio risk levels
                risk_assessment = await self.risk_manager.assess_portfolio_risk()
                
                if risk_assessment["risk_level"] == "HIGH":
                    logger.warning(f"High risk detected: {risk_assessment}")
                    await self._handle_high_risk_situation(risk_assessment)
                
                # Check individual position risks
                for position_id, position in self.active_positions.items():
                    position_risk = await self.risk_manager.assess_position_risk(position)
                    
                    if position_risk["action_required"]:
                        await self._handle_position_risk(position, position_risk)
                
                await asyncio.sleep(60)  # Check risk every minute
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _system_health_loop(self):
        """Monitor system health and performance"""
        logger.info("💚 Starting system health monitoring loop")
        
        while self.is_running:
            try:
                # Check API connections
                delta_health = await self.delta_connector.health_check()
                
                # Log system status
                if delta_health["status"] == "healthy":
                    logger.debug("System health check: All systems operational")
                else:
                    logger.warning(f"System health issue: {delta_health}")
                
                # Update uptime metrics
                self.system_metrics["uptime_hours"] = (
                    datetime.utcnow() - self.system_metrics["uptime_start"]
                ).total_seconds() / 3600
                
                await asyncio.sleep(300)  # Health check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in system health loop: {e}")
                await asyncio.sleep(300)
    
    async def _generate_and_process_signal(self, symbol: str):
        """Generate and process a trading signal for a symbol"""
        try:
            # Check if we should generate a signal (rate limiting)
            last_generation = self.last_signal_generation.get(symbol)
            if last_generation and (datetime.utcnow() - last_generation).seconds < 300:
                return
            
            # Generate AI signal
            logger.info(f"🧠 Generating AI signal for {symbol}")
            signal_response = await generate_signal(symbol)
            
            if not signal_response or signal_response.get("signal_type") == "HOLD":
                logger.debug(f"No actionable signal for {symbol}")
                return
            
            # Validate signal with risk management
            is_valid, validation_reason = await self.risk_manager.validate_signal(signal_response)
            
            if not is_valid:
                logger.info(f"Signal rejected for {symbol}: {validation_reason}")
                return
            
            # Check if we already have a position in this symbol
            existing_position = await self._get_existing_position(symbol)
            if existing_position:
                logger.info(f"Already have position in {symbol}, skipping signal")
                return
            
            # Execute the signal
            await self._execute_signal(signal_response)
            
            # Update tracking
            self.last_signal_generation[symbol] = datetime.utcnow()
            self.system_metrics["signals_generated"] += 1
            
            logger.info(f"✅ Signal processed for {symbol}: {signal_response['signal_type']}")
            
        except Exception as e:
            logger.error(f"Error processing signal for {symbol}: {e}")
    
    async def _execute_signal(self, signal: Dict[str, Any]):
        """Execute a validated trading signal"""
        try:
            logger.info(f"🎯 Executing signal: {signal['symbol']} {signal['signal_type']}")
            
            # Calculate position size
            position_size = await self.risk_manager.calculate_position_size(
                signal["symbol"],
                signal["entry_price"],
                signal.get("stop_loss")
            )
            
            if position_size <= 0:
                logger.warning(f"Invalid position size calculated: {position_size}")
                return
            
            # Execute trade
            trade_result = await self.trade_executor.execute_trade(
                symbol=signal["symbol"],
                side=signal["signal_type"],
                size=position_size,
                entry_price=signal["entry_price"],
                stop_loss=signal.get("stop_loss"),
                take_profit=signal.get("take_profit"),
                reasoning=signal.get("reasoning", "AI-generated signal")
            )
            
            if trade_result["success"]:
                # Track the new position
                self.active_positions[trade_result["trade_id"]] = trade_result
                self.system_metrics["trades_executed"] += 1
                
                logger.info(f"✅ Trade executed successfully: {trade_result['trade_id']}")
            else:
                logger.error(f"❌ Trade execution failed: {trade_result['error']}")
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    async def _manage_position(self, position: Dict[str, Any]):
        """Manage an active trading position"""
        try:
            # Get current market price
            current_price = await self.delta_connector.get_current_price(position["symbol"])
            
            # Update position with current market data
            position["current_price"] = current_price
            position["unrealized_pnl"] = self._calculate_unrealized_pnl(position, current_price)
            
            # Check exit conditions
            exit_decision = await self.position_manager.check_exit_conditions(position)
            
            if exit_decision["should_exit"]:
                logger.info(f"🚪 Exiting position {position['trade_id']}: {exit_decision['reason']}")
                
                # Execute exit
                exit_result = await self.trade_executor.close_position(
                    position["trade_id"],
                    exit_decision["exit_type"],
                    exit_decision.get("exit_price")
                )
                
                if exit_result["success"]:
                    # Remove from active positions
                    del self.active_positions[position["trade_id"]]
                    
                    # Update metrics
                    self.system_metrics["positions_managed"] += 1
                    self.system_metrics["total_pnl"] += exit_result["realized_pnl"]
                    
                    logger.info(f"✅ Position closed: {exit_result['realized_pnl']:.2f} PnL")
                else:
                    logger.error(f"❌ Failed to close position: {exit_result['error']}")
            
            # Update stop loss if needed
            elif exit_decision.get("update_stop_loss"):
                await self._update_stop_loss(position, exit_decision["new_stop_loss"])
            
        except Exception as e:
            logger.error(f"Error managing position {position.get('trade_id')}: {e}")
    
    async def _check_market_conditions(self, symbol: str):
        """Check market conditions for a symbol"""
        try:
            market_data = await self.delta_connector.get_market_data(symbol)
            
            # Check for extreme volatility
            if market_data.get("volatility", 0) > 0.1:  # 10% volatility threshold
                logger.warning(f"High volatility detected in {symbol}: {market_data['volatility']:.2%}")
            
            # Check for low liquidity
            if market_data.get("volume_24h", 0) < 1000000:  # $1M volume threshold
                logger.warning(f"Low liquidity detected in {symbol}: ${market_data['volume_24h']:,.0f}")
            
        except Exception as e:
            logger.error(f"Error checking market conditions for {symbol}: {e}")
    
    async def _check_emergency_conditions(self):
        """Check for emergency market conditions"""
        try:
            # Check overall portfolio risk
            portfolio_risk = await self.risk_manager.get_portfolio_risk_level()
            
            if portfolio_risk >= 0.8:  # 80% risk threshold
                logger.critical(f"EMERGENCY: Portfolio risk at {portfolio_risk:.1%}")
                
                # Consider emergency actions
                if portfolio_risk >= 0.9:  # 90% emergency threshold
                    await self._emergency_close_all_positions()
            
        except Exception as e:
            logger.error(f"Error checking emergency conditions: {e}")
    
    async def _emergency_close_all_positions(self):
        """Emergency close all positions"""
        logger.critical("🚨 EMERGENCY: Closing all positions")
        
        for position_id, position in list(self.active_positions.items()):
            try:
                await self.trade_executor.emergency_close_position(position_id)
                del self.active_positions[position_id]
                logger.info(f"Emergency closed position: {position_id}")
            except Exception as e:
                logger.error(f"Failed to emergency close position {position_id}: {e}")
    
    async def _load_existing_positions(self):
        """Load existing positions from database"""
        try:
            # Get active trades from database
            db = next(get_db())
            active_trades = db.query(Trade).filter(
                Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIALLY_FILLED])
            ).all()
            
            for trade in active_trades:
                self.active_positions[trade.id] = {
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.trade_type.value,
                    "size": float(trade.size),
                    "entry_price": float(trade.entry_price),
                    "stop_loss": float(trade.stop_loss) if trade.stop_loss else None,
                    "take_profit": float(trade.take_profit) if trade.take_profit else None,
                    "created_at": trade.created_at
                }
            
            logger.info(f"Loaded {len(self.active_positions)} existing positions")
            
        except Exception as e:
            logger.error(f"Error loading existing positions: {e}")
    
    async def _update_positions_from_exchange(self):
        """Update position data from exchange"""
        try:
            exchange_positions = await self.delta_connector.get_positions()
            
            # Sync with our tracked positions
            for position_id, tracked_position in self.active_positions.items():
                symbol = tracked_position["symbol"]
                
                # Find corresponding exchange position
                exchange_position = next(
                    (p for p in exchange_positions if p["symbol"] == symbol),
                    None
                )
                
                if exchange_position:
                    tracked_position.update({
                        "current_size": exchange_position["size"],
                        "current_price": exchange_position["mark_price"],
                        "unrealized_pnl": exchange_position["unrealized_pnl"]
                    })
            
        except Exception as e:
            logger.error(f"Error updating positions from exchange: {e}")
    
    def _calculate_unrealized_pnl(self, position: Dict[str, Any], current_price: float) -> float:
        """Calculate unrealized PnL for a position"""
        try:
            entry_price = position["entry_price"]
            size = position["size"]
            side = position["side"]
            
            if side.upper() == "BUY":
                return (current_price - entry_price) * size
            else:  # SELL
                return (entry_price - current_price) * size
                
        except Exception as e:
            logger.error(f"Error calculating unrealized PnL: {e}")
            return 0.0
    
    async def _get_existing_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Check if we have an existing position in a symbol"""
        for position in self.active_positions.values():
            if position["symbol"] == symbol:
                return position
        return None
    
    async def _update_stop_loss(self, position: Dict[str, Any], new_stop_loss: float):
        """Update stop loss for a position"""
        try:
            result = await self.trade_executor.update_stop_loss(
                position["trade_id"],
                new_stop_loss
            )
            
            if result["success"]:
                position["stop_loss"] = new_stop_loss
                logger.info(f"Updated stop loss for {position['trade_id']}: {new_stop_loss}")
            else:
                logger.error(f"Failed to update stop loss: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error updating stop loss: {e}")
    
    async def _handle_high_risk_situation(self, risk_assessment: Dict[str, Any]):
        """Handle high risk portfolio situation"""
        logger.warning(f"Handling high risk situation: {risk_assessment}")
        
        # Reduce position sizes
        for position_id, position in self.active_positions.items():
            if position.get("unrealized_pnl", 0) < 0:  # Losing positions
                # Tighten stop losses
                current_stop = position.get("stop_loss")
                if current_stop:
                    new_stop = await self.risk_manager.calculate_tighter_stop_loss(position)
                    if new_stop != current_stop:
                        await self._update_stop_loss(position, new_stop)
    
    async def _handle_position_risk(self, position: Dict[str, Any], risk_assessment: Dict[str, Any]):
        """Handle individual position risk"""
        logger.info(f"Handling position risk for {position['trade_id']}: {risk_assessment}")
        
        if risk_assessment["action"] == "CLOSE":
            await self.trade_executor.close_position(position["trade_id"], "RISK_MANAGEMENT")
        elif risk_assessment["action"] == "REDUCE":
            await self.trade_executor.reduce_position_size(
                position["trade_id"],
                risk_assessment["new_size"]
            )
        elif risk_assessment["action"] == "UPDATE_STOP":
            await self._update_stop_loss(position, risk_assessment["new_stop_loss"])
    
    async def _update_system_metrics(self):
        """Update system performance metrics"""
        try:
            # Calculate win rate
            if self.system_metrics["trades_executed"] > 0:
                # This would need to query completed trades from database
                # For now, using a placeholder calculation
                winning_trades = max(0, self.system_metrics["trades_executed"] - len(self.active_positions))
                self.system_metrics["win_rate"] = winning_trades / self.system_metrics["trades_executed"]
            
            # Update other metrics as needed
            self.system_metrics["active_positions"] = len(self.active_positions)
            self.system_metrics["last_updated"] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    # Public API methods for external access
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "is_running": self.is_running,
            "is_trading_enabled": self.is_trading_enabled,
            "active_positions": len(self.active_positions),
            "trading_pairs": self.trading_pairs,
            "metrics": self.system_metrics,
            "last_updated": datetime.utcnow()
        }
    
    async def enable_trading(self):
        """Enable autonomous trading"""
        self.is_trading_enabled = True
        logger.info("✅ Autonomous trading enabled")
    
    async def disable_trading(self):
        """Disable autonomous trading"""
        self.is_trading_enabled = False
        logger.info("⏸️ Autonomous trading disabled")
    
    async def get_active_positions(self) -> Dict[str, Any]:
        """Get all active positions"""
        return self.active_positions.copy()
    
    async def force_close_position(self, position_id: str) -> Dict[str, Any]:
        """Force close a specific position"""
        if position_id in self.active_positions:
            result = await self.trade_executor.close_position(position_id, "MANUAL")
            if result["success"]:
                del self.active_positions[position_id]
            return result
        else:
            return {"success": False, "error": "Position not found"}


# Global orchestrator instance
orchestrator = AutonomousTradingOrchestrator()

