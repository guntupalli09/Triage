#!/usr/bin/env python3
"""Step 4A.10.6 — EXPLICITLY NON-AUTHORITATIVE development/adversarial
controls for the structural defense-control redesign. Never to be
treated as a frozen validation corpus; built and iterated on freely
before the real frozen corpus is built and locked."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indemnification_policy_engine as ie

# (text, expect_flagged, note)
CASES = [
    # --- genuine negation asymmetry: one role controls, the other
    # explicitly lacks control -- must still escalate (this is a REAL
    # asymmetry, not something the new mechanism should paper over) ---
    (
        "Each party shall indemnify the other for third-party claims; Meridian Vendors oversees the response to any claim brought against it, while Alcove Traders has no say in the response to any claim brought against it.",
        True, "genuine asymmetry: control vs explicit no-control, self-referential both sides",
    ),
    (
        "Each party shall indemnify the other for third-party claims; Alpha Corp steers settlement decisions on any claim against it, whereas Beta Corp lacks any role in settlement decisions on any claim against it.",
        True, "genuine asymmetry: control vs 'lacks any role', self-referential both sides",
    ),
    # --- genuinely symmetric, fresh verbs never seen in dev/frozen
    # corpora so far (this is the actual generalization test) ---
    (
        "Each party shall indemnify the other for third-party claims; Omega LLC spearheads the litigation response to any claim brought against it, and Sigma LLC likewise spearheads the litigation response to any claim brought against it.",
        False, "symmetric, fresh verb 'spearheads' -- must pass",
    ),
    (
        "Each party shall indemnify the other for third-party claims; Northwind Traders calls the shots on any settlement of a claim against it, while Southgate Partners calls the shots on any settlement of a claim against it as well.",
        False, "symmetric, fresh idiom 'calls the shots on' -- must pass",
    ),
    (
        "Each party shall indemnify the other for third-party claims; Redwood Systems owns the strategy for any claim asserted against it, and Cedar Systems owns that same strategy for any claim asserted against it.",
        False, "symmetric, fresh verb 'owns' -- must pass",
    ),
    # --- adversarial: response-process word present but UNRELATED to
    # claim defense/control -- must NOT be mistaken for a control
    # statement (false establishment risk) ---
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Harbor Logistics maintains a dedicated settlement fund against its own working-capital account, and Bay Logistics maintains that same dedicated settlement fund arrangement against its own working-capital account.",
        False, "adversarial: 'settlement' + 'against its' present but NOT about claim-defense control, genuinely identical arrangement -- should not falsely differ",
    ),
    # --- adversarial: negation word present nearby but NOT actually
    # negating the control statement (should not be misread as
    # self_no_control) ---
    (
        "Each party shall indemnify the other for third-party claims; Trailhead Inc, notwithstanding any objection, directs the defense strategy for any claim against it, and Ridgeline Inc, notwithstanding any objection, directs the defense strategy for any claim against it.",
        False, "adversarial: 'notwithstanding' contains no true negation of control -- both roles genuinely control, must still pass symmetric",
    ),
    # --- three-role structural stress (still must abstain/escalate
    # correctly, not crash) ---
    (
        "Each party shall indemnify the other for third-party claims; Founder Holdings, Meridian Capital, and Alcove Partners shall each control the response to any claim against it, and Founder Holdings's approach differs materially from Meridian Capital's approach to the same.",
        True, "three roles, explicit differentiation signal ('differs materially') -- must escalate, not crash",
    ),
    # --- both roles genuinely lack control (symmetric no-control, not
    # just symmetric control) -- must still pass as symmetric ---
    (
        "Each party shall indemnify the other for third-party claims; Pinehurst Realty has no say in the defense of any claim brought against it, and Cordell Realty likewise has no say in the defense of any claim brought against it.",
        False, "symmetric: BOTH roles explicitly lack control -- must pass, not escalate",
    ),
    # --- unrelated 'response'/'defense' usage with no self-reference at
    # all -- must never establish a defense_control value from this ---
    (
        "Each party shall indemnify the other for claims arising under this Agreement; Stonebridge Analytics filed a coordinated public-relations response to the industry downturn, and Larkspur Analytics filed a coordinated public-relations response to the industry downturn.",
        False, "adversarial: 'response' present, no self-reference ('against it') at all -- must not establish defense_control from unrelated PR context (should pass via structural equivalence, not via a defense_control value)",
    ),
    # --- explicit contrast connective right after the self-control
    # clause, still must escalate (contrastive shouldn't suppress a
    # REAL asymmetry the same way it protects a real symmetry) ---
    (
        "Each party shall indemnify the other for third-party claims; Anchorpoint Media commands the litigation strategy for any claim against it, but Willowmere Media has absolutely no input into litigation strategy for any claim against it.",
        True, "genuine asymmetry phrased with 'but' -- must still escalate",
    ),
]


def main():
    ie.HYBRID_DISCOVERY_ENABLED = False
    passed = 0
    failed = []
    for text, expect_flagged, note in CASES:
        reasons = ie._detect_reciprocal_asymmetry(text)
        flagged = bool(reasons)
        ok = flagged == expect_flagged
        if ok:
            passed += 1
        else:
            failed.append((text, expect_flagged, flagged, reasons, note))
    print(f"PASS: {passed}/{len(CASES)}")
    for text, expect, got, reasons, note in failed:
        print(f"\nFAIL [{note}]")
        print(f"  expected_flagged={expect} got_flagged={got}")
        print(f"  text: {text}")
        print(f"  reasons: {reasons}")


if __name__ == "__main__":
    main()
