#!/usr/bin/env python3
"""Candidate 3 final gap-closure -- Section 18 real-provider repeatability
test.

Selects >=48 adversarial cases spanning all 12 adapters from the burned
corpus (4 per adapter, up from the prior mission's 3), explicitly forces
inclusion of ip_ownership-080 (the confirmed clean-state variance case
from the Candidate 3 remediation mission) as a burned regression case,
and adds 2 fresh DEVELOPMENT-ONLY cases representing the SAME failure
class (an adverb sitting between "owned" and "by" in a passive-voice
ownership statement) so ip_ownership-080 is not the only stability case
for its own failure shape. Runs each through the REAL OpenAI provider 5
independent times.

Records AI candidate-set stability, grounded-fact stability, canonical-
fact (absence_state) stability, and policy-decision stability separately,
per Section 18. Required: PROVIDER_INDUCED_CLEAN_STATE_VARIANCE = 0.
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
import fact_admission as fa  # noqa: E402

# 4 cases per adapter x 12 adapters = 48, chosen to include at least one
# LEE1 (positive control), one descriptive/hypothetical/negotiation/quoted
# family case, one condition/exception/ambiguous family case, and one
# additional distinctive family per adapter.
_by_adapter_family_targets = {
    "limitation_of_liability": ["LEE1", "LEE2", "LEE6", "LEE7"],
    "indemnification": ["LEE1", "LEE2", "LEE6", "LEE7"],
    "confidentiality": ["LEE1", "LEE2", "LEE8", "NEGATED"],
    "payment_terms": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING", "LEE8"],
    "ip_ownership": ["LEE1", "UNUSUAL_VALID_DRAFTING", "LEE2", "LEE7"],
    "insurance": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING", "LEE6"],
    "data_security": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING", "NEGATED"],
    "governing_law": ["LEE1", "LEE2", "LEE8", "UNUSUAL_VALID_DRAFTING"],
    "termination": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING", "LEE8"],
    "warranties": ["LEE1", "UNUSUAL_VALID_DRAFTING", "LEE2", "LEE6"],
    "sla": ["LEE1", "UNUSUAL_VALID_DRAFTING", "LEE2", "LEE8"],
    "assignment": ["LEE1", "LEE2", "UNUSUAL_VALID_DRAFTING", "LEE8"],
}

# Fresh, development-only variants of ip_ownership-080's exact failure
# class (an adverb between "owned" and "by" in a passive-voice ownership
# statement) -- NOT from the burned corpus, freshly worded for this
# mission, so ip_ownership-080 is not the only stability case for its
# own failure shape (Section 18's explicit instruction).
DEV_ONLY_EXTRA_CASES = [
    {"id": "dev-ipownership-080-class-01", "adapter": "ip_ownership",
     "text": ("12. Ownership. All deliverables produced by Contractor under this "
              "engagement shall be owned exclusively by Client upon acceptance."),
     "expected": "YES_OPERATIVE", "policy": {}},
    {"id": "dev-ipownership-080-class-02", "adapter": "ip_ownership",
     "text": ("11. Intellectual Property. All custom software developed for Buyer "
              "under this Order Form shall be owned solely by Buyer."),
     "expected": "YES_OPERATIVE", "policy": {}},
    # Fresh, development-only variant of ip_ownership-086's exact failure
    # class (same-clause "except for X, which Y retains" exception
    # attached to an ownership statement) -- freshly worded, not from the
    # burned corpus, per Section 18's instruction that ip_ownership-086
    # (like ip_ownership-080) not be the only stability case for its
    # failure shape.
    {"id": "dev-ipownership-086-class-01", "adapter": "ip_ownership",
     "text": ("12. Intellectual Property. All work product shall be owned by Client, "
              "except for Contractor's proprietary tools and libraries used in its creation, which "
              "Contractor retains."),
     "expected": "YES_BUT_EXCEPTION", "policy": {}},
]


def _select():
    by_adapter = {}
    for c in CASES:
        by_adapter.setdefault(c["adapter"], []).append(c)
    selected = []
    for adapter, families in _by_adapter_family_targets.items():
        used = set()
        for fam in families:
            for c in by_adapter[adapter]:
                if c["id"] in used:
                    continue
                if (fam.startswith("LEE") and str(c["lee_category"]) == fam[3:]) or c["family"] == fam:
                    if c["id"] not in [s["id"] for s in selected]:
                        selected.append(c)
                        used.add(c["id"])
                        break
    # Force-include ip_ownership-080 and ip_ownership-086 as burned
    # regression cases if not already selected by the family-target scan
    # above -- ip_ownership-086 is the NEW clean-state variance case this
    # mission found and fixed via the Section 18 repeatability test.
    for forced_id in ("ip_ownership-080", "ip_ownership-086"):
        if forced_id not in [s["id"] for s in selected]:
            for c in CASES:
                if c["id"] == forced_id:
                    selected.append(c)
                    break
    return selected


def main():
    cases = _select() + DEV_ONLY_EXTRA_CASES
    print(f"Selected {len(cases)} cases across {len(set(c['adapter'] for c in cases))} adapters "
          f"({len(cases) * 5} real executions planned)", flush=True)

    orig_discover = fa.discover_candidate_spans

    results = []
    for case in cases:
        adapter = case["adapter"]
        extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS[adapter]
        policy = policy_cls(**case.get("policy", {}))
        run_states = []
        run_absence_states = []
        run_candidate_counts = []
        run_candidate_spans = []

        candidate_log = {"count": None, "spans": None}

        def _patched_discover(text, clause_type, focus_description, *, api_key=None, _log=candidate_log):
            result = orig_discover(text, clause_type, focus_description, api_key=api_key)
            _log["count"] = len(result)
            _log["spans"] = [c.evidence_span for c in result]
            return result

        fa.discover_candidate_spans = _patched_discover
        try:
            for i in range(5):
                candidate_log["count"] = None
                candidate_log["spans"] = None
                facts = extract_fn(case["text"])
                decision = evaluate_fn(facts, policy)
                run_states.append(decision.state)
                run_absence_states.append(getattr(facts, "absence_state", None) if facts is not None else "NONE")
                run_candidate_counts.append(candidate_log["count"])
                run_candidate_spans.append(candidate_log["spans"])
                print(f"{case['id']} run {i+1}/5: state={decision.state} "
                      f"absence_state={run_absence_states[-1]} candidates={candidate_log['count']}", flush=True)
        finally:
            fa.discover_candidate_spans = orig_discover

        clean_states = {"ACCEPT", "ACCEPT_WITH_NOTE"}
        unsafe_transition = any(s not in clean_states for s in run_states) and any(s in clean_states for s in run_states)
        results.append({
            "case_id": case["id"], "adapter": adapter, "expected": case["expected"],
            "run_states": run_states,
            "run_absence_states": run_absence_states,
            "run_candidate_counts": run_candidate_counts,
            "run_candidate_spans": run_candidate_spans,
            "candidate_set_varied": len(set(tuple(s or []) for s in run_candidate_spans)) > 1,
            "canonical_fact_varied": len(set(run_absence_states)) > 1,
            "policy_decision_varied": len(set(run_states)) > 1,
            "unsafe_clean_transition": unsafe_transition,
        })

    out_path = os.path.join(os.path.dirname(__file__), "repeatability_final_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    n_unsafe = sum(1 for r in results if r["unsafe_clean_transition"])
    n_candidate_var = sum(1 for r in results if r["candidate_set_varied"])
    n_canonical_var = sum(1 for r in results if r["canonical_fact_varied"])
    n_decision_var = sum(1 for r in results if r["policy_decision_varied"])
    print(f"\n{len(cases)} cases x 5 runs = {len(cases)*5} real calls attempted. "
          f"AI_CANDIDATE_SET_VARIED: {n_candidate_var}/{len(cases)}. "
          f"CANONICAL_FACT_VARIED: {n_canonical_var}/{len(cases)}. "
          f"POLICY_DECISION_VARIED: {n_decision_var}/{len(cases)}. "
          f"PROVIDER_INDUCED_CLEAN_STATE_VARIANCE (unsafe transitions): {n_unsafe}/{len(cases)} (must be 0). "
          f"Wrote {out_path}")


if __name__ == "__main__":
    main()
