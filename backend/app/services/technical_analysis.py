"""
Technical Analysis Service for Crypto-0DTE System

Provides real technical analysis indicators and trading signals
based on market data, replacing the fake AI implementation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from app.utils.financial import FinancialCalculator


logger = logging.getLogger(__name__)


@dataclass
class TechnicalSignal:
    """Technical analysis signal data structure"""
    symbol: str
    signal_type: str  # "BUY", "SELL", "HOLD"
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    entry_price: Decimal
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    indicators: Dict[str, float]
    reasoning: str
    timestamp: datetime


class TechnicalAnalyzer:
    """Real technical analysis implementation"""
    
    def __init__(self):
        self.calculator = FinancialCalculator()
    
    def calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return []
        
        sma = []
        for i in range(period - 1, len(prices)):
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(avg)
        
        return sma
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema = [sum(prices[:period]) / period]  # Start with SMA
        
        for i in range(period, len(prices)):
            ema_value = (prices[i] * multiplier) + (ema[-1] * (1 - multiplier))
            ema.append(ema_value)
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return []
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi = []
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_value = 100
            else:
                rs = avg_gain / avg_loss
                rsi_value = 100 - (100 / (1 + rs))
            
            rsi.append(rsi_value)
        
        return rsi
    
    def calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow:
            return {"macd": [], "signal": [], "histogram": []}
        
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        
        # Align the EMAs (slow EMA starts later)
        start_idx = slow - fast
        ema_fast_aligned = ema_fast[start_idx:]
        
        macd_line = [fast_val - slow_val for fast_val, slow_val in zip(ema_fast_aligned, ema_slow)]
        signal_line = self.calculate_ema(macd_line, signal)
        
        # Align for histogram calculation
        histogram_start = len(macd_line) - len(signal_line)
        macd_aligned = macd_line[histogram_start:]
        histogram = [macd_val - signal_val for macd_val, signal_val in zip(macd_aligned, signal_line)]
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> Dict[str, List[float]]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return {"upper": [], "middle": [], "lower": []}
        
        sma = self.calculate_sma(prices, period)
        upper_band = []
        lower_band = []
        
        for i in range(period - 1, len(prices)):
            price_slice = prices[i - period + 1:i + 1]
            std = np.std(price_slice)
            sma_val = sma[i - period + 1]
            
            upper_band.append(sma_val + (std * std_dev))
            lower_band.append(sma_val - (std * std_dev))
        
        return {
            "upper": upper_band,
            "middle": sma,
            "lower": lower_band
        }
    
    def calculate_stochastic(self, highs: List[float], lows: List[float], closes: List[float], k_period: int = 14, d_period: int = 3) -> Dict[str, List[float]]:
        """Calculate Stochastic Oscillator"""
        if len(closes) < k_period:
            return {"k": [], "d": []}
        
        k_values = []
        
        for i in range(k_period - 1, len(closes)):
            high_slice = highs[i - k_period + 1:i + 1]
            low_slice = lows[i - k_period + 1:i + 1]
            
            highest_high = max(high_slice)
            lowest_low = min(low_slice)
            
            if highest_high == lowest_low:
                k_value = 50  # Avoid division by zero
            else:
                k_value = ((closes[i] - lowest_low) / (highest_high - lowest_low)) * 100
            
            k_values.append(k_value)
        
        d_values = self.calculate_sma(k_values, d_period)
        
        return {"k": k_values, "d": d_values}
    
    def analyze_momentum(self, prices: List[float]) -> Dict[str, float]:
        """Analyze price momentum"""
        if len(prices) < 20:
            return {"momentum_score": 0.0, "trend_strength": 0.0}
        
        # Calculate short and long term momentum
        short_momentum = (prices[-1] - prices[-5]) / prices[-5] * 100  # 5-period momentum
        long_momentum = (prices[-1] - prices[-20]) / prices[-20] * 100  # 20-period momentum
        
        # Calculate trend strength using linear regression slope
        x = np.arange(len(prices[-20:]))
        y = np.array(prices[-20:])
        slope = np.polyfit(x, y, 1)[0]
        trend_strength = abs(slope) / np.mean(y) * 100
        
        momentum_score = (short_momentum + long_momentum) / 2
        
        return {
            "momentum_score": momentum_score,
            "trend_strength": trend_strength,
            "short_momentum": short_momentum,
            "long_momentum": long_momentum
        }
    
    def analyze_volume(self, prices: List[float], volumes: List[float]) -> Dict[str, float]:
        """Analyze volume patterns"""
        if len(volumes) < 20:
            return {"volume_trend": 0.0, "price_volume_correlation": 0.0}
        
        # Calculate volume moving average
        recent_volume = np.mean(volumes[-5:])
        avg_volume = np.mean(volumes[-20:])
        volume_trend = (recent_volume - avg_volume) / avg_volume * 100
        
        # Calculate price-volume correlation
        price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        volume_changes = [volumes[i] - volumes[i-1] for i in range(1, len(volumes))]
        
        if len(price_changes) >= 20:
            correlation = np.corrcoef(price_changes[-20:], volume_changes[-20:])[0, 1]
            if np.isnan(correlation):
                correlation = 0.0
        else:
            correlation = 0.0
        
        return {
            "volume_trend": volume_trend,
            "price_volume_correlation": correlation,
            "volume_ratio": recent_volume / avg_volume if avg_volume > 0 else 1.0
        }
    
    def generate_signal(self, symbol: str, market_data: Dict[str, Any]) -> TechnicalSignal:
        """Generate trading signal based on technical analysis"""
        try:
            prices = market_data.get("prices", [])
            volumes = market_data.get("volumes", [])
            highs = market_data.get("highs", prices)
            lows = market_data.get("lows", prices)
            
            if len(prices) < 50:
                return self._create_hold_signal(symbol, prices[-1] if prices else 0)
            
            current_price = prices[-1]
            
            # Calculate technical indicators
            rsi = self.calculate_rsi(prices)
            macd = self.calculate_macd(prices)
            bollinger = self.calculate_bollinger_bands(prices)
            stochastic = self.calculate_stochastic(highs, lows, prices)
            momentum = self.analyze_momentum(prices)
            volume_analysis = self.analyze_volume(prices, volumes) if volumes else {}
            
            # Calculate moving averages
            sma_20 = self.calculate_sma(prices, 20)
            sma_50 = self.calculate_sma(prices, 50)
            ema_12 = self.calculate_ema(prices, 12)
            ema_26 = self.calculate_ema(prices, 26)
            
            # Scoring system for signal generation
            buy_score = 0
            sell_score = 0
            indicators = {}
            
            # RSI Analysis
            if rsi:
                current_rsi = rsi[-1]
                indicators["rsi"] = current_rsi
                
                if current_rsi < 30:  # Oversold
                    buy_score += 2
                elif current_rsi < 40:
                    buy_score += 1
                elif current_rsi > 70:  # Overbought
                    sell_score += 2
                elif current_rsi > 60:
                    sell_score += 1
            
            # MACD Analysis
            if macd["macd"] and macd["signal"]:
                macd_line = macd["macd"][-1]
                signal_line = macd["signal"][-1]
                histogram = macd["histogram"][-1] if macd["histogram"] else 0
                
                indicators["macd"] = macd_line
                indicators["macd_signal"] = signal_line
                indicators["macd_histogram"] = histogram
                
                if macd_line > signal_line and histogram > 0:
                    buy_score += 2
                elif macd_line < signal_line and histogram < 0:
                    sell_score += 2
            
            # Bollinger Bands Analysis
            if bollinger["upper"] and bollinger["lower"]:
                upper_band = bollinger["upper"][-1]
                lower_band = bollinger["lower"][-1]
                middle_band = bollinger["middle"][-1]
                
                indicators["bb_upper"] = upper_band
                indicators["bb_lower"] = lower_band
                indicators["bb_middle"] = middle_band
                
                if current_price <= lower_band:  # Price at lower band
                    buy_score += 2
                elif current_price >= upper_band:  # Price at upper band
                    sell_score += 2
                elif current_price > middle_band:
                    buy_score += 1
                else:
                    sell_score += 1
            
            # Moving Average Analysis
            if sma_20 and sma_50:
                sma_20_current = sma_20[-1]
                sma_50_current = sma_50[-1]
                
                indicators["sma_20"] = sma_20_current
                indicators["sma_50"] = sma_50_current
                
                if current_price > sma_20_current > sma_50_current:  # Bullish alignment
                    buy_score += 2
                elif current_price < sma_20_current < sma_50_current:  # Bearish alignment
                    sell_score += 2
                elif current_price > sma_20_current:
                    buy_score += 1
                elif current_price < sma_20_current:
                    sell_score += 1
            
            # Stochastic Analysis
            if stochastic["k"] and stochastic["d"]:
                k_value = stochastic["k"][-1]
                d_value = stochastic["d"][-1]
                
                indicators["stoch_k"] = k_value
                indicators["stoch_d"] = d_value
                
                if k_value < 20 and d_value < 20:  # Oversold
                    buy_score += 1
                elif k_value > 80 and d_value > 80:  # Overbought
                    sell_score += 1
            
            # Momentum Analysis
            momentum_score = momentum.get("momentum_score", 0)
            trend_strength = momentum.get("trend_strength", 0)
            
            indicators["momentum"] = momentum_score
            indicators["trend_strength"] = trend_strength
            
            if momentum_score > 2 and trend_strength > 1:
                buy_score += 2
            elif momentum_score < -2 and trend_strength > 1:
                sell_score += 2
            elif momentum_score > 0:
                buy_score += 1
            elif momentum_score < 0:
                sell_score += 1
            
            # Volume Analysis
            if volume_analysis:
                volume_trend = volume_analysis.get("volume_trend", 0)
                volume_ratio = volume_analysis.get("volume_ratio", 1)
                
                indicators["volume_trend"] = volume_trend
                indicators["volume_ratio"] = volume_ratio
                
                if volume_trend > 20 and volume_ratio > 1.5:  # High volume confirmation
                    if buy_score > sell_score:
                        buy_score += 1
                    elif sell_score > buy_score:
                        sell_score += 1
            
            # Generate signal based on scores
            total_score = buy_score + sell_score
            if total_score == 0:
                return self._create_hold_signal(symbol, current_price, indicators)
            
            if buy_score > sell_score:
                signal_strength = buy_score / (buy_score + sell_score)
                confidence = min(signal_strength * 1.2, 1.0)  # Boost confidence slightly
                
                # Calculate stop loss and take profit
                stop_loss = self.calculator.to_decimal(current_price * 0.98)  # 2% stop loss
                take_profit = self.calculator.to_decimal(current_price * 1.06)  # 6% take profit
                
                reasoning = self._generate_buy_reasoning(indicators, buy_score, sell_score)
                
                return TechnicalSignal(
                    symbol=symbol,
                    signal_type="BUY",
                    strength=signal_strength,
                    confidence=confidence,
                    entry_price=self.calculator.to_decimal(current_price),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    reasoning=reasoning,
                    timestamp=datetime.utcnow()
                )
            
            else:
                signal_strength = sell_score / (buy_score + sell_score)
                confidence = min(signal_strength * 1.2, 1.0)
                
                # Calculate stop loss and take profit for short position
                stop_loss = self.calculator.to_decimal(current_price * 1.02)  # 2% stop loss
                take_profit = self.calculator.to_decimal(current_price * 0.94)  # 6% take profit
                
                reasoning = self._generate_sell_reasoning(indicators, buy_score, sell_score)
                
                return TechnicalSignal(
                    symbol=symbol,
                    signal_type="SELL",
                    strength=signal_strength,
                    confidence=confidence,
                    entry_price=self.calculator.to_decimal(current_price),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    indicators=indicators,
                    reasoning=reasoning,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return self._create_hold_signal(symbol, current_price if 'current_price' in locals() else 0)
    
    def _create_hold_signal(self, symbol: str, price: float, indicators: Dict = None) -> TechnicalSignal:
        """Create a HOLD signal"""
        return TechnicalSignal(
            symbol=symbol,
            signal_type="HOLD",
            strength=0.0,
            confidence=0.5,
            entry_price=self.calculator.to_decimal(price),
            stop_loss=None,
            take_profit=None,
            indicators=indicators or {},
            reasoning="Insufficient data or conflicting signals. Holding position.",
            timestamp=datetime.utcnow()
        )
    
    def _generate_buy_reasoning(self, indicators: Dict, buy_score: int, sell_score: int) -> str:
        """Generate reasoning for buy signal"""
        reasons = []
        
        if indicators.get("rsi", 50) < 40:
            reasons.append("RSI indicates oversold conditions")
        
        if indicators.get("macd_histogram", 0) > 0:
            reasons.append("MACD showing bullish momentum")
        
        if indicators.get("momentum", 0) > 1:
            reasons.append("Strong upward price momentum")
        
        if indicators.get("bb_lower", 0) > 0 and "bb_lower" in indicators:
            current_price = indicators.get("current_price", 0)
            if current_price <= indicators["bb_lower"]:
                reasons.append("Price touching lower Bollinger Band")
        
        if indicators.get("volume_trend", 0) > 10:
            reasons.append("Increasing volume supports the move")
        
        base_reason = f"Technical analysis favors BUY with score {buy_score} vs {sell_score}."
        if reasons:
            return base_reason + " Key factors: " + ", ".join(reasons[:3])
        else:
            return base_reason + " Multiple indicators align for bullish outlook."
    
    def _generate_sell_reasoning(self, indicators: Dict, buy_score: int, sell_score: int) -> str:
        """Generate reasoning for sell signal"""
        reasons = []
        
        if indicators.get("rsi", 50) > 60:
            reasons.append("RSI indicates overbought conditions")
        
        if indicators.get("macd_histogram", 0) < 0:
            reasons.append("MACD showing bearish momentum")
        
        if indicators.get("momentum", 0) < -1:
            reasons.append("Strong downward price momentum")
        
        if indicators.get("bb_upper", 0) > 0 and "bb_upper" in indicators:
            current_price = indicators.get("current_price", 0)
            if current_price >= indicators["bb_upper"]:
                reasons.append("Price touching upper Bollinger Band")
        
        if indicators.get("volume_trend", 0) > 10:
            reasons.append("Increasing volume supports the move")
        
        base_reason = f"Technical analysis favors SELL with score {sell_score} vs {buy_score}."
        if reasons:
            return base_reason + " Key factors: " + ", ".join(reasons[:3])
        else:
            return base_reason + " Multiple indicators align for bearish outlook."


class StrategyEngine:
    """Strategy engine that combines multiple technical analysis approaches"""
    
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
    
    def btc_lightning_scalp_strategy(self, market_data: Dict[str, Any]) -> TechnicalSignal:
        """BTC Lightning Scalp Strategy - Quick momentum-based trades"""
        signal = self.analyzer.generate_signal("BTC-USDT", market_data)
        
        # Adjust for scalping (tighter stops, quicker profits)
        if signal.signal_type in ["BUY", "SELL"]:
            current_price = signal.entry_price
            
            if signal.signal_type == "BUY":
                signal.stop_loss = current_price * Decimal('0.995')  # 0.5% stop
                signal.take_profit = current_price * Decimal('1.015')  # 1.5% profit
            else:
                signal.stop_loss = current_price * Decimal('1.005')  # 0.5% stop
                signal.take_profit = current_price * Decimal('0.985')  # 1.5% profit
            
            signal.reasoning += " [Scalping strategy: tight stops, quick profits]"
        
        return signal
    
    def eth_defi_correlation_strategy(self, market_data: Dict[str, Any]) -> TechnicalSignal:
        """ETH DeFi Correlation Strategy - ETH moves based on DeFi sentiment"""
        signal = self.analyzer.generate_signal("ETH-USDT", market_data)
        
        # Adjust confidence based on DeFi market conditions
        # In a real implementation, this would incorporate DeFi TVL, yields, etc.
        signal.confidence *= 0.9  # Slightly reduce confidence for correlation dependency
        signal.reasoning += " [DeFi correlation strategy: ETH moves with DeFi ecosystem]"
        
        return signal
    
    def cross_asset_arbitrage_strategy(self, btc_data: Dict, eth_data: Dict) -> List[TechnicalSignal]:
        """Cross-Asset Arbitrage Strategy - BTC/ETH relative value"""
        btc_signal = self.analyzer.generate_signal("BTC-USDT", btc_data)
        eth_signal = self.analyzer.generate_signal("ETH-USDT", eth_data)
        
        signals = []
        
        # Look for divergence in signals
        if btc_signal.signal_type == "BUY" and eth_signal.signal_type == "SELL":
            # BTC strong, ETH weak - go long BTC, short ETH
            btc_signal.reasoning += " [Arbitrage: BTC outperforming ETH]"
            eth_signal.reasoning += " [Arbitrage: ETH underperforming BTC]"
            signals.extend([btc_signal, eth_signal])
        
        elif btc_signal.signal_type == "SELL" and eth_signal.signal_type == "BUY":
            # ETH strong, BTC weak - go long ETH, short BTC
            btc_signal.reasoning += " [Arbitrage: BTC underperforming ETH]"
            eth_signal.reasoning += " [Arbitrage: ETH outperforming BTC]"
            signals.extend([btc_signal, eth_signal])
        
        return signals
    
    def fear_greed_contrarian_strategy(self, market_data: Dict[str, Any], fear_greed_index: int) -> TechnicalSignal:
        """Fear & Greed Contrarian Strategy - Contrarian approach to market sentiment"""
        signal = self.analyzer.generate_signal("BTC-USDT", market_data)
        
        # Adjust signal based on Fear & Greed Index
        if fear_greed_index <= 20:  # Extreme Fear
            if signal.signal_type == "SELL":
                signal.signal_type = "BUY"  # Contrarian
                signal.confidence = min(signal.confidence * 1.3, 1.0)
                signal.reasoning = f"Contrarian BUY: Extreme Fear (F&G: {fear_greed_index}). " + signal.reasoning
        
        elif fear_greed_index >= 80:  # Extreme Greed
            if signal.signal_type == "BUY":
                signal.signal_type = "SELL"  # Contrarian
                signal.confidence = min(signal.confidence * 1.3, 1.0)
                signal.reasoning = f"Contrarian SELL: Extreme Greed (F&G: {fear_greed_index}). " + signal.reasoning
        
        else:
            signal.reasoning += f" [F&G Index: {fear_greed_index} - neutral sentiment]"
        
        return signal

