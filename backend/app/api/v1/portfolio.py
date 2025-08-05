"""
Portfolio API Endpoints

Provides portfolio management, position tracking, and P&L analysis functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.portfolio import Portfolio, Position, Transaction

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Pydantic models for API responses
class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    total_value: float
    cash_balance: float
    invested_amount: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    pnl_percentage: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PositionResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    position_type: str
    opened_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    total_amount: float
    fees: float
    executed_at: datetime
    order_id: Optional[str]
    
    class Config:
        from_attributes = True

class CreatePortfolioRequest(BaseModel):
    name: str
    initial_cash: float = 10000.0

class CreateTransactionRequest(BaseModel):
    symbol: str
    transaction_type: str  # BUY, SELL
    quantity: float
    price: float
    fees: float = 0.0

@router.get("/", response_model=List[PortfolioResponse])
async def get_portfolios(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db)
):
    """Get all portfolios, optionally filtered by user"""
    try:
        query = db.query(Portfolio)
        if user_id:
            query = query.filter(Portfolio.user_id == user_id)
        
        portfolios = query.order_by(Portfolio.created_at.desc()).all()
        return [PortfolioResponse.from_orm(portfolio) for portfolio in portfolios]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolios: {str(e)}")

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific portfolio by ID"""
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return PortfolioResponse.from_orm(portfolio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio: {str(e)}")

@router.post("/", response_model=PortfolioResponse)
async def create_portfolio(
    portfolio_request: CreatePortfolioRequest,
    user_id: int = Query(..., description="User ID for the portfolio"),
    db: Session = Depends(get_db)
):
    """Create a new portfolio"""
    try:
        portfolio = Portfolio(
            user_id=user_id,
            name=portfolio_request.name,
            cash_balance=portfolio_request.initial_cash,
            total_value=portfolio_request.initial_cash,
            invested_amount=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            total_pnl=0.0,
            pnl_percentage=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
        
        return PortfolioResponse.from_orm(portfolio)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create portfolio: {str(e)}")

@router.get("/{portfolio_id}/positions", response_model=List[PositionResponse])
async def get_portfolio_positions(
    portfolio_id: int,
    active_only: bool = Query(True, description="Show only active positions"),
    db: Session = Depends(get_db)
):
    """Get all positions in a portfolio"""
    try:
        query = db.query(Position).filter(Position.portfolio_id == portfolio_id)
        if active_only:
            query = query.filter(Position.quantity > 0)
        
        positions = query.order_by(Position.updated_at.desc()).all()
        return [PositionResponse.from_orm(position) for position in positions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch positions: {str(e)}")

@router.get("/{portfolio_id}/transactions", response_model=List[TransactionResponse])
async def get_portfolio_transactions(
    portfolio_id: int,
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    transaction_type: Optional[str] = Query(None, description="Filter by type (BUY, SELL)"),
    limit: int = Query(100, description="Number of transactions to return"),
    db: Session = Depends(get_db)
):
    """Get transaction history for a portfolio"""
    try:
        query = db.query(Transaction).filter(Transaction.portfolio_id == portfolio_id)
        
        if symbol:
            query = query.filter(Transaction.symbol == symbol)
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        transactions = query.order_by(Transaction.executed_at.desc()).limit(limit).all()
        return [TransactionResponse.from_orm(transaction) for transaction in transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transactions: {str(e)}")

@router.post("/{portfolio_id}/transactions", response_model=TransactionResponse)
async def create_transaction(
    portfolio_id: int,
    transaction_request: CreateTransactionRequest,
    db: Session = Depends(get_db)
):
    """Create a new transaction (buy/sell)"""
    try:
        # Verify portfolio exists
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        # Calculate total amount
        total_amount = transaction_request.quantity * transaction_request.price + transaction_request.fees
        
        # Check if sufficient cash for buy orders
        if transaction_request.transaction_type == "BUY" and portfolio.cash_balance < total_amount:
            raise HTTPException(status_code=400, detail="Insufficient cash balance")
        
        # Create transaction
        transaction = Transaction(
            portfolio_id=portfolio_id,
            symbol=transaction_request.symbol,
            transaction_type=transaction_request.transaction_type,
            quantity=transaction_request.quantity,
            price=transaction_request.price,
            total_amount=total_amount,
            fees=transaction_request.fees,
            executed_at=datetime.utcnow()
        )
        
        db.add(transaction)
        
        # Update portfolio cash balance
        if transaction_request.transaction_type == "BUY":
            portfolio.cash_balance -= total_amount
        else:  # SELL
            portfolio.cash_balance += (total_amount - transaction_request.fees)
        
        # Update or create position
        position = db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.symbol == transaction_request.symbol
        ).first()
        
        if not position:
            position = Position(
                portfolio_id=portfolio_id,
                symbol=transaction_request.symbol,
                quantity=0.0,
                avg_entry_price=0.0,
                current_price=transaction_request.price,
                market_value=0.0,
                unrealized_pnl=0.0,
                unrealized_pnl_percentage=0.0,
                position_type="LONG",
                opened_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(position)
        
        # Update position quantity and average price
        if transaction_request.transaction_type == "BUY":
            total_cost = (position.quantity * position.avg_entry_price) + (transaction_request.quantity * transaction_request.price)
            total_quantity = position.quantity + transaction_request.quantity
            position.avg_entry_price = total_cost / total_quantity if total_quantity > 0 else 0
            position.quantity = total_quantity
        else:  # SELL
            position.quantity -= transaction_request.quantity
        
        position.current_price = transaction_request.price
        position.market_value = position.quantity * position.current_price
        position.unrealized_pnl = position.market_value - (position.quantity * position.avg_entry_price)
        position.unrealized_pnl_percentage = (position.unrealized_pnl / (position.quantity * position.avg_entry_price)) * 100 if position.quantity > 0 else 0
        position.updated_at = datetime.utcnow()
        
        # Update portfolio totals
        portfolio.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(transaction)
        
        return TransactionResponse.from_orm(transaction)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {str(e)}")

@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get portfolio performance metrics"""
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get transactions in the period
        transactions = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.executed_at >= start_date
        ).all()
        
        # Calculate metrics
        total_trades = len(transactions)
        buy_trades = len([t for t in transactions if t.transaction_type == "BUY"])
        sell_trades = len([t for t in transactions if t.transaction_type == "SELL"])
        total_fees = sum(t.fees for t in transactions)
        
        return {
            "portfolio_id": portfolio_id,
            "period_days": days,
            "total_value": portfolio.total_value,
            "cash_balance": portfolio.cash_balance,
            "invested_amount": portfolio.invested_amount,
            "total_pnl": portfolio.total_pnl,
            "pnl_percentage": portfolio.pnl_percentage,
            "unrealized_pnl": portfolio.unrealized_pnl,
            "realized_pnl": portfolio.realized_pnl,
            "total_trades": total_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "total_fees": total_fees,
            "updated_at": portfolio.updated_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance: {str(e)}")

@router.put("/{portfolio_id}/update-prices")
async def update_portfolio_prices(
    portfolio_id: int,
    db: Session = Depends(get_db)
):
    """Update current prices for all positions in portfolio"""
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        positions = db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.quantity > 0
        ).all()
        
        # In a real implementation, you would fetch current prices from the exchange
        # For now, we'll just update the timestamp
        for position in positions:
            # TODO: Fetch current price from exchange
            # position.current_price = await get_current_price(position.symbol)
            position.market_value = position.quantity * position.current_price
            position.unrealized_pnl = position.market_value - (position.quantity * position.avg_entry_price)
            position.unrealized_pnl_percentage = (position.unrealized_pnl / (position.quantity * position.avg_entry_price)) * 100 if position.quantity > 0 else 0
            position.updated_at = datetime.utcnow()
        
        # Update portfolio totals
        total_market_value = sum(p.market_value for p in positions)
        portfolio.total_value = portfolio.cash_balance + total_market_value
        portfolio.unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        portfolio.total_pnl = portfolio.realized_pnl + portfolio.unrealized_pnl
        portfolio.pnl_percentage = (portfolio.total_pnl / portfolio.invested_amount) * 100 if portfolio.invested_amount > 0 else 0
        portfolio.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "Portfolio prices updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update prices: {str(e)}")

@router.get("/health")
async def portfolio_health():
    """Health check for portfolio service"""
    return {
        "status": "healthy",
        "service": "portfolio",
        "timestamp": datetime.utcnow()
    }

