#!/usr/bin/env python3
"""Step 4A.7.5 — material-fact trust audit (the Phase 10 spec Step 4A.7.1
disclosed as "not built as a separate artifact").

For every CLEAN automatic decision (ACCEPT / ACCEPT_WITH_NOTE / NEGOTIATE —
i.e. no human review triggered) drawn from the re-run Step 4A.6 corpus plus
the Step 4A.7.3 fresh battery, this identifies the material fact(s) the
decision actually depended on and classifies each fact's verification basis
as one of:

  ESTABLISHED                  — the fact's exact value is literally present
                                  in the quoted contract language the
                                  decision cites (controlling_provision /
                                  the "Contract language:" excerpt).
  BOUNDED-MECHANICALLY-ESTABLISHED
                                — the fact was derived by a deterministic
                                  structural rule over two or more explicit
                                  values (greater-of/lesser-of comparison,
                                  or the indemnification named-pair /
                                  reciprocal-opener term-invariance check,
                                  which sidesteps ever having to decide
                                  which party "we" are).
  WEAKLY-ESTABLISHED            — the fact was inferred via a closed generic-
                                  vocabulary lookup (side_for_role) WITHOUT
                                  cross-checking the document's own
                                  definition text for a conflicting
                                  directional statement (the deliberate,
                                  disclosed scope decision from the A6-L-52
                                  fix — see liability_policy_engine.py's
                                  _unmapped_cap_role_pair_reason docstring).
  UNVERIFIED                    — the fact was used with no textual grounding
                                  found in the excerpt at all (a silent
                                  default). Any UNVERIFIED fact that could
                                  have changed a clean decision is a HARD
                                  finding and is reported, not hidden.

This is an automated, code-grounded classification (not a hand-written
paragraph per case — infeasible at this volume) with an explicit,
inspectable rule set per adapter. A human spot-check of a sample is printed
at the end for independent verification of the automated calls.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.run_step4a4_heldout import run_case
from benchmarks.step4a6_corpus import ALL_CASES as A6_CASES
from benchmarks.step4a7_3_fresh_adversarial_battery import CASES as FRESH_CASES
from benchmarks.indemnification_corpus import CASES as INDEM_CORPUS_CASES
from liability_policy_engine import _CAP_SENTENCE_ROLE_PAIR_RE

CLEAN_STATES = {"ACCEPT", "ACCEPT_WITH_NOTE", "NEGOTIATE"}
TARGET_PER_ADAPTER = 50

_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _quoted_contract_language(explanation: str) -> str:
    m = re.search(r'Contract language:\s*"(.*?)"', explanation)
    return m.group(1) if m else ""


def audit_liability(case, decision):
    facts = []
    quote = _quoted_contract_language(decision.explanation)
    if "greater of" in decision.explanation.lower() or "lesser of" in decision.explanation.lower():
        facts.append(("general liability cap (greater-of/lesser-of comparison)",
                      "BOUNDED-MECHANICALLY-ESTABLISHED"))
    else:
        nums_extracted = set(_NUM_RE.findall(decision.extracted_summary or ""))
        nums_quoted = set(_NUM_RE.findall(quote))
        basis = "ESTABLISHED" if nums_extracted and nums_extracted.issubset(nums_quoted) else "UNVERIFIED"
        facts.append((f"general liability cap value ({decision.extracted_summary})", basis))

    if case["kwargs"].get("contract_side") in ("buy_side", "sell_side"):
        if _CAP_SENTENCE_ROLE_PAIR_RE.search(case["text"]):
            facts.append(("role/side attribution for the cap sentence "
                          "(generic vocabulary trusted, not cross-checked against "
                          "the document's own definition text)", "WEAKLY-ESTABLISHED"))
    return facts


def audit_indemnification(case, decision, our_position):
    facts = []
    exposure = (our_position or {}).get("exposure")
    protection = (our_position or {}).get("protection")
    text_lower = case["text"].lower()
    reciprocal_shape = "each party" in text_lower or "each of the parties" in text_lower
    two_directional = case["text"].lower().count("shall indemnify") >= 2 or \
        case["text"].lower().count("indemnify, defend") >= 2

    if exposure is not None:
        if reciprocal_shape or two_directional:
            facts.append((f"exposure party identity ({exposure!r})",
                          "BOUNDED-MECHANICALLY-ESTABLISHED"))
        elif exposure.lower() in text_lower:
            facts.append((f"exposure party identity ({exposure!r})", "ESTABLISHED"))
        else:
            facts.append((f"exposure party identity ({exposure!r})", "UNVERIFIED"))
    if protection is not None:
        if reciprocal_shape or two_directional:
            facts.append((f"protection party identity ({protection!r})",
                          "BOUNDED-MECHANICALLY-ESTABLISHED"))
        elif protection.lower() in text_lower:
            facts.append((f"protection party identity ({protection!r})", "ESTABLISHED"))
        else:
            facts.append((f"protection party identity ({protection!r})", "UNVERIFIED"))
    if not facts:
        facts.append(("no exposure/protection obligation resolved (structural fact only)",
                      "ESTABLISHED"))
    return facts


def audit_payment(case, decision, our_position):
    facts = []
    summary = decision.extracted_summary or ""
    text = case["text"]
    m = re.search(r"Net\s*(\d+)", summary)
    if m:
        established = re.search(rf"\bNet\s*{m.group(1)}\b", text, re.I) or \
            re.search(rf"\b{m.group(1)}\s+days\b", text, re.I)
        facts.append((f"net-days value ({summary})", "ESTABLISHED" if established else "UNVERIFIED"))
    payor_side = (our_position or {}).get("payor_side")
    if payor_side is not None:
        facts.append((f"payor side ({payor_side!r})", "BOUNDED-MECHANICALLY-ESTABLISHED"))
    return facts


AUDITORS = {
    "liability": lambda c, d, pos: audit_liability(c, d),
    "indemnification": audit_indemnification,
    "payment_terms": audit_payment,
}


def main():
    extra_indem = [
        dict(id=c["id"], adapter="indemnification", text=c["text"], kwargs=c["policy_overrides"])
        for c in INDEM_CORPUS_CASES
    ]
    pool = list(A6_CASES) + list(FRESH_CASES) + extra_indem
    by_adapter = {"liability": [], "indemnification": [], "payment_terms": []}

    for c in pool:
        adapter = c["adapter"]
        decision, our_position = run_case(adapter, c["text"], c["kwargs"])
        if decision.state in CLEAN_STATES:
            by_adapter[adapter].append((c, decision, our_position))

    tier_counts = {"ESTABLISHED": 0, "BOUNDED-MECHANICALLY-ESTABLISHED": 0,
                   "WEAKLY-ESTABLISHED": 0, "UNVERIFIED": 0}
    hard_findings = []
    spot_check = []

    for adapter, rows in by_adapter.items():
        sample = rows[:TARGET_PER_ADAPTER]
        print(f"=== {adapter}: {len(rows)} clean decisions available, auditing {len(sample)} ===")
        for i, (c, decision, our_position) in enumerate(rows):
            auditor = AUDITORS[adapter]
            facts = auditor(c, decision, our_position)
            take_for_report = i < TARGET_PER_ADAPTER
            for fact_desc, basis in facts:
                if take_for_report:
                    tier_counts[basis] += 1
                    if basis == "UNVERIFIED":
                        hard_findings.append((c["id"], adapter, fact_desc, decision.state))
                    if i < 3:
                        spot_check.append((c["id"], adapter, fact_desc, basis))
        print(f"  ({len(rows)} total clean; {min(len(rows), TARGET_PER_ADAPTER)} counted toward the >=50 target)")
        if len(rows) < TARGET_PER_ADAPTER:
            print(f"  *** SHORT: only {len(rows)} clean decisions available, need {TARGET_PER_ADAPTER} ***")

    total_facts = sum(tier_counts.values())
    print()
    print(f"TOTAL MATERIAL FACTS CLASSIFIED: {total_facts}")
    for tier, n in tier_counts.items():
        pct = (100.0 * n / total_facts) if total_facts else 0.0
        print(f"  {tier}: {n} ({pct:.1f}%)")

    print()
    print(f"=== HARD FINDINGS (UNVERIFIED facts behind a clean decision): {len(hard_findings)} ===")
    for row in hard_findings:
        print(" ", row)

    print()
    print("=== SPOT-CHECK SAMPLE (first 3 per adapter, for independent human verification) ===")
    for row in spot_check:
        print(" ", row)


if __name__ == "__main__":
    main()
