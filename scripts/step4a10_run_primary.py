#!/usr/bin/env python3
"""Step 4A.10 Phase 11/12 — PRIMARY EXECUTION of the locked independent
corpus. First complete run is the primary validation run; no tuning after
seeing results (per the task's absolute rule).

Three arms, computed from ONE real API call per document (cached and
reused across arms so Arm B and Arm C see identical discovery output —
avoids doubling API cost and removes live-call variance as a confound
between arms):
  ARM A — regex only (HYBRID_DISCOVERY_ENABLED=False), unmodified production path.
  ARM B — semantic only: cached real candidates run through the UNMODIFIED
          production _verify_semantic_candidate, with no regex union.
  ARM C — hybrid: unmodified production extract_indemnification_facts with
          HYBRID_DISCOVERY_ENABLED=True, SEMANTIC_PROVIDER="REAL", fed by
          the same cached candidates via a monkeypatch of the real-call
          function only (production code itself is untouched).
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
import semantic_discovery_real as sdr

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "artifacts" / "step4a10"

CASES = json.load(open(ROOT / "benchmarks" / "step4a10_benchmark.json"))
MUTATIONS = json.load(open(ROOT / "benchmarks" / "step4a10_mutations.json"))


def real_call_once(text):
    """Single real API call, returns (candidates_or_None, error_or_None)."""
    t0 = time.perf_counter()
    try:
        cands = sdr.discover_candidate_spans_real(text, "indemnification")
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}", time.perf_counter() - t0
    return cands, None, time.perf_counter() - t0


def arm_a_regex_only(text):
    ie.HYBRID_DISCOVERY_ENABLED = False
    facts = ie.extract_indemnification_facts(text)
    if facts is None:
        return "CONFIRMED_ABSENT", []
    return (("PRESENT_AND_VERIFIED" if facts.obligations else facts.absence_state),
            [o.discovery_source for o in facts.obligations])


def arm_b_semantic_only(text, cands, err):
    if err is not None:
        return "RECOGNITION_UNCERTAIN", [], {"rejected": 0, "unresolved": 0, "verified": 0}
    if not cands:
        return "CONFIRMED_ABSENT", [], {"rejected": 0, "unresolved": 0, "verified": 0}
    tally = {"rejected": 0, "unresolved": 0, "verified": 0}
    verified_obligations = []
    for cand in cands:
        outcome, obligation = ie._verify_semantic_candidate(text, cand)
        if outcome == "VERIFIED":
            tally["verified"] += 1
            verified_obligations.append(obligation)
        elif outcome == "UNRESOLVED":
            tally["unresolved"] += 1
        else:
            tally["rejected"] += 1
    if verified_obligations:
        return "PRESENT_AND_VERIFIED", verified_obligations, tally
    if tally["unresolved"] > 0:
        return "PRESENT_BUT_UNRESOLVED", [], tally
    return "CONFIRMED_ABSENT", [], tally


def arm_c_hybrid(text, cands, err):
    ie.HYBRID_DISCOVERY_ENABLED = True
    ie.SEMANTIC_PROVIDER = "REAL"

    def fake_real(document_text, concept, **kw):
        if err is not None:
            raise RuntimeError(err)
        return cands

    with patch("semantic_discovery_real.discover_candidate_spans_real", side_effect=fake_real):
        facts = ie.extract_indemnification_facts(text)
    if facts is None:
        return "CONFIRMED_ABSENT", []
    return (("PRESENT_AND_VERIFIED" if facts.obligations else facts.absence_state),
            [o.discovery_source for o in facts.obligations])


def process_batch(cases, label):
    results = {}
    t0 = time.perf_counter()
    for i, c in enumerate(cases):
        cid = c["id"]
        cands, err, latency_s = real_call_once(c["text"])
        arm_a_outcome, arm_a_sources = arm_a_regex_only(c["text"])
        arm_b_outcome, arm_b_obls, arm_b_tally = arm_b_semantic_only(c["text"], cands, err)
        arm_c_outcome, arm_c_sources = arm_c_hybrid(c["text"], cands, err)
        results[cid] = {
            "arm_a": arm_a_outcome,
            "arm_b": arm_b_outcome,
            "arm_b_tally": arm_b_tally,
            "arm_c": arm_c_outcome,
            "arm_c_sources": arm_c_sources,
            "candidate_count": len(cands) if cands else 0,
            "candidates": [
                {"quote": cand.evidence_span, "start": cand.start_offset, "end": cand.end_offset}
                for cand in (cands or [])
            ],
            "semantic_error": err,
            "latency_s": latency_s,
        }
        if (i + 1) % 25 == 0:
            print(f"  [{label}] {i + 1}/{len(cases)} done ({time.perf_counter() - t0:.1f}s elapsed)", file=sys.stderr)
    return results


def main():
    print("=== PRIMARY CORPUS (394 cases) ===", file=sys.stderr)
    primary = process_batch(CASES, "primary")
    with open(OUTDIR / "phase11_primary_results.json", "w") as f:
        json.dump(primary, f, indent=2)

    print("=== FORMATTING MUTATIONS (40 cases) ===", file=sys.stderr)
    mut_results = process_batch(MUTATIONS, "mutations")
    with open(OUTDIR / "phase31_mutation_results.json", "w") as f:
        json.dump(mut_results, f, indent=2)

    print("DONE", file=sys.stderr)


if __name__ == "__main__":
    main()
