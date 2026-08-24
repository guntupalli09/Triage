#!/usr/bin/env python3
"""Candidate 3 -- Section 10 repeatability test.

Selects 2 real-AI-invoking cases per adapter (24 total) from the main
corpus run and re-runs extract_fn -> evaluate_fn 5 times each through the
REAL provider. AI discovery need not be deterministic; what must hold is
that the AUTHORITATIVE decision never drifts from REVIEW/UNRESOLVED to
CLEAN purely because of AI output variation, without newly grounded
deterministic evidence.
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

SELECTED_IDS = [
    "limitation_of_liability-011", "limitation_of_liability-018",
    "indemnification-020", "indemnification-027",
    "confidentiality-044", "confidentiality-051",
    "payment_terms-064", "payment_terms-071",
    "ip_ownership-081", "ip_ownership-099",
    "insurance-111", "insurance-118",
    "data_security-123", "data_security-131",
    "governing_law-141", "governing_law-151",
    "termination-171", "termination-178",
    "warranties-191", "warranties-198",
    "sla-211", "sla-218",
    "assignment-231", "assignment-239",
]


def main():
    cases_by_id = {c["id"]: c for c in CASES}
    assert len(SELECTED_IDS) == 24, len(SELECTED_IDS)
    results = []
    for cid in SELECTED_IDS:
        case = cases_by_id[cid]
        adapter = case["adapter"]
        extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS[adapter]
        policy = policy_cls(**case.get("policy", {}))
        run_states = []
        run_ai_evidence = []
        for i in range(5):
            facts = extract_fn(case["text"])
            decision = evaluate_fn(facts, policy)
            run_states.append(decision.state)
            ai_ev = getattr(facts, "ai_identified_condition", None) or getattr(facts, "ai_identified_exception", None) \
                or getattr(facts, "ai_identified_definition_or_reference", None)
            run_ai_evidence.append(ai_ev)
            print(f"{cid} run {i+1}/5: state={decision.state}", flush=True)
        state_variation = len(set(run_states)) > 1
        ai_variation = len(set(run_ai_evidence)) > 1
        # Forbidden transition: any run REVIEW/UNRESOLVED-ish, another run CLEAN
        clean_states = {"ACCEPT", "ACCEPT_WITH_NOTE"}
        unsafe_transition = any(s not in clean_states for s in run_states) and any(s in clean_states for s in run_states)
        results.append({
            "case_id": cid, "adapter": adapter, "expected": case["expected"],
            "run_states": run_states, "state_variation": state_variation,
            "ai_output_variation": ai_variation,
            "unsafe_review_to_clean_transition": unsafe_transition,
        })

    out_path = os.path.join(os.path.dirname(__file__), "repeatability_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    n_unsafe = sum(1 for r in results if r["unsafe_review_to_clean_transition"])
    n_state_var = sum(1 for r in results if r["state_variation"])
    n_ai_var = sum(1 for r in results if r["ai_output_variation"])
    print(f"\n24 cases x 5 runs. AI_OUTPUT_VARIATION: {n_ai_var}/24. "
          f"POLICY_DECISION_VARIATION: {n_state_var}/24. "
          f"UNSAFE_REVIEW_TO_CLEAN_TRANSITIONS: {n_unsafe}/24 (must be 0). Wrote {out_path}")


if __name__ == "__main__":
    main()
