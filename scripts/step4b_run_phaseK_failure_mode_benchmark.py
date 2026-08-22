"""Step 4B Phase K runner -- calls the real production functions directly,
through the highest realistic boundary for each dependency-failure target:

- evaluator.LLMEvaluator.evaluate / _validate_result (explanation-provider
  unavailable/exception/malformed/contradictory output)
- document_aggregation.aggregate_document_state (corrupt/missing decision
  payloads, malformed configuration state)
- policy_enforcement._segment_matches_context (malformed deal_value)
- main.build_enhanced_issues (malformed severity)
- policy_enforcement.evaluate_active_policies (one adapter raising, real
  isolation boundary -- collaborator functions patched, the function under
  test is real)
- interaction_engine_core.evaluate (one rule's predicate raising, real
  isolation boundary)
- main._document_state_for_contract (malformed/incomplete persisted Contract
  fields)
"""
import os
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/step4b_phaseK_runner.db")
import sys
sys.path.insert(0, ".")

import json
import types
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import patch

import main
import playbook_authoring as pa
import policy_enforcement as pe
import interaction_engine_core as ixc
import interaction_rules as ixr
import document_aggregation as agg
from policy_engine_core import PolicyDecision
from evaluator import LLMEvaluator
from benchmarks.step4b_phaseK_failure_mode_benchmark import CASES, MATERIAL_STATES

_ev = LLMEvaluator.__new__(LLMEvaluator)
_ev.client = None
_ev.model = "test-model"

_SOME_FINDING = {"rule_id": "R1", "rule_name": "Some Rule", "title": "Some Finding",
                  "severity": "high", "matched_excerpt": "excerpt", "rationale": "why", "context": ""}


def _fake_client(raiser=None, raw_content=None):
    """Builds a minimal fake OpenAI-shaped client. `raiser`, if given, is
    called instead of returning a response (simulating a network/API
    exception). Otherwise the response's message.content is `raw_content`."""
    class _Msg:
        def __init__(self, content):
            self.content = content

    class _Choice:
        def __init__(self, content):
            self.message = _Msg(content)

    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]

    class _Completions:
        def create(self, **kwargs):
            if raiser is not None:
                raise raiser
            return _Resp(raw_content)

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    return SimpleNamespace(chat=_Chat())


_EXC_MAP = {
    "TimeoutError": TimeoutError("simulated timeout"),
    "ConnectionError": ConnectionError("simulated connection error"),
    "ValueError": ValueError("simulated value error"),
    "RuntimeError": RuntimeError("simulated runtime error"),
    "json.JSONDecodeError-equivalent": json.JSONDecodeError("simulated bad json", "{", 0),
    "OSError": OSError("simulated os error"),
    "MemoryError": MemoryError("simulated memory error"),
    "AttributeError": AttributeError("simulated attribute error"),
}


def _pd(clause_type, state="ACCEPT"):
    return PolicyDecision(
        rule_id="TEST", clause_type=clause_type, state=state,
        contract_language="", extracted_summary="", policy_limit_summary="",
        required_action="", explanation="", negotiation_ladder=[],
        category_treatments=[], unresolved_facts=[], start_index=0, end_index=10,
        controlling_provision={"label": f"{clause_type} clause", "excerpt": "...", "start_index": "0", "end_index": "10"},
        interaction_facts={}, reconciliation=None,
    )


_ALL_CLEAN_DECISIONS = {ct: _pd(ct) for ct in pa.CLAUSE_TYPES}


def _apply_active_policies_isolation(raising_clause_type):
    """Real policy_enforcement.evaluate_active_policies, called with the
    real active_positions/build_policy_rule_for_enforcement/_ENGINE_FUNCS
    collaborators patched to isolate the boundary under test: every clause
    type has some ACTIVE position object (content irrelevant -- rule
    construction is patched to a no-op), and exactly one clause type's
    extract_fn raises. This exercises evaluate_active_policies' own
    try/except isolation logic for real, the same isolation contract its
    docstring describes."""
    positions = {ct: SimpleNamespace(id=i, clause_type=ct) for i, ct in enumerate(pa.CLAUSE_TYPES)}

    def _raising_extract(text):
        raise RuntimeError("simulated adapter failure")

    def _ok_extract(text):
        return {}

    def _ok_evaluate(facts, rule, source=""):
        return _pd(rule.clause_type if hasattr(rule, "clause_type") else "unknown", "ACCEPT")

    fake_engine_funcs = {}
    for ct in pa.CLAUSE_TYPES:
        if ct == raising_clause_type:
            fake_engine_funcs[ct] = (_raising_extract, _ok_evaluate)
        else:
            fake_engine_funcs[ct] = (_ok_extract, (lambda facts, rule, source="", _ct=ct: _pd(_ct, "ACCEPT")))

    with patch.object(pa, "build_policy_rule_for_enforcement", lambda position: SimpleNamespace(clause_type=position.clause_type)), \
         patch.object(pa, "_ENGINE_FUNCS", fake_engine_funcs), \
         patch.object(pe, "_revision_metadata_for", lambda position: {"policy_position_id": position.id}):
        playbook = SimpleNamespace(id=1, name="PB")
        outcomes = pe.evaluate_active_policies(db=None, playbook=playbook, contract_text="x", active_positions=positions)

    by_ct = {o.clause_type: o for o in outcomes}
    raising_outcome = by_ct.get(raising_clause_type)
    others = [o for ct, o in by_ct.items() if ct != raising_clause_type]
    raising_ok = raising_outcome is not None and raising_outcome.error is not None and raising_outcome.decision is None
    others_ok = all(o.error is None and o.decision is not None for o in others)
    return {"other_clauses_unaffected": others_ok, "raising_clause_becomes_error": raising_ok}


def _interaction_engine_predicate_raises(raising_rule_index):
    rules = list(ixr.LAUNCH_CATALOG)
    target = rules[raising_rule_index]

    def _raising_predicate(decisions):
        raise RuntimeError("simulated predicate failure")

    patched_rule = ixc.InteractionRule(
        interaction_id=target.interaction_id, label=target.label, kind=target.kind,
        participating_clause_types=target.participating_clause_types, ceiling_state=target.ceiling_state,
        predicate=_raising_predicate, version=target.version,
    )
    rules[raising_rule_index] = patched_rule

    results = ixc.evaluate(_ALL_CLEAN_DECISIONS, rules)
    by_id = {r.interaction_id: r for r in results}
    raising_result = by_id[target.interaction_id]
    others = [r for r in results if r.interaction_id != target.interaction_id]
    raising_ok = raising_result.state == ixc.EVALUATION_ERROR
    others_ok = all(r.state != ixc.EVALUATION_ERROR for r in others)
    return {"other_rules_unaffected": others_ok, "raising_rule_becomes_error": raising_ok}


def _document_state_for_contract_no_crash(payload):
    contract = SimpleNamespace(
        overall_risk=payload.get("overall_risk"),
        policy_decisions_json=payload.get("policy_decisions_json"),
        interaction_decisions_json=payload.get("interaction_decisions_json"),
    )
    state = main._document_state_for_contract(contract)
    return {"no_crash": True, "not_clean": state not in ("CLEAN", "CLEAN_LEGACY_ATTENTION"), "state": state}


def _run_one(c):
    target = c["target"]
    p = c["payload"]

    if target == "evaluate_provider_none":
        _ev.client = None
        result = _ev.evaluate(findings=[_SOME_FINDING], overall_risk="high")
        return {"returns_none": result is None}

    if target == "evaluate_client_raises":
        _ev.client = _fake_client(raiser=_EXC_MAP[p["exception_family"]])
        result = _ev.evaluate(findings=[_SOME_FINDING], overall_risk="high")
        return {"returns_none": result is None}

    if target == "evaluate_malformed_json_response":
        _ev.client = _fake_client(raw_content=p["raw_content"])
        result = _ev.evaluate(findings=[_SOME_FINDING], overall_risk="high")
        return {"returns_none": result is None}

    if target == "validate_result_rejects_malformed":
        try:
            _ev._validate_result(p["malformed_output"])
            return {"raises": False}
        except Exception:
            return {"raises": True}

    if target == "aggregate_no_crash":
        try:
            result = agg.aggregate_document_state(p["overall_risk"], p["policy_decisions"], p["interaction_decisions"], p["mode"])
            out = {"no_crash": True, "state": result["document_state"]}
            if "not_clean" in c["expected"]:
                out["not_clean"] = result["document_state"] not in ("CLEAN", "CLEAN_LEGACY_ATTENTION")
            return out
        except Exception as exc:
            return {"no_crash": False, "exception": f"{type(exc).__name__}: {exc}"}

    if target == "segment_match_no_crash":
        try:
            position = SimpleNamespace(
                segment_business_unit=None, segment_customer_type=None,
                segment_deal_value_min=p["segment_min"], segment_deal_value_max=p["segment_max"],
            )
            matched = pe._segment_matches_context(position, {"deal_value": p["deal_value"]})
            return {"no_crash": True, "matches_bound": matched}
        except Exception as exc:
            return {"no_crash": False, "exception": f"{type(exc).__name__}: {exc}"}

    if target == "build_enhanced_issues_no_crash":
        try:
            out = main.build_enhanced_issues([p["finding"]], {"top_issues": []})
            return {"no_crash": True, "count": len(out)}
        except Exception as exc:
            return {"no_crash": False, "exception": f"{type(exc).__name__}: {exc}"}

    if target == "apply_active_policies_isolation":
        return _apply_active_policies_isolation(p["raising_clause_type"])

    if target == "interaction_engine_predicate_raises":
        return _interaction_engine_predicate_raises(p["raising_rule_index"])

    if target == "document_state_for_contract_no_crash":
        try:
            return _document_state_for_contract_no_crash(p)
        except Exception as exc:
            return {"no_crash": False, "exception": f"{type(exc).__name__}: {exc}"}

    raise ValueError(f"unknown target {target}")


def run():
    rows = []
    for c in CASES:
        try:
            actual = _run_one(c)
        except Exception as exc:
            actual = {"no_crash": False, "unhandled_exception": f"{type(exc).__name__}: {exc}"}
        correct = all(actual.get(k) == v for k, v in c["expected"].items())
        rows.append({"id": c["id"], "family": c["family"], "target": c["target"],
                     "expected": c["expected"], "actual": actual, "correct": correct, "notes": c["notes"]})
    return rows


if __name__ == "__main__":
    rows = run()
    total = len(rows)
    correct = sum(1 for r in rows if r["correct"])
    print(f"Total cases: {total}")
    print(f"Correct: {correct}/{total}")

    print("\n=== by family ===")
    fam = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in rows:
        fam[r["family"]]["total"] += 1
        fam[r["family"]]["correct"] += r["correct"]
    for k, v in sorted(fam.items()):
        status = "OK" if v["correct"] == v["total"] else "MISMATCH"
        print(f"  {k}: {v['correct']}/{v['total']} {status}")

    print("\n=== HARD GATES ===")
    dependency_failure_crash = [r["id"] for r in rows if r["actual"].get("no_crash") is False]
    dependency_failure_false_clean = [
        r["id"] for r in rows
        if r["expected"].get("not_clean") is True and r["actual"].get("not_clean") is False
    ]
    unhandled = [r["id"] for r in rows if "unhandled_exception" in r["actual"]]
    isolation_broken = [
        r["id"] for r in rows
        if r["target"] in ("apply_active_policies_isolation", "interaction_engine_predicate_raises") and not r["correct"]
    ]
    gates = {
        "dependency_failure_crashes_application": dependency_failure_crash,
        "dependency_failure_becomes_false_clean": dependency_failure_false_clean,
        "unhandled_exception_in_benchmark_harness": unhandled,
        "single_component_failure_not_isolated": isolation_broken,
    }
    for name, ids in gates.items():
        status = "PASS" if not ids else "FAIL"
        print(f"HARD GATE {name} == 0: {len(ids)} -> {status}")
        for cid in ids:
            row = next(r for r in rows if r["id"] == cid)
            print(f"    {cid}: expected={row['expected']} actual={row['actual']} ({row['notes']})")

    mismatches = [r for r in rows if not r["correct"]]
    print(f"\n=== mismatches (any expectation not met): {len(mismatches)} ===")
    for r in mismatches:
        print(f"  {r['id']} ({r['target']}): expected={r['expected']} actual={r['actual']}")

    with open("artifacts/step4b/phaseK_failure_mode_results.json", "w") as f:
        json.dump({"rows": rows, "gates": gates, "total": total, "correct": correct}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/phaseK_failure_mode_results.json")
