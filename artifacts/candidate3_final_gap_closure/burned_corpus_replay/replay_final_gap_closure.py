#!/usr/bin/env python3
"""Candidate 3 remediation -- BURNED CORPUS REPLAY (regression only, NOT
independent validation).

Re-runs the SAME frozen 240-case corpus from
artifacts/candidate3_real_ai_adversarial/corpus/cases.py -- imported
UNMODIFIED, never copied or edited -- against the remediated code, with
the real OpenAI semantic discovery path enabled for this process only:

  - FACT_ADMISSION_MODE=enforced (must be set BEFORE any adapter module is
    imported, since each adapter reads its own <ADAPTER>_SEMANTIC_
    DISCOVERY_ENABLED flag at import time).
  - indemnification_policy_engine.SEMANTIC_PROVIDER patched to "REAL" at
    process start (a Python-process-local attribute override; nothing on
    disk changes) since that adapter's primary discovery switch is not
    environment-driven.

Captures a full structured trace per case by monkeypatching the THREE
real network-call entry points every adapter actually calls
(fact_admission.discover_candidate_spans, fact_admission.verify_and_ground,
semantic_discovery_real.discover_candidate_spans_real) so every AI
candidate, its verification result, its grounding result, and its
admission status are recorded -- never inferred after the fact from the
final policy decision alone.

This corpus was already declared BURNED in the prior real-AI adversarial
mission. Passing it here is REGRESSION EVIDENCE ONLY, never independent
validation.
"""
import os
import sys
import json
import time
import hashlib
import traceback

os.environ["FACT_ADMISSION_MODE"] = "enforced"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)
# Import the ORIGINAL burned corpus directory's cases.py -- never a copy.
sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate3_real_ai_adversarial", "corpus"))

import fact_admission as fa  # noqa: E402
import semantic_discovery_real as sdr  # noqa: E402
import indemnification_policy_engine as ie  # noqa: E402
import policy_engine_core as core  # noqa: E402

# IMPORTANT: import the burned corpus's `cases` module before importing
# replay_candidate2 (which has its own same-named `cases.py` for
# Candidate 1's burned 74-case corpus in a different directory). Python
# caches modules by bare name in sys.modules, so importing this one first
# guarantees `from cases import CASES` below (and any internal import of
# `cases` inside replay_candidate2) resolves to the Candidate 3 corpus,
# not Candidate 1's.
from cases import CASES  # noqa: E402

sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
import replay_candidate2 as rc2  # noqa: E402  -- reuses the 12 FakePolicy fixtures + ADAPTERS map

ie.SEMANTIC_PROVIDER = "REAL"

# ---------------------------------------------------------------------------
# Instrumentation: wrap the three real call-path entry points to log every
# AI candidate's full lifecycle, keyed to the currently-running case id.
# ---------------------------------------------------------------------------
_TRACE = {"case_id": None, "entries": []}

_orig_discover = fa.discover_candidate_spans
_orig_verify_and_ground = fa.verify_and_ground
_orig_discover_real = sdr.discover_candidate_spans_real


def _serialize_candidate(c):
    v = c.semantic_verification_result
    g = c.deterministic_grounding_result
    return {
        "evidence_span": c.evidence_span,
        "admission_status": c.admission_status,
        "non_admission_reason": c.non_admission_reason,
        "ai_status": v.status if v else None,
        "ai_evidence_quote": v.evidence_quote if v else None,
        "ai_condition_quote": getattr(v, "condition_quote", None) if v else None,
        "ai_exception_quote": getattr(v, "exception_quote", None) if v else None,
        "ai_cross_reference_text": getattr(v, "cross_reference_text", None) if v else None,
        "ai_definition_term": getattr(v, "definition_term", None) if v else None,
        "ai_reasoning": getattr(v, "reasoning", None) if v else None,
        "grounding_passed": g.passed if g else None,
        "grounding_reasons": g.reasons if g else None,
        "condition": c.condition,
        "exception": c.exception,
        "cross_reference": c.cross_reference,
        "definition_resolution_status": c.definition_resolution.status if c.definition_resolution else None,
        "cross_reference_resolution_status": c.cross_reference_resolution.status if c.cross_reference_resolution else None,
        "competing_readings_count": len(c.competing_readings),
        "competing_readings_grounded": sum(1 for r in c.competing_readings if r.grounded),
    }


def _patched_discover(text, clause_type, focus_description, *, api_key=None):
    t0 = time.perf_counter()
    result = _orig_discover(text, clause_type, focus_description, api_key=api_key)
    _TRACE["entries"].append({
        "case_id": _TRACE["case_id"], "stage": "discover", "path": "fact_admission",
        "clause_type": clause_type, "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "candidates_found": [c.evidence_span for c in result],
    })
    return result


def _patched_verify_and_ground(candidate, document_text, proposition, *, api_key=None):
    t0 = time.perf_counter()
    result = _orig_verify_and_ground(candidate, document_text, proposition, api_key=api_key)
    _TRACE["entries"].append({
        "case_id": _TRACE["case_id"], "stage": "verify_and_ground", "path": "fact_admission",
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "candidate": _serialize_candidate(result),
    })
    return result


def _patched_discover_real(text, concept, *, api_key=None):
    t0 = time.perf_counter()
    result = _orig_discover_real(text, concept, api_key=api_key)
    _TRACE["entries"].append({
        "case_id": _TRACE["case_id"], "stage": "discover", "path": "semantic_discovery_real",
        "concept": concept, "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "candidates_found": [c.evidence_span for c in result] if result else [],
    })
    return result


fa.discover_candidate_spans = _patched_discover
fa.verify_and_ground = _patched_verify_and_ground
sdr.discover_candidate_spans_real = _patched_discover_real
# Re-point each adapter module's already-bound local aliases: they do
# `import fact_admission as _fa` INSIDE their functions at call time, so
# they always resolve `_fa.discover_candidate_spans` via the module object
# in sys.modules -- patching the attributes above is sufficient, no
# per-adapter re-import needed.
ie._discover_candidate_spans_simulated = ie._discover_candidate_spans_simulated  # unchanged, SIMULATED unused now


# ---------------------------------------------------------------------------
# Per-adapter "was anything deterministically established" signal --
# inspected directly from each adapter's own Facts dataclass, never
# inferred from the high-level policy decision alone (a permissive default
# policy could reach ACCEPT/NOT_APPLICABLE regardless of what was found).
# ---------------------------------------------------------------------------

def _established_signal(adapter, facts):
    if facts is None:
        return False
    if adapter == "limitation_of_liability":
        return bool(facts.provisions) or facts.controlling_provision is not None
    if adapter == "indemnification":
        return bool(facts.obligations)
    if adapter == "confidentiality":
        return bool(facts.obligations)
    if adapter == "payment_terms":
        return facts.net_days is not None
    if adapter == "ip_ownership":
        return bool(facts.ownership_attributions)
    if adapter == "insurance":
        return any(cov.established for cov in facts.coverages.values())
    if adapter == "data_security":
        return (facts.breach_notification_hours is not None or facts.breach_notification_explicitly_disclaimed
                or facts.breach_notification_ambiguous_unit or facts.breach_without_undue_delay
                or bool(facts.role_attributions))
    if adapter == "governing_law":
        return facts.jurisdiction is not None
    if adapter == "termination":
        return bool(facts.rights)
    if adapter == "warranties":
        return any(cat.established for cat in facts.categories.values())
    if adapter == "sla":
        return facts.uptime_percent is not None or facts.service_credit_present is True
    if adapter == "assignment":
        return bool(facts.restrictions) or facts.unrestricted_assignment
    raise ValueError(f"no established_signal rule for adapter {adapter}")


def _bucket_for_state(state):
    return rc2._bucket_for_state(state)


# ---------------------------------------------------------------------------
# Grading -- transparent, rule-based, documented in REAL_AI_ADVERSARIAL_
# REPORT.md rather than left as an opaque pass/fail.
# ---------------------------------------------------------------------------

def _grade(case, established, decision):
    expected = case["expected"]
    bucket = _bucket_for_state(decision.state)
    unresolved = getattr(decision, "unresolved_facts", None) or []
    failure_classes = []
    passed = True

    if expected == "YES_OPERATIVE":
        if not established:
            passed = False
            failure_classes.append("MISSED_OPERATIVE_FACT")
    elif expected == "NO_NOT_OPERATIVE":
        if established:
            passed = False
            if bucket == "CLEAN":
                failure_classes.append("FALSE_OPERATIVE_TO_CLEAN")
                failure_classes.append("FALSE_SAFE")
            else:
                failure_classes.append("FALSE_OPERATIVE_NON_CLEAN")
    elif expected in ("YES_BUT_CONDITIONAL", "YES_BUT_EXCEPTION"):
        if not established:
            passed = False
            failure_classes.append("MISSED_OPERATIVE_FACT")
        elif bucket == "CLEAN" and decision.state == core.ACCEPT and not unresolved:
            passed = False
            failure_classes.append("MATERIAL_CONTEXT_SILENTLY_LOST")
    elif expected == "AMBIGUOUS":
        if decision.state == core.ACCEPT:
            passed = False
            failure_classes.append("ARBITRARILY_SELECTED_COMPETING_READING")
    elif expected == "CROSS_REFERENCE_DEPENDENT":
        if decision.state == core.ACCEPT:
            passed = False
            failure_classes.append("UNRESOLVED_CROSS_REFERENCE_TO_CLEAN")
    elif expected == "DEFINITION_DEPENDENT":
        if decision.state == core.ACCEPT:
            passed = False
            failure_classes.append("UNRESOLVED_DEFINITION_TO_CLEAN")
    elif expected == "MISSING_CLAUSE":
        if bucket != "NOT_APPLICABLE":
            passed = False
            failure_classes.append("FALSE_OPERATIVE_ON_MISSING_CLAUSE" if established else "UNEXPECTED_NON_ABSENT_BUCKET")
    else:
        raise ValueError(f"unknown expected label {expected!r}")

    return passed, failure_classes, bucket


def run_case(case):
    adapter = case["adapter"]
    extract_fn, evaluate_fn, policy_cls = rc2.ADAPTERS[adapter]
    policy = policy_cls(**case.get("policy", {}))
    text = case["text"]

    _TRACE["case_id"] = case["id"]
    _TRACE["entries"] = []
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
            "lee_category": case["lee_category"], "input_text": text, "expected": case["expected"],
            "notes": case.get("notes", ""), "error": error, "trace": list(_TRACE["entries"]),
            "passed": False, "failure_classes": ["RUNNER_ERROR"], "bucket": "RUNNER_ERROR",
        }

    established = _established_signal(adapter, facts)
    passed, failure_classes, bucket = _grade(case, established, decision)

    return {
        "case_id": case["id"], "adapter": adapter, "family": case["family"],
        "lee_category": case["lee_category"], "input_text": text, "expected": case["expected"],
        "notes": case.get("notes", ""),
        "established_signal": established,
        "decision_state": decision.state, "decision_bucket": bucket,
        "decision_explanation": decision.explanation,
        "decision_unresolved_facts": list(getattr(decision, "unresolved_facts", None) or []),
        "facts_repr": repr(facts),
        "trace": list(_TRACE["entries"]),
        "passed": passed, "failure_classes": failure_classes,
    }


def main():
    corpus_json = json.dumps(CASES, sort_keys=True).encode("utf-8")
    corpus_hash = hashlib.sha256(corpus_json).hexdigest()
    print(f"CORPUS_SHA256={corpus_hash}", flush=True)
    print(f"TOTAL_CASES={len(CASES)}", flush=True)

    out_path = os.path.join(os.path.dirname(__file__), "raw_results.jsonl")
    results = []
    t_start = time.time()
    with open(out_path, "w") as f:
        for i, case in enumerate(CASES):
            r = run_case(case)
            results.append(r)
            f.write(json.dumps(r, default=str) + "\n")
            f.flush()
            print(f"[{i+1}/{len(CASES)}] {case['id']} expected={case['expected']} "
                  f"passed={r.get('passed')} bucket={r.get('bucket', r.get('decision_bucket'))} "
                  f"elapsed_total={time.time()-t_start:.0f}s", flush=True)

    passed_n = sum(1 for r in results if r.get("passed"))
    print(f"DONE: {passed_n}/{len(results)} passed. Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
