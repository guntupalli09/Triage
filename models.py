"""
SQLAlchemy models for Triage Counsel.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, Enum as SAEnum, Table, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base
from encryption import EncryptedJSON, EncryptedText


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

    # Multi-factor authentication (TOTP) — see mfa.py. Opt-in per user, off
    # by default. mfa_secret is encrypted at rest (EncryptedText) since it
    # lets anyone who reads it generate valid codes indefinitely.
    # mfa_secret is set as soon as enrollment starts (before mfa_enabled is
    # true) so the QR code stays stable across a page reload during setup;
    # it isn't a live credential until mfa_enabled flips to True.
    mfa_secret = Column(EncryptedText, nullable=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_enrolled_at = Column(DateTime, nullable=True)
    # [{"hash": sha256hex, "used_at": iso-datetime|None}, ...] — one-way
    # hashes only, never the plaintext codes (see mfa.py).
    mfa_recovery_codes_json = Column(JSON, nullable=True)

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

    # Analysis results. Encrypted (EncryptedJSON — see encryption.py)
    # wherever the payload can embed verbatim contract excerpts;
    # rule_counts_json is just severity counts ({"high": 2, ...}) with no
    # contract-derived text, so it stays a plain JSON column.
    overall_risk = Column(String(20), nullable=True)
    findings_json = Column(EncryptedJSON, nullable=True)
    llm_result_json = Column(EncryptedJSON, nullable=True)
    rule_counts_json = Column(JSON, nullable=True)
    rule_engine_version = Column(String(20), nullable=True)
    analysis_completed = Column(Boolean, default=False)

    # Workflow decision layer + structured contract-to-cash terms. Persisted
    # explicitly (not just recomputed from findings_json) so audit history
    # reflects exactly what was shown at analysis time, even if the
    # blocking/policy-block rule classification changes in a later release.
    signature_readiness = Column(String(40), nullable=True)
    payment_terms_json = Column(EncryptedJSON, nullable=True)
    blocking_findings_json = Column(EncryptedJSON, nullable=True)
    policy_blocked_findings_json = Column(EncryptedJSON, nullable=True)

    # Three-score risk dashboard (Legal Risk / Business Risk / Negotiation
    # Difficulty) — see risk_dashboard.py. Additive to overall_risk, not a
    # replacement. The three ints are persisted directly for cheap
    # display/sorting; risk_dashboard_json carries the full breakdown
    # (top contributing findings per score + methodology note).
    legal_risk_score = Column(Integer, nullable=True)
    business_risk_score = Column(Integer, nullable=True)
    negotiation_difficulty_score = Column(Integer, nullable=True)
    risk_dashboard_json = Column(EncryptedJSON, nullable=True)

    # Defined-terms & cross-reference integrity — see structure_checker.py.
    # Document-hygiene findings (unused/duplicate/undefined terms, broken
    # references to sections/exhibits/schedules), independent of severity.
    structure_report_json = Column(EncryptedJSON, nullable=True)

    # Deterministic Clause Quality Engine — see clause_quality.py. First
    # module: arbitration completeness (institution/seat/rules/arbitrator
    # count/language/emergency relief/litigation conflict), 0-100 or
    # null/not-applicable when no arbitration clause is present.
    clause_quality_json = Column(EncryptedJSON, nullable=True)

    # Deterministic party/effective-date/contract-type extraction — see
    # metadata_extractor.py. A field this couldn't confidently extract is
    # null/empty, never a guess.
    metadata_json = Column(EncryptedJSON, nullable=True)

    # Risk Allocation & Clause Balance Score — see risk_balance.py.
    # Aggregates existing per-finding favorability data; null/not-
    # applicable when the engine found no directionally classifiable
    # findings.
    risk_balance_json = Column(EncryptedJSON, nullable=True)

    # Playbook comparison
    playbook_id = Column(Integer, ForeignKey("playbooks.id"), nullable=True)
    deviations_json = Column(EncryptedJSON, nullable=True)

    # Deterministic policy-rule evaluation (see liability_policy_engine.py).
    # One entry per evaluated clause type ("limitation_of_liability" today);
    # each value is the PolicyDecision dict (state, evidence, negotiation
    # ladder, source playbook/rule). Persisted independently of
    # findings_json/deviations_json because it is not a rule-engine finding
    # or a template diff — it is a policy verdict against a specific
    # PolicyRule, and it must survive even if that PolicyRule is later
    # edited or deleted. Encrypted — embeds verbatim contract excerpts.
    policy_decisions_json = Column(EncryptedJSON, nullable=True)

    # Review workflow — one decision per finding (rule_id -> {action, reason,
    # edited_text, decided_at}), recorded as the attorney works through the
    # merged findings+redlines review pass. See review_workflow.py. action is
    # one of: accepted, edited, rejected, flagged, dismissed, commented (a
    # comment can be added alongside any other action). Never recomputed from
    # findings_json — a decision is what the attorney actually did, which
    # must survive even if a later rule-engine version would classify the
    # same clause differently.
    review_decisions_json = Column(EncryptedJSON, nullable=True)
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
    # Pre-computed analysis of the template. Encrypted — embeds verbatim
    # excerpts of the template text (see encryption.EncryptedJSON).
    template_findings_json = Column(EncryptedJSON, nullable=True)
    template_risk = Column(String(20), nullable=True)

    user = relationship("User", back_populates="playbooks")
    policy_rules = relationship("PolicyRule", back_populates="playbook", cascade="all, delete-orphan")


class PolicyRule(Base):
    """A deterministic policy rule for one clause type on one playbook —
    see liability_policy_engine.py for the evaluator that consumes this.

    Modeled as its own table (rather than columns on Playbook) because a
    playbook is meant to eventually hold one PolicyRule per clause type
    (limitation_of_liability today; indemnification/termination/etc. are
    the natural next additions), each independently created/edited/removed.

    Thresholds are stored as a multiplier of annual contract fees (e.g. 1.0
    = "1x annual fees") since that is how liability caps are conventionally
    negotiated; a fixed-amount cap is normalized to a multiplier at
    evaluation time when the contract's fee value is known, or compared
    directly when it is not (see liability_policy_engine.evaluate).
    """
    __tablename__ = "policy_rules"
    __table_args__ = (UniqueConstraint("playbook_id", "clause_type", name="uq_policy_rule_playbook_clause"),)

    id = Column(Integer, primary_key=True)
    playbook_id = Column(Integer, ForeignKey("playbooks.id"), nullable=False, index=True)
    clause_type = Column(String(64), nullable=False)  # "limitation_of_liability" (only type implemented today)
    contract_side = Column(String(20), nullable=False, default="mutual")  # buy_side, sell_side, mutual
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Position thresholds, as a multiplier of annual fees. preferred is the
    # ideal ask; acceptable_max auto-clears without comment; negotiate_max
    # is the ceiling of what's negotiable before escalation is required.
    preferred_multiplier = Column(Float, nullable=True)
    acceptable_max_multiplier = Column(Float, nullable=True)
    negotiate_max_multiplier = Column(Float, nullable=True)
    prohibit_unlimited = Column(Boolean, nullable=False, default=True)

    # Required carve-outs (e.g. ["fraud", "confidentiality", "ip_infringement"]).
    # A cap that is otherwise acceptable but silent on a required exception
    # is downgraded to NEGOTIATE — see evaluate().
    required_exceptions_json = Column(JSON, nullable=True)

    # Fallback clause text offered when a redline is required. Encrypted —
    # this is drafted contract language, same sensitivity as template_text.
    fallback_text = Column(EncryptedText, nullable=True)

    # Escalation: crossing negotiate_max_multiplier (or hitting a prohibited
    # position) routes to this named approval authority instead of auto-
    # generating a redline the reviewing attorney can accept solo.
    escalation_approval_authority = Column(String(255), nullable=True)

    # Consequential/indirect-damages policy — see liability_policy_engine.py's
    # evaluate_liability_policy(). Previously the engine extracted whether a
    # clause excluded consequential damages but never consumed that fact;
    # these fields make it a real, consumed policy input: when required,
    # a missing exclusion (or one missing a required carve-out) downgrades
    # the decision the same way a missing required exception does.
    require_consequential_damages_exclusion = Column(Boolean, nullable=False, default=False)
    required_consequential_carveouts_json = Column(JSON, nullable=True)

    playbook = relationship("Playbook", back_populates="policy_rules")


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


# --- RBAC (P8) — replaces the single hardcoded-admin-email check. See
# rbac.py for the seeding, permission-check, and grant/revoke logic that
# operates on these tables; manage_roles.py is the operator-facing CLI for
# assigning roles (no admin UI exists for this yet).

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class UserRole(Base):
    """A role assignment: which user has which role, when, and (if known)
    who granted it. A user can hold more than one role."""
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role")
