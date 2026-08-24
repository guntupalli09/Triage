#!/usr/bin/env python3
"""Phase 4/5/6 analysis of raw_results.jsonl. Read-only: computes hard
safety gates, per-adapter matrix, and interaction-scenario results.
Run only AFTER the one-shot execution (run_independent_corpus.py)
completes. Does not modify raw_results.jsonl or the frozen corpus."""
import json
import os
from collections import defaultdict, Counter

HERE = os.path.dirname(__file__)
results = [json.loads(l) for l in open(os.path.join(HERE, "raw_results.jsonl"))]
print(f"Total results: {len(results)}")

# ---------------------------------------------------------------------------
# Phase 4: hard safety gates
# ---------------------------------------------------------------------------
HARD_GATES = [
    "FALSE_SAFE", "UNVERIFIED_FEEDING_CLEAN", "FALSE_ABSENCE", "FALSE_OPERATIVE_TO_CLEAN",
    "MATERIAL_CONTEXT_SILENTLY_LOST", "ARBITRARILY_SELECTED_COMPETING_READING",
    "UNRESOLVED_CROSS_REFERENCE_TO_CLEAN", "UNRESOLVED_DEFINITION_TO_CLEAN",
]
gate_counts = Counter()
gate_cases = defaultdict(list)

NON_MISSING_EXPECTED = {
    "YES_OPERATIVE", "YES_BUT_CONDITIONAL", "YES_BUT_EXCEPTION", "AMBIGUOUS",
    "CROSS_REFERENCE_DEPENDENT", "DEFINITION_DEPENDENT",
}

for r in results:
    fcs = r.get("failure_classes", []) or []
    for gate in ["FALSE_SAFE", "FALSE_OPERATIVE_TO_CLEAN", "MATERIAL_CONTEXT_SILENTLY_LOST",
                 "ARBITRARILY_SELECTED_COMPETING_READING", "UNRESOLVED_CROSS_REFERENCE_TO_CLEAN",
                 "UNRESOLVED_DEFINITION_TO_CLEAN"]:
        if gate in fcs:
            gate_counts[gate] += 1
            gate_cases[gate].append(r["case_id"])

    # UNVERIFIED_FEEDING_CLEAN: blanket, expectation-agnostic check -- a
    # clean (ACCEPT/ACCEPT_WITH_NOTE) decision reached with NO
    # deterministic/verified fact established at all for that adapter.
    bucket = r.get("decision_bucket") or r.get("bucket")
    established = r.get("established_signal")
    if bucket == "CLEAN" and established is False:
        gate_counts["UNVERIFIED_FEEDING_CLEAN"] += 1
        gate_cases["UNVERIFIED_FEEDING_CLEAN"].append(r["case_id"])

    # FALSE_ABSENCE: the clause was genuinely present (expected != MISSING_CLAUSE)
    # but the decision bucket is NOT_APPLICABLE (system says "not addressed").
    if r["expected"] in NON_MISSING_EXPECTED and bucket == "NOT_APPLICABLE":
        gate_counts["FALSE_ABSENCE"] += 1
        gate_cases["FALSE_ABSENCE"].append(r["case_id"])

print("\n=== PHASE 4: HARD SAFETY GATES ===")
for gate in HARD_GATES:
    print(f"{gate}: {gate_counts[gate]}")
    if gate_counts[gate]:
        print(f"  cases: {gate_cases[gate]}")

# Non-hard-gate diagnostics
false_escalation = sum(1 for r in results if r["expected"] in ("NO_NOT_OPERATIVE",)
                        and (r.get("decision_bucket") or r.get("bucket")) not in ("NOT_APPLICABLE", "CLEAN"))
correct_clean = sum(1 for r in results if (r.get("decision_bucket") or r.get("bucket")) == "CLEAN" and r["passed"])
correct_non_clean = sum(1 for r in results if (r.get("decision_bucket") or r.get("bucket")) not in ("CLEAN",) and r["passed"])
conservative_review = sum(1 for r in results if (r.get("decision_bucket") or r.get("bucket")) == "REQUIRES_REVIEW")

print("\n=== OTHER METRICS ===")
print(f"FALSE_ESCALATION (expected NO_NOT_OPERATIVE, decision not absent/clean): {false_escalation}")
print(f"CONSERVATIVE_REVIEW_RATE: {conservative_review}/{len(results)} = {conservative_review/len(results):.1%}")
print(f"CORRECT_CLEAN: {correct_clean}")
print(f"CORRECT_NON_CLEAN: {correct_non_clean}")

overall_passed = sum(1 for r in results if r["passed"])
print(f"\nOverall pass rate: {overall_passed}/{len(results)} = {overall_passed/len(results):.1%}")

fc_counter = Counter()
for r in results:
    for fc in r.get("failure_classes", []) or []:
        fc_counter[fc] += 1
print("\nAll failure classes observed:")
for fc, n in sorted(fc_counter.items()):
    print(f"  {fc}: {n}")

# ---------------------------------------------------------------------------
# Phase 5: 12-adapter coverage matrix
# ---------------------------------------------------------------------------
print("\n=== PHASE 5: 12-ADAPTER MATRIX ===")
ADAPTER_DISPLAY = {
    "limitation_of_liability": "Limitation of Liability", "indemnification": "Indemnification",
    "termination": "Termination", "confidentiality": "Confidentiality", "assignment": "Assignment",
    "governing_law": "Governing Law", "data_security": "Data Protection & Security",
    "ip_ownership": "IP Ownership & Licensing", "insurance": "Insurance",
    "payment_terms": "Payment Terms", "warranties": "Warranties", "sla": "SLA / Service Levels",
}
by_adapter = defaultdict(list)
for r in results:
    by_adapter[r["adapter"]].append(r)

adapter_matrix = {}
for adapter in ADAPTER_DISPLAY:
    rs = by_adapter.get(adapter, [])
    cases_n = len(rs)
    correct = sum(1 for r in rs if r["passed"])
    fs = sum(1 for r in rs if "FALSE_SAFE" in (r.get("failure_classes") or []))
    fa_ = sum(1 for r in rs if r["expected"] in NON_MISSING_EXPECTED
              and (r.get("decision_bucket") or r.get("bucket")) == "NOT_APPLICABLE")
    fotc = sum(1 for r in rs if "FALSE_OPERATIVE_TO_CLEAN" in (r.get("failure_classes") or []))
    mcsl = sum(1 for r in rs if "MATERIAL_CONTEXT_SILENTLY_LOST" in (r.get("failure_classes") or []))
    udtc = sum(1 for r in rs if "UNRESOLVED_CROSS_REFERENCE_TO_CLEAN" in (r.get("failure_classes") or [])
               or "UNRESOLVED_DEFINITION_TO_CLEAN" in (r.get("failure_classes") or []))
    fesc = sum(1 for r in rs if r["expected"] == "NO_NOT_OPERATIVE"
               and (r.get("decision_bucket") or r.get("bucket")) not in ("NOT_APPLICABLE", "CLEAN"))
    hard_gate_total = fs + fa_ + fotc + mcsl + udtc
    adapter_matrix[adapter] = {
        "display": ADAPTER_DISPLAY[adapter], "cases": cases_n, "correct": correct,
        "false_safe": fs, "false_absence": fa_, "false_operative_to_clean": fotc,
        "silent_context_loss": mcsl, "unresolved_dependency_to_clean": udtc,
        "false_escalation": fesc, "final_gate": "PASS" if hard_gate_total == 0 else "FAIL",
    }
    print(f"{ADAPTER_DISPLAY[adapter]}: cases={cases_n} correct={correct} FS={fs} FA={fa_} "
          f"FOTC={fotc} SCL={mcsl} UDTC={udtc} FESC={fesc} -> {adapter_matrix[adapter]['final_gate']}")

with open(os.path.join(HERE, "phase4_5_analysis.json"), "w") as f:
    json.dump({
        "hard_gates": {g: gate_counts[g] for g in HARD_GATES},
        "hard_gate_cases": {g: gate_cases[g] for g in HARD_GATES if gate_cases[g]},
        "false_escalation": false_escalation, "conservative_review_rate": conservative_review / len(results),
        "correct_clean": correct_clean, "correct_non_clean": correct_non_clean,
        "overall_pass_rate": overall_passed / len(results),
        "adapter_matrix": adapter_matrix,
    }, f, indent=2)
print("\nWrote phase4_5_analysis.json")
