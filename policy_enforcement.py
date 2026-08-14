"""
Phase 4: Production Enforcement Cutover.

This module is the ONLY place production contract review decides which
policy source is authoritative (legacy PolicyRule vs ACTIVE
PolicyPosition) and the ONLY place that turns an ACTIVE PolicyPosition
into a production PolicyDecision. It introduces no second evaluation
implementation: every clause type is evaluated by calling the exact same
extract_*_facts / evaluate_*_policy pair the six engines have always had,
looked up via playbook_authoring._ENGINE_FUNCS, against a policy object
built by playbook_authoring.build_policy_rule_for_enforcement (which
itself refuses anything but a re-validated ACTIVE position). See
docs/architecture/phase4_cutover.md for the full design, including the
shadow-period / cutover-condition / rollback-switch / cleanup-condition
definitions this module implements.

Mode (env var POLICY_ENFORCEMENT_MODE, read fresh on every call — never
cached, so an operator can flip it without a redeploy):

  "legacy"  - Production reads ONLY the legacy PolicyRule (limitation_of_
              liability only). Exactly pre-Phase-4 behavior. This is the
              rollback switch.
  "shadow"  - DEFAULT. Production's user-visible result still comes from
              the legacy PolicyRule path (apply_liability_policy), same
              as "legacy". In addition, when a migrated ACTIVE
              limitation_of_liability PolicyPosition exists for the same
              playbook, this module ALSO evaluates it purely for
              comparison and records divergence metadata to AuditLog —
              never the user-visible result, never duplicated contract
              text.
  "cutover" - Production reads ACTIVE PolicyPositions for all six clause
              types via build_policy_rule_for_enforcement. PolicyRule is
              no longer consulted for the user-visible result. Requires
              verify_migration_coverage_or_fail_closed to have passed at
              startup (see main.py's startup handler) — cutover mode does
              not silently drop enforcement for an unmigrated policy.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

import liability_policy_engine
import playbook_authoring as pa
from models import AuditLog, Contract, Playbook, PolicyPosition, PolicyRule

DEFAULT_MODE = "shadow"


# ---------------------------------------------------------------------------
# Legacy path (pre-Phase-4 behavior, unchanged) — lives here rather than in
# main.py so this module is the single place that decides what production
# policy enforcement does, in every mode. main.py imports this function by
# name; nothing about its behavior changed when it moved.
# ---------------------------------------------------------------------------

_LEGACY_POLICY_STATE_SEVERITY = {
    liability_policy_engine.PROHIBITED: "critical",
    liability_policy_engine.ESCALATE: "high",
    liability_policy_engine.MUST_REDLINE: "high",
    liability_policy_engine.REQUIRES_REVIEW: "high",
    liability_policy_engine.NEGOTIATE: "medium",
    liability_policy_engine.ACCEPT_WITH_NOTE: "low",
    liability_policy_engine.ACCEPT: "low",
}


def apply_liability_policy(db: DBSession, playbook: Optional[Playbook], contract_text: str, findings_dict: List[Dict]) -> Optional[Dict]:
    """If `playbook` has a limitation-of-liability PolicyRule, evaluates the
    contract's liability cap deterministically against it and, when the
    result requires attorney attention (anything but ACCEPT/ACCEPT_WITH_NOTE/
    NOT_APPLICABLE), appends a synthetic finding to `findings_dict` (mutated
    in place) so it flows through the existing review/accept/redline/audit
    pipeline exactly like a rule-engine finding — same Track Changes export,
    same accept/edit/reject decision recording. Returns the policy decision
    dict (always, even when ACCEPT/NOT_APPLICABLE) for Contract.policy_decisions_json,
    or None if no policy rule is configured on this playbook."""
    if not playbook:
        return None
    policy = db.query(PolicyRule).filter(
        PolicyRule.playbook_id == playbook.id, PolicyRule.clause_type == "limitation_of_liability",
    ).first()
    if not policy:
        return None

    facts = liability_policy_engine.extract_liability_facts(contract_text)
    decision = liability_policy_engine.evaluate_liability_policy(
        facts, policy, source=f"{playbook.name} v{policy.version}",
    )

    actionable_states = {
        liability_policy_engine.NEGOTIATE, liability_policy_engine.MUST_REDLINE,
        liability_policy_engine.PROHIBITED, liability_policy_engine.ESCALATE,
        liability_policy_engine.REQUIRES_REVIEW,
    }
    if decision.state in actionable_states and decision.start_index is not None:
        findings_dict.append({
            "rule_id": decision.rule_id, "rule_name": "Limitation of Liability Policy",
            "title": f"Limitation of Liability — {decision.state.replace('_', ' ')}",
            "severity": _LEGACY_POLICY_STATE_SEVERITY.get(decision.state, "medium"),
            "rationale": decision.explanation,
            "matched_excerpt": decision.contract_language, "position": None, "context": None,
            "clause_number": None, "matched_keywords": [], "aliases": [],
            "start_index": decision.start_index, "end_index": decision.end_index,
            "exact_snippet": decision.contract_language, "evidence": None,
            "party_direction": None, "finding_type": "policy_decision",
            "finding_type_label": "Policy Decision", "confidence_breakdown": None,
            "redline": {
                "issue": decision.required_action, "legal_rationale": decision.explanation,
                "suggested_redline": decision.fallback_text or "",
            } if decision.fallback_text else None,
            "policy_state": decision.state,
            # clause_type identifies which deterministic engine produced
            # this finding — needed by verify_policy_finding (Phase 4.1)
            # to know which extract_fn/evaluate_fn pair to replay.
            "clause_type": "limitation_of_liability",
            # escalate_to (UX audit P0-3): the engine already computes who
            # must approve an ESCALATE state (policy_engine_core.
            # escalate_to_for_state) — this is the one place it was being
            # silently dropped before reaching the UI.
            "escalate_to": decision.escalate_to,
            "negotiation_ladder": [
                {"label": s["label"], "description": s["description"], "status": s["status"]}
                for s in decision.as_dict()["negotiation_ladder"]
            ],
            "policy_source": decision.source,
            "controlling_provision": decision.controlling_provision,
            "our_position": decision.our_position,
            "counterparty_position": decision.counterparty_position,
            "evidence_report": decision.render_evidence_report(),
        })
    return {"limitation_of_liability": decision.as_dict()}


def get_enforcement_mode() -> str:
    """Read fresh from the environment on every call — deliberately not
    cached at import time or in a settings singleton, so an operator
    flipping POLICY_ENFORCEMENT_MODE (the rollback switch) takes effect
    immediately without a redeploy.

    This is the ONE authoritative reader of POLICY_ENFORCEMENT_MODE in the
    codebase. Nothing else may call os.getenv on it — every UI surface,
    readiness report and test goes through this function or
    is_policy_authoritative() below."""
    mode = os.getenv("POLICY_ENFORCEMENT_MODE", DEFAULT_MODE).strip().lower()
    if mode not in ("legacy", "shadow", "cutover"):
        return DEFAULT_MODE
    return mode


def is_policy_authoritative() -> bool:
    """Whether an ACTIVE PolicyPosition actually governs the user-visible
    result of a production contract review right now.

    "Policy lifecycle = ACTIVE" and "policy is authoritative in production"
    are two different facts, and conflating them is UX walkthrough P0-2: in
    shadow (the shipped default) and legacy modes an ACTIVE, 100%-coverage
    Playbook has NO effect on the user-visible review — it is evaluated for
    comparison only. Any UI that implies "this Playbook is governing this
    review" must gate on this function, never on position.status."""
    return get_enforcement_mode() == "cutover"


# Plain-English, lawyer-facing wording for each mode. Raw env-var
# terminology ("shadow", "cutover", "POLICY_ENFORCEMENT_MODE") is
# deliberately absent — it is meaningless to the person reading a review
# and belongs only on operator surfaces (policy_readiness / the Phase 4.1
# readiness CLI), which report the technical mode string directly.
ENFORCEMENT_DISCLOSURE = {
    "cutover": {
        "label": "Governing contract reviews",
        "detail": "Your approved policy positions decide the outcome of contract reviews.",
        "authoritative": True,
    },
    "shadow": {
        "label": "Checking only — not yet deciding reviews",
        "detail": (
            "Your approved positions are being checked against every review for accuracy, but "
            "they are not deciding outcomes yet. Ask your administrator to turn on policy "
            "enforcement once you're satisfied with the results."
        ),
        "authoritative": False,
    },
    "legacy": {
        "label": "Checking only — not yet deciding reviews",
        "detail": (
            "Policy enforcement from this Workbench is turned off for this deployment, so these "
            "positions are not deciding contract review outcomes. Ask your administrator to turn "
            "it on."
        ),
        "authoritative": False,
    },
}


def enforcement_disclosure() -> Dict[str, Any]:
    """The lawyer-facing description of the current enforcement state, for
    templates. Keyed off the single canonical mode reader."""
    return dict(ENFORCEMENT_DISCLOSURE[get_enforcement_mode()])


# ---------------------------------------------------------------------------
# Operator visibility: how long has this deployment been in its current mode?
#
# A production deployment sitting in shadow indefinitely with nobody
# noticing is exactly the failure P0-2 describes. Nothing here flips the
# mode — Phase 4.1 requires human-authorized cutover backed by production
# shadow evidence — it only makes the current state, and its age, visible
# on the operator surface that already exists (policy_readiness /
# scripts/phase4_readiness_check.py).
# ---------------------------------------------------------------------------

ENFORCEMENT_MODE_EVENT_TYPE = "policy_enforcement_mode_observed"


def last_recorded_mode(db: DBSession) -> Optional[AuditLog]:
    return (
        db.query(AuditLog)
        .filter(AuditLog.event_type == ENFORCEMENT_MODE_EVENT_TYPE)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .first()
    )


def record_enforcement_mode_observation(db: DBSession) -> Optional[AuditLog]:
    """Records the current enforcement mode to AuditLog, but ONLY when it
    differs from the last recorded one — so the log holds one row per mode
    change, and its timestamp answers "how long have we been in this mode".
    Idempotent by construction: calling it on every review costs one
    indexed read and no write in the steady state. Adds to the session;
    the caller commits."""
    mode = get_enforcement_mode()
    last = last_recorded_mode(db)
    if last is not None and (last.metadata_json or {}).get("mode") == mode:
        return None
    row = AuditLog(
        event_type=ENFORCEMENT_MODE_EVENT_TYPE, actor_user_id=None,
        target_type="deployment", target_id=None, success=True, detail=mode,
        metadata_json={"mode": mode, "authoritative": is_policy_authoritative()},
    )
    db.add(row)
    return row


# ---------------------------------------------------------------------------
# Snapshot — concurrency/race safety (requirement 6)
# ---------------------------------------------------------------------------

def snapshot_active_positions(db: DBSession, playbook_id: int) -> Dict[str, PolicyPosition]:
    """Queries the ACTIVE PolicyPosition set for a playbook exactly ONCE.
    Callers must take this snapshot at the START of a contract review and
    reuse the same dict for every clause type evaluated during that
    review — never re-query per clause. This is what guarantees a single
    contract is never partially evaluated under one policy revision and
    partially under another if a lawyer activates a new revision (which
    archives the old ACTIVE row) while the review is in flight: the
    archived row's PolicyPosition object, once loaded into this dict, is
    unaffected by a later UPDATE to a *different* row (the new revision
    is a new row, per PolicyPosition's revision-not-mutation model — see
    models.py). DRAFT/NEEDS_REVIEW/APPROVED/ARCHIVED rows are excluded by
    the status filter itself; they can never leak into production output
    by construction, not by convention."""
    rows = (
        db.query(PolicyPosition)
        .filter(PolicyPosition.playbook_id == playbook_id, PolicyPosition.status == "ACTIVE")
        .all()
    )
    return {row.clause_type: row for row in rows}


def config_hash_for_position(position: PolicyPosition) -> str:
    """Deterministic hash identifying this exact revision's enforcement-
    relevant content (config_json + the three shared columns). Two
    different PolicyPosition rows with byte-identical enforcement content
    hash identically; any content change changes the hash. Used for
    revision pinning (requirement 5) and shadow-mode divergence logging,
    never for anything requiring cryptographic collision resistance
    beyond "change detection," so sha256 of a canonical JSON dump is
    sufficient."""
    payload = json.dumps(
        {
            "clause_type": position.clause_type,
            "contract_side": position.contract_side,
            "escalation_approval_authority": position.escalation_approval_authority,
            "fallback_text": position.fallback_text,
            "config_json": position.config_json or {},
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _revision_metadata_for(position: PolicyPosition) -> Dict[str, Any]:
    return {
        "policy_position_id": position.id,
        "clause_type": position.clause_type,
        "revision_activated_at": position.activated_at.isoformat() if position.activated_at else None,
        "config_hash": config_hash_for_position(position),
        "source_type": position.source_type,
    }


# ---------------------------------------------------------------------------
# Multi-clause evaluation — cutover path (requirements 3, 4, 11)
# ---------------------------------------------------------------------------

@dataclass
class ClauseEvaluationOutcome:
    clause_type: str
    decision: Optional[Any]  # PolicyDecision, or None on error
    revision_metadata: Dict[str, Any]
    error: Optional[str] = None


def evaluate_active_policies(
    db: DBSession,
    playbook: Playbook,
    contract_text: str,
    *,
    active_positions: Optional[Dict[str, PolicyPosition]] = None,
) -> List[ClauseEvaluationOutcome]:
    """Evaluates every clause type that currently has an ACTIVE
    PolicyPosition against contract_text, in pa.CLAUSE_TYPES' fixed order
    (requirement 10 — deterministic serialization order). Absence of an
    ACTIVE position for a clause type means that clause type is simply
    skipped — never evaluated against a stale/draft/no policy, and never
    treated as permissive acceptance (requirement 4).

    `active_positions`, if given, MUST be a snapshot already taken via
    snapshot_active_positions — this function never re-queries per clause,
    so passing the same dict for the whole review is what gives the
    concurrency guarantee described there. If omitted, a snapshot is taken
    once, here, for this call only.

    One clause type raising an unexpected exception is isolated
    (requirement 11): it is recorded as an error outcome (decision=None,
    a short exception-type-only message — never a traceback or contract
    text, which could otherwise leak into logs) and every other clause
    type's evaluation proceeds and is preserved. No fabricated decision is
    ever substituted for a failed evaluation."""
    if active_positions is None:
        active_positions = snapshot_active_positions(db, playbook.id)

    outcomes: List[ClauseEvaluationOutcome] = []
    for clause_type in pa.CLAUSE_TYPES:
        position = active_positions.get(clause_type)
        if position is None:
            continue
        revision_metadata = _revision_metadata_for(position)
        try:
            rule = pa.build_policy_rule_for_enforcement(position)
            extract_fn, evaluate_fn = pa._ENGINE_FUNCS[clause_type]
            facts = extract_fn(contract_text)
            label = pa.CLAUSE_TYPE_LABELS[clause_type]
            decision = evaluate_fn(
                facts, rule, source=f"{playbook.name} — {label} (policy position #{position.id})",
            )
            outcomes.append(ClauseEvaluationOutcome(
                clause_type=clause_type, decision=decision, revision_metadata=revision_metadata,
            ))
        except Exception as exc:  # noqa: BLE001 — isolation boundary, see docstring
            outcomes.append(ClauseEvaluationOutcome(
                clause_type=clause_type, decision=None, revision_metadata=revision_metadata,
                error=f"{type(exc).__name__}",
            ))
    return outcomes


_ACTIONABLE_STATES = {"NEGOTIATE", "MUST_REDLINE", "PROHIBITED", "ESCALATE", "REQUIRES_REVIEW"}

_STATE_SEVERITY = {
    "PROHIBITED": "critical",
    "ESCALATE": "high",
    "MUST_REDLINE": "high",
    "REQUIRES_REVIEW": "high",
    "NEGOTIATE": "medium",
    "ACCEPT_WITH_NOTE": "low",
    "ACCEPT": "low",
}


def _finding_from_decision(clause_type: str, decision) -> Optional[Dict[str, Any]]:
    """Builds the same shape of synthetic "policy_decision" finding
    apply_liability_policy has always built, generalized to any clause
    type — this is the one existing finding-injection contract
    (finding_type="policy_decision", consumed generically by the review
    UI's findings loop and by review_workflow's accept/edit/reject), never
    a second, clause-specific plumbing path (requirement 9)."""
    if decision.state not in _ACTIONABLE_STATES or decision.start_index is None:
        return None
    return {
        "rule_id": decision.rule_id, "rule_name": f"{pa.CLAUSE_TYPE_LABELS[clause_type]} Policy",
        "title": f"{pa.CLAUSE_TYPE_LABELS[clause_type]} — {decision.state.replace('_', ' ')}",
        "severity": _STATE_SEVERITY.get(decision.state, "medium"),
        "rationale": decision.explanation,
        "matched_excerpt": decision.contract_language, "position": None, "context": None,
        "clause_number": None, "matched_keywords": [], "aliases": [],
        "start_index": decision.start_index, "end_index": decision.end_index,
        "exact_snippet": decision.contract_language, "evidence": None,
        "party_direction": None, "finding_type": "policy_decision",
        "finding_type_label": "Policy Decision", "confidence_breakdown": None,
        "redline": {
            "issue": decision.required_action, "legal_rationale": decision.explanation,
            "suggested_redline": decision.fallback_text or "",
        } if decision.fallback_text else None,
        "policy_state": decision.state,
        # clause_type / escalate_to — see apply_liability_policy's matching
        # comment; same rationale, generalized to all six adapters.
        "clause_type": clause_type,
        "escalate_to": decision.escalate_to,
        "negotiation_ladder": [
            {"label": s["label"], "description": s["description"], "status": s["status"]}
            for s in decision.as_dict()["negotiation_ladder"]
        ],
        "policy_source": decision.source,
        "controlling_provision": decision.controlling_provision,
        "our_position": decision.our_position,
        "counterparty_position": decision.counterparty_position,
        "evidence_report": decision.render_evidence_report(),
    }


def _error_finding(clause_type: str) -> Dict[str, Any]:
    """Safe error state for a clause whose evaluation raised (requirement
    11): a visible, auditable notice that automated evaluation could not
    run for this clause type, routed to manual review — never a
    fabricated legal decision, and carrying no exception detail or
    contract text that error logging shouldn't surface to a reviewer."""
    label = pa.CLAUSE_TYPE_LABELS[clause_type]
    return {
        "rule_id": f"policy-error-{clause_type}", "rule_name": f"{label} Policy",
        "title": f"{label} — Automated evaluation failed",
        "severity": "high",
        "rationale": (
            f"The deterministic {label.lower()} policy engine could not evaluate this contract "
            "against your active policy. This clause has not been assessed and requires manual review."
        ),
        "matched_excerpt": None, "position": None, "context": None,
        "clause_number": None, "matched_keywords": [], "aliases": [],
        "start_index": None, "end_index": None, "exact_snippet": None, "evidence": None,
        "party_direction": None, "finding_type": "policy_decision",
        "finding_type_label": "Policy Decision", "confidence_breakdown": None,
        "redline": None, "policy_state": "EVALUATION_ERROR", "negotiation_ladder": [],
        "policy_source": None, "controlling_provision": None, "our_position": None,
        "counterparty_position": None, "evidence_report": None,
        "clause_type": clause_type, "escalate_to": None,
    }


def apply_active_policies(
    db: DBSession,
    playbook: Optional[Playbook],
    contract_text: str,
    findings_dict: List[Dict],
    *,
    active_positions: Optional[Dict[str, PolicyPosition]] = None,
    outcomes_out: Optional[List["ClauseEvaluationOutcome"]] = None,
) -> Optional[Dict[str, Any]]:
    """Cutover-mode equivalent of apply_liability_policy, generalized to
    all six clause types. Appends a synthetic finding per clause type that
    reaches an actionable state (mutates findings_dict in place, same
    contract as apply_liability_policy), and returns
    (policy_decisions, policy_revision_metadata) for Contract's two
    columns. Iterates pa.CLAUSE_TYPES in its fixed order so
    policy_decisions_json's key order — and therefore its serialization —
    is deterministic for the same playbook + same ACTIVE set (requirement
    10).

    `outcomes_out`, if given, is appended to (never replaced) with the same
    List[ClauseEvaluationOutcome] this function already computed — the one
    sanctioned way for interaction_enforcement.apply_interaction_rules to
    see this review's per-clause decisions without a second call into
    evaluate_active_policies (which would re-run every extract_fn/
    evaluate_fn pair a second time for no reason, since nothing here is
    non-deterministic). Optional and additive: every existing caller that
    omits it sees no change in behavior."""
    if not playbook:
        return None
    outcomes = evaluate_active_policies(db, playbook, contract_text, active_positions=active_positions)
    if outcomes_out is not None:
        outcomes_out.extend(outcomes)
    if not outcomes:
        return None

    policy_decisions: Dict[str, Any] = {}
    revision_metadata: Dict[str, Any] = {}
    for outcome in outcomes:
        revision_metadata[outcome.clause_type] = dict(outcome.revision_metadata)
        if outcome.error is not None:
            revision_metadata[outcome.clause_type]["error"] = outcome.error
            findings_dict.append(_error_finding(outcome.clause_type))
            continue
        decision = outcome.decision
        policy_decisions[outcome.clause_type] = decision.as_dict()
        finding = _finding_from_decision(outcome.clause_type, decision)
        if finding is not None:
            findings_dict.append(finding)

    return {"policy_decisions": policy_decisions, "policy_revision_metadata": revision_metadata}


# ---------------------------------------------------------------------------
# Shadow comparison — requirements 1, 2
# ---------------------------------------------------------------------------

# Fields legally required to be byte-identical for "zero divergence."
# Excludes `source` (a free-text label that legitimately differs between
# the two paths — "<playbook> v<version>" vs "<playbook> — Limitation of
# Liability (policy position #<id>)" — and carries no legal meaning) and
# excludes nothing else: state, every evidence/provenance field, and the
# full negotiation ladder must match exactly.
_DIVERGENCE_IGNORED_FIELDS = {"source"}


def _diff_decision_dicts(legacy: Dict[str, Any], migrated: Dict[str, Any]) -> List[str]:
    keys = (set(legacy) | set(migrated)) - _DIVERGENCE_IGNORED_FIELDS
    return sorted(k for k in keys if legacy.get(k) != migrated.get(k))


def run_shadow_comparison(
    db: DBSession, playbook: Playbook, contract_text: str, *, contract_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Shadow-mode comparison for limitation_of_liability only (the only
    clause type with a legacy PolicyRule to compare against — the other
    five have no legacy equivalent, so for them "cutover" is simply
    "policy enforcement exists where none did before," not a divergence
    question). Evaluates BOTH the legacy PolicyRule path and the migrated
    ACTIVE PolicyPosition path (when both exist for this playbook) and
    logs comparison metadata to AuditLog — state, whether they diverged,
    and which fields diverged, never the contract text or the full
    decision payload (which embeds verbatim contract excerpts).

    Returns the comparison dict for callers that want it directly (e.g.
    the release-gate benchmark); production request handling in "shadow"
    mode does not use the return value to decide what to show the user —
    the legacy call's own return value remains authoritative there."""
    legacy_rule = db.query(PolicyRule).filter(
        PolicyRule.playbook_id == playbook.id, PolicyRule.clause_type == "limitation_of_liability",
    ).first()
    migrated_position = db.query(PolicyPosition).filter(
        PolicyPosition.playbook_id == playbook.id,
        PolicyPosition.clause_type == "limitation_of_liability",
        PolicyPosition.status == "ACTIVE",
    ).first()
    if legacy_rule is None or migrated_position is None:
        return None

    legacy_facts = liability_policy_engine.extract_liability_facts(contract_text)
    legacy_decision = liability_policy_engine.evaluate_liability_policy(
        legacy_facts, legacy_rule, source=f"{playbook.name} v{legacy_rule.version}",
    )

    migrated_outcomes = evaluate_active_policies(
        db, playbook, contract_text,
        active_positions={"limitation_of_liability": migrated_position},
    )
    migrated_outcome = migrated_outcomes[0] if migrated_outcomes else None

    legacy_dict = legacy_decision.as_dict()
    # is_error and diverged are deliberately distinct signals (Phase 4.1):
    # a comparison where the migrated path couldn't even run is an
    # OPERATIONAL failure (the evaluation itself broke), not necessarily
    # evidence that the two policy representations disagree — conflating
    # them would make policy_readiness.py's separate "shadow evaluation
    # errors" and "live shadow divergence" release-gate checks
    # indistinguishable from AuditLog alone. is_error implies diverged
    # (there's no valid migrated state to call "matching"), but not the
    # reverse.
    if migrated_outcome is None or migrated_outcome.error is not None:
        is_error = True
        diverged = True
        diff_fields = ["EVALUATION_ERROR"]
        migrated_state = None
    else:
        is_error = False
        migrated_dict = migrated_outcome.decision.as_dict()
        diff_fields = _diff_decision_dicts(legacy_dict, migrated_dict)
        diverged = bool(diff_fields)
        migrated_state = migrated_dict["state"]

    comparison = {
        "playbook_id": playbook.id,
        "legacy_policy_rule_id": legacy_rule.id,
        "migrated_policy_position_id": migrated_position.id,
        "legacy_state": legacy_dict["state"],
        "migrated_state": migrated_state,
        "diverged": diverged,
        "is_error": is_error,
        "diff_fields": diff_fields,
    }

    db.add(AuditLog(
        event_type="phase4_shadow_comparison",
        actor_user_id=None,
        target_type="contract", target_id=contract_id,
        success=not diverged,
        detail="error" if is_error else ("diverged" if diverged else "match"),
        metadata_json=comparison,
    ))
    return comparison


# ---------------------------------------------------------------------------
# Migration coverage — requirement 7 (fail closed)
# ---------------------------------------------------------------------------

def find_unmigrated_liability_policies(db: DBSession) -> List[int]:
    """Every legacy limitation_of_liability PolicyRule that is not yet
    backed by an equivalent ACTIVE PolicyPosition. Non-empty means cutover
    mode would silently stop enforcing that playbook's liability policy —
    exactly the failure this function exists to catch before it happens.
    Returns playbook_ids, never policy content."""
    unmigrated = []
    for rule in db.query(PolicyRule).filter(PolicyRule.clause_type == "limitation_of_liability").all():
        active = db.query(PolicyPosition).filter(
            PolicyPosition.playbook_id == rule.playbook_id,
            PolicyPosition.clause_type == "limitation_of_liability",
            PolicyPosition.status == "ACTIVE",
        ).first()
        if active is None:
            unmigrated.append(rule.playbook_id)
    return unmigrated


class MigrationCoverageError(RuntimeError):
    """Raised when cutover mode is requested but migration coverage is
    incomplete. Deliberately fatal (not a warning/log line) — requirement
    7 asks for fail-closed behavior on deployment/cutover, and a swallowed
    exception here is exactly the "silently dropping enforcement" this
    module must not do."""


def verify_migration_coverage_or_fail_closed(db: DBSession) -> None:
    unmigrated = find_unmigrated_liability_policies(db)
    if unmigrated:
        raise MigrationCoverageError(
            f"Refusing to start in cutover mode: {len(unmigrated)} playbook(s) have a legacy "
            f"limitation_of_liability PolicyRule with no equivalent ACTIVE PolicyPosition "
            f"(playbook_ids={unmigrated}). Run playbook_authoring.migrate_all_legacy_policy_rules(db) "
            f"and re-verify before enabling POLICY_ENFORCEMENT_MODE=cutover."
        )


# ---------------------------------------------------------------------------
# Orchestrator — the single call site main.py uses
# ---------------------------------------------------------------------------

def apply_policies_for_review(
    db: DBSession, playbook: Optional[Playbook], contract_text: str, findings_dict: List[Dict],
    *, contract_id: Optional[int] = None,
) -> Dict[str, Any]:
    """The one function main.py calls for policy enforcement, regardless
    of mode. Returns {"policy_decisions": ..., "policy_revision_metadata":
    ...} — the former goes to Contract.policy_decisions_json exactly as
    before (backward-compatible shape: {clause_type: decision_dict}), the
    latter to the new Contract.policy_revision_metadata_json column
    (empty/absent in legacy and shadow modes, since the legacy path has no
    PolicyPosition revision to pin)."""
    mode = get_enforcement_mode()
    # One row per mode change (no-op in the steady state) so an operator can
    # see how long this deployment has been in its current mode — P0-2.
    try:
        record_enforcement_mode_observation(db)
    except Exception:  # noqa: BLE001 — observability must never break a review
        pass

    if mode == "cutover":
        if not playbook:
            return {"policy_decisions": None, "policy_revision_metadata": None, "interaction_decisions": None}
        snapshot = snapshot_active_positions(db, playbook.id)
        outcomes: List["ClauseEvaluationOutcome"] = []
        result = apply_active_policies(
            db, playbook, contract_text, findings_dict, active_positions=snapshot, outcomes_out=outcomes,
        )
        if result is None:
            return {"policy_decisions": None, "policy_revision_metadata": None, "interaction_decisions": None}
        # Interaction Engine V1 (docs/architecture/interaction_engine_v1_design.md
        # S11) — the single integration point. Local import to avoid a
        # module-load-time circular import (interaction_enforcement.py
        # imports ClauseEvaluationOutcome from this module); consumes only
        # the outcomes this same apply_active_policies() call already
        # computed — no second evaluation pass, no raw-text access.
        import interaction_enforcement
        result["interaction_decisions"] = interaction_enforcement.apply_interaction_rules(outcomes, findings_dict)
        return result

    # legacy and shadow both use the legacy path for the user-visible result.
    legacy_decisions = apply_liability_policy(db, playbook, contract_text, findings_dict)

    if mode == "shadow" and playbook is not None:
        try:
            run_shadow_comparison(db, playbook, contract_text, contract_id=contract_id)
        except Exception:
            # Shadow comparison is diagnostic-only; a failure here must
            # never affect the user-visible legacy result already computed
            # above (requirement 1: "the user-visible result must still
            # come from the legacy path during shadow mode").
            pass

    return {"policy_decisions": legacy_decisions, "policy_revision_metadata": None, "interaction_decisions": None}


# ---------------------------------------------------------------------------
# Phase 4.1 UX remediation — policy-decision Verify (P0-2 from
# docs/architecture/playbook_ux_audit.md)
#
# The existing rule-engine "Verify" action (main.py's /review/verify)
# only ever replays rule_engine.analyze() — the pattern-match rule set.
# Every policy engine's RULE_ID (e.g. liability_policy_engine.RULE_ID ==
# "POLICY_LOL_CAP") never appears in that replay, so verifying a
# policy_decision finding through the old path always returns
# verified=False and the UI incorrectly reports the finding "may be
# stale," regardless of whether the underlying policy actually changed.
# This is a distinct verification question needing its own replay: does
# THIS deterministic policy engine, evaluated against THIS contract text
# under the EXACT policy configuration that produced the original
# decision, reproduce the same result? "Exact configuration" means the
# pinned revision (Contract.policy_revision_metadata_json, Phase 4) when
# one exists — never today's current ACTIVE position, which may since
# have been superseded — falling back to the current legacy PolicyRule
# for findings produced while in "legacy"/"shadow" mode, where no
# revision was pinned because PolicyRule has no revisioning at all (it is
# mutated in place, so "the current row" IS "the row that produced this
# decision," unlike PolicyPosition).
# ---------------------------------------------------------------------------

def verify_policy_finding(db: DBSession, contract: Contract, finding: Dict[str, Any]) -> Dict[str, Any]:
    """Re-evaluates a single policy_decision finding and reports whether
    the deterministic engine reproduces the same state. Ownership is
    re-derived from contract.playbook_id (the caller has already checked
    contract.user_id == the requesting user — see main.py's
    _get_owned_contract) — a pinned policy_position_id is only ever
    looked up scoped to that playbook_id, never trusted bare, so this
    cannot be used to read another user's policy configuration.

    Returns one of:
      {"policy_verification": True, "verified": True/False,
       "replayed_state": <state or None>, "original_state": <state>,
       "reason": <short, safe, no contract/policy text>}
    """
    clause_type = finding.get("clause_type")
    original_state = finding.get("policy_state")

    if clause_type not in pa.CLAUSE_TYPES:
        return {
            "policy_verification": True, "verified": False,
            "replayed_state": None, "original_state": original_state,
            "reason": "This finding does not identify a known policy clause type.",
        }

    extract_fn, evaluate_fn = pa._ENGINE_FUNCS[clause_type]
    revision_meta = (contract.policy_revision_metadata_json or {}).get(clause_type)

    if revision_meta and revision_meta.get("policy_position_id") is not None and not revision_meta.get("error"):
        # cutover-mode finding — replay against the EXACT pinned revision,
        # by id, regardless of whether it is still ACTIVE today (it may
        # have since been superseded by a newer revision — see module
        # docstring). Scoped to this contract's own playbook, never a bare
        # id lookup.
        position = db.query(PolicyPosition).filter(
            PolicyPosition.id == revision_meta["policy_position_id"],
            PolicyPosition.playbook_id == contract.playbook_id,
        ).first()
        if position is None:
            return {
                "policy_verification": True, "verified": False,
                "replayed_state": None, "original_state": original_state,
                "reason": "The exact policy revision that produced this decision no longer exists.",
            }
        if config_hash_for_position(position) != revision_meta.get("config_hash"):
            # Should not happen under the revision-not-mutation invariant
            # (Phase 1) — an ACTIVE row is never mutated in place, and this
            # pinned row is looked up by id regardless of current status.
            # Reported as a distinct, honest reason rather than folded into
            # a generic "stale" message if it is ever observed.
            return {
                "policy_verification": True, "verified": False,
                "replayed_state": None, "original_state": original_state,
                "reason": "The pinned policy revision's content does not match what was recorded at review time.",
            }
        rule = pa.BUILDERS[clause_type](position)
        source_label = f"Verify replay — pinned revision #{position.id}"
    elif clause_type == "limitation_of_liability":
        # legacy/shadow-mode finding — PolicyRule has no revisioning of its
        # own (rows are mutated in place), so "the row that produced this
        # decision" and "the current row" are the same row by construction.
        rule = db.query(PolicyRule).filter(
            PolicyRule.playbook_id == contract.playbook_id, PolicyRule.clause_type == clause_type,
        ).first()
        if rule is None:
            return {
                "policy_verification": True, "verified": False,
                "replayed_state": None, "original_state": original_state,
                "reason": "This playbook no longer has a Limitation of Liability policy configured.",
            }
        source_label = "Verify replay — current policy"
    else:
        return {
            "policy_verification": True, "verified": False,
            "replayed_state": None, "original_state": original_state,
            "reason": "No policy revision was recorded for this decision.",
        }

    facts = extract_fn(contract.contract_text)
    replay_decision = evaluate_fn(facts, rule, source=source_label)
    verified = replay_decision.state == original_state
    return {
        "policy_verification": True, "verified": verified,
        "replayed_state": replay_decision.state, "original_state": original_state,
        "reason": None if verified else "Re-evaluating this policy against the contract produced a different result.",
    }
