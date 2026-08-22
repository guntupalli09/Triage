"""Step 4B Phase A — >=150 case multi-policy DOCUMENT-level development
benchmark. DEVELOPMENT evidence -- may be iterated against.

Unlike Phase 4 (pairwise interaction-predicate correctness) and the
document-aggregation benchmark (aggregation logic in isolation), this
corpus builds realistic MULTI-POLICY documents -- 3 to 12 simultaneously
applicable policies, drawn only from the actual 12-adapter catalog
(playbook_authoring.CLAUSE_TYPES) -- and runs each one through the REAL
interaction engine (interaction_engine_core.evaluate against the full
7-rule interaction_rules.LAUNCH_CATALOG) and the REAL document aggregation
function (document_aggregation.aggregate_document_state), never a
reimplementation of either. Ground truth is predeclared by hand, per
family, using the already-validated six-state precedence model -- never
derived by calling the function under test.

Central hard invariant under test: a clean policy decision must never
neutralize another policy's violation, another policy's REQUIRES_REVIEW,
an interaction finding, an evaluation error, or a configuration problem --
regardless of how many clean policies surround it.
"""
from typing import Any, Dict, List, Optional

from policy_engine_core import PolicyDecision

# The actual 12-adapter catalog -- do not invent unsupported policies.
CLAUSE_TYPES = (
    "limitation_of_liability", "indemnification", "termination", "confidentiality",
    "assignment", "governing_law", "data_security", "ip_ownership", "insurance",
    "payment_terms", "warranties", "sla",
)
# The 6 clause types that actually participate in at least one of the 7
# launch-catalog interaction rules (interaction_rules.py) -- the other 6
# are real, independently-evaluated policies with no interaction wiring.
INTERACTION_CLAUSE_TYPES = ("limitation_of_liability", "indemnification", "insurance", "termination", "payment_terms", "sla")

DOCUMENTS: List[Dict[str, Any]] = []


def pd(clause_type: str, state: str, category_treatments=None, interaction_facts=None,
       reconciliation: Optional[str] = None, controlling_provision: Optional[Dict] = None) -> PolicyDecision:
    return PolicyDecision(
        rule_id="TEST", clause_type=clause_type, state=state,
        contract_language="", extracted_summary="", policy_limit_summary="",
        required_action="", explanation="", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10,
        controlling_provision=controlling_provision if controlling_provision is not None else
        ({"label": f"{clause_type} clause", "excerpt": "...evidence...", "start_index": "0", "end_index": "10"} if state != "NOT_APPLICABLE" else None),
        interaction_facts=interaction_facts or {},
        reconciliation=reconciliation,
    )


def ct(category, treatment, established=True):
    return {"category": category, "treatment": treatment, "cap_summary": "", "raw_excerpt": "", "established": established}


def clean(clause_type: str) -> PolicyDecision:
    return pd(clause_type, "ACCEPT")


def doc(doc_id: str, family: str, decisions: Dict[str, PolicyDecision], overall_risk: str,
        mode: str, expected_document_state: str, notes: str = "") -> Dict[str, Any]:
    return {
        "id": doc_id, "family": family, "decisions": decisions, "overall_risk": overall_risk,
        "mode": mode, "expected_document_state": expected_document_state,
        "num_policies": len(decisions), "notes": notes,
    }


_ALL_CLEAN_NO_IX = {ct_: clean(ct_) for ct_ in CLAUSE_TYPES if ct_ not in INTERACTION_CLAUSE_TYPES}


def _pick(n: int, offset: int = 0) -> List[str]:
    """Deterministic, varying subset of the 12 clause types, `n` of them,
    rotating the starting point by `offset` so different documents in the
    same bucket cover different clause-type combinations rather than
    always the first n."""
    rotated = CLAUSE_TYPES[offset % len(CLAUSE_TYPES):] + CLAUSE_TYPES[:offset % len(CLAUSE_TYPES)]
    return list(rotated[:n])


# ===========================================================================
# Bucket 1: 50 documents, 3-4 applicable policies
# ===========================================================================
for i in range(50):
    n = 3 if i % 2 == 0 else 4
    clause_types = _pick(n, offset=i)
    decisions = {ctp: clean(ctp) for ctp in clause_types}
    family = "fully-clean-small"
    expected = "CLEAN"
    overall_risk = "low"
    if i % 5 == 1:
        # one violation among the rest clean
        target = clause_types[0]
        decisions[target] = pd(target, "PROHIBITED")
        family = "one-violation-among-clean-small"
        expected = "HAS_POLICY_VIOLATION"
    elif i % 5 == 2:
        target = clause_types[-1]
        decisions[target] = pd(target, "REQUIRES_REVIEW")
        family = "one-review-among-clean-small"
        expected = "REQUIRES_REVIEW"
    elif i % 5 == 3:
        target = clause_types[len(clause_types) // 2]
        decisions[target] = pd(target, "NOT_APPLICABLE")
        family = "not-applicable-mixed-small"
        # NOT_APPLICABLE resolves the clause type (a decision IS on
        # record), unlike a clause type never covered by the playbook at
        # all -- if `target` participates in any interaction rule, that
        # rule's participant is present-but-unsafe (genuine uncertainty,
        # not "no interaction possible"), which correctly escalates to
        # REQUIRES_REVIEW. Only truly CLEAN when the NOT_APPLICABLE clause
        # type has no interaction wiring at all.
        expected = "REQUIRES_REVIEW" if target in INTERACTION_CLAUSE_TYPES else "CLEAN"
    elif i % 5 == 4:
        target = clause_types[0]
        decisions[target] = pd(target, "EVALUATION_ERROR")
        family = "evaluation-error-among-clean-small"
        expected = "REQUIRES_REVIEW"
    DOCUMENTS.append(doc(f"docA-small-{i:02d}", family, decisions, overall_risk, "cutover", expected,
                          "clean surrounding policies must not neutralize the one material finding" if expected != "CLEAN" else ""))

# ===========================================================================
# Bucket 2: 50 documents, 5-7 applicable policies
# ===========================================================================
for i in range(50):
    n = 5 + (i % 3)
    clause_types = _pick(n, offset=i * 3)
    decisions = {ctp: clean(ctp) for ctp in clause_types}
    family = "fully-clean-medium"
    expected = "CLEAN"
    overall_risk = "low"
    bucket = i % 8
    if bucket == 1:
        decisions[clause_types[0]] = pd(clause_types[0], "MUST_REDLINE")
        family = "one-violation-among-clean-medium"
        expected = "HAS_POLICY_VIOLATION"
    elif bucket == 2:
        decisions[clause_types[1 % n]] = pd(clause_types[1 % n], "REQUIRES_REVIEW")
        family = "one-review-among-clean-medium"
        expected = "REQUIRES_REVIEW"
    elif bucket == 3 and all(x in clause_types for x in ("limitation_of_liability", "indemnification")):
        decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")])
        decisions["indemnification"] = pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])
        family = "interaction-finding-among-clean-medium"
        expected = "HAS_CRITICAL_INTERACTION"
    elif bucket == 4:
        decisions[clause_types[0]] = pd(clause_types[0], "ESCALATE", reconciliation="amendment_resolved")
        family = "amendment-resolved-violation-medium"
        expected = "HAS_POLICY_VIOLATION"
    elif bucket == 5:
        decisions[clause_types[0]] = pd(clause_types[0], "REQUIRES_REVIEW", reconciliation="unreconciled")
        family = "multiple-provisions-unreconciled-medium"
        expected = "REQUIRES_REVIEW"
    elif bucket == 6:
        decisions[clause_types[-1]] = pd(clause_types[-1], "NEGOTIATE")
        family = "negotiate-state-among-clean-medium"
        expected = "HAS_POLICY_VIOLATION"
    elif bucket == 7:
        # non-operative-text framing on a clean finding must not itself
        # create a violation
        target = clause_types[0]
        decisions[target] = pd(target, "ACCEPT", controlling_provision={
            "label": "Recitals", "excerpt": "WHEREAS the parties agree...", "start_index": "0", "end_index": "10"})
        family = "non-operative-text-framing-clean-medium"
        expected = "CLEAN"
    DOCUMENTS.append(doc(f"docA-medium-{i:02d}", family, decisions, overall_risk, "cutover", expected,
                          "one signal must survive regardless of 5-7 surrounding policies"))

# ===========================================================================
# Bucket 3: 50 documents, 8+ applicable policies (up to all 12)
# ===========================================================================
for i in range(50):
    n = 8 + (i % 5)  # 8..12
    clause_types = _pick(min(n, 12), offset=i * 5)
    decisions = {ctp: clean(ctp) for ctp in clause_types}
    family = "fully-clean-large"
    expected = "CLEAN"
    overall_risk = "low"
    bucket = i % 10
    if bucket == 1:
        decisions[clause_types[0]] = pd(clause_types[0], "PROHIBITED")
        family = "one-violation-among-20-clean-large"
        expected = "HAS_POLICY_VIOLATION"
    elif bucket == 2:
        decisions[clause_types[1]] = pd(clause_types[1], "REQUIRES_REVIEW")
        family = "one-review-among-clean-large"
        expected = "REQUIRES_REVIEW"
    elif bucket == 3 and all(x in clause_types for x in ("limitation_of_liability", "insurance")):
        decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "uncapped")])
        decisions["insurance"] = pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)])
        family = "interaction-finding-large"
        expected = "HAS_CRITICAL_INTERACTION"
    elif bucket == 4 and all(x in clause_types for x in ("termination", "payment_terms")):
        decisions["termination"] = pd("termination", "ACCEPT", [ct("non_payment", "immediate")])
        decisions["payment_terms"] = pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})
        family = "directional-interaction-large"
        expected = "HAS_CRITICAL_INTERACTION"
    elif bucket == 5 and all(x in clause_types for x in ("sla", "payment_terms")):
        decisions["sla"] = pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True})
        decisions["payment_terms"] = pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})
        family = "dependency-interaction-review-large"
        expected = "REQUIRES_REVIEW"
    elif bucket == 6:
        decisions[clause_types[0]] = pd(clause_types[0], "EVALUATION_ERROR")
        family = "evaluation-error-among-many-clean-large"
        expected = "REQUIRES_REVIEW"
    elif bucket == 7:
        # multiple distinct violations at once (compound)
        decisions[clause_types[0]] = pd(clause_types[0], "PROHIBITED")
        decisions[clause_types[1]] = pd(clause_types[1], "MUST_REDLINE")
        family = "compound-multiple-violations-large"
        expected = "HAS_POLICY_VIOLATION"
    elif bucket == 8:
        # violation + review together -- violation must win precedence
        decisions[clause_types[0]] = pd(clause_types[0], "ESCALATE")
        decisions[clause_types[1]] = pd(clause_types[1], "REQUIRES_REVIEW")
        family = "compound-violation-and-review-large"
        expected = "HAS_POLICY_VIOLATION"
    elif bucket == 9:
        # duplicate evidence: same category appearing twice on one clause's
        # category_treatments -- must resolve via the real last-wins
        # mechanism, not crash or double-count.
        target = clause_types[0]
        decisions[target] = pd(target, "ACCEPT", [ct("misc", "clean"), ct("misc", "clean")])
        family = "duplicate-evidence-large"
        expected = "CLEAN"
    DOCUMENTS.append(doc(f"docA-large-{i:02d}", family, decisions, overall_risk, "cutover", expected,
                          f"{n}-policy document; one signal must survive regardless of scale"))

# ===========================================================================
# Compound-mechanism documents (>=50 required across all buckets combined --
# counted separately here, added on top, each combining >=2 mechanisms:
# interaction + violation, amendment + review, direction + compound, etc.)
# ===========================================================================
for i in range(50):
    n = 6 + (i % 4)
    clause_types = _pick(n, offset=i * 7 + 1)
    decisions = {ctp: clean(ctp) for ctp in clause_types}
    mech = i % 6
    if mech == 0 and all(x in clause_types for x in ("limitation_of_liability", "indemnification")):
        decisions["limitation_of_liability"] = pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "uncapped")], reconciliation="amendment_resolved")
        decisions["indemnification"] = pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")])
        if len(clause_types) > 2:
            decisions[clause_types[2]] = pd(clause_types[2], "REQUIRES_REVIEW")
        family = "compound-interaction-plus-amendment-plus-review"
        expected = "HAS_CRITICAL_INTERACTION"
    elif mech == 1 and all(x in clause_types for x in ("termination", "payment_terms")):
        decisions["termination"] = pd("termination", "ACCEPT", [ct("non_payment", "immediate")])
        decisions["payment_terms"] = pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True})
        # Pick the violation target from a clause type that is NOT one of
        # the two just wired for the interaction above -- overwriting
        # either would silently destroy the interaction setup.
        violation_target = next(c for c in clause_types if c not in ("termination", "payment_terms"))
        decisions[violation_target] = pd(violation_target, "MUST_REDLINE")
        family = "compound-directional-interaction-plus-violation"
        expected = "HAS_CRITICAL_INTERACTION"
    elif mech == 2:
        decisions[clause_types[0]] = pd(clause_types[0], "REQUIRES_REVIEW", reconciliation="unreconciled")
        decisions[clause_types[1 % n]] = pd(clause_types[1 % n], "EVALUATION_ERROR")
        family = "compound-multiple-provisions-plus-evaluation-error"
        expected = "REQUIRES_REVIEW"
    elif mech == 3 and all(x in clause_types for x in ("sla", "payment_terms")):
        decisions["sla"] = pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True})
        decisions["payment_terms"] = pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True})
        decisions[clause_types[0]] = pd(clause_types[0], "PROHIBITED")
        family = "compound-dependency-interaction-plus-violation"
        expected = "HAS_POLICY_VIOLATION"
    elif mech == 4:
        decisions[clause_types[0]] = pd(clause_types[0], "ACCEPT", [ct("carveout", "unresolved")])
        na_target = clause_types[1 % n]
        decisions[na_target] = pd(na_target, "NOT_APPLICABLE")
        family = "compound-not-applicable-plus-clean"
        # Same distinction as not-applicable-mixed-small above: NOT_APPLICABLE
        # is a resolved-but-unsafe participant if na_target happens to be
        # one of the 6 interaction-wired clause types -- genuine
        # uncertainty, not "no interaction possible."
        expected = "REQUIRES_REVIEW" if na_target in INTERACTION_CLAUSE_TYPES else "CLEAN"
    else:
        decisions[clause_types[0]] = pd(clause_types[0], "PROHIBITED")
        decisions[clause_types[1 % n]] = pd(clause_types[1 % n], "REQUIRES_REVIEW")
        decisions[clause_types[2 % n]] = pd(clause_types[2 % n], "NOT_APPLICABLE")
        family = "compound-triple-mechanism"
        expected = "HAS_POLICY_VIOLATION"
    overall_risk = "high" if i % 9 == 0 else "low"
    DOCUMENTS.append(doc(f"docA-compound-{i:02d}", family, decisions, overall_risk, "cutover", expected,
                          "compound: two or more mechanisms co-present in one document"))
