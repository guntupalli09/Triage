#!/usr/bin/env python3
"""Auto-classifies the Step 4A.3 held-out corpus rerun against the frozen
GT, bucketing CA/CR/FE/WC. Value matching is a best-effort substring/
normalized-number heuristic — ambiguous cases are flagged NEEDS_MANUAL
rather than silently bucketed, since fabricating a bucket would violate
the "never fabricate ground truth" rule. This script does not modify any
production file or the frozen corpus."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import liability_policy_engine as lpe
import indemnification_policy_engine as ie
import payment_terms_policy_engine as pte
from benchmarks.step4a2_heldout_corpus import CASES as SEMANTIC_CASES
from benchmarks.step4a2_formatting_mutations import MUT_CASES
from benchmarks.run_step4a2_heldout import run_case

CLEAN_STATES = {"ACCEPT", "ACCEPT_WITH_NOTE", "NEGOTIATE", "MUST_REDLINE", "PROHIBITED", "ESCALATE", "NOT_APPLICABLE"}


def norm(s):
    if s is None:
        return None
    s = str(s).lower()
    s = re.sub(r"[,$]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def value_matches(extracted_summary, our_position, gt_side, gt_value):
    ok_side = True
    ok_value = True
    hay = norm(extracted_summary)
    if gt_side is not None:
        pos_vals = [norm(v) for v in (our_position or {}).values() if v]
        ok_side = any(gt_side.lower() in (v or "") or (v or "") in gt_side.lower() for v in pos_vals) or (gt_side.lower() in (hay or ""))
    if gt_value:
        gv = norm(gt_value)
        # try each "/"-or-","-separated token of the gt value against the summary
        tokens = re.split(r"[;/]| — | -- ", str(gt_value))
        ok_value = any(norm(t) and norm(t) in (hay or "") for t in tokens) if tokens else (gv in (hay or ""))
    return ok_side and ok_value


def classify(case, decision, our_position):
    gt = case["gt"]
    review_expected = gt["review_expected"]
    state = decision.state
    if state == "REQUIRES_REVIEW":
        return "CR" if review_expected else "FE"
    if state not in CLEAN_STATES:
        return "NEEDS_MANUAL"
    if review_expected:
        return "WC"  # clean decision reached where review was required -> wrong-clean
    # clean decision, review not expected -> compare to gt value/side
    gt_side = gt.get("correct_side")
    gt_value = gt.get("correct_value")
    if gt_side is None and gt_value is None:
        return "CA"  # no specific value asserted, any clean decision accepted
    matched = value_matches(decision.extracted_summary, our_position, gt_side, gt_value)
    return "CA" if matched else "NEEDS_MANUAL"


def main():
    all_cases = SEMANTIC_CASES + MUT_CASES
    counts = {"CA": 0, "CR": 0, "FE": 0, "WC": 0, "NEEDS_MANUAL": 0}
    wc_ids = []
    manual_ids = []
    for case in all_cases:
        decision, our_position = run_case(case)
        bucket = classify(case, decision, our_position)
        counts[bucket] += 1
        if bucket == "WC":
            wc_ids.append(case["id"])
        if bucket == "NEEDS_MANUAL":
            manual_ids.append(case["id"])

    total = len(all_cases)
    automatic = counts["CA"] + counts["WC"]
    print(f"Total cases: {total}")
    print(f"CA={counts['CA']} CR={counts['CR']} FE={counts['FE']} WC={counts['WC']} NEEDS_MANUAL={counts['NEEDS_MANUAL']}")
    if automatic:
        print(f"WCDR (WC/automatic) = {counts['WC']/automatic:.1%}")
    print(f"CADR (CA/total) = {counts['CA']/total:.1%}")
    print(f"\nWC case ids ({len(wc_ids)}): {wc_ids}")
    print(f"\nNEEDS_MANUAL case ids ({len(manual_ids)}): {manual_ids}")


if __name__ == "__main__":
    main()
