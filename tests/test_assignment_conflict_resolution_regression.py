"""
Regression tests for the assignment_policy_engine._resolve_restrictions_for_side
silent-overwrite bug (Stage A.3 of the pre-#11 hardening pass).

Before this fix, when two named restrictions on the SAME side (e.g. two
separately drafted restrictions on "Vendor") stated materially different
consent standards, the resolver assigned `our_restriction = r` /
`their_restriction = r` inside its loop with no guard against a prior
assignment -- so the second-mentioned restriction silently replaced the
first, with no conflict noted and no REQUIRES_REVIEW routing. This mirrors
confidentiality_policy_engine._resolve_obligations_for_side's
`_monetary_key`-guarded pattern, which handles the structurally identical
situation correctly and is the reference implementation this fix copies.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from types import SimpleNamespace

import assignment_policy_engine as a


def _restriction(role, side, consent_standard, start, excerpt=None, section="9", exceptions=None):
    return a.AssignmentRestriction(
        restricted_role=role, restricted_side=side, consent_required=True,
        consent_standard=consent_standard, exceptions_present=exceptions or {},
        raw_excerpt=excerpt or f"{role} restriction text",
        start_index=start, end_index=start + 10, section_label=section,
    )


def test_duplicate_identical_restrictions_on_same_side_do_not_falsely_conflict():
    r1 = _restriction("Vendor", "sell_side", "sole_discretion", 0)
    r2 = _restriction("Vendor", "sell_side", "sole_discretion", 200)
    our, their, reasons = a._resolve_restrictions_for_side([r1, r2], "sell_side")
    assert reasons == [], f"identical duplicate restrictions should not be flagged as conflicting: {reasons}"
    assert our is not None
    assert our.consent_standard == "sole_discretion"


def test_materially_conflicting_restrictions_on_same_side_route_to_requires_review():
    r1 = _restriction("Vendor", "sell_side", "sole_discretion", 0)
    r2 = _restriction("Vendor", "sell_side", "reasonable", 200)
    our, their, reasons = a._resolve_restrictions_for_side([r1, r2], "sell_side")
    assert len(reasons) == 1
    assert "cannot determine which governs" in reasons[0]
    # The first-seen restriction is kept as the (still-flagged) candidate,
    # never silently discarded, and never silently overwritten by the
    # second -- confirms the fix doesn't just suppress the second value,
    # it flags the conflict and keeps evaluation honest about which one
    # was retained.
    assert our is not None and our.consent_standard == "sole_discretion"


def test_conflicting_exceptions_on_same_side_also_flagged():
    r1 = _restriction("Vendor", "sell_side", "not_stated", 0, exceptions={"affiliate": True})
    r2 = _restriction("Vendor", "sell_side", "not_stated", 200, exceptions={"merger_acquisition": True})
    our, their, reasons = a._resolve_restrictions_for_side([r1, r2], "sell_side")
    assert len(reasons) == 1
    assert "cannot determine which governs" in reasons[0]


def test_opposite_side_restrictions_remain_independently_resolvable():
    our_side_restriction = _restriction("Vendor", "sell_side", "sole_discretion", 0)
    their_side_restriction = _restriction("Customer", "buy_side", "reasonable", 200)
    our, their, reasons = a._resolve_restrictions_for_side(
        [our_side_restriction, their_side_restriction], "sell_side"
    )
    assert reasons == []
    assert our is not None and our.consent_standard == "sole_discretion"
    assert their is not None and their.consent_standard == "reasonable"


def test_conflicting_restrictions_on_counterparty_side_also_route_correctly():
    r1 = _restriction("Customer", "buy_side", "sole_discretion", 0)
    r2 = _restriction("Customer", "buy_side", "reasonable", 200)
    our, their, reasons = a._resolve_restrictions_for_side([r1, r2], "sell_side")
    assert len(reasons) == 1
    assert "counterparty's side" in reasons[0]


def test_end_to_end_conflicting_restrictions_route_to_requires_review():
    text = (
        "9.1 Vendor may not assign this Agreement without the prior written consent of Customer, "
        "in its sole discretion. Notwithstanding the foregoing, in Section 9.4, Vendor may not "
        "assign this Agreement to a competitor without the prior written consent of Customer, "
        "such consent not to be unreasonably withheld."
    )
    facts = a.extract_assignment_facts(text)
    policy = SimpleNamespace(
        contract_side="sell_side", escalation_approval_authority="Legal Director", fallback_text="Fallback.",
        required_exceptions_json=[], prohibit_sole_discretion_consent=False,
        require_consent_for_counterparty_assignment=False,
    )
    decision = a.evaluate_assignment_policy(facts, policy, source="regression-test")
    assert decision.state == "REQUIRES_REVIEW"
    assert any("cannot determine which governs" in f for f in decision.unresolved_facts)


def test_assignment_benchmark_corpus_golden_outputs_unchanged():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from benchmarks.run_assignment_benchmark import run, summarize
    data = run()
    summary = summarize(data)
    assert summary["false_safe_count"] == 0
    assert summary["false_escalation_count"] == 0
    mismatches = [r for r in data["rows"] if not r["state_correct"]]
    assert mismatches == [], f"golden-output drift on: {[r['id'] for r in mismatches]}"
