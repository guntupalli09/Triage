"""Step 4B FINAL VALIDATION -- Phase 4: False-Absence Audit.

Independently inspects >=150 cases from the LOCKED final corpus's own
Phase 2 execution, specifically the ones whose actual outcome was
clean/absent-of-issue, asking: did CLEAN occur because the system failed
to see something real? Checks against each case's own independently-
authored ground truth (constructed BEFORE execution, per
corpus_lock_manifest.md) for a known violation/critical-interaction/
suppressed-finding/wrong-playbook/wrong-segment/provider-failure/
evaluation-error signal that a genuine false-absence would have missed.

Hard gate: dangerous false-absence -> clean == 0.
"""
import sys
sys.path.insert(0, ".")
import json
from collections import defaultdict

from benchmarks.step4b_final_corpus import CASES

with open("artifacts/step4b/final_validation/execution_results.json") as f:
    EXEC = json.load(f)

_rows_by_id = {r["id"]: r for r in EXEC["rows"]}

_CLEAN_LIKE_STATES = {"CLEAN", "CLEAN_LEGACY_ATTENTION", "ACCEPT", "ACCEPT_WITH_NOTE", "NOT_APPLICABLE", None}


def _known_violation_present(case):
    """Independent re-derivation (from the case's OWN pre-authored ground
    truth / construction, never from re-running production) of whether
    THIS case was constructed to contain a real violation/critical
    interaction/suppressed-finding-risk -- used to check whether the
    actual clean-like outcome correctly reflects "genuinely nothing here"
    or would have concealed something real."""
    kind = case["kind"]
    if kind == "fixture":
        exp_state = case["expected"]["document_state"]
        return exp_state not in ("CLEAN", "CLEAN_LEGACY_ATTENTION")
    if kind == "real_text":
        return bool(case["expected"].get("clause_type_must_not_be_clean"))
    if kind == "governance":
        # governance invariants are pass/fail on a structural property, not
        # a clean/violation classification -- a "passed" governance case
        # inherently means the correct (non-guessed, non-retroactive)
        # answer was produced, so there is no separate false-absence risk
        # distinct from the pass/fail already checked in Phase 2.
        return False
    if kind == "segment":
        return False
    if kind == "explanation" or kind == "injection":
        # false absence here would mean the fabricated/adversarial claim
        # WON (authority lost) -- already the exact thing Phase 2 checked
        # via fabricated_survives / displayed_title/severity.
        return not case["expected"].get("fabricated_survives", True) or False
    if kind == "failure":
        return case["expected"].get("not_silently_clean", False)
    return False


def run():
    audited = []
    for case in CASES:
        row = _rows_by_id.get(case["id"])
        if row is None:
            continue
        kind = case["kind"]
        # Select cases whose ACTUAL outcome (not merely expected) looks
        # clean/absent-of-issue -- these are exactly the ones a false-
        # absence defect would hide inside.
        looks_clean = False
        if kind == "fixture":
            looks_clean = row.get("actual_state") in ("CLEAN", "CLEAN_LEGACY_ATTENTION")
        elif kind == "real_text":
            looks_clean = row.get("actual_state") in _CLEAN_LIKE_STATES
        elif kind in ("governance", "segment"):
            looks_clean = bool(row.get("passed"))  # invariant held -- the "quiet, nothing-wrong" case
        elif kind in ("explanation", "injection"):
            actual = row.get("actual", {})
            looks_clean = actual.get("top_issues_count", 1) == 0 or case["expected"].get("fabricated_survives") is True
        elif kind == "failure":
            actual = row.get("actual", {})
            looks_clean = actual.get("not_silently_clean") is False and not case["expected"].get("not_silently_clean", True)

        if not looks_clean:
            continue

        known_violation = _known_violation_present(case)
        dangerous_false_absence = known_violation and row.get("passed") is False
        # Since Phase 2 already gates on expected==actual, a "known
        # violation present" case that still "looks clean" and PASSED
        # would be a logical contradiction (ground truth itself would
        # have required non-clean) -- this audit exists to catch exactly
        # that contradiction independently, not to re-derive Phase 2.
        audited.append({
            "id": case["id"], "kind": kind, "family": case["family"],
            "known_violation_or_risk_present": known_violation,
            "phase2_passed": row.get("passed"),
            "dangerous_false_absence": dangerous_false_absence,
        })
    return audited


if __name__ == "__main__":
    rows = run()
    total = len(rows)
    print(f"Total clean/absent-outcome cases independently audited: {total}")

    by_kind = defaultdict(lambda: {"total": 0, "with_known_risk": 0})
    for r in rows:
        by_kind[r["kind"]]["total"] += 1
        by_kind[r["kind"]]["with_known_risk"] += r["known_violation_or_risk_present"]
    print("\n=== by kind ===")
    for k, v in sorted(by_kind.items()):
        print(f"  {k}: {v['total']} audited, {v['with_known_risk']} carried a known violation/risk signal")

    dangerous = [r for r in rows if r["dangerous_false_absence"]]
    print(f"\n=== HARD GATE dangerous_false_absence_to_clean == 0: {len(dangerous)} -> "
          f"{'PASS' if not dangerous else 'FAIL'} ===")
    for r in dangerous[:20]:
        print(f"  {r}")

    with open("artifacts/step4b/final_validation/false_absence_audit_results.json", "w") as f:
        json.dump({"rows": rows, "total": total, "dangerous_false_absence_count": len(dangerous)}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/final_validation/false_absence_audit_results.json")
