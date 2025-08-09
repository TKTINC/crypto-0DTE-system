"""
Metrics Service for Crypto-0DTE System

Provides comprehensive observability metrics for:
- Order execution metrics (counters, histograms)
- Portfolio and risk metrics (gauges)
- System health and performance metrics
- Prometheus /metrics endpoint integration
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import asyncio

from app.database import get_db
from app.config import Settings
from app.models.trade import Trade, TradeStatus
from app.models.order import Order, OrderStatus
from sqlalchemy import select, func

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Comprehensive metrics collection and exposure service.
    
    Implements GPT-5's recommendation for Prometheus metrics with:
    - Counters: orders_submitted, orders_filled, orders_canceled, orders_rejected, retries_total
    - Histograms: submit_to_fill_seconds, slippage_bps
    - Gauges: gross_exposure, open_positions, daily_pnl
    """
    
    def __init__(self):
        self.settings = Settings()
        
        # Order Execution Counters
        self.orders_submitted = Counter(
            'crypto_orders_submitted_total',
            'Total number of orders submitted to exchange',
            ['symbol', 'side', 'order_type', 'environment']
        )
        
        self.orders_filled = Counter(
            'crypto_orders_filled_total',
            'Total number of orders successfully filled',
            ['symbol', 'side', 'order_type', 'environment']
        )
        
        self.orders_canceled = Counter(
            'crypto_orders_canceled_total',
            'Total number of orders canceled',
            ['symbol', 'side', 'reason', 'environment']
        )
        
        self.orders_rejected = Counter(
            'crypto_orders_rejected_total',
            'Total number of orders rejected by exchange or risk gate',
            ['symbol', 'side', 'reason', 'environment']
        )
        
        self.retries_total = Counter(
            'crypto_retries_total',
            'Total number of operation retries',
            ['operation_type', 'reason', 'environment']
        )
        
        # Risk Gate Metrics
        self.risk_gate_checks = Counter(
            'crypto_risk_gate_checks_total',
            'Total number of risk gate checks performed',
            ['verdict', 'risk_type', 'environment']
        )
        
        # Execution Performance Histograms
        self.submit_to_fill_seconds = Histogram(
            'crypto_submit_to_fill_seconds',
            'Time from order submission to fill completion',
            ['symbol', 'order_type', 'environment'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0]
        )
        
        self.slippage_bps = Histogram(
            'crypto_slippage_basis_points',
            'Order slippage in basis points',
            ['symbol', 'side', 'environment'],
            buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500, 1000]
        )
        
        # Portfolio and Risk Gauges
        self.gross_exposure = Gauge(
            'crypto_gross_exposure_usd',
            'Total gross exposure across all positions in USD',
            ['environment']
        )
        
        self.open_positions = Gauge(
            'crypto_open_positions_count',
            'Number of currently open positions',
            ['environment']
        )
        
        self.daily_pnl = Gauge(
            'crypto_daily_pnl_usd',
            'Daily profit and loss in USD',
            ['environment']
        )
        
        self.portfolio_value = Gauge(
            'crypto_portfolio_value_usd',
            'Total portfolio value in USD',
            ['environment']
        )
        
        self.consecutive_losses = Gauge(
            'crypto_consecutive_losses_count',
            'Number of consecutive losing trades',
            ['environment']
        )
        
        # System Health Gauges
        self.system_uptime_seconds = Gauge(
            'crypto_system_uptime_seconds',
            'System uptime in seconds'
        )
        
        self.last_trade_timestamp = Gauge(
            'crypto_last_trade_timestamp',
            'Timestamp of last executed trade'
        )
        
        # Initialize
        self.start_time = time.time()
        self.environment = "testnet" if self.settings.PAPER_TRADING else "live"
        
        logger.info("✅ Metrics Service initialized")
    
    def record_order_submitted(self, symbol: str, side: str, order_type: str):
        """Record an order submission"""
        self.orders_submitted.labels(
            symbol=symbol,
            side=side,
            order_type=order_type,
            environment=self.environment
        ).inc()
        
        logger.debug(f"📊 METRIC: Order submitted - {symbol} {side} {order_type}")
    
    def record_order_filled(self, symbol: str, side: str, order_type: str, 
                           submit_time: datetime, fill_time: datetime,
                           expected_price: float, fill_price: float):
        """Record an order fill with execution metrics"""
        # Record fill counter
        self.orders_filled.labels(
            symbol=symbol,
            side=side,
            order_type=order_type,
            environment=self.environment
        ).inc()
        
        # Record execution time
        execution_seconds = (fill_time - submit_time).total_seconds()
        self.submit_to_fill_seconds.labels(
            symbol=symbol,
            order_type=order_type,
            environment=self.environment
        ).observe(execution_seconds)
        
        # Record slippage
        if expected_price > 0:
            slippage = abs(fill_price - expected_price) / expected_price * 10000  # basis points
            self.slippage_bps.labels(
                symbol=symbol,
                side=side,
                environment=self.environment
            ).observe(slippage)
        
        # Update last trade timestamp
        self.last_trade_timestamp.set(fill_time.timestamp())
        
        logger.debug(f"📊 METRIC: Order filled - {symbol} {side} {order_type} in {execution_seconds:.2f}s")
    
    def record_order_canceled(self, symbol: str, side: str, reason: str):
        """Record an order cancellation"""
        self.orders_canceled.labels(
            symbol=symbol,
            side=side,
            reason=reason,
            environment=self.environment
        ).inc()
        
        logger.debug(f"📊 METRIC: Order canceled - {symbol} {side} ({reason})")
    
    def record_order_rejected(self, symbol: str, side: str, reason: str):
        """Record an order rejection"""
        self.orders_rejected.labels(
            symbol=symbol,
            side=side,
            reason=reason,
            environment=self.environment
        ).inc()
        
        logger.debug(f"📊 METRIC: Order rejected - {symbol} {side} ({reason})")
    
    def record_retry(self, operation_type: str, reason: str):
        """Record an operation retry"""
        self.retries_total.labels(
            operation_type=operation_type,
            reason=reason,
            environment=self.environment
        ).inc()
        
        logger.debug(f"📊 METRIC: Retry - {operation_type} ({reason})")
    
    def record_risk_gate_check(self, verdict: str, risk_type: str = "general"):
        """Record a risk gate check"""
        self.risk_gate_checks.labels(
            verdict=verdict.lower(),
            risk_type=risk_type,
            environment=self.environment
        ).inc()
        
        logger.debug(f"📊 METRIC: Risk gate - {verdict} ({risk_type})")
    
    async def update_portfolio_metrics(self):
        """Update portfolio and risk metrics from database"""
        try:
            async for db in get_db():
                # Calculate gross exposure
                result = await db.execute(
                    select(func.sum(Trade.size * Trade.entry_price)).where(
                        Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIAL])
                    )
                )
                gross_exposure_value = result.scalar() or 0.0
                self.gross_exposure.labels(environment=self.environment).set(gross_exposure_value)
                
                # Count open positions
                result = await db.execute(
                    select(func.count(Trade.id)).where(
                        Trade.status.in_([TradeStatus.OPEN, TradeStatus.PARTIAL])
                    )
                )
                open_positions_count = result.scalar() or 0
                self.open_positions.labels(environment=self.environment).set(open_positions_count)
                
                # Calculate daily P&L
                today = datetime.utcnow().date()
                result = await db.execute(
                    select(func.sum(Trade.pnl)).where(
                        Trade.exit_time >= today,
                        Trade.status == TradeStatus.CLOSED
                    )
                )
                daily_pnl_value = result.scalar() or 0.0
                self.daily_pnl.labels(environment=self.environment).set(daily_pnl_value)
                
                # Calculate portfolio value (simplified - would need actual balance from exchange)
                portfolio_value_estimate = gross_exposure_value + daily_pnl_value + 10000  # Base balance
                self.portfolio_value.labels(environment=self.environment).set(portfolio_value_estimate)
                
                # Count consecutive losses
                result = await db.execute(
                    select(Trade).where(
                        Trade.status == TradeStatus.CLOSED
                    ).order_by(Trade.exit_time.desc()).limit(10)
                )
                recent_trades = result.scalars().all()
                
                consecutive_losses_count = 0
                for trade in recent_trades:
                    if trade.pnl < 0:
                        consecutive_losses_count += 1
                    else:
                        break
                
                self.consecutive_losses.labels(environment=self.environment).set(consecutive_losses_count)
                
                logger.debug(f"📊 METRICS UPDATED: Exposure={gross_exposure_value:.2f}, Positions={open_positions_count}, P&L={daily_pnl_value:.2f}")
                
        except Exception as e:
            logger.error(f"Error updating portfolio metrics: {e}")
    
    def update_system_metrics(self):
        """Update system health metrics"""
        current_time = time.time()
        uptime = current_time - self.start_time
        self.system_uptime_seconds.set(uptime)
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of key metrics for API responses"""
        await self.update_portfolio_metrics()
        self.update_system_metrics()
        
        return {
            "portfolio": {
                "gross_exposure": self.gross_exposure.labels(environment=self.environment)._value._value,
                "open_positions": self.open_positions.labels(environment=self.environment)._value._value,
                "daily_pnl": self.daily_pnl.labels(environment=self.environment)._value._value,
                "portfolio_value": self.portfolio_value.labels(environment=self.environment)._value._value,
                "consecutive_losses": self.consecutive_losses.labels(environment=self.environment)._value._value
            },
            "system": {
                "uptime_seconds": self.system_uptime_seconds._value._value,
                "environment": self.environment,
                "last_trade_timestamp": self.last_trade_timestamp._value._value
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus formatted metrics"""
        self.update_system_metrics()
        return generate_latest()


# Global metrics service instance
metrics_service = MetricsService()

