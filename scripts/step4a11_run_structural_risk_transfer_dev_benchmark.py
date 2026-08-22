"""Step 4A.11 Phase 3 — PRE/POST runner for the structural risk-transfer
DEV benchmark (benchmarks/step4a11_structural_risk_transfer_dev_benchmark.py).

Run with --pre before any production code in this increment is touched,
and again (without --pre) after the mechanism is implemented.
"""

import sys

sys.path.insert(0, ".")

import indemnification_policy_engine as ie
from benchmarks.step4a11_structural_risk_transfer_dev_benchmark import CASES


def _actual(text: str):
    facts = ie.extract_indemnification_facts(text)
    if not facts or not facts.obligations:
        return "NOT_ESTABLISHED", None, None
    ob = facts.obligations[0]
    return "ESTABLISHED", ob.indemnifying_role, ob.indemnified_role


def main() -> None:
    rows = []
    for c in CASES:
        status, actor, beneficiary = _actual(c["text"])
        correct_status = status == c["expected_status"]
        correct_roles = True
        if c["expected_status"] == "ESTABLISHED" and status == "ESTABLISHED":
            correct_roles = (actor == c["expected_actor"]) and (beneficiary == c["expected_beneficiary"])
        false_established = c["expected_status"] == "NOT_ESTABLISHED" and status == "ESTABLISHED"
        missed = c["expected_status"] == "ESTABLISHED" and status == "NOT_ESTABLISHED"
        rows.append({
            "id": c["id"], "tags": c["tags"],
            "expected_status": c["expected_status"], "actual_status": status,
            "expected_actor": c["expected_actor"], "actual_actor": actor,
            "expected_beneficiary": c["expected_beneficiary"], "actual_beneficiary": beneficiary,
            "correct_status": correct_status, "correct_roles": correct_roles,
            "false_established": false_established, "missed": missed,
        })

    n = len(rows)
    established_expected = [r for r in rows if r["expected_status"] == "ESTABLISHED"]
    not_established_expected = [r for r in rows if r["expected_status"] == "NOT_ESTABLISHED"]
    correctly_established = sum(1 for r in established_expected if r["actual_status"] == "ESTABLISHED" and r["correct_roles"])
    wrong_roles = sum(1 for r in established_expected if r["actual_status"] == "ESTABLISHED" and not r["correct_roles"])
    missed_count = sum(1 for r in rows if r["missed"])
    false_established_count = sum(1 for r in rows if r["false_established"])
    correctly_not_established = sum(1 for r in not_established_expected if r["actual_status"] == "NOT_ESTABLISHED")

    print(f"Total cases: {n}")
    print(f"Expected ESTABLISHED: {len(established_expected)}")
    print(f"  -- correctly established (right status AND right actor/beneficiary): {correctly_established}")
    print(f"  -- WRONG ROLES while established (DANGEROUS if nonzero): {wrong_roles}")
    print(f"  -- missed (stayed NOT_ESTABLISHED): {missed_count}")
    print()
    print(f"Expected NOT_ESTABLISHED: {len(not_established_expected)}")
    print(f"  -- correctly NOT_ESTABLISHED: {correctly_not_established}")
    print(f"  -- FALSE ESTABLISHED (safety-critical, must be 0): {false_established_count}")
    print()

    if wrong_roles or false_established_count:
        print("=== SAFETY-CRITICAL MISMATCHES ===")
        for r in rows:
            if r["false_established"] or (r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "ESTABLISHED" and not r["correct_roles"]):
                print(f"  {r['id']}: expected {r['expected_status']}/{r['expected_actor']}/{r['expected_beneficiary']}, "
                      f"got {r['actual_status']}/{r['actual_actor']}/{r['actual_beneficiary']}")
        print()

    if missed_count:
        print("=== MISSED (lost automation, not unsafe) ===")
        for r in rows:
            if r["missed"]:
                print(f"  {r['id']} (tags: {r['tags']}): expected {r['expected_actor']}/{r['expected_beneficiary']}")
        print()

    print(f"HARD REQUIREMENT false_established == 0: {'PASS' if false_established_count == 0 else 'FAIL'}")
    print(f"HARD REQUIREMENT wrong_roles_while_established == 0: {'PASS' if wrong_roles == 0 else 'FAIL'}")


if __name__ == "__main__":
    main()
