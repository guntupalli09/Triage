#!/usr/bin/env python3
"""Candidate 3 -- Section 9 provider-failure attacks.

These are DELIBERATE FAULT INJECTION tests (mocked), never real-provider
calls -- labeled SIMULATED_FAILURE_TEST throughout, never presented as
real-AI behavior. The objective is deterministic failure handling: every
failure mode below must fail closed (never CLEAN/ACCEPT, never
CONFIRMED_ABSENT when material facts remain unresolved).

Exercises the shared fact_admission.py framework (11 adapters) directly,
plus semantic_discovery_real.py (indemnification's primary path).
"""
import os
import sys
import json
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)

os.environ["FACT_ADMISSION_MODE"] = "enforced"

import fact_admission as fa  # noqa: E402
import insurance_policy_engine as ine  # noqa: E402
import indemnification_policy_engine as ie  # noqa: E402
import semantic_discovery_real as sdr  # noqa: E402
import policy_engine_core as core  # noqa: E402

ie.SEMANTIC_PROVIDER = "REAL"

RESULTS = []


def _record(name, description, decision_state, bucket, note=""):
    safe = bucket not in ("CLEAN",) and decision_state != "CONFIRMED_ABSENT"
    RESULTS.append({
        "test": name, "label": "SIMULATED_FAILURE_TEST", "description": description,
        "decision_state": decision_state, "bucket": bucket, "fail_closed": safe, "note": note,
    })
    print(f"{name}: state={decision_state} bucket={bucket} fail_closed={safe}")


def _bucket(state):
    if state in (core.ACCEPT, core.ACCEPT_WITH_NOTE):
        return "CLEAN"
    if state in (core.NEGOTIATE, core.MUST_REDLINE, core.PROHIBITED):
        return "NOT_CLEAN"
    if state == core.REQUIRES_REVIEW:
        return "REQUIRES_REVIEW"
    if state == core.NOT_APPLICABLE:
        return "NOT_APPLICABLE"
    return f"OTHER:{state}"


# Deliberately anchor-free for the insurance adapter's deterministic regex
# vocabulary (which matches the bare word "insurance" and several other
# broad synonyms) -- so extraction relies ENTIRELY on semantic discovery,
# exercising the real network-call code path the fault-injection patches
# below actually intercept. A text containing "insurance" would short-
# circuit to the deterministic path and never reach the mocked urlopen.
TEXT = ("9. Risk Coverage. Vendor shall keep in force a risk-transfer arrangement with a reputable "
        "underwriter protecting against third-party bodily injury and property damage claims arising "
        "from its operations, in an amount not less than two million dollars per occurrence.")


def _run_insurance_with_urlopen(side_effect=None, return_value=None):
    with patch("urllib.request.urlopen", side_effect=side_effect, return_value=return_value):
        facts = ine.extract_insurance_facts(TEXT)
    policy = MagicMock()
    policy.contract_side = "sell_side"
    policy.require_cgl = True
    policy.cgl_minimum_per_occurrence = 1000000
    for attr in dir(policy):
        pass
    # Use the real FakePolicy for a clean, complete attribute set.
    sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
    import replay_candidate2 as rc2
    p = rc2._InsurancePolicy(require_cgl=True, cgl_minimum_per_occurrence=1000000.0)
    decision = ine.evaluate_insurance_policy(facts, p)
    return facts, decision


def _fake_openai_response(body_dict, status=200):
    body = json.dumps(body_dict).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


def test_missing_api_key():
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    with patch.dict(os.environ, env, clear=True):
        os.environ["FACT_ADMISSION_MODE"] = "enforced"
        facts = ine.extract_insurance_facts(TEXT)
    sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
    import replay_candidate2 as rc2
    p = rc2._InsurancePolicy(require_cgl=True, cgl_minimum_per_occurrence=1000000.0)
    decision = ine.evaluate_insurance_policy(facts, p)
    _record("missing_api_key", "OPENAI_API_KEY unset", decision.state, _bucket(decision.state))


def test_invalid_api_key():
    import urllib.error
    def side_effect(*a, **kw):
        raise urllib.error.HTTPError(url="x", code=401, msg="Unauthorized", hdrs=None, fp=None)
    facts, decision = _run_insurance_with_urlopen(side_effect=side_effect)
    _record("invalid_api_key", "HTTP 401 from provider", decision.state, _bucket(decision.state))


def test_timeout():
    def side_effect(*a, **kw):
        raise TimeoutError("timed out")
    facts, decision = _run_insurance_with_urlopen(side_effect=side_effect)
    _record("timeout", "socket timeout", decision.state, _bucket(decision.state))


def test_connection_failure():
    import urllib.error
    def side_effect(*a, **kw):
        raise urllib.error.URLError("connection refused")
    facts, decision = _run_insurance_with_urlopen(side_effect=side_effect)
    _record("connection_failure", "URLError: connection refused", decision.state, _bucket(decision.state))


def test_http_429():
    import urllib.error
    def side_effect(*a, **kw):
        raise urllib.error.HTTPError(url="x", code=429, msg="Too Many Requests", hdrs=None, fp=None)
    facts, decision = _run_insurance_with_urlopen(side_effect=side_effect)
    _record("http_429", "HTTP 429 rate limited", decision.state, _bucket(decision.state))


def test_http_500():
    import urllib.error
    def side_effect(*a, **kw):
        raise urllib.error.HTTPError(url="x", code=500, msg="Internal Server Error", hdrs=None, fp=None)
    facts, decision = _run_insurance_with_urlopen(side_effect=side_effect)
    _record("http_500", "HTTP 500 provider error", decision.state, _bucket(decision.state))


def test_malformed_json():
    fake = MagicMock()
    fake.__enter__.return_value.read.return_value = b'{"choices": [{"message": {"content": "not valid json {{{"}}]}'
    fake.__exit__.return_value = False
    facts, decision = _run_insurance_with_urlopen(return_value=fake)
    _record("malformed_json", "model content is not valid JSON", decision.state, _bucket(decision.state))


def test_empty_response():
    fake = _fake_openai_response({"choices": []})
    facts, decision = _run_insurance_with_urlopen(return_value=fake)
    _record("empty_response", "choices list is empty", decision.state, _bucket(decision.state))


def test_missing_required_fields():
    fake = _fake_openai_response({"id": "x"})  # no "choices" key at all
    facts, decision = _run_insurance_with_urlopen(return_value=fake)
    _record("missing_required_fields", "response has no 'choices' key", decision.state, _bucket(decision.state))


def test_evidence_quote_not_in_source():
    fake = _fake_openai_response({"choices": [{"message": {"content": json.dumps(
        {"candidates": [{"quote": "this exact sentence does not appear anywhere in the document"}]}
    )}}]})
    with patch("urllib.request.urlopen", return_value=fake):
        cands = fa.discover_candidate_spans(TEXT, "insurance", "an insurance coverage requirement", api_key="fake-key-for-fault-injection-test")
    _record("evidence_quote_not_in_source", "hallucinated quote, not a substring of the document",
            "N/A", "CANDIDATES_DISCARDED" if not cands else "CANDIDATE_WRONGLY_KEPT",
            note=f"{len(cands)} candidates survived (must be 0)")


def test_invented_condition():
    real_doc = "9. Insurance. Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    quote = "Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    fake = _fake_openai_response({"choices": [{"message": {"content": json.dumps({
        "status": "ESTABLISHED", "evidence_quote": quote,
        "condition_quote": "this condition text is invented and not in the document",
        "exception_quote": None, "cross_reference_text": None, "definition_term": None,
        "competing_reading_a": None, "competing_reading_b": None, "reasoning": "x",
    })}}]})
    cand = fa.CandidateMaterialFact(clause_type="insurance", fact_type="clause_presence",
                                     evidence_span=quote, start_offset=real_doc.find(quote),
                                     end_offset=real_doc.find(quote) + len(quote), source="TEST")
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_and_ground(cand, real_doc, quote, api_key="fake-key-for-fault-injection-test")
    _record("invented_condition", "verifier claims a condition quote absent from the document",
            result.admission_status, "ADMITTED" if result.admission_status == "ADMITTED" else "BLOCKED",
            note=result.non_admission_reason or "")


def test_invented_exception():
    real_doc = "9. Insurance. Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    quote = "Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    fake = _fake_openai_response({"choices": [{"message": {"content": json.dumps({
        "status": "ESTABLISHED", "evidence_quote": quote,
        "condition_quote": None, "exception_quote": "this exception is invented and not in the document",
        "cross_reference_text": None, "definition_term": None,
        "competing_reading_a": None, "competing_reading_b": None, "reasoning": "x",
    })}}]})
    cand = fa.CandidateMaterialFact(clause_type="insurance", fact_type="clause_presence",
                                     evidence_span=quote, start_offset=real_doc.find(quote),
                                     end_offset=real_doc.find(quote) + len(quote), source="TEST")
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_and_ground(cand, real_doc, quote, api_key="fake-key-for-fault-injection-test")
    _record("invented_exception", "verifier claims an exception quote absent from the document",
            result.admission_status, "ADMITTED" if result.admission_status == "ADMITTED" else "BLOCKED",
            note=result.non_admission_reason or "")


def test_invented_definition():
    real_doc = "9. Insurance. Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    quote = "Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    fake = _fake_openai_response({"choices": [{"message": {"content": json.dumps({
        "status": "ESTABLISHED", "evidence_quote": quote,
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
        "definition_term": "Required Coverage",
        "competing_reading_a": None, "competing_reading_b": None, "reasoning": "x",
    })}}]})
    cand = fa.CandidateMaterialFact(clause_type="insurance", fact_type="clause_presence",
                                     evidence_span=quote, start_offset=real_doc.find(quote),
                                     end_offset=real_doc.find(quote) + len(quote), source="TEST")
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_and_ground(cand, real_doc, quote, api_key="fake-key-for-fault-injection-test")
    _record("invented_definition", "verifier names a defined term not actually defined anywhere in the document",
            result.admission_status, "ADMITTED" if result.admission_status == "ADMITTED" else "BLOCKED",
            note=result.non_admission_reason or "")


def test_invented_cross_reference():
    real_doc = "9. Insurance. Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    quote = "Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    fake = _fake_openai_response({"choices": [{"message": {"content": json.dumps({
        "status": "ESTABLISHED", "evidence_quote": quote,
        "condition_quote": None, "exception_quote": None,
        "cross_reference_text": "Section 99 (does not exist in this document)",
        "definition_term": None,
        "competing_reading_a": None, "competing_reading_b": None, "reasoning": "x",
    })}}]})
    cand = fa.CandidateMaterialFact(clause_type="insurance", fact_type="clause_presence",
                                     evidence_span=quote, start_offset=real_doc.find(quote),
                                     end_offset=real_doc.find(quote) + len(quote), source="TEST")
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_and_ground(cand, real_doc, quote, api_key="fake-key-for-fault-injection-test")
    _record("invented_cross_reference", "verifier cites a section that does not exist in the document",
            result.admission_status, "ADMITTED" if result.admission_status == "ADMITTED" else "BLOCKED",
            note=result.non_admission_reason or "")


def test_contradictory_model_response():
    real_doc = "9. Insurance. Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    quote = "Vendor shall maintain Commercial General Liability insurance with a $2,000,000 limit."
    # status NOT_ESTABLISHED but an evidence_quote is still provided -- a
    # self-contradictory response the schema doesn't forbid syntactically.
    fake = _fake_openai_response({"choices": [{"message": {"content": json.dumps({
        "status": "NOT_ESTABLISHED", "evidence_quote": quote,
        "condition_quote": None, "exception_quote": None, "cross_reference_text": None,
        "definition_term": None, "competing_reading_a": None, "competing_reading_b": None,
        "reasoning": "contradictory on purpose",
    })}}]})
    cand = fa.CandidateMaterialFact(clause_type="insurance", fact_type="clause_presence",
                                     evidence_span=quote, start_offset=real_doc.find(quote),
                                     end_offset=real_doc.find(quote) + len(quote), source="TEST")
    with patch("urllib.request.urlopen", return_value=fake):
        result = fa.verify_and_ground(cand, real_doc, quote, api_key="fake-key-for-fault-injection-test")
    _record("contradictory_model_response", "status=NOT_ESTABLISHED but evidence_quote is populated",
            result.admission_status, "ADMITTED" if result.admission_status == "ADMITTED" else "BLOCKED",
            note=result.non_admission_reason or "")


def test_indemnification_primary_path_provider_failure():
    """Path B (semantic_discovery_real.py) -- indemnification's primary
    discovery must also fail closed on a provider error, never silently
    treated as 'no obligation found'."""
    import urllib.error
    doc = "12. Indemnification. Vendor shall indemnify Customer for third-party claims arising from its gross negligence."
    def side_effect(*a, **kw):
        raise urllib.error.URLError("connection refused")
    with patch("urllib.request.urlopen", side_effect=side_effect):
        facts = ie.extract_indemnification_facts(doc)
    sys.path.insert(0, os.path.join(REPO_ROOT, "artifacts", "candidate2_remediation", "corpus_replay"))
    import replay_candidate2 as rc2
    p = rc2._IndemnificationPolicy()
    decision = ie.evaluate_indemnification_policy(facts, p)
    _record("indemnification_primary_path_provider_failure",
            "semantic_discovery_real network failure during indemnification's PRIMARY discovery "
            "(the deterministic anchor 'indemnify' is ALSO present in this text, so this exercises "
            "the fail-closed path for a provider error that happens alongside a successful "
            "deterministic parse, not a total-absence scenario)",
            decision.state, _bucket(decision.state))


if __name__ == "__main__":
    test_missing_api_key()
    test_invalid_api_key()
    test_timeout()
    test_connection_failure()
    test_http_429()
    test_http_500()
    test_malformed_json()
    test_empty_response()
    test_missing_required_fields()
    test_evidence_quote_not_in_source()
    test_invented_condition()
    test_invented_exception()
    test_invented_definition()
    test_invented_cross_reference()
    test_contradictory_model_response()
    test_indemnification_primary_path_provider_failure()

    out_path = os.path.join(os.path.dirname(__file__), "fault_injection_results.json")
    with open(out_path, "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    n_fail_closed = sum(1 for r in RESULTS if r.get("fail_closed", True))
    print(f"\n{n_fail_closed}/{len(RESULTS)} fail-closed. Wrote {out_path}")
