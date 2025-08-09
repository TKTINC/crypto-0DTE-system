"""
Metrics Service

Provides Prometheus metrics collection and export functionality.
"""

import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import logging

logger = logging.getLogger(__name__)

class MetricsService:
    """Service for collecting and exporting Prometheus metrics"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure single metrics instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize metrics service (singleton)"""
        if self._initialized:
            return
            
        # Trading Metrics
        self.orders_total = Counter(
            'crypto_orders_total',
            'Total number of orders placed',
            ['symbol', 'side', 'order_type', 'status']
        )
        
        self.order_execution_duration = Histogram(
            'crypto_order_execution_duration_seconds',
            'Time taken to execute orders',
            ['symbol', 'side', 'order_type']
        )
        
        self.fills_total = Counter(
            'crypto_fills_total',
            'Total number of order fills',
            ['symbol', 'side']
        )
        
        self.slippage_histogram = Histogram(
            'crypto_slippage_bps',
            'Order slippage in basis points',
            ['symbol', 'side']
        )
        
        # Risk Metrics
        self.risk_gate_decisions = Counter(
            'crypto_risk_gate_decisions_total',
            'Risk gate decisions',
            ['decision', 'reason']
        )
        
        self.portfolio_value = Gauge(
            'crypto_portfolio_value_usd',
            'Current portfolio value in USD',
            ['environment']
        )
        
        self.daily_pnl = Gauge(
            'crypto_daily_pnl_usd',
            'Daily P&L in USD',
            ['environment']
        )
        
        self.open_positions = Gauge(
            'crypto_open_positions_count',
            'Number of open positions',
            ['environment']
        )
        
        self.trading_locked = Gauge(
            'crypto_trading_locked',
            'Trading lock status (1=locked, 0=unlocked)',
            ['reason']
        )
        
        # System Metrics
        self.health_check_duration = Histogram(
            'crypto_health_check_duration_seconds',
            'Health check response times',
            ['service']
        )
        
        self.health_check_failures = Counter(
            'crypto_health_check_failures_total',
            'Health check failures',
            ['service']
        )
        
        self.api_requests_total = Counter(
            'crypto_api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.api_request_duration = Histogram(
            'crypto_api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint']
        )
        
        # Exchange Metrics
        self.exchange_requests_total = Counter(
            'crypto_exchange_requests_total',
            'Total exchange API requests',
            ['exchange', 'endpoint', 'status_code']
        )
        
        self.exchange_rate_limited = Counter(
            'crypto_exchange_rate_limited_total',
            'Exchange rate limit hits',
            ['exchange']
        )
        
        self.exchange_connection_status = Gauge(
            'crypto_exchange_connection_status',
            'Exchange connection status (1=connected, 0=disconnected)',
            ['exchange', 'environment']
        )
        
        self._initialized = True
        logger.info("MetricsService initialized successfully")
    
    def record_order_placed(self, symbol: str, side: str, order_type: str, status: str):
        """Record an order placement"""
        self.orders_total.labels(
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=status
        ).inc()
    
    def record_order_execution_time(self, symbol: str, side: str, order_type: str, duration_seconds: float):
        """Record order execution time"""
        self.order_execution_duration.labels(
            symbol=symbol,
            side=side,
            order_type=order_type
        ).observe(duration_seconds)
    
    def record_fill(self, symbol: str, side: str, slippage_bps: float = None):
        """Record an order fill"""
        self.fills_total.labels(symbol=symbol, side=side).inc()
        
        if slippage_bps is not None:
            self.slippage_histogram.labels(symbol=symbol, side=side).observe(slippage_bps)
    
    def record_risk_gate_decision(self, decision: str, reason: str):
        """Record a risk gate decision"""
        self.risk_gate_decisions.labels(decision=decision, reason=reason).inc()
    
    def update_portfolio_metrics(self, environment: str, value_usd: float, daily_pnl: float, open_positions_count: int):
        """Update portfolio metrics"""
        self.portfolio_value.labels(environment=environment).set(value_usd)
        self.daily_pnl.labels(environment=environment).set(daily_pnl)
        self.open_positions.labels(environment=environment).set(open_positions_count)
    
    def set_trading_lock(self, locked: bool, reason: str = ""):
        """Set trading lock status"""
        self.trading_locked.labels(reason=reason).set(1 if locked else 0)
    
    def record_health_check(self, service: str, duration_seconds: float, success: bool):
        """Record health check metrics"""
        self.health_check_duration.labels(service=service).observe(duration_seconds)
        if not success:
            self.health_check_failures.labels(service=service).inc()
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float):
        """Record API request metrics"""
        self.api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.api_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration_seconds)
    
    def record_exchange_request(self, exchange: str, endpoint: str, status_code: int):
        """Record exchange API request"""
        self.exchange_requests_total.labels(
            exchange=exchange,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        if status_code == 429:
            self.exchange_rate_limited.labels(exchange=exchange).inc()
    
    def set_exchange_connection_status(self, exchange: str, environment: str, connected: bool):
        """Set exchange connection status"""
        self.exchange_connection_status.labels(
            exchange=exchange,
            environment=environment
        ).set(1 if connected else 0)
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest().decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get Prometheus content type"""
        return CONTENT_TYPE_LATEST

# Global singleton instance
metrics_service = MetricsService()

