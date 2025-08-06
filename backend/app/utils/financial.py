"""
Financial Utilities for Crypto-0DTE System

Provides precise financial calculations using Decimal arithmetic
to avoid floating-point precision errors in trading operations.
"""

from decimal import Decimal, getcontext, ROUND_HALF_UP, ROUND_DOWN
from typing import Union, Optional
import logging

# Set decimal precision for financial calculations
getcontext().prec = 28  # 28 decimal places for high precision

logger = logging.getLogger(__name__)


class FinancialCalculator:
    """High-precision financial calculator using Decimal arithmetic"""
    
    @staticmethod
    def to_decimal(value: Union[str, int, float, Decimal]) -> Decimal:
        """Convert value to Decimal with proper handling"""
        if isinstance(value, Decimal):
            return value
        elif isinstance(value, (int, str)):
            return Decimal(str(value))
        elif isinstance(value, float):
            # Convert float to string first to avoid precision issues
            return Decimal(str(value))
        else:
            raise ValueError(f"Cannot convert {type(value)} to Decimal")
    
    @staticmethod
    def calculate_position_size(
        account_balance: Union[str, int, float, Decimal],
        risk_percentage: Union[str, int, float, Decimal],
        entry_price: Union[str, int, float, Decimal],
        stop_loss_price: Union[str, int, float, Decimal]
    ) -> Decimal:
        """
        Calculate position size based on risk management rules
        
        Args:
            account_balance: Total account balance
            risk_percentage: Percentage of account to risk (e.g., 0.02 for 2%)
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            
        Returns:
            Position size in base currency units
        """
        try:
            balance = FinancialCalculator.to_decimal(account_balance)
            risk_pct = FinancialCalculator.to_decimal(risk_percentage)
            entry = FinancialCalculator.to_decimal(entry_price)
            stop_loss = FinancialCalculator.to_decimal(stop_loss_price)
            
            # Calculate risk amount
            risk_amount = balance * risk_pct
            
            # Calculate price difference (risk per unit)
            price_diff = abs(entry - stop_loss)
            
            if price_diff == 0:
                raise ValueError("Entry price and stop loss price cannot be the same")
            
            # Calculate position size
            position_size = risk_amount / price_diff
            
            # Round down to avoid over-risking
            return position_size.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            raise
    
    @staticmethod
    def calculate_pnl(
        position_size: Union[str, int, float, Decimal],
        entry_price: Union[str, int, float, Decimal],
        exit_price: Union[str, int, float, Decimal],
        position_type: str = "long"
    ) -> Decimal:
        """
        Calculate profit and loss for a position
        
        Args:
            position_size: Size of the position
            entry_price: Entry price
            exit_price: Exit price
            position_type: "long" or "short"
            
        Returns:
            PnL amount (positive for profit, negative for loss)
        """
        try:
            size = FinancialCalculator.to_decimal(position_size)
            entry = FinancialCalculator.to_decimal(entry_price)
            exit = FinancialCalculator.to_decimal(exit_price)
            
            if position_type.lower() == "long":
                pnl = size * (exit - entry)
            elif position_type.lower() == "short":
                pnl = size * (entry - exit)
            else:
                raise ValueError("Position type must be 'long' or 'short'")
            
            return pnl.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating PnL: {e}")
            raise
    
    @staticmethod
    def calculate_percentage_change(
        initial_value: Union[str, int, float, Decimal],
        final_value: Union[str, int, float, Decimal]
    ) -> Decimal:
        """Calculate percentage change between two values"""
        try:
            initial = FinancialCalculator.to_decimal(initial_value)
            final = FinancialCalculator.to_decimal(final_value)
            
            if initial == 0:
                raise ValueError("Initial value cannot be zero")
            
            change = ((final - initial) / initial) * Decimal('100')
            return change.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating percentage change: {e}")
            raise
    
    @staticmethod
    def calculate_compound_return(
        initial_balance: Union[str, int, float, Decimal],
        returns: list,
        periods: int = None
    ) -> Decimal:
        """Calculate compound return over multiple periods"""
        try:
            balance = FinancialCalculator.to_decimal(initial_balance)
            
            for return_pct in returns:
                return_decimal = FinancialCalculator.to_decimal(return_pct)
                balance = balance * (Decimal('1') + return_decimal / Decimal('100'))
            
            return balance.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating compound return: {e}")
            raise
    
    @staticmethod
    def calculate_sharpe_ratio(
        returns: list,
        risk_free_rate: Union[str, int, float, Decimal] = Decimal('0.02')
    ) -> Decimal:
        """Calculate Sharpe ratio for a series of returns"""
        try:
            if not returns:
                return Decimal('0')
            
            returns_decimal = [FinancialCalculator.to_decimal(r) for r in returns]
            risk_free = FinancialCalculator.to_decimal(risk_free_rate)
            
            # Calculate mean return
            mean_return = sum(returns_decimal) / Decimal(len(returns_decimal))
            
            # Calculate standard deviation
            variance = sum((r - mean_return) ** 2 for r in returns_decimal) / Decimal(len(returns_decimal))
            std_dev = variance.sqrt()
            
            if std_dev == 0:
                return Decimal('0')
            
            # Calculate Sharpe ratio
            sharpe = (mean_return - risk_free) / std_dev
            return sharpe.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            raise
    
    @staticmethod
    def calculate_max_drawdown(balance_history: list) -> Decimal:
        """Calculate maximum drawdown from balance history"""
        try:
            if not balance_history:
                return Decimal('0')
            
            balances = [FinancialCalculator.to_decimal(b) for b in balance_history]
            
            max_balance = balances[0]
            max_drawdown = Decimal('0')
            
            for balance in balances:
                if balance > max_balance:
                    max_balance = balance
                
                drawdown = (max_balance - balance) / max_balance * Decimal('100')
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return max_drawdown.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            raise
    
    @staticmethod
    def calculate_fees(
        trade_amount: Union[str, int, float, Decimal],
        fee_rate: Union[str, int, float, Decimal]
    ) -> Decimal:
        """Calculate trading fees"""
        try:
            amount = FinancialCalculator.to_decimal(trade_amount)
            rate = FinancialCalculator.to_decimal(fee_rate)
            
            fees = amount * rate
            return fees.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating fees: {e}")
            raise
    
    @staticmethod
    def calculate_slippage_adjusted_price(
        intended_price: Union[str, int, float, Decimal],
        slippage_percentage: Union[str, int, float, Decimal],
        order_type: str = "buy"
    ) -> Decimal:
        """Calculate price adjusted for slippage"""
        try:
            price = FinancialCalculator.to_decimal(intended_price)
            slippage = FinancialCalculator.to_decimal(slippage_percentage)
            
            if order_type.lower() == "buy":
                # For buy orders, slippage increases the price
                adjusted_price = price * (Decimal('1') + slippage / Decimal('100'))
            elif order_type.lower() == "sell":
                # For sell orders, slippage decreases the price
                adjusted_price = price * (Decimal('1') - slippage / Decimal('100'))
            else:
                raise ValueError("Order type must be 'buy' or 'sell'")
            
            return adjusted_price.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating slippage-adjusted price: {e}")
            raise


class RiskManager:
    """Risk management utilities with precise calculations"""
    
    @staticmethod
    def validate_position_size(
        position_size: Union[str, int, float, Decimal],
        account_balance: Union[str, int, float, Decimal],
        max_position_percentage: Union[str, int, float, Decimal] = Decimal('0.30')
    ) -> bool:
        """Validate if position size is within risk limits"""
        try:
            size = FinancialCalculator.to_decimal(position_size)
            balance = FinancialCalculator.to_decimal(account_balance)
            max_pct = FinancialCalculator.to_decimal(max_position_percentage)
            
            max_allowed = balance * max_pct
            return size <= max_allowed
            
        except Exception as e:
            logger.error(f"Error validating position size: {e}")
            return False
    
    @staticmethod
    def calculate_portfolio_risk(
        positions: list,
        correlations: dict = None
    ) -> Decimal:
        """Calculate overall portfolio risk"""
        try:
            if not positions:
                return Decimal('0')
            
            # Simple risk calculation (sum of individual position risks)
            # In a real implementation, this would consider correlations
            total_risk = Decimal('0')
            
            for position in positions:
                position_risk = FinancialCalculator.to_decimal(position.get('risk', 0))
                total_risk += position_risk
            
            return total_risk.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            raise


# Convenience functions for common calculations
def safe_divide(
    numerator: Union[str, int, float, Decimal],
    denominator: Union[str, int, float, Decimal]
) -> Optional[Decimal]:
    """Safely divide two numbers, returning None if denominator is zero"""
    try:
        num = FinancialCalculator.to_decimal(numerator)
        den = FinancialCalculator.to_decimal(denominator)
        
        if den == 0:
            return None
        
        return num / den
    except Exception:
        return None


def format_currency(
    amount: Union[str, int, float, Decimal],
    currency: str = "USD",
    decimal_places: int = 2
) -> str:
    """Format amount as currency string"""
    try:
        decimal_amount = FinancialCalculator.to_decimal(amount)
        quantized = decimal_amount.quantize(
            Decimal('0.' + '0' * decimal_places),
            rounding=ROUND_HALF_UP
        )
        return f"{currency} {quantized:,}"
    except Exception:
        return f"{currency} 0.00"

