#!/usr/bin/env python3
"""Phase 3 -- ONE-SHOT execution of the frozen, genuinely-new independent
corpus against FROZEN_CANDIDATE_SHA, with FACT_ADMISSION_MODE=enforced,
POLICY_ENFORCEMENT_MODE=cutover-equivalent semantic discovery enabled for
every adapter, and the real OpenAI provider.

Reuses the ALREADY-VALIDATED grading/instrumentation machinery from
replay_final_gap_closure.py (imported, not copied) -- that machinery is a
scoring RUBRIC, not corpus content, so reusing it does not compromise the
independence of this NEW corpus. This script supplies its own run_case
loop only because the new corpus's case dicts have a different (simpler)
shape than the burned corpus's (no lee_category field).

NO tuning after seeing results. NO production-code changes. Run once.
"""
import os
import sys
import json
import time
import hashlib
import traceback

os.environ["FACT_ADMISSION_MODE"] = "enforced"
os.environ["INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED"] = "true"
os.environ["INDEMNIFICATION_RECONCILIATION_ENABLED"] = "true"
assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY must be set before running this script"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate3_final_gap_closure", "burned_corpus_replay"))

import fact_admission as fa  # noqa: E402
import indemnification_policy_engine as ie  # noqa: E402
ie.SEMANTIC_PROVIDER = "REAL"
import replay_candidate2 as rc2  # noqa: E402
import replay_final_gap_closure as rfgc  # noqa: E402  -- reuse grading/instrumentation only

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "corpus")
CASES = json.load(open(os.path.join(CORPUS_DIR, "cases.json")))
EXPECTED_SHA = open(os.path.join(CORPUS_DIR, "corpus_sha256.txt")).read().strip()
computed_sha = hashlib.sha256(json.dumps(CASES, sort_keys=True).encode("utf-8")).hexdigest()
assert computed_sha == EXPECTED_SHA, (
    f"CORPUS INTEGRITY FAILURE: computed {computed_sha} != frozen {EXPECTED_SHA}. STOP."
)
print(f"Corpus integrity verified: {computed_sha}", flush=True)
print(f"Total cases: {len(CASES)}", flush=True)


def run_case(case):
    adapter = case["adapter"]
    extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS[adapter]
    policy = policy_cls(**case.get("policy", {}))
    text = case["text"]

    rfgc._TRACE["case_id"] = case["id"]
    rfgc._TRACE["entries"] = []
    error = None
    try:
        facts = extract_fn(text)
        decision = evaluate_fn(facts, policy)
    except Exception as exc:  # noqa: BLE001 -- record, never crash the run
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        facts = None
        decision = None

    if error is not None:
        return {
            "case_id": case["id"], "adapter": adapter, "family": case["family"],
            "input_text": text, "expected": case["expected"], "notes": case.get("notes", ""),
            "error": error, "trace": list(rfgc._TRACE["entries"]),
            "passed": False, "failure_classes": ["RUNNER_ERROR"], "bucket": "RUNNER_ERROR",
        }

    established = rfgc._established_signal(adapter, facts)
    # rfgc._grade reads case["lee_category"] only inside error-path dict
    # construction (not in the grading logic itself) -- safe to call
    # directly with our simpler case dict, per direct inspection of
    # replay_final_gap_closure.py's _grade function body.
    passed, failure_classes, bucket = rfgc._grade(case, established, decision)

    return {
        "case_id": case["id"], "adapter": adapter, "family": case["family"],
        "input_text": text, "expected": case["expected"], "notes": case.get("notes", ""),
        "established_signal": established,
        "decision_state": decision.state, "decision_bucket": bucket,
        "decision_explanation": decision.explanation,
        "decision_unresolved_facts": list(getattr(decision, "unresolved_facts", None) or []),
        "facts_repr": repr(facts),
        "trace": list(rfgc._TRACE["entries"]),
        "passed": passed, "failure_classes": failure_classes,
    }


def main():
    out_path = os.path.join(os.path.dirname(__file__), "raw_results.jsonl")
    results = []
    t_start = time.time()
    with open(out_path, "w") as f:
        for i, case in enumerate(CASES):
            r = run_case(case)
            results.append(r)
            f.write(json.dumps(r, default=str) + "\n")
            f.flush()
            print(f"[{i+1}/{len(CASES)}] {case['id']} adapter={case['adapter']} family={case['family']} "
                  f"expected={case['expected']} passed={r.get('passed')} bucket={r.get('bucket', r.get('decision_bucket'))} "
                  f"elapsed_total={time.time()-t_start:.0f}s", flush=True)

    passed_n = sum(1 for r in results if r.get("passed"))
    print(f"DONE: {passed_n}/{len(results)} passed. Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
