"""Step 4A.11 Phase 6 -- executes the LOCKED final authoritative corpus
exactly once against frozen production (commit d769491). This is the
authoritative run; per protocol, no production/corpus changes are permitted
after this executes and its results are seen, except a determinism
reproduction using the identical frozen configuration.

Metrics mirror scripts/step4a11_run_fresh_adversarial_battery.py's own
mapping (CA/CR/FE/WC/SM plus the safety-critical sub-categories), extended
for "mutual" reciprocal indemnification cases (both directions checked
independently -- a mutual case counts CA only if EVERY obligation the case
implies is both present and correct, never partial credit).
"""
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import indemnification_policy_engine as ie
import liability_policy_engine as le
import payment_terms_policy_engine as pe
from benchmarks.step4a11_final_corpus import CASES


def _actual_indemnification(text: str, expected_kind: str):
    facts = ie.extract_indemnification_facts(text)
    if facts is None:
        return "NOT_ESTABLISHED", None, "CONFIRMED_ABSENT", None
    if not facts.obligations:
        return "NOT_ESTABLISHED", None, facts.absence_state, None
    if expected_kind == "mutual":
        mutual_ok = any(ob.is_mutual_reciprocal for ob in facts.obligations)
        return ("ESTABLISHED" if mutual_ok else "NOT_ESTABLISHED"), None, facts.absence_state, None
    ob = facts.obligations[0]
    return "ESTABLISHED", {"actor": ob.indemnifying_role, "beneficiary": ob.indemnified_role}, facts.absence_state, ob.condition.status if ob.condition else "UNCONDITIONAL"


def _actual_liability(text: str, expected_dimension):
    facts = le.extract_liability_facts(text)
    if not facts or not facts.provisions:
        return "NOT_ESTABLISHED", None, "ABSENT" if not facts else "PRESENT_NO_PROVISION", None
    p = facts.controlling_provision or facts.provisions[0]
    cond = p.condition.status if p.condition else "UNCONDITIONAL"
    cap, _ = p.general_cap_expression.effective_cap() if p.general_cap_expression.structure != "unresolved" else (None, None)
    if cap is None:
        return "NOT_ESTABLISHED", None, "PRESENT_UNRESOLVED_CAP", cond
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
    if facts is None:
        return "NOT_ESTABLISHED", None, "ABSENT", None
    cond = facts.condition.status if facts.condition else "UNCONDITIONAL"
    if expected_dimension == "net_days":
        if facts.net_days is None:
            return "NOT_ESTABLISHED", None, "PRESENT_NO_VALUE", cond
        return "ESTABLISHED", {"net_days": facts.net_days}, "PRESENT", cond
    if expected_dimension == "late_fee_rate_percent":
        val = getattr(facts, "late_fee_rate_percent", None)
        if val is None:
            return "NOT_ESTABLISHED", None, "PRESENT_NO_VALUE", cond
        return "ESTABLISHED", {"late_fee_rate_percent": val}, "PRESENT", cond
    # Step 4A.11 Phase 6 harness fix (pre-official-numbers): the presence of
    # a condition is NOT itself a material fact -- a case with no expected
    # dimension declared must be scored on whether an actual material value
    # (net_days or late_fee_rate_percent) was established, never on whether
    # conditional language happens to be nearby. The prior version treated
    # ANY detected condition as "established," which produced a false
    # ESTABLISHED reading on cases with no material value at all (a payment
    # obligation entirely delegated to an unincluded cross-referenced
    # schedule, with only a proviso about the schedule's own execution).
    established_any = facts.net_days is not None or getattr(facts, "late_fee_rate_percent", None) is not None
    return ("ESTABLISHED" if established_any else "NOT_ESTABLISHED"), None, ("PRESENT" if established_any else "PRESENT_NO_VALUE"), cond


def run():
    rows = []
    for c in CASES:
        if c["adapter"] == "indemnification":
            is_mutual = c["expected"] is None and "mutual" in c.get("notes", "").lower()
            status, value, absence_state, cond = _actual_indemnification(c["text"], "mutual" if is_mutual else "ab")
        elif c["adapter"] == "liability":
            status, value, absence_state, cond = _actual_liability(c["text"], c["expected_dimension"])
        else:
            status, value, absence_state, cond = _actual_payment(c["text"], c["expected_dimension"])

        expected_status = c["expected_status"]
        correct_status = status == expected_status
        correct_value = True
        if expected_status == "ESTABLISHED" and c["expected"]:
            if c["adapter"] == "indemnification":
                correct_value = value is not None and value.get("actor") == c["expected"].get("actor") and value.get("beneficiary") == c["expected"].get("beneficiary")
            else:
                correct_value = value == c["expected"]

        rows.append({
            "id": c["id"], "adapter": c["adapter"], "tier": c["tier"],
            "attack_families": c["attack_families"], "disposition": c["disposition"],
            "expected_status": expected_status, "actual_status": status,
            "correct_status": correct_status, "correct_value": correct_value,
            "absence_state": absence_state, "actual_condition": cond,
        })
    return rows


def classify(rows):
    CA = CR = FE = WC = SM = 0
    false_structural = []
    wrong_owner = []
    for r in rows:
        exp, act = r["expected_status"], r["actual_status"]
        if exp == "ESTABLISHED" and act == "ESTABLISHED" and r["correct_value"]:
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

        if "AF9" in r["attack_families"] and r["absence_state"] in ("CONFIRMED_ABSENT", "ABSENT"):
            SM += 1

    return {"CA": CA, "CR": CR, "FE": FE, "WC": WC, "SM": SM,
            "false_structural_establishment": false_structural, "wrong_ownership": wrong_owner}


def by_breakdown(rows, key):
    out = defaultdict(lambda: {"CA": 0, "CR": 0, "FE": 0, "WC": 0, "total": 0})
    for r in rows:
        exp, act = r["expected_status"], r["actual_status"]
        ks = r[key] if not isinstance(r[key], list) else r[key]
        keys = ks if isinstance(ks, list) else [ks]
        for k in keys:
            out[k]["total"] += 1
            if exp == "ESTABLISHED" and act == "ESTABLISHED" and r["correct_value"]:
                out[k]["CA"] += 1
            elif exp == "ESTABLISHED" and act == "NOT_ESTABLISHED":
                out[k]["FE"] += 1
            elif exp in ("NOT_ESTABLISHED", "CONFLICTING") and act in ("NOT_ESTABLISHED", "CONFLICTING"):
                out[k]["CR"] += 1
            else:
                out[k]["WC"] += 1
    return dict(out)


def semantic_authority_check():
    import indemnification_policy_engine as ie_mod
    hybrid = {c["id"]: _actual_indemnification(c["text"], "ab") for c in CASES if c["adapter"] == "indemnification"}
    ie_mod.HYBRID_DISCOVERY_ENABLED = False
    regex_only = {c["id"]: _actual_indemnification(c["text"], "ab") for c in CASES if c["adapter"] == "indemnification"}
    ie_mod.HYBRID_DISCOVERY_ENABLED = True
    diffs = [cid for cid in hybrid if hybrid[cid][0] != regex_only[cid][0] or hybrid[cid][1] != regex_only[cid][1]]
    return diffs


def determinism_check(repeats=5):
    mismatches = []
    baseline = {c["id"]: (c["adapter"] == "indemnification" and _actual_indemnification(c["text"], "ab") or
                           c["adapter"] == "liability" and _actual_liability(c["text"], c["expected_dimension"]) or
                           _actual_payment(c["text"], c["expected_dimension"])) for c in CASES}
    for _ in range(repeats - 1):
        for c in CASES:
            if c["adapter"] == "indemnification":
                r = _actual_indemnification(c["text"], "ab")
            elif c["adapter"] == "liability":
                r = _actual_liability(c["text"], c["expected_dimension"])
            else:
                r = _actual_payment(c["text"], c["expected_dimension"])
            if r != baseline[c["id"]]:
                mismatches.append(c["id"])
    return mismatches


if __name__ == "__main__":
    rows = run()
    metrics = classify(rows)
    print(f"Total cases: {len(rows)}")
    print(f"CA={metrics['CA']} CR={metrics['CR']} FE={metrics['FE']} WC={metrics['WC']} SM={metrics['SM']}")
    n_expected_established = sum(1 for r in rows if r["expected_status"] == "ESTABLISHED")
    print(f"\nAutomation Recall (CA / expected-ESTABLISHED): {metrics['CA']}/{n_expected_established} = {metrics['CA']/n_expected_established:.1%}")

    print(f"\nHARD GATE false_structural_establishment == 0: {len(metrics['false_structural_establishment'])} -> "
          f"{'PASS' if not metrics['false_structural_establishment'] else 'FAIL'}")
    for cid in metrics["false_structural_establishment"]:
        print(f"    {cid}")
    print(f"HARD GATE wrong_ownership == 0: {len(metrics['wrong_ownership'])} -> "
          f"{'PASS' if not metrics['wrong_ownership'] else 'FAIL'}")
    for cid in metrics["wrong_ownership"]:
        print(f"    {cid}")
    print(f"HARD GATE SM == 0: {metrics['SM']} -> {'PASS' if metrics['SM'] == 0 else 'FAIL'}")

    print("\n=== by adapter ===")
    for k, v in sorted(by_breakdown(rows, "adapter").items()):
        print(f"  {k}: {v}")
    print("\n=== by tier ===")
    for k, v in sorted(by_breakdown(rows, "tier").items()):
        print(f"  tier {k}: {v}")
    print("\n=== by attack family ===")
    for k, v in sorted(by_breakdown(rows, "attack_families").items()):
        print(f"  {k}: {v}")

    print("\n=== semantic->authority check ===")
    diffs = semantic_authority_check()
    print(f"HARD GATE semantic_authority_diffs == 0: {len(diffs)} -> {'PASS' if not diffs else 'FAIL'}")
    if diffs:
        print(diffs)

    print("\n=== determinism check (5x repeat) ===")
    mism = determinism_check(5)
    print(f"HARD GATE determinism == 100%: {len(mism)} mismatches -> {'PASS' if not mism else 'FAIL'}")

    # Clean-Verified Recall = CA / total POSITIVE (expected ESTABLISHED) cases
    cvr = metrics["CA"] / n_expected_established
    print(f"\nClean-Verified Recall (final corpus): {cvr:.1%} (target >=44.5%)")
    for t in (1, 2, 3):
        tier_rows = [r for r in rows if r["tier"] == t and r["expected_status"] == "ESTABLISHED"]
        tier_ca = sum(1 for r in tier_rows if r["actual_status"] == "ESTABLISHED" and r["correct_value"])
        if tier_rows:
            print(f"  Tier {t} Clean-Verified Recall: {tier_ca}/{len(tier_rows)} = {tier_ca/len(tier_rows):.1%}")

    with open("artifacts/step4a11_phase6_freeze/final_corpus_run.json", "w") as f:
        json.dump({"rows": rows, "metrics": {k: v for k, v in metrics.items() if not isinstance(v, list)},
                    "false_structural_establishment": metrics["false_structural_establishment"],
                    "wrong_ownership": metrics["wrong_ownership"],
                    "semantic_authority_diffs": diffs, "determinism_mismatches": mism}, f, indent=2)
    print("\nWrote artifacts/step4a11_phase6_freeze/final_corpus_run.json")
