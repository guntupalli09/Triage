"""
SQLAlchemy models for Triage Counsel.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Subscription
    plan = Column(String(50), default="none")  # none, trial, starter, professional
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="inactive")  # active, inactive, canceled
    subscription_expires_at = Column(DateTime, nullable=True)
    monthly_limit = Column(Integer, default=3)  # free tier: 3 contracts/month
    contracts_this_month = Column(Integer, default=0)
    usage_reset_at = Column(DateTime, default=datetime.utcnow)

    contracts = relationship("Contract", back_populates="user", order_by="desc(Contract.created_at)")
    playbooks = relationship("Playbook", back_populates="user")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    contract_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Analysis results (stored as JSON for flexibility)
    overall_risk = Column(String(20), nullable=True)
    findings_json = Column(JSON, nullable=True)
    llm_result_json = Column(JSON, nullable=True)
    rule_counts_json = Column(JSON, nullable=True)
    rule_engine_version = Column(String(20), nullable=True)
    analysis_completed = Column(Boolean, default=False)

    # Playbook comparison
    playbook_id = Column(Integer, ForeignKey("playbooks.id"), nullable=True)
    deviations_json = Column(JSON, nullable=True)

    # Sharing
    share_token = Column(String(64), nullable=True, unique=True, index=True)
    share_password_hash = Column(String(255), nullable=True)

    # Batch tracking
    batch_id = Column(String(64), nullable=True, index=True)

    user = relationship("User", back_populates="contracts")
    playbook = relationship("Playbook")

    def generate_share_token(self):
        self.share_token = secrets.token_urlsafe(32)
        return self.share_token


class Playbook(Base):
    __tablename__ = "playbooks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    contract_type = Column(String(100), nullable=True)  # NDA, MSA, SaaS, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # The standard contract text to compare against
    template_text = Column(Text, nullable=False)
    # Pre-computed analysis of the template
    template_findings_json = Column(JSON, nullable=True)
    template_risk = Column(String(20), nullable=True)

    user = relationship("User", back_populates="playbooks")
