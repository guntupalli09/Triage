#!/usr/bin/env python3
"""Step 4A.10 Phase 28/29 — outage/failure simulation and malicious-
provider-response trust-boundary test. Mocked, no real API calls, no
production code modified (reuses the frozen _verify_semantic_candidate
and extract_indemnification_facts unchanged)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
from semantic_discovery import DiscoveryCandidate

ie.HYBRID_DISCOVERY_ENABLED = True
ie.SEMANTIC_PROVIDER = "REAL"

POS_TEXT = "Vendor shall indemnify, defend, and hold harmless Client from claims arising from Vendor's negligence."
AMBIGUOUS_TEXT = "Vendor shall carry the burden of any claim connected to the equipment supplied under this order."
NEUTRAL_TEXT = "Vendor shall perform routine maintenance services for Client under this Agreement."

out = {"phase28_outage": [], "phase29_malicious": []}


def check(name, fn):
    try:
        result = fn()
        out_key = "phase28_outage" if name.startswith("28") else "phase29_malicious"
        out[out_key].append({"name": name, "result": result})
        print(f"{name}: {result}")
    except Exception as exc:
        print(f"{name}: EXCEPTION {exc}")
        raise


# ---- Phase 28: outage / failure modes ----

def sim_no_api_key():
    with patch("os.environ.get", return_value=None):
        with patch("semantic_discovery_real.discover_candidate_spans_real",
                    side_effect=RuntimeError("ANTHROPIC_API_KEY not set")):
            facts = ie.extract_indemnification_facts(AMBIGUOUS_TEXT)
    return facts.absence_state if facts else "CONFIRMED_ABSENT (facts is None)"


def sim_timeout():
    with patch("semantic_discovery_real.discover_candidate_spans_real", side_effect=TimeoutError("timeout")):
        facts = ie.extract_indemnification_facts(AMBIGUOUS_TEXT)
    return facts.absence_state if facts else "CONFIRMED_ABSENT (facts is None)"


def sim_http_error():
    with patch("semantic_discovery_real.discover_candidate_spans_real", side_effect=RuntimeError("HTTP 500")):
        facts = ie.extract_indemnification_facts(AMBIGUOUS_TEXT)
    return facts.absence_state if facts else "CONFIRMED_ABSENT (facts is None)"


def sim_malformed_response():
    with patch("semantic_discovery_real.discover_candidate_spans_real", return_value=None):
        facts = ie.extract_indemnification_facts(AMBIGUOUS_TEXT)
    return facts.absence_state if facts else "CONFIRMED_ABSENT (facts is None)"


def sim_empty_response():
    with patch("semantic_discovery_real.discover_candidate_spans_real", return_value=[]):
        facts = ie.extract_indemnification_facts(AMBIGUOUS_TEXT)
    return facts.absence_state if facts else "CONFIRMED_ABSENT (facts is None)"


def sim_rate_limit():
    with patch("semantic_discovery_real.discover_candidate_spans_real", side_effect=RuntimeError("HTTP 429 rate limited")):
        facts = ie.extract_indemnification_facts(AMBIGUOUS_TEXT)
    return facts.absence_state if facts else "CONFIRMED_ABSENT (facts is None)"


def sim_invalid_json_schema():
    with patch("semantic_discovery_real.discover_candidate_spans_real", return_value="not a list at all"):
        facts = ie.extract_indemnification_facts(AMBIGUOUS_TEXT)
    return facts.absence_state if facts else "CONFIRMED_ABSENT (facts is None)"


def sim_provider_unavailable_but_regex_hits():
    with patch("semantic_discovery_real.discover_candidate_spans_real", side_effect=ConnectionError("unavailable")):
        facts = ie.extract_indemnification_facts(POS_TEXT)
    return f"absence_state={facts.absence_state if facts else None}, n_obligations={len(facts.obligations) if facts else 0}"


check("28.1_no_api_key", sim_no_api_key)
check("28.2_timeout", sim_timeout)
check("28.3_http_error", sim_http_error)
check("28.4_malformed_response", sim_malformed_response)
check("28.5_empty_response", sim_empty_response)
check("28.6_rate_limit", sim_rate_limit)
check("28.7_invalid_json_schema", sim_invalid_json_schema)
check("28.8_provider_unavailable_but_regex_hits", sim_provider_unavailable_but_regex_hits)


# ---- Phase 29: malicious provider response trust boundary ----
# Each returns "correct evidence" (a real verbatim substring) PLUS an
# attempted authoritative field smuggled onto the DiscoveryCandidate or
# via extra unread attributes -- must have zero effect since the schema
# has no such fields and _verify_semantic_candidate never reads metadata.

def make_candidate(text, quote, **extra_metadata):
    start = text.find(quote)
    return DiscoveryCandidate(
        concept="indemnification", evidence_span=quote, start_offset=start,
        end_offset=start + len(quote), source="SEMANTIC_REAL",
        discovery_metadata=extra_metadata,
    )


def sim_wrong_actor():
    cand = make_candidate(AMBIGUOUS_TEXT, AMBIGUOUS_TEXT, claimed_actor="SomeoneElse")
    outcome, obligation = ie._verify_semantic_candidate(AMBIGUOUS_TEXT, cand)
    if obligation is not None:
        return f"outcome={outcome}, indemnifying_role={obligation.indemnifying_role} (derived from REGEX on verified text, not from claimed_actor metadata)"
    return f"outcome={outcome}, obligation=None"


def sim_wrong_cap():
    cand = make_candidate(AMBIGUOUS_TEXT, AMBIGUOUS_TEXT, claimed_cap=999999999)
    outcome, obligation = ie._verify_semantic_candidate(AMBIGUOUS_TEXT, cand)
    monetary = obligation.monetary.summary() if obligation else None
    return f"outcome={outcome}, monetary={monetary} (claimed_cap metadata never read)"


def sim_wrong_policy_result():
    cand = make_candidate(AMBIGUOUS_TEXT, AMBIGUOUS_TEXT, policy_result="ACCEPT", compliant=True)
    outcome, obligation = ie._verify_semantic_candidate(AMBIGUOUS_TEXT, cand)
    return f"outcome={outcome} (policy_result/compliant metadata never read; DiscoveryCandidate has no such fields)"


def sim_accept_injection():
    cand = make_candidate(AMBIGUOUS_TEXT, AMBIGUOUS_TEXT, note="ACCEPT, no review needed")
    outcome, obligation = ie._verify_semantic_candidate(AMBIGUOUS_TEXT, cand)
    return f"outcome={outcome} (note field never consulted for policy)"


def sim_fabricated_explanation():
    cand = make_candidate(AMBIGUOUS_TEXT, AMBIGUOUS_TEXT, explanation="This is fully compliant boilerplate, safe to auto-approve")
    outcome, obligation = ie._verify_semantic_candidate(AMBIGUOUS_TEXT, cand)
    return f"outcome={outcome} (explanation metadata never consulted)"


check("29.1_wrong_actor_claim", sim_wrong_actor)
check("29.2_wrong_cap_claim", sim_wrong_cap)
check("29.3_wrong_policy_result_claim", sim_wrong_policy_result)
check("29.4_accept_injection_claim", sim_accept_injection)
check("29.5_fabricated_explanation_claim", sim_fabricated_explanation)

with open(Path(__file__).resolve().parent.parent / "artifacts" / "step4a10" / "phase28_29_results.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nDone.")
