"""
Transaction Service for Crypto-0DTE System

Provides atomic transaction operations with proper rollback handling
and financial precision using Decimal arithmetic.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
import logging
from datetime import datetime

from app.models.portfolio import Portfolio, Position, Transaction, TransactionType, PositionStatus
from app.models.signal import Signal
from app.utils.financial import FinancialCalculator
from app.database import get_db


logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """Custom exception for transaction errors"""
    pass


class InsufficientFundsError(TransactionError):
    """Exception raised when insufficient funds for transaction"""
    pass


class PositionNotFoundError(TransactionError):
    """Exception raised when position is not found"""
    pass


class TransactionService:
    """Service for handling atomic financial transactions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.calculator = FinancialCalculator()
    
    def execute_buy_order(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        signal_id: Optional[int] = None,
        exchange_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a buy order with atomic transaction handling
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Trading symbol (e.g., "BTC-USDT")
            quantity: Quantity to buy
            price: Price per unit
            signal_id: Optional signal ID that triggered this trade
            exchange_order_id: Exchange order ID for tracking
            
        Returns:
            Dictionary with transaction details
        """
        try:
            # Start database transaction
            with self.db.begin():
                # Get portfolio
                portfolio = self.db.query(Portfolio).filter(
                    Portfolio.id == portfolio_id
                ).with_for_update().first()
                
                if not portfolio:
                    raise TransactionError(f"Portfolio {portfolio_id} not found")
                
                # Calculate transaction details
                quantity_decimal = self.calculator.to_decimal(quantity)
                price_decimal = self.calculator.to_decimal(price)
                total_cost = quantity_decimal * price_decimal
                
                # Calculate fees (assuming 0.1% trading fee)
                fee_rate = Decimal('0.001')
                trading_fee = self.calculator.calculate_fees(total_cost, fee_rate)
                total_amount = total_cost + trading_fee
                
                # Check if sufficient funds
                if portfolio.cash_balance < total_amount:
                    raise InsufficientFundsError(
                        f"Insufficient funds. Required: {total_amount}, Available: {portfolio.cash_balance}"
                    )
                
                # Update portfolio cash balance
                portfolio.cash_balance -= total_amount
                portfolio.invested_amount += total_cost
                
                # Find or create position
                position = self.db.query(Position).filter(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.symbol == symbol,
                        Position.status == PositionStatus.OPEN
                    )
                ).first()
                
                if position:
                    # Update existing position
                    old_total_cost = position.total_cost
                    old_quantity = position.quantity
                    
                    # Calculate new average price
                    new_total_cost = old_total_cost + total_cost
                    new_quantity = old_quantity + quantity_decimal
                    new_average_price = new_total_cost / new_quantity
                    
                    position.quantity = new_quantity
                    position.average_price = new_average_price
                    position.total_cost = new_total_cost
                    position.current_price = price_decimal
                    position.market_value = new_quantity * price_decimal
                    position.updated_at = datetime.utcnow()
                    
                else:
                    # Create new position
                    position = Position(
                        portfolio_id=portfolio_id,
                        symbol=symbol,
                        quantity=quantity_decimal,
                        average_price=price_decimal,
                        current_price=price_decimal,
                        total_cost=total_cost,
                        market_value=quantity_decimal * price_decimal,
                        status=PositionStatus.OPEN,
                        is_active=True
                    )
                    self.db.add(position)
                    self.db.flush()  # Get position ID
                
                # Create transaction record
                transaction = Transaction(
                    portfolio_id=portfolio_id,
                    position_id=position.id,
                    transaction_type=TransactionType.BUY,
                    symbol=symbol,
                    quantity=quantity_decimal,
                    price=price_decimal,
                    total_amount=total_cost,
                    commission=trading_fee,
                    total_fees=trading_fee,
                    exchange_order_id=exchange_order_id,
                    signal_id=signal_id,
                    status="COMPLETED"
                )
                self.db.add(transaction)
                
                # Update portfolio metrics
                self._update_portfolio_metrics(portfolio)
                
                # Commit transaction
                self.db.commit()
                
                logger.info(f"Buy order executed: {symbol} x {quantity} @ {price}")
                
                return {
                    "success": True,
                    "transaction_id": transaction.id,
                    "position_id": position.id,
                    "symbol": symbol,
                    "quantity": float(quantity_decimal),
                    "price": float(price_decimal),
                    "total_cost": float(total_cost),
                    "fees": float(trading_fee),
                    "new_position_size": float(position.quantity),
                    "average_price": float(position.average_price)
                }
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Buy order failed: {e}")
            raise TransactionError(f"Buy order failed: {str(e)}")
    
    def execute_sell_order(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        signal_id: Optional[int] = None,
        exchange_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a sell order with atomic transaction handling
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Trading symbol
            quantity: Quantity to sell
            price: Price per unit
            signal_id: Optional signal ID that triggered this trade
            exchange_order_id: Exchange order ID for tracking
            
        Returns:
            Dictionary with transaction details
        """
        try:
            # Start database transaction
            with self.db.begin():
                # Get portfolio
                portfolio = self.db.query(Portfolio).filter(
                    Portfolio.id == portfolio_id
                ).with_for_update().first()
                
                if not portfolio:
                    raise TransactionError(f"Portfolio {portfolio_id} not found")
                
                # Get position
                position = self.db.query(Position).filter(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.symbol == symbol,
                        Position.status == PositionStatus.OPEN
                    )
                ).with_for_update().first()
                
                if not position:
                    raise PositionNotFoundError(f"No open position found for {symbol}")
                
                # Calculate transaction details
                quantity_decimal = self.calculator.to_decimal(quantity)
                price_decimal = self.calculator.to_decimal(price)
                
                # Check if sufficient quantity
                if position.quantity < quantity_decimal:
                    raise TransactionError(
                        f"Insufficient quantity. Requested: {quantity_decimal}, Available: {position.quantity}"
                    )
                
                # Calculate sale proceeds
                gross_proceeds = quantity_decimal * price_decimal
                
                # Calculate fees
                fee_rate = Decimal('0.001')
                trading_fee = self.calculator.calculate_fees(gross_proceeds, fee_rate)
                net_proceeds = gross_proceeds - trading_fee
                
                # Calculate realized P&L
                cost_basis = quantity_decimal * position.average_price
                realized_pnl = net_proceeds - cost_basis
                
                # Update position
                position.quantity -= quantity_decimal
                position.current_price = price_decimal
                position.realized_pnl += realized_pnl
                
                if position.quantity == 0:
                    # Close position completely
                    position.status = PositionStatus.CLOSED
                    position.closed_at = datetime.utcnow()
                    position.is_active = False
                else:
                    # Partial sale
                    position.status = PositionStatus.PARTIAL
                    position.total_cost -= cost_basis
                    position.market_value = position.quantity * price_decimal
                
                position.updated_at = datetime.utcnow()
                
                # Update portfolio
                portfolio.cash_balance += net_proceeds
                portfolio.invested_amount -= cost_basis
                portfolio.total_pnl += realized_pnl
                
                # Create transaction record
                transaction = Transaction(
                    portfolio_id=portfolio_id,
                    position_id=position.id,
                    transaction_type=TransactionType.SELL,
                    symbol=symbol,
                    quantity=quantity_decimal,
                    price=price_decimal,
                    total_amount=gross_proceeds,
                    commission=trading_fee,
                    total_fees=trading_fee,
                    realized_pnl=realized_pnl,
                    cost_basis=cost_basis,
                    exchange_order_id=exchange_order_id,
                    signal_id=signal_id,
                    status="COMPLETED"
                )
                self.db.add(transaction)
                
                # Update portfolio metrics
                self._update_portfolio_metrics(portfolio)
                
                # Commit transaction
                self.db.commit()
                
                logger.info(f"Sell order executed: {symbol} x {quantity} @ {price}, PnL: {realized_pnl}")
                
                return {
                    "success": True,
                    "transaction_id": transaction.id,
                    "position_id": position.id,
                    "symbol": symbol,
                    "quantity": float(quantity_decimal),
                    "price": float(price_decimal),
                    "gross_proceeds": float(gross_proceeds),
                    "net_proceeds": float(net_proceeds),
                    "fees": float(trading_fee),
                    "realized_pnl": float(realized_pnl),
                    "remaining_quantity": float(position.quantity),
                    "position_status": position.status.value
                }
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Sell order failed: {e}")
            raise TransactionError(f"Sell order failed: {str(e)}")
    
    def _update_portfolio_metrics(self, portfolio: Portfolio):
        """Update portfolio performance metrics"""
        try:
            # Get all active positions
            positions = self.db.query(Position).filter(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.is_active == True
                )
            ).all()
            
            # Calculate total market value
            total_market_value = Decimal('0')
            for position in positions:
                position.market_value = position.quantity * position.current_price
                position.unrealized_pnl = position.market_value - (position.quantity * position.average_price)
                if position.quantity > 0:
                    position.unrealized_pnl_percentage = (position.unrealized_pnl / (position.quantity * position.average_price)) * Decimal('100')
                total_market_value += position.market_value
            
            # Update portfolio totals
            portfolio.total_value = portfolio.cash_balance + total_market_value
            
            if portfolio.invested_amount > 0:
                portfolio.total_pnl_percentage = (portfolio.total_pnl / portfolio.invested_amount) * Decimal('100')
            
            portfolio.updated_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error updating portfolio metrics: {e}")
            raise
    
    def get_transaction_history(
        self,
        portfolio_id: int,
        symbol: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 100
    ) -> List[Transaction]:
        """Get transaction history for a portfolio"""
        try:
            query = self.db.query(Transaction).filter(
                Transaction.portfolio_id == portfolio_id
            )
            
            if symbol:
                query = query.filter(Transaction.symbol == symbol)
            
            if transaction_type:
                query = query.filter(Transaction.transaction_type == transaction_type)
            
            return query.order_by(Transaction.executed_at.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            raise TransactionError(f"Failed to get transaction history: {str(e)}")
    
    def calculate_portfolio_performance(self, portfolio_id: int) -> Dict[str, Any]:
        """Calculate comprehensive portfolio performance metrics"""
        try:
            portfolio = self.db.query(Portfolio).filter(
                Portfolio.id == portfolio_id
            ).first()
            
            if not portfolio:
                raise TransactionError(f"Portfolio {portfolio_id} not found")
            
            # Get all transactions
            transactions = self.get_transaction_history(portfolio_id, limit=1000)
            
            # Calculate performance metrics
            total_invested = sum(
                float(t.total_amount) for t in transactions 
                if t.transaction_type == TransactionType.BUY
            )
            
            total_proceeds = sum(
                float(t.total_amount) for t in transactions 
                if t.transaction_type == TransactionType.SELL
            )
            
            total_fees = sum(float(t.total_fees) for t in transactions)
            
            return {
                "portfolio_id": portfolio_id,
                "total_value": float(portfolio.total_value),
                "cash_balance": float(portfolio.cash_balance),
                "invested_amount": float(portfolio.invested_amount),
                "total_pnl": float(portfolio.total_pnl),
                "total_pnl_percentage": float(portfolio.total_pnl_percentage),
                "total_invested": total_invested,
                "total_proceeds": total_proceeds,
                "total_fees": total_fees,
                "total_trades": len(transactions),
                "win_rate": float(portfolio.win_rate),
                "sharpe_ratio": float(portfolio.sharpe_ratio) if portfolio.sharpe_ratio else None,
                "max_drawdown": float(portfolio.max_drawdown)
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio performance: {e}")
            raise TransactionError(f"Failed to calculate performance: {str(e)}")

