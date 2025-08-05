"""
Compliance API Endpoints

Provides compliance monitoring, tax reporting, and regulatory functionality.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.compliance import ComplianceLog, TaxRecord

router = APIRouter(prefix="/compliance", tags=["compliance"])

# Pydantic models for API responses
class ComplianceLogResponse(BaseModel):
    id: int
    user_id: int
    event_type: str
    description: str
    severity: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class TaxRecordResponse(BaseModel):
    id: int
    user_id: int
    transaction_id: int
    tax_year: int
    transaction_type: str
    symbol: str
    quantity: float
    price: float
    capital_gain_loss: Optional[float]
    tds_amount: Optional[float]
    tax_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ComplianceReportRequest(BaseModel):
    user_id: int
    start_date: datetime
    end_date: datetime
    report_type: str  # "TAX", "AUDIT", "REGULATORY"

@router.get("/logs", response_model=List[ComplianceLogResponse])
async def get_compliance_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, RESOLVED, DISMISSED)"),
    limit: int = Query(100, description="Number of logs to return"),
    db: Session = Depends(get_db)
):
    """Get compliance logs with optional filters"""
    try:
        query = db.query(ComplianceLog)
        
        if user_id:
            query = query.filter(ComplianceLog.user_id == user_id)
        if event_type:
            query = query.filter(ComplianceLog.event_type == event_type)
        if severity:
            query = query.filter(ComplianceLog.severity == severity)
        if status:
            query = query.filter(ComplianceLog.status == status)
        
        logs = query.order_by(ComplianceLog.created_at.desc()).limit(limit).all()
        return [ComplianceLogResponse.from_orm(log) for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch compliance logs: {str(e)}")

@router.get("/logs/{log_id}", response_model=ComplianceLogResponse)
async def get_compliance_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific compliance log by ID"""
    try:
        log = db.query(ComplianceLog).filter(ComplianceLog.id == log_id).first()
        if not log:
            raise HTTPException(status_code=404, detail="Compliance log not found")
        return ComplianceLogResponse.from_orm(log)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch compliance log: {str(e)}")

@router.post("/logs")
async def create_compliance_log(
    user_id: int,
    event_type: str,
    description: str,
    severity: str = "MEDIUM",
    db: Session = Depends(get_db)
):
    """Create a new compliance log entry"""
    try:
        valid_severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if severity not in valid_severities:
            raise HTTPException(status_code=400, detail=f"Invalid severity. Must be one of: {valid_severities}")
        
        log = ComplianceLog(
            user_id=user_id,
            event_type=event_type,
            description=description,
            severity=severity,
            status="OPEN",
            created_at=datetime.utcnow()
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        return ComplianceLogResponse.from_orm(log)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create compliance log: {str(e)}")

@router.put("/logs/{log_id}/status")
async def update_compliance_log_status(
    log_id: int,
    status: str,
    resolution_notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update compliance log status"""
    try:
        log = db.query(ComplianceLog).filter(ComplianceLog.id == log_id).first()
        if not log:
            raise HTTPException(status_code=404, detail="Compliance log not found")
        
        valid_statuses = ["OPEN", "RESOLVED", "DISMISSED"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        log.status = status
        if status in ["RESOLVED", "DISMISSED"]:
            log.resolved_at = datetime.utcnow()
        
        if resolution_notes:
            log.resolution_notes = resolution_notes
        
        db.commit()
        
        return {"message": f"Compliance log {log_id} status updated to {status}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update compliance log: {str(e)}")

@router.get("/tax-records", response_model=List[TaxRecordResponse])
async def get_tax_records(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    tax_year: Optional[int] = Query(None, description="Filter by tax year"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    tax_status: Optional[str] = Query(None, description="Filter by tax status"),
    limit: int = Query(100, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get tax records with optional filters"""
    try:
        query = db.query(TaxRecord)
        
        if user_id:
            query = query.filter(TaxRecord.user_id == user_id)
        if tax_year:
            query = query.filter(TaxRecord.tax_year == tax_year)
        if transaction_type:
            query = query.filter(TaxRecord.transaction_type == transaction_type)
        if tax_status:
            query = query.filter(TaxRecord.tax_status == tax_status)
        
        records = query.order_by(TaxRecord.created_at.desc()).limit(limit).all()
        return [TaxRecordResponse.from_orm(record) for record in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tax records: {str(e)}")

@router.get("/tax-summary/{user_id}")
async def get_tax_summary(
    user_id: int,
    tax_year: int = Query(..., description="Tax year for summary"),
    db: Session = Depends(get_db)
):
    """Get tax summary for a user and year"""
    try:
        records = db.query(TaxRecord).filter(
            TaxRecord.user_id == user_id,
            TaxRecord.tax_year == tax_year
        ).all()
        
        total_capital_gains = sum(r.capital_gain_loss or 0 for r in records if (r.capital_gain_loss or 0) > 0)
        total_capital_losses = sum(abs(r.capital_gain_loss or 0) for r in records if (r.capital_gain_loss or 0) < 0)
        total_tds = sum(r.tds_amount or 0 for r in records)
        
        buy_transactions = len([r for r in records if r.transaction_type == "BUY"])
        sell_transactions = len([r for r in records if r.transaction_type == "SELL"])
        
        return {
            "user_id": user_id,
            "tax_year": tax_year,
            "total_transactions": len(records),
            "buy_transactions": buy_transactions,
            "sell_transactions": sell_transactions,
            "total_capital_gains": total_capital_gains,
            "total_capital_losses": total_capital_losses,
            "net_capital_gain_loss": total_capital_gains - total_capital_losses,
            "total_tds": total_tds,
            "generated_at": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tax summary: {str(e)}")

@router.post("/generate-report")
async def generate_compliance_report(
    report_request: ComplianceReportRequest,
    db: Session = Depends(get_db)
):
    """Generate compliance report"""
    try:
        valid_report_types = ["TAX", "AUDIT", "REGULATORY"]
        if report_request.report_type not in valid_report_types:
            raise HTTPException(status_code=400, detail=f"Invalid report type. Must be one of: {valid_report_types}")
        
        # In a real implementation, you would:
        # 1. Query relevant data based on report type
        # 2. Generate report document (PDF, Excel, etc.)
        # 3. Store report in database
        # 4. Return report ID or download link
        
        report_id = f"RPT_{report_request.report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "report_id": report_id,
            "report_type": report_request.report_type,
            "user_id": report_request.user_id,
            "start_date": report_request.start_date,
            "end_date": report_request.end_date,
            "status": "GENERATING",
            "generated_at": datetime.utcnow(),
            "message": "Report generation initiated. Check status using report_id."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@router.get("/kyc-status/{user_id}")
async def get_kyc_status(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get KYC (Know Your Customer) status for a user"""
    try:
        # In a real implementation, you would query KYC data from database
        return {
            "user_id": user_id,
            "kyc_status": "VERIFIED",
            "verification_level": "LEVEL_2",
            "documents_submitted": ["PAN", "AADHAAR", "BANK_STATEMENT"],
            "verified_at": datetime.utcnow() - timedelta(days=30),
            "expires_at": datetime.utcnow() + timedelta(days=335),
            "trading_limits": {
                "daily_limit": 1000000.0,
                "monthly_limit": 10000000.0,
                "annual_limit": 100000000.0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch KYC status: {str(e)}")

@router.get("/regulatory-limits")
async def get_regulatory_limits():
    """Get current regulatory limits and requirements"""
    try:
        return {
            "position_limits": {
                "single_stock_max_percentage": 10.0,
                "sector_max_percentage": 25.0,
                "derivative_exposure_limit": 5000000.0
            },
            "reporting_requirements": {
                "large_trade_threshold": 100000.0,
                "suspicious_activity_threshold": 500000.0,
                "daily_reporting_required": True
            },
            "tax_requirements": {
                "tds_rate": 0.1,  # 10%
                "capital_gains_tax_rate": 0.15,  # 15%
                "holding_period_for_ltcg": 365  # days
            },
            "updated_at": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch regulatory limits: {str(e)}")

@router.post("/audit-trail")
async def create_audit_trail(
    user_id: int,
    action: str,
    resource: str,
    details: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Create audit trail entry"""
    try:
        # In a real implementation, you would store audit trail in database
        audit_id = f"AUD_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{user_id}"
        
        return {
            "audit_id": audit_id,
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details,
            "timestamp": datetime.utcnow(),
            "ip_address": "127.0.0.1",  # In real implementation, get from request
            "user_agent": "API Client"  # In real implementation, get from request
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create audit trail: {str(e)}")

@router.get("/health")
async def compliance_health():
    """Health check for compliance service"""
    return {
        "status": "healthy",
        "service": "compliance",
        "regulatory_data_updated": datetime.utcnow() - timedelta(hours=1),
        "timestamp": datetime.utcnow()
    }

