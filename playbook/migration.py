"""
One-time, idempotent backfill: wraps every pre-existing User in a default
Firm (+Organization/PracticeGroup/Client/Matter placeholders) and wraps
every pre-existing Playbook in a PolicySet/PolicyRule set, so the policy
engine has something to evaluate against with zero UI adoption.

Never modifies models.Playbook or its data — this only reads Playbook rows
and creates new rows elsewhere. Safe to call on every startup: each step is
guarded by a check for already-migrated state (User.default_firm_id,
PolicySet.legacy_playbook_id) before creating anything.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from models import User, Playbook
from playbook.db_models import (
    Firm, FirmMembership, Organization, PracticeGroup, Client, Matter,
    ContractType, PolicySet, PolicyRule, AuditEntry,
)
from playbook.topic_binding import derive_policy_topic

logger = logging.getLogger(__name__)

DEFAULT_CONTRACT_TYPE_SLUG = "general"
DEFAULT_CONTRACT_TYPE_NAME = "General"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or "default"


def ensure_default_firm(db: Session, user: User) -> Firm:
    """Creates (or returns the existing) default Firm + one Organization/
    PracticeGroup/Client/Matter placeholder chain for a single User. Public
    — used both by the bulk startup migration below and lazily by the
    upload flow (main.py) for a User created after the last startup, so
    every user always has a Firm to evaluate against, not just ones that
    existed when init_db() last ran."""
    if user.default_firm_id:
        firm = db.query(Firm).filter(Firm.id == user.default_firm_id).first()
        if firm:
            return firm

    label = user.name or user.company or user.email or f"User {user.id}"
    base_slug = _slugify(f"{label}-firm-{user.id}")
    slug = base_slug
    suffix = 1
    while db.query(Firm).filter(Firm.slug == slug).first():
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    firm = Firm(name=f"{label}'s Firm", slug=slug, is_default_shim=True)
    db.add(firm)
    db.flush()

    db.add(FirmMembership(firm_id=firm.id, user_id=user.id, role="admin"))

    org = Organization(firm_id=firm.id, name="Default")
    db.add(org)
    db.flush()

    practice_group = PracticeGroup(organization_id=org.id, name="Default")
    db.add(practice_group)
    db.flush()

    client = Client(practice_group_id=practice_group.id, name="Unassigned")
    db.add(client)
    db.flush()

    matter = Matter(client_id=client.id, name="Unassigned")
    db.add(matter)
    db.flush()

    user.default_firm_id = firm.id
    db.flush()

    logger.info("Migration: created default Firm %s for User %s", firm.id, user.id)
    return firm


def _default_matter(db: Session, firm: Firm) -> Matter:
    org = db.query(Organization).filter(Organization.firm_id == firm.id).first()
    practice_group = db.query(PracticeGroup).filter(PracticeGroup.organization_id == org.id).first()
    client = db.query(Client).filter(Client.practice_group_id == practice_group.id).first()
    return db.query(Matter).filter(Matter.client_id == client.id).first()


def _ensure_contract_type(db: Session, firm: Firm, name: str) -> ContractType:
    name = (name or DEFAULT_CONTRACT_TYPE_NAME).strip() or DEFAULT_CONTRACT_TYPE_NAME
    slug = _slugify(name)
    ct = db.query(ContractType).filter(ContractType.firm_id == firm.id, ContractType.slug == slug).first()
    if ct:
        return ct
    ct = ContractType(firm_id=firm.id, name=name, slug=slug)
    db.add(ct)
    db.flush()
    return ct


def _migrate_playbook(db: Session, playbook: Playbook, firm: Firm, matter: Matter) -> None:
    already = (
        db.query(PolicySet)
        .filter(PolicySet.legacy_playbook_id == playbook.id)
        .first()
    )
    if already:
        return

    contract_type = _ensure_contract_type(db, firm, playbook.contract_type)

    policy_set = PolicySet(
        firm_id=firm.id,
        matter_id=matter.id,
        contract_type_id=contract_type.id,
        name=playbook.name,
        description=playbook.description,
        version_major=1,
        version_minor=0,
        status="published",
        author_user_id=playbook.user_id,
        approval_date=datetime.utcnow(),
        effective_date=datetime.utcnow(),
        legacy_playbook_id=playbook.id,
    )
    db.add(policy_set)
    db.flush()

    for entry in (playbook.template_findings_json or []):
        rule_id = entry.get("rule_id")
        if not rule_id:
            continue
        db.add(PolicyRule(
            policy_set_id=policy_set.id,
            policy_topic=derive_policy_topic(rule_id),
            bound_rule_ids_json=[rule_id],
            title=entry.get("title") or rule_id,
            status="acceptable",
            severity=entry.get("severity"),
            business_reason=(
                "Present in the firm's pre-existing standard template "
                f"'{playbook.name}' — carried over as a tolerated baseline "
                "during migration to the policy engine."
            ),
        ))

    db.add(AuditEntry(
        firm_id=firm.id,
        entity_type="policy_set",
        entity_id=policy_set.id,
        action="import",
        reason="Automated migration from legacy Playbook",
        detail_json={"source": "playbook_migration", "legacy_playbook_id": playbook.id},
    ))

    logger.info("Migration: wrapped Playbook %s as PolicySet %s", playbook.id, policy_set.id)


def run_legacy_playbook_migration(db: Session) -> None:
    """Entry point called once from database.py:init_db(). Idempotent —
    processes only Users without a default_firm_id and Playbooks without a
    corresponding PolicySet yet, one User/Playbook transaction at a time so
    a failure partway through is retriable on the next startup."""
    users = db.query(User).all()
    for user in users:
        try:
            firm = ensure_default_firm(db, user)
            matter = _default_matter(db, firm)
            playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).all()
            for playbook in playbooks:
                _migrate_playbook(db, playbook, firm, matter)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Legacy playbook migration failed for User %s", user.id)
