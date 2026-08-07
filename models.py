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
from encryption import EncryptedText


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # NULL for Google-only accounts
    google_sub = Column(String(255), unique=True, nullable=True, index=True)
    reset_token_hash = Column(String(64), nullable=True, index=True)  # sha256 of the emailed token
    reset_token_expires_at = Column(DateTime, nullable=True)
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

    # Analytics — see analytics_models.py. Registered by class name only
    # (not imported here) to keep the identity schema decoupled from the
    # analytics schema; both share the same declarative Base so SQLAlchemy
    # resolves these once analytics_models has been imported anywhere
    # (database.init_db() does this at startup).
    acquisition = relationship(
        "UserAcquisition", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    events = relationship("UserEvent", back_populates="user", cascade="all, delete-orphan")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    # Encrypted at rest (AES-256-GCM) — see encryption.py. Transparent to
    # every reader/writer of this attribute; the DB column stores an
    # "enc:v1:<kid>:<nonce>:<ciphertext>" envelope, never plaintext, for any
    # row written after this column type was applied.
    contract_text = Column(EncryptedText, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Analysis results (stored as JSON for flexibility)
    overall_risk = Column(String(20), nullable=True)
    findings_json = Column(JSON, nullable=True)
    llm_result_json = Column(JSON, nullable=True)
    rule_counts_json = Column(JSON, nullable=True)
    rule_engine_version = Column(String(20), nullable=True)
    analysis_completed = Column(Boolean, default=False)

    # Workflow decision layer + structured contract-to-cash terms. Persisted
    # explicitly (not just recomputed from findings_json) so audit history
    # reflects exactly what was shown at analysis time, even if the
    # blocking/policy-block rule classification changes in a later release.
    signature_readiness = Column(String(40), nullable=True)
    payment_terms_json = Column(JSON, nullable=True)
    blocking_findings_json = Column(JSON, nullable=True)
    policy_blocked_findings_json = Column(JSON, nullable=True)

    # Three-score risk dashboard (Legal Risk / Business Risk / Negotiation
    # Difficulty) — see risk_dashboard.py. Additive to overall_risk, not a
    # replacement. The three ints are persisted directly for cheap
    # display/sorting; risk_dashboard_json carries the full breakdown
    # (top contributing findings per score + methodology note).
    legal_risk_score = Column(Integer, nullable=True)
    business_risk_score = Column(Integer, nullable=True)
    negotiation_difficulty_score = Column(Integer, nullable=True)
    risk_dashboard_json = Column(JSON, nullable=True)

    # Defined-terms & cross-reference integrity — see structure_checker.py.
    # Document-hygiene findings (unused/duplicate/undefined terms, broken
    # references to sections/exhibits/schedules), independent of severity.
    structure_report_json = Column(JSON, nullable=True)

    # Deterministic Clause Quality Engine — see clause_quality.py. First
    # module: arbitration completeness (institution/seat/rules/arbitrator
    # count/language/emergency relief/litigation conflict), 0-100 or
    # null/not-applicable when no arbitration clause is present.
    clause_quality_json = Column(JSON, nullable=True)

    # Deterministic party/effective-date/contract-type extraction — see
    # metadata_extractor.py. A field this couldn't confidently extract is
    # null/empty, never a guess.
    metadata_json = Column(JSON, nullable=True)

    # Risk Allocation & Clause Balance Score — see risk_balance.py.
    # Aggregates existing per-finding favorability data; null/not-
    # applicable when the engine found no directionally classifiable
    # findings.
    risk_balance_json = Column(JSON, nullable=True)

    # Playbook comparison
    playbook_id = Column(Integer, ForeignKey("playbooks.id"), nullable=True)
    deviations_json = Column(JSON, nullable=True)

    # Review workflow — one decision per finding (rule_id -> {action, reason,
    # edited_text, decided_at}), recorded as the attorney works through the
    # merged findings+redlines review pass. See review_workflow.py. action is
    # one of: accepted, edited, rejected, flagged, dismissed, commented (a
    # comment can be added alongside any other action). Never recomputed from
    # findings_json — a decision is what the attorney actually did, which
    # must survive even if a later rule-engine version would classify the
    # same clause differently.
    review_decisions_json = Column(JSON, nullable=True)
    review_finalized_at = Column(DateTime, nullable=True)

    # Sharing. share_token identifies the link; the fields below govern
    # whether it currently grants access — see main.py's
    # _evaluate_share_link_access(). None/0 means "no limit" for expiry/max
    # views, matching the pre-hardening behavior for any link created before
    # these columns existed (nullable, so old rows default to unrestricted).
    share_token = Column(String(64), nullable=True, unique=True, index=True)
    share_password_hash = Column(String(255), nullable=True)
    share_expires_at = Column(DateTime, nullable=True)
    share_revoked_at = Column(DateTime, nullable=True)
    share_max_views = Column(Integer, nullable=True)
    share_view_count = Column(Integer, nullable=False, default=0)

    # Batch tracking
    batch_id = Column(String(64), nullable=True, index=True)

    user = relationship("User", back_populates="contracts")
    playbook = relationship("Playbook")
    events = relationship("ContractEvent", back_populates="contract", cascade="all, delete-orphan")

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

    # The standard contract text to compare against. Encrypted at rest
    # (AES-256-GCM) — see encryption.py / Contract.contract_text above.
    template_text = Column(EncryptedText, nullable=False)
    # Pre-computed analysis of the template
    template_findings_json = Column(JSON, nullable=True)
    template_risk = Column(String(20), nullable=True)

    user = relationship("User", back_populates="playbooks")


class AuditLog(Base):
    """Append-only security/activity audit trail (P3: share-link events;
    P7 extends this with login/upload/delete/export/admin/etc. event types).
    Immutable by convention — no route in this codebase ever issues an
    UPDATE or DELETE against this table; every write is an INSERT.

    event_type is a short machine-readable string, e.g.
    "share_link_created", "share_link_revoked", "share_link_accessed".
    target_type/target_id identify what the event happened to (e.g.
    "contract", 42). success/detail capture the outcome for access-attempt
    events (e.g. success=False, detail="expired").
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    target_type = Column(String(64), nullable=True)
    target_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=True)
    detail = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
