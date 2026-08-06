"""
Data model for the policy enforcement engine.

Hierarchy (structural parent -> child nesting, complete tenant isolation
at the Firm boundary): Firm -> Organization -> PracticeGroup -> Client -> Matter.
ContractType is NOT a nesting level — it is a firm-scoped classification tag
that a PolicySet can optionally combine with a hierarchy node (see
PolicySet's scope columns and playbook/inheritance.py for the resolution
algorithm this enables).

Every table that isn't reachable from `firm_id` in one hop is reachable via
its parent chain — repository.py enforces that every read/write is scoped
through that chain, never by bare primary key.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, JSON, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from database import Base


# ---------------------------------------------------------------------------
# Tenancy hierarchy
# ---------------------------------------------------------------------------

class Firm(Base):
    __tablename__ = "firms"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # True only for Firms auto-created by the legacy Playbook migration for
    # a pre-existing User — lets admin tooling distinguish a real firm from
    # a migration placeholder without guessing from name/slug.
    is_default_shim = Column(Boolean, default=False)

    memberships = relationship("FirmMembership", back_populates="firm", cascade="all, delete-orphan")
    organizations = relationship("Organization", back_populates="firm", cascade="all, delete-orphan")
    contract_types = relationship("ContractType", back_populates="firm", cascade="all, delete-orphan")


class FirmMembership(Base):
    """Many-to-many User<->Firm. The legacy migration creates exactly one
    row per existing User (role='admin'), but the schema supports multiple
    attorneys per Firm from day one — no future migration needed for that."""
    __tablename__ = "firm_memberships"

    id = Column(Integer, primary_key=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(30), default="attorney")  # attorney, admin, reviewer
    created_at = Column(DateTime, default=datetime.utcnow)

    firm = relationship("Firm", back_populates="memberships")

    __table_args__ = (UniqueConstraint("firm_id", "user_id", name="uq_firm_user"),)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    firm = relationship("Firm", back_populates="organizations")
    practice_groups = relationship("PracticeGroup", back_populates="organization", cascade="all, delete-orphan")


class PracticeGroup(Base):
    __tablename__ = "practice_groups"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Commercial Practice"
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="practice_groups")
    clients = relationship("Client", back_populates="practice_group", cascade="all, delete-orphan")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    practice_group_id = Column(Integer, ForeignKey("practice_groups.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Client XYZ"
    created_at = Column(DateTime, default=datetime.utcnow)

    practice_group = relationship("PracticeGroup", back_populates="clients")
    matters = relationship("Matter", back_populates="client", cascade="all, delete-orphan")


class Matter(Base):
    __tablename__ = "matters"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Matter 103"
    matter_number = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="matters")


class ContractType(Base):
    """Firm-scoped classification tag ("Vendor Agreements", "NDA", "MSA"),
    not a hierarchy nesting level. A PolicySet can scope to one of these
    independent of, or in combination with, a hierarchy node."""
    __tablename__ = "contract_types"

    id = Column(Integer, primary_key=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # "Vendor Agreements", "NDA", "MSA"...
    slug = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    firm = relationship("Firm", back_populates="contract_types")

    __table_args__ = (UniqueConstraint("firm_id", "slug", name="uq_firm_contract_type"),)


# ---------------------------------------------------------------------------
# Policy set / rule / version
# ---------------------------------------------------------------------------

class PolicySet(Base):
    """The firm's authored legal positions for a scope — successor concept
    to Playbook, but scoped to a hierarchy node (+ optional ContractType)
    instead of directly to a User, and independently versioned/approved."""
    __tablename__ = "policy_sets"

    id = Column(Integer, primary_key=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)

    # Exactly one of these is set to anchor this PolicySet at one hierarchy
    # level (all null = Firm-wide default). contract_type_id is independent
    # of the hierarchy scope — see playbook/inheritance.py for how the two
    # combine during resolution.
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    practice_group_id = Column(Integer, ForeignKey("practice_groups.id"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id"), nullable=True, index=True)
    contract_type_id = Column(Integer, ForeignKey("contract_types.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Versioning
    version_major = Column(Integer, nullable=False, default=1)
    version_minor = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="draft")  # draft, published, deprecated
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)
    previous_version_id = Column(Integer, ForeignKey("policy_sets.id"), nullable=True)
    deprecated = Column(Boolean, default=False)

    # Legacy bridge — set only for PolicySets created by the Playbook
    # migration (playbook/migration.py). NULL for anything authored
    # natively in this system.
    legacy_playbook_id = Column(Integer, ForeignKey("playbooks.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rules = relationship("PolicyRule", back_populates="policy_set", cascade="all, delete-orphan")
    change_logs = relationship(
        "PolicyChangeLog", back_populates="policy_set", cascade="all, delete-orphan",
        order_by="PolicyChangeLog.created_at",
    )

    __table_args__ = (
        Index(
            "ix_policy_sets_scope", "firm_id", "organization_id", "practice_group_id",
            "client_id", "matter_id", "contract_type_id",
        ),
    )


class PolicyRule(Base):
    """One firm legal position for one policy topic. Independently authored
    — it does not require an uploaded template document to exist."""
    __tablename__ = "policy_rules"

    id = Column(Integer, primary_key=True)
    policy_set_id = Column(Integer, ForeignKey("policy_sets.id"), nullable=False, index=True)

    # --- Binding to the deterministic rule engine (rules_engine.py) ---
    # The topic token shared with a Finding.rule_id's middle segment (see
    # playbook/topic_binding.py::derive_policy_topic), e.g. "INDEM", "LOL".
    # A firm-authored topic with no current engine counterpart is allowed;
    # such a rule simply never matches a Finding and always evaluates
    # NOT_APPLICABLE until the engine gains a rule for that topic.
    policy_topic = Column(String(100), nullable=False, index=True)
    # Optional explicit list of exact rule_ids this PolicyRule binds to,
    # for when policy_topic alone is too coarse. Explicit binding always
    # wins over topic binding. Null/empty = bind to the whole topic.
    bound_rule_ids_json = Column(JSON, nullable=True)

    title = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # acceptable | negotiate | prohibited
    preferred_position = Column(Text, nullable=True)
    fallback_position = Column(Text, nullable=True)
    approved_redline = Column(Text, nullable=True)
    minimum_requirement = Column(Text, nullable=True)
    maximum_requirement = Column(Text, nullable=True)
    business_reason = Column(Text, nullable=True)
    legal_reason = Column(Text, nullable=True)
    risk_score = Column(Integer, nullable=True)  # 0-100, firm-authored
    severity = Column(String(20), nullable=True)  # firm's own severity view; independent of the engine's
    approval_required = Column(Boolean, default=False)
    escalation_owner = Column(String(255), nullable=True)  # name/role/email, free text
    effective_date = Column(DateTime, nullable=True)
    jurisdiction = Column(String(100), nullable=True)
    applies_to_contract_types_json = Column(JSON, nullable=True)  # list[str] of ContractType slugs
    exceptions_json = Column(JSON, nullable=True)  # list of {condition, note}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy_set = relationship("PolicySet", back_populates="rules")

    __table_args__ = (Index("ix_policy_rules_topic", "policy_set_id", "policy_topic"),)


class PolicyChangeLog(Base):
    __tablename__ = "policy_change_logs"

    id = Column(Integer, primary_key=True)
    policy_set_id = Column(Integer, ForeignKey("policy_sets.id"), nullable=False, index=True)
    from_version = Column(String(20), nullable=True)   # "1.0"
    to_version = Column(String(20), nullable=False)    # "1.1"
    summary = Column(Text, nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    policy_set = relationship("PolicySet", back_populates="change_logs")


# ---------------------------------------------------------------------------
# Decision / evaluation / override / audit
# ---------------------------------------------------------------------------

class PolicyEvaluation(Base):
    """One row per contract-evaluation run — the header for the set of
    per-finding PolicyDecision rows it produced."""
    __tablename__ = "policy_evaluations"

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    matter_id = Column(Integer, ForeignKey("matters.id"), nullable=True, index=True)
    contract_type_id = Column(Integer, ForeignKey("contract_types.id"), nullable=True, index=True)
    rule_engine_version = Column(String(20), nullable=False)
    # Ordered list of PolicySet ids actually merged for this run (one per
    # hierarchy level that had a matching set) — the resolution trail, for
    # audit ("why did this decision come out this way").
    resolved_policy_set_ids_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    decisions = relationship(
        "PolicyDecision", back_populates="evaluation", cascade="all, delete-orphan",
        order_by="PolicyDecision.id",
    )


class PolicyDecision(Base):
    """One deterministic policy verdict for one Finding occurrence."""
    __tablename__ = "policy_decisions"

    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("policy_evaluations.id"), nullable=False, index=True)
    finding_key = Column(String(64), nullable=False)  # "{rule_id}#{index}" — review_workflow.py's convention
    rule_id = Column(String(80), nullable=False, index=True)
    policy_rule_id = Column(Integer, ForeignKey("policy_rules.id"), nullable=True, index=True)
    # NULL when no PolicyRule bound to this Finding's topic — the decision
    # is still recorded (as NOT_APPLICABLE with a reason), never dropped.

    policy_status = Column(String(20), nullable=False)
    # COMPLIANT | PARTIALLY_COMPLIANT | NEGOTIABLE | PROHIBITED | ESCALATE | NOT_APPLICABLE
    reason = Column(Text, nullable=False)
    preferred_position = Column(Text, nullable=True)
    fallback_position = Column(Text, nullable=True)
    escalation_required = Column(Boolean, default=False)
    escalation_owner = Column(String(255), nullable=True)
    matched_policy_set_id = Column(Integer, ForeignKey("policy_sets.id"), nullable=True)
    matched_policy_rule_version = Column(String(20), nullable=True)  # "1.0" snapshot at decision time
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluation = relationship("PolicyEvaluation", back_populates="decisions")

    __table_args__ = (Index("ix_policy_decisions_eval_key", "evaluation_id", "finding_key"),)


class PolicyOverride(Base):
    """Append-only. NEVER mutates PolicyRule/PolicySet — references the
    PolicyDecision being overridden. No update route is ever exposed for
    this table at the service layer; it is insert-only by construction."""
    __tablename__ = "policy_overrides"

    id = Column(Integer, primary_key=True)
    policy_decision_id = Column(Integer, ForeignKey("policy_decisions.id"), nullable=False, index=True)
    attorney_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    matter_id = Column(Integer, ForeignKey("matters.id"), nullable=True)
    reason = Column(Text, nullable=False)
    overridden_status = Column(String(20), nullable=False)  # the attorney's replacement status
    approval_required = Column(Boolean, default=False)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditEntry(Base):
    """Firm-wide append-only audit log — superset of PolicyOverride, also
    covers publish/rollback/import/export/clone/archive admin actions."""
    __tablename__ = "audit_entries"

    id = Column(Integer, primary_key=True)
    firm_id = Column(Integer, ForeignKey("firms.id"), nullable=False, index=True)
    entity_type = Column(String(40), nullable=False)  # policy_set, policy_decision, override, ...
    entity_id = Column(Integer, nullable=False)
    action = Column(String(40), nullable=False)  # publish, rollback, override, decide, import, export, clone, archive
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    playbook_version = Column(String(20), nullable=True)
    rule_engine_version = Column(String(20), nullable=True)
    reason = Column(Text, nullable=True)
    attorney_comments = Column(Text, nullable=True)
    detail_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_audit_entries_entity", "entity_type", "entity_id"),)
