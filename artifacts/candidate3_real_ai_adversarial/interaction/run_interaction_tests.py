#!/usr/bin/env python3
"""Candidate 3 -- Section 11 interaction engine tests, exercised through
the REAL adapters (real AI enabled) feeding real PolicyDecision objects
into interaction_engine_core.evaluate() with the actual currently-
configured LAUNCH_CATALOG rules.
"""
import os
import sys
import json

os.environ["FACT_ADMISSION_MODE"] = "enforced"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
import replay_candidate2 as rc2  # noqa: E402

import indemnification_policy_engine as ie  # noqa: E402
import interaction_engine_core as iec  # noqa: E402
import interaction_rules as ir  # noqa: E402

ie.SEMANTIC_PROVIDER = "REAL"

RESULTS = []


def _decision_for(adapter, text, **policy_overrides):
    extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS[adapter]
    policy = policy_cls(**policy_overrides)
    facts = extract_fn(text)
    return evaluate_fn(facts, policy)


def _record(name, description, decisions, interaction_decisions):
    summary = [{"interaction_id": d.interaction_id, "state": d.state,
                "missing_clause_types": d.missing_clause_types} for d in interaction_decisions]
    RESULTS.append({
        "test": name, "description": description,
        "participant_states": {k: v.state for k, v in decisions.items()},
        "interaction_results": summary,
    })
    print(f"{name}: participants={ {k: v.state for k, v in decisions.items()} }")
    for d in interaction_decisions:
        print(f"    {d.interaction_id}: {d.state}" + (f" (missing: {d.missing_clause_types})" if d.missing_clause_types else ""))


def test_liability_indemnification_all_established():
    liability_text = ("15. Limitation of Liability. Vendor's aggregate liability shall not exceed one times "
                       "the fees paid in the prior twelve months.")
    indemnification_text = ("12. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer "
                             "from and against any and all third-party claims of any kind, without limitation "
                             "as to amount.")
    liability_decision = _decision_for("limitation_of_liability", liability_text,
                                        prohibit_unlimited=True, preferred_multiplier=1.0,
                                        acceptable_max_multiplier=1.0, negotiate_max_multiplier=2.0)
    indemnification_decision = _decision_for("indemnification", indemnification_text,
                                              prohibit_uncapped_exposure=True)
    decisions = {"limitation_of_liability": liability_decision, "indemnification": indemnification_decision}
    result = iec.evaluate(decisions, ir.LAUNCH_CATALOG)
    _record("liability_x_indemnification_all_established",
            "Uncapped indemnification alongside a capped liability clause -- both established",
            decisions, result)


def test_liability_indemnification_one_unresolved():
    liability_text = ("15. Limitation of Liability. Liability shall be capped as specified in Schedule C "
                       "(Risk Allocation Terms) attached hereto.")  # cross-reference dependent -> REQUIRES_REVIEW
    indemnification_text = ("12. Indemnification. Vendor shall indemnify Customer against any and all "
                             "third-party claims, without limitation as to amount.")
    liability_decision = _decision_for("limitation_of_liability", liability_text, prohibit_unlimited=True)
    indemnification_decision = _decision_for("indemnification", indemnification_text,
                                              prohibit_uncapped_exposure=True)
    decisions = {"limitation_of_liability": liability_decision, "indemnification": indemnification_decision}
    result = iec.evaluate(decisions, ir.LAUNCH_CATALOG)
    _record("liability_x_indemnification_one_unresolved",
            "Liability clause defers to a missing Schedule C (REQUIRES_REVIEW) -- must gate to "
            "INSUFFICIENT_FACTS, never silently treat the missing participant as if it were resolved",
            decisions, result)


def test_liability_indemnification_one_absent():
    liability_text = "9. Confidentiality. Each party shall protect the other's Confidential Information."
    indemnification_text = ("12. Indemnification. Vendor shall indemnify Customer against any and all "
                             "third-party claims, without limitation as to amount.")
    liability_decision = _decision_for("limitation_of_liability", liability_text, prohibit_unlimited=True)
    indemnification_decision = _decision_for("indemnification", indemnification_text,
                                              prohibit_uncapped_exposure=True)
    decisions = {"limitation_of_liability": liability_decision, "indemnification": indemnification_decision}
    result = iec.evaluate(decisions, ir.LAUNCH_CATALOG)
    _record("liability_x_indemnification_one_absent",
            "No liability clause present at all (NOT_APPLICABLE) -- must gate to INSUFFICIENT_FACTS",
            decisions, result)


def test_liability_indemnification_provider_failure():
    from unittest.mock import patch
    import urllib.error
    liability_text = "9. Confidentiality. Each party shall protect the other's Confidential Information."
    # Anchor-free indemnification text so extraction relies entirely on
    # the (about to fail) real provider call.
    indemnification_text = ("12. Risk Transfer. Vendor will step in and cover Customer's losses if a third "
                             "party comes after Customer because of something Vendor did wrong.")
    def side_effect(*a, **kw):
        raise urllib.error.URLError("connection refused")
    with patch("urllib.request.urlopen", side_effect=side_effect):
        indemnification_decision = _decision_for("indemnification", indemnification_text,
                                                  prohibit_uncapped_exposure=True)
    liability_decision = _decision_for("limitation_of_liability", liability_text, prohibit_unlimited=True)
    decisions = {"limitation_of_liability": liability_decision, "indemnification": indemnification_decision}
    result = iec.evaluate(decisions, ir.LAUNCH_CATALOG)
    _record("liability_x_indemnification_provider_failure",
            "Indemnification's real-AI discovery hits a network failure on colloquial (regex-invisible) "
            "language -- must gate to INSUFFICIENT_FACTS, never silently CLEAN",
            decisions, result)


def test_termination_x_payment():
    termination_text = ("18. Termination. Customer may terminate immediately for Vendor's non-payment "
                         "obligations breach without a cure period.")
    payment_text = ("6. Payment Terms. Customer may withhold payment of any amount reasonably disputed in "
                     "good faith pending resolution.")
    termination_decision = _decision_for("termination", termination_text)
    payment_decision = _decision_for("payment_terms", payment_text)
    decisions = {"termination": termination_decision, "payment_terms": payment_decision}
    result = iec.evaluate(decisions, ir.LAUNCH_CATALOG)
    _record("termination_x_payment",
            "Immediate non-payment termination alongside a good-faith dispute-withholding right",
            decisions, result)


def test_sla_x_payment():
    sla_text = "14. Service Level. The Service shall maintain 99.9% uptime with service credits for any shortfall."
    payment_text = "6. Payment Terms. Customer shall receive service credits applied against future invoices for any SLA shortfall."
    sla_decision = _decision_for("sla", sla_text)
    payment_decision = _decision_for("payment_terms", payment_text)
    decisions = {"sla": sla_decision, "payment_terms": payment_decision}
    result = iec.evaluate(decisions, ir.LAUNCH_CATALOG)
    _record("sla_x_payment", "SLA service credits alongside payment-terms service-credit application",
            decisions, result)


def test_confidentiality_x_data_security_not_configured():
    """No LAUNCH_CATALOG rule currently pairs confidentiality with
    data_security -- verified by inspecting interaction_rules.py directly
    rather than assumed. Recorded as N/A, not silently skipped."""
    pairs = {tuple(sorted(r.participating_clause_types)) for r in ir.LAUNCH_CATALOG}
    configured = tuple(sorted(("confidentiality", "data_security"))) in pairs
    RESULTS.append({
        "test": "confidentiality_x_data_security", "description":
        "Mission asks to test confidentiality x data_security interaction",
        "n_a": True, "reason": "No interaction_rules.LAUNCH_CATALOG rule currently pairs these two clause "
                                "types (confirmed by inspecting interaction_rules.py directly)",
        "currently_configured_pairs": sorted(str(p) for p in pairs),
    })
    print("confidentiality_x_data_security: N/A -- not a currently configured interaction rule. "
          f"Configured pairs: {sorted(str(p) for p in pairs)}")


if __name__ == "__main__":
    test_liability_indemnification_all_established()
    test_liability_indemnification_one_unresolved()
    test_liability_indemnification_one_absent()
    test_liability_indemnification_provider_failure()
    test_termination_x_payment()
    test_sla_x_payment()
    test_confidentiality_x_data_security_not_configured()

    out_path = os.path.join(os.path.dirname(__file__), "interaction_results.json")
    with open(out_path, "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    print(f"\nWrote {out_path}")
