#!/usr/bin/env python3
"""Candidate 3 remediation -- Section 15 real-provider repeatability test.

Selects >=36 adversarial cases spanning all 12 adapters from the burned
corpus, runs each through the REAL OpenAI provider 5 independent times,
and checks the required invariant: AI proposals may differ run-to-run,
but the CANONICAL authoritative outcome must never swing between a clean
state (ACCEPT/ACCEPT_WITH_NOTE) and any other state purely from provider
sampling variance.
"""
import os
import sys
import json

os.environ["FACT_ADMISSION_MODE"] = "enforced"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate3_real_ai_adversarial", "corpus"))

from cases import CASES  # noqa: E402

sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
import replay_candidate2 as rc2  # noqa: E402

import indemnification_policy_engine as ie  # noqa: E402
ie.SEMANTIC_PROVIDER = "REAL"

# 3 cases per adapter x 12 adapters = 36, chosen to include at least one
# LEE1 (positive control), one descriptive/hypothetical/negotiation/quoted
# family case, and one condition/exception/ambiguous family case per
# adapter -- the shapes most likely to actually invoke a real AI call and
# most likely to matter if variance leaks through.
SELECTED_IDS = []
_by_adapter_family_targets = {
    "limitation_of_liability": ["LEE1", "LEE2", "LEE6"],
    "indemnification": ["LEE1", "LEE2", "LEE6"],
    "confidentiality": ["LEE1", "LEE2", "LEE8"],
    "payment_terms": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING"],
    "ip_ownership": ["LEE1", "UNUSUAL_VALID_DRAFTING", "LEE2"],
    "insurance": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING"],
    "data_security": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING"],
    "governing_law": ["LEE1", "LEE2", "LEE8"],
    "termination": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING"],
    "warranties": ["LEE1", "UNUSUAL_VALID_DRAFTING", "LEE2"],
    "sla": ["LEE1", "UNUSUAL_VALID_DRAFTING", "LEE2"],
    "assignment": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING"],
}


def _select():
    by_adapter = {}
    for c in CASES:
        by_adapter.setdefault(c["adapter"], []).append(c)
    selected = []
    for adapter, families in _by_adapter_family_targets.items():
        used = set()
        for fam in families:
            for c in by_adapter[adapter]:
                key = (c["lee_category"], c["family"])
                if c["id"] in used:
                    continue
                if (fam.startswith("LEE") and str(c["lee_category"]) == fam[3:]) or c["family"] == fam:
                    if c["id"] not in [s["id"] for s in selected]:
                        selected.append(c)
                        used.add(c["id"])
                        break
    return selected


def main():
    cases = _select()
    print(f"Selected {len(cases)} cases across {len(set(c['adapter'] for c in cases))} adapters")
    results = []
    for case in cases:
        adapter = case["adapter"]
        extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS[adapter]
        policy = policy_cls(**case.get("policy", {}))
        run_states = []
        run_established = []
        for i in range(5):
            facts = extract_fn(case["text"])
            decision = evaluate_fn(facts, policy)
            run_states.append(decision.state)
            run_established.append(getattr(facts, "absence_state", None) if facts is not None else "NONE")
            print(f"{case['id']} run {i+1}/5: state={decision.state} absence_state={run_established[-1]}", flush=True)
        clean_states = {"ACCEPT", "ACCEPT_WITH_NOTE"}
        unsafe_transition = any(s not in clean_states for s in run_states) and any(s in clean_states for s in run_states)
        results.append({
            "case_id": case["id"], "adapter": adapter, "expected": case["expected"],
            "run_states": run_states, "run_absence_states": run_established,
            "state_variation": len(set(run_states)) > 1,
            "unsafe_clean_transition": unsafe_transition,
        })

    out_path = os.path.join(os.path.dirname(__file__), "repeatability_remediated_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    n_unsafe = sum(1 for r in results if r["unsafe_clean_transition"])
    n_var = sum(1 for r in results if r["state_variation"])
    print(f"\n{len(cases)} cases x 5 runs = {len(cases)*5} real calls attempted. "
          f"POLICY_DECISION_VARIATION: {n_var}/{len(cases)}. "
          f"UNSAFE_CLEAN_TRANSITIONS: {n_unsafe}/{len(cases)} (must be 0). Wrote {out_path}")


if __name__ == "__main__":
    main()
