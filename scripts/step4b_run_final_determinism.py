"""Step 4B FINAL VALIDATION -- Phase 5: Determinism Reproduction.

Uses the preselected >=75 high-complexity replay-pool documents (100
here: 'high-complexity-replay-pool' + 'compound-multi-interaction'
families), each replayed 5x through the REAL interaction_engine_core.evaluate
+ document_aggregation.aggregate_document_state, comparing authoritative
artifacts (policy states, interaction states, document_state) -- never
timestamps/ids/prose. Not a re-run of the whole corpus, no scoring change.
"""
import sys
sys.path.insert(0, ".")
import json
from collections import defaultdict

import interaction_engine_core as ixc
import interaction_rules as ixr
import document_aggregation as agg
from policy_engine_core import PolicyDecision as PD

from benchmarks.step4b_final_corpus import CASES

REPLAY_FAMILIES = ("high-complexity-replay-pool", "compound-multi-interaction")


def _strip(d):
    non_authoritative = {"explanation", "required_action", "contract_language", "extracted_summary",
                          "policy_limit_summary", "rule_id", "start_index", "end_index"}
    if isinstance(d, dict):
        return {k: _strip(v) for k, v in sorted(d.items()) if k not in non_authoritative}
    if isinstance(d, list):
        return [_strip(v) for v in d]
    return d


def _run_once(decisions_raw, overall_risk, mode):
    pd_objs = {}
    for ct, d in decisions_raw.items():
        pd_objs[ct] = PD(
            rule_id=d["rule_id"], clause_type=d["clause_type"], state=d["state"],
            contract_language="", extracted_summary="", policy_limit_summary="",
            required_action="", explanation="", negotiation_ladder=[],
            category_treatments=d["category_treatments"], unresolved_facts=[],
            start_index=d["start_index"], end_index=d["end_index"],
            controlling_provision=d["controlling_provision"],
            interaction_facts=d["interaction_facts"], reconciliation=None,
        )
    ix_results = ixc.evaluate(pd_objs, ixr.LAUNCH_CATALOG)
    interaction_decisions = {r.interaction_id: r.as_dict() for r in ix_results}
    doc_result = agg.aggregate_document_state(overall_risk, decisions_raw, interaction_decisions, mode)
    return _strip({"policy_decisions": decisions_raw, "interaction_decisions": interaction_decisions,
                    "document_state": doc_result["document_state"]})


def run():
    replay_cases = [c for c in CASES if c["family"] in REPLAY_FAMILIES]
    results = []
    for c in replay_cases:
        p = c["payload"]
        runs = [_run_once(p["policy_decisions"], p["overall_risk"], p["mode"]) for _ in range(5)]
        all_equal = all(r == runs[0] for r in runs)
        results.append({"id": c["id"], "family": c["family"], "all_equal": all_equal,
                         "document_state": runs[0]["document_state"]})
    return results


if __name__ == "__main__":
    results = run()
    total = len(results)
    print(f"Total replay-pool documents: {total} (each replayed 5x)")
    contradictions = [r for r in results if not r["all_equal"]]
    print(f"HARD GATE contradictory_authoritative_decision == 0: {len(contradictions)} -> "
          f"{'PASS' if not contradictions else 'FAIL'}")
    for r in contradictions[:20]:
        print(f"  {r}")

    by_fam = defaultdict(lambda: {"total": 0, "equal": 0})
    for r in results:
        by_fam[r["family"]]["total"] += 1
        by_fam[r["family"]]["equal"] += r["all_equal"]
    print("\n=== by family ===")
    for f, v in by_fam.items():
        print(f"  {f}: {v['equal']}/{v['total']} deterministic")

    with open("artifacts/step4b/final_validation/determinism_results.json", "w") as f:
        json.dump({"results": results, "total": total, "contradictions": len(contradictions)}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/final_validation/determinism_results.json")
