#!/usr/bin/env python3
"""
Verifier benchmark (Step 4A.1) — measures liability_policy_engine's
_has_liability_concept_nearby() directly (CONCEPT+LIMIT verification for a
single candidate value), independent of final policy decisions, plus an
end-to-end cross-reference resolution section (genuine / unrelated / mixed).

Section 1 — direct candidate verification: constructs a CapValue at a known
offset within a sentence and checks whether _has_liability_concept_nearby
correctly accepts (genuine liability cap) or rejects (unrelated numeric
concept) it.

Section 2 — end-to-end cross-reference resolution: full extract+evaluate
liability adapter, corpus of genuine / unrelated / mixed referenced
schedules.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import liability_policy_engine as lpe

# ---------------------------------------------------------------------------
# Section 1: direct CONCEPT+LIMIT verification (15 positive + 15 negative)
# ---------------------------------------------------------------------------

POSITIVE_CASES = [
    ("pos-01-shall-not-exceed", "Provider's aggregate liability shall not exceed $500,000 under this Agreement."),
    ("pos-02-multiplier-fees", "Provider's aggregate liability shall not exceed 2 times the annual fees paid."),
    ("pos-03-intervening-clause", "In no event shall either party's liability arising under this Agreement exceed 2 times the total annual fees paid in the preceding twelve (12) months."),
    ("pos-04-total-liability-under-or-relating", "The total liability of either party under or relating to this Agreement shall be limited to $1,000,000."),
    ("pos-05-maximum-aggregate", "The maximum aggregate liability of Provider under this Agreement is $2,000,000."),
    ("pos-06-contract-tort-or-otherwise", "Liability, whether in contract, tort, or otherwise, shall not exceed 2 times the fees paid in the preceding twelve (12) months."),
    ("pos-07-referenced-schedule-heading", "Exhibit A: Risk Allocation. Provider's maximum aggregate liability to Customer shall not exceed $2,000,000."),
    ("pos-08-unusual-heading-2", "Schedule 3: Commercial Terms. Notwithstanding any other provision, aggregate liability under this Agreement is capped at $750,000."),
    ("pos-09-modifier-between", "Provider's liability, calculated on a per-claim basis and subject to Section 14.2, shall not exceed $1,000,000."),
    ("pos-10-multiline", "Provider's aggregate\nliability under this Agreement\nshall not exceed $500,000."),
    ("pos-11-parenthetical", "In no event shall Provider's liability exceed (i) $500,000, or (ii) the fees paid in the preceding year, whichever is greater."),
    ("pos-12-uncapped-negative-signal", "Provider's liability for breaches of confidentiality shall be uncapped, but all other liability shall not exceed $1,000,000."),
    ("pos-13-ceiling-word", "The ceiling on Provider's aggregate liability under this Agreement is $3,000,000."),
    ("pos-14-cumulative", "Provider's cumulative liability across all claims shall not exceed 2 times the fees paid."),
    ("pos-15-liable-for-phrasing", "In no event shall Provider be liable for amounts exceeding $500,000 in the aggregate."),
]

NEGATIVE_CASES = [
    ("neg-01-sla-service-credit", "Provider's service credit obligation for missed response times shall not exceed $10,000 per incident."),
    ("neg-02-insurance-limit", "Provider shall maintain commercial general liability insurance with limits of not less than $2,000,000 per occurrence."),
    ("neg-03-purchase-price", "The purchase price for the Deliverables shall not exceed $500,000."),
    ("neg-04-fee-amount", "The annual license fee payable by Customer shall not exceed $100,000."),
    ("neg-05-damages-example", "For illustration purposes only, in a scenario where damages total $50,000, no party asserts entitlement to insurance proceeds."),
    ("neg-06-notice-period", "Either party may terminate this Agreement upon written notice not to exceed $5,000 in associated administrative costs, without regard to Provider's liability under any other provision."),
    ("neg-07-deductible", "The deductible under Provider's insurance policy shall not exceed $25,000 per claim."),
    ("neg-08-indemnification-basket", "Customer's indemnification obligations shall not apply until aggregate claims exceed the $50,000 basket."),
    ("neg-09-termination-fee", "Customer shall pay a termination fee not to exceed $75,000 upon termination for convenience."),
    ("neg-10-security-deposit", "The security deposit held by Provider shall not exceed one month's fees, or $20,000, whichever is less."),
    ("neg-11-unrelated-schedule-number", "Schedule B: Support Levels. Provider shall respond to Severity 1 tickets within two hours and shall issue service credits not to exceed $10,000 per incident."),
    ("neg-12-liability-word-service-credit-same-sentence", "Without limiting Provider's liability generally, Provider's service credit obligation for missed response times shall not exceed $10,000 per incident."),
    ("neg-13-followed-by-unrelated-definition", "Limitation of Liability. Provider's liability shall be as set forth in Schedule C. Schedule C: Definitions. 'Threshold Amount' means $500,000."),
    ("neg-14-cross-ref-identifier", "As referenced in Section 8.3(a)(ii), the applicable amount is $500,000."),
    ("neg-15-late-fee", "A late fee not to exceed 1.5% per month, up to $5,000, shall apply to overdue invoices."),
]


import re

_DOLLAR_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
_MULT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:x|times)\b", re.I)


def _locate_numeric_span(text):
    """Finds the FIRST dollar or multiplier figure's span in `text`, for
    constructing a synthetic CapValue at the correct offset. This
    benchmark measures the CONCEPT+LIMIT verifier in isolation — it does
    NOT re-test whether _find_cap_values' own regex would have extracted
    this exact drafting pattern (that is a separate, pre-existing
    extraction-recall question, out of Step 4A.1's scope; see the
    'value_extraction_gap' notes below for cases where it independently
    fails)."""
    m = _DOLLAR_RE.search(text) or _MULT_RE.search(text)
    if not m:
        return None
    return m.start(), m.end()


def run_section1():
    print("## Section 1 — Direct CONCEPT+LIMIT verification (isolated from VALUE extraction)\n")
    print(f"Corpus size: {len(POSITIVE_CASES) + len(NEGATIVE_CASES)} cases ({len(POSITIVE_CASES)} positive, {len(NEGATIVE_CASES)} negative)\n")
    print("Measures _has_liability_concept_nearby() directly against a synthetic CapValue at the "
          "numeric figure's actual span — isolated from _find_cap_values' own separate, pre-existing "
          "value-extraction drafting-pattern coverage (out of Step 4A.1's scope; noted separately "
          "below where it independently fails to extract a value at all).\n")
    tp = fn = tn = fp = 0
    value_extraction_gaps = []
    rows = []
    for case_id, text in POSITIVE_CASES:
        span = _locate_numeric_span(text)
        assert span is not None, f"{case_id}: test case itself has no numeric figure"
        cap = lpe.CapValue(kind="fixed_amount", fixed_amount=1.0, start_index=span[0], end_index=span[1])
        established = lpe._has_liability_concept_nearby(text, cap)
        if established:
            tp += 1
        else:
            fn += 1
        # Separately note (not counted against the concept verifier) whether
        # _find_cap_values would ALSO have extracted a value here at all.
        if not lpe._find_cap_values(text):
            value_extraction_gaps.append(case_id)
        rows.append((case_id, "genuine", "ACCEPTED" if established else "REJECTED",
                     "OK" if established else "MISS (concept verifier)"))
    for case_id, text in NEGATIVE_CASES:
        span = _locate_numeric_span(text)
        assert span is not None, f"{case_id}: test case itself has no numeric figure"
        cap = lpe.CapValue(kind="fixed_amount", fixed_amount=1.0, start_index=span[0], end_index=span[1])
        established = lpe._has_liability_concept_nearby(text, cap)
        if established:
            fp += 1
        else:
            tn += 1
        rows.append((case_id, "unrelated", "ACCEPTED" if established else "REJECTED",
                     "FALSE ACCEPT (concept verifier)" if established else "OK"))

    print("| id | expected | concept-verifier result | note |")
    print("|---|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |")

    n_pos, n_neg = len(POSITIVE_CASES), len(NEGATIVE_CASES)
    genuine_recall = tp / n_pos if n_pos else float("nan")
    unrelated_rejection = tn / n_neg if n_neg else float("nan")
    false_acceptance = fp / n_neg if n_neg else float("nan")
    unnecessary_rejection = fn / n_pos if n_pos else float("nan")
    print(f"\n- Genuine-cap verification recall (concept+limit check alone): {genuine_recall:.1%} ({tp}/{n_pos})")
    print(f"- Unrelated-number rejection rate: {unrelated_rejection:.1%} ({tn}/{n_neg})")
    print(f"- False acceptance rate: {false_acceptance:.1%} ({fp}/{n_neg})")
    print(f"- Unnecessary rejection/escalation rate: {unnecessary_rejection:.1%} ({fn}/{n_pos})")
    if value_extraction_gaps:
        print(f"\nNote — separately, {len(value_extraction_gaps)}/{n_pos} genuine cases would ALSO fail at the "
              f"unrelated VALUE-extraction step (_find_cap_values), independent of concept verification: "
              f"{', '.join(value_extraction_gaps)}. This is a pre-existing _find_cap_values drafting-pattern "
              f"coverage gap, not a Step 4A.1 regression — flagged for a future extraction-recall pass, out "
              f"of this step's scope.")
    return {"n_pos": n_pos, "n_neg": n_neg, "tp": tp, "fn": fn, "tn": tn, "fp": fp, "value_extraction_gaps": value_extraction_gaps}


# ---------------------------------------------------------------------------
# Section 2: end-to-end cross-reference resolution — genuine / unrelated / mixed
# ---------------------------------------------------------------------------

FILLER = "Filler text between sections. " * 25


def xref_text(delegation_label, schedule_body, schedule_label=None):
    schedule_label = schedule_label or delegation_label
    return (
        f"9. Limitation of Liability. Provider's aggregate liability shall be as set forth "
        f"in {delegation_label}.\n\n" + FILLER + f"\n\n{schedule_label}: {schedule_body}"
    )


GENUINE_XREF_CASES = [
    ("gxr-01", xref_text("Schedule C", "Liability. Provider's maximum aggregate liability shall not exceed $500,000.")),
    ("gxr-02", xref_text("Exhibit A", "Risk Allocation. In no event shall either party's liability arising under this Agreement exceed 2 times the annual fees paid.")),
    ("gxr-03", xref_text("Schedule 3", "Commercial Terms. Aggregate liability under this Agreement is capped at $750,000.")),
    ("gxr-04", xref_text("Appendix B", "General Terms. The total liability of either party under or relating to this Agreement shall be limited to $1,000,000.")),
    ("gxr-05", xref_text("Schedule D", "Liability and Indemnification. Provider's cumulative liability across all claims shall not exceed 3 times the fees paid in the preceding twelve (12) months.")),
]

UNRELATED_XREF_CASES = [
    ("uxr-01", xref_text("Schedule C", "Support Service Levels. Provider's obligation to issue service credits shall not exceed $10,000 per incident.")),
    ("uxr-02", xref_text("Exhibit A", "Insurance. Provider shall maintain commercial general liability insurance with limits of not less than $2,000,000.")),
    ("uxr-03", xref_text("Schedule D", "Governing Law. This Agreement is governed by the laws of Delaware.")),
    ("uxr-04", xref_text("Schedule E", "Fees. The annual license fee shall not exceed $250,000.")),
    ("uxr-05", xref_text("Appendix C", "Termination. Customer shall pay a termination fee not to exceed $75,000.")),
]

MIXED_XREF_CASES = [
    ("mxr-01", xref_text("Schedule C", "Commercial Terms. Uptime shall be 99.9% measured monthly. Provider's maximum aggregate liability to Customer shall not exceed $1,000,000.")),
    ("mxr-02", xref_text("Exhibit A", "Terms. Initial term is 3 years, renewal terms of 1 year each. Provider's aggregate liability shall not exceed $500,000.")),
    ("mxr-03", xref_text("Schedule D", "Risk Terms. Provider's service credit obligation shall not exceed $10,000 per incident. Provider's aggregate liability shall not exceed $2,000,000.")),
    ("mxr-04", xref_text("Appendix B", "Insurance and Liability. Insurance limits shall be $2,000,000 per occurrence. Provider's aggregate liability shall not exceed $500,000.")),
    ("mxr-05", xref_text("Schedule E", "Commercial. The purchase price is $500,000. Provider's maximum aggregate liability shall not exceed $1,000,000.")),
]


def run_section2():
    print("\n\n## Section 2 — End-to-end cross-reference resolution\n")
    results = {"genuine": [], "unrelated": [], "mixed": []}
    for label, cases in [("genuine", GENUINE_XREF_CASES), ("unrelated", UNRELATED_XREF_CASES), ("mixed", MIXED_XREF_CASES)]:
        print(f"\n### {label.capitalize()} ({len(cases)} cases)\n")
        print("| id | state | extracted_summary |")
        print("|---|---|---|")
        for case_id, text in cases:
            facts = lpe.extract_liability_facts(text)
            from dataclasses import dataclass
            from typing import Optional, List
            @dataclass
            class P:
                preferred_multiplier: Optional[float] = 1.0
                acceptable_max_multiplier: Optional[float] = 2.0
                negotiate_max_multiplier: Optional[float] = 3.0
                prohibit_unlimited: bool = True
                required_exceptions_json: Optional[List[str]] = None
                fallback_text: Optional[str] = "fallback"
                escalation_approval_authority: Optional[str] = "Legal Director"
                contract_side: str = "mutual"
                require_consequential_damages_exclusion: bool = False
                required_consequential_carveouts_json: Optional[List[str]] = None
            d = lpe.evaluate_liability_policy(facts, P())
            print(f"| {case_id} | {d.state} | {d.extracted_summary!r} |")
            results[label].append((case_id, d.state, d.extracted_summary))
    return results


if __name__ == "__main__":
    s1 = run_section1()
    s2 = run_section2()
