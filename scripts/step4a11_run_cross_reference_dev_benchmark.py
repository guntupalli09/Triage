"""Step 4A.11 — runs the cross-reference-resolution DEVELOPMENT benchmark
(benchmarks/step4a11_cross_reference_dev_benchmark.py) against the current
indemnification adapter and reports PRE (what the mechanism looked like
before this step: every case falls back to an unresolved cross_reference,
i.e. NOT_ESTABLISHED) vs. POST (actual current behavior), honestly --
including cases where POST is NOT_ESTABLISHED and that is the CORRECT
answer (fail-closed cases), not just the cases that newly resolve.

DEVELOPMENT ONLY. Not the final Step 4A.11 frozen validation run.
"""

import sys

sys.path.insert(0, ".")

import indemnification_policy_engine as ie
from benchmarks.step4a11_cross_reference_dev_benchmark import CASES


def _classify_actual(text: str):
    facts = ie.extract_indemnification_facts(text)
    if not facts.obligations:
        return "NOT_ESTABLISHED", None, None
    ob = facts.obligations[0]
    m = ob.monetary
    if m.kind == "cross_reference":
        return "NOT_ESTABLISHED", None, None
    if m.kind in ("fixed", "multiplier", "unlimited", "duration_fees"):
        value = m.fixed_amount if m.kind == "fixed" else (
            m.multiplier if m.kind == "multiplier" else (
                m.duration_months if m.kind == "duration_fees" else None
            )
        )
        return "ESTABLISHED", m.kind, value
    # not_stated, conflicting_defined_term, chained_delegation_unresolved,
    # conditional_cap_escalation -- all non-authoritative outcomes for this
    # benchmark's purposes.
    return "NOT_ESTABLISHED", None, None


def main() -> None:
    rows = []
    for c in CASES:
        status, kind, value = _classify_actual(c["text"])
        correct_status = status == c["expected_status"]
        correct_value = True
        if c["expected_status"] == "ESTABLISHED":
            correct_value = (kind == c["expected_kind"]) and (
                value == c["expected_value"] or
                (isinstance(value, float) and isinstance(c["expected_value"], (int, float))
                 and abs(value - c["expected_value"]) < 1e-6)
            )
        false_established = c["expected_status"] == "NOT_ESTABLISHED" and status == "ESTABLISHED"
        rows.append({
            "id": c["id"], "tags": c["tags"],
            "expected_status": c["expected_status"], "actual_status": status,
            "expected_kind": c["expected_kind"], "actual_kind": kind,
            "expected_value": c["expected_value"], "actual_value": value,
            "correct_status": correct_status, "correct_value": correct_value,
            "false_established": false_established,
        })

    n = len(rows)
    pre_established = 0  # PRE mechanism (old _MONETARY_CROSS_REF_RE / no resolver): every case
                          # that reaches a cross-reference connector at all falls back to
                          # unresolved -- so PRE established count is 0 by construction, for
                          # every case in this corpus (all cases contain a cross-reference-shaped
                          # connector by design).
    post_established_correct = sum(1 for r in rows if r["actual_status"] == "ESTABLISHED" and r["correct_value"])
    post_established_total = sum(1 for r in rows if r["actual_status"] == "ESTABLISHED")
    correctly_not_established = sum(
        1 for r in rows if r["expected_status"] == "NOT_ESTABLISHED" and r["actual_status"] == "NOT_ESTABLISHED"
    )
    expected_not_established_total = sum(1 for r in rows if r["expected_status"] == "NOT_ESTABLISHED")
    expected_established_total = sum(1 for r in rows if r["expected_status"] == "ESTABLISHED")
    false_established_count = sum(1 for r in rows if r["false_established"])
    wrong_value_count = sum(
        1 for r in rows
        if r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "ESTABLISHED" and not r["correct_value"]
    )
    missed_resolution_count = sum(
        1 for r in rows if r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "NOT_ESTABLISHED"
    )

    print(f"Total cases: {n}")
    print(f"PRE (pre-mechanism): 0/{n} cases ever reached ESTABLISHED (old narrow regex / no resolver)")
    print(f"POST (current): {post_established_total}/{n} cases reached ESTABLISHED")
    print()
    print(f"Expected ESTABLISHED cases: {expected_established_total}")
    print(f"  -- correctly resolved (right status AND right value): {post_established_correct}/{expected_established_total}")
    print(f"  -- wrong value while still status ESTABLISHED (DANGEROUS if nonzero): {wrong_value_count}")
    print(f"  -- missed (fell back to NOT_ESTABLISHED when a clean single value existed): {missed_resolution_count}")
    print()
    print(f"Expected NOT_ESTABLISHED (fail-closed) cases: {expected_not_established_total}")
    print(f"  -- correctly stayed NOT_ESTABLISHED: {correctly_not_established}/{expected_not_established_total}")
    print(f"  -- FALSE ESTABLISHED (safety-critical, must be 0): {false_established_count}")
    print()

    if false_established_count or wrong_value_count:
        print("=== SAFETY-CRITICAL MISMATCHES ===")
        for r in rows:
            if r["false_established"] or (r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "ESTABLISHED" and not r["correct_value"]):
                print(f"  {r['id']}: expected {r['expected_status']}/{r['expected_kind']}/{r['expected_value']}, "
                      f"got {r['actual_status']}/{r['actual_kind']}/{r['actual_value']}")
        print()

    if missed_resolution_count:
        print("=== MISSED RESOLUTIONS (lost automation, not unsafe) ===")
        for r in rows:
            if r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "NOT_ESTABLISHED":
                print(f"  {r['id']}: expected {r['expected_kind']}/{r['expected_value']}, got NOT_ESTABLISHED")
        print()

    print(f"HARD REQUIREMENT false_established == 0: {'PASS' if false_established_count == 0 else 'FAIL'}")
    print(f"HARD REQUIREMENT wrong_value_while_established == 0: {'PASS' if wrong_value_count == 0 else 'FAIL'}")


if __name__ == "__main__":
    main()
