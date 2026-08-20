#!/usr/bin/env python3
"""Step 4A.9.2 — real-provider run of the UNMODIFIED locked 200-case
benchmark from Step 4A.9.1 (benchmarks/step4a9_1_benchmark.json).
Frozen at commit 5afbda9 — no tuning after seeing results."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indemnification_policy_engine as ie
import semantic_discovery_real as sdr

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "step4a9_1_benchmark.json"
OUTDIR = Path(__file__).resolve().parent.parent / "artifacts" / "step4a9_2"

with open(BENCH) as f:
    CASES = json.load(f)


def recognition_outcome(text: str):
    facts = ie.extract_indemnification_facts(text)
    if facts is None:
        return "CONFIRMED_ABSENT", []
    return (
        ("PRESENT_AND_VERIFIED" if facts.obligations else facts.absence_state),
        [o.discovery_source for o in facts.obligations],
    )


def run(run_label: str):
    ie.SEMANTIC_PROVIDER = "REAL"
    ie.HYBRID_DISCOVERY_ENABLED = True
    sdr.CALL_LOG.clear()
    results = {}
    errors = {}
    t0 = time.perf_counter()
    for i, c in enumerate(CASES):
        try:
            outcome, sources = recognition_outcome(c["text"])
        except Exception as exc:  # noqa: BLE001 — record and continue, never crash the run
            outcome, sources = "RUN_ERROR", []
            errors[c["id"]] = f"{type(exc).__name__}: {exc}"
        results[c["id"]] = {"outcome": outcome, "sources": sources}
        if (i + 1) % 25 == 0:
            print(f"  [{run_label}] {i + 1}/{len(CASES)} done ({time.perf_counter() - t0:.1f}s elapsed)", file=sys.stderr)
    total_elapsed = time.perf_counter() - t0
    call_log = list(sdr.CALL_LOG)
    return {
        "results": results, "errors": errors, "total_elapsed_s": total_elapsed,
        "call_log": call_log,
    }


def summarize(run_data, label):
    results = run_data["results"]
    by_id = {c["id"]: c for c in CASES}
    print(f"\n=== {label} ===")
    print(f"Total wall time: {run_data['total_elapsed_s']:.1f}s over {len(CASES)} cases")
    print(f"Run errors (crashed, not provider-unavailable): {len(run_data['errors'])}")
    for cid, msg in run_data["errors"].items():
        print(f"  {cid}: {msg}")

    pos_ids = [c["id"] for c in CASES if c["label"] == "POSITIVE"]
    neg_ids = [c["id"] for c in CASES if c["label"] == "NEGATIVE"]
    novel_ids = [c["id"] for c in CASES if c["family"] == "novel_unseen"]

    def bucket(ids):
        counts = {"PRESENT_AND_VERIFIED": 0, "PRESENT_BUT_UNRESOLVED": 0, "RECOGNITION_UNCERTAIN": 0, "CONFIRMED_ABSENT": 0, "RUN_ERROR": 0}
        for i in ids:
            counts[results[i]["outcome"]] = counts.get(results[i]["outcome"], 0) + 1
        return counts

    pos_c = bucket(pos_ids)
    neg_c = bucket(neg_ids)
    novel_c = bucket(novel_ids)
    n_pos, n_neg, n_novel = len(pos_ids), len(neg_ids), len(novel_ids)

    print(f"\nPOSITIVE (n={n_pos}): {pos_c}")
    print(f"  false-absence rate: {pos_c['CONFIRMED_ABSENT'] / n_pos:.1%}")
    print(f"  discovered-or-verified recall: {(n_pos - pos_c['CONFIRMED_ABSENT'] - pos_c['RUN_ERROR']) / n_pos:.1%}")
    print(f"  clean-VERIFIED recall: {pos_c['PRESENT_AND_VERIFIED'] / n_pos:.1%}")

    print(f"\nNOVEL_UNSEEN (n={n_novel}, the killer-gate family): {novel_c}")
    print(f"  false-absence rate: {novel_c['CONFIRMED_ABSENT'] / n_novel:.1%}")
    print(f"  material recovery (discovered, not absent): {n_novel - novel_c['CONFIRMED_ABSENT']} / {n_novel}")

    print(f"\nNEGATIVE (n={n_neg}): {neg_c}")
    print(f"  true-negative rate: {neg_c['CONFIRMED_ABSENT'] / n_neg:.1%}")
    print(f"  FALSE clean-verified on a hard negative (dangerous): {neg_c['PRESENT_AND_VERIFIED']}")
    print(f"  false-candidate rate (routed to review unnecessarily): {(n_neg - neg_c['CONFIRMED_ABSENT']) / n_neg:.1%}")

    # Latency/cost
    log = run_data["call_log"]
    ok = [c for c in log if c["status"] == "ok"]
    if ok:
        lat = sorted(c["elapsed_ms"] for c in ok)
        in_tok = sum(c["input_tokens"] or 0 for c in ok)
        out_tok = sum(c["output_tokens"] or 0 for c in ok)
        print(f"\nLatency/cost over {len(ok)} successful real API calls:")
        print(f"  latency ms: min={lat[0]:.0f} median={lat[len(lat)//2]:.0f} max={lat[-1]:.0f} mean={sum(lat)/len(lat):.0f}")
        print(f"  total input tokens: {in_tok}, total output tokens: {out_tok}")
        print(f"  mean tokens/doc: in={in_tok/len(ok):.1f} out={out_tok/len(ok):.1f}")
    non_ok = [c for c in log if c["status"] != "ok"]
    print(f"  non-ok calls: {len(non_ok)} ({[c['status'] for c in non_ok]})")

    return {
        "pos": pos_c, "neg": neg_c, "novel": novel_c,
        "n_pos": n_pos, "n_neg": n_neg, "n_novel": n_novel,
    }


def main():
    run1 = run("run1")
    summary1 = summarize(run1, "REAL PROVIDER — RUN 1")
    with open(OUTDIR / "phase_real_run1_raw.json", "w") as f:
        json.dump(run1, f, indent=2)

    run2 = run("run2")
    summary2 = summarize(run2, "REAL PROVIDER — RUN 2 (determinism check)")
    with open(OUTDIR / "phase_real_run2_raw.json", "w") as f:
        json.dump(run2, f, indent=2)

    # Determinism of the AUTHORITATIVE outcome (not raw candidate text)
    diffs = []
    for cid in run1["results"]:
        o1 = run1["results"][cid]["outcome"]
        o2 = run2["results"].get(cid, {}).get("outcome")
        if o1 != o2:
            diffs.append((cid, o1, o2))
    print(f"\n=== AUTHORITATIVE-OUTCOME DETERMINISM (run1 vs run2) ===")
    print(f"Mismatches: {len(diffs)} / {len(CASES)}")
    for d in diffs:
        print(f"  {d}")

    with open(OUTDIR / "phase_real_determinism_diffs.json", "w") as f:
        json.dump(diffs, f, indent=2)


if __name__ == "__main__":
    main()
