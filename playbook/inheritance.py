"""
Inheritance Resolver — merges PolicySets across the Firm -> Organization ->
PracticeGroup -> Client -> Matter chain into one effective, flat policy map.

Resolution algorithm:
  1. Walk the ancestor chain for the given matter_id (Matter -> Client ->
     PracticeGroup -> Organization -> Firm). If no matter_id is given, the
     chain is just [Firm] (falls back to Firm-level defaults only).
  2. At each level, from MOST specific to LEAST (Matter, Client,
     PracticeGroup, Organization, Firm), collect the latest published,
     non-deprecated PolicySet scoped to that node where contract_type_id is
     either None (level-wide) or equals the requested contract_type_id —
     preferring the contract-type-specific set over the level-wide one at
     the same level.
  3. Layer the collected sets from LEAST specific to MOST specific into one
     effective map, keyed by (policy_topic, contract_type). A lower level's
     PolicyRule overwrites a higher level's only when they share this exact
     key — a Matter-level INDEM rule overrides a Client-level INDEM rule for
     that matter, but does not touch a Client-level LOL rule.

This is deterministic and total even when only Firm-level defaults exist —
a Firm with no Organization/PracticeGroup/Client/Matter-level PolicySets at
all still resolves correctly (a single-layer merge with no ancestors).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from playbook.db_models import (
    Firm, Organization, PracticeGroup, Client, Matter, PolicySet, PolicyRule,
)

# Ordered most-specific -> least-specific; also defines the FK column name
# on PolicySet for each level.
_LEVELS = ("matter", "client", "practice_group", "organization", "firm")


@dataclass
class ResolutionTrailEntry:
    level: str
    policy_set_id: int
    version: str


@dataclass
class EffectivePolicySet:
    topics: Dict[str, PolicyRule] = field(default_factory=dict)
    resolution_trail: List[ResolutionTrailEntry] = field(default_factory=list)

    def get(self, topic: str) -> Optional[PolicyRule]:
        return self.topics.get(topic)

    def values(self):
        return self.topics.values()

    @property
    def policy_set_ids(self) -> List[int]:
        return [e.policy_set_id for e in self.resolution_trail]


def _ancestor_ids(db: Session, matter_id: Optional[int]) -> Dict[str, Optional[int]]:
    """Returns {"matter": id|None, "client": id|None, "practice_group": id|None,
    "organization": id|None} for the given matter_id's ancestor chain."""
    ids = {"matter": None, "client": None, "practice_group": None, "organization": None}
    if not matter_id:
        return ids
    matter = db.query(Matter).filter(Matter.id == matter_id).first()
    if not matter:
        return ids
    ids["matter"] = matter.id
    client = db.query(Client).filter(Client.id == matter.client_id).first()
    if not client:
        return ids
    ids["client"] = client.id
    practice_group = db.query(PracticeGroup).filter(PracticeGroup.id == client.practice_group_id).first()
    if not practice_group:
        return ids
    ids["practice_group"] = practice_group.id
    org = db.query(Organization).filter(Organization.id == practice_group.organization_id).first()
    if org:
        ids["organization"] = org.id
    return ids


def _scope_column(level: str) -> str:
    return "organization_id" if level == "organization" else f"{level}_id"


def _best_policy_set_for_level(
    db: Session, firm_id: int, level: str, level_id: Optional[int], contract_type_id: Optional[int],
) -> Optional[PolicySet]:
    if level != "firm" and level_id is None:
        return None

    q = db.query(PolicySet).filter(
        PolicySet.firm_id == firm_id, PolicySet.status == "published", PolicySet.deprecated.is_(False),
    )
    if level == "firm":
        q = q.filter(
            PolicySet.organization_id.is_(None), PolicySet.practice_group_id.is_(None),
            PolicySet.client_id.is_(None), PolicySet.matter_id.is_(None),
        )
    else:
        col = getattr(PolicySet, _scope_column(level))
        q = q.filter(col == level_id)

    candidates = q.all()
    if not candidates:
        return None

    if contract_type_id is not None:
        specific = [c for c in candidates if c.contract_type_id == contract_type_id]
        if specific:
            candidates = specific
        else:
            candidates = [c for c in candidates if c.contract_type_id is None]
    else:
        candidates = [c for c in candidates if c.contract_type_id is None]

    if not candidates:
        return None

    return max(candidates, key=lambda c: (c.version_major, c.version_minor, c.updated_at))


class InheritanceResolver:
    @staticmethod
    def resolve(
        db: Session, firm_id: int, matter_id: Optional[int] = None, contract_type_id: Optional[int] = None,
    ) -> EffectivePolicySet:
        ancestors = _ancestor_ids(db, matter_id)
        level_ids = {**ancestors, "firm": firm_id}

        # Collect most-specific -> least-specific, then layer in reverse
        # order so least-specific applies first and gets overwritten by
        # anything more specific sharing the same (topic, contract_type) key.
        collected: List[PolicySet] = []
        for level in _LEVELS:
            ps = _best_policy_set_for_level(db, firm_id, level, level_ids.get(level), contract_type_id)
            if ps is not None:
                collected.append((level, ps))

        effective = EffectivePolicySet()
        for level, ps in reversed(collected):
            for rule in ps.rules:
                effective.topics[rule.policy_topic] = rule
            effective.resolution_trail.append(
                ResolutionTrailEntry(level=level, policy_set_id=ps.id, version=f"{ps.version_major}.{ps.version_minor}")
            )

        return effective
