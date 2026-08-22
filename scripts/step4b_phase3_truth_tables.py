"""Step 4B Phase 3 — empirically verify interaction authority behavior for
each of the 7 launch-catalog rules against constructed PolicyDecision
fixtures (bypassing extraction, per the design doc's own recommended
benchmark methodology). Prints one truth table per rule and writes a
structured JSON dump for the Phase 3 report."""
import sys
sys.path.insert(0, ".")

import json
from policy_engine_core import PolicyDecision
import interaction_engine_core as ixc
import interaction_rules as ixr


def pd(clause_type, state, category_treatments=None, interaction_facts=None, rule_id="TEST"):
    return PolicyDecision(
        rule_id=rule_id, clause_type=clause_type, state=state,
        contract_language="", extracted_summary="", policy_limit_summary="",
        required_action="", explanation="", negotiation_ladder=[],
        category_treatments=category_treatments or [], unresolved_facts=[],
        start_index=0, end_index=10,
        controlling_provision={"label": f"{clause_type} clause", "excerpt": "...evidence...", "start_index": "0", "end_index": "10"},
        interaction_facts=interaction_facts or {},
    )


def ct(category, treatment, established=True):
    return {"category": category, "treatment": treatment, "cap_summary": "", "raw_excerpt": "", "established": established}


def run_one(rule, decisions):
    return ixc.evaluate(decisions, [rule])[0]


ALL_RESULTS = {}


def section(rule_index, name, cases):
    rule = ixr.LAUNCH_CATALOG[rule_index]
    print("=" * 110)
    print(f"RULE {rule_index + 1}: {rule.interaction_id}  ({name})")
    print("=" * 110)
    rows = []
    for label, decisions in cases.items():
        d = run_one(rule, decisions)
        evidence_ok = all(d.participating_provisions.get(ct_) is not None for ct_ in decisions if ct_ in rule.participating_clause_types)
        print(f"  {label:60s} -> state={d.state:20s} missing={d.missing_clause_types} evidence_present={evidence_ok}")
        rows.append({"case": label, "state": d.state, "missing": list(d.missing_clause_types), "evidence_ok": evidence_ok})
    ALL_RESULTS[rule.interaction_id] = rows


# ---------------------------------------------------------------------------
# Rule 1
# ---------------------------------------------------------------------------
section(0, "IP uncapped liability + indemnity", {
    "ESTABLISHED+ESTABLISHED (fires)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
    },
    "ESTABLISHED+ESTABLISHED (no match: within_general_cap)": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("ip_infringement", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
    },
    "ESTABLISHED+NOT_APPLICABLE": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "NOT_APPLICABLE"),
    },
    "ESTABLISHED+REQUIRES_REVIEW": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "REQUIRES_REVIEW"),
    },
    "missing participant entirely": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
    },
    "wrong category (data_breach, not ip_infringement)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
    },
    "EVALUATION_ERROR participant": {
        "limitation_of_liability": pd("limitation_of_liability", "EVALUATION_ERROR"),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "covered")]),
    },
    "both resolved, treatment excludes (excluded not covered)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("ip_infringement", "excluded")]),
    },
    "duplicate/repeated call determinism (5x)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
    },
})

# ---------------------------------------------------------------------------
# Rule 2 — shared category mismatch (generalizes rule 1 to 4 other categories)
# ---------------------------------------------------------------------------
section(1, "Shared category mismatch", {
    "ESTABLISHED+ESTABLISHED single category fires": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "super_cap")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered")]),
    },
    "multiple categories fire together (not separate rows)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped"), ct("confidentiality", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered"), ct("confidentiality", "covered")]),
    },
    "ip_infringement excluded from this rule (rule 1's job)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered")]),
    },
    "missing participant": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
    },
    "one REQUIRES_REVIEW": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "indemnification": pd("indemnification", "REQUIRES_REVIEW"),
    },
})

# ---------------------------------------------------------------------------
# Rule 3 — indemnity within general cap (DEPENDENCY, informational)
# ---------------------------------------------------------------------------
section(2, "Indemnity within general cap (DEPENDENCY)", {
    "within_general_cap + covered fires (informational)": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    },
    "not_addressed + covered fires": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "not_addressed")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    },
    "uncapped does NOT trigger this rule (rule 1/2's job)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "indemnification": pd("indemnification", "ESCALATE", [ct("data_breach", "covered")]),
    },
    "one REQUIRES_REVIEW blocks": {
        "limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW"),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    },
})

# ---------------------------------------------------------------------------
# Rule 4 — category-level ambiguity (per-category "unresolved" -- distinct
# from decision-level REQUIRES_REVIEW; this is the CONFLICTING-analog)
# ---------------------------------------------------------------------------
section(3, "Category-level ambiguity (CONFLICTING-analog)", {
    "liability category unresolved, decision otherwise ACCEPT": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("gross_negligence", "unresolved")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("gross_negligence", "not_addressed")]),
    },
    "indemnification category unresolved": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("willful_misconduct", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("willful_misconduct", "unresolved")]),
    },
    "BOTH categories unresolved simultaneously (CONFLICTING+CONFLICTING analog)": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("confidentiality", "unresolved")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("confidentiality", "unresolved")]),
    },
    "no ambiguity, clean categories": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    },
    "whole-decision REQUIRES_REVIEW (gated before rule 4 even runs)": {
        "limitation_of_liability": pd("limitation_of_liability", "REQUIRES_REVIEW"),
        "indemnification": pd("indemnification", "ACCEPT", [ct("data_breach", "covered")]),
    },
})

# ---------------------------------------------------------------------------
# Rule 5 — uncapped liability, no cyber insurance
# ---------------------------------------------------------------------------
section(4, "Uncapped liability, no cyber insurance", {
    "uncapped + not established fires": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
    },
    "uncapped + established does NOT fire": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "within_general_cap", established=True)]),
    },
    "within_general_cap does not fire regardless of insurance": {
        "limitation_of_liability": pd("limitation_of_liability", "ACCEPT", [ct("data_breach", "within_general_cap")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
    },
    "wrong category (ip_infringement has no insurance mapping)": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped")]),
        "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
    },
    "missing insurance participant": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
    },
    "insurance NOT_APPLICABLE": {
        "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("data_breach", "uncapped")]),
        "insurance": pd("insurance", "NOT_APPLICABLE"),
    },
})

# ---------------------------------------------------------------------------
# Rule 6 — non-payment termination vs. dispute withholding (uses
# interaction_facts, directional: counterparty's non-payment right)
# ---------------------------------------------------------------------------
section(5, "Non-payment termination vs. withholding (directional)", {
    "immediate + withholdable=True fires": {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
    },
    "immediate + withholdable=False does not fire": {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": False}),
    },
    "immediate + withholdable=None (unestablished) does not fire": {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={}),
    },
    "non-immediate (has notice/cure) does not fire even if withholdable": {
        "termination": pd("termination", "ACCEPT", [ct("non_payment", "notice_and_cure")]),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
    },
    "missing payment_terms participant": {
        "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
    },
    "termination REQUIRES_REVIEW gates": {
        "termination": pd("termination", "REQUIRES_REVIEW"),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True}),
    },
})

# ---------------------------------------------------------------------------
# Rule 7 — SLA x Payment Terms service credit dependency
# ---------------------------------------------------------------------------
section(6, "SLA x Payment Terms service credit dependency", {
    "both True fires": {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
    },
    "SLA True, Payment False does not fire": {
        "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": False}),
    },
    "both None (unestablished) does not fire": {
        "sla": pd("sla", "ACCEPT", interaction_facts={}),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={}),
    },
    "missing sla participant": {
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
    },
    "sla NOT_APPLICABLE": {
        "sla": pd("sla", "NOT_APPLICABLE"),
        "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"service_credit_present": True}),
    },
})

print("\n\nFull LAUNCH_CATALOG determinism check (5x over a mixed decision set):")
mixed = {
    "limitation_of_liability": pd("limitation_of_liability", "ESCALATE", [ct("ip_infringement", "uncapped"), ct("data_breach", "uncapped")]),
    "indemnification": pd("indemnification", "ESCALATE", [ct("ip_infringement", "covered"), ct("data_breach", "covered")]),
    "insurance": pd("insurance", "ACCEPT", [ct("cyber_liability", "not_addressed", established=False)]),
    "termination": pd("termination", "ESCALATE", [ct("non_payment", "immediate")]),
    "payment_terms": pd("payment_terms", "ACCEPT", interaction_facts={"disputed_amounts_withholdable": True, "service_credit_present": True}),
    "sla": pd("sla", "ACCEPT", interaction_facts={"service_credit_present": True}),
}
det_ok = ixc.check_deterministic(lambda: ixc.evaluate(mixed, ixr.LAUNCH_CATALOG), repeats=5)
print(f"  determinism (5x) = {det_ok}")

with open("artifacts/step4b/phase3_truth_table_results.json", "w") as f:
    json.dump({"results": ALL_RESULTS, "full_catalog_determinism_5x": det_ok}, f, indent=2)
print("\nWrote artifacts/step4b/phase3_truth_table_results.json")
