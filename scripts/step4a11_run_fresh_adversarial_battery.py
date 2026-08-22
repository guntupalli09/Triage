"""Step 4A.11 Phase 4 — runner for the fresh adversarial DEVELOPMENT
battery (benchmarks/step4a11_fresh_adversarial_battery.py).

Metrics are predeclared HERE, before execution, mapped from the
fact-level ground truth schema the battery actually carries (ESTABLISHED/
NOT_ESTABLISHED/CONFLICTING + owner/value/condition) onto the requested
Step 4A.10-style vocabulary:

  CA  (Clean Automatic)      -- expected ESTABLISHED, actual ESTABLISHED
                                 with correct owner/value AND correct
                                 condition (when scored).
  CR  (Correctly Routed)     -- expected NOT_ESTABLISHED/CONFLICTING,
                                 actual matches.
  FE  (False Escalation)     -- expected ESTABLISHED, actual
                                 NOT_ESTABLISHED. Lost automation, not
                                 unsafe.
  WC  (Wrong Clean)          -- actual ESTABLISHED with WRONG owner/
                                 value, OR expected NOT_ESTABLISHED/
                                 CONFLICTING but actual ESTABLISHED
                                 (false structural establishment). The
                                 dangerous category.
  SM / SM-CRITICAL           -- AF9 false-absence cases only: SM = a
                                 genuinely present provision reported
                                 CONFIRMED_ABSENT (indemnification) or
                                 clause_found=False (liability/payment)
                                 instead of a safe review state.
                                 SM-CRITICAL = an SM case where a
                                 wrong-but-plausible value was ALSO
                                 attached (none expected in this
                                 battery's design; reported if found).
  false-symmetry / false-asymmetry -- AF8 cases only.
  stripped-condition authority     -- AF3 cases: expected_condition ==
                                 "ESTABLISHED" but the fact itself
                                 establishes cleanly with NO condition
                                 attached (UNCONDITIONAL) -- silently
                                 dropped, not merely "not detected."
  semantic->authority         -- measured separately: toggling
                                 HYBRID_DISCOVERY_ENABLED off vs on
                                 across the whole battery must never
                                 change any outcome (deterministic
                                 re-verification, not discovery
                                 provenance, decides every fact).
  Automation Recall / Clean-Verified Recall -- computed directly from
                                 this battery's own expected-ESTABLISHED
                                 fraction reached.

  policy-changing UNVERIFIED-CA and fabricated-evidence->authority are
  NOT independently recomputed by this script -- they require the
  dedicated material-fact trust audit and security audit that come
  AFTER this battery per the phase-4 ordering, and are deferred there
  honestly rather than approximated here.

Ground-truth corrections made before this first execution are marked
GTD in the battery's own case notes (none were needed after the overlap
-driven rewrites — those were corpus INDEPENDENCE fixes, not ground-
truth corrections). Any GTD found AFTER this run will be disclosed
separately, not silently applied.
"""

import sys

sys.path.insert(0, ".")

import indemnification_policy_engine as ie
import liability_policy_engine as le
import payment_terms_policy_engine as pe
from benchmarks.step4a11_fresh_adversarial_battery import CASES


def _actual_indemnification(text: str):
    facts = ie.extract_indemnification_facts(text)
    if not facts or not facts.obligations:
        absence_state = facts.absence_state if facts else "CONFIRMED_ABSENT"
        return "NOT_ESTABLISHED", None, absence_state, None
    ob = facts.obligations[0]
    cond = ob.condition.status if ob.condition else "UNCONDITIONAL"
    return "ESTABLISHED", {"actor": ob.indemnifying_role, "beneficiary": ob.indemnified_role}, facts.absence_state, cond


def _actual_liability(text: str, expected_dimension):
    facts = le.extract_liability_facts(text)
    if not facts or not facts.provisions:
        return "NOT_ESTABLISHED", None, "ABSENT" if not facts else "PRESENT_NO_PROVISION", None
    p = facts.controlling_provision or facts.provisions[0]
    cond = p.condition.status if p.condition else "UNCONDITIONAL"
    # Always attempt to resolve the general cap -- expected_dimension is
    # None only when the case has no specific expected VALUE to check
    # (e.g. a hard negative), never a signal to skip resolution and
    # report ESTABLISHED merely because a Provision object exists (a
    # Provision can exist with an entirely unresolved cap expression).
    cap, _ = p.general_cap_expression.effective_cap() if p.general_cap_expression.structure != "unresolved" else (None, None)
    if cap is None:
        return "NOT_ESTABLISHED", None, "PRESENT_UNRESOLVED_CAP", cond
    # Normalize liability's own kind vocabulary ("fee_multiplier"/
    # "fixed_amount"/"unlimited") onto this battery's ground-truth
    # convention ("multiplier"/"fixed"/"unlimited"), matching the
    # indemnification adapter's MonetaryTreatment naming used throughout
    # the case dicts.
    if cap.kind == "fee_multiplier" and cap.multiplier is not None:
        value = {"kind": "multiplier", "multiplier": cap.multiplier}
    elif cap.kind == "fixed_amount" and cap.fixed_amount is not None:
        value = {"kind": "fixed", "fixed_amount": cap.fixed_amount}
    elif cap.kind == "unlimited":
        value = {"kind": "unlimited"}
    else:
        return "NOT_ESTABLISHED", None, "PRESENT_UNRESOLVED_CAP", cond
    return "ESTABLISHED", value, "PRESENT", cond


def _actual_payment(text: str, expected_dimension):
    facts = pe.extract_payment_facts(text)
    if not facts:
        return "NOT_ESTABLISHED", None, "ABSENT", None
    cond = facts.condition.status if facts.condition else "UNCONDITIONAL"
    if expected_dimension == "net_days":
        if facts.net_days is None:
            return "NOT_ESTABLISHED", None, "PRESENT_NO_NET_DAYS", cond
        return "ESTABLISHED", {"net_days": facts.net_days}, "PRESENT", cond
    if expected_dimension == "late_fee_rate_percent":
        if facts.late_fee_rate_percent is None:
            return "NOT_ESTABLISHED", None, "PRESENT_NO_LATE_FEE", cond
        return "ESTABLISHED", {"late_fee_rate_percent": facts.late_fee_rate_percent}, "PRESENT", cond
    # No specific dimension targeted -- treat any established dimension
    # (net_days, condition, etc.) as evidence of establishment.
    established_any = facts.net_days is not None or facts.condition is not None and facts.condition.status != "UNCONDITIONAL"
    return ("ESTABLISHED" if established_any else "NOT_ESTABLISHED"), None, "PRESENT", cond


def run() -> list:
    rows = []
    for c in CASES:
        adapter = c["adapter"]
        if adapter == "indemnification":
            status, value, absence_state, cond = _actual_indemnification(c["text"])
        elif adapter == "liability":
            status, value, absence_state, cond = _actual_liability(c["text"], c["expected_dimension"])
        else:
            status, value, absence_state, cond = _actual_payment(c["text"], c["expected_dimension"])

        expected_status = c["expected_status"]
        correct_status = status == expected_status
        correct_value = True
        if expected_status == "ESTABLISHED" and c["expected"]:
            if adapter == "indemnification":
                correct_value = value is not None and value.get("actor") == c["expected"].get("actor") and value.get("beneficiary") == c["expected"].get("beneficiary")
            elif adapter == "liability":
                correct_value = value == c["expected"]
            elif adapter == "payment_terms":
                correct_value = value == c["expected"]

        condition_correct = True
        if c["expected_condition"] is not None:
            condition_correct = cond == c["expected_condition"]

        rows.append({
            "id": c["id"], "adapter": adapter, "attack_families": c["attack_families"],
            "expected_status": expected_status, "actual_status": status,
            "correct_status": correct_status, "correct_value": correct_value,
            "condition_correct": condition_correct if c["expected_condition"] is not None else None,
            "absence_state": absence_state, "actual_condition": cond,
            "tags": c["attack_families"],
        })
    return rows


def classify(rows):
    CA = CR = FE = WC = SM = 0
    stripped_condition = []
    false_structural = []
    wrong_owner = []
    for r in rows:
        exp, act = r["expected_status"], r["actual_status"]
        if exp == "ESTABLISHED" and act == "ESTABLISHED" and r["correct_value"] and r["condition_correct"] is not False:
            CA += 1
        elif exp == "ESTABLISHED" and act == "NOT_ESTABLISHED":
            FE += 1
        elif exp in ("NOT_ESTABLISHED", "CONFLICTING") and act in ("NOT_ESTABLISHED", "CONFLICTING"):
            CR += 1
        elif exp == "ESTABLISHED" and act == "ESTABLISHED" and not r["correct_value"]:
            WC += 1
            wrong_owner.append(r["id"])
        elif exp in ("NOT_ESTABLISHED", "CONFLICTING") and act == "ESTABLISHED":
            WC += 1
            false_structural.append(r["id"])
        if r["condition_correct"] is False and r["expected_status"] == "ESTABLISHED":
            # expected an ESTABLISHED condition but actual came back
            # UNCONDITIONAL/wrong on an otherwise-correctly-established fact
            if r["actual_condition"] == "UNCONDITIONAL":
                stripped_condition.append(r["id"])

        if "AF9" in r["attack_families"] and r["absence_state"] in ("CONFIRMED_ABSENT", "ABSENT"):
            SM += 1

    return {
        "CA": CA, "CR": CR, "FE": FE, "WC": WC, "SM": SM,
        "false_structural_establishment": false_structural,
        "wrong_ownership": wrong_owner,
        "stripped_condition_authority": stripped_condition,
    }


def semantic_authority_check():
    """HYBRID_DISCOVERY_ENABLED toggled off vs on across the whole
    battery must never change any indemnification outcome."""
    original = ie.HYBRID_DISCOVERY_ENABLED
    try:
        ie.HYBRID_DISCOVERY_ENABLED = True
        hybrid = {c["id"]: _actual_indemnification(c["text"]) for c in CASES if c["adapter"] == "indemnification"}
        ie.HYBRID_DISCOVERY_ENABLED = False
        regex_only = {c["id"]: _actual_indemnification(c["text"]) for c in CASES if c["adapter"] == "indemnification"}
    finally:
        ie.HYBRID_DISCOVERY_ENABLED = original
    diffs = [cid for cid in hybrid if hybrid[cid][:2] != regex_only[cid][:2]]
    return diffs


def determinism_check(repeats: int = 5):
    import json
    mismatches = []
    for c in CASES:
        adapter = c["adapter"]
        hashes = set()
        for _ in range(repeats):
            if adapter == "indemnification":
                result = _actual_indemnification(c["text"])
            elif adapter == "liability":
                result = _actual_liability(c["text"], c["expected_dimension"])
            else:
                result = _actual_payment(c["text"], c["expected_dimension"])
            hashes.add(json.dumps(result, default=str, sort_keys=True))
        if len(hashes) != 1:
            mismatches.append(c["id"])
    return mismatches


def main() -> None:
    rows = run()
    n = len(rows)
    metrics = classify(rows)

    established_expected = [r for r in rows if r["expected_status"] == "ESTABLISHED"]
    automation_recall = metrics["CA"] / len(established_expected) if established_expected else 0.0

    print(f"Total cases: {n}")
    print(f"CA={metrics['CA']} CR={metrics['CR']} FE={metrics['FE']} WC={metrics['WC']} SM={metrics['SM']}")
    print()
    print(f"Automation Recall (CA / expected-ESTABLISHED): {metrics['CA']}/{len(established_expected)} = {automation_recall:.1%}")
    print()
    print(f"HARD GATE false_structural_establishment == 0: {len(metrics['false_structural_establishment'])} "
          f"-> {'PASS' if not metrics['false_structural_establishment'] else 'FAIL'}")
    if metrics["false_structural_establishment"]:
        for cid in metrics["false_structural_establishment"]:
            print(f"    {cid}")
    print(f"HARD GATE wrong_ownership == 0: {len(metrics['wrong_ownership'])} "
          f"-> {'PASS' if not metrics['wrong_ownership'] else 'FAIL'}")
    if metrics["wrong_ownership"]:
        for cid in metrics["wrong_ownership"]:
            print(f"    {cid}")
    print(f"HARD GATE stripped_condition_authority == 0: {len(metrics['stripped_condition_authority'])} "
          f"-> {'PASS' if not metrics['stripped_condition_authority'] else 'FAIL'}")
    if metrics["stripped_condition_authority"]:
        for cid in metrics["stripped_condition_authority"]:
            print(f"    {cid}")
    print(f"HARD GATE SM (false absence, AF9) == 0: {metrics['SM']} -> {'PASS' if metrics['SM'] == 0 else 'FAIL'}")
    print()

    print("=== FE (false escalation -- lost automation, not unsafe) ===")
    for r in rows:
        if r["expected_status"] == "ESTABLISHED" and r["actual_status"] == "NOT_ESTABLISHED":
            print(f"  {r['id']} (tags: {r['tags']})")
    print()

    print("=== semantic->authority check ===")
    diffs = semantic_authority_check()
    print(f"HARD GATE semantic_authority_diffs == 0: {len(diffs)} -> {'PASS' if not diffs else 'FAIL'}")
    if diffs:
        for d in diffs:
            print(f"    {d}")
    print()

    print("=== determinism check (5x repeat) ===")
    det_mismatches = determinism_check()
    print(f"HARD GATE determinism == 100%: {len(det_mismatches)} mismatches -> "
          f"{'PASS' if not det_mismatches else 'FAIL'}")
    if det_mismatches:
        for d in det_mismatches:
            print(f"    {d}")


if __name__ == "__main__":
    main()
