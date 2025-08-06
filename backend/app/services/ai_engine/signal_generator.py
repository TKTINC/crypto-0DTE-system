"""
AI Signal Generation Engine

Advanced AI system for generating cryptocurrency trading signals using
multiple machine learning models and ensemble methods.
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Optional AI/ML imports - gracefully handle missing dependencies
try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
except ImportError:
    tf = None
    HAS_TENSORFLOW = False

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    pipeline = None
    HAS_TRANSFORMERS = False

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit
import ta

from app.config import settings
from app.database import get_db_session, redis_manager, influxdb_manager
from app.models.signal import Signal, SignalExecution, SignalPerformance
from app.models.market_data import CryptoPrice, OrderBook, MarketSentiment, DeFiMetrics
from app.services.ai_engine.feature_engineering import FeatureEngineer
from app.services.ai_engine.model_manager import ModelManager
from app.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class TradingSignal:
    """Trading signal data structure"""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    entry_price: Decimal
    target_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    position_size: float
    strategy: str
    reasoning: str
    features: Dict[str, float]
    timestamp: datetime
    expiry: datetime


class AISignalGenerator:
    """AI-powered signal generation engine"""
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.model_manager = ModelManager()
        
        # Supported symbols
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        
        # Model configurations
        self.models = {
            "lstm_price_predictor": None,
            "transformer_sentiment": None,
            "random_forest_momentum": None,
            "gradient_boost_volatility": None,
            "ensemble_meta_model": None
        }
        
        # Feature scalers
        self.scalers = {
            "price_features": StandardScaler(),
            "volume_features": RobustScaler(),
            "sentiment_features": StandardScaler()
        }
        
        # Signal history for learning
        self.signal_history: List[TradingSignal] = []
        self.performance_metrics = {}
        
        # Strategy configurations
        self.strategy_configs = settings.STRATEGY_CONFIG
        
        # Running state
        self.running = False
        self.last_signal_time = {}
        
        # Minimum intervals between signals (seconds)
        self.signal_intervals = {
            "btc_lightning_scalp": 300,      # 5 minutes
            "eth_defi_correlation": 900,     # 15 minutes
            "cross_asset_arbitrage": 600,    # 10 minutes
            "funding_rate_arbitrage": 1800,  # 30 minutes
            "fear_greed_contrarian": 3600    # 1 hour
        }
    
    async def initialize(self):
        """Initialize the AI signal generator"""
        logger.info("Initializing AI Signal Generator...")
        
        try:
            # Initialize feature engineer
            await self.feature_engineer.initialize()
            
            # Load or train models
            await self._load_or_train_models()
            
            # Load historical performance
            await self._load_performance_metrics()
            
            logger.info("AI Signal Generator initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing AI Signal Generator: {e}")
            raise
    
    async def start(self):
        """Start the signal generation process"""
        logger.info("Starting AI Signal Generator...")
        
        self.running = True
        
        # Start signal generation tasks
        tasks = [
            asyncio.create_task(self._generate_signals_loop()),
            asyncio.create_task(self._update_models_loop()),
            asyncio.create_task(self._performance_tracking_loop())
        ]
        
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error in signal generation: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """Stop the signal generation process"""
        logger.info("Stopping AI Signal Generator...")
        self.running = False
    
    # =============================================================================
    # MAIN SIGNAL GENERATION LOOP
    # =============================================================================
    
    async def _generate_signals_loop(self):
        """Main signal generation loop"""
        while self.running:
            try:
                for symbol in self.symbols:
                    # Generate signals for each strategy
                    signals = await self._generate_signals_for_symbol(symbol)
                    
                    # Process and store signals
                    for signal in signals:
                        await self._process_signal(signal)
                
                # Wait before next iteration
                await asyncio.sleep(30)  # Generate signals every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in signal generation loop: {e}")
                await asyncio.sleep(60)
    
    async def _generate_signals_for_symbol(self, symbol: str) -> List[TradingSignal]:
        """Generate signals for a specific symbol"""
        signals = []
        
        try:
            # Get market data and features
            features = await self.feature_engineer.get_features(symbol)
            
            if not features:
                logger.warning(f"No features available for {symbol}")
                return signals
            
            # Generate signals from each strategy
            strategies = [
                ("btc_lightning_scalp", self._btc_lightning_scalp_strategy),
                ("eth_defi_correlation", self._eth_defi_correlation_strategy),
                ("cross_asset_arbitrage", self._cross_asset_arbitrage_strategy),
                ("funding_rate_arbitrage", self._funding_rate_arbitrage_strategy),
                ("fear_greed_contrarian", self._fear_greed_contrarian_strategy)
            ]
            
            for strategy_name, strategy_func in strategies:
                # Check if strategy is enabled
                if not self.strategy_configs.get(strategy_name, {}).get("enabled", False):
                    continue
                
                # Check minimum interval
                if not self._can_generate_signal(strategy_name):
                    continue
                
                # Generate signal
                signal = await strategy_func(symbol, features)
                if signal:
                    signals.append(signal)
                    self.last_signal_time[strategy_name] = datetime.utcnow()
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return signals
    
    def _can_generate_signal(self, strategy: str) -> bool:
        """Check if enough time has passed to generate a new signal"""
        if strategy not in self.last_signal_time:
            return True
        
        time_since_last = (datetime.utcnow() - self.last_signal_time[strategy]).total_seconds()
        min_interval = self.signal_intervals.get(strategy, 300)
        
        return time_since_last >= min_interval
    
    # =============================================================================
    # STRATEGY IMPLEMENTATIONS
    # =============================================================================
    
    async def _btc_lightning_scalp_strategy(self, symbol: str, features: Dict) -> Optional[TradingSignal]:
        """BTC Lightning Scalp Strategy - Fast momentum-based trades"""
        if symbol != "BTCUSDT":
            return None
        
        try:
            config = self.strategy_configs["btc_lightning_scalp"]
            
            # Extract relevant features
            momentum = features.get("momentum_5m", 0)
            volume_ratio = features.get("volume_ratio_1h", 1)
            rsi = features.get("rsi_14", 50)
            macd_signal = features.get("macd_signal", 0)
            price = features.get("current_price", 0)
            
            # Signal conditions
            momentum_threshold = config["momentum_threshold"]
            volume_confirmation = config["volume_confirmation"]
            
            signal_type = None
            confidence = 0.0
            reasoning = ""
            
            # Buy conditions
            if (momentum > momentum_threshold and 
                volume_ratio > volume_confirmation and 
                rsi < 70 and 
                macd_signal > 0):
                
                signal_type = SignalType.BUY
                confidence = min(0.95, 0.6 + (momentum * 10) + (volume_ratio * 0.1))
                reasoning = f"Strong upward momentum ({momentum:.3f}) with volume confirmation ({volume_ratio:.2f})"
            
            # Sell conditions
            elif (momentum < -momentum_threshold and 
                  volume_ratio > volume_confirmation and 
                  rsi > 30 and 
                  macd_signal < 0):
                
                signal_type = SignalType.SELL
                confidence = min(0.95, 0.6 + (abs(momentum) * 10) + (volume_ratio * 0.1))
                reasoning = f"Strong downward momentum ({momentum:.3f}) with volume confirmation ({volume_ratio:.2f})"
            
            if signal_type:
                # Calculate position sizing
                position_size = self._calculate_position_size(
                    symbol, confidence, config["position_size"]
                )
                
                # Calculate targets
                entry_price = Decimal(str(price))
                target_price, stop_loss = self._calculate_scalp_targets(
                    entry_price, signal_type, confidence
                )
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=self._get_signal_strength(confidence),
                    confidence=confidence,
                    entry_price=entry_price,
                    target_price=target_price,
                    stop_loss=stop_loss,
                    position_size=position_size,
                    strategy="btc_lightning_scalp",
                    reasoning=reasoning,
                    features=features,
                    timestamp=datetime.utcnow(),
                    expiry=datetime.utcnow() + timedelta(minutes=30)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in BTC Lightning Scalp strategy: {e}")
            return None
    
    async def _eth_defi_correlation_strategy(self, symbol: str, features: Dict) -> Optional[TradingSignal]:
        """ETH DeFi Correlation Strategy - Trade ETH based on DeFi ecosystem"""
        if symbol != "ETHUSDT":
            return None
        
        try:
            config = self.strategy_configs["eth_defi_correlation"]
            
            # Extract DeFi-related features
            defi_tvl_change = features.get("defi_tvl_change_24h", 0)
            defi_token_momentum = features.get("defi_token_momentum", 0)
            eth_defi_correlation = features.get("eth_defi_correlation", 0)
            gas_price_trend = features.get("gas_price_trend", 0)
            dex_volume_change = features.get("dex_volume_change_24h", 0)
            price = features.get("current_price", 0)
            
            correlation_threshold = config["correlation_threshold"]
            
            signal_type = None
            confidence = 0.0
            reasoning = ""
            
            # Strong DeFi ecosystem growth
            if (defi_tvl_change > 0.05 and  # 5% TVL increase
                defi_token_momentum > 0.03 and  # 3% token momentum
                eth_defi_correlation > correlation_threshold and
                dex_volume_change > 0.1):  # 10% volume increase
                
                signal_type = SignalType.BUY
                confidence = min(0.92, 0.7 + (defi_tvl_change * 2) + (eth_defi_correlation * 0.3))
                reasoning = f"Strong DeFi ecosystem growth: TVL+{defi_tvl_change:.1%}, DEX volume+{dex_volume_change:.1%}"
            
            # DeFi ecosystem decline
            elif (defi_tvl_change < -0.03 and  # 3% TVL decrease
                  defi_token_momentum < -0.02 and  # 2% token decline
                  eth_defi_correlation > correlation_threshold):
                
                signal_type = SignalType.SELL
                confidence = min(0.88, 0.65 + (abs(defi_tvl_change) * 2) + (eth_defi_correlation * 0.2))
                reasoning = f"DeFi ecosystem decline: TVL{defi_tvl_change:.1%}, tokens{defi_token_momentum:.1%}"
            
            if signal_type:
                position_size = self._calculate_position_size(
                    symbol, confidence, config["position_size"]
                )
                
                entry_price = Decimal(str(price))
                target_price, stop_loss = self._calculate_defi_targets(
                    entry_price, signal_type, confidence, defi_tvl_change
                )
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=self._get_signal_strength(confidence),
                    confidence=confidence,
                    entry_price=entry_price,
                    target_price=target_price,
                    stop_loss=stop_loss,
                    position_size=position_size,
                    strategy="eth_defi_correlation",
                    reasoning=reasoning,
                    features=features,
                    timestamp=datetime.utcnow(),
                    expiry=datetime.utcnow() + timedelta(hours=4)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in ETH DeFi Correlation strategy: {e}")
            return None
    
    async def _cross_asset_arbitrage_strategy(self, symbol: str, features: Dict) -> Optional[TradingSignal]:
        """Cross-Asset Arbitrage Strategy - Exploit BTC/ETH correlation breakdowns"""
        try:
            config = self.strategy_configs["cross_asset_arbitrage"]
            
            # Get both BTC and ETH features
            btc_features = await self.feature_engineer.get_features("BTCUSDT")
            eth_features = await self.feature_engineer.get_features("ETHUSDT")
            
            if not btc_features or not eth_features:
                return None
            
            # Calculate correlation metrics
            btc_momentum = btc_features.get("momentum_1h", 0)
            eth_momentum = eth_features.get("momentum_1h", 0)
            correlation_1h = features.get("btc_eth_correlation_1h", 0.8)
            correlation_24h = features.get("btc_eth_correlation_24h", 0.8)
            
            # Expected correlation vs actual
            expected_correlation = (correlation_1h + correlation_24h) / 2
            actual_momentum_correlation = np.corrcoef([btc_momentum], [eth_momentum])[0, 1]
            
            correlation_deviation = abs(expected_correlation - actual_momentum_correlation)
            deviation_threshold = config["correlation_deviation_threshold"]
            
            if correlation_deviation > deviation_threshold:
                # Determine which asset is lagging
                if symbol == "BTCUSDT" and btc_momentum < eth_momentum * expected_correlation:
                    signal_type = SignalType.BUY
                    reasoning = f"BTC lagging ETH momentum (deviation: {correlation_deviation:.3f})"
                elif symbol == "ETHUSDT" and eth_momentum < btc_momentum * expected_correlation:
                    signal_type = SignalType.BUY
                    reasoning = f"ETH lagging BTC momentum (deviation: {correlation_deviation:.3f})"
                elif symbol == "BTCUSDT" and btc_momentum > eth_momentum * expected_correlation:
                    signal_type = SignalType.SELL
                    reasoning = f"BTC leading ETH momentum (deviation: {correlation_deviation:.3f})"
                elif symbol == "ETHUSDT" and eth_momentum > btc_momentum * expected_correlation:
                    signal_type = SignalType.SELL
                    reasoning = f"ETH leading BTC momentum (deviation: {correlation_deviation:.3f})"
                else:
                    return None
                
                confidence = min(0.85, 0.6 + (correlation_deviation * 2))
                position_size = self._calculate_position_size(
                    symbol, confidence, config["position_size"]
                )
                
                price = features.get("current_price", 0)
                entry_price = Decimal(str(price))
                target_price, stop_loss = self._calculate_arbitrage_targets(
                    entry_price, signal_type, correlation_deviation
                )
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=self._get_signal_strength(confidence),
                    confidence=confidence,
                    entry_price=entry_price,
                    target_price=target_price,
                    stop_loss=stop_loss,
                    position_size=position_size,
                    strategy="cross_asset_arbitrage",
                    reasoning=reasoning,
                    features=features,
                    timestamp=datetime.utcnow(),
                    expiry=datetime.utcnow() + timedelta(hours=2)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Cross-Asset Arbitrage strategy: {e}")
            return None
    
    async def _funding_rate_arbitrage_strategy(self, symbol: str, features: Dict) -> Optional[TradingSignal]:
        """Funding Rate Arbitrage Strategy - Exploit funding rate inefficiencies"""
        try:
            config = self.strategy_configs["funding_rate_arbitrage"]
            
            # Extract funding rate features
            current_funding_rate = features.get("funding_rate", 0)
            predicted_funding_rate = features.get("predicted_funding_rate", 0)
            funding_rate_trend = features.get("funding_rate_trend_24h", 0)
            open_interest_change = features.get("open_interest_change_24h", 0)
            
            funding_threshold = config["funding_rate_threshold"]
            
            signal_type = None
            confidence = 0.0
            reasoning = ""
            
            # High positive funding rate (longs pay shorts)
            if (current_funding_rate > funding_threshold and
                predicted_funding_rate > funding_threshold and
                open_interest_change > 0.1):  # 10% OI increase
                
                signal_type = SignalType.SELL  # Short to collect funding
                confidence = min(0.88, 0.6 + (current_funding_rate * 20))
                reasoning = f"High funding rate ({current_funding_rate:.4f}) - short to collect funding"
            
            # High negative funding rate (shorts pay longs)
            elif (current_funding_rate < -funding_threshold and
                  predicted_funding_rate < -funding_threshold and
                  open_interest_change > 0.1):
                
                signal_type = SignalType.BUY  # Long to collect funding
                confidence = min(0.88, 0.6 + (abs(current_funding_rate) * 20))
                reasoning = f"Negative funding rate ({current_funding_rate:.4f}) - long to collect funding"
            
            if signal_type:
                position_size = self._calculate_position_size(
                    symbol, confidence, config["position_size"]
                )
                
                price = features.get("current_price", 0)
                entry_price = Decimal(str(price))
                target_price, stop_loss = self._calculate_funding_targets(
                    entry_price, signal_type, current_funding_rate
                )
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=self._get_signal_strength(confidence),
                    confidence=confidence,
                    entry_price=entry_price,
                    target_price=target_price,
                    stop_loss=stop_loss,
                    position_size=position_size,
                    strategy="funding_rate_arbitrage",
                    reasoning=reasoning,
                    features=features,
                    timestamp=datetime.utcnow(),
                    expiry=datetime.utcnow() + timedelta(hours=8)  # Until next funding
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Funding Rate Arbitrage strategy: {e}")
            return None
    
    async def _fear_greed_contrarian_strategy(self, symbol: str, features: Dict) -> Optional[TradingSignal]:
        """Fear & Greed Contrarian Strategy - Trade against extreme sentiment"""
        try:
            config = self.strategy_configs["fear_greed_contrarian"]
            
            # Extract sentiment features
            fear_greed_index = features.get("fear_greed_index", 50)
            sentiment_trend = features.get("sentiment_trend_7d", 0)
            social_sentiment = features.get("social_sentiment", 0)
            news_sentiment = features.get("news_sentiment", 0)
            
            fear_threshold = config["fear_threshold"]
            greed_threshold = config["greed_threshold"]
            
            signal_type = None
            confidence = 0.0
            reasoning = ""
            
            # Extreme fear - contrarian buy
            if (fear_greed_index <= fear_threshold and
                sentiment_trend < -0.1 and  # Declining sentiment
                social_sentiment < -0.3):   # Negative social sentiment
                
                signal_type = SignalType.BUY
                confidence = min(0.90, 0.7 + ((fear_threshold - fear_greed_index) / 100))
                reasoning = f"Extreme fear (F&G: {fear_greed_index}) - contrarian buy opportunity"
            
            # Extreme greed - contrarian sell
            elif (fear_greed_index >= greed_threshold and
                  sentiment_trend > 0.1 and   # Rising sentiment
                  social_sentiment > 0.3):    # Positive social sentiment
                
                signal_type = SignalType.SELL
                confidence = min(0.90, 0.7 + ((fear_greed_index - greed_threshold) / 100))
                reasoning = f"Extreme greed (F&G: {fear_greed_index}) - contrarian sell opportunity"
            
            if signal_type:
                position_size = self._calculate_position_size(
                    symbol, confidence, config["position_size"]
                )
                
                price = features.get("current_price", 0)
                entry_price = Decimal(str(price))
                target_price, stop_loss = self._calculate_contrarian_targets(
                    entry_price, signal_type, fear_greed_index
                )
                
                return TradingSignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=self._get_signal_strength(confidence),
                    confidence=confidence,
                    entry_price=entry_price,
                    target_price=target_price,
                    stop_loss=stop_loss,
                    position_size=position_size,
                    strategy="fear_greed_contrarian",
                    reasoning=reasoning,
                    features=features,
                    timestamp=datetime.utcnow(),
                    expiry=datetime.utcnow() + timedelta(days=3)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Fear & Greed Contrarian strategy: {e}")
            return None
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def _calculate_position_size(self, symbol: str, confidence: float, base_size: float) -> float:
        """Calculate position size based on confidence and risk management"""
        # Adjust position size based on confidence
        confidence_multiplier = min(1.5, confidence * 1.5)
        
        # Apply risk management limits
        max_position = settings.MAX_POSITION_SIZE
        min_position = settings.MIN_POSITION_SIZE
        
        position_size = base_size * confidence_multiplier
        position_size = max(min_position, min(max_position, position_size))
        
        return position_size
    
    def _get_signal_strength(self, confidence: float) -> SignalStrength:
        """Convert confidence to signal strength"""
        if confidence >= 0.85:
            return SignalStrength.VERY_STRONG
        elif confidence >= 0.75:
            return SignalStrength.STRONG
        elif confidence >= 0.65:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _calculate_scalp_targets(self, entry_price: Decimal, signal_type: SignalType, confidence: float) -> Tuple[Decimal, Decimal]:
        """Calculate targets for scalping strategy"""
        if signal_type == SignalType.BUY:
            target_price = entry_price * Decimal("1.008")  # 0.8% target
            stop_loss = entry_price * Decimal("0.996")     # 0.4% stop loss
        else:
            target_price = entry_price * Decimal("0.992")  # 0.8% target
            stop_loss = entry_price * Decimal("1.004")     # 0.4% stop loss
        
        return target_price, stop_loss
    
    def _calculate_defi_targets(self, entry_price: Decimal, signal_type: SignalType, confidence: float, tvl_change: float) -> Tuple[Decimal, Decimal]:
        """Calculate targets for DeFi correlation strategy"""
        # Adjust targets based on DeFi momentum
        target_multiplier = 1 + (abs(tvl_change) * 2)  # Scale with TVL change
        
        if signal_type == SignalType.BUY:
            target_price = entry_price * Decimal(str(1.025 * target_multiplier))  # 2.5% base target
            stop_loss = entry_price * Decimal("0.985")                           # 1.5% stop loss
        else:
            target_price = entry_price * Decimal(str(0.975 / target_multiplier))  # 2.5% base target
            stop_loss = entry_price * Decimal("1.015")                           # 1.5% stop loss
        
        return target_price, stop_loss
    
    def _calculate_arbitrage_targets(self, entry_price: Decimal, signal_type: SignalType, deviation: float) -> Tuple[Decimal, Decimal]:
        """Calculate targets for arbitrage strategy"""
        # Target based on correlation deviation
        target_multiplier = 1 + (deviation * 3)
        
        if signal_type == SignalType.BUY:
            target_price = entry_price * Decimal(str(1.015 * target_multiplier))  # 1.5% base target
            stop_loss = entry_price * Decimal("0.99")                            # 1% stop loss
        else:
            target_price = entry_price * Decimal(str(0.985 / target_multiplier))  # 1.5% base target
            stop_loss = entry_price * Decimal("1.01")                            # 1% stop loss
        
        return target_price, stop_loss
    
    def _calculate_funding_targets(self, entry_price: Decimal, signal_type: SignalType, funding_rate: float) -> Tuple[Decimal, Decimal]:
        """Calculate targets for funding rate strategy"""
        # Target to capture funding payments
        funding_profit = abs(funding_rate) * 3  # 3 funding periods
        
        if signal_type == SignalType.BUY:
            target_price = entry_price * Decimal(str(1 + funding_profit))
            stop_loss = entry_price * Decimal("0.985")  # 1.5% stop loss
        else:
            target_price = entry_price * Decimal(str(1 - funding_profit))
            stop_loss = entry_price * Decimal("1.015")  # 1.5% stop loss
        
        return target_price, stop_loss
    
    def _calculate_contrarian_targets(self, entry_price: Decimal, signal_type: SignalType, fear_greed: int) -> Tuple[Decimal, Decimal]:
        """Calculate targets for contrarian strategy"""
        # Larger targets for extreme sentiment
        extreme_multiplier = 1 + (abs(fear_greed - 50) / 100)
        
        if signal_type == SignalType.BUY:
            target_price = entry_price * Decimal(str(1.05 * extreme_multiplier))  # 5% base target
            stop_loss = entry_price * Decimal("0.97")                            # 3% stop loss
        else:
            target_price = entry_price * Decimal(str(0.95 / extreme_multiplier))  # 5% base target
            stop_loss = entry_price * Decimal("1.03")                            # 3% stop loss
        
        return target_price, stop_loss
    
    # =============================================================================
    # SIGNAL PROCESSING
    # =============================================================================
    
    async def _process_signal(self, signal: TradingSignal):
        """Process and store a generated signal"""
        try:
            # Store signal in database
            await self._store_signal(signal)
            
            # Cache signal in Redis
            await self._cache_signal(signal)
            
            # Add to signal history
            self.signal_history.append(signal)
            
            # Limit history size
            if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-1000:]
            
            logger.info(f"Generated {signal.signal_type.value} signal for {signal.symbol} "
                       f"({signal.strategy}) - Confidence: {signal.confidence:.2%}")
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def _store_signal(self, signal: TradingSignal):
        """Store signal in database"""
        try:
            async with get_db_session() as session:
                db_signal = Signal(
                    symbol=signal.symbol,
                    signal_type=signal.signal_type.value,
                    strength=signal.strength.value,
                    confidence=signal.confidence,
                    entry_price=signal.entry_price,
                    target_price=signal.target_price,
                    stop_loss=signal.stop_loss,
                    position_size=signal.position_size,
                    strategy=signal.strategy,
                    reasoning=signal.reasoning,
                    features=signal.features,
                    timestamp=signal.timestamp,
                    expiry=signal.expiry,
                    status="active"
                )
                
                session.add(db_signal)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing signal in database: {e}")
    
    async def _cache_signal(self, signal: TradingSignal):
        """Cache signal in Redis"""
        try:
            cache_key = f"signal:{signal.symbol}:{signal.strategy}:latest"
            signal_data = {
                "signal_type": signal.signal_type.value,
                "strength": signal.strength.value,
                "confidence": signal.confidence,
                "entry_price": float(signal.entry_price),
                "target_price": float(signal.target_price) if signal.target_price else None,
                "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
                "position_size": signal.position_size,
                "strategy": signal.strategy,
                "reasoning": signal.reasoning,
                "timestamp": signal.timestamp.isoformat(),
                "expiry": signal.expiry.isoformat()
            }
            
            await redis_manager.set_cache(
                cache_key,
                json.dumps(signal_data),
                ttl=3600  # 1 hour
            )
            
        except Exception as e:
            logger.error(f"Error caching signal: {e}")
    
    # =============================================================================
    # MODEL MANAGEMENT
    # =============================================================================
    
    async def _load_or_train_models(self):
        """Load existing models or train new ones"""
        try:
            # Try to load existing models
            models_loaded = await self.model_manager.load_models()
            
            if not models_loaded:
                logger.info("No existing models found, training new models...")
                await self._train_initial_models()
            else:
                logger.info("Loaded existing AI models")
                
        except Exception as e:
            logger.error(f"Error loading/training models: {e}")
            # Continue with basic models
    
    async def _train_initial_models(self):
        """Train initial AI models"""
        try:
            # Get historical data for training
            training_data = await self._get_training_data()
            
            if training_data is not None and len(training_data) > 1000:
                # Train models
                await self.model_manager.train_models(training_data)
                logger.info("Initial AI models trained successfully")
            else:
                logger.warning("Insufficient data for model training")
                
        except Exception as e:
            logger.error(f"Error training initial models: {e}")
    
    async def _get_training_data(self) -> Optional[pd.DataFrame]:
        """Get historical data for model training"""
        try:
            # Query historical price data
            query = """
            SELECT symbol, timestamp, close_price, volume, price_change
            FROM crypto_prices 
            WHERE timestamp >= NOW() - INTERVAL '30 days'
            ORDER BY symbol, timestamp
            """
            
            # Execute query and return DataFrame
            # This would be implemented with actual database query
            # For now, return None to indicate no data
            return None
            
        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            return None
    
    async def _update_models_loop(self):
        """Periodically update AI models"""
        while self.running:
            try:
                await asyncio.sleep(settings.MODEL_UPDATE_FREQUENCY)
                
                # Update models with new data
                await self._update_models()
                
            except Exception as e:
                logger.error(f"Error in model update loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _update_models(self):
        """Update AI models with new data"""
        try:
            # Get recent performance data
            performance_data = await self._get_recent_performance()
            
            if performance_data:
                # Update models
                await self.model_manager.update_models(performance_data)
                logger.info("AI models updated with recent performance data")
                
        except Exception as e:
            logger.error(f"Error updating models: {e}")
    
    async def _get_recent_performance(self) -> Optional[Dict]:
        """Get recent signal performance for model updates"""
        try:
            # Query recent signal performance
            # This would be implemented with actual database query
            return None
            
        except Exception as e:
            logger.error(f"Error getting recent performance: {e}")
            return None
    
    # =============================================================================
    # PERFORMANCE TRACKING
    # =============================================================================
    
    async def _performance_tracking_loop(self):
        """Track signal performance for learning"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Update signal performance
                await self._update_signal_performance()
                
            except Exception as e:
                logger.error(f"Error in performance tracking: {e}")
                await asyncio.sleep(600)
    
    async def _update_signal_performance(self):
        """Update performance metrics for active signals"""
        try:
            # Get active signals
            active_signals = await self._get_active_signals()
            
            for signal in active_signals:
                # Check if signal has been executed or expired
                performance = await self._calculate_signal_performance(signal)
                
                if performance:
                    await self._store_signal_performance(signal, performance)
                    
        except Exception as e:
            logger.error(f"Error updating signal performance: {e}")
    
    async def _get_active_signals(self) -> List[Dict]:
        """Get active signals from database"""
        try:
            # Query active signals
            # This would be implemented with actual database query
            return []
            
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    async def _calculate_signal_performance(self, signal: Dict) -> Optional[Dict]:
        """Calculate performance metrics for a signal"""
        try:
            # Get current price and calculate performance
            # This would be implemented with actual price data
            return None
            
        except Exception as e:
            logger.error(f"Error calculating signal performance: {e}")
            return None
    
    async def _store_signal_performance(self, signal: Dict, performance: Dict):
        """Store signal performance in database"""
        try:
            async with get_db_session() as session:
                signal_performance = SignalPerformance(
                    signal_id=signal["id"],
                    realized_pnl=performance.get("realized_pnl", 0),
                    unrealized_pnl=performance.get("unrealized_pnl", 0),
                    max_profit=performance.get("max_profit", 0),
                    max_loss=performance.get("max_loss", 0),
                    duration_minutes=performance.get("duration_minutes", 0),
                    hit_target=performance.get("hit_target", False),
                    hit_stop_loss=performance.get("hit_stop_loss", False),
                    timestamp=datetime.utcnow()
                )
                
                session.add(signal_performance)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error storing signal performance: {e}")
    
    async def _load_performance_metrics(self):
        """Load historical performance metrics"""
        try:
            # Load performance metrics from database
            # This would be implemented with actual database query
            self.performance_metrics = {}
            
        except Exception as e:
            logger.error(f"Error loading performance metrics: {e}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for signal generator"""
    signal_generator = AISignalGenerator()
    
    try:
        await signal_generator.initialize()
        await signal_generator.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Signal generator error: {e}")
    finally:
        await signal_generator.stop()


if __name__ == "__main__":
    asyncio.run(main())


# Alias for backward compatibility
SignalGeneratorService = AISignalGenerator

