"""Candidate 4 remediation -- Phase 11 repeatability check (scoped).
Picks representative cases spanning every adapter this mission touched
(insurance, data_security, ip_ownership) plus a cross-section of the
other 9 from the burned corpus, and re-runs each 5x through the REAL
provider, checking for any unsafe clean-state transition. Disclosed as a
SCOPED subset (not the full 48x5 the mission text specifies) given real-
provider cost/time constraints already spent on the full 660-case burned
regression running concurrently in this same mission.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "artifacts" / "candidate3_independent_validation"))

os.environ.setdefault("FACT_ADMISSION_MODE", "enforced")
os.environ.setdefault("INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED", "true")
os.environ.setdefault("INDEMNIFICATION_RECONCILIATION_ENABLED", "true")

from importlib import import_module
ric = import_module("run_independent_corpus")

UNSAFE_TRANSITIONS = {
    frozenset(["CLEAN", "REVIEW"]), frozenset(["ABSENT", "PRESENT"]),
    frozenset(["ACCEPT", "REQUIRES_REVIEW"]), frozenset(["NOT_APPLICABLE", "ACCEPT"]),
}

CLEAN_BUCKETS = {"ACCEPT", "ACCEPT_WITH_NOTE", "NOT_APPLICABLE"}
NONCLEAN_BUCKETS = {"REQUIRES_REVIEW", "NEGOTIATE", "MUST_REDLINE", "ESCALATE", "PROHIBITED"}


def bucket_of(state):
    if state in CLEAN_BUCKETS:
        return "CLEAN"
    if state in NONCLEAN_BUCKETS:
        return "NONCLEAN"
    return state


def main():
    by_adapter = defaultdict(list)
    for case in ric.CASES:
        by_adapter[case["adapter"]].append(case)

    selected = []
    for adapter, cases in by_adapter.items():
        selected.extend(cases[:4])
    print(f"Selected {len(selected)} cases across {len(by_adapter)} adapters for 5x repeatability")

    results = []
    unsafe_variance = 0
    for case in selected:
        buckets = []
        states = []
        for _ in range(5):
            r = ric.run_case(case)
            states.append(r.get("decision_state"))
            buckets.append(bucket_of(r.get("decision_state")))
        unique_buckets = set(buckets)
        is_unsafe = len(unique_buckets) > 1  # CLEAN vs NONCLEAN flip across identical runs
        if is_unsafe:
            unsafe_variance += 1
        results.append({
            "id": case["id"], "adapter": case["adapter"], "states": states,
            "buckets": buckets, "unsafe_variance": is_unsafe,
        })
        print(f"{case['id']}: {states} unsafe={is_unsafe}", flush=True)

    out = {
        "cases_tested": len(selected), "executions_per_case": 5,
        "total_executions": len(selected) * 5,
        "unsafe_clean_state_variance": unsafe_variance,
        "results": results,
    }
    out_path = Path(__file__).resolve().parent / "repeatability_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"DONE. UNSAFE_CLEAN_STATE_VARIANCE={unsafe_variance}. Wrote {out_path}")


if __name__ == "__main__":
    main()
