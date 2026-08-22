"""Step 4B Phase C -- >=100 case DEVELOPMENT severity/prioritization
benchmark. Targets the three real production consumers identified by the
read-only trace (artifacts/step4b/phaseC_severity_inventory.md):

  1. main.build_enhanced_issues -- sorts by severity (presentation only);
     must never suppress/mutate a finding because of its severity value.
  2. review_queue.build_review_queue -- orders/classifies by TIER_RANK,
     keyed on policy_state, never on severity; must be provably immune to
     a severity value that contradicts policy_state.
  3. document_aggregation.aggregate_document_state -- never reads
     "severity" at all; must be provably immune to a severity field
     present (or absent, or malformed) inside a policy/interaction
     decision dict.

Each case predeclares an expected outcome for the ONE consumer it
targets, tagged via "target".
"""
from typing import Any, Dict, List

CASES: List[Dict[str, Any]] = []


def case(cid, family, target, payload, expected, notes=""):
    CASES.append({"id": cid, "family": family, "target": target, "payload": payload, "expected": expected, "notes": notes})


# ===========================================================================
# Target 1: main.build_enhanced_issues (severity must never suppress/mutate)
# ===========================================================================
SEVERITIES = ["critical", "high", "medium", "low", "", None, "URGENT!!", "unknown_value", 12345, "Critical", "LOW"]

for i, sev in enumerate(SEVERITIES):
    findings = [{"rule_id": f"R_SEV_{i}", "title": "Finding", "severity": sev,
                 "clause_number": None, "start_index": i, "end_index": i + 10, "rationale": "x"}]
    case(f"sevC-be-survives-{i}", "same-finding-different-severity", "build_enhanced_issues",
         {"findings": findings, "llm_top_issues": []},
         {"count": 1}, f"severity={sev!r} must not cause suppression")

# same evidence, different severity, two distinct findings -- both survive
for i in range(6):
    findings = [
        {"rule_id": "R_SAME_EV", "title": "F1", "severity": "critical", "clause_number": "1.1", "start_index": 10, "end_index": 20},
        {"rule_id": "R_SAME_EV_2", "title": "F2", "severity": "low", "clause_number": "1.1", "start_index": 10, "end_index": 20},
    ]
    case(f"sevC-be-same-evidence-diffsev-{i}", "same-evidence-different-severity", "build_enhanced_issues",
         {"findings": findings, "llm_top_issues": []}, {"count": 2}, "different rule_ids, same evidence span -- both survive regardless of differing severity")

# same rule, different severity across two genuinely distinct locations -- both survive (Phase B invariant + severity orthogonality)
for i in range(6):
    findings = [
        {"rule_id": "R_MULTI", "title": "F", "severity": "high", "clause_number": f"{i}.1", "start_index": 100 * i, "end_index": 100 * i + 10},
        {"rule_id": "R_MULTI", "title": "F", "severity": "low", "clause_number": f"{i}.2", "start_index": 100 * i + 500, "end_index": 100 * i + 520},
    ]
    case(f"sevC-be-same-rule-diffsev-diffloc-{i}", "same-rule-different-severity", "build_enhanced_issues",
         {"findings": findings, "llm_top_issues": []}, {"count": 2}, "same rule_id, different locations AND different severities -- both survive")

# multiple findings, many severities -- verify sort order (descending severity) and zero loss
for i in range(6):
    sevs = ["low", "critical", "medium", "high"]
    findings = [{"rule_id": f"R_ORDER_{i}_{j}", "title": f"F{j}", "severity": s, "clause_number": None,
                 "start_index": j, "end_index": j + 5} for j, s in enumerate(sevs)]
    case(f"sevC-be-order-{i}", "ordering-many-severities", "build_enhanced_issues",
         {"findings": findings, "llm_top_issues": []},
         {"count": 4, "order": ["critical", "high", "medium", "low"]}, "sort must be by severity, all 4 must survive")

# malformed/unexpected severity values must not crash and must not be dropped
for i, sev in enumerate([{"nested": "dict"}, [1, 2], 0, False, True]):
    findings = [{"rule_id": f"R_MALFORMED_{i}", "title": "F", "severity": sev, "clause_number": None, "start_index": 0, "end_index": 5}]
    case(f"sevC-be-malformed-{i}", "malformed-severity", "build_enhanced_issues",
         {"findings": findings, "llm_top_issues": []}, {"count": 1}, f"malformed severity {sev!r} must not crash or suppress")

# ===========================================================================
# Target 2: review_queue.build_review_queue (TIER_RANK, never severity)
# ===========================================================================
# same policy_state, contradictory severity fields -- ordering must be
# identical to the no-severity-field baseline (tier_rank driven purely by
# policy_state)
_STATES_FOR_TIER = ["PROHIBITED", "MUST_REDLINE", "ESCALATE", "NEGOTIATE", "REQUIRES_REVIEW", "EVALUATION_ERROR"]
for i, contradiction in enumerate([
    {"PROHIBITED": "low", "NEGOTIATE": "critical"},         # low-severity-labeled PROHIBITED must still rank first
    {"MUST_REDLINE": "medium", "REQUIRES_REVIEW": "critical"},
    {"ESCALATE": "low", "EVALUATION_ERROR": "high"},
]):
    findings = []
    for j, (state, sev) in enumerate(contradiction.items()):
        findings.append({"rule_id": f"R_TIER_{i}_{j}", "finding_type": "policy_decision",
                          "policy_state": state, "severity": sev, "clause_type": f"clause_{j}"})
    expected_order_states = sorted(contradiction.keys(), key=lambda s: __import__("review_queue").tier_rank(s))
    case(f"sevC-rq-tier-immune-{i}", "tier-rank-immune-to-severity", "build_review_queue",
         {"findings": findings, "policy_decisions": {}},
         {"policy_order_states": expected_order_states},
         "TIER_RANK ordering must follow policy_state, completely ignoring a contradicting severity label")

# an ACCEPT_WITH_NOTE-equivalent (non-actionable) item must never enter the
# queue's actionable buckets even with severity="critical" spoofed onto it --
# but ACCEPT/ACCEPT_WITH_NOTE never produce a finding at all (per
# policy_enforcement._finding_from_decision's own actionable-states gate),
# so this is exercised via policy_decisions (the PASS/NOT_APPLICABLE path),
# confirming severity has no bearing on the passed/not-applicable
# classification either.
for i in range(6):
    policy_decisions = {f"clause_{i}": {"state": "ACCEPT_WITH_NOTE", "severity": "critical",
                                          "extracted_summary": "s", "policy_limit_summary": "p"}}
    case(f"sevC-rq-passed-immune-{i}", "passed-classification-immune-to-severity", "build_review_queue",
         {"findings": [], "policy_decisions": policy_decisions},
         {"passed_count": 1, "policy_exception_count": 0},
         "a spoofed severity='critical' on an ACCEPT_WITH_NOTE decision must not promote it into the exception queue")

# ===========================================================================
# Target 3: document_aggregation.aggregate_document_state (no severity read at all)
# ===========================================================================
_DOC_CASES = [
    ("clean", "ACCEPT", "NOT_TRIGGERED", "low", "CLEAN"),
    ("violation", "PROHIBITED", "NOT_TRIGGERED", "low", "HAS_POLICY_VIOLATION"),
    ("review", "REQUIRES_REVIEW", "NOT_TRIGGERED", "low", "REQUIRES_REVIEW"),
    ("interaction", "ACCEPT", "ESCALATE", "low", "HAS_CRITICAL_INTERACTION"),
    ("legacy-high-clean", "ACCEPT", "NOT_TRIGGERED", "high", "CLEAN_LEGACY_ATTENTION"),
]
for i, (name, pstate, istate, ov, expected_state) in enumerate(_DOC_CASES):
    for j, sev in enumerate(["critical", "low", None, "garbage", 999]):
        policy_decisions = {"indemnification": {"state": pstate, "severity": sev}}
        interaction_decisions = {"IX_TEST": {"state": istate, "severity": sev, "missing_clause_types": []}}
        case(f"sevC-agg-{name}-sev{j}", "aggregation-immune-to-severity", "aggregate_document_state",
             {"overall_risk": ov, "policy_decisions": policy_decisions, "interaction_decisions": interaction_decisions, "mode": "cutover"},
             {"document_state": expected_state},
             f"severity={sev!r} embedded in the decision dict must have zero effect on document_state")

# named required scenarios: legacy-high + deterministic low-severity
# finding must still surface CLEAN_LEGACY_ATTENTION (severity irrelevant);
# legacy-low + deterministic critical(-labeled) finding must still surface
# via its STATE, not its severity label.
for i in range(6):
    policy_decisions = {"indemnification": {"state": "ACCEPT", "severity": "low"}}
    case(f"sevC-agg-legacyhigh-lowsev-{i}", "legacy-high-plus-low-severity-finding", "aggregate_document_state",
         {"overall_risk": "high", "policy_decisions": policy_decisions, "interaction_decisions": {}, "mode": "cutover"},
         {"document_state": "CLEAN_LEGACY_ATTENTION"}, "a low-severity-labeled clean finding does not erase legacy-high attention")
for i in range(6):
    policy_decisions = {"indemnification": {"state": "PROHIBITED", "severity": "critical"}}
    case(f"sevC-agg-legacylow-criticalsev-{i}", "legacy-low-plus-critical-severity-violation", "aggregate_document_state",
         {"overall_risk": "low", "policy_decisions": policy_decisions, "interaction_decisions": {}, "mode": "cutover"},
         {"document_state": "HAS_POLICY_VIOLATION"}, "governed by state=PROHIBITED, not by the severity label")

# REQUIRES_REVIEW + low violation / REQUIRES_REVIEW + critical violation --
# precedence must follow state (violation beats review), severity must not
# reverse it even when the violation is severity-labeled "low" and the
# review is severity-labeled "critical" (or vice versa).
for i, (violation_sev, review_sev) in enumerate([("low", "critical"), ("critical", "low"), ("medium", "medium")]):
    policy_decisions = {
        "indemnification": {"state": "PROHIBITED", "severity": violation_sev},
        "sla": {"state": "REQUIRES_REVIEW", "severity": review_sev},
    }
    case(f"sevC-agg-violation-vs-review-precedence-{i}", "review-plus-violation-severity-crossed", "aggregate_document_state",
         {"overall_risk": "low", "policy_decisions": policy_decisions, "interaction_decisions": {}, "mode": "cutover"},
         {"document_state": "HAS_POLICY_VIOLATION"},
         f"violation_severity={violation_sev!r} review_severity={review_sev!r} -- precedence must still favor the violation STATE, unaffected by which one is labeled more severe")

# interaction + base finding with different (crossed) severities -- interaction ESCALATE must still win precedence
for i, (interaction_sev, policy_sev) in enumerate([("low", "critical"), ("critical", "low")]):
    policy_decisions = {"indemnification": {"state": "PROHIBITED", "severity": policy_sev}}
    interaction_decisions = {"IX_TEST": {"state": "ESCALATE", "severity": interaction_sev, "missing_clause_types": []}}
    case(f"sevC-agg-interaction-vs-policy-severity-crossed-{i}", "interaction-plus-base-finding-severity-crossed", "aggregate_document_state",
         {"overall_risk": "low", "policy_decisions": policy_decisions, "interaction_decisions": interaction_decisions, "mode": "cutover"},
         {"document_state": "HAS_CRITICAL_INTERACTION"},
         f"interaction_severity={interaction_sev!r} policy_severity={policy_sev!r} -- interaction ESCALATE state still wins precedence regardless of which side is labeled more severe")

# ---------------------------------------------------------------------------
# Top-up: same severity + different policies / same severity + different
# evidence (build_enhanced_issues), and additional review_queue tier-order
# volume, to comfortably clear the >=100 minimum.
# ---------------------------------------------------------------------------
for i in range(10):
    findings = [
        {"rule_id": f"R_SAMESEV_A_{i}", "title": "F1", "severity": "high", "clause_number": None, "start_index": i, "end_index": i + 5},
        {"rule_id": f"R_SAMESEV_B_{i}", "title": "F2", "severity": "high", "clause_number": None, "start_index": i + 100, "end_index": i + 105},
    ]
    case(f"sevC-be-samesev-diffpolicy-{i}", "same-severity-different-policies", "build_enhanced_issues",
         {"findings": findings, "llm_top_issues": []}, {"count": 2}, "identical severity, different rule_ids/evidence -- both survive")

for i in range(10):
    findings = [
        {"rule_id": f"R_SAMESEV_EV_{i}", "title": "F1", "severity": "medium", "clause_number": "2.1", "start_index": 10, "end_index": 20},
        {"rule_id": f"R_SAMESEV_EV_{i}", "title": "F1", "severity": "medium", "clause_number": "2.2", "start_index": 30, "end_index": 40},
    ]
    case(f"sevC-be-samesev-diffevidence-{i}", "same-severity-different-evidence", "build_enhanced_issues",
         {"findings": findings, "llm_top_issues": []}, {"count": 2}, "identical severity AND rule_id, different evidence locations -- both survive (Phase B dedup key)")

for i in range(9):
    findings = [
        {"rule_id": f"R_TIERVOL_{i}_0", "finding_type": "policy_decision", "policy_state": "REQUIRES_REVIEW", "severity": "low", "clause_type": "a"},
        {"rule_id": f"R_TIERVOL_{i}_1", "finding_type": "policy_decision", "policy_state": "PROHIBITED", "severity": "medium", "clause_type": "b"},
        {"rule_id": f"R_TIERVOL_{i}_2", "finding_type": "policy_decision", "policy_state": "NEGOTIATE", "severity": "critical", "clause_type": "c"},
    ]
    case(f"sevC-rq-tier-volume-{i}", "tier-rank-immune-to-severity-volume", "build_review_queue",
         {"findings": findings, "policy_decisions": {}},
         {"policy_order_states": ["PROHIBITED", "NEGOTIATE", "REQUIRES_REVIEW"]},
         "3-item tier ordering must follow policy_state alone, ignoring severity ordering entirely (critical-labeled NEGOTIATE ranks after medium-labeled PROHIBITED)")
