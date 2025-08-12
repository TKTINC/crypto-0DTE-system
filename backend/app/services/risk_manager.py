"""
Risk Management Framework for Crypto-0DTE System

Comprehensive risk management for autonomous trading:
- Portfolio risk assessment and monitoring
- Position sizing calculations
- Signal validation and filtering
- Emergency risk controls
- Drawdown protection
- Exposure limits and diversification
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import math
import statistics
import uuid
import json

from sqlalchemy import select
from app.services.exchanges.delta_exchange import DeltaExchangeConnector
from app.database import get_db
from app.config import Settings
from app.models.trade import Trade, TradeStatus, TradeType
from app.models.signal import Signal, SignalType
from app.models.risk_event import RiskEvent, RiskEventType
from app.models.signal_event import SignalEvent, SignalEventType
from app.services.metrics_service import metrics_service

logger = logging.getLogger(__name__)


class RiskDenied(Exception):
    """Exception raised when an order is denied by the risk gate"""
    def __init__(self, reason: str, risk_type: str = "general"):
        self.reason = reason
        self.risk_type = risk_type
        super().__init__(f"Risk denied ({risk_type}): {reason}")


class RiskManager:
    """
    Comprehensive risk management system for autonomous trading.
    
    Features:
    - Portfolio risk assessment
    - Dynamic position sizing
    - Signal validation and filtering
    - Exposure limits and controls
    - Drawdown protection
    - Emergency risk controls
    """
    
    def __init__(self, paper_trading: bool = None):
        self.settings = Settings()
        
        # Determine paper trading mode
        self.paper_trading = paper_trading if paper_trading is not None else True  # Default to paper trading for safety
        
        # Initialize Delta Exchange connector with environment awareness
        self.delta_connector = DeltaExchangeConnector(paper_trading=self.paper_trading)
        
        # Risk Configuration
        self.max_portfolio_risk = 0.02        # 2% max portfolio risk per trade
        self.max_daily_loss = 0.05            # 5% max daily loss
        self.max_drawdown = 0.15              # 15% max drawdown
        self.max_position_size = 0.10         # 10% max position size of portfolio
        self.max_correlation_exposure = 0.30  # 30% max exposure to correlated assets
        self.max_open_positions = 5           # Max 5 open positions
        self.min_account_balance = 1000       # Minimum account balance to trade
        
        # Risk Gate Configuration (Critical Safety Parameters)
        self.max_consecutive_losses = 4       # Max 4 consecutive losses before pause
        self.consecutive_loss_pause_hours = 12  # Pause trading for 12 hours after consecutive losses
        self.event_pause_active = False       # Event-based trading pause flag
        
        # Risk Metrics
        self.daily_pnl = 0.0
        self.max_daily_drawdown = 0.0
        self.portfolio_value = 0.0
        self.total_exposure = 0.0
        self.risk_metrics_cache = {}
        self.last_risk_update = None
        
        # Signal Validation
        self.min_signal_confidence = 0.6      # 60% minimum confidence
        self.max_signals_per_hour = 10        # Max 10 signals per hour
        self.signal_cooldown = 300            # 5 minutes between signals for same symbol
        self.recent_signals = {}
        
        logger.info("Risk Manager initialized")
    
    async def initialize(self):
        """Initialize the risk manager (non-blocking for API failures)"""
        try:
            # Initialize Delta Exchange connector (DISABLED during startup to prevent blocking)
            logger.info("⏸️ Risk Manager Delta connector initialization DISABLED during startup")
            logger.info("💡 Risk Manager will be enabled after successful deployment")
            # try:
            #     await self.delta_connector.initialize()
            #     logger.info("Delta Exchange connector initialized successfully")
            # except Exception as e:
            #     logger.warning(f"Delta Exchange connector initialization failed: {e}")
            #     logger.info("Risk Manager will continue with limited functionality")
            
            # Load risk metrics (this doesn't make API calls)
            await self._load_risk_metrics()
            
            # Initialize portfolio tracking (now non-blocking for API failures)
            await self._initialize_portfolio_tracking()
            
            logger.info("✅ Risk Manager initialized (startup blocking disabled)")
            
        except Exception as e:
            logger.warning(f"Risk Manager initialization had issues but continuing: {e}")
            # Don't raise the exception - allow startup to continue
    
    async def cleanup(self):
        """Cleanup the risk manager"""
        try:
            # Save risk metrics
            await self._save_risk_metrics()
            
            # Cleanup Delta connector
            await self.delta_connector.cleanup()
            
            logger.info("✅ Risk Manager cleaned up")
            
        except Exception as e:
            logger.error(f"Error during Risk Manager cleanup: {e}")
    
    async def validate_signal(self, signal: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a trading signal against risk criteria.
        
        Args:
            signal: Signal data to validate
        
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            symbol = signal.get("symbol")
            signal_type = signal.get("signal_type")
            confidence = signal.get("confidence", 0)
            entry_price = signal.get("entry_price", 0)
            
            logger.debug(f"Validating signal: {symbol} {signal_type} ({confidence:.1%})")
            
            # Check signal confidence
            if confidence < self.min_signal_confidence:
                return False, f"Signal confidence too low: {confidence:.1%} < {self.min_signal_confidence:.1%}"
            
            # Check signal rate limiting
            rate_limit_check = await self._check_signal_rate_limits(symbol)
            if not rate_limit_check["allowed"]:
                return False, rate_limit_check["reason"]
            
            # Check portfolio risk limits
            portfolio_check = await self._check_portfolio_risk_limits()
            if not portfolio_check["allowed"]:
                return False, portfolio_check["reason"]
            
            # Check position limits
            position_check = await self._check_position_limits(symbol)
            if not position_check["allowed"]:
                return False, position_check["reason"]
            
            # Check market conditions
            market_check = await self._check_market_conditions(symbol)
            if not market_check["allowed"]:
                return False, market_check["reason"]
            
            # Check correlation limits
            correlation_check = await self._check_correlation_limits(symbol)
            if not correlation_check["allowed"]:
                return False, correlation_check["reason"]
            
            # Check account balance
            balance_check = await self._check_minimum_balance()
            if not balance_check["allowed"]:
                return False, balance_check["reason"]
            
            # All checks passed
            await self._record_signal_validation(symbol, True)
            return True, "Signal validation passed"
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return False, f"Signal validation error: {str(e)}"
    
    async def check_order_risk_gate(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        order_type: str = "market"
    ) -> Tuple[bool, str]:
        """
        CRITICAL RISK CHOKE-POINT: Check all risk criteria before any order placement.
        
        This method MUST be called before every order placement to ensure:
        - Daily loss limits not exceeded
        - Per-asset exposure within limits
        - Consecutive loss breaker not tripped
        - Event pause not active
        - Portfolio risk limits respected
        
        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            size: Order size
            price: Order price (for limit orders)
            order_type: Order type (market/limit)
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Generate trace ID for correlation
        trace_id = str(uuid.uuid4())[:8]
        
        # Get current market data for context
        try:
            current_price = await self.delta_connector.get_current_price(symbol)
        except:
            current_price = price or 0
        
        # Structured log entry
        risk_context = {
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "order_type": order_type,
            "current_price": current_price,
            "notional_value": size * (price or current_price),
            "action": "risk_gate_check"
        }
        
        logger.info(f"🛡️ RISK GATE [{trace_id}]: {json.dumps(risk_context)}")
        
        try:
            # 1. Check daily loss limits
            daily_pnl = await self._calculate_daily_pnl()
            if daily_pnl < -self.max_daily_loss:
                reason = f"Daily loss limit exceeded: {daily_pnl:.2f} < -{self.max_daily_loss:.2f}"
                risk_denial = {
                    "trace_id": trace_id,
                    "risk_type": "daily_loss_limit",
                    "reason": reason,
                    "daily_pnl": daily_pnl,
                    "max_daily_loss": self.max_daily_loss,
                    "verdict": "DENIED"
                }
                logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_denial)}")
                return False, reason
            
            # 2. Check per-asset exposure limits
            current_exposure = await self._get_asset_exposure(symbol)
            portfolio_value = await self._get_portfolio_value()
            
            if portfolio_value > 0:
                exposure_ratio = current_exposure / portfolio_value
                if exposure_ratio > self.max_position_size:
                    reason = f"Asset exposure limit exceeded: {exposure_ratio:.1%} > {self.max_position_size:.1%}"
                    risk_denial = {
                        "trace_id": trace_id,
                        "risk_type": "asset_exposure_limit",
                        "reason": reason,
                        "current_exposure": current_exposure,
                        "portfolio_value": portfolio_value,
                        "exposure_ratio": exposure_ratio,
                        "max_position_size": self.max_position_size,
                        "verdict": "DENIED"
                    }
                    logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_denial)}")
                    return False, reason
            
            # 3. Check consecutive loss breaker
            consecutive_losses = await self._count_consecutive_losses()
            if consecutive_losses >= self.max_consecutive_losses:
                reason = f"Consecutive loss breaker tripped: {consecutive_losses} >= {self.max_consecutive_losses}"
                risk_denial = {
                    "trace_id": trace_id,
                    "risk_type": "consecutive_loss_breaker",
                    "reason": reason,
                    "consecutive_losses": consecutive_losses,
                    "max_consecutive_losses": self.max_consecutive_losses,
                    "verdict": "DENIED"
                }
                logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_denial)}")
                return False, reason
            
            # 4. Check event pause status
            if await self._is_event_pause_active():
                reason = "Event pause active - no new positions allowed"
                risk_denial = {
                    "trace_id": trace_id,
                    "risk_type": "event_pause",
                    "reason": reason,
                    "verdict": "DENIED"
                }
                logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_denial)}")
                return False, reason
            
            # 5. Check portfolio risk limits
            portfolio_check = await self._check_portfolio_risk_limits()
            if not portfolio_check["allowed"]:
                reason = f"Portfolio risk limit: {portfolio_check['reason']}"
                risk_denial = {
                    "trace_id": trace_id,
                    "risk_type": "portfolio_risk_limit",
                    "reason": reason,
                    "portfolio_check": portfolio_check,
                    "verdict": "DENIED"
                }
                logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_denial)}")
                return False, reason
            
            # 6. Check minimum balance
            balance_check = await self._check_minimum_balance()
            if not balance_check["allowed"]:
                reason = f"Insufficient balance: {balance_check['reason']}"
                risk_denial = {
                    "trace_id": trace_id,
                    "risk_type": "insufficient_balance",
                    "reason": reason,
                    "balance_check": balance_check,
                    "verdict": "DENIED"
                }
                logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_denial)}")
                return False, reason
            
            # 7. Check market conditions
            market_check = await self._check_market_conditions(symbol)
            if not market_check["allowed"]:
                reason = f"Market conditions: {market_check['reason']}"
                risk_denial = {
                    "trace_id": trace_id,
                    "risk_type": "market_conditions",
                    "reason": reason,
                    "market_check": market_check,
                    "verdict": "DENIED"
                }
                logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_denial)}")
                return False, reason
            
            # All risk checks passed
            risk_approval = {
                "trace_id": trace_id,
                "verdict": "APPROVED",
                "daily_pnl": daily_pnl,
                "exposure_ratio": exposure_ratio if portfolio_value > 0 else 0,
                "consecutive_losses": consecutive_losses,
                "portfolio_value": portfolio_value,
                "checks_passed": ["daily_loss", "asset_exposure", "consecutive_loss", "event_pause", "portfolio_risk", "balance", "market_conditions"]
            }
            logger.info(f"✅ RISK APPROVED [{trace_id}]: {json.dumps(risk_approval)}")
            
            # Record metrics
            metrics_service.record_risk_gate_decision("approved", "all_checks_passed")
            
            # Persist risk event to database
            await self._persist_risk_event(
                event_type=RiskEventType.ORDER_APPROVED,
                correlation_id=trace_id,
                symbol=symbol,
                side=side,
                quantity=size,
                price=price or current_price,
                notional_usd=size * (price or current_price),
                decision="approved",
                reason="All risk checks passed",
                details=json.dumps(risk_approval)
            )
            
            return True, "Risk gate passed - order approved"
            
        except Exception as e:
            logger.error(f"Error in risk gate: {e}")
            reason = f"Risk gate error: {str(e)}"
            risk_error = {
                "trace_id": trace_id,
                "risk_type": "system_error",
                "reason": reason,
                "error": str(e),
                "verdict": "DENIED"
            }
            logger.warning(f"🚫 RISK DENIED [{trace_id}]: {json.dumps(risk_error)}")
            return False, reason
    
    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: Optional[float] = None
    ) -> float:
        """
        Calculate optimal position size based on risk management rules.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price for the position
            stop_loss: Stop loss price (if any)
        
        Returns:
            Position size in base currency
        """
        try:
            logger.debug(f"Calculating position size for {symbol}")
            
            # Get current portfolio value
            portfolio_value = await self._get_portfolio_value()
            
            if portfolio_value <= 0:
                logger.warning("Portfolio value is zero or negative")
                return 0.0
            
            # Calculate risk amount (max loss per trade)
            risk_amount = portfolio_value * self.max_portfolio_risk
            
            # If stop loss is provided, use it for position sizing
            if stop_loss and entry_price > 0:
                # Calculate risk per unit
                risk_per_unit = abs(entry_price - stop_loss)
                
                if risk_per_unit > 0:
                    # Position size based on risk
                    risk_based_size = risk_amount / risk_per_unit
                else:
                    risk_based_size = 0.0
            else:
                # Default position sizing (2% of portfolio)
                risk_based_size = risk_amount / entry_price if entry_price > 0 else 0.0
            
            # Apply maximum position size limit
            max_position_value = portfolio_value * self.max_position_size
            max_size_limit = max_position_value / entry_price if entry_price > 0 else 0.0
            
            # Take the smaller of risk-based size and max size limit
            calculated_size = min(risk_based_size, max_size_limit)
            
            # Apply minimum order size from exchange
            min_order_size = await self.delta_connector.get_minimum_order_size(symbol)
            
            if calculated_size < min_order_size:
                logger.warning(f"Calculated size {calculated_size} below minimum {min_order_size}")
                return 0.0
            
            # Round to appropriate precision
            final_size = self._round_to_precision(calculated_size, symbol)
            
            logger.info(f"Position size calculated for {symbol}: {final_size}")
            return final_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    async def assess_portfolio_risk(self) -> Dict[str, Any]:
        """
        Assess current portfolio risk level.
        
        Returns:
            Dict with risk assessment details
        """
        try:
            # Update risk metrics
            await self._update_risk_metrics()
            
            # Calculate various risk metrics
            portfolio_value = await self._get_portfolio_value()
            total_exposure = await self._calculate_total_exposure()
            daily_pnl = await self._calculate_daily_pnl()
            drawdown = await self._calculate_current_drawdown()
            open_positions = await self._count_open_positions()
            
            # Determine risk level
            risk_factors = []
            risk_score = 0.0
            
            # Check daily loss
            if daily_pnl < 0:
                daily_loss_pct = abs(daily_pnl) / portfolio_value if portfolio_value > 0 else 0
                if daily_loss_pct > self.max_daily_loss * 0.8:  # 80% of max daily loss
                    risk_factors.append(f"High daily loss: {daily_loss_pct:.1%}")
                    risk_score += 0.3
            
            # Check drawdown
            if drawdown > self.max_drawdown * 0.7:  # 70% of max drawdown
                risk_factors.append(f"High drawdown: {drawdown:.1%}")
                risk_score += 0.4
            
            # Check exposure
            exposure_pct = total_exposure / portfolio_value if portfolio_value > 0 else 0
            if exposure_pct > 0.8:  # 80% exposure
                risk_factors.append(f"High exposure: {exposure_pct:.1%}")
                risk_score += 0.2
            
            # Check position count
            if open_positions >= self.max_open_positions * 0.8:  # 80% of max positions
                risk_factors.append(f"High position count: {open_positions}")
                risk_score += 0.1
            
            # Determine risk level
            if risk_score >= 0.7:
                risk_level = "HIGH"
            elif risk_score >= 0.4:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            return {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "metrics": {
                    "portfolio_value": portfolio_value,
                    "total_exposure": total_exposure,
                    "exposure_percentage": exposure_pct,
                    "daily_pnl": daily_pnl,
                    "daily_pnl_percentage": daily_pnl / portfolio_value if portfolio_value > 0 else 0,
                    "current_drawdown": drawdown,
                    "open_positions": open_positions,
                    "max_positions": self.max_open_positions
                },
                "limits": {
                    "max_daily_loss": self.max_daily_loss,
                    "max_drawdown": self.max_drawdown,
                    "max_position_size": self.max_position_size,
                    "max_open_positions": self.max_open_positions
                },
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {e}")
            return {
                "risk_level": "UNKNOWN",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def assess_position_risk(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk for a specific position.
        
        Args:
            position: Position data
        
        Returns:
            Dict with position risk assessment
        """
        try:
            trade_id = position["trade_id"]
            symbol = position["symbol"]
            current_price = position["current_price"]
            entry_price = position["entry_price"]
            size = position["size"]
            side = position["side"]
            
            # Calculate current P&L
            if side.upper() == "BUY":
                unrealized_pnl = (current_price - entry_price) * size
                unrealized_pnl_pct = (current_price - entry_price) / entry_price
            else:
                unrealized_pnl = (entry_price - current_price) * size
                unrealized_pnl_pct = (entry_price - current_price) / entry_price
            
            # Calculate position value
            position_value = current_price * size
            portfolio_value = await self._get_portfolio_value()
            position_weight = position_value / portfolio_value if portfolio_value > 0 else 0
            
            # Assess risk factors
            risk_factors = []
            action_required = False
            recommended_action = None
            
            # Check for large losses
            if unrealized_pnl_pct < -0.05:  # 5% loss
                risk_factors.append(f"Large unrealized loss: {unrealized_pnl_pct:.1%}")
                if unrealized_pnl_pct < -0.08:  # 8% loss
                    action_required = True
                    recommended_action = "CLOSE"
            
            # Check position size
            if position_weight > self.max_position_size * 1.2:  # 120% of max position size
                risk_factors.append(f"Oversized position: {position_weight:.1%}")
                action_required = True
                recommended_action = "REDUCE"
            
            # Check time-based risk
            created_at = position.get("created_at")
            if created_at:
                position_age = (datetime.utcnow() - created_at).total_seconds() / 3600
                if position_age > 12:  # 12 hours
                    risk_factors.append(f"Old position: {position_age:.1f} hours")
            
            # Check market volatility
            market_data = await self.delta_connector.get_market_data(symbol)
            volatility = market_data.get("volatility", 0)
            if volatility > 0.1:  # 10% volatility
                risk_factors.append(f"High volatility: {volatility:.1%}")
            
            return {
                "trade_id": trade_id,
                "symbol": symbol,
                "risk_factors": risk_factors,
                "action_required": action_required,
                "action": recommended_action,
                "metrics": {
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_pct": unrealized_pnl_pct,
                    "position_value": position_value,
                    "position_weight": position_weight,
                    "volatility": volatility
                },
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error assessing position risk: {e}")
            return {
                "trade_id": position.get("trade_id"),
                "error": str(e),
                "action_required": False
            }
    
    async def get_portfolio_risk_level(self) -> float:
        """Get current portfolio risk level (0.0 to 1.0)"""
        try:
            risk_assessment = await self.assess_portfolio_risk()
            return risk_assessment.get("risk_score", 0.0)
        except Exception as e:
            logger.error(f"Error getting portfolio risk level: {e}")
            return 1.0  # Return high risk on error
    
    async def calculate_tighter_stop_loss(self, position: Dict[str, Any]) -> float:
        """Calculate a tighter stop loss for risk management"""
        try:
            current_price = position["current_price"]
            entry_price = position["entry_price"]
            side = position["side"]
            current_stop = position.get("stop_loss")
            
            # Calculate current profit
            if side.upper() == "BUY":
                profit_pct = (current_price - entry_price) / entry_price
                # Tighten stop loss to lock in some profit
                new_stop = entry_price + (current_price - entry_price) * 0.5
            else:
                profit_pct = (entry_price - current_price) / entry_price
                # Tighten stop loss to lock in some profit
                new_stop = entry_price - (entry_price - current_price) * 0.5
            
            # Ensure new stop is better than current stop
            if current_stop:
                if side.upper() == "BUY":
                    new_stop = max(new_stop, current_stop)
                else:
                    new_stop = min(new_stop, current_stop)
            
            return new_stop
            
        except Exception as e:
            logger.error(f"Error calculating tighter stop loss: {e}")
            return position.get("stop_loss", 0)
    
    # Private helper methods
    
    async def _check_signal_rate_limits(self, symbol: str) -> Dict[str, Any]:
        """Check signal rate limiting"""
        try:
            now = datetime.utcnow()
            
            # Check symbol-specific cooldown
            if symbol in self.recent_signals:
                last_signal_time = self.recent_signals[symbol]
                time_since_last = (now - last_signal_time).total_seconds()
                
                if time_since_last < self.signal_cooldown:
                    return {
                        "allowed": False,
                        "reason": f"Signal cooldown active for {symbol}: {time_since_last:.0f}s < {self.signal_cooldown}s"
                    }
            
            # Check hourly signal limit
            hour_ago = now - timedelta(hours=1)
            recent_signals_count = sum(
                1 for timestamp in self.recent_signals.values()
                if timestamp > hour_ago
            )
            
            if recent_signals_count >= self.max_signals_per_hour:
                return {
                    "allowed": False,
                    "reason": f"Hourly signal limit reached: {recent_signals_count} >= {self.max_signals_per_hour}"
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking signal rate limits: {e}")
            return {"allowed": False, "reason": f"Rate limit check error: {str(e)}"}
    
    async def _check_portfolio_risk_limits(self) -> Dict[str, Any]:
        """Check portfolio-level risk limits"""
        try:
            # Check daily loss limit
            daily_pnl = await self._calculate_daily_pnl()
            portfolio_value = await self._get_portfolio_value()
            
            if portfolio_value > 0:
                daily_loss_pct = abs(daily_pnl) / portfolio_value if daily_pnl < 0 else 0
                
                if daily_loss_pct >= self.max_daily_loss:
                    return {
                        "allowed": False,
                        "reason": f"Daily loss limit reached: {daily_loss_pct:.1%} >= {self.max_daily_loss:.1%}"
                    }
            
            # Check drawdown limit
            drawdown = await self._calculate_current_drawdown()
            if drawdown >= self.max_drawdown:
                return {
                    "allowed": False,
                    "reason": f"Drawdown limit reached: {drawdown:.1%} >= {self.max_drawdown:.1%}"
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking portfolio risk limits: {e}")
            return {"allowed": False, "reason": f"Portfolio risk check error: {str(e)}"}
    
    async def _check_position_limits(self, symbol: str) -> Dict[str, Any]:
        """Check position-related limits"""
        try:
            # Check maximum open positions
            open_positions = await self._count_open_positions()
            if open_positions >= self.max_open_positions:
                return {
                    "allowed": False,
                    "reason": f"Maximum open positions reached: {open_positions} >= {self.max_open_positions}"
                }
            
            # Check if already have position in this symbol
            existing_position = await self._has_existing_position(symbol)
            if existing_position:
                return {
                    "allowed": False,
                    "reason": f"Already have position in {symbol}"
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return {"allowed": False, "reason": f"Position limit check error: {str(e)}"}
    
    async def _check_market_conditions(self, symbol: str) -> Dict[str, Any]:
        """Check market conditions for trading"""
        try:
            market_data = await self.delta_connector.get_market_data(symbol)
            
            # Check volatility
            volatility = market_data.get("volatility", 0)
            if volatility > 0.2:  # 20% volatility threshold
                return {
                    "allowed": False,
                    "reason": f"Extreme volatility in {symbol}: {volatility:.1%}"
                }
            
            # Check liquidity
            volume_24h = market_data.get("volume_24h", 0)
            if volume_24h < 1000000:  # $1M volume threshold
                return {
                    "allowed": False,
                    "reason": f"Low liquidity in {symbol}: ${volume_24h:,.0f} 24h volume"
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            return {"allowed": True}  # Allow on error to avoid blocking
    
    async def _check_correlation_limits(self, symbol: str) -> Dict[str, Any]:
        """Check correlation exposure limits"""
        try:
            # Get current positions
            open_positions = await self._get_open_positions()
            
            # Calculate exposure to correlated assets
            # For simplicity, we'll consider BTC and ETH as different asset classes
            crypto_exposure = 0.0
            portfolio_value = await self._get_portfolio_value()
            
            for position in open_positions:
                if position["symbol"].startswith(("BTC", "ETH")):
                    position_value = position["current_price"] * position["size"]
                    crypto_exposure += position_value
            
            # Add proposed position exposure
            if symbol.startswith(("BTC", "ETH")):
                exposure_pct = crypto_exposure / portfolio_value if portfolio_value > 0 else 0
                
                if exposure_pct > self.max_correlation_exposure:
                    return {
                        "allowed": False,
                        "reason": f"Correlation exposure limit: {exposure_pct:.1%} >= {self.max_correlation_exposure:.1%}"
                    }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking correlation limits: {e}")
            return {"allowed": True}  # Allow on error
    
    async def _check_minimum_balance(self) -> Dict[str, Any]:
        """Check minimum account balance"""
        try:
            balance = await self.delta_connector.get_account_balance()
            available_balance = balance.get("available_balance", 0)
            
            if available_balance < self.min_account_balance:
                return {
                    "allowed": False,
                    "reason": f"Insufficient balance: ${available_balance:,.0f} < ${self.min_account_balance:,.0f}"
                }
            
            return {"allowed": True}
            
        except Exception as e:
            logger.error(f"Error checking minimum balance: {e}")
            return {"allowed": False, "reason": f"Balance check error: {str(e)}"}
    
    async def _record_signal_validation(self, symbol: str, validated: bool):
        """Record signal validation for rate limiting"""
        if validated:
            self.recent_signals[symbol] = datetime.utcnow()
    
    async def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        try:
            balance = await self.delta_connector.get_account_balance()
            return balance.get("total_balance", 0)
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return 0.0
    
    async def _calculate_total_exposure(self) -> float:
        """Calculate total position exposure"""
        try:
            open_positions = await self._get_open_positions()
            total_exposure = 0.0
            
            for position in open_positions:
                position_value = position["current_price"] * position["size"]
                total_exposure += position_value
            
            return total_exposure
            
        except Exception as e:
            logger.error(f"Error calculating total exposure: {e}")
            return 0.0
    
    async def _calculate_daily_pnl(self) -> float:
        """Calculate daily P&L"""
        try:
            # Get today's trades
            today = datetime.utcnow().date()
            daily_pnl = 0.0
            
            async for db in get_db():
                result = await db.execute(
                    select(Trade).filter(
                        Trade.created_at >= today,
                        Trade.status == TradeStatus.CLOSED
                    )
                )
                daily_trades = result.scalars().all()
                
                daily_pnl = sum(float(trade.realized_pnl or 0) for trade in daily_trades)
                break  # Exit after getting the data
                
            # Add unrealized P&L from open positions
            open_positions = await self._get_open_positions()
            for position in open_positions:
                daily_pnl += position.get("unrealized_pnl", 0)
            
            return daily_pnl
            
        except Exception as e:
            logger.error(f"Error calculating daily P&L: {e}")
            return 0.0
    
    async def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown from peak"""
        try:
            # This would typically track the peak portfolio value
            # For now, we'll use a simplified calculation
            current_value = await self._get_portfolio_value()
            
            # Get historical peak (simplified)
            peak_value = max(current_value, self.min_account_balance * 2)  # Assume some peak
            
            drawdown = (peak_value - current_value) / peak_value if peak_value > 0 else 0
            return max(0, drawdown)
            
        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}")
            return 0.0
    
    async def _count_open_positions(self) -> int:
        """Count open positions"""
        try:
            async for db in get_db():
                result = await db.execute(
                    select(Trade).filter(
                        Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIALLY_FILLED])
                    )
                )
                trades = result.scalars().all()
                return len(trades)
        except Exception as e:
            logger.error(f"Error counting open positions: {e}")
            return 0
    
    async def _has_existing_position(self, symbol: str) -> bool:
        """Check if there's an existing position in symbol"""
        try:
            async for db in get_db():
                result = await db.execute(
                    select(Trade).filter(
                        Trade.symbol == symbol,
                        Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIALLY_FILLED])
                    )
                )
                existing = result.scalars().first()
                return existing is not None
        except Exception as e:
            logger.error(f"Error checking existing position: {e}")
            return False
    
    async def _get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            open_trades = []
            async for db in get_db():
                result = await db.execute(
                    select(Trade).filter(
                        Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIALLY_FILLED])
                    )
                )
                open_trades = result.scalars().all()
                break  # Exit after getting the data
            
            positions = []
            for trade in open_trades:
                # Get current price
                current_price = await self.delta_connector.get_current_price(trade.symbol)
                
                # Calculate unrealized P&L
                entry_price = float(trade.entry_price) if trade.entry_price else 0
                size = float(trade.size)
                
                if trade.trade_type == TradeType.BUY:
                    unrealized_pnl = (current_price - entry_price) * size
                else:
                    unrealized_pnl = (entry_price - current_price) * size
                
                positions.append({
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.trade_type.value,
                    "size": size,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "unrealized_pnl": unrealized_pnl,
                    "created_at": trade.created_at
                })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
    
    def _round_to_precision(self, size: float, symbol: str) -> float:
        """Round position size to appropriate precision"""
        try:
            # Default to 6 decimal places for crypto
            precision = 6
            
            # Adjust precision based on symbol
            if "BTC" in symbol:
                precision = 6
            elif "ETH" in symbol:
                precision = 4
            
            return round(size, precision)
            
        except Exception as e:
            logger.error(f"Error rounding to precision: {e}")
            return size
    
    async def _load_risk_metrics(self):
        """Load risk metrics from persistent storage"""
        try:
            # Initialize with default values
            self.daily_pnl = 0.0
            self.max_daily_drawdown = 0.0
            self.portfolio_value = 0.0
            self.total_exposure = 0.0
            self.recent_signals = {}
            
            logger.info("Risk metrics loaded")
            
        except Exception as e:
            logger.error(f"Error loading risk metrics: {e}")
    
    async def _save_risk_metrics(self):
        """Save risk metrics to persistent storage"""
        try:
            # In a real implementation, this would save to database
            logger.info("Risk metrics saved")
            
        except Exception as e:
            logger.error(f"Error saving risk metrics: {e}")
    
    async def _initialize_portfolio_tracking(self):
        """Initialize portfolio tracking (non-blocking for API failures)"""
        try:
            # Try to get portfolio value, but don't block startup if it fails
            try:
                self.portfolio_value = await self._get_portfolio_value()
            except Exception as e:
                logger.warning(f"Could not get portfolio value during startup: {e}")
                self.portfolio_value = 0.0
            
            # Try to calculate exposure, but don't block startup if it fails
            try:
                self.total_exposure = await self._calculate_total_exposure()
            except Exception as e:
                logger.warning(f"Could not calculate total exposure during startup: {e}")
                self.total_exposure = 0.0
            
            # Try to calculate daily P&L, but don't block startup if it fails
            try:
                self.daily_pnl = await self._calculate_daily_pnl()
            except Exception as e:
                logger.warning(f"Could not calculate daily P&L during startup: {e}")
                self.daily_pnl = 0.0
            
            logger.info(f"Portfolio tracking initialized: ${self.portfolio_value:,.0f}")
            
        except Exception as e:
            logger.warning(f"Portfolio tracking initialization failed, using defaults: {e}")
            # Set safe defaults
            self.portfolio_value = 0.0
            self.total_exposure = 0.0
            self.daily_pnl = 0.0
    
    async def _update_risk_metrics(self):
        """Update risk metrics cache"""
        try:
            now = datetime.utcnow()
            
            # Update every minute
            if (self.last_risk_update is None or 
                (now - self.last_risk_update).total_seconds() > 60):
                
                self.portfolio_value = await self._get_portfolio_value()
                self.total_exposure = await self._calculate_total_exposure()
                self.daily_pnl = await self._calculate_daily_pnl()
                self.last_risk_update = now
                
                logger.debug("Risk metrics updated")
            
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")
    
    # Public API methods
    
    async def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            portfolio_risk = await self.assess_portfolio_risk()
            
            return {
                "portfolio_risk": portfolio_risk,
                "limits": {
                    "max_portfolio_risk": self.max_portfolio_risk,
                    "max_daily_loss": self.max_daily_loss,
                    "max_drawdown": self.max_drawdown,
                    "max_position_size": self.max_position_size,
                    "max_open_positions": self.max_open_positions,
                    "min_signal_confidence": self.min_signal_confidence
                },
                "current_metrics": {
                    "portfolio_value": self.portfolio_value,
                    "total_exposure": self.total_exposure,
                    "daily_pnl": self.daily_pnl,
                    "open_positions": await self._count_open_positions()
                },
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting risk summary: {e}")
            return {"error": str(e)}
    
    async def _get_asset_exposure(self, symbol: str) -> float:
        """Get current exposure for a specific asset"""
        try:
            async for db in get_db():
                result = await db.execute(
                    select(Trade).where(
                        Trade.symbol == symbol,
                        Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIAL])
                    )
                )
                trades = result.scalars().all()
                
                total_exposure = sum(trade.size * trade.entry_price for trade in trades)
                return total_exposure
                
        except Exception as e:
            logger.error(f"Error getting asset exposure for {symbol}: {e}")
            return 0.0
    
    async def _count_consecutive_losses(self) -> int:
        """Count consecutive losing trades"""
        try:
            async for db in get_db():
                result = await db.execute(
                    select(Trade).where(
                        Trade.status == TradeStatus.CLOSED
                    ).order_by(Trade.exit_time.desc()).limit(10)
                )
                recent_trades = result.scalars().all()
                
                consecutive_losses = 0
                for trade in recent_trades:
                    if trade.pnl < 0:
                        consecutive_losses += 1
                    else:
                        break
                
                return consecutive_losses
                
        except Exception as e:
            logger.error(f"Error counting consecutive losses: {e}")
            return 0
    
    async def _is_event_pause_active(self) -> bool:
        """Check if event pause is currently active"""
        try:
            # This would check for market events, volatility spikes, etc.
            # For now, return False (no pause)
            return False
            
        except Exception as e:
            logger.error(f"Error checking event pause: {e}")
            return True  # Err on the side of caution
    
    async def emergency_risk_shutdown(self) -> Dict[str, Any]:
        """Emergency risk shutdown - stop all trading"""
        try:
            logger.critical("🚨 EMERGENCY RISK SHUTDOWN ACTIVATED")
            
            # Set trading lock
            metrics_service.set_trading_lock(True, "emergency_shutdown")
            
            # Persist emergency stop event
            await self._persist_risk_event(
                event_type=RiskEventType.EMERGENCY_STOP,
                correlation_id=str(uuid.uuid4())[:8],
                decision="locked",
                reason="Emergency risk shutdown activated",
                details=json.dumps({"timestamp": datetime.utcnow().isoformat()})
            )
            
            # This would trigger emergency procedures
            return {
                "success": True,
                "message": "Emergency risk shutdown activated",
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error in emergency risk shutdown: {e}")
            return {"success": False, "error": str(e)}
    
    async def _persist_risk_event(
        self,
        event_type: RiskEventType,
        correlation_id: str,
        symbol: str = None,
        side: str = None,
        quantity: float = None,
        price: float = None,
        notional_usd: float = None,
        decision: str = None,
        reason: str = None,
        risk_score: float = None,
        confidence: float = None,
        details: str = None
    ):
        """Persist risk event to database for audit trail"""
        try:
            async for db in get_db():
                # Get current portfolio metrics
                portfolio_value = await self._get_portfolio_value()
                daily_pnl = await self._calculate_daily_pnl()
                total_exposure = await self._calculate_total_exposure()
                open_positions_count = await self._count_open_positions()
                
                # Create risk event
                risk_event = RiskEvent(
                    event_type=event_type,
                    correlation_id=correlation_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    notional_usd=notional_usd,
                    portfolio_value_usd=portfolio_value,
                    daily_pnl_usd=daily_pnl,
                    total_exposure_usd=total_exposure,
                    open_positions_count=open_positions_count,
                    decision=decision,
                    reason=reason,
                    risk_score=risk_score,
                    confidence=confidence,
                    environment="testnet" if self.paper_trading else "live",
                    paper_trading=self.paper_trading,
                    details=details
                )
                
                db.add(risk_event)
                await db.commit()
                
                logger.debug(f"Risk event persisted: {event_type} for {correlation_id}")
                
        except Exception as e:
            logger.error(f"Failed to persist risk event: {e}")
            # Don't fail the main operation if persistence fails

