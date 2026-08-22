"""Step 4B Phase D -- >=150 case DEVELOPMENT aggregation-stress benchmark.
Fresh documents (not reused from Phase A), attacking the six-state
aggregation model under highly imbalanced finding mixtures -- one signal
buried among many clean findings, multiple simultaneous signals, and
mixed legacy/deterministic signals. Runs the REAL interaction engine +
REAL document_aggregation.aggregate_document_state, never reimplemented.
"""
from typing import Any, Dict, List, Optional

from policy_engine_core import PolicyDecision

CLAUSE_TYPES = (
    "limitation_of_liability", "indemnification", "termination", "confidentiality",
    "assignment", "governing_law", "data_security", "ip_ownership", "insurance",
    "payment_terms", "warranties", "sla",
)
INTERACTION_CLAUSE_TYPES = ("limitation_of_liability", "indemnification", "insurance", "termination", "payment_terms", "sla")

DOCUMENTS: List[Dict[str, Any]] = []


def pd(clause_type: str, state: str, category_treatments=None, interaction_facts=None,
       reconciliation: Optional[str] = None) -> PolicyDecision:
    return PolicyDecision(
        rule_id="TEST", clause_type=clause_type, state=state,
        contract_language="", extracted_summary="", policy_limit_summary="",
        required_action="", explanation="", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10,
        controlling_provision=({"label": f"{clause_type} clause", "excerpt": "...", "start_index": "0", "end_index": "10"} if state != "NOT_APPLICABLE" else None),
        interaction_facts=interaction_facts or {}, reconciliation=reconciliation,
    )


def ct(category, treatment, established=True):
    return {"category": category, "treatment": treatment, "cap_summary": "", "raw_excerpt": "", "established": established}


def clean(clause_type: str) -> PolicyDecision:
    return pd(clause_type, "ACCEPT")


def doc(doc_id, family, decisions, overall_risk, mode, expected, notes=""):
    return {"id": doc_id, "family": family, "decisions": decisions, "overall_risk": overall_risk,
            "mode": mode, "expected_document_state": expected, "notes": notes}


# All 6 interaction-participating clause types present + established, plus
# the other 6, gives every document here a fully-resolved interaction
# surface (no INSUFFICIENT_FACTS noise from uncovered clause types) -- so
# imbalance is entirely about clean-vs-signal count, not coverage gaps
# (that axis was Phase A's focus).
_FULL_CLEAN = {ct_: clean(ct_) for ct_ in CLAUSE_TYPES}

# Family 1: 1 violation + 20 clean findings (12 real clause types is our
# ceiling -- "20 clean findings" is modeled as the full 12-clause set
# minus the 1 signal, all ACCEPT, which is the maximum clean-finding count
# this catalog supports; documented explicitly, not silently downsized).
for i, target in enumerate(CLAUSE_TYPES):
    decisions = dict(_FULL_CLEAN)
    decisions[target] = pd(target, "PROHIBITED")
    DOCUMENTS.append(doc(f"docD-1violation-{i}", "1-violation-among-max-clean", decisions, "low", "cutover",
                          "HAS_POLICY_VIOLATION", f"signal on {target}, 11 other clause types clean"))

# Family 2: 1 REQUIRES_REVIEW + rest clean
for i, target in enumerate(CLAUSE_TYPES):
    decisions = dict(_FULL_CLEAN)
    decisions[target] = pd(target, "REQUIRES_REVIEW")
    DOCUMENTS.append(doc(f"docD-1review-{i}", "1-review-among-max-clean", decisions, "low", "cutover",
                          "REQUIRES_REVIEW", f"signal on {target}, 11 other clause types clean"))

# Family 3: 1 EVALUATION_ERROR + rest clean
for i, target in enumerate(CLAUSE_TYPES):
    decisions = dict(_FULL_CLEAN)
    decisions[target] = pd(target, "EVALUATION_ERROR")
    DOCUMENTS.append(doc(f"docD-1error-{i}", "1-evaluation-error-among-max-clean", decisions, "low", "cutover",
                          "REQUIRES_REVIEW", f"signal on {target}, 11 other clause types clean"))

# Family 4: 1 critical interaction + rest clean (rotate through all 5
# ESCALATE-capable rules)
_ESCALATE_SETUPS = [
    ("limitation_of_liability", "indemnification", [ct("ip_infringement", "uncapped")], [ct("ip_infringement", "covered")], None, None),
    ("limitation_of_liability", "indemnification", [ct("data_breach", "super_cap")], [ct("data_breach", "covered")], None, None),
    ("limitation_of_liability", "insurance", [ct("data_breach", "uncapped")], [ct("cyber_liability", "not_addressed", False)], None, None),
    ("termination", "payment_terms", [ct("non_payment", "immediate")], None, None, {"disputed_amounts_withholdable": True}),
]
for i, (ct1, ct2, cats1, cats2, facts1, facts2) in enumerate(_ESCALATE_SETUPS * 2):
    decisions = dict(_FULL_CLEAN)
    decisions[ct1] = pd(ct1, "ACCEPT", cats1, facts1)
    decisions[ct2] = pd(ct2, "ACCEPT", cats2, facts2)
    DOCUMENTS.append(doc(f"docD-1interaction-{i}", "1-critical-interaction-among-max-clean", decisions, "low", "cutover",
                          "HAS_CRITICAL_INTERACTION", f"interaction via {ct1}/{ct2}, everything else clean"))

# Family 5: configuration-unresolved + many clean findings (cutover, policy_decisions=None entirely)
for i in range(4):
    DOCUMENTS.append(doc(f"docD-config-unresolved-{i}", "configuration-unresolved-among-clean", None, "low" if i % 2 == 0 else "high", "cutover",
                          "CONFIGURATION_UNRESOLVED", "no playbook resolved at all -- distinct from 'many clean'"))

# Family 6: many NOT_APPLICABLE + one violation
for i, target in enumerate(CLAUSE_TYPES):
    decisions = {ct_: pd(ct_, "NOT_APPLICABLE") for ct_ in CLAUSE_TYPES if ct_ != target}
    decisions[target] = pd(target, "MUST_REDLINE")
    DOCUMENTS.append(doc(f"docD-na-plus-violation-{i}", "many-not-applicable-plus-one-violation", decisions, "low", "cutover",
                          "HAS_POLICY_VIOLATION", f"11 NOT_APPLICABLE, 1 violation on {target}"))

# Family 7: many NOT_APPLICABLE + one unresolved
for i, target in enumerate(CLAUSE_TYPES):
    decisions = {ct_: pd(ct_, "NOT_APPLICABLE") for ct_ in CLAUSE_TYPES if ct_ != target}
    decisions[target] = pd(target, "REQUIRES_REVIEW")
    DOCUMENTS.append(doc(f"docD-na-plus-review-{i}", "many-not-applicable-plus-one-unresolved", decisions, "low", "cutover",
                          "REQUIRES_REVIEW", f"11 NOT_APPLICABLE, 1 unresolved on {target}"))

# Family 8: multiple violations (2-4 simultaneously)
for i in range(8):
    n_violations = 2 + (i % 3)
    targets = CLAUSE_TYPES[i % 6: i % 6 + n_violations] or CLAUSE_TYPES[:n_violations]
    decisions = dict(_FULL_CLEAN)
    for t in targets:
        decisions[t] = pd(t, "PROHIBITED")
    DOCUMENTS.append(doc(f"docD-multi-violation-{i}", "multiple-violations", decisions, "low", "cutover",
                          "HAS_POLICY_VIOLATION", f"{n_violations} simultaneous violations"))

# Family 9: multiple reviews
for i in range(8):
    n_reviews = 2 + (i % 3)
    targets = CLAUSE_TYPES[i % 6: i % 6 + n_reviews] or CLAUSE_TYPES[:n_reviews]
    decisions = dict(_FULL_CLEAN)
    for t in targets:
        decisions[t] = pd(t, "REQUIRES_REVIEW")
    DOCUMENTS.append(doc(f"docD-multi-review-{i}", "multiple-reviews", decisions, "low", "cutover",
                          "REQUIRES_REVIEW", f"{n_reviews} simultaneous reviews"))

# Family 10: multiple interactions simultaneously
for i in range(6):
    decisions = dict(_FULL_CLEAN)
    decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped"), ct("data_breach", "uncapped")])
    decisions["indemnification"] = pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered"), ct("data_breach", "covered")])
    decisions["insurance"] = pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", False)])
    DOCUMENTS.append(doc(f"docD-multi-interaction-{i}", "multiple-interactions", decisions, "low", "cutover",
                          "HAS_CRITICAL_INTERACTION", "3 rules (IP, shared-category, cyber-insurance) all fire at once"))

# Family 11: violation + review together
for i in range(6):
    decisions = dict(_FULL_CLEAN)
    decisions["indemnification"] = pd("indemnification", "MUST_REDLINE")
    decisions["sla"] = pd("sla", "REQUIRES_REVIEW")
    DOCUMENTS.append(doc(f"docD-violation-plus-review-{i}", "violation-plus-review", decisions, "low", "cutover",
                          "HAS_POLICY_VIOLATION", "violation must win precedence over review"))

# Family 12: violation + evaluation error
for i in range(6):
    decisions = dict(_FULL_CLEAN)
    decisions["indemnification"] = pd("indemnification", "PROHIBITED")
    decisions["warranties"] = pd("warranties", "EVALUATION_ERROR")
    DOCUMENTS.append(doc(f"docD-violation-plus-error-{i}", "violation-plus-evaluation-error", decisions, "low", "cutover",
                          "HAS_POLICY_VIOLATION", "violation must win precedence over evaluation error"))

# Family 13: critical interaction + review together
for i in range(6):
    decisions = dict(_FULL_CLEAN)
    decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")])
    decisions["indemnification"] = pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])
    decisions["governing_law"] = pd("governing_law", "REQUIRES_REVIEW")
    DOCUMENTS.append(doc(f"docD-interaction-plus-review-{i}", "critical-interaction-plus-review", decisions, "low", "cutover",
                          "HAS_CRITICAL_INTERACTION", "interaction must win precedence over review"))

# Family 14: critical interaction + violation together
for i in range(6):
    decisions = dict(_FULL_CLEAN)
    decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")])
    decisions["indemnification"] = pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])
    decisions["warranties"] = pd("warranties", "PROHIBITED")
    DOCUMENTS.append(doc(f"docD-interaction-plus-violation-{i}", "critical-interaction-plus-violation", decisions, "low", "cutover",
                          "HAS_CRITICAL_INTERACTION", "interaction must win precedence over base violation, per the documented precedence order"))

# Family 15: clean legacy + deterministic violation (the central false-clean scenario)
for i in range(6):
    decisions = dict(_FULL_CLEAN)
    decisions["confidentiality"] = pd("confidentiality", "ESCALATE")
    DOCUMENTS.append(doc(f"docD-cleanlegacy-detviolation-{i}", "clean-legacy-plus-deterministic-violation", decisions, "low", "cutover",
                          "HAS_POLICY_VIOLATION", "overall_risk=low must not suppress the deterministic violation"))

# Family 16: high legacy + deterministic clean
for i in range(6):
    DOCUMENTS.append(doc(f"docD-highlegacy-detclean-{i}", "high-legacy-plus-deterministic-clean", dict(_FULL_CLEAN), "high", "cutover",
                          "CLEAN_LEGACY_ATTENTION", "deterministic layer clean does not erase legacy-high attention"))

# Family 17: low legacy + deterministic critical
for i in range(6):
    decisions = dict(_FULL_CLEAN)
    decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])
    decisions["insurance"] = pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", False)])
    DOCUMENTS.append(doc(f"docD-lowlegacy-detcritical-{i}", "low-legacy-plus-deterministic-critical", decisions, "low", "cutover",
                          "HAS_CRITICAL_INTERACTION", "overall_risk=low must not suppress a critical deterministic interaction"))

# Family 18: mixed policy coverage (some clause types entirely absent from
# policy_decisions, not merely NOT_APPLICABLE -- the Phase A distinction)
for i in range(8):
    covered = CLAUSE_TYPES[:4 + (i % 4)]
    decisions = {ct_: clean(ct_) for ct_ in covered}
    DOCUMENTS.append(doc(f"docD-mixed-coverage-{i}", "mixed-policy-coverage", decisions, "low", "cutover",
                          "CLEAN", f"only {len(covered)}/12 clause types covered by this playbook, all clean"))

# Family 19: interaction participant genuinely absent (not covered by playbook at all)
for i in range(4):
    decisions = {"limitation_of_liability": clean("limitation_of_liability"), "indemnification": clean("indemnification")}
    DOCUMENTS.append(doc(f"docD-participant-absent-{i}", "interaction-participant-genuinely-absent", decisions, "low", "cutover",
                          "CLEAN", "insurance/termination/payment_terms/sla never covered by this playbook -- Phase A fix must hold here too"))

# Family 20: interaction participant unresolved (covered, but REQUIRES_REVIEW)
for i in range(4):
    decisions = dict(_FULL_CLEAN)
    decisions["insurance"] = pd("insurance", "REQUIRES_REVIEW")
    DOCUMENTS.append(doc(f"docD-participant-unresolved-{i}", "interaction-participant-unresolved", decisions, "low", "cutover",
                          "REQUIRES_REVIEW", "insurance IS covered but unresolved -- genuine uncertainty must still surface"))

# Family 21: multiple non-participating interaction rules simultaneously (variety of coverage gaps)
for i in range(6):
    covered = ["limitation_of_liability", "indemnification", "confidentiality", "assignment"]
    decisions = {ct_: clean(ct_) for ct_ in covered}
    DOCUMENTS.append(doc(f"docD-multi-nonparticipating-{i}", "multiple-non-participating-interaction-rules", decisions, "low", "cutover",
                          "CLEAN", "5 of 7 interaction rules have a genuinely-uncovered participant (insurance/termination/payment_terms/sla) -- none should escalate"))
