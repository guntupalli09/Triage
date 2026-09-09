"""
Interaction Engine V1 — the seven-rule launch catalog.

Every rule here is scoped exactly to the READY_FROM_STRUCTURED_FACTS
interactions classified in docs/architecture/interaction_engine_v1_design.md
S3.10. No rule reparses contract text, calls an extractor, or reasons about
anything beyond the PolicyDecision fields documented in each rule's own
docstring (category_treatments, controlling_provision, and — for rules 6
and 7 only — the small, explicitly-registered PolicyDecision.interaction_facts
extension; see policy_engine_core.INTERACTION_FACT_REGISTRY for exactly
which keys those two rules are allowed to read and why).

Each predicate receives ONLY the already-gated, already-resolved
PolicyDecision objects for its own participating_clause_types (see
interaction_engine_core._gate_participants) — it never sees an unresolved
or absent participant, so it never has to (and never does) guess.
"""
from __future__ import annotations

from typing import Dict, Optional

from interaction_engine_core import (
    ACCEPT_WITH_NOTE, CONFLICT, DEPENDENCY, ESCALATE, REQUIRES_REVIEW,
    InteractionFinding, InteractionRule,
)
from policy_engine_core import PolicyDecision

# Category keys independently used, with identical string values, by both
# liability_policy_engine.py and indemnification_policy_engine.py (see
# design doc S1.2 — confirmed at the regex level, not merely by name).
_SHARED_LIABILITY_INDEMNITY_CATEGORIES = (
    "ip_infringement", "data_breach", "confidentiality", "gross_negligence", "willful_misconduct",
)
_NON_IP_SHARED_CATEGORIES = tuple(c for c in _SHARED_LIABILITY_INDEMNITY_CATEGORIES if c != "ip_infringement")


def _by_category(decision: PolicyDecision) -> Dict[str, dict]:
    return {t["category"]: t for t in decision.category_treatments}


# ---------------------------------------------------------------------------
# Rule 1 — IP infringement: Indemnification covers it AND Liability treats
# it as uncapped/super-capped. The flagship example from the design doc.
# ---------------------------------------------------------------------------

def _rule_ip_uncapped_indemnity(decisions: Dict[str, PolicyDecision]) -> Optional[InteractionFinding]:
    liability_ct = _by_category(decisions["limitation_of_liability"])
    indemnification_ct = _by_category(decisions["indemnification"])
    lt = liability_ct.get("ip_infringement")
    it = indemnification_ct.get("ip_infringement")
    if not lt or not it:
        return None
    if lt["treatment"] not in ("uncapped", "super_cap") or it["treatment"] != "covered":
        return None
    return InteractionFinding(
        state=ESCALATE,
        explanation=(
            "Limitation of Liability treats IP infringement as "
            f"{lt['treatment'].replace('_', ' ')} — excluded from (or given a separate cap above) the general "
            "liability cap — while Indemnification independently establishes that our exposure covers "
            "third-party IP infringement claims. These two independently established positions interact: "
            "an IP infringement claim could expose us to liability the general cap does not limit."
        ),
        required_action="Legal review required — confirm the IP infringement exposure under Indemnification is intended to be uncapped.",
        matched_facts={"limitation_of_liability": lt["treatment"], "indemnification": it["treatment"]},
    )


# ---------------------------------------------------------------------------
# Rule 2 — same pattern as Rule 1, generalized to the four other categories
# shared between Liability and Indemnification (data_breach, confidentiality,
# gross_negligence, willful_misconduct). A separate registered rule from
# Rule 1 (not merged) because IP infringement is the flagship, independently
# reviewable case; this rule reports every OTHER category that matches the
# same pattern in one interaction so a lawyer sees "these categories are all
# affected" rather than four visually-identical rows.
# ---------------------------------------------------------------------------

def _rule_shared_category_mismatch(decisions: Dict[str, PolicyDecision]) -> Optional[InteractionFinding]:
    liability_ct = _by_category(decisions["limitation_of_liability"])
    indemnification_ct = _by_category(decisions["indemnification"])
    matched = []
    for cat in _NON_IP_SHARED_CATEGORIES:
        lt = liability_ct.get(cat)
        it = indemnification_ct.get(cat)
        if lt and it and lt["treatment"] in ("uncapped", "super_cap") and it["treatment"] == "covered":
            matched.append(cat)
    if not matched:
        return None
    labels = ", ".join(c.replace("_", " ") for c in matched)
    return InteractionFinding(
        state=ESCALATE,
        explanation=(
            f"Limitation of Liability treats the following categor{'y' if len(matched) == 1 else 'ies'} as "
            f"uncapped or separately capped above the general limit: {labels}. Indemnification independently "
            f"establishes that our exposure covers {'this' if len(matched) == 1 else 'these'} same categor"
            f"{'y' if len(matched) == 1 else 'ies'}. These are independently established positions that interact."
        ),
        required_action=f"Legal review required — confirm the {labels} exposure under Indemnification is intended to be uncapped.",
        matched_facts={"categories": labels},
    )


# ---------------------------------------------------------------------------
# Rule 3 — Indemnification exposure rides inside Liability's general cap
# (informational DEPENDENCY, not an incompatibility).
#
# Two independent signals (either is enough), after Phase 4 hydration:
#   (a) Per shared category: LoL treats the cat as within_general_cap /
#       not_addressed AND Indemnification covers it (launch-catalog join).
#   (b) Family-level vendor indemnity inside the general cap: LoL category
#       "indemnification" is within_general_cap / not_addressed, OR
#       ContractDocumentFacts.cross_clause records
#       LIABILITY_APPLIES_TO_INDEMNIFICATION (§6.3), AND Indemnification
#       establishes any covered exposure. Explicit per-category uncapped /
#       super_cap carve-outs are excluded from (b) so Rule 1 owns that conflict.
# ---------------------------------------------------------------------------

def _family_indemnity_within_general_cap(
    liability_ct: Dict[str, dict], document_facts,
) -> bool:
    lt = liability_ct.get("indemnification")
    if lt and lt.get("treatment") in ("within_general_cap", "not_addressed"):
        return True
    if document_facts is None:
        return False
    from contract_facts.presence import Presence

    link = document_facts.cross_clause.liability_applies_to_indemnification()
    return link is not None and link.presence is Presence.PRESENT


def _rule_indemnity_within_general_cap(
    decisions: Dict[str, PolicyDecision], document_facts=None,
) -> Optional[InteractionFinding]:
    liability_ct = _by_category(decisions["limitation_of_liability"])
    indemnification_ct = _by_category(decisions["indemnification"])
    matched = []
    for cat in _SHARED_LIABILITY_INDEMNITY_CATEGORIES:
        lt = liability_ct.get(cat)
        it = indemnification_ct.get(cat)
        if lt and it and lt["treatment"] in ("within_general_cap", "not_addressed") and it["treatment"] == "covered":
            matched.append(cat)

    family_within = _family_indemnity_within_general_cap(liability_ct, document_facts)
    if family_within:
        for cat in _SHARED_LIABILITY_INDEMNITY_CATEGORIES:
            it = indemnification_ct.get(cat)
            if not it or it.get("treatment") != "covered" or cat in matched:
                continue
            lt = liability_ct.get(cat)
            if lt and lt.get("treatment") in ("uncapped", "super_cap"):
                continue
            matched.append(cat)
        if not matched:
            # Covered triggers outside the shared LoL/Indemnity vocabulary
            # still count for a family-level §6.3 / indemnification-within-cap note.
            # Skip categories Liability already carved out as uncapped/super_cap
            # (Rules 1–2 own those conflicts).
            for cat, it in indemnification_ct.items():
                if it.get("treatment") != "covered":
                    continue
                lt = liability_ct.get(cat)
                if lt and lt.get("treatment") in ("uncapped", "super_cap"):
                    continue
                matched.append(cat)

    if not matched:
        return None
    labels = ", ".join(c.replace("_", " ") for c in matched)
    category_word = "category" if len(matched) == 1 else "categories"
    source = "family_within_general_cap" if family_within else "per_category"
    return InteractionFinding(
        state=ACCEPT_WITH_NOTE,
        explanation=(
            f"Indemnification covers {labels}, and Limitation of Liability does not carve this {category_word} "
            f"out of the general cap — indemnification exposure for {labels} rides inside the general liability cap."
        ),
        required_action="None — noted for the file: indemnification exposure for this category is bounded by the general liability cap.",
        matched_facts={"categories": labels, "source": source},
    )


# ---------------------------------------------------------------------------
# Rule 4 — either side leaves a shared category's treatment genuinely
# ambiguous (category_treatments[cat].treatment == "unresolved"), even when
# the decision as a whole resolved to a state other than REQUIRES_REVIEW
# (this happens when the ambiguous category is not itself one the policy
# listed as required/prohibited -- see liability_policy_engine.py's
# evaluate_liability_policy: an unresolved category only forces the whole
# decision to REQUIRES_REVIEW when that category is in required_exceptions).
# This is genuinely distinct from interaction_engine_core's generic
# whole-decision gating (INSUFFICIENT_FACTS), which only catches a
# decision-level REQUIRES_REVIEW/NOT_APPLICABLE/error -- per-category
# ambiguity on an otherwise-resolved decision would otherwise never surface
# at the interaction layer at all.
# ---------------------------------------------------------------------------

def _rule_category_ambiguity(decisions: Dict[str, PolicyDecision]) -> Optional[InteractionFinding]:
    liability_ct = _by_category(decisions["limitation_of_liability"])
    indemnification_ct = _by_category(decisions["indemnification"])
    ambiguous = []
    for cat in _SHARED_LIABILITY_INDEMNITY_CATEGORIES:
        lt = liability_ct.get(cat)
        it = indemnification_ct.get(cat)
        if (lt and lt["treatment"] == "unresolved") or (it and it["treatment"] == "unresolved"):
            ambiguous.append(cat)
    if not ambiguous:
        return None
    labels = ", ".join(c.replace("_", " ") for c in ambiguous)
    return InteractionFinding(
        state=REQUIRES_REVIEW,
        explanation=(
            f"Limitation of Liability and/or Indemnification treat the following categor"
            f"{'y' if len(ambiguous) == 1 else 'ies'} ambiguously (carve-out language that could not be "
            f"reliably classified): {labels}. Whether these two clauses' positions interact cannot be "
            "determined until that ambiguity is resolved."
        ),
        required_action=f"Manual review required — resolve the ambiguous {labels} carve-out language before this interaction can be evaluated.",
        matched_facts={"categories": labels},
    )


# ---------------------------------------------------------------------------
# Rule 5 — Liability treats data breach as uncapped/super-capped with no
# matching cyber liability insurance coverage established. data_breach is
# the only Liability category with a real Insurance coverage-type mapping
# (design doc S3.2 — do not generalize to categories without one, e.g.
# ip_infringement has no corresponding insurance product).
# ---------------------------------------------------------------------------

def _rule_uncapped_liability_no_cyber_insurance(decisions: Dict[str, PolicyDecision]) -> Optional[InteractionFinding]:
    liability_ct = _by_category(decisions["limitation_of_liability"])
    insurance_ct = _by_category(decisions["insurance"])
    lt = liability_ct.get("data_breach")
    it = insurance_ct.get("cyber_liability")
    if not lt or not it:
        return None
    if lt["treatment"] not in ("uncapped", "super_cap") or it["established"]:
        return None
    return InteractionFinding(
        state=ESCALATE,
        explanation=(
            f"Limitation of Liability treats data breach exposure as {lt['treatment'].replace('_', ' ')} "
            "— excluded from (or capped separately above) the general liability cap — but no cyber liability "
            "insurance coverage is established in this contract's Insurance clause. Uncapped data-breach "
            "exposure with no corresponding insurance position is a material, independently-established risk."
        ),
        required_action="Legal review required — confirm data-breach exposure is intentionally uncapped with no offsetting cyber insurance requirement.",
        matched_facts={"limitation_of_liability": lt["treatment"], "insurance": "cyber_liability not established"},
    )


# ---------------------------------------------------------------------------
# Rule 6 — Termination grants the counterparty an immediate (no notice/cure)
# non-payment termination right, while Payment Terms independently
# establishes that disputed amounts may be lawfully withheld. Uses
# PolicyDecision.interaction_facts["disputed_amounts_withholdable"] (see
# policy_engine_core.INTERACTION_FACT_REGISTRY) — the one fact this rule
# needs that has no home in payment_terms' category_treatments (which only
# ever carries "payor"/"net_days"). Termination needs no such extension:
# a "non_payment" category_treatments entry is already produced
# unconditionally by termination_policy_engine.py for every counterparty
# right, regardless of trigger_type.
# ---------------------------------------------------------------------------

def _rule_nonpayment_termination_vs_withholding(decisions: Dict[str, PolicyDecision]) -> Optional[InteractionFinding]:
    termination_ct = _by_category(decisions["termination"])
    non_payment = termination_ct.get("non_payment")
    if not non_payment or non_payment["treatment"] != "immediate":
        return None
    withholdable = decisions["payment_terms"].interaction_facts.get("disputed_amounts_withholdable")
    if withholdable is not True:
        return None
    return InteractionFinding(
        state=ESCALATE,
        explanation=(
            "Termination grants the counterparty an immediate right to terminate for non-payment, with no "
            "stated notice or cure period. Payment Terms independently establishes a right to withhold "
            "disputed amounts. A payment properly disputed and withheld under Payment Terms could trigger "
            "immediate termination under the non-payment right, since Termination states no carve-out for "
            "amounts withheld under a legitimate dispute."
        ),
        required_action="Legal review required — confirm the non-payment termination right excludes amounts properly disputed and withheld under Payment Terms.",
        matched_facts={"termination": "non_payment: immediate", "payment_terms": "disputed_amounts_withholdable: True"},
    )


# ---------------------------------------------------------------------------
# Rule 7 — SLA and Payment Terms both independently reference a service
# credit mechanism. By explicit prior design decision (sla_policy_engine.py's
# module docstring, docs/architecture/sla_adapter_design.md S7/S8),
# payment_terms.service_credit_present is deliberately presence-only and is
# never merged with SLA's own (much richer) credit mechanics during
# extraction -- this rule is exactly the reconciliation point that design
# decision anticipated. Presence-consistency depth only: this can never
# become a numeric CONFLICT check without payment_terms extracting the
# percentage/basis/cap, which it deliberately does not.
# ---------------------------------------------------------------------------

def _rule_sla_payment_credit_dependency(decisions: Dict[str, PolicyDecision]) -> Optional[InteractionFinding]:
    sla_credit = decisions["sla"].interaction_facts.get("service_credit_present")
    payment_credit = decisions["payment_terms"].interaction_facts.get("service_credit_present")
    if sla_credit is not True or payment_credit is not True:
        return None
    return InteractionFinding(
        state=REQUIRES_REVIEW,
        explanation=(
            "Both SLA and Payment Terms independently reference a service credit mechanism. SLA owns the "
            "actual service-level remedy (trigger, percentage, calculation basis, cap, exclusivity, claim "
            "deadline); Payment Terms only notices that a service credit exists in the commercial/payment "
            "context. Confirm both clauses describe one consistent mechanism, not two different ones."
        ),
        required_action="Manual review required — confirm SLA and Payment Terms describe the same service credit mechanism.",
        matched_facts={"sla": "service_credit_present: True", "payment_terms": "service_credit_present: True"},
    )


# ---------------------------------------------------------------------------
# The launch catalog — fixed order, used by evaluate() so
# interaction_decisions_json's key order is deterministic for the same
# playbook + same decisions (mirrors pa.CLAUSE_TYPES' own ordering
# contract for the twelve adapters).
# ---------------------------------------------------------------------------

LAUNCH_CATALOG = [
    InteractionRule(
        interaction_id="IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY",
        label="IP infringement: uncapped liability with indemnity exposure",
        kind=CONFLICT, ceiling_state=ESCALATE,
        participating_clause_types=("limitation_of_liability", "indemnification"),
        predicate=_rule_ip_uncapped_indemnity,
    ),
    InteractionRule(
        interaction_id="IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH",
        label="Shared risk category: uncapped liability with indemnity exposure",
        kind=CONFLICT, ceiling_state=ESCALATE,
        participating_clause_types=("limitation_of_liability", "indemnification"),
        predicate=_rule_shared_category_mismatch,
    ),
    InteractionRule(
        interaction_id="IX_INDEMNITY_WITHIN_GENERAL_CAP",
        label="Indemnification exposure rides inside the general liability cap",
        kind=DEPENDENCY, ceiling_state=ACCEPT_WITH_NOTE,
        participating_clause_types=("limitation_of_liability", "indemnification"),
        predicate=_rule_indemnity_within_general_cap,
    ),
    InteractionRule(
        interaction_id="IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY",
        label="Liability/Indemnification: ambiguous shared-category treatment",
        kind=DEPENDENCY, ceiling_state=REQUIRES_REVIEW,
        participating_clause_types=("limitation_of_liability", "indemnification"),
        predicate=_rule_category_ambiguity,
    ),
    InteractionRule(
        interaction_id="IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE",
        label="Uncapped data-breach liability with no cyber insurance",
        kind=CONFLICT, ceiling_state=ESCALATE,
        participating_clause_types=("limitation_of_liability", "insurance"),
        predicate=_rule_uncapped_liability_no_cyber_insurance,
    ),
    InteractionRule(
        interaction_id="IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING",
        label="Non-payment termination right vs. dispute withholding",
        kind=CONFLICT, ceiling_state=ESCALATE,
        participating_clause_types=("termination", "payment_terms"),
        predicate=_rule_nonpayment_termination_vs_withholding,
    ),
    InteractionRule(
        interaction_id="IX_SLA_PAYMENT_CREDIT_DEPENDENCY",
        label="SLA and Payment Terms both reference service credits",
        kind=DEPENDENCY, ceiling_state=REQUIRES_REVIEW,
        participating_clause_types=("sla", "payment_terms"),
        predicate=_rule_sla_payment_credit_dependency,
    ),
]

LAUNCH_CATALOG_IDS = tuple(r.interaction_id for r in LAUNCH_CATALOG)
