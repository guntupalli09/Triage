"""Step 4A.11 Phase 2 — PRE/POST runner for the conditional-applicability
DEV benchmark (benchmarks/step4a11_conditional_applicability_dev_benchmark.py).

Run with --pre before any production code in this phase is touched, and
again (without --pre) after the mechanism is implemented, to produce an
honest PRE -> POST comparison.

PRE semantics: as of the start of this phase, NONE of the three adapters'
data models (IndemnityObligation/MonetaryTreatment, LiabilityFacts/
CategoryTreatment, PaymentFacts) carry any condition/applicability field at
all. So PRE is not "the mechanism gets some cases wrong" -- it is "the
mechanism does not exist," and every material fact, conditional or not, is
exposed identically to a clean unconditional fact. This script's PRE mode
therefore reports two things honestly: (1) a parseability sanity check
(does today's engine even detect the underlying clause in each DEV case,
independent of conditions, so a downstream "it didn't resolve" isn't
mistaken for "the condition mechanism worked") and (2) the STRIPPED-
CONDITION EXPOSURE COUNT -- how many of the expected-ESTABLISHED cases
currently have their material fact exposed with zero condition
information, which is exactly the unsafe gap this phase exists to close.

POST semantics (once the mechanism exists): re-run the same cases and
score condition status against expected_status using whatever
adapter-level introspection hook the production code exposes.
"""

import sys

sys.path.insert(0, ".")

import argparse

import indemnification_policy_engine as ie
import liability_policy_engine as le
import payment_terms_policy_engine as pe
from benchmarks.step4a11_conditional_applicability_dev_benchmark import CASES


def _clause_detected(adapter: str, text: str) -> bool:
    if adapter == "indemnification":
        facts = ie.extract_indemnification_facts(text)
        return bool(facts and facts.obligations)
    if adapter == "liability":
        facts = le.extract_liability_facts(text)
        return bool(facts and facts.clause_found)
    if adapter == "payment_terms":
        facts = pe.extract_payment_facts(text)
        return bool(facts and facts.clause_found)
    raise ValueError(adapter)


def _condition_status(adapter: str, text: str):
    """POST hook -- returns (status, condition_type) once the production
    mechanism exposes one, else None (mechanism not yet implemented for
    this adapter)."""
    if adapter == "indemnification":
        facts = ie.extract_indemnification_facts(text)
        if not facts or not facts.obligations:
            return None
        ob = facts.obligations[0]
        cond = getattr(ob, "condition", None)
        if cond is None:
            return None
        return cond.status, cond.condition_type
    if adapter == "liability":
        facts = le.extract_liability_facts(text)
        if not facts:
            return None
        cond = getattr(facts, "condition", None)
        if cond is None:
            return None
        return cond.status, cond.condition_type
    if adapter == "payment_terms":
        facts = pe.extract_payment_facts(text)
        if not facts:
            return None
        cond = getattr(facts, "condition", None)
        if cond is None:
            return None
        return cond.status, cond.condition_type
    raise ValueError(adapter)


def run_pre() -> None:
    n = len(CASES)
    undetected = []
    for c in CASES:
        if not _clause_detected(c["adapter"], c["text"]):
            undetected.append(c["id"])

    established_expected = [c for c in CASES if c["expected_status"] == "ESTABLISHED"]
    conflicting_expected = [c for c in CASES if c["expected_status"] == "CONFLICTING"]
    not_established_expected = [c for c in CASES if c["expected_status"] == "NOT_ESTABLISHED"]

    print(f"=== PRE (mechanism absent) — {n} cases ===")
    print()
    print("Sanity check: clause parseable by today's extractor (independent of any condition)")
    print(f"  Detected: {n - len(undetected)}/{n}")
    if undetected:
        print(f"  NOT detected (benchmark case needs a text fix before this phase can measure it): {undetected}")
    print()
    print("Condition representation in current production data model:")
    print(f"  Cases with ANY condition field populated: 0/{n} (no condition field exists yet on any adapter's facts)")
    print()
    print(f"Expected-ESTABLISHED cases (a real condition should attach to the material fact): {len(established_expected)}")
    print(f"  -> STRIPPED-CONDITION EXPOSURE COUNT (fact exposed as if unconditional today): {len(established_expected)}/{len(established_expected)}")
    print(f"     (by construction — every one of these facts currently carries no condition information at all)")
    print()
    print(f"Expected-CONFLICTING cases: {len(conflicting_expected)} — currently indistinguishable from a clean single fact")
    print(f"Expected-NOT_ESTABLISHED cases: {len(not_established_expected)} — currently indistinguishable from a clean single fact")
    print()
    print("PRE BASELINE: 0/%d cases have deterministic condition-ownership representation." % n)


def run_post() -> None:
    n = len(CASES)
    rows = []
    for c in CASES:
        result = _condition_status(c["adapter"], c["text"])
        actual_status = result[0] if result else "NO_MECHANISM"
        actual_type = result[1] if result else None
        rows.append({
            "id": c["id"], "adapter": c["adapter"], "tags": c["tags"],
            "expected_status": c["expected_status"], "actual_status": actual_status,
            "expected_type": c["expected_condition_type"], "actual_type": actual_type,
        })

    correct = sum(1 for r in rows if r["actual_status"] == r["expected_status"])
    stripped_condition = [
        r for r in rows if r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "UNCONDITIONAL"
    ]
    false_conditional = [
        r for r in rows if r["expected_status"] == "UNCONDITIONAL" and r["actual_status"] not in ("UNCONDITIONAL",)
    ]
    missed_to_review = [
        r for r in rows if r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "NOT_ESTABLISHED"
    ]
    no_mechanism = [r for r in rows if r["actual_status"] == "NO_MECHANISM"]

    print(f"=== POST — {n} cases ===")
    print(f"Exact status match: {correct}/{n} ({correct/n:.1%})")
    print()
    print(f"HARD REQUIREMENT stripped-condition authoritative facts == 0: "
          f"{len(stripped_condition)} -> {'PASS' if not stripped_condition else 'FAIL'}")
    if stripped_condition:
        for r in stripped_condition:
            print(f"    {r['id']} ({r['adapter']}): expected ESTABLISHED, got UNCONDITIONAL")
    print()
    print(f"False-conditional (flagged a condition where none exists): {len(false_conditional)}")
    for r in false_conditional:
        print(f"    {r['id']} ({r['adapter']}): expected {r['expected_status']}, got {r['actual_status']}")
    print()
    print(f"Missed (fell back to NOT_ESTABLISHED / review when attachment was actually clear): {len(missed_to_review)}")
    for r in missed_to_review:
        print(f"    {r['id']} ({r['adapter']})")
    print()
    if no_mechanism:
        print(f"Cases still returning NO_MECHANISM (adapter not yet wired): {len(no_mechanism)}")
        for r in no_mechanism:
            print(f"    {r['id']} ({r['adapter']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre", action="store_true")
    args = parser.parse_args()
    if args.pre:
        run_pre()
    else:
        run_post()
