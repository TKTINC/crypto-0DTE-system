"""
Compliance Models for Crypto-0DTE-System

SQLAlchemy models for tax records, TDS tracking, and compliance logging.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class TaxEventType(enum.Enum):
    """Tax event type enumeration."""
    CAPITAL_GAIN = "CAPITAL_GAIN"
    CAPITAL_LOSS = "CAPITAL_LOSS"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    MINING_INCOME = "MINING_INCOME"
    STAKING_REWARD = "STAKING_REWARD"
    AIRDROP = "AIRDROP"
    FORK = "FORK"


class TDSStatus(enum.Enum):
    """TDS status enumeration."""
    PENDING = "PENDING"
    DEDUCTED = "DEDUCTED"
    PAID = "PAID"
    EXEMPTED = "EXEMPTED"


class ComplianceLogLevel(enum.Enum):
    """Compliance log level enumeration."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TaxRecord(Base):
    """
    Tax record model for tracking taxable events and calculations.
    """
    __tablename__ = "tax_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    # Tax Event Details
    tax_year = Column(Integer, nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # From TaxEventType enum
    event_date = Column(DateTime(timezone=True), nullable=False)
    
    # Asset Information
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    
    # Price Information
    acquisition_price = Column(Float, nullable=True)  # Original purchase price
    disposal_price = Column(Float, nullable=True)  # Sale price
    fair_market_value = Column(Float, nullable=False)  # FMV at time of event
    
    # Tax Calculations
    cost_basis = Column(Float, nullable=True)
    proceeds = Column(Float, nullable=True)
    capital_gain_loss = Column(Float, nullable=True)  # Positive for gain, negative for loss
    
    # Holding Period
    acquisition_date = Column(DateTime(timezone=True), nullable=True)
    holding_period_days = Column(Integer, nullable=True)
    is_long_term = Column(Boolean, nullable=True)  # True if held > 1 year
    
    # Tax Rates and Amounts
    applicable_tax_rate = Column(Float, nullable=True)  # Tax rate as percentage
    tax_amount = Column(Float, nullable=True)  # Calculated tax amount
    
    # Indian Tax Specific
    is_speculative = Column(Boolean, default=False)  # For Indian tax classification
    section_applicable = Column(String(20), nullable=True)  # e.g., "44AD", "44ADA"
    
    # Documentation
    supporting_documents = Column(JSON, nullable=True)  # Array of document references
    notes = Column(Text, nullable=True)
    
    # Status and Tracking
    is_reported = Column(Boolean, default=False)  # Has this been included in tax filing?
    reported_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    transaction = relationship("Transaction")

    def __repr__(self):
        return f"<TaxRecord(id={self.id}, year={self.tax_year}, type={self.event_type}, gain_loss={self.capital_gain_loss})>"


class TDSRecord(Base):
    """
    TDS (Tax Deducted at Source) record model for tracking TDS obligations.
    """
    __tablename__ = "tds_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tax_record_id = Column(Integer, ForeignKey("tax_records.id"), nullable=True)
    
    # TDS Details
    financial_year = Column(String(10), nullable=False)  # e.g., "2024-25"
    quarter = Column(String(5), nullable=False)  # "Q1", "Q2", "Q3", "Q4"
    
    # Transaction Information
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    transaction_amount = Column(Float, nullable=False)
    transaction_type = Column(String(50), nullable=False)
    
    # TDS Calculation
    tds_rate = Column(Float, nullable=False)  # TDS rate as percentage
    tds_amount = Column(Float, nullable=False)  # Calculated TDS amount
    surcharge_amount = Column(Float, default=0.0)
    cess_amount = Column(Float, default=0.0)
    total_tds = Column(Float, nullable=False)  # Total TDS including surcharge and cess
    
    # Deductor Information
    deductor_name = Column(String(200), nullable=False)
    deductor_tan = Column(String(20), nullable=True)  # Tax Account Number
    deductor_pan = Column(String(20), nullable=True)  # Permanent Account Number
    
    # TDS Certificate
    certificate_number = Column(String(50), nullable=True)
    certificate_date = Column(DateTime(timezone=True), nullable=True)
    form_16a_available = Column(Boolean, default=False)
    
    # Payment Details
    challan_number = Column(String(50), nullable=True)
    payment_date = Column(DateTime(timezone=True), nullable=True)
    bank_name = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(20), default="PENDING")  # From TDSStatus enum
    is_claimed = Column(Boolean, default=False)  # Has this been claimed in ITR?
    
    # Compliance
    section_code = Column(String(10), nullable=True)  # e.g., "194S" for crypto
    nature_of_payment = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    tax_record = relationship("TaxRecord")

    def __repr__(self):
        return f"<TDSRecord(id={self.id}, fy={self.financial_year}, amount={self.tds_amount}, status={self.status})>"


class ComplianceLog(Base):
    """
    Compliance log model for tracking compliance-related events and audits.
    """
    __tablename__ = "compliance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system-wide events
    
    # Log Details
    event_type = Column(String(50), nullable=False)  # e.g., "TAX_CALCULATION", "TDS_DEDUCTION", "AUDIT_TRAIL"
    log_level = Column(String(20), nullable=False)  # From ComplianceLogLevel enum
    message = Column(Text, nullable=False)
    
    # Context Information
    module = Column(String(50), nullable=True)  # e.g., "TAX_ENGINE", "TDS_PROCESSOR"
    function_name = Column(String(100), nullable=True)
    
    # Related Records
    related_record_type = Column(String(50), nullable=True)  # e.g., "TaxRecord", "TDSRecord"
    related_record_id = Column(Integer, nullable=True)
    
    # Technical Details
    stack_trace = Column(Text, nullable=True)  # For error logs
    request_id = Column(String(100), nullable=True)  # For request tracking
    session_id = Column(String(100), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)  # Additional context data
    
    # IP and User Agent (for audit trail)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    
    # Compliance Officer Review
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<ComplianceLog(id={self.id}, type={self.event_type}, level={self.log_level}, resolved={self.is_resolved})>"

