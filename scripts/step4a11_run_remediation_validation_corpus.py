"""Step 4A.11 Remediation — Phase 7 executes the LOCKED fresh 167-case
validation corpus exactly once against frozen remediation production
(2f8d4762cec595ec6b5f7a16edd5b885e9bde67d). Authoritative run: no tuning
after results are seen. The only permitted subsequent execution is a
determinism reproduction using the identical frozen configuration.
"""
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import indemnification_policy_engine as ie
import liability_policy_engine as le
import payment_terms_policy_engine as pe
from benchmarks.step4a11_remediation_validation_corpus import CASES


def _actual_indemnification(text, is_mutual_expected):
    facts = ie.extract_indemnification_facts(text)
    if facts is None or not facts.obligations:
        return "NOT_ESTABLISHED", None
    if is_mutual_expected:
        mutual_ok = any(ob.is_mutual_reciprocal for ob in facts.obligations)
        return ("ESTABLISHED" if mutual_ok else "NOT_ESTABLISHED"), None
    ob = facts.obligations[0]
    return "ESTABLISHED", {"actor": ob.indemnifying_role, "beneficiary": ob.indemnified_role}


def _actual_liability(text):
    facts = le.extract_liability_facts(text)
    if not facts or not facts.provisions:
        return "NOT_ESTABLISHED", None
    p = facts.controlling_provision or facts.provisions[0]
    cap, _ = p.general_cap_expression.effective_cap() if p.general_cap_expression.structure != "unresolved" else (None, None)
    if cap is None:
        return "NOT_ESTABLISHED", None
    if cap.kind == "fee_multiplier" and cap.multiplier is not None:
        return "ESTABLISHED", {"kind": "multiplier", "multiplier": cap.multiplier}
    if cap.kind == "fixed_amount" and cap.fixed_amount is not None:
        return "ESTABLISHED", {"kind": "fixed", "fixed_amount": cap.fixed_amount}
    if cap.kind == "unlimited":
        return "ESTABLISHED", {"kind": "unlimited"}
    return "NOT_ESTABLISHED", None


def _actual_payment(text, expected_dimension):
    facts = pe.extract_payment_facts(text)
    if facts is None:
        return "NOT_ESTABLISHED", None
    if expected_dimension == "net_days":
        if facts.net_days is None:
            return "NOT_ESTABLISHED", None
        return "ESTABLISHED", {"net_days": facts.net_days}
    established_any = facts.net_days is not None or getattr(facts, "late_fee_rate_percent", None) is not None
    return ("ESTABLISHED" if established_any else "NOT_ESTABLISHED"), None


def run():
    rows = []
    for c in CASES:
        is_mutual = c["expected"] is None and c["expected_status"] == "ESTABLISHED" and c["adapter"] == "indemnification"
        if c["adapter"] == "indemnification":
            status, value = _actual_indemnification(c["text"], is_mutual)
        elif c["adapter"] == "liability":
            status, value = _actual_liability(c["text"])
        else:
            status, value = _actual_payment(c["text"], c["expected_dimension"])

        expected_status = c["expected_status"]
        correct_value = True
        if expected_status == "ESTABLISHED" and c["expected"]:
            if c["adapter"] == "indemnification":
                correct_value = value is not None and value.get("actor") == c["expected"].get("actor") and value.get("beneficiary") == c["expected"].get("beneficiary")
            else:
                correct_value = value == c["expected"]

        rows.append({
            "id": c["id"], "focus": c["focus"], "adapter": c["adapter"],
            "expected_status": expected_status, "actual_status": status,
            "correct_value": correct_value,
        })
    return rows


def classify(rows):
    CA = CR = FE = WC = 0
    wrong_ownership = []
    for r in rows:
        exp, act = r["expected_status"], r["actual_status"]
        if exp == "ESTABLISHED" and act == "ESTABLISHED" and r["correct_value"]:
            CA += 1
        elif exp == "ESTABLISHED" and act == "NOT_ESTABLISHED":
            FE += 1
        elif exp in ("NOT_ESTABLISHED", "CONFLICTING") and act in ("NOT_ESTABLISHED", "CONFLICTING"):
            CR += 1
        else:
            WC += 1
            wrong_ownership.append(r["id"])
    return {"CA": CA, "CR": CR, "FE": FE, "WC": WC, "wrong_ownership": wrong_ownership}


def by_focus(rows):
    out = defaultdict(lambda: {"CA": 0, "CR": 0, "FE": 0, "WC": 0, "total": 0})
    for r in rows:
        f = r["focus"]
        out[f]["total"] += 1
        exp, act = r["expected_status"], r["actual_status"]
        if exp == "ESTABLISHED" and act == "ESTABLISHED" and r["correct_value"]:
            out[f]["CA"] += 1
        elif exp == "ESTABLISHED" and act == "NOT_ESTABLISHED":
            out[f]["FE"] += 1
        elif exp in ("NOT_ESTABLISHED", "CONFLICTING") and act in ("NOT_ESTABLISHED", "CONFLICTING"):
            out[f]["CR"] += 1
        else:
            out[f]["WC"] += 1
    return dict(out)


def semantic_authority_check():
    hybrid = {c["id"]: _actual_indemnification(c["text"], False) for c in CASES if c["adapter"] == "indemnification"}
    ie.HYBRID_DISCOVERY_ENABLED = False
    regex_only = {c["id"]: _actual_indemnification(c["text"], False) for c in CASES if c["adapter"] == "indemnification"}
    ie.HYBRID_DISCOVERY_ENABLED = True
    return [cid for cid in hybrid if hybrid[cid] != regex_only[cid]]


def determinism_check(repeats=5):
    def one_pass(c):
        if c["adapter"] == "indemnification":
            return _actual_indemnification(c["text"], c["expected"] is None and c["expected_status"] == "ESTABLISHED")
        if c["adapter"] == "liability":
            return _actual_liability(c["text"])
        return _actual_payment(c["text"], c["expected_dimension"])

    baseline = {c["id"]: one_pass(c) for c in CASES}
    mismatches = []
    for _ in range(repeats - 1):
        for c in CASES:
            if one_pass(c) != baseline[c["id"]]:
                mismatches.append(c["id"])
    return mismatches


if __name__ == "__main__":
    rows = run()
    metrics = classify(rows)
    print(f"Total cases: {len(rows)}")
    print(f"CA={metrics['CA']} CR={metrics['CR']} FE={metrics['FE']} WC={metrics['WC']}")
    n_exp_est = sum(1 for r in rows if r["expected_status"] == "ESTABLISHED")
    print(f"Automation Recall: {metrics['CA']}/{n_exp_est} = {metrics['CA']/n_exp_est:.1%}")
    print(f"\nHARD GATE wrong_ownership/wrong-role-clean == 0: {len(metrics['wrong_ownership'])} -> "
          f"{'PASS' if not metrics['wrong_ownership'] else 'FAIL'}")
    for cid in metrics["wrong_ownership"]:
        print(f"    {cid}")

    print("\n=== by focus ===")
    for k, v in sorted(by_focus(rows).items()):
        print(f"  {k}: {v}")

    diffs = semantic_authority_check()
    print(f"\nHARD GATE semantic_authority_diffs == 0: {len(diffs)} -> {'PASS' if not diffs else 'FAIL'}")

    mism = determinism_check(5)
    print(f"HARD GATE determinism == 100%: {len(mism)} mismatches -> {'PASS' if not mism else 'FAIL'}")

    with open("artifacts/step4a11_remediation/phase7_validation_run.json", "w") as f:
        json.dump({"rows": rows, "metrics": {k: v for k, v in metrics.items() if not isinstance(v, list)},
                    "wrong_ownership": metrics["wrong_ownership"],
                    "semantic_authority_diffs": diffs, "determinism_mismatches": mism}, f, indent=2)
    print("\nWrote artifacts/step4a11_remediation/phase7_validation_run.json")
