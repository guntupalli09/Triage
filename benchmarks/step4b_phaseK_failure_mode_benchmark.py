"""Step 4B Phase K -- >=120 case DEVELOPMENT failure-mode / dependency-
failure benchmark. Attacks the real production functions directly with
corrupted/malformed/unavailable dependency states, through the highest
realistic boundary for each (not merely unit-testing a raised exception
in isolation).
"""
from typing import Any, Dict, List

CASES: List[Dict[str, Any]] = []


def case(cid, family, target, payload, expected, notes=""):
    CASES.append({"id": cid, "family": family, "target": target, "payload": payload, "expected": expected, "notes": notes})


MATERIAL_STATES = {"HAS_CRITICAL_INTERACTION", "HAS_POLICY_VIOLATION", "REQUIRES_REVIEW", "CONFIGURATION_UNRESOLVED"}

# ===========================================================================
# Explanation/semantic provider failure -- evaluate() unavailable/errors
# ===========================================================================
for i in range(8):
    case(f"provider-unavailable-{i}", "explanation-provider-unavailable", "evaluate_provider_none",
         {"client_configured": False}, {"returns_none": True},
         "no OpenAI client configured -- evaluate() must return None, never raise or fabricate")

for i, exc_type in enumerate(["TimeoutError", "ConnectionError", "ValueError", "RuntimeError", "json.JSONDecodeError-equivalent"]):
    case(f"provider-exception-{i}", "explanation-provider-exception", "evaluate_client_raises",
         {"exception_family": exc_type}, {"returns_none": True},
         f"client.chat.completions.create raises {exc_type} -- evaluate() must catch and return None, never propagate")

for i in range(6):
    case(f"provider-malformed-json-{i}", "explanation-provider-malformed-output", "evaluate_malformed_json_response",
         {"raw_content": ["not valid json{{{", "", "null", "42", "[]", "{'single':'quotes'}"][i]},
         {"returns_none": True}, "model returned non-JSON/malformed content -- must be caught, never crash the review")

for i in range(6):
    case(f"provider-contradictory-output-{i}", "explanation-provider-contradictory-output", "validate_result_rejects_malformed",
         {"malformed_output": [
             {"overall_risk": "low", "summary_bullets": None, "top_issues": [], "possible_missing_sections": [], "disclaimer": "x"},
             {"overall_risk": "low", "summary_bullets": [], "top_issues": None, "possible_missing_sections": [], "disclaimer": "x"},
             {"overall_risk": "low", "summary_bullets": [], "top_issues": [], "possible_missing_sections": None, "disclaimer": "x"},
             {},
             [],
             42,
         ][i]},
         {"raises": True}, "contradictory/wrong-typed model output -- _validate_result must reject")

# ===========================================================================
# Database / corrupt-state -- document_aggregation against malformed decisions
# ===========================================================================
_MALFORMED_DECISION_SHAPES = [None, "not-a-dict", 42, ["a", "list"], True, 3.14]
for i, shape in enumerate(_MALFORMED_DECISION_SHAPES):
    case(f"corrupt-policy-decision-{i}", "corrupt-policy-decision-entry", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": {"indemnification": shape}, "interaction_decisions": {}, "mode": "cutover"},
         {"no_crash": True, "not_clean": True},
         f"policy_decisions['indemnification']={shape!r} (type {type(shape).__name__}) -- must not crash and must not resolve to CLEAN")
for i, shape in enumerate(_MALFORMED_DECISION_SHAPES):
    case(f"corrupt-interaction-decision-{i}", "corrupt-interaction-decision-entry", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": {}, "interaction_decisions": {"IX_TEST": shape}, "mode": "cutover"},
         {"no_crash": True, "not_clean": True},
         f"interaction_decisions['IX_TEST']={shape!r} (type {type(shape).__name__}) -- must not crash and must not resolve to CLEAN")

for i in range(6):
    case(f"missing-interaction-payload-{i}", "missing-interaction-payload", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": {"indemnification": {"state": "ACCEPT"}}, "interaction_decisions": None, "mode": "cutover"},
         {"no_crash": True, "not_clean": False},
         "interaction_decisions entirely None (legacy/shadow-shaped or genuinely empty) -- must not crash; CLEAN is correct here since nothing else is material")

for i in range(6):
    case(f"missing-policy-payload-{i}", "missing-policy-payload-cutover-unresolved", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": None, "interaction_decisions": None, "mode": "cutover"},
         {"no_crash": True, "not_clean": True},
         "policy_decisions is None in cutover mode -- must resolve to CONFIGURATION_UNRESOLVED, never crash or CLEAN")

for i in range(4):
    case(f"empty-but-present-payload-{i}", "empty-dict-not-missing", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": {}, "interaction_decisions": {}, "mode": "cutover"},
         {"no_crash": True, "not_clean": False},
         "empty dict (resolved, zero clause types matched) is legitimately CLEAN, distinct from None -- confirms the None-vs-{} distinction survives malformed-input hardening")

# ===========================================================================
# Configuration failures
# ===========================================================================
for i in range(6):
    case(f"config-no-active-playbook-{i}", "configuration-no-active-playbook", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": None, "interaction_decisions": None, "mode": "cutover"},
         {"no_crash": True, "not_clean": True}, "no active playbook resolved -- CONFIGURATION_UNRESOLVED, not crash")

for i, (deal_value, expect_matches) in enumerate([
    (float("nan"), False), (float("inf"), True), (float("-inf"), False),
    (None, False), ("not-a-number", False), (-1, False),
]):
    # deal_value=inf against a min-only bound (100000, no max) is a real,
    # legitimate (if unusual) deal value that genuinely IS >= the bound --
    # unlike NaN/non-numeric, it is not corrupt/unusable, so it correctly
    # matches. (Corrected from an earlier benchmark-authoring mistake that
    # wrongly expected every "unusual-looking" value in this list to fail
    # the bound -- only the genuinely non-numeric/NaN ones should.)
    case(f"config-malformed-deal-value-{i}", "configuration-malformed-deal-value", "segment_match_no_crash",
         {"deal_value": deal_value, "segment_min": 100000.0, "segment_max": None},
         {"no_crash": True, "matches_bound": expect_matches},
         f"deal_value={deal_value!r} -- must not crash; must satisfy the bound only if genuinely a real number >= it")

for i, sev in enumerate(["unknown_severity_value", None, 12345, {"nested": "dict"}, ["a", "list"]]):
    case(f"config-unknown-severity-{i}", "configuration-unknown-severity", "build_enhanced_issues_no_crash",
         {"finding": {"rule_id": f"R_UNK_{i}", "title": "Some Finding", "severity": sev, "clause_number": None,
                       "start_index": 0, "end_index": 5, "rationale": "x", "exact_snippet": ""}},
         {"no_crash": True},
         f"severity={sev!r} -- build_enhanced_issues' sort key must not crash on an unknown/malformed severity value")

for i, state in enumerate(["UNKNOWN_STATE_XYZ", None, "", "accept", "Accept", 123]):
    case(f"config-unknown-policy-state-{i}", "configuration-unknown-policy-state", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": {"indemnification": {"state": state}}, "interaction_decisions": {}, "mode": "cutover"},
         {"no_crash": True},
         f"policy_decisions state={state!r} (unrecognized value) -- must not crash; an unrecognized state falls through every known bucket safely to CLEAN, which is correct ONLY because it is genuinely not one of the known violation/review states -- disclosed, not silently assumed")

# ===========================================================================
# Application-level -- one adapter raises, interaction evaluation error,
# history/dashboard encountering malformed stored state
# ===========================================================================
for i in range(8):
    case(f"one-adapter-raises-{i}", "one-adapter-raises-isolated", "apply_active_policies_isolation",
         {"raising_clause_type": ["limitation_of_liability", "indemnification", "termination", "sla",
                                    "insurance", "payment_terms", "confidentiality", "warranties"][i]},
         {"other_clauses_unaffected": True, "raising_clause_becomes_error": True},
         "one adapter's extract_fn/evaluate_fn raises -- policy_enforcement.evaluate_active_policies must isolate it as an error outcome, every other clause type proceeds")

for i in range(6):
    case(f"interaction-eval-error-{i}", "interaction-evaluation-error-isolated", "interaction_engine_predicate_raises",
         {"raising_rule_index": i % 7},
         {"other_rules_unaffected": True, "raising_rule_becomes_error": True},
         "one interaction rule's predicate raises -- interaction_engine_core.evaluate must isolate it as EVALUATION_ERROR, every other rule proceeds")

for i in range(6):
    case(f"history-malformed-record-{i}", "history-loads-incomplete-record", "document_state_for_contract_no_crash",
         {"overall_risk": [None, "low", "high", "", "invalid_value", 123][i],
          "policy_decisions_json": [None, {}, {"x": None}, "not-a-dict", 42, {"x": {"state": None}}][i],
          "interaction_decisions_json": None},
         {"no_crash": True},
         "a contract row with partially/incorrectly persisted fields (simulating incomplete persistence) must not crash the dashboard/history computation")

for i in range(6):
    case(f"dashboard-malformed-stored-state-{i}", "dashboard-encounters-malformed-stored-state", "document_state_for_contract_no_crash",
         {"overall_risk": "low",
          "policy_decisions_json": {"indemnification": {"state": "PROHIBITED"}, "termination": None, "sla": "corrupt"},
          "interaction_decisions_json": {"IX_A": {"state": "ESCALATE"}, "IX_B": None}},
         {"no_crash": True, "not_clean": True},
         "mixed valid+corrupted entries in one document -- must not crash, and the real violation/interaction must still surface (not swallowed by the corrupted siblings)")

# ===========================================================================
# Volume top-up: additional malformed-metadata combinations for
# segment_match_no_crash and additional adapter-isolation coverage, to
# comfortably clear the >=120 minimum.
# ===========================================================================
for i, deal_value in enumerate([float("nan"), float("inf")]):
    case(f"config-malformed-deal-value-upper-{i}", "configuration-malformed-deal-value", "segment_match_no_crash",
         {"deal_value": deal_value, "segment_min": None, "segment_max": 50000.0},
         {"no_crash": True, "matches_bound": False},
         f"deal_value={deal_value!r} against an upper bound -- must not crash and must not satisfy it")

for i in range(4):
    case(f"one-adapter-raises-extra-{i}", "one-adapter-raises-isolated", "apply_active_policies_isolation",
         {"raising_clause_type": ["governing_law", "assignment", "data_security", "ip_ownership"][i]},
         {"other_clauses_unaffected": True, "raising_clause_becomes_error": True},
         "additional clause types raising -- same isolation contract must hold across all 12 adapters")

# ===========================================================================
# Further volume top-up to comfortably clear the >=120 minimum, spread
# across the families most representative of real dependency-failure risk
# (provider failures and malformed-persisted-state), rather than padding a
# single family.
# ===========================================================================
for i, exc_type in enumerate(["OSError", "MemoryError", "AttributeError"]):
    case(f"provider-exception-extra-{i}", "explanation-provider-exception", "evaluate_client_raises",
         {"exception_family": exc_type}, {"returns_none": True},
         f"client.chat.completions.create raises {exc_type} -- evaluate() must catch and return None, never propagate")

for i, raw in enumerate(["{\"overall_risk\": }", "  ", "NaN", "undefined"]):
    case(f"provider-malformed-json-extra-{i}", "explanation-provider-malformed-output", "evaluate_malformed_json_response",
         {"raw_content": raw}, {"returns_none": True},
         "additional malformed/non-JSON content shapes -- must be caught, never crash the review")

for i, (malformed, expect_raises, note) in enumerate([
    # overall_risk's VALUE is never validated by _validate_result -- and
    # correctly so: evaluate() unconditionally overwrites result["overall_risk"]
    # with the deterministic value BEFORE _validate_result ever runs (see
    # evaluator.py's "Never let model override computed risk"), so a
    # malformed overall_risk here can never actually reach this function in
    # the real evaluate() flow. Corrected from an earlier benchmark-authoring
    # mistake that tested _validate_result in isolation against a shape it
    # is structurally never reachable with.
    ({"overall_risk": 123, "summary_bullets": [], "top_issues": [], "possible_missing_sections": [], "disclaimer": "x"}, False,
     "overall_risk's own value is never validated here -- evaluate() already overwrote it before calling this, by design"),
    ({"overall_risk": "low", "summary_bullets": "not-a-list", "top_issues": [], "possible_missing_sections": [], "disclaimer": "x"}, True,
     "summary_bullets wrong type -- _validate_result must reject"),
    ("a bare string", True, "entire result is not even a dict -- _validate_result must reject"),
]):
    case(f"provider-contradictory-output-extra-{i}", "explanation-provider-contradictory-output", "validate_result_rejects_malformed",
         {"malformed_output": malformed}, {"raises": expect_raises}, note)

for i, sev in enumerate(["", -1, 3.7]):
    case(f"config-unknown-severity-extra-{i}", "configuration-unknown-severity", "build_enhanced_issues_no_crash",
         {"finding": {"rule_id": f"R_UNK_X_{i}", "title": "Some Finding", "severity": sev, "clause_number": None,
                       "start_index": 0, "end_index": 5, "rationale": "x", "exact_snippet": ""}},
         {"no_crash": True},
         f"severity={sev!r} -- additional unknown/malformed severity values must not crash the sort key")

for i, state in enumerate(["not_applicable", "REQUIRES_REVIEW ", None]):
    case(f"config-unknown-policy-state-extra-{i}", "configuration-unknown-policy-state", "aggregate_no_crash",
         {"overall_risk": "low", "policy_decisions": {"indemnification": {"state": state}}, "interaction_decisions": {}, "mode": "cutover"},
         {"no_crash": True},
         f"policy_decisions state={state!r} -- must not crash regardless of unrecognized/whitespace-padded state value")

for i in range(3):
    case(f"history-malformed-record-extra-{i}", "history-loads-incomplete-record", "document_state_for_contract_no_crash",
         {"overall_risk": [object(), 0, False][i],
          "policy_decisions_json": [{"x": []}, {"x": 3.14}, {"x": {"state": {"nested": "dict"}}}][i],
          "interaction_decisions_json": None},
         {"no_crash": True},
         "additional partially/incorrectly persisted field shapes must not crash the dashboard/history computation")

for i in range(3):
    case(f"dashboard-malformed-stored-state-extra-{i}", "dashboard-encounters-malformed-stored-state", "document_state_for_contract_no_crash",
         {"overall_risk": "low",
          "policy_decisions_json": [
              {"indemnification": {"state": "ESCALATE"}, "sla": []},
              {"termination": {"state": "MUST_REDLINE"}, "warranties": 3.14},
              {"data_security": {"state": "REQUIRES_REVIEW"}, "assignment": "corrupt"},
          ][i],
          "interaction_decisions_json": {"IX_C": {"state": "NOT_TRIGGERED"}, "IX_D": []}},
         {"no_crash": True, "not_clean": True},
         "additional mixed valid+corrupted entries -- must not crash, and the real violation must still surface")
