"""
SQLAlchemy models for Triage AI.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, Index,
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
    plan = Column(String(50), default="none")
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="inactive")
    subscription_expires_at = Column(DateTime, nullable=True)
    monthly_limit = Column(Integer, default=3)
    contracts_this_month = Column(Integer, default=0)
    usage_reset_at = Column(DateTime, default=datetime.utcnow)

    # New fields
    is_admin = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    contracts = relationship("Contract", back_populates="user", order_by="desc(Contract.created_at)")
    playbooks = relationship("Playbook", back_populates="user")

    __table_args__ = (
        Index("ix_users_plan", "plan"),
        Index("ix_users_subscription_status", "subscription_status"),
        Index("ix_users_created_at", "created_at"),
    )


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    contract_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Analysis results
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

    # New fields
    analysis_duration_ms = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    file_type = Column(String(10), nullable=True)

    user = relationship("User", back_populates="contracts")
    playbook = relationship("Playbook")

    __table_args__ = (
        Index("ix_contracts_user_created", "user_id", "created_at"),
        Index("ix_contracts_user_risk", "user_id", "overall_risk"),
    )

    def generate_share_token(self):
        self.share_token = secrets.token_urlsafe(32)
        return self.share_token


class Playbook(Base):
    __tablename__ = "playbooks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    contract_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    template_text = Column(Text, nullable=False)
    template_findings_json = Column(JSON, nullable=True)
    template_risk = Column(String(20), nullable=True)

    user = relationship("User", back_populates="playbooks")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True)
    analysis_id = Column(String(30), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    job_type = Column(String(20), default="single")
    batch_id = Column(String(64), nullable=True, index=True)
    filename = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    playbook_id = Column(Integer, ForeignKey("playbooks.id"), nullable=True)
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    worker_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    enqueued_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")
    contract = relationship("Contract")
    playbook = relationship("Playbook")

    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_created_at", "created_at"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User")

    __table_args__ = (
        Index("ix_audit_user_created", "user_id", "created_at"),
    )


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id = Column(Integer, primary_key=True)
    stripe_event_id = Column(String(255), unique=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    payload_json = Column(JSON, nullable=True)
    processed = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("analysis_jobs.id"), nullable=True)
    model = Column(String(50), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_cents = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    contract = relationship("Contract")
    job = relationship("AnalysisJob")

    __table_args__ = (
        Index("ix_api_usage_user_created", "user_id", "created_at"),
    )
