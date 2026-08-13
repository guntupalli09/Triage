"""
Phase 2 — Deterministic/Private Template Import: extraction proposal
builders.

Reads a PlaybookSourceDocument's text through the SAME six
extract_*_facts() functions the engines already use (imported directly,
never modified, never wrapped), and proposes PolicyPositionField values —
never writes to an ACTIVE PolicyPosition, never auto-activates, never
calls an LLM or any network API. See
docs/architecture/phase2_extraction_mapping.md for the field-by-field
classification (DIRECTLY_ESTABLISHABLE / REQUIRES_LAWYER_INTERPRETATION /
NOT_DERIVABLE_FROM_TEMPLATE) this module implements, and the governing
rule behind every judgment call below: a template's own clause content
may establish the *negative* of a prohibition/requirement when it
self-evidently contains the disfavored thing itself, but a favorable term
never establishes the requirement in the other direction, and plain
silence never establishes anything.

This is an evidence-extraction system, not a policy-completion system —
the release-gate metric that matters most is false-establishment: cases
where the source document does not actually support a value this module
proposed as ESTABLISHED. See benchmarks/phase2_extraction_corpus.py /
benchmarks/run_phase2_extraction_benchmark.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import assignment_policy_engine as ape
import confidentiality_policy_engine as cpe
import data_security_policy_engine as dse
import governing_law_policy_engine as gpe
import indemnification_policy_engine as ipe
import ip_ownership_policy_engine as ipoe
import liability_policy_engine as lpe
import playbook_authoring as pa
import termination_policy_engine as tpe
from models import Playbook, PlaybookSourceDocument, PolicyPosition, PolicyPositionField

# Bumped whenever a proposal function's logic changes in a way that could
# change output for the same input document — never bumped for unrelated
# changes elsewhere in this module. Stamped onto every EXTRACTED field
# this module writes (models.PolicyPositionField.extraction_version), so
# a historical proposal is always explicable against the code that made
# it, per the Phase 2 determinism requirement.
EXTRACTION_VERSION = "phase2-deterministic-v1"


@dataclass
class ProposedField:
    """One proposed value for one config_json field, before it's written
    to the database. `status` is the only thing that determines what
    happens to `value` downstream (only ESTABLISHED values are ever
    written into config_json — see _apply_proposal). `source` defaults to
    "EXTRACTED" (Phase 2's only producer); Phase 3 (playbook_ai_extraction.py)
    sets it explicitly to "EXTRACTED" or "INFERRED" per candidate, and may
    also produce status="REQUIRES_LAWYER_INTERPRETATION" (models.py's 4th
    field status, unreachable from Phase 2's deterministic path)."""
    status: str  # "ESTABLISHED" | "NOT_ESTABLISHED" | "CONFLICTING" | "REQUIRES_LAWYER_INTERPRETATION"
    value: Any = None
    evidence_excerpt: Optional[str] = None
    evidence_start_index: Optional[int] = None
    evidence_end_index: Optional[int] = None
    reason: Optional[str] = None  # human-readable, shown for non-ESTABLISHED statuses
    source: str = "EXTRACTED"


def _not_established(reason: str) -> ProposedField:
    return ProposedField(status="NOT_ESTABLISHED", reason=reason)


def _established(value: Any, excerpt: str, start: Optional[int] = None, end: Optional[int] = None) -> ProposedField:
    return ProposedField(status="ESTABLISHED", value=value, evidence_excerpt=excerpt,
                          evidence_start_index=start, evidence_end_index=end)


def _conflicting(excerpt_a: str, excerpt_b: str, reason: str) -> ProposedField:
    combined = f"Conflict — {reason}. First: \"{excerpt_a}\" — Second: \"{excerpt_b}\""
    return ProposedField(status="CONFLICTING", evidence_excerpt=combined, reason=reason)


def _other_side(contract_side: str) -> Optional[str]:
    if contract_side == "buy_side":
        return "sell_side"
    if contract_side == "sell_side":
        return "buy_side"
    return None  # "mutual" has no single "other side"


# ---------------------------------------------------------------------------
# 1. Limitation of Liability
# ---------------------------------------------------------------------------

def _propose_liability_fields(facts: "lpe.LiabilityFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["limitation_of_liability"]}

    if not facts.clause_found:
        return out

    # Multiple provisions with genuinely different effective caps that the
    # engine's own reconciliation could not resolve to one controlling
    # provision -> conflicting, never silently pick one.
    if facts.reconciliation == "unreconciled" and len(facts.provisions) >= 2:
        caps = []
        for prov in facts.provisions:
            cap, _reason = prov.general_cap_expression.effective_cap()
            if cap is not None:
                caps.append((prov, cap))
        if len(caps) >= 2 and len({c.summary() for _, c in caps}) > 1:
            (prov_a, cap_a), (prov_b, cap_b) = caps[0], caps[1]
            out["preferred_multiplier"] = _conflicting(
                prov_a.raw_excerpt, prov_b.raw_excerpt,
                f"multiple liability provisions state different caps ({cap_a.summary()} vs {cap_b.summary()})",
            )
            return out

    provision = facts.controlling_provision
    if provision is None:
        return out

    cap, _reason = provision.general_cap_expression.effective_cap()
    if cap is not None:
        if cap.kind == "fee_multiplier" and cap.basis == lpe.BASIS_FEES:
            out["preferred_multiplier"] = _established(cap.multiplier, provision.raw_excerpt, cap.start_index, cap.end_index)
        elif cap.kind == "unlimited":
            # Self-evident: the template's own cap IS unlimited liability,
            # so the template plainly does not categorically prohibit it.
            out["prohibit_unlimited"] = _established(False, provision.raw_excerpt, cap.start_index, cap.end_index)

    established_exceptions = [
        cat for cat, treatment in provision.category_treatments.items()
        if treatment.established and treatment.treatment in ("uncapped", "super_cap")
    ]
    if established_exceptions:
        excerpt = " | ".join(
            provision.category_treatments[c].raw_excerpt or provision.raw_excerpt for c in established_exceptions
        )
        out["required_exceptions_json"] = _established(established_exceptions, excerpt)

    if provision.consequential_damages_established and provision.consequential_damages_excluded is True:
        out["require_consequential_damages_exclusion"] = _established(True, provision.raw_excerpt)
        if provision.consequential_damages_carveouts:
            out["required_consequential_carveouts_json"] = _established(
                provision.consequential_damages_carveouts, provision.raw_excerpt,
            )

    return out


# ---------------------------------------------------------------------------
# 2. Indemnification
# ---------------------------------------------------------------------------

def _propose_indemnification_fields(facts: "ipe.IndemnificationFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["indemnification"]}
    if not facts.clause_found:
        return out

    # Reused verbatim from indemnification_policy_engine — the same
    # already-tested logic evaluate_indemnification_policy() itself uses
    # to decide which obligation is "ours," so Phase 2's read can never
    # silently disagree with what the engine would resolve at review time.
    exposure, protection, reasons = ipe._resolve_obligations_for_side(facts.obligations, contract_side)
    if reasons:
        for name in out:
            if out[name].status == "NOT_ESTABLISHED":
                out[name].reason = "; ".join(reasons)

    if protection is not None:
        covered = [t for t, tt in protection.trigger_treatments.items() if tt.established and tt.treatment == "covered"]
        if covered:
            out["required_protection_triggers_json"] = _established(covered, protection.raw_excerpt)

    if exposure is not None:
        excluded = [t for t, tt in exposure.trigger_treatments.items() if tt.established and tt.treatment == "excluded"]
        if excluded:
            out["prohibited_exposure_triggers_json"] = _established(excluded, exposure.raw_excerpt)

        if exposure.scope == "third_party_only":
            out["require_exposure_third_party_only"] = _established(True, exposure.raw_excerpt)
        elif exposure.scope == "includes_first_party":
            out["require_exposure_third_party_only"] = _established(False, exposure.raw_excerpt)

        if exposure.defense_control == "indemnifying_party":
            out["require_defense_control_for_exposure"] = _established(True, exposure.raw_excerpt)
        elif exposure.defense_control == "indemnified_party":
            out["require_defense_control_for_exposure"] = _established(False, exposure.raw_excerpt)

        if exposure.notice_required is True and exposure.cooperation_required is True:
            out["require_notice_and_cooperation_for_exposure"] = _established(True, exposure.raw_excerpt)

        if exposure.monetary.kind == "unlimited":
            out["prohibit_uncapped_exposure"] = _established(False, exposure.raw_excerpt)
        elif exposure.monetary.kind == "multiplier":
            out["exposure_preferred_multiplier"] = _established(exposure.monetary.multiplier, exposure.monetary.raw_excerpt or exposure.raw_excerpt)

    return out


# ---------------------------------------------------------------------------
# 3. Termination
# ---------------------------------------------------------------------------

def _propose_termination_fields(facts: "tpe.TerminationFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["termination"]}
    if not facts.clause_found:
        return out

    other_side = _other_side(contract_side)

    def _rights_for(side: Optional[str], mutual_only: bool = False):
        if mutual_only or side is None:
            return [r for r in facts.rights if r.is_mutual]
        return [r for r in facts.rights if r.holder_side == side] + [r for r in facts.rights if r.is_mutual]

    our_rights = _rights_for(contract_side, mutual_only=(contract_side == "mutual"))
    their_rights = _rights_for(other_side, mutual_only=(contract_side == "mutual"))

    our_convenience = [r for r in our_rights if r.trigger_type == "convenience"]
    their_convenience = [r for r in their_rights if r.trigger_type == "convenience"]
    if our_convenience and their_convenience:
        out["require_mutual_convenience_termination"] = _established(True, their_convenience[0].raw_excerpt)

    their_convenience_notice = [r for r in their_convenience if r.notice_period_days is not None]
    if their_convenience_notice:
        values = {r.notice_period_days for r in their_convenience_notice}
        if len(values) == 1:
            r = their_convenience_notice[0]
            out["min_notice_days_against_us"] = _established(r.notice_period_days, r.raw_excerpt, r.start_index, r.end_index)
        else:
            a, b = their_convenience_notice[0], their_convenience_notice[1]
            out["min_notice_days_against_us"] = _conflicting(a.raw_excerpt, b.raw_excerpt, "different notice periods stated")

    their_cause = [r for r in their_rights if r.trigger_type == "material_breach" and r.cure_period_days is not None]
    if their_cause:
        values = {r.cure_period_days for r in their_cause}
        if len(values) == 1:
            r = their_cause[0]
            out["min_cure_days_against_us"] = _established(r.cure_period_days, r.raw_excerpt, r.start_index, r.end_index)
        else:
            a, b = their_cause[0], their_cause[1]
            out["min_cure_days_against_us"] = _conflicting(a.raw_excerpt, b.raw_excerpt, "different cure periods stated")

    our_immediate_cause = [r for r in our_rights if r.trigger_type == "material_breach" and r.immediate]
    if our_immediate_cause:
        # Self-evident: our own template lets termination for cause happen
        # immediately without a cure opportunity, so it plainly doesn't
        # categorically prohibit that.
        out["prohibit_immediate_termination_for_cause"] = _established(False, our_immediate_cause[0].raw_excerpt)

    present_topics = [t for t, st in facts.survival_topics.items() if st.present]
    if present_topics:
        out["required_survival_topics_json"] = _established(present_topics, "Survival clause")

    if facts.fee.kind == "unlimited":
        out["prohibit_uncapped_termination_fee"] = _established(False, facts.fee.raw_excerpt)
    elif facts.fee.kind == "multiplier":
        out["fee_preferred_multiplier"] = _established(facts.fee.multiplier, facts.fee.raw_excerpt)

    return out


# ---------------------------------------------------------------------------
# 4. Confidentiality
# ---------------------------------------------------------------------------

def _propose_confidentiality_fields(facts: "cpe.ConfidentialityFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["confidentiality"]}
    if not facts.clause_found:
        return out

    other_side = _other_side(contract_side)

    they_protect_us = [o for o in facts.obligations if (o.protecting_side == other_side and o.protected_side == contract_side) or o.is_mutual]
    we_protect_them = [o for o in facts.obligations if (o.protecting_side == contract_side and o.protected_side == other_side) or o.is_mutual]

    if they_protect_us and we_protect_them:
        out["require_mutual_confidentiality"] = _established(True, they_protect_us[0].raw_excerpt)

    if they_protect_us:
        obligation = they_protect_us[0]
        present = [t for t, present in obligation.exclusions_present.items() if present]
        if present:
            out["required_exclusions_json"] = _established(present, obligation.raw_excerpt)
        if obligation.duration_years is not None:
            values = {o.duration_years for o in they_protect_us if o.duration_years is not None}
            if len(values) == 1:
                out["min_protection_duration_years"] = _established(obligation.duration_years, obligation.raw_excerpt, obligation.start_index, obligation.end_index)
            else:
                a, b = they_protect_us[0], they_protect_us[1]
                out["min_protection_duration_years"] = _conflicting(a.raw_excerpt, b.raw_excerpt, "different protection durations stated")

    if we_protect_them:
        obligation = we_protect_them[0]
        if obligation.duration_years is not None:
            values = {o.duration_years for o in we_protect_them if o.duration_years is not None}
            if len(values) == 1:
                out["max_exposure_duration_years"] = _established(obligation.duration_years, obligation.raw_excerpt, obligation.start_index, obligation.end_index)
            else:
                a, b = we_protect_them[0], we_protect_them[1]
                out["max_exposure_duration_years"] = _conflicting(a.raw_excerpt, b.raw_excerpt, "different exposure durations stated")

    return out


# ---------------------------------------------------------------------------
# 5. Assignment
# ---------------------------------------------------------------------------

def _propose_assignment_fields(facts: "ape.AssignmentFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["assignment"]}
    if not facts.clause_found:
        return out

    other_side = _other_side(contract_side)

    our_restrictions = [r for r in facts.restrictions if r.restricted_side == contract_side or r.is_mutual]
    their_restrictions = [r for r in facts.restrictions if r.restricted_side == other_side or r.is_mutual]

    if our_restrictions and their_restrictions:
        out["require_consent_for_counterparty_assignment"] = _established(True, their_restrictions[0].raw_excerpt)

    if our_restrictions:
        restriction = our_restrictions[0]
        present = [t for t, present in restriction.exceptions_present.items() if present]
        if present:
            out["required_exceptions_json"] = _established(present, restriction.raw_excerpt)
        if restriction.consent_standard == "sole_discretion":
            # Self-evident: our own template subjects us to sole-discretion
            # consent, so it plainly doesn't prohibit that language.
            out["prohibit_sole_discretion_consent"] = _established(False, restriction.raw_excerpt)

    return out


# ---------------------------------------------------------------------------
# 6. Governing Law
# ---------------------------------------------------------------------------

_DISPUTE_RESOLUTION_MAP = {
    "arbitration": "arbitration",
    "mediation_then_arbitration": "arbitration",
    "litigation": "litigation",
}


def _propose_governing_law_fields(facts: "gpe.GoverningLawFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["governing_law"]}
    if not facts.clause_found:
        return out

    if facts.jurisdiction:
        out["preferred_jurisdictions_json"] = _established([facts.jurisdiction], facts.raw_excerpt, facts.start_index, facts.end_index)

    mapped = _DISPUTE_RESOLUTION_MAP.get(facts.dispute_resolution)
    if mapped:
        out["required_dispute_resolution"] = _established(mapped, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.jury_trial_waived:
        out["require_jury_trial_waiver"] = _established(True, facts.raw_excerpt, facts.start_index, facts.end_index)

    return out


_SUBPROCESSOR_TREATMENT_REQUIREMENT = {"notice": "notice", "consent": "consent"}


def _propose_data_security_fields(facts: "dse.DataSecurityFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["data_security"]}
    if not facts.clause_found:
        return out

    if facts.role_conflict:
        out["require_processor_role"] = _conflicting(
            facts.raw_excerpt, facts.raw_excerpt, "the same named party is attributed both controller and processor")
    else:
        our_role, unresolved_directional, _is_joint = dse._resolve_our_role(facts, contract_side)
        if our_role is not None and not unresolved_directional:
            # Self-evident: the template's own role statement plainly
            # establishes what role we expect to occupy going forward.
            out["require_processor_role"] = _established(our_role == "processor", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.subprocessor_conflict:
        out["prohibit_unrestricted_subprocessors"] = _conflicting(
            facts.raw_excerpt, facts.raw_excerpt, "subprocessor treatment is stated inconsistently")
    elif facts.subprocessor_treatment is not None:
        out["prohibit_unrestricted_subprocessors"] = _established(
            facts.subprocessor_treatment != "unrestricted", facts.raw_excerpt, facts.start_index, facts.end_index)
        req = _SUBPROCESSOR_TREATMENT_REQUIREMENT.get(facts.subprocessor_treatment)
        if req:
            out["require_subprocessor_notice_or_consent"] = _established(req, facts.raw_excerpt, facts.start_index, facts.end_index)
        elif facts.subprocessor_treatment == "prohibited":
            out["require_subprocessor_notice_or_consent"] = _established("not_required", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.breach_notification_conflict:
        out["preferred_breach_notification_hours"] = _conflicting(
            facts.raw_excerpt, facts.raw_excerpt, "different breach-notification periods stated")
    elif facts.breach_notification_hours is not None:
        out["preferred_breach_notification_hours"] = _established(float(facts.breach_notification_hours), facts.raw_excerpt, facts.start_index, facts.end_index)
        out["require_fixed_breach_notification_period"] = _established(True, facts.raw_excerpt, facts.start_index, facts.end_index)
    elif facts.breach_without_undue_delay:
        out["require_fixed_breach_notification_period"] = _established(False, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.transfer_mechanism in ("prohibited", "scc", "adequacy"):
        out["require_international_transfer_safeguard"] = _established(True, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.data_residency_region:
        out["require_data_residency"] = _established(True, facts.raw_excerpt, facts.start_index, facts.end_index)
        out["required_data_residency_regions_json"] = _established([facts.data_residency_region], facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.deletion_or_return_required is not None:
        out["require_deletion_or_return"] = _established(facts.deletion_or_return_required, facts.raw_excerpt, facts.start_index, facts.end_index)
    if facts.retention_days is not None:
        out["max_retention_days"] = _established(float(facts.retention_days), facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.audit_rights is not None:
        out["require_audit_rights"] = _established(facts.audit_rights, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.security_standard == "named_certification":
        out["require_named_security_certification"] = _established(True, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.cooperation_obligation:
        out["require_cooperation_obligation"] = _established(True, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.confidentiality_of_personal_data:
        out["require_confidentiality_of_personal_data"] = _established(True, facts.raw_excerpt, facts.start_index, facts.end_index)

    return out


def _propose_ip_ownership_fields(facts: "ipoe.IPFacts", contract_side: str) -> Dict[str, ProposedField]:
    out: Dict[str, ProposedField] = {name: _not_established("clause not found or dimension not addressed")
                                      for name in pa.CLAUSE_TYPE_CONFIG_FIELDS["ip_ownership"]}
    if not facts.clause_found:
        return out

    if "background_ip" in facts.ownership_conflict_categories:
        out["require_we_retain_background_ip"] = _conflicting(
            facts.raw_excerpt, facts.raw_excerpt, "conflicting owner attributions for background IP")
    else:
        owner, unresolved = ipoe._resolve_owner(facts, contract_side, "background_ip")
        if owner is not None and not unresolved:
            # Self-evident: the template's own ownership statement plainly
            # establishes what we expect going forward.
            out["require_we_retain_background_ip"] = _established(owner == "us", facts.raw_excerpt, facts.start_index, facts.end_index)

    if "work_product" in facts.ownership_conflict_categories:
        out["require_we_own_work_product"] = _conflicting(
            facts.raw_excerpt, facts.raw_excerpt, "conflicting owner attributions for work product")
    else:
        owner, unresolved = ipoe._resolve_owner(facts, contract_side, "work_product")
        if owner is not None and not unresolved:
            out["require_we_own_work_product"] = _established(owner == "us", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.joint_ownership_categories:
        # Self-evident: the template's own structure establishes joint
        # ownership, so the template plainly does not categorically
        # prohibit it.
        out["prohibit_joint_ownership"] = _established(False, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.embedded_background_ip_license_present is not None:
        out["require_license_for_embedded_background_ip"] = _established(facts.embedded_background_ip_license_present, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.exclusivity_conflict:
        out["require_license_exclusive"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different exclusivity stated")
    elif facts.exclusivity is not None:
        out["require_license_exclusive"] = _established(facts.exclusivity == "exclusive", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.royalty_conflict:
        out["prohibit_royalty_bearing_license"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different royalty treatment stated")
    elif facts.royalty is not None:
        out["prohibit_royalty_bearing_license"] = _established(facts.royalty == "royalty_free", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.duration_conflict:
        out["require_perpetual_license"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different license durations stated")
    elif facts.duration is not None:
        out["require_perpetual_license"] = _established(facts.duration == "perpetual", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.revocability_conflict:
        out["prohibit_revocable_license"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different revocability stated")
    elif facts.revocability is not None:
        out["prohibit_revocable_license"] = _established(facts.revocability == "irrevocable", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.sublicensable_conflict:
        out["require_sublicensable"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different sublicensing rights stated")
    elif facts.sublicensable is not None:
        out["require_sublicensable"] = _established(facts.sublicensable, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.transferable_conflict:
        out["require_transferable"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different transferability stated")
    elif facts.transferable is not None:
        out["require_transferable"] = _established(facts.transferable, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.territory_conflict:
        out["require_worldwide_territory"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different territory stated")
    elif facts.territory is not None:
        out["require_worldwide_territory"] = _established(facts.territory == "worldwide", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.purpose_limited is not None:
        out["require_purpose_limited_license"] = _established(facts.purpose_limited, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.derivative_conflict:
        out["prohibit_derivative_works"] = _conflicting(facts.raw_excerpt, facts.raw_excerpt, "different derivative-works treatment stated")
    elif facts.derivative_works_permitted is not None:
        out["prohibit_derivative_works"] = _established(not facts.derivative_works_permitted, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.feedback_treatment is not None:
        out["require_feedback_assigned"] = _established(facts.feedback_treatment == "assigned", facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.residual_knowledge_rights is not None:
        out["require_residual_knowledge_rights"] = _established(facts.residual_knowledge_rights, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.open_source_obligations_present is not None:
        out["require_open_source_disclosure"] = _established(facts.open_source_obligations_present, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.infringement_remedy_referenced is not None:
        out["require_infringement_remedy_reference"] = _established(facts.infringement_remedy_referenced, facts.raw_excerpt, facts.start_index, facts.end_index)

    if facts.post_termination_survival is not None:
        out["require_post_termination_survival"] = _established(facts.post_termination_survival, facts.raw_excerpt, facts.start_index, facts.end_index)

    return out


_PROPOSAL_FUNCS = {
    "limitation_of_liability": _propose_liability_fields,
    "indemnification": _propose_indemnification_fields,
    "termination": _propose_termination_fields,
    "confidentiality": _propose_confidentiality_fields,
    "assignment": _propose_assignment_fields,
    "governing_law": _propose_governing_law_fields,
    "data_security": _propose_data_security_fields,
    "ip_ownership": _propose_ip_ownership_fields,
}


def propose_fields(clause_type: str, facts: Any, contract_side: str) -> Dict[str, ProposedField]:
    """Public entry point — one function per clause type, dispatched by
    clause_type. `facts` is whatever extract_*_facts() for that clause
    type returned (may be None)."""
    if facts is None:
        return {name: _not_established("no clause of this type found in the document")
                for name in pa.CLAUSE_TYPE_CONFIG_FIELDS[clause_type]}
    return _PROPOSAL_FUNCS[clause_type](facts, contract_side)


# ---------------------------------------------------------------------------
# Orchestration — writes proposals into DRAFT/NEEDS_REVIEW PolicyPosition
# rows, never an ACTIVE one, never auto-approved/activated.
# ---------------------------------------------------------------------------

def _apply_proposal(
    db, position: PolicyPosition, proposed: Dict[str, ProposedField],
    source_document: PlaybookSourceDocument, user, *, extraction_version: str = EXTRACTION_VERSION,
) -> None:
    """Merges a proposal into a position. A field the lawyer has already
    manually confirmed (source=MANUAL, status=ESTABLISHED) is never
    overwritten by a re-extraction — re-importing a document must not
    silently clobber a decision a human already made. Fields with no
    usable evidence this run (status=NOT_ESTABLISHED) are left alone
    entirely: they neither create a row nor downgrade an existing one.
    CONFLICTING and REQUIRES_LAWYER_INTERPRETATION (Phase 3) both write a
    field row with evidence but never a config_json value — reused
    unmodified by playbook_ai_extraction.py, which is the only caller
    that ever produces REQUIRES_LAWYER_INTERPRETATION or source=INFERRED
    proposals; this function itself has no Phase-2-vs-3 branching, only
    generic status/source handling."""
    config = dict(position.config_json or {})
    existing_fields = {f.field_name: f for f in position.fields if f.superseded_by_field_id is None}
    now = datetime.utcnow()

    for field_name, proposal in proposed.items():
        if proposal.status == "NOT_ESTABLISHED":
            continue

        existing = existing_fields.get(field_name)
        if existing is not None and existing.source == "MANUAL" and existing.status == "ESTABLISHED":
            continue  # protect the lawyer's own confirmed decision

        if proposal.status == "ESTABLISHED":
            config[field_name] = proposal.value
        else:  # CONFLICTING | REQUIRES_LAWYER_INTERPRETATION
            config.pop(field_name, None)

        if existing is None:
            existing = PolicyPositionField(policy_position_id=position.id, field_name=field_name)
            db.add(existing)
            existing_fields[field_name] = existing

        existing.value_json = proposal.value if proposal.status == "ESTABLISHED" else None
        existing.source = proposal.source
        existing.status = proposal.status
        existing.evidence_document_id = source_document.id
        existing.evidence_excerpt = proposal.evidence_excerpt
        existing.evidence_start_index = proposal.evidence_start_index
        existing.evidence_end_index = proposal.evidence_end_index
        existing.extraction_version = extraction_version
        existing.confirmed_by_user_id = None
        existing.confirmed_at = None

    pa.validate_config(position.clause_type, config)
    position.config_json = config
    if position.status in ("NEEDS_REVIEW", "APPROVED"):
        position.status = "DRAFT"
    position.source_type = "MIXED" if position.source_type not in ("NONE",) and position.source_type != "UPLOADED_TEMPLATE" else "UPLOADED_TEMPLATE"


def import_source_document(
    db, playbook: Playbook, source_document: PlaybookSourceDocument, contract_side: str, user,
) -> Dict[str, PolicyPosition]:
    """Runs all six extractors against source_document.extracted_text and
    proposes fields into (possibly newly-created) DRAFT PolicyPosition
    rows — one per clause type the document actually addresses. A clause
    type with no clause found in the document, or no usable evidence at
    all, is left completely untouched (no empty position is created for
    it). Never writes to an ACTIVE position (get_or_build_editable_position
    forks a revision instead, exactly as Phase 1 editing does) and never
    changes any position's status to APPROVED/ACTIVE — extraction only
    ever produces DRAFT (or leaves an existing NEEDS_REVIEW/APPROVED
    position at DRAFT, per _apply_proposal, since its content changed).

    Returns {clause_type: PolicyPosition} for every clause type touched.
    """
    results: Dict[str, PolicyPosition] = {}
    for clause_type in pa.CLAUSE_TYPES:
        extract_fn, _evaluate_fn = pa._ENGINE_FUNCS[clause_type]
        facts = extract_fn(source_document.extracted_text)
        if facts is None or not getattr(facts, "clause_found", False):
            continue

        proposed = propose_fields(clause_type, facts, contract_side)
        if not any(p.status in ("ESTABLISHED", "CONFLICTING") for p in proposed.values()):
            continue

        position, _is_new = pa.get_or_build_editable_position(db, playbook, clause_type)
        if position.contract_side == "mutual" and contract_side != "mutual":
            position.contract_side = contract_side
        _apply_proposal(db, position, proposed, source_document, user)
        results[clause_type] = position

    return results
