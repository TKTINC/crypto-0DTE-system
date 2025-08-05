"""
Risk Profile Models for Crypto-0DTE-System

SQLAlchemy models for risk assessment, metrics, and management.
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class RiskLevel(enum.Enum):
    """Risk level enumeration."""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class RiskCategory(enum.Enum):
    """Risk category enumeration."""
    MARKET_RISK = "MARKET_RISK"
    LIQUIDITY_RISK = "LIQUIDITY_RISK"
    CREDIT_RISK = "CREDIT_RISK"
    OPERATIONAL_RISK = "OPERATIONAL_RISK"
    REGULATORY_RISK = "REGULATORY_RISK"
    TECHNOLOGY_RISK = "TECHNOLOGY_RISK"


class RiskProfile(Base):
    """
    Risk profile model for user risk assessment and preferences.
    """
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Overall Risk Assessment
    overall_risk_score = Column(Float, nullable=False, default=0.0)  # 0-100 scale
    risk_level = Column(String(20), nullable=False, default="MODERATE")  # From RiskLevel enum
    risk_capacity = Column(Float, nullable=False, default=0.0)  # Financial capacity to take risk
    
    # Risk Tolerance Questionnaire Results
    age_group = Column(String(20), nullable=True)  # "18-25", "26-35", etc.
    investment_experience = Column(String(20), nullable=True)  # "BEGINNER", "INTERMEDIATE", "ADVANCED"
    financial_goals = Column(JSON, nullable=True)  # Array of goals
    time_horizon = Column(String(20), nullable=True)  # "SHORT", "MEDIUM", "LONG"
    
    # Financial Situation
    annual_income_range = Column(String(30), nullable=True)  # "0-50K", "50K-100K", etc.
    liquid_net_worth = Column(Float, nullable=True)
    percentage_to_invest = Column(Float, nullable=True)  # % of net worth willing to invest
    
    # Risk Preferences
    max_acceptable_loss = Column(Float, nullable=True)  # Maximum loss user can accept (%)
    volatility_tolerance = Column(String(20), nullable=True)  # "LOW", "MEDIUM", "HIGH"
    drawdown_tolerance = Column(Float, nullable=True)  # Maximum drawdown tolerance (%)
    
    # Trading Preferences
    preferred_holding_period = Column(String(20), nullable=True)  # "MINUTES", "HOURS", "DAYS", "WEEKS"
    max_position_size = Column(Float, nullable=True)  # Maximum position size as % of portfolio
    diversification_preference = Column(String(20), nullable=True)  # "CONCENTRATED", "DIVERSIFIED"
    
    # Behavioral Factors
    loss_aversion_score = Column(Float, nullable=True)  # 0-10 scale
    overconfidence_score = Column(Float, nullable=True)  # 0-10 scale
    panic_selling_tendency = Column(Float, nullable=True)  # 0-10 scale
    fomo_susceptibility = Column(Float, nullable=True)  # Fear of missing out score
    
    # Risk Limits
    daily_loss_limit = Column(Float, nullable=True)  # Daily loss limit (%)
    weekly_loss_limit = Column(Float, nullable=True)  # Weekly loss limit (%)
    monthly_loss_limit = Column(Float, nullable=True)  # Monthly loss limit (%)
    
    # Stress Testing
    stress_test_score = Column(Float, nullable=True)  # How user handles market stress
    market_crash_response = Column(String(20), nullable=True)  # "PANIC_SELL", "HOLD", "BUY_MORE"
    
    # Assessment Metadata
    questionnaire_version = Column(String(10), nullable=True)  # Version of risk questionnaire used
    assessment_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    next_review_date = Column(DateTime(timezone=True), nullable=True)
    
    # Validation
    is_validated = Column(Boolean, default=False)  # Has this been validated by advisor?
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Notes
    advisor_notes = Column(Text, nullable=True)
    user_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="risk_profile")
    validator = relationship("User", foreign_keys=[validated_by])
    risk_metrics = relationship("RiskMetrics", back_populates="risk_profile")

    def __repr__(self):
        return f"<RiskProfile(id={self.id}, user_id={self.user_id}, score={self.overall_risk_score}, level={self.risk_level})>"

    def calculate_risk_score(self):
        """Calculate overall risk score based on various factors."""
        score = 0.0
        
        # Age factor (younger = higher risk tolerance)
        age_scores = {
            "18-25": 25, "26-35": 20, "36-45": 15, "46-55": 10, "56-65": 5, "65+": 0
        }
        score += age_scores.get(self.age_group, 10)
        
        # Experience factor
        exp_scores = {
            "BEGINNER": 5, "INTERMEDIATE": 15, "ADVANCED": 25
        }
        score += exp_scores.get(self.investment_experience, 10)
        
        # Time horizon factor
        horizon_scores = {
            "SHORT": 5, "MEDIUM": 15, "LONG": 25
        }
        score += horizon_scores.get(self.time_horizon, 10)
        
        # Financial capacity
        if self.percentage_to_invest:
            if self.percentage_to_invest > 20:
                score += 20
            elif self.percentage_to_invest > 10:
                score += 15
            elif self.percentage_to_invest > 5:
                score += 10
            else:
                score += 5
        
        # Loss tolerance
        if self.max_acceptable_loss:
            if self.max_acceptable_loss > 20:
                score += 20
            elif self.max_acceptable_loss > 10:
                score += 15
            elif self.max_acceptable_loss > 5:
                score += 10
            else:
                score += 5
        
        self.overall_risk_score = min(100, max(0, score))
        
        # Determine risk level
        if self.overall_risk_score >= 80:
            self.risk_level = RiskLevel.VERY_HIGH.value
        elif self.overall_risk_score >= 60:
            self.risk_level = RiskLevel.HIGH.value
        elif self.overall_risk_score >= 40:
            self.risk_level = RiskLevel.MODERATE.value
        elif self.overall_risk_score >= 20:
            self.risk_level = RiskLevel.LOW.value
        else:
            self.risk_level = RiskLevel.VERY_LOW.value


class RiskMetrics(Base):
    """
    Risk metrics model for tracking portfolio and trading risk metrics.
    """
    __tablename__ = "risk_metrics"

    id = Column(Integer, primary_key=True, index=True)
    risk_profile_id = Column(Integer, ForeignKey("risk_profiles.id"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    
    # Time Period
    calculation_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Portfolio Risk Metrics
    portfolio_value = Column(Float, nullable=False)
    portfolio_volatility = Column(Float, nullable=True)  # Annualized volatility
    portfolio_beta = Column(Float, nullable=True)  # Beta vs market
    
    # Value at Risk (VaR)
    var_1_day_95 = Column(Float, nullable=True)  # 1-day VaR at 95% confidence
    var_1_day_99 = Column(Float, nullable=True)  # 1-day VaR at 99% confidence
    var_1_week_95 = Column(Float, nullable=True)  # 1-week VaR at 95% confidence
    
    # Expected Shortfall (Conditional VaR)
    cvar_1_day_95 = Column(Float, nullable=True)  # Expected loss beyond VaR
    cvar_1_day_99 = Column(Float, nullable=True)
    
    # Drawdown Metrics
    max_drawdown = Column(Float, nullable=True)  # Maximum drawdown in period
    current_drawdown = Column(Float, nullable=True)  # Current drawdown
    drawdown_duration = Column(Integer, nullable=True)  # Days in current drawdown
    
    # Concentration Risk
    concentration_ratio = Column(Float, nullable=True)  # Herfindahl index
    largest_position_weight = Column(Float, nullable=True)  # Weight of largest position
    top_5_concentration = Column(Float, nullable=True)  # Weight of top 5 positions
    
    # Liquidity Risk
    liquidity_score = Column(Float, nullable=True)  # 0-100 scale
    illiquid_position_percentage = Column(Float, nullable=True)  # % in illiquid assets
    
    # Correlation Risk
    average_correlation = Column(Float, nullable=True)  # Average correlation between positions
    max_correlation = Column(Float, nullable=True)  # Maximum correlation
    
    # Leverage Metrics
    leverage_ratio = Column(Float, nullable=True)  # Total exposure / equity
    margin_utilization = Column(Float, nullable=True)  # Used margin / available margin
    
    # Performance Risk Metrics
    sharpe_ratio = Column(Float, nullable=True)  # Risk-adjusted return
    sortino_ratio = Column(Float, nullable=True)  # Downside risk-adjusted return
    calmar_ratio = Column(Float, nullable=True)  # Return / max drawdown
    
    # Tail Risk
    skewness = Column(Float, nullable=True)  # Distribution skewness
    kurtosis = Column(Float, nullable=True)  # Distribution kurtosis
    tail_ratio = Column(Float, nullable=True)  # Right tail / left tail
    
    # Risk Limit Utilization
    daily_loss_utilization = Column(Float, nullable=True)  # % of daily limit used
    weekly_loss_utilization = Column(Float, nullable=True)  # % of weekly limit used
    monthly_loss_utilization = Column(Float, nullable=True)  # % of monthly limit used
    
    # Risk Alerts
    risk_alerts = Column(JSON, nullable=True)  # Array of active risk alerts
    risk_score = Column(Float, nullable=True)  # Overall risk score 0-100
    
    # Compliance
    exceeds_risk_limits = Column(Boolean, default=False)
    risk_limit_breaches = Column(JSON, nullable=True)  # Array of limit breaches
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    risk_profile = relationship("RiskProfile", back_populates="risk_metrics")
    portfolio = relationship("Portfolio")

    def __repr__(self):
        return f"<RiskMetrics(id={self.id}, date={self.calculation_date}, var={self.var_1_day_95}, score={self.risk_score})>"

