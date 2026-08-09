"""
Labeled adversarial corpus for the Limitation-of-Liability policy engine
benchmark (see benchmarks/run_liability_benchmark.py).

Ground truth is recorded at two levels, scored independently:
  1. Structured facts: general cap (kind/multiplier/fixed_amount), the
     treatment of each of the 7 named carve-out categories, consequential-
     damages exclusion, and mutuality — what liability_policy_engine's
     extraction layer is actually supposed to produce.
  2. Expected policy state: what a competent human reviewer would decide,
     under DEFAULT_POLICY unless a case overrides it — not what the current
     engine happens to output. Several drafting patterns here (greater-of/
     lesser-of, per-claim vs aggregate, cross-references, amendments) are
     structurally beyond what the engine's simple general_cap model can
     represent; for those the ground-truth expected_state is REQUIRES_REVIEW
     — the legally correct behavior is to abstain rather than guess — even
     though the engine may not reach that answer today. That gap is the
     point of this corpus, not a labeling error.

expected_general_cap:
    None                 -> facts is None entirely (no clause found at all)
    "SKIP"                -> don't score fact-level extraction for this case
                             (structure is outside today's fact model);
                             only the final policy state is scored
    {"kind": ..., "multiplier": ..., "fixed_amount": ...} -> scored exactly

expected_category_treatments: partial dict {category: expected_treatment}.
Only categories explicitly listed are scored — an omitted category is not
assumed to be "not_addressed"; it is simply not asserted for that case.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "preferred_multiplier": 1.0,
    "acceptable_max_multiplier": 2.0,
    "negotiate_max_multiplier": 3.0,
    "prohibit_unlimited": True,
    "required_exceptions_json": [],
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: liability capped at 1x annual fees.",
    "contract_side": "mutual",
    "require_consequential_damages_exclusion": False,
    "required_consequential_carveouts_json": [],
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    expected_general_cap: Any = "SKIP",
    expected_category_treatments: Optional[Dict[str, str]] = None,
    expected_consequential_excluded: Optional[bool] = "SKIP",
    expected_mutuality: str = "SKIP",
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id,
        "tags": tags,
        "text": text,
        "expected_state": expected_state,
        "expected_general_cap": expected_general_cap,
        "expected_category_treatments": expected_category_treatments or {},
        "expected_consequential_excluded": expected_consequential_excluded,
        "expected_mutuality": expected_mutuality,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# 1. Clean multiplier caps
# ---------------------------------------------------------------------------
CASES += [
    case("clean-01", ["clean_multiplier"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed 1 times the total annual fees paid in the twelve (12) months "
         "preceding the claim.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0}),
    case("clean-02", ["clean_multiplier"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed 2 times the total fees paid in the twelve (12) months preceding "
         "the claim.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         notes="Boundary of the auto-accept range."),
    case("clean-03", ["clean_multiplier"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed 2.5 times the total annual fees paid in the twelve (12) months "
         "preceding the claim.",
         "NEGOTIATE", {"kind": "fee_multiplier", "multiplier": 2.5}),
    case("clean-04", ["clean_multiplier"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed 3 times the total fees paid in the twelve (12) months preceding "
         "the claim.",
         "NEGOTIATE", {"kind": "fee_multiplier", "multiplier": 3.0},
         notes="Boundary of the negotiable range."),
    case("clean-05", ["clean_multiplier"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed 3.5 times the total annual fees paid in the twelve (12) months "
         "preceding the claim.",
         "ESCALATE", {"kind": "fee_multiplier", "multiplier": 3.5}),
    case("clean-06", ["clean_multiplier", "word_number"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability under "
         "this Agreement exceed two (2) times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         notes="Word-form multiplier with a parenthetical digit."),
]

# ---------------------------------------------------------------------------
# 2. Fees paid vs fees payable (basis distinction the engine does not model —
#    extraction of the multiplier itself should still succeed either way)
# ---------------------------------------------------------------------------
CASES += [
    case("basis-01", ["fee_basis"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees payable under this Agreement.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         notes="'payable' vs 'paid' is a real legal distinction (owed vs remitted) the engine does not model as a separate fact."),
    case("basis-02", ["fee_basis"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2 times the fees "
         "payable in the twelve (12) months preceding the claim.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0}),
    case("basis-03", ["fee_basis"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2.5 times the fees "
         "invoiced under this Agreement.",
         "NEGOTIATE", {"kind": "fee_multiplier", "multiplier": 2.5},
         notes="'invoiced' is yet another basis word; engine only looks for 'fees'."),
    case("basis-04", ["fee_basis"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the fees due "
         "and payable under this Agreement.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0}),
    case("basis-05", ["fee_basis"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 3 times the total fees "
         "actually paid by Customer under this Agreement.",
         "NEGOTIATE", {"kind": "fee_multiplier", "multiplier": 3.0}),
]

# ---------------------------------------------------------------------------
# 3. Fee period: preceding 12 months vs lifetime agreement fees
# ---------------------------------------------------------------------------
CASES += [
    case("period-01", ["fee_period"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total fees "
         "paid in the twelve (12) months immediately preceding the event giving rise to the claim.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         notes="Trailing-12-months basis — much smaller dollar exposure than lifetime fees for a multi-year deal."),
    case("period-02", ["fee_period"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total fees "
         "paid over the life of this Agreement.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         notes="Lifetime-fees basis — same multiplier value but a much larger real dollar exposure than period-01; engine treats both identically since fee_period is not a modeled fact."),
    case("period-03", ["fee_period"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2 times the aggregate "
         "fees paid by Customer since the Effective Date.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0}),
    case("period-04", ["fee_period"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2 times the fees paid "
         "in the twelve (12) months prior to the first event giving rise to liability.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0}),
    case("period-05", ["fee_period"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 3 times the total fees "
         "paid or payable during the initial term of this Agreement.",
         "NEGOTIATE", {"kind": "fee_multiplier", "multiplier": 3.0}),
]

# ---------------------------------------------------------------------------
# 4. Fixed-dollar caps
# ---------------------------------------------------------------------------
CASES += [
    case("fixed-01", ["fixed_amount"],
         "12. Limitation of Liability. In no event shall Supplier's maximum aggregate liability "
         "exceed $500,000 for any claim arising under this Agreement.",
         "ESCALATE", {"kind": "fixed_amount", "fixed_amount": 500000.0}),
    case("fixed-02", ["fixed_amount"],
         "12. Limitation of Liability. Supplier's maximum aggregate liability shall not exceed "
         "$1,000,000.00 under this Agreement.",
         "ESCALATE", {"kind": "fixed_amount", "fixed_amount": 1000000.0}),
    case("fixed-03", ["fixed_amount"],
         "12. Limitation of Liability. In no event shall either party be liable for an amount in "
         "excess of $250,000.",
         "ESCALATE", {"kind": "fixed_amount", "fixed_amount": 250000.0}),
    case("fixed-04", ["fixed_amount", "currency_notation"],
         "12. Limitation of Liability. In no event shall aggregate liability exceed USD 500,000 "
         "under this Agreement.",
         "MUST_REDLINE", {"kind": "not_stated"},
         notes="No literal '$' sign — regex requires it, so this fails to extract at all. Documents a real extraction gap (still safe: MUST_REDLINE, not a false ACCEPT)."),
    case("fixed-05", ["fixed_amount"],
         "12. Limitation of Liability. Vendor's maximum liability under this Agreement shall not "
         "exceed $75,000.",
         "ESCALATE", {"kind": "fixed_amount", "fixed_amount": 75000.0},
         notes="Below every configured multiplier threshold in real dollar terms, but the engine cannot normalize a fixed amount, so it still escalates for manual comparison rather than guessing ACCEPT."),
    case("fixed-06", ["fixed_amount"],
         "12. Limitation of Liability. Liability shall not exceed $10,000,000 in the aggregate.",
         "ESCALATE", {"kind": "fixed_amount", "fixed_amount": 10000000.0}),
]

# ---------------------------------------------------------------------------
# 5. Greater-of $X or fees structures
# ---------------------------------------------------------------------------
CASES += [
    case("greater-01", ["greater_of"],
         "12. Limitation of Liability. Aggregate liability shall not exceed the greater of "
         "$1,000,000 or 2 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Not a simple cap — it's a floor-protected multiplier. Engine has no 'greater of' concept; ground truth is REQUIRES_REVIEW. Catastrophic failure mode would be silently accepting the smaller reading."),
    case("greater-02", ["greater_of"],
         "12. Limitation of Liability. In no event shall liability exceed the greater of (a) "
         "$500,000, or (b) 3 times the fees paid under this Agreement.",
         "REQUIRES_REVIEW", "SKIP"),
    case("greater-03", ["greater_of"],
         "12. Limitation of Liability. Supplier's aggregate liability shall be limited to the "
         "greater of one times annual fees or $250,000.",
         "REQUIRES_REVIEW", "SKIP"),
    case("greater-04", ["greater_of"],
         "12. Limitation of Liability. Liability shall not exceed whichever is greater: $2,000,000 "
         "or 1 times the fees paid in the preceding 12 months.",
         "REQUIRES_REVIEW", "SKIP"),
    case("greater-05", ["greater_of"],
         "12. Limitation of Liability. The cap on aggregate liability shall be the greater of 2x "
         "annual fees or $1,000,000, whichever amount is higher.",
         "REQUIRES_REVIEW", "SKIP"),
]

# ---------------------------------------------------------------------------
# 6. Lesser-of structures
# ---------------------------------------------------------------------------
CASES += [
    case("lesser-01", ["lesser_of"],
         "12. Limitation of Liability. Aggregate liability shall not exceed the lesser of "
         "$1,000,000 or 2 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="A misread here is especially dangerous: silently picking the larger of the two values would be a real false-safe failure for the counterparty's benefit."),
    case("lesser-02", ["lesser_of"],
         "12. Limitation of Liability. In no event shall liability exceed the lesser of (a) "
         "$500,000, or (b) 3 times the fees paid under this Agreement.",
         "REQUIRES_REVIEW", "SKIP"),
    case("lesser-03", ["lesser_of"],
         "12. Limitation of Liability. Supplier's aggregate liability shall be limited to the "
         "lesser of one times annual fees or $250,000.",
         "REQUIRES_REVIEW", "SKIP"),
    case("lesser-04", ["lesser_of"],
         "12. Limitation of Liability. Liability shall not exceed whichever is lesser: $2,000,000 "
         "or 1 times the fees paid in the preceding 12 months.",
         "REQUIRES_REVIEW", "SKIP"),
    case("lesser-05", ["lesser_of"],
         "12. Limitation of Liability. The cap on aggregate liability shall be the lesser of 2x "
         "annual fees or $1,000,000, whichever amount is lower.",
         "REQUIRES_REVIEW", "SKIP"),
]

# ---------------------------------------------------------------------------
# 7. Separate customer/vendor caps (two distinct named-role general caps)
# ---------------------------------------------------------------------------
CASES += [
    case("separate-01", ["separate_caps"],
         "12. Limitation of Liability. Customer's aggregate liability shall not exceed 1 times the "
         "fees paid. Vendor's aggregate liability shall not exceed 3 times the fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Two distinct general-cap values for two named roles — the engine's single general_cap concept cannot represent this; correct behavior is to abstain, not silently average or pick the first."),
    case("separate-02", ["separate_caps"],
         "12. Limitation of Liability. Client's maximum liability shall not exceed 2 times the "
         "annual fees paid. Provider's maximum liability shall not exceed 1 times the annual fees "
         "paid.",
         "REQUIRES_REVIEW", "SKIP"),
    case("separate-03", ["separate_caps"],
         "12. Limitation of Liability. Company's liability is capped at $1,000,000. Contractor's "
         "liability is capped at 2 times the fees paid.",
         "REQUIRES_REVIEW", "SKIP"),
    case("separate-04", ["separate_caps"],
         "12. Limitation of Liability. Licensee's aggregate liability shall not exceed 1 times "
         "fees paid, while Licensor's aggregate liability shall not exceed 5 times fees paid.",
         "REQUIRES_REVIEW", "SKIP"),
    case("separate-05", ["separate_caps"],
         "12. Limitation of Liability. Buyer's liability under this Agreement is limited to 1 "
         "times the purchase price. Seller's liability is limited to 4 times the purchase price.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Also uses a non-fee basis ('purchase price') the extractor's fee-keyword pattern wouldn't match at all — likely surfaces as MUST_REDLINE/not_stated in practice, itself a documented gap."),
]

# ---------------------------------------------------------------------------
# 8. Per-claim vs aggregate caps
# ---------------------------------------------------------------------------
CASES += [
    case("perclaim-01", ["per_claim_vs_aggregate"],
         "12. Limitation of Liability. In no event shall Supplier's liability for any single claim "
         "exceed 1 times the fees paid, and in no event shall Supplier's aggregate liability across "
         "all claims exceed 3 times the fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Two distinct numeric values addressing different scopes (per-claim vs aggregate) — not a conflict to resolve by picking one, but a structure the engine doesn't represent."),
    case("perclaim-02", ["per_claim_vs_aggregate"],
         "12. Limitation of Liability. Liability per individual claim shall not exceed $250,000; "
         "aggregate liability for all claims in a 12-month period shall not exceed $1,000,000.",
         "REQUIRES_REVIEW", "SKIP"),
    case("perclaim-03", ["per_claim_vs_aggregate"],
         "12. Limitation of Liability. No single claim shall result in liability exceeding 2 times "
         "the fees paid; total liability across all claims shall not exceed 4 times the fees paid.",
         "REQUIRES_REVIEW", "SKIP"),
    case("perclaim-04", ["per_claim_vs_aggregate"],
         "12. Limitation of Liability. Per-occurrence liability is capped at 1 times fees paid, "
         "and aggregate annual liability is capped at 2 times fees paid.",
         "REQUIRES_REVIEW", "SKIP"),
    case("perclaim-05", ["per_claim_vs_aggregate"],
         "12. Limitation of Liability. Each claim is subject to a cap of $100,000, subject to an "
         "aggregate cap across all claims of $500,000 in any twelve-month period.",
         "REQUIRES_REVIEW", "SKIP"),
]

# ---------------------------------------------------------------------------
# 9. Single super-caps (category-specific cap distinct from the general cap)
# ---------------------------------------------------------------------------
CASES += [
    case("supercap-01", ["super_cap"],
         "12. Limitation of Liability. Except as set forth below, in no event shall either party's "
         "aggregate liability exceed 1 times the total annual fees paid. Notwithstanding the "
         "foregoing, in the event of a data breach, liability shall not exceed 2 times the total "
         "annual fees paid.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"data_breach": "super_cap"}),
    case("supercap-02", ["super_cap"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except that for claims arising from confidentiality breaches, liability "
         "shall not exceed 3 times the total annual fees paid.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"confidentiality": "super_cap"}),
    case("supercap-03", ["super_cap"],
         "12. Limitation of Liability. Liability shall not exceed 2 times the total annual fees "
         "paid. Notwithstanding the foregoing, for indemnification obligations, liability shall not "
         "exceed 5 times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         {"indemnification": "super_cap"}),
    case("supercap-04", ["super_cap"],
         "12. Limitation of Liability. Aggregate liability is capped at 1 times fees paid, provided "
         "that liability for intellectual property infringement claims shall not exceed $2,000,000.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"ip_infringement": "super_cap"}),
    case("supercap-05", ["super_cap"],
         "12. Limitation of Liability. Liability shall not exceed 2.5 times the total annual fees "
         "paid, except that liability arising from a data breach shall not exceed 4 times the total "
         "annual fees paid.",
         "NEGOTIATE", {"kind": "fee_multiplier", "multiplier": 2.5},
         {"data_breach": "super_cap"}),
]

# ---------------------------------------------------------------------------
# 10. Multiple super-caps in one clause
# ---------------------------------------------------------------------------
CASES += [
    case("multisupercap-01", ["multiple_super_caps"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid. Notwithstanding the foregoing, liability arising from a data breach "
         "shall not exceed 2 times the total annual fees paid, and the foregoing limitation shall "
         "not apply to claims arising from intellectual property infringement.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"data_breach": "super_cap", "ip_infringement": "uncapped"}),
    case("multisupercap-02", ["multiple_super_caps"],
         "12. Limitation of Liability. Liability shall not exceed 2 times the total annual fees "
         "paid, except that liability for confidentiality breaches shall not exceed 3 times the "
         "total annual fees paid, and liability for indemnification obligations shall not exceed 5 "
         "times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         {"confidentiality": "super_cap", "indemnification": "super_cap"}),
    case("multisupercap-03", ["multiple_super_caps"],
         "12. Limitation of Liability. Aggregate liability is capped at 1 times fees paid. The "
         "foregoing limitation shall not apply to claims arising from fraud or gross negligence.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"fraud": "uncapped", "gross_negligence": "uncapped"}),
    case("multisupercap-04", ["multiple_super_caps"],
         "12. Limitation of Liability. Liability shall not exceed 1.5 times the total annual fees "
         "paid. Notwithstanding the foregoing, liability for a data breach shall not exceed "
         "$1,000,000, and liability for IP infringement shall not exceed 3 times the total annual "
         "fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 1.5},
         {"data_breach": "super_cap", "ip_infringement": "super_cap"},
         notes="Corrected after the remediation benchmark run: 1.5x is above the 1.0x preferred "
               "threshold under DEFAULT_POLICY, so ACCEPT_WITH_NOTE is the arithmetically correct "
               "label, not ACCEPT (original label was a labeling arithmetic error, not an engine gap)."),
    case("multisupercap-05", ["multiple_super_caps"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2 times the total "
         "annual fees paid. This limitation shall not apply to willful misconduct, and liability "
         "for confidentiality breaches shall not exceed 4 times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         {"willful_misconduct": "uncapped", "confidentiality": "super_cap"}),
]

# ---------------------------------------------------------------------------
# 11. Uncapped carve-outs — one per category
# ---------------------------------------------------------------------------
CASES += [
    case("uncapped-01", ["uncapped_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except for breaches of fraud.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"fraud": "uncapped"}, policy_overrides={"required_exceptions_json": ["fraud"]}),
    case("uncapped-02", ["uncapped_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except for breaches of gross negligence.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"gross_negligence": "uncapped"}, policy_overrides={"required_exceptions_json": ["gross_negligence"]}),
    case("uncapped-03", ["uncapped_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except for willful misconduct.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"willful_misconduct": "uncapped"}, policy_overrides={"required_exceptions_json": ["willful_misconduct"]}),
    case("uncapped-04", ["uncapped_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid; the foregoing limitation shall not apply to claims arising from "
         "intellectual property infringement.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"ip_infringement": "uncapped"}, policy_overrides={"required_exceptions_json": ["ip_infringement"]}),
    case("uncapped-05", ["uncapped_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except for breaches of confidentiality, which shall not be subject to "
         "the foregoing limitation.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"confidentiality": "uncapped"}, policy_overrides={"required_exceptions_json": ["confidentiality"]}),
    case("uncapped-06", ["uncapped_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, other than a party's indemnification obligations under Section 14.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"indemnification": "uncapped"}, policy_overrides={"required_exceptions_json": ["indemnification"]}),
    case("uncapped-07", ["uncapped_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except for breaches arising from a data breach, which shall not be "
         "subject to the foregoing limitation.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"data_breach": "uncapped"}, policy_overrides={"required_exceptions_json": ["data_breach"]}),
]

# ---------------------------------------------------------------------------
# 12. Partial carve-outs (narrower than they first appear)
# ---------------------------------------------------------------------------
CASES += [
    case("partial-01", ["partial_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except for claims arising from a party's gross negligence in "
         "performing its data security obligations, which shall not be subject to the foregoing "
         "limitation.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"gross_negligence": "uncapped"},
         policy_overrides={"required_exceptions_json": ["gross_negligence", "data_breach"]},
         notes="The carve-out is scoped narrowly ('gross negligence IN data security'), not a blanket gross-negligence exception AND not a blanket data-breach exception. A correct engine should not credit both categories equally from one narrow clause — worth checking what data_breach gets classified as here."),
    case("partial-02", ["partial_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2 times the total "
         "annual fees paid, except that this limitation shall not apply to fraud committed in "
         "connection with a data breach.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         {"fraud": "uncapped"},
         policy_overrides={"required_exceptions_json": ["fraud", "data_breach"]},
         notes="Carve-out is for fraud-in-connection-with-a-breach specifically, not all data breaches generally."),
    case("partial-03", ["partial_carveout"],
         "12. Limitation of Liability. Liability shall not exceed 1 times the total annual fees "
         "paid, except for breaches of confidentiality involving trade secrets.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"confidentiality": "uncapped"},
         policy_overrides={"required_exceptions_json": ["confidentiality"]},
         notes="Carve-out is scoped to trade-secret breaches, narrower than 'confidentiality' generally — engine has no way to represent the qualifier."),
    case("partial-04", ["partial_carveout"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, except for indemnification obligations arising solely under Section "
         "14(a) (IP Infringement Indemnity).",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"indemnification": "uncapped"},
         policy_overrides={"required_exceptions_json": ["indemnification", "ip_infringement"]},
         notes="Carve-out is for one specific indemnity sub-clause, not indemnification obligations generally."),
    case("partial-05", ["partial_carveout"],
         "12. Limitation of Liability. Liability shall not exceed 1 times the total annual fees "
         "paid, except for willful misconduct causing bodily injury.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         {"willful_misconduct": "uncapped"},
         policy_overrides={"required_exceptions_json": ["willful_misconduct"]},
         notes="Carve-out qualifier ('causing bodily injury') narrows scope but the category itself is still genuinely carved out."),
]

# ---------------------------------------------------------------------------
# 13. Consequential-damages waivers
# ---------------------------------------------------------------------------
CASES += [
    case("conseq-01", ["consequential_damages"],
         "12. Limitation of Liability. In no event shall either party be liable for any "
         "consequential, indirect, special, or punitive damages arising out of this Agreement, "
         "even if advised of the possibility of such damages. Aggregate liability shall not exceed "
         "1 times the total annual fees paid.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         expected_consequential_excluded=True),
    case("conseq-02", ["consequential_damages"],
         "12. Limitation of Liability. Neither party shall be liable for indirect or consequential "
         "damages. Aggregate liability shall not exceed 2 times the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         expected_consequential_excluded=True),
    case("conseq-03", ["consequential_damages"],
         "12. Limitation of Liability. In no event shall Supplier be liable for special or "
         "incidental damages. Aggregate liability shall not exceed 1 times the total annual fees "
         "paid.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         expected_consequential_excluded=True),
    case("conseq-04", ["consequential_damages", "not_addressed"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         expected_consequential_excluded=None,
         notes="No consequential-damages language at all — should read as 'not addressed', not as an unresolved/ambiguous fact."),
    case("conseq-05", ["consequential_damages"],
         "12. Limitation of Liability. Punitive damages are excluded in all cases. Aggregate "
         "liability shall not exceed 3 times the total annual fees paid.",
         "NEGOTIATE", {"kind": "fee_multiplier", "multiplier": 3.0},
         expected_consequential_excluded=True),
]

# ---------------------------------------------------------------------------
# 14. Carve-outs from the consequential-damages waiver
# ---------------------------------------------------------------------------
CASES += [
    case("conseq-carveout-01", ["consequential_carveout"],
         "12. Limitation of Liability. In no event shall either party be liable for consequential "
         "damages, except that this exclusion shall not apply to a breach of confidentiality "
         "obligations. Aggregate liability shall not exceed 1 times the total annual fees paid.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         expected_consequential_excluded=True,
         notes="Consequential-damages exclusion carved back out for confidentiality — engine records carveouts list but this fact isn't wired into the decision at all yet."),
    case("conseq-carveout-02", ["consequential_carveout"],
         "12. Limitation of Liability. Neither party shall be liable for indirect damages, other "
         "than damages arising from a data breach. Aggregate liability shall not exceed 2 times "
         "the total annual fees paid.",
         "ACCEPT_WITH_NOTE", {"kind": "fee_multiplier", "multiplier": 2.0},
         expected_consequential_excluded=True),
    case("conseq-carveout-03", ["consequential_carveout"],
         "12. Limitation of Liability. Consequential damages are excluded, excluding breaches of "
         "fraud or willful misconduct. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         expected_consequential_excluded=True),
]

# ---------------------------------------------------------------------------
# 15. Cross-references to other sections/schedules
# ---------------------------------------------------------------------------
CASES += [
    case("xref-01", ["cross_reference"],
         "12. Limitation of Liability. The limitation of liability applicable to this Agreement "
         "shall be as set forth in Schedule C (Liability Terms).",
         "REQUIRES_REVIEW", {"kind": "not_stated"},
         notes="No number in the clause itself — the real cap lives in a schedule the engine never reads. MUST_REDLINE ('insert cap language') is a misleading instruction here; ideal is REQUIRES_REVIEW ('verify Schedule C'). Still non-ACCEPT either way."),
    case("xref-02", ["cross_reference"],
         "12. Limitation of Liability. Liability caps for each Order Form are set forth in the "
         "applicable Order Form and incorporated herein by reference.",
         "REQUIRES_REVIEW", {"kind": "not_stated"}),
    case("xref-03", ["cross_reference"],
         "12. Limitation of Liability. See Exhibit B for the applicable liability caps and "
         "carve-outs, which are incorporated into this Section by reference.",
         "REQUIRES_REVIEW", {"kind": "not_stated"}),
    case("xref-04", ["cross_reference"],
         "12. Limitation of Liability. The parties' respective liability caps are set forth in "
         "Section 3 of the Master Services Agreement referenced in Recital A.",
         "REQUIRES_REVIEW", {"kind": "not_stated"}),
    case("xref-05", ["cross_reference"],
         "12. Limitation of Liability. Notwithstanding anything to the contrary, liability limits "
         "for Professional Services are governed exclusively by Schedule D.",
         "REQUIRES_REVIEW", {"kind": "not_stated"}),
]

# ---------------------------------------------------------------------------
# 16. Asymmetric caps (directional favorability, distinct from "separate caps"
#     structurally — here one side is uncapped while the other has a stated
#     multiplier)
# ---------------------------------------------------------------------------
CASES += [
    case("asym-01", ["asymmetric"],
         "12. Limitation of Liability. Customer's aggregate liability shall not exceed 1 times the "
         "fees paid under this Agreement. This limitation shall not apply to Customer's payment "
         "obligations, which remain uncapped.",
         "REQUIRES_REVIEW", "SKIP",
         notes="A payment-obligations carve-out isn't one of the 7 tracked categories, and 'uncapped' language here doesn't correspond to a category keyword the engine looks for — likely silently ignored, worth checking."),
    case("asym-02", ["asymmetric"],
         "12. Limitation of Liability. Vendor's liability is capped at 1 times fees paid. "
         "Customer's liability under this Agreement is not subject to any cap.",
         "REQUIRES_REVIEW", "SKIP",
         notes="One named party has a numeric cap, the other is explicitly uncapped — a real asymmetric structure the single general_cap model can't hold."),
    case("asym-03", ["asymmetric"],
         "12. Limitation of Liability. Supplier's aggregate liability shall not exceed 2 times the "
         "fees paid. Customer's aggregate liability shall not exceed 5 times the fees paid.",
         "REQUIRES_REVIEW", "SKIP"),
    case("asym-04", ["asymmetric"],
         "12. Limitation of Liability. Licensor's liability under this Agreement is limited to $1 "
         "and no greater amount under any circumstances. Licensee's liability is limited to 2 times "
         "the fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Nominal-damages ($1) clause paired with a real multiplier cap for the other party — extreme asymmetry."),
    case("asym-05", ["asymmetric"],
         "12. Limitation of Liability. Contractor's aggregate liability shall not exceed 1 times "
         "fees paid; Client's aggregate liability shall not exceed 1 times fees paid, except that "
         "Client's payment obligations shall remain uncapped in all events.",
         "REQUIRES_REVIEW", "SKIP"),
]

# ---------------------------------------------------------------------------
# 17. Ambiguous drafting (no extractable numeric position, genuinely vague)
# ---------------------------------------------------------------------------
CASES += [
    case("vague-01", ["ambiguous_drafting"],
         "12. Limitation of Liability. Each party's liability shall be limited to a reasonable "
         "amount under the circumstances, taking into account industry custom.",
         "MUST_REDLINE", {"kind": "not_stated"}),
    case("vague-02", ["ambiguous_drafting"],
         "12. Limitation of Liability. The parties agree that liability shall be limited as is "
         "customary for agreements of this type and value.",
         "MUST_REDLINE", {"kind": "not_stated"}),
    case("vague-03", ["ambiguous_drafting"],
         "12. Limitation of Liability. Liability shall be capped at an amount to be mutually "
         "agreed by the parties in good faith following any claim.",
         "MUST_REDLINE", {"kind": "not_stated"}),
    case("vague-04", ["ambiguous_drafting"],
         "12. Limitation of Liability. Each party's liability shall be proportionate to its "
         "responsibility for the loss, subject to a cap to be determined by the parties' insurers.",
         "MUST_REDLINE", {"kind": "not_stated"}),
    case("vague-05", ["ambiguous_drafting"],
         "12. Limitation of Liability. Liability shall be limited to the extent permitted by "
         "applicable law, and the parties shall negotiate a specific cap prior to the Effective "
         "Date if required by either party's insurer.",
         "MUST_REDLINE", {"kind": "not_stated"}),
    case("vague-06", ["ambiguous_drafting"],
         "12. Limitation of Liability. The parties intend for liability to be limited but have not "
         "yet agreed on specific terms, which will be documented in a future amendment.",
         "MUST_REDLINE", {"kind": "not_stated"}),
]

# ---------------------------------------------------------------------------
# 18. Malformed clauses (OCR/extraction artifacts)
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-01", ["malformed"],
         "12. Limitat on of Liabi ity. In no ev nt shall aggreg te liabil ty excee 2 tmes the fes "
         "pd in the twelve months preceding the cl aim.",
         "NOT_APPLICABLE", None,
         notes="Simulated OCR corruption severe enough to break even the 'limitation of liability' anchor phrase itself — the engine cannot find any LoL clause at all, so NOT_APPLICABLE is the honest, correct outcome (not MUST_REDLINE, which would incorrectly imply a clause was located). Originally mislabeled MUST_REDLINE in this corpus; corrected after the first benchmark run."),
    case("malformed-02", ["malformed"],
         "12.  Limitation   of   Liability.    In no event  shall  liability   exceed  2x  the  "
         "fees    paid     annually     under      this      Agreement     structure.",
         "ACCEPT_WITH_NOTE", {"kind": "not_stated"},
         notes="Excess whitespace, and '2x' shorthand instead of '2 times'/'two times' — regex requires the literal word 'times' or 'x' with a following space, so this specific shorthand form is a known miss; documents the gap rather than asserting a false pass."),
    case("malformed-03", ["malformed"],
         "12. Limitation of Liability.\x00\x00 In no event shall aggregate liability exceed 1 "
         "times the total annual fees paid.\x01",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         notes="Stray control characters around otherwise clean text — should not block extraction (control chars aren't inside the matched span)."),
    case("malformed-04", ["malformed"],
         "12. Limitation of Liabilty. Aggreagte liability shal not excede 1 times the total anual "
         "fees paid.",
         "NOT_APPLICABLE", None,
         notes="The typo in 'Liabilty' (missing the second 'i') breaks the anchor phrase itself, so no clause is located at all — NOT_APPLICABLE is correct. Originally mislabeled MUST_REDLINE in this corpus; corrected after the first benchmark run. Note the multiplier ('1 times the total ... fees paid') would have extracted cleanly despite its own typos ('anual') had the anchor matched — the anchor is the single point of failure here."),
    case("malformed-05", ["malformed"],
         "12. LIMITATION OF LIABILITY -- IN NO EVENT SHALL AGGREGATE LIABILITY EXCEED 1 TIMES THE "
         "TOTAL ANNUAL FEES PAID.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         notes="All-caps clause (common in older paper contracts) — regexes are case-insensitive so this should extract cleanly."),
    case("malformed-06", ["malformed"],
         "12. Limitation of Liability. In no event shall aggregate liability exceed [***] times "
         "the total annual fees paid.",
         "MUST_REDLINE", {"kind": "not_stated"},
         notes="Redacted number (common in filed exhibits with confidential terms redacted) — must not be misparsed as a real value."),
]

# ---------------------------------------------------------------------------
# 19. No Limitation of Liability clause at all
# ---------------------------------------------------------------------------
CASES += [
    case("noclause-01", ["no_clause"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of Delaware, "
         "without regard to its conflict of laws principles.",
         "NOT_APPLICABLE", None),
    case("noclause-02", ["no_clause"],
         "10. Term and Termination. This Agreement shall commence on the Effective Date and "
         "continue for an initial term of one year, automatically renewing for successive one-year "
         "terms unless either party provides notice of non-renewal.",
         "NOT_APPLICABLE", None),
    case("noclause-03", ["no_clause"],
         "11. Confidentiality. Each party shall protect the other party's Confidential Information "
         "using the same degree of care it uses for its own confidential information, but no less "
         "than reasonable care.",
         "NOT_APPLICABLE", None),
    case("noclause-04", ["no_clause"],
         "8. Indemnification. Each party shall indemnify, defend, and hold harmless the other party "
         "from third-party claims arising out of its breach of this Agreement.",
         "NOT_APPLICABLE", None),
    case("noclause-05", ["no_clause"],
         "13. Assignment. Neither party may assign this Agreement without the prior written consent "
         "of the other party, except in connection with a merger, acquisition, or sale of "
         "substantially all assets.",
         "NOT_APPLICABLE", None),
]

# ---------------------------------------------------------------------------
# 20. Multiple Limitation of Liability sections in one document
# ---------------------------------------------------------------------------
CASES += [
    case("multisection-01", ["multiple_sections"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability exceed "
         "1 times the total annual fees paid. ... 28. Exhibit A Terms. This Exhibit modifies the "
         "Agreement as follows. 28.1 Limitation of Liability. Notwithstanding Section 12, "
         "liability under this Exhibit shall not exceed 5 times the fees paid under this Exhibit.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Two LoL sections close enough together to fall in the same extraction window — should surface as a general-cap conflict (1x vs 5x) rather than silently keeping the first."),
    case("multisection-02", ["multiple_sections", "window_boundary"],
         "12. Limitation of Liability. In no event shall either party's aggregate liability exceed "
         "1 times the total annual fees paid." + (" Lorem ipsum dolor sit amet, consectetur "
         "adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. " * 60)
         + " Exhibit F. Limitation of Liability (Professional Services). Liability under this "
         "Exhibit shall not exceed 5 times the fees paid for Professional Services.",
         "REQUIRES_REVIEW", "SKIP",
         notes="DELIBERATE STRESS TEST: the second LoL section is padded well past the engine's 3000-character extraction window, so it is invisible to extraction entirely. The engine will silently report only the first section's 1x cap as ACCEPT, never seeing the second section's 5x. This is a genuine false-ACCEPT risk from the fixed-window design, not just a labeling gap — flag prominently if the run confirms it."),
    case("multisection-03", ["multiple_sections"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2 times the total "
         "annual fees paid. Section 12 shall apply to the Master Agreement generally. Schedule 2, "
         "Section 4: Limitation of Liability (Data Processing Addendum). Liability for data "
         "protection breaches under this Schedule shall not exceed 4 times the annual fees paid "
         "under the Order Form referencing this Schedule.",
         "REQUIRES_REVIEW", "SKIP"),
    case("multisection-04", ["multiple_sections"],
         "12. Limitation of Liability. Liability is capped at 1 times fees paid. 12A. Limitation "
         "of Liability for Beta Features. Notwithstanding Section 12, liability for Beta Features "
         "is capped at 0.5 times fees paid.",
         "REQUIRES_REVIEW", "SKIP"),
    case("multisection-05", ["multiple_sections"],
         "12. Limitation of Liability. General liability cap: 1 times fees paid. Appendix 3 "
         "Limitation of Liability Override: for Enterprise Tier customers, liability cap: 3 times "
         "fees paid.",
         "REQUIRES_REVIEW", "SKIP"),
]

# ---------------------------------------------------------------------------
# 21. Amendments overriding the original cap
# ---------------------------------------------------------------------------
CASES += [
    case("amendment-01", ["amendment"],
         "12. Limitation of Liability. In no event shall aggregate liability exceed 1 times the "
         "total annual fees paid. ... Amendment No. 1 to Agreement. Section 12 (Limitation of "
         "Liability) of the Agreement is hereby amended and restated in its entirety to increase "
         "the liability cap to 5 times the total annual fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="The amendment supersedes the original 1x cap with 5x, but nothing in the engine understands amendment precedence or a restated section overriding an earlier one — this should surface as a general-cap conflict, not silently return the stale 1x."),
    case("amendment-02", ["amendment", "window_boundary"],
         "12. Limitation of Liability. In no event shall aggregate liability exceed 1 times the "
         "total annual fees paid." + (" This Agreement contains various other terms and conditions "
         "not material to this clause, repeated here only to occupy space in the extraction "
         "window for testing purposes. " * 55)
         + " First Amendment to Master Services Agreement, dated as of the date below: The parties "
         "agree that Section 12 (Limitation of Liability) is amended and restated to provide that "
         "aggregate liability shall not exceed 6 times the total annual fees paid, superseding the "
         "original Section 12 in its entirety.",
         "REQUIRES_REVIEW", "SKIP",
         notes="DELIBERATE STRESS TEST, same failure mode as multisection-02: the amendment's superseding 6x cap sits beyond the 3000-character window, so extraction never sees it and the engine will confidently ACCEPT on the stale, superseded 1x figure. This is the corpus's headline false-ACCEPT risk — the whole point of testing amendment scenarios."),
    case("amendment-03", ["amendment"],
         "12. Limitation of Liability. Liability is capped at 2 times fees paid. Amendment No. 2: "
         "the parties agree to decrease the liability cap in Section 12 to 1 times fees paid, "
         "effective as of the date of this Amendment.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Amendment lowers the cap (favorable direction) but the conflict-detection mechanism doesn't know that — still correctly worth flagging for review rather than guessing which value governs."),
    case("amendment-04", ["amendment"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid, as amended by Amendment No. 3, which increased the original 0.5x cap "
         "to the current 1x cap reflected in this restated Section 12.",
         "ACCEPT", {"kind": "fee_multiplier", "multiplier": 1.0},
         notes="Not a stress test — the clause has already been fully restated with only the current 1x value present (the superseded 0.5x is only mentioned narratively, not as a second operative cap), so a single clean extraction is the correct, achievable outcome here."),
    case("amendment-05", ["amendment"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total "
         "annual fees paid. Amendment No. 4 (Side Letter): Notwithstanding Section 12, for the "
         "Q3 renewal term only, the liability cap shall be increased to 3 times the total annual "
         "fees paid.",
         "REQUIRES_REVIEW", "SKIP",
         notes="Conditional/temporary amendment (only for one renewal term) — even a system that handled amendment precedence would need to know which term is currently active; correct default is to flag for review."),
]
