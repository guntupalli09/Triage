#!/usr/bin/env python3
"""Step 4A.7.6 — absence audit (the Phase 11 spec Step 4A.7.1 disclosed as
"not independently rebuilt from scratch").

Runs every targeted absence case across the three adapters (the existing
liability/indemnification absence families from the locked Step 4A.6
corpus, plus the new payment_terms absence corpus this step adds) and
classifies the extraction-return path as one of:

  CONFIRMED-ABSENT              (A) — the concept genuinely is not in the
                                       document, and the system correctly,
                                       confidently says so.
  NOT-RECOGNIZED                 (B) — the concept IS present in the
                                       document's text, but the system
                                       reported it as absent anyway — a real
                                       false-absence defect, distinct from A.
  RECOGNIZED-BUT-UNRESOLVED      (C) — the system correctly recognized the
                                       clause exists, but could not resolve
                                       enough of it to reach a clean decision
                                       (REQUIRES_REVIEW) — correct, not a
                                       false absence.
  EXPECTED-BUT-MISSING           (D) — policy configuration expects a
                                       specific sub-fact (e.g. a late-fee
                                       rate, a tax-responsibility statement)
                                       that the document never addresses —
                                       must escalate, not be silently
                                       treated as satisfied.
  NOT-APPLICABLE                     — the fact category genuinely doesn't
                                       apply to this document (e.g. a
                                       security deposit clause is not the
                                       operative payment-terms provision).

Verifies B != A, C != A, D != A are held apart by measuring: false-absence
rate (B / (A+B) — cases genuinely present but reported as CONFIRMED-ABSENT)
and unnecessary-review rate isn't separately meaningful here since C is
itself the correct outcome for a recognized-but-unresolved clause.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case
from benchmarks.step4a6_corpus_liability_absence import LIABILITY_ABSENCE
from benchmarks.step4a6_corpus_indemnification_absence import INDEMNIFICATION_ABSENCE
from benchmarks.step4a7_6_payment_absence_corpus import CASES as PAYMENT_ABSENCE

CLAUSE_KEYWORDS = {
    "liability": [r"\blimitation of liability\b", r"\bliability\b.{0,40}\bshall\b",
                  r"\baggregate liability\b"],
    "indemnification": [r"\bindemnif", r"hold\s+\w+\s+harmless", r"bear\s+full\s+responsibility\s+for\s+defending",
                        r"make\s+\w+\s+whole\s+for"],
    "payment_terms": [r"\bpayment terms\b", r"\bshall pay\b", r"\bremit\b", r"\bcompensation\b",
                       r"\bfees and charges\b", r"\bremittance\b", r"\bsecurity deposit\b"],
}


def _clause_language_present(adapter, text):
    return any(re.search(p, text, re.I) for p in CLAUSE_KEYWORDS[adapter])


def classify(adapter, case, decision):
    text = case["text"]
    present = _clause_language_present(adapter, text)
    state = decision.state

    if case["id"] == "A7-PA-09":
        # Deliberately-present-but-inapplicable control (security deposit,
        # not the operative payment-terms clause).
        return "NOT-APPLICABLE" if state == "NOT_APPLICABLE" else \
            f"MISCLASSIFIED (expected NOT-APPLICABLE, got {state})"

    if state == "NOT_APPLICABLE":
        return "CONFIRMED-ABSENT" if not present else "NOT-RECOGNIZED"
    if state == "REQUIRES_REVIEW":
        return "RECOGNIZED-BUT-UNRESOLVED" if present else "NOT-RECOGNIZED(escalated-blind)"
    if state in ("MUST_REDLINE", "ESCALATE", "NEGOTIATE"):
        return "EXPECTED-BUT-MISSING" if present else "NOT-RECOGNIZED(escalated-blind)"
    if state in ("ACCEPT", "ACCEPT_WITH_NOTE"):
        return f"UNEXPECTED-CLEAN (state={state}, present={present})"
    return f"UNCLASSIFIED (state={state}, present={present})"


def main():
    pool = list(LIABILITY_ABSENCE) + list(INDEMNIFICATION_ABSENCE) + list(PAYMENT_ABSENCE)
    print(f"Total absence cases: {len(pool)}\n")

    counts = {}
    hard_findings = []
    for c in pool:
        decision, _ = run_case(c["adapter"], c["text"], c["kwargs"])
        cls = classify(c["adapter"], c, decision)
        counts[cls] = counts.get(cls, 0) + 1
        print(f"[{c['id']}] adapter={c['adapter']} state={decision.state} -> {cls}")
        if cls.startswith("NOT-RECOGNIZED") or cls.startswith("MISCLASSIFIED") or \
                cls.startswith("UNCLASSIFIED"):
            hard_findings.append((c["id"], c["adapter"], cls, decision.state))

    print()
    print("=== CLASSIFICATION COUNTS ===")
    for cls, n in sorted(counts.items()):
        print(f"  {cls}: {n}")

    confirmed_absent = counts.get("CONFIRMED-ABSENT", 0)
    not_recognized = sum(v for k, v in counts.items() if k.startswith("NOT-RECOGNIZED"))
    false_absence_rate = (100.0 * not_recognized / (confirmed_absent + not_recognized)) \
        if (confirmed_absent + not_recognized) else 0.0
    print()
    print(f"False-absence rate (present-but-reported-absent / all absent-shaped outcomes): "
          f"{not_recognized}/{confirmed_absent + not_recognized} ({false_absence_rate:.1f}%)")

    print()
    print(f"=== HARD FINDINGS: {len(hard_findings)} ===")
    for row in hard_findings:
        print(" ", row)


if __name__ == "__main__":
    main()
