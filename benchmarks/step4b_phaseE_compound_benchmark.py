"""Step 4B Phase E -- >=150 case DEVELOPMENT compound-interaction
benchmark. >=3 applicable policies per document, drawn only from the real
12-adapter catalog and the real 7-rule interaction_rules.LAUNCH_CATALOG
(never invented interactions). Runs the real interaction engine + real
document_aggregation.aggregate_document_state.
"""
from typing import Any, Dict, List

from policy_engine_core import PolicyDecision

CLAUSE_TYPES = (
    "limitation_of_liability", "indemnification", "termination", "confidentiality",
    "assignment", "governing_law", "data_security", "ip_ownership", "insurance",
    "payment_terms", "warranties", "sla",
)

DOCUMENTS: List[Dict[str, Any]] = []


def pd(clause_type, state, category_treatments=None, interaction_facts=None, reconciliation=None, controlling_provision=None):
    return PolicyDecision(
        rule_id="TEST", clause_type=clause_type, state=state,
        contract_language="", extracted_summary="", policy_limit_summary="",
        required_action="", explanation="", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10,
        controlling_provision=controlling_provision if controlling_provision is not None else
        ({"label": f"{clause_type} clause", "excerpt": "...", "start_index": "0", "end_index": "10"} if state != "NOT_APPLICABLE" else None),
        interaction_facts=interaction_facts or {}, reconciliation=reconciliation,
    )


def ct(category, treatment, established=True):
    return {"category": category, "treatment": treatment, "cap_summary": "", "raw_excerpt": "", "established": established}


def clean(clause_type):
    return pd(clause_type, "ACCEPT")


def doc(doc_id, family, decisions, overall_risk, expected, n_interactions_fired, notes=""):
    return {"id": doc_id, "family": family, "decisions": decisions, "overall_risk": overall_risk, "mode": "cutover",
            "expected_document_state": expected, "n_interactions_fired": n_interactions_fired, "notes": notes}


def _ix_liability_indemnity(decisions):
    decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")])
    decisions["indemnification"] = pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])


def _ix_termination_payment(decisions):
    decisions["termination"] = pd("termination", "ACCEPT", [ct("non_payment", "immediate")])
    decisions["payment_terms"] = pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})


def _ix_sla_payment(decisions):
    decisions["sla"] = pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True})
    decisions["payment_terms"] = pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})


def _ix_shared_category(decisions):
    decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])
    decisions["indemnification"] = pd("indemnification", "ACCEPT", [ct("data_breach", "covered")])


def _ix_cyber_insurance(decisions):
    decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])
    decisions["insurance"] = pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", False)])


# ===========================================================================
# Bucket 1: 50 documents, exactly 3 applicable policies -- explicit
# recipes (combo and interaction setup chosen together, never decoupled by
# an independent modulo) so the interaction actually fires when intended.
# ===========================================================================
_RECIPES_3POLICY = [
    ("3-policy-liability-indemnity-interaction", ("limitation_of_liability", "indemnification", "confidentiality"), _ix_liability_indemnity, "HAS_CRITICAL_INTERACTION", 1),
    ("3-policy-termination-payment-interaction", ("termination", "payment_terms", "governing_law"), _ix_termination_payment, "HAS_CRITICAL_INTERACTION", 1),
    ("3-policy-sla-payment-dependency", ("sla", "payment_terms", "warranties"), _ix_sla_payment, "REQUIRES_REVIEW", 1),
    ("3-policy-shared-category-interaction", ("limitation_of_liability", "indemnification", "assignment"), _ix_shared_category, "HAS_CRITICAL_INTERACTION", 1),
    ("3-policy-clean", ("data_security", "ip_ownership", "governing_law"), None, "CLEAN", 0),
]
for i in range(50):
    name, combo, setup_fn, expected, n_fired = _RECIPES_3POLICY[i % len(_RECIPES_3POLICY)]
    decisions = {c: clean(c) for c in combo}
    if setup_fn:
        setup_fn(decisions)
    DOCUMENTS.append(doc(f"docE-3pol-{i:02d}", name, decisions, "low", expected, n_fired, f"combo={combo}"))

# ===========================================================================
# Bucket 2: 50 documents, 4-6 applicable policies
# ===========================================================================
_RECIPES_4_6 = [
    ("4to6-policy-liability-indemnity-plus-extra-clean", ("limitation_of_liability", "indemnification", "confidentiality", "governing_law"), _ix_liability_indemnity, "HAS_CRITICAL_INTERACTION", 1),
    ("4to6-policy-one-policy-feeds-two-interactions", ("limitation_of_liability", "indemnification", "insurance", "warranties"),
     lambda d: (d.update({
         "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")]),
         "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
         "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", False)]),
     })), "HAS_CRITICAL_INTERACTION", 2),
    ("4to6-policy-shared-participant-two-interactions", ("termination", "payment_terms", "sla", "assignment"),
     lambda d: (d.update({
         "termination": pd("termination", "ACCEPT", [ct("non_payment", "immediate")]),
         "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": True}),
         "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
     })), "HAS_CRITICAL_INTERACTION", 2),
    ("4to6-policy-sla-payment-plus-clean", ("sla", "payment_terms", "data_security", "ip_ownership", "governing_law"), _ix_sla_payment, "REQUIRES_REVIEW", 1),
    ("4to6-policy-liability-plus-termination-two-interactions", ("limitation_of_liability", "indemnification", "termination", "payment_terms"),
     lambda d: (_ix_liability_indemnity(d), _ix_termination_payment(d)), "HAS_CRITICAL_INTERACTION", 2),
    ("4to6-policy-one-unresolved-among-established", ("limitation_of_liability", "indemnification", "insurance", "termination", "sla", "payment_terms"), None, "REQUIRES_REVIEW", 0),
]
for i in range(50):
    name, combo, setup_fn, expected, n_fired = _RECIPES_4_6[i % len(_RECIPES_4_6)]
    decisions = {c: clean(c) for c in combo}
    if setup_fn:
        setup_fn(decisions)
    elif name == "4to6-policy-amendment-violation-plus-decoy":
        decisions[combo[-1]] = pd(combo[-1], "MUST_REDLINE", reconciliation="amendment_resolved")
        decisions[combo[0]] = pd(combo[0], "ACCEPT", controlling_provision={
            "label": "Recitals", "excerpt": "WHEREAS the parties...", "start_index": "0", "end_index": "10"})
    elif name == "4to6-policy-one-unresolved-among-established":
        decisions[combo[2]] = pd(combo[2], "REQUIRES_REVIEW")
    DOCUMENTS.append(doc(f"docE-4to6pol-{i:02d}", name, decisions, "low", expected, n_fired, f"combo={combo}"))

# ===========================================================================
# Bucket 3: 50 documents, 7+ applicable policies (up to all 12)
# ===========================================================================
_RECIPES_7PLUS = [
    ("7plus-policy-two-independent-interactions",
     ("limitation_of_liability", "indemnification", "termination", "payment_terms", "confidentiality", "assignment", "governing_law"),
     lambda d: (_ix_liability_indemnity(d), _ix_termination_payment(d)), "HAS_CRITICAL_INTERACTION", 2),
    ("7plus-policy-three-plus-interactions",
     ("limitation_of_liability", "indemnification", "insurance", "sla", "payment_terms", "confidentiality", "data_security"),
     lambda d: (d.update({
         "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped"), ct("data_breach", "super_cap")]),
         "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("data_breach", "covered")]),
         "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", False)]),
         "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
         "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
     })), "HAS_CRITICAL_INTERACTION", 4),  # IP + shared-category + cyber-insurance ESCALATE, plus SLA/payment REQUIRES_REVIEW -- verified directly against ixc.evaluate() before predeclaring, not assumed
    ("7plus-policy-multiple-base-violations",
     ("assignment", "governing_law", "data_security", "ip_ownership", "warranties", "confidentiality", "termination", "sla"),
     None, "HAS_POLICY_VIOLATION", 0),
    ("7plus-policy-interaction-plus-unrelated-review",
     ("limitation_of_liability", "indemnification", "insurance", "assignment", "governing_law", "data_security", "warranties"),
     lambda d: (_ix_cyber_insurance(d), d.update({"warranties": pd("warranties", "REQUIRES_REVIEW")})), "HAS_CRITICAL_INTERACTION", 1),
    ("7plus-policy-not-applicable-plus-violation",
     ("confidentiality", "assignment", "governing_law", "data_security", "ip_ownership", "warranties", "termination", "sla"),
     None, "HAS_POLICY_VIOLATION", 0),
    ("7plus-policy-evaluation-error",
     ("limitation_of_liability", "indemnification", "termination", "confidentiality", "assignment", "governing_law", "data_security"),
     None, "REQUIRES_REVIEW", 0),
    ("7plus-policy-all-twelve-clean",
     CLAUSE_TYPES, None, "CLEAN", 0),
]
for i in range(50):
    name, combo, setup_fn, expected, n_fired = _RECIPES_7PLUS[i % len(_RECIPES_7PLUS)]
    decisions = {c: clean(c) for c in combo}
    if setup_fn:
        setup_fn(decisions)
    elif name == "7plus-policy-multiple-base-violations":
        decisions[combo[0]] = pd(combo[0], "PROHIBITED")
        decisions[combo[1]] = pd(combo[1], "MUST_REDLINE")
    elif name == "7plus-policy-not-applicable-plus-violation":
        decisions[combo[0]] = pd(combo[0], "NOT_APPLICABLE")
        decisions[combo[1]] = pd(combo[1], "NOT_APPLICABLE")
        decisions[combo[2]] = pd(combo[2], "ESCALATE")
    elif name == "7plus-policy-evaluation-error":
        decisions[combo[0]] = pd(combo[0], "EVALUATION_ERROR")
    overall_risk = "low"
    if i % 11 == 0 and name == "7plus-policy-all-twelve-clean":
        overall_risk = "high"
        expected = "CLEAN_LEGACY_ATTENTION"
    DOCUMENTS.append(doc(f"docE-7pluspol-{i:02d}", name, decisions, overall_risk,
                          expected, n_fired, f"{len(combo)}-policy document, combo={combo}"))
