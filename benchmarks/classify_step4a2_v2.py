#!/usr/bin/env python3
"""Step 4A.3 authoritative reclassification of the frozen Step 4A.2
held-out corpus (108 semantic + 10 formatting-mutation cases). Does NOT
modify the corpus or its ground truth. Auto-classifies only when highly
confident; everything else is printed in full for manual judgment (state,
extracted_summary, our_position, unresolved_facts, vs GT) rather than
guessed."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.step4a2_heldout_corpus import CASES as SEMANTIC_CASES
from benchmarks.step4a2_formatting_mutations import MUT_CASES
from benchmarks.run_step4a2_heldout import run_case

CLEAN_STATES = {"ACCEPT", "ACCEPT_WITH_NOTE", "NEGOTIATE", "MUST_REDLINE", "PROHIBITED", "ESCALATE"}


def norm(s):
    if s is None:
        return None
    s = str(s).lower()
    s = re.sub(r"\.00\b", "", s)
    s = re.sub(r"[,$]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main():
    all_cases = SEMANTIC_CASES + MUT_CASES
    results = {}
    for case in all_cases:
        decision, our_position = run_case(case)
        gt = case["gt"]
        review_expected = gt["review_expected"]
        state = decision.state
        row = {
            "id": case["id"], "adapter": case["adapter"], "family": case["family"],
            "state": state, "extracted_summary": decision.extracted_summary,
            "our_position": our_position, "unresolved_facts": decision.unresolved_facts,
            "gt_review_expected": review_expected, "gt_side": gt.get("correct_side"),
            "gt_value": gt.get("correct_value"), "gt_reason": gt.get("reason"),
            "base_id": case.get("base_id"),
        }

        if state == "NOT_APPLICABLE":
            row["auto"] = "NA_OR_SILENT_MISS"  # needs manual: could be genuine NA or a silent miss
        elif state == "REQUIRES_REVIEW":
            row["auto"] = "CR" if review_expected else "FE"
        elif state in CLEAN_STATES:
            if review_expected:
                row["auto"] = "WC"  # unambiguous: any clean decision when review required is wrong-clean
            elif gt.get("correct_side") is None and gt.get("correct_value") is None:
                row["auto"] = "CA"  # no specific answer asserted -> any clean decision accepted
            else:
                gv = norm(gt.get("correct_value"))
                gs = norm(gt.get("correct_side"))
                hay = norm(decision.extracted_summary)
                pos_vals = " ".join(norm(v) or "" for v in (our_position or {}).values())
                side_ok = gs is None or gs in (hay or "") or gs in pos_vals
                val_ok = True
                if gv:
                    tokens = [norm(t) for t in re.split(r"[;/]| — | -- ", str(gt.get("correct_value")))]
                    val_ok = any(t and t in (hay or "") for t in tokens)
                row["auto"] = "CA" if (side_ok and val_ok) else "NEEDS_MANUAL"
        else:
            row["auto"] = "NEEDS_MANUAL"
        results[case["id"]] = row
    return results


if __name__ == "__main__":
    results = main()
    from collections import Counter
    counts = Counter(r["auto"] for r in results.values())
    print("Auto-bucket counts:", dict(counts))
    print()
    for cid, r in results.items():
        if r["auto"] in ("NEEDS_MANUAL", "NA_OR_SILENT_MISS"):
            print(f"--- {cid} [{r['adapter']}] state={r['state']} auto={r['auto']} ---")
            print(f"  extracted_summary: {r['extracted_summary']!r}")
            print(f"  our_position: {r['our_position']}")
            print(f"  unresolved_facts: {r['unresolved_facts']}")
            print(f"  GT: review_expected={r['gt_review_expected']} side={r['gt_side']} value={r['gt_value']}")
            print(f"  GT reason: {r['gt_reason']}")
            print()
