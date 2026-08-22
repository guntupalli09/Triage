"""Step 4B document-aggregation DEVELOPMENT benchmark, >=100 cases.

Tests document_aggregation.aggregate_document_state directly (a pure
function over already-persisted Contract fields), AND separately measures
PRE false-clean behavior of what production actually exposes TODAY on the
same fixtures -- current dashboard/listing logic is exactly
"overall_risk == 'high'" (main.py:1203, :1231), nothing else. See
artifacts/step4b/document_aggregation_dev_benchmark_report.md.
"""
from typing import Any, Dict, List, Optional

CASES: List[Dict[str, Any]] = []


def pdec(state: str) -> Dict[str, Any]:
    return {"state": state}


def idec(state: str) -> Dict[str, Any]:
    return {"state": state}


def case(cid: str, family: str, overall_risk: Optional[str],
         policy_decisions: Optional[Dict[str, Dict]], interaction_decisions: Optional[Dict[str, Dict]],
         mode: str, expected_document_state: str, notes: str = "") -> Dict[str, Any]:
    return {
        "id": cid, "family": family, "overall_risk": overall_risk,
        "policy_decisions": policy_decisions, "interaction_decisions": interaction_decisions,
        "mode": mode, "expected_document_state": expected_document_state, "notes": notes,
    }


CLAUSES = ["limitation_of_liability", "indemnification", "payment_terms", "termination",
           "insurance", "sla", "confidentiality", "ip", "data_security", "governing_law",
           "assignment", "non_compete"]
VIOLATION_STATES = ["PROHIBITED", "MUST_REDLINE", "ESCALATE", "NEGOTIATE"]
CLEAN_STATES = ["ACCEPT", "ACCEPT_WITH_NOTE", "NOT_APPLICABLE"]
INTERACTION_IDS = [
    "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY", "IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH",
    "IX_INDEMNITY_WITHIN_GENERAL_CAP", "IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY",
    "IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE", "IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING",
    "IX_SLA_PAYMENT_CREDIT_DEPENDENCY",
]

# --- Family: clean legacy + clean policy (cutover) ---
for i, ov in enumerate(("low", "medium")):
    CASES.append(case(f"agg-clean-legacy-clean-policy-{i}", "clean-legacy-clean-policy", ov,
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS},
                       "cutover", "CLEAN"))

# --- Family: clean legacy + policy violation (cutover) ---
for i, (ov, vs) in enumerate([("low", "PROHIBITED"), ("low", "MUST_REDLINE"), ("medium", "ESCALATE"), ("low", "NEGOTIATE")]):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["indemnification"] = pdec(vs)
    CASES.append(case(f"agg-clean-legacy-policy-violation-{i}", "clean-legacy-policy-violation", ov,
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS},
                       "cutover", "HAS_POLICY_VIOLATION",
                       "the central false-clean scenario: legacy risk says nothing is wrong, deterministic policy layer disagrees"))

# --- Family: clean legacy + interaction violation (cutover) ---
for i in range(4):
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix[INTERACTION_IDS[i]] = idec("ESCALATE")
    CASES.append(case(f"agg-clean-legacy-interaction-violation-{i}", "clean-legacy-interaction-violation", "low",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, ix, "cutover", "HAS_CRITICAL_INTERACTION"))

# --- Family: clean legacy + policy REQUIRES_REVIEW ---
for i, ov in enumerate(("low", "medium")):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["sla"] = pdec("REQUIRES_REVIEW")
    CASES.append(case(f"agg-clean-legacy-policy-review-{i}", "clean-legacy-policy-review", ov,
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "REQUIRES_REVIEW"))

# --- Family: clean legacy + conflicting/unresolved policy evidence (modeled as REQUIRES_REVIEW policy state) ---
for i in range(3):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["payment_terms"] = pdec("REQUIRES_REVIEW")
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix["IX_SLA_PAYMENT_CREDIT_DEPENDENCY"] = idec("INSUFFICIENT_FACTS")
    CASES.append(case(f"agg-clean-legacy-conflicting-evidence-{i}", "clean-legacy-conflicting-policy-evidence", "low",
                       pd, ix, "cutover", "REQUIRES_REVIEW"))

# --- Family: high legacy risk + policy clean ---
for i in range(3):
    CASES.append(case(f"agg-high-legacy-policy-clean-{i}", "high-legacy-policy-clean", "high",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS},
                       "cutover", "CLEAN_LEGACY_ATTENTION",
                       "policy layer clean does not erase a legacy high-risk signal; must not look SAFER than pre-Step-4B"))

# --- Family: high legacy risk + policy NOT_APPLICABLE (whole document out of scope for the playbook) ---
for i in range(3):
    CASES.append(case(f"agg-high-legacy-policy-na-{i}", "high-legacy-policy-not-applicable", "high",
                       {c: pdec("NOT_APPLICABLE") for c in CLAUSES[:6]}, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS},
                       "cutover", "CLEAN_LEGACY_ATTENTION"))

# --- Family: multiple policy violations ---
for i in range(4):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["indemnification"] = pdec("PROHIBITED")
    pd["termination"] = pdec("ESCALATE")
    CASES.append(case(f"agg-multiple-policy-violations-{i}", "multiple-policy-violations", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "HAS_POLICY_VIOLATION"))

# --- Family: multiple interactions ---
for i in range(3):
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix["IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"] = idec("ESCALATE")
    ix["IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE"] = idec("ESCALATE")
    CASES.append(case(f"agg-multiple-interactions-{i}", "multiple-interactions", "low",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, ix, "cutover", "HAS_CRITICAL_INTERACTION"))

# --- Family: one critical finding hidden among many clean findings ---
for i in range(5):
    pd = {c: pdec("ACCEPT") for c in CLAUSES}
    pd[CLAUSES[i]] = pdec("PROHIBITED")
    CASES.append(case(f"agg-hidden-among-clean-{i}", "one-critical-hidden-among-many-clean", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "HAS_POLICY_VIOLATION",
                       "12-adapter-scale document where 11 of 12 policies are clean -- the one violation must not be diluted/averaged away"))

# --- Family: shadow mode (structurally unreachable interaction/violation paths beyond legacy liability) ---
for i, ov in enumerate(("low", "medium", "high")):
    CASES.append(case(f"agg-shadow-clean-{i}", "shadow-mode", ov,
                       {"limitation_of_liability": pdec("ACCEPT")}, None, "shadow",
                       "CLEAN_LEGACY_ATTENTION" if ov == "high" else "CLEAN"))
CASES.append(case("agg-shadow-legacy-liability-violation", "shadow-mode", "low",
                   {"limitation_of_liability": pdec("PROHIBITED")}, None, "shadow", "HAS_POLICY_VIOLATION",
                   "shadow mode still runs the single legacy liability decision as the user-visible policy_decisions -- this remains reachable even though the 12-adapter layer and interaction engine are not"))
CASES.append(case("agg-shadow-no-playbook", "shadow-mode", "low", None, None, "shadow", "CLEAN",
                   "shadow mode with no playbook at all -- policy_decisions is None but mode != cutover, so CONFIGURATION_UNRESOLVED does not apply (that state is cutover-specific by design)"))

# --- Family: legacy mode (same reachability as shadow) ---
for i, ov in enumerate(("low", "high")):
    CASES.append(case(f"agg-legacy-mode-{i}", "legacy-mode", ov,
                       {"limitation_of_liability": pdec("ACCEPT")}, None, "legacy",
                       "CLEAN_LEGACY_ATTENTION" if ov == "high" else "CLEAN"))

# --- Family: cutover mode, no playbook resolved (CONFIGURATION_UNRESOLVED) ---
for i, ov in enumerate(("low", "high")):
    CASES.append(case(f"agg-cutover-no-playbook-{i}", "cutover-configuration-unresolved", ov,
                       None, None, "cutover", "CONFIGURATION_UNRESOLVED"))

# --- Family: precedence ordering -- interaction beats policy violation beats review beats config-unresolved beats legacy-high ---
CASES.append(case("agg-precedence-interaction-over-policy", "precedence", "low",
                   {"indemnification": pdec("PROHIBITED")},
                   {"IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY": idec("ESCALATE")}, "cutover",
                   "HAS_CRITICAL_INTERACTION", "both a policy violation and a critical interaction present -- interaction takes precedence per the spec's ordering"))
CASES.append(case("agg-precedence-policy-over-review", "precedence", "low",
                   {"indemnification": pdec("PROHIBITED"), "sla": pdec("REQUIRES_REVIEW")},
                   {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "HAS_POLICY_VIOLATION"))
CASES.append(case("agg-precedence-review-over-legacy-high", "precedence", "high",
                   {"sla": pdec("REQUIRES_REVIEW")}, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS},
                   "cutover", "REQUIRES_REVIEW"))

# --- Family: EVALUATION_ERROR on an interaction must not be silently dropped ---
for i in range(3):
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix["IX_SLA_PAYMENT_CREDIT_DEPENDENCY"] = idec("EVALUATION_ERROR")
    CASES.append(case(f"agg-interaction-evaluation-error-{i}", "interaction-evaluation-error", "low",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, ix, "cutover", "REQUIRES_REVIEW",
                       "an EVALUATION_ERROR interaction is not clean -- must surface as REQUIRES_REVIEW, not be silently ignored as if untriggered"))

# --- Family: INSUFFICIENT_FACTS interaction alone (no violation, no ESCALATE) ---
for i in range(3):
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix["IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING"] = idec("INSUFFICIENT_FACTS")
    CASES.append(case(f"agg-interaction-insufficient-facts-{i}", "interaction-insufficient-facts", "low",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, ix, "cutover", "REQUIRES_REVIEW"))

# --- Family: interaction REQUIRES_REVIEW ceiling (Rule 4/7 style) ---
for i in range(3):
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix["IX_LIABILITY_INDEMNITY_CATEGORY_AMBIGUITY"] = idec("REQUIRES_REVIEW")
    CASES.append(case(f"agg-interaction-requires-review-{i}", "interaction-requires-review", "low",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, ix, "cutover", "REQUIRES_REVIEW"))

# --- Family: interaction ACCEPT_WITH_NOTE (Rule 3 style) is informational only, not a violation or review trigger ---
for i in range(3):
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix["IX_INDEMNITY_WITHIN_GENERAL_CAP"] = idec("ACCEPT_WITH_NOTE")
    CASES.append(case(f"agg-interaction-accept-with-note-{i}", "interaction-accept-with-note", "low",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, ix, "cutover", "CLEAN",
                       "ACCEPT_WITH_NOTE is Rule 3's own ceiling (informational DEPENDENCY, not a conflict) -- must not be conflated with the ESCALATE/REQUIRES_REVIEW states that DO carry document-level weight"))

# --- Family: policy decision ACCEPT_WITH_NOTE alone is clean ---
for i in range(3):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["insurance"] = pdec("ACCEPT_WITH_NOTE")
    CASES.append(case(f"agg-policy-accept-with-note-{i}", "policy-accept-with-note", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "CLEAN"))

# --- Family: policy decision NOT_APPLICABLE alone (never evaluated) is clean, not a review trigger ---
for i in range(3):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["non_compete"] = pdec("NOT_APPLICABLE")
    CASES.append(case(f"agg-policy-not-applicable-{i}", "policy-not-applicable", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "CLEAN",
                       "NOT_APPLICABLE is correctly not-evaluated, never itself a review trigger -- distinct from REQUIRES_REVIEW / EVALUATION_ERROR"))

# --- Family: policy decision EVALUATION_ERROR alone must not be silently dropped ---
for i in range(3):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["governing_law"] = pdec("EVALUATION_ERROR")
    CASES.append(case(f"agg-policy-evaluation-error-{i}", "policy-evaluation-error", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "REQUIRES_REVIEW",
                       "EVALUATION_ERROR is not in the violation-state set, but is also not clean -- must not disappear"))

# --- Family: empty dicts vs None -- must be handled identically (both mean 'nothing material found'), not crash ---
CASES.append(case("agg-empty-dict-policy", "empty-vs-none", "low", {}, {}, "cutover", "CLEAN"))
CASES.append(case("agg-none-policy-shadow", "empty-vs-none", "low", None, None, "shadow", "CLEAN"))

# --- Family: compound -- both a violation AND a review-state present simultaneously ---
for i in range(3):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["indemnification"] = pdec("MUST_REDLINE")
    pd["sla"] = pdec("REQUIRES_REVIEW")
    CASES.append(case(f"agg-compound-violation-and-review-{i}", "compound-violation-and-review", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "HAS_POLICY_VIOLATION"))

# --- Family: dashboard/listing safety negative controls -- legacy overall_risk=low with each violation state individually ---
for i, vs in enumerate(VIOLATION_STATES):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["confidentiality"] = pdec(vs)
    CASES.append(case(f"agg-listing-safety-violation-{i}", "dashboard-listing-safety", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "HAS_POLICY_VIOLATION",
                       f"listing-safety probe: overall_risk=low with confidentiality={vs} must not be filterable-out of every attention queue"))

# --- Family: dashboard/listing safety -- interaction ESCALATE with legacy overall_risk=low ---
for i in range(3):
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix[INTERACTION_IDS[i + 2]] = idec("ESCALATE")
    CASES.append(case(f"agg-listing-safety-interaction-{i}", "dashboard-listing-safety", "low",
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, ix, "cutover", "HAS_CRITICAL_INTERACTION",
                       "listing-safety probe: a critical interaction with overall_risk=low must not disappear from every attention queue"))

# --- Family: all 12 adapters clean, all 7 interactions NOT_TRIGGERED (full-scale clean document) ---
for i, ov in enumerate(("low", "medium")):
    CASES.append(case(f"agg-full-scale-clean-{i}", "full-scale-clean", ov,
                       {c: pdec("ACCEPT") for c in CLAUSES}, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS},
                       "cutover", "CLEAN"))

# --- Family: full-scale document, violation buried in the last adapter alphabetically/positionally ---
for i, clause in enumerate(CLAUSES):
    pd = {c: pdec("ACCEPT") for c in CLAUSES}
    pd[clause] = pdec("ESCALATE")
    CASES.append(case(f"agg-full-scale-violation-position-{i}", "full-scale-violation-position-independence", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "HAS_POLICY_VIOLATION",
                       "violation must be found regardless of which of the 12 adapters (dict iteration order) carries it"))

# --- Family: shadow mode with legacy liability REQUIRES_REVIEW (reachable even in shadow) ---
for i in range(2):
    CASES.append(case(f"agg-shadow-legacy-liability-review-{i}", "shadow-mode", "low",
                       {"limitation_of_liability": pdec("REQUIRES_REVIEW")}, None, "shadow", "REQUIRES_REVIEW"))

# --- Family: cutover, policy_decisions present but empty dict (playbook resolved, zero clause types matched) ---
for i, ov in enumerate(("low", "high")):
    CASES.append(case(f"agg-cutover-empty-policy-decisions-{i}", "cutover-empty-policy-decisions", ov,
                       {}, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover",
                       "CLEAN_LEGACY_ATTENTION" if ov == "high" else "CLEAN",
                       "empty dict (not None) means the playbook WAS resolved but matched nothing -- distinct from CONFIGURATION_UNRESOLVED, which requires policy_decisions is None"))

# --- Family: overall_risk missing/None entirely (analysis not yet completed edge case) ---
for i in range(2):
    CASES.append(case(f"agg-overall-risk-none-{i}", "overall-risk-none", None,
                       {c: pdec("ACCEPT") for c in CLAUSES[:6]}, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS},
                       "cutover", "CLEAN", "None overall_risk must not be treated as 'high' or crash the comparison"))

# --- Family: multiple critical interactions plus a policy violation simultaneously (compound, worst case) ---
for i in range(3):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["termination"] = pdec("PROHIBITED")
    ix = {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}
    ix["IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"] = idec("ESCALATE")
    ix["IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE"] = idec("ESCALATE")
    CASES.append(case(f"agg-compound-worst-case-{i}", "compound-multiple-critical-plus-violation", "low",
                       pd, ix, "cutover", "HAS_CRITICAL_INTERACTION"))

# --- Family: policy NEGOTIATE state specifically (weakest violation state) still counts as a violation, not review ---
for i in range(3):
    pd = {c: pdec("ACCEPT") for c in CLAUSES[:6]}
    pd["assignment"] = pdec("NEGOTIATE")
    CASES.append(case(f"agg-policy-negotiate-{i}", "policy-negotiate-state", "low",
                       pd, {r: idec("NOT_TRIGGERED") for r in INTERACTION_IDS}, "cutover", "HAS_POLICY_VIOLATION",
                       "NEGOTIATE must not be miscategorized as merely REQUIRES_REVIEW -- it is a policy position taken, a violation of the playbook's preferred term"))

print(f"[step4b_document_aggregation_dev_benchmark] {len(CASES)} cases loaded") if __name__ == "__main__" else None
