"""
Labeled adversarial corpus for the Insurance policy engine benchmark
(see benchmarks/run_insurance_benchmark.py). Adapter #9 — third adapter
added after the original six.

Labels here were written from the policy semantics and the drafting
pattern alone, reasoning directly from insurance_policy_engine.py's
evaluate_insurance_policy logic, never by running the implementation and
copying whatever it happened to output.

DEFAULT_POLICY intentionally requires NOTHING by default (every
require_* field is False, every numeric minimum is None) — the opposite
convention from earlier adapters' corpora, adopted after benchmarking
ip_ownership_corpus.py revealed that an always-on, MUST_REDLINE-severity
default requirement silently dominated dozens of single-dimension test
cases that never addressed it. Each case here explicitly turns on only
the dimension(s) it means to test via policy_overrides, so a test's
text only ever needs to address what it says it's testing.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "buy_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: $1M/$2M CGL, $1M Professional Liability (claims-made with "
                      "3-year tail), $2M Cyber Liability, statutory Workers' Compensation, $1M "
                      "Employer's Liability, additional insured, waiver of subrogation, primary and "
                      "non-contributory, certificate of insurance, A.M. Best A- VII minimum rating, "
                      "30 days' cancellation notice, maintained throughout the term, subcontractor "
                      "coverage, evidence before commencement.",
    "require_cgl": False, "cgl_minimum_per_occurrence": None, "cgl_minimum_aggregate": None,
    "require_professional_liability": False, "professional_liability_minimum_limit": None,
    "require_cyber_liability": False, "cyber_liability_minimum_limit": None,
    "require_workers_comp": False,
    "require_employers_liability": False, "employers_liability_minimum_limit": None,
    "require_auto_liability": False, "auto_liability_minimum_limit": None,
    "require_counterparty_obligated": False,
    "require_additional_insured": False,
    "require_waiver_of_subrogation": False,
    "require_primary_non_contributory": False,
    "require_certificate_of_insurance": False,
    "require_minimum_insurer_rating": False,
    "require_notice_of_cancellation": False, "minimum_cancellation_notice_days": None,
    "require_policy_maintenance_through_term": False,
    "require_claims_made_tail": False,
    "require_subcontractor_coverage": False,
    "require_evidence_before_commencement": False,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Fully-compliant baseline: every coverage type + every administrative
# requirement satisfied.
# ---------------------------------------------------------------------------
FULLY_COMPLIANT_TEXT = (
    "12. Insurance. Vendor shall maintain, at its own expense, the following insurance coverages "
    "throughout the Term of this Agreement: (a) Commercial General Liability insurance with limits "
    "of not less than $1,000,000 per occurrence and $2,000,000 in the aggregate; (b) Professional "
    "Liability (Errors & Omissions) insurance with limits of not less than $1,000,000 per claim, "
    "maintained on a claims-made basis, with a minimum three-year extended reporting period "
    "following termination; (c) Cyber Liability insurance with limits of not less than $2,000,000 "
    "per claim; (d) Workers' Compensation insurance as required by applicable law; and (e) "
    "Employer's Liability insurance with limits of not less than $1,000,000 each accident. "
    "Customer shall be named as an additional insured on all policies except Workers' Compensation "
    "and Employer's Liability, and all policies shall include a waiver of subrogation in favor of "
    "Customer and shall be primary and non-contributory. Vendor shall provide Customer with a "
    "certificate of insurance evidencing such coverage prior to commencement of the Services. All "
    "insurers shall carry an A.M. Best rating of at least A- VII. Vendor shall provide Customer "
    "with 30 days' prior written notice of cancellation or material change to any policy. Vendor "
    "shall require its subcontractors to maintain insurance coverage equivalent to that required "
    "of Vendor hereunder."
)
FULLY_COMPLIANT_POLICY = {
    "require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0, "cgl_minimum_aggregate": 2_000_000.0,
    "require_professional_liability": True, "professional_liability_minimum_limit": 1_000_000.0,
    "require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0,
    "require_workers_comp": True,
    "require_employers_liability": True, "employers_liability_minimum_limit": 1_000_000.0,
    "require_counterparty_obligated": True,
    "require_additional_insured": True, "require_waiver_of_subrogation": True,
    "require_primary_non_contributory": True, "require_certificate_of_insurance": True,
    "require_minimum_insurer_rating": True,
    "require_notice_of_cancellation": True, "minimum_cancellation_notice_days": 30.0,
    "require_policy_maintenance_through_term": True, "require_claims_made_tail": True,
    "require_subcontractor_coverage": True, "require_evidence_before_commencement": True,
}

CASES += [
    case("clean-01", ["clean_all"], FULLY_COMPLIANT_TEXT, "ACCEPT",
         policy_overrides=dict(FULLY_COMPLIANT_POLICY),
         notes="Every configured dimension satisfied at the preferred tier."),
]

# ---------------------------------------------------------------------------
# Clean single-coverage-type requirements: CGL, cyber-only, E&O.
# ---------------------------------------------------------------------------
CASES += [
    case("cgl-01", ["cgl", "clean"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence and $2,000,000 in the aggregate.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                                      "cgl_minimum_aggregate": 2_000_000.0},
         notes="CGL limits at exactly the required minimums."),
    case("cgl-02", ["cgl", "below_minimum"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $500,000 per occurrence.",
         "NEGOTIATE", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="$500K is below the required $1M minimum."),
    case("cgl-03", ["cgl", "above_minimum"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $5,000,000 per occurrence.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="$5M exceeds the required $1M minimum."),
    case("cgl-04", ["cgl", "missing"],
         "9. Insurance. Vendor shall maintain Professional Liability insurance with limits of not "
         "less than $1,000,000 per claim.",
         "MUST_REDLINE", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="CGL is required but the clause only addresses Professional Liability."),
    case("cyber-01", ["cyber", "clean"],
         "9. Insurance. Vendor shall maintain Cyber Liability insurance with limits of not less "
         "than $2,000,000 per claim.",
         "ACCEPT", policy_overrides={"require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0},
         notes="Cyber-only requirement satisfied."),
    case("cyber-02", ["cyber", "below_minimum"],
         "9. Insurance. Vendor shall maintain Cyber Liability insurance with limits of not less "
         "than $500,000 per claim.",
         "NEGOTIATE", policy_overrides={"require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0},
         notes="$500K is below the required $2M minimum."),
    case("cyber-03", ["cyber", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "MUST_REDLINE", policy_overrides={"require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0},
         notes="Cyber Liability is required but the clause only addresses CGL."),
    case("eo-01", ["professional_liability", "clean"],
         "9. Insurance. Vendor shall maintain Professional Liability (Errors & Omissions) "
         "insurance with limits of not less than $1,000,000 per claim.",
         "ACCEPT", policy_overrides={"require_professional_liability": True, "professional_liability_minimum_limit": 1_000_000.0},
         notes="E&O-only requirement satisfied."),
    case("eo-02", ["professional_liability", "below_minimum"],
         "9. Insurance. Vendor shall maintain Errors and Omissions insurance with limits of not "
         "less than $250,000 per claim.",
         "NEGOTIATE", policy_overrides={"require_professional_liability": True, "professional_liability_minimum_limit": 1_000_000.0},
         notes="$250K is below the required $1M minimum."),
]

# ---------------------------------------------------------------------------
# Multiple policy types in one clause.
# ---------------------------------------------------------------------------
CASES += [
    case("multi-01", ["multi_type", "clean"],
         "9. Insurance. Vendor shall maintain the following coverages: (a) Commercial General "
         "Liability with limits of not less than $1,000,000 per occurrence; (b) Cyber Liability "
         "with limits of not less than $2,000,000 per claim; (c) Professional Liability with "
         "limits of not less than $1,000,000 per claim.",
         "ACCEPT",
         policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                            "require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0,
                            "require_professional_liability": True, "professional_liability_minimum_limit": 1_000_000.0},
         notes="Three coverage types listed in one clause, each with its own correctly-scoped "
               "limit — no cross-contamination between them."),
    case("multi-02", ["multi_type", "one_below_minimum"],
         "9. Insurance. Vendor shall maintain the following coverages: (a) Commercial General "
         "Liability with limits of not less than $1,000,000 per occurrence; (b) Cyber Liability "
         "with limits of not less than $250,000 per claim.",
         "NEGOTIATE",
         policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                            "require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0},
         notes="CGL satisfied; Cyber Liability's $250K is below the $2M minimum — the two "
               "coverage types' limits must not be confused with each other."),
    case("multi-03", ["multi_type", "five_types"],
         "9. Insurance. Vendor shall maintain, throughout the Term: (a) Commercial General "
         "Liability, $1,000,000 per occurrence / $2,000,000 aggregate; (b) Professional Liability, "
         "$1,000,000 per claim; (c) Cyber Liability, $2,000,000 per claim; (d) Workers' "
         "Compensation as required by law; (e) Employer's Liability, $1,000,000 each accident.",
         "ACCEPT",
         policy_overrides={**FULLY_COMPLIANT_POLICY, "require_counterparty_obligated": False,
                            "require_additional_insured": False, "require_waiver_of_subrogation": False,
                            "require_primary_non_contributory": False, "require_certificate_of_insurance": False,
                            "require_minimum_insurer_rating": False, "require_notice_of_cancellation": False,
                            "minimum_cancellation_notice_days": None, "require_claims_made_tail": False,
                            "require_subcontractor_coverage": False, "require_evidence_before_commencement": False},
         notes="All five coverage types itemized in one list, each independently correct."),
]

# ---------------------------------------------------------------------------
# Per-occurrence + aggregate limits; conflicting dollar limits.
# ---------------------------------------------------------------------------
CASES += [
    case("limits-01", ["limits", "per_occurrence_and_aggregate"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence and $2,000,000 in the aggregate.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                                      "cgl_minimum_aggregate": 2_000_000.0},
         notes="Both per-occurrence and aggregate limits independently extracted and satisfied."),
    case("limits-02", ["limits", "aggregate_below_minimum"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence and $1,500,000 in the aggregate.",
         "NEGOTIATE", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                                         "cgl_minimum_aggregate": 2_000_000.0},
         notes="Per-occurrence satisfied but aggregate ($1.5M) is below the $2M minimum."),
    case("limits-03", ["limits", "conflicting_per_occurrence"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence. Notwithstanding the foregoing, Vendor shall "
         "maintain Commercial General Liability insurance with limits of not less than "
         "$2,000,000 per occurrence.",
         "REQUIRES_REVIEW", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Two different per-occurrence CGL limits stated — genuine conflict, must abstain."),
    case("limits-04", ["limits", "conflicting_aggregate"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with an "
         "aggregate limit of not less than $2,000,000. Notwithstanding the foregoing, the "
         "aggregate limit for such Commercial General Liability insurance shall be not less than "
         "$3,000,000.",
         "REQUIRES_REVIEW", policy_overrides={"require_cgl": True, "cgl_minimum_aggregate": 2_000_000.0},
         notes="Two different aggregate CGL limits stated — genuine conflict."),
    case("limits-05", ["limits", "missing_aggregate"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "NEGOTIATE", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                                         "cgl_minimum_aggregate": 2_000_000.0},
         notes="No aggregate limit stated at all, but policy requires one."),
]

# ---------------------------------------------------------------------------
# Additional insured; waiver of subrogation; primary/non-contributory;
# certificates; insurer rating; cancellation notice; subcontractor
# coverage; claims-made tail; evidence timing; policy maintenance.
# ---------------------------------------------------------------------------
CASES += [
    case("cond-01", ["additional_insured", "present"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance. Customer "
         "shall be named as an additional insured on such policy.",
         "ACCEPT", policy_overrides={"require_additional_insured": True},
         notes="Additional insured status stated."),
    case("cond-02", ["additional_insured", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "NEGOTIATE", policy_overrides={"require_additional_insured": True},
         notes="No additional insured language present."),
    case("cond-03", ["waiver_of_subrogation", "present"],
         "9. Insurance. Vendor's insurance policies shall include a waiver of subrogation in "
         "favor of Customer.",
         "ACCEPT", policy_overrides={"require_waiver_of_subrogation": True},
         notes="Waiver of subrogation stated."),
    case("cond-04", ["waiver_of_subrogation", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_waiver_of_subrogation": True},
         notes="No waiver of subrogation language present."),
    case("cond-05", ["primary_non_contributory", "present"],
         "9. Insurance. Vendor's Commercial General Liability insurance shall be primary and "
         "non-contributory with respect to any insurance maintained by Customer.",
         "ACCEPT", policy_overrides={"require_primary_non_contributory": True},
         notes="Primary and non-contributory language stated."),
    case("cond-06", ["primary_non_contributory", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_primary_non_contributory": True},
         notes="No primary/non-contributory language present."),
    case("cond-07", ["certificate", "present"],
         "9. Insurance. Vendor shall provide Customer with a certificate of insurance evidencing "
         "the coverage required under this Section.",
         "ACCEPT", policy_overrides={"require_certificate_of_insurance": True},
         notes="Certificate of insurance requirement stated."),
    case("cond-08", ["certificate", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_certificate_of_insurance": True},
         notes="No certificate-of-insurance language present."),
    case("cond-09", ["insurer_rating", "am_best"],
         "9. Insurance. All insurers providing coverage hereunder shall carry an A.M. Best "
         "rating of at least A- VII.",
         "ACCEPT", policy_overrides={"require_minimum_insurer_rating": True},
         notes="A.M. Best rating requirement stated."),
    case("cond-10", ["insurer_rating", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_minimum_insurer_rating": True},
         notes="No insurer-rating language present."),
    case("cond-11", ["cancellation_notice", "30_days"],
         "9. Insurance. Vendor shall provide Customer with 30 days' prior written notice of "
         "cancellation of any required policy.",
         "ACCEPT", policy_overrides={"require_notice_of_cancellation": True, "minimum_cancellation_notice_days": 30.0},
         notes="30-day cancellation notice matches the required minimum exactly."),
    case("cond-12", ["cancellation_notice", "below_minimum"],
         "9. Insurance. Vendor shall provide Customer with 10 days' prior written notice of "
         "cancellation of any required policy.",
         "NEGOTIATE", policy_overrides={"require_notice_of_cancellation": True, "minimum_cancellation_notice_days": 30.0},
         notes="10-day notice is below the required 30-day minimum."),
    case("cond-13", ["cancellation_notice", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_notice_of_cancellation": True, "minimum_cancellation_notice_days": 30.0},
         notes="No cancellation-notice language present."),
    case("cond-14", ["subcontractor", "present"],
         "9. Insurance. Vendor shall require its subcontractors to maintain insurance coverage "
         "equivalent to that required of Vendor hereunder.",
         "ACCEPT", policy_overrides={"require_subcontractor_coverage": True},
         notes="Subcontractor insurance obligation stated."),
    case("cond-15", ["subcontractor", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_subcontractor_coverage": True},
         notes="No subcontractor-coverage language present."),
    case("cond-16", ["claims_made_tail", "present"],
         "9. Insurance. Vendor's Professional Liability insurance shall be maintained on a "
         "claims-made basis, with a minimum three-year extended reporting period following "
         "termination of this Agreement.",
         "ACCEPT", policy_overrides={"require_claims_made_tail": True},
         notes="Extended reporting period (tail) commitment stated."),
    case("cond-17", ["claims_made_tail", "missing"],
         "9. Insurance. Vendor shall maintain Professional Liability insurance on a claims-made "
         "basis.",
         "NEGOTIATE", policy_overrides={"require_claims_made_tail": True},
         notes="Claims-made basis stated but no tail/extended-reporting-period commitment."),
    case("cond-18", ["evidence_timing", "before_commencement"],
         "9. Insurance. Vendor shall provide evidence of such insurance prior to commencement of "
         "the Services.",
         "ACCEPT", policy_overrides={"require_evidence_before_commencement": True},
         notes="Evidence-before-commencement timing stated."),
    case("cond-19", ["evidence_timing", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_evidence_before_commencement": True},
         notes="No evidence-of-coverage timing language present."),
    case("cond-20", ["policy_maintenance", "present"],
         "9. Insurance. Vendor shall maintain the required insurance coverage throughout the "
         "Term of this Agreement.",
         "ACCEPT", policy_overrides={"require_policy_maintenance_through_term": True},
         notes="Maintenance-through-term commitment stated."),
    case("cond-21", ["policy_maintenance", "missing"],
         "9. Insurance. Vendor shall obtain Commercial General Liability insurance.",
         "NEGOTIATE", policy_overrides={"require_policy_maintenance_through_term": True},
         notes="No maintenance-through-term commitment stated."),
]

# ---------------------------------------------------------------------------
# Workers' Comp, Employer's Liability, Auto Liability.
# ---------------------------------------------------------------------------
CASES += [
    case("wc-01", ["workers_comp", "present"],
         "9. Insurance. Vendor shall maintain Workers' Compensation insurance as required by "
         "applicable law.",
         "ACCEPT", policy_overrides={"require_workers_comp": True},
         notes="Workers' Comp is a pure presence requirement (no numeric limit modeled — "
               "statutory)."),
    case("wc-02", ["workers_comp", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "MUST_REDLINE", policy_overrides={"require_workers_comp": True},
         notes="Workers' Comp required but not addressed at all."),
    case("el-01", ["employers_liability", "clean"],
         "9. Insurance. Vendor shall maintain Employer's Liability insurance with limits of not "
         "less than $1,000,000 each accident.",
         "ACCEPT", policy_overrides={"require_employers_liability": True, "employers_liability_minimum_limit": 1_000_000.0},
         notes="Employer's Liability limit satisfied."),
    case("el-02", ["employers_liability", "below_minimum"],
         "9. Insurance. Vendor shall maintain Employer's Liability insurance with limits of not "
         "less than $500,000 each accident.",
         "NEGOTIATE", policy_overrides={"require_employers_liability": True, "employers_liability_minimum_limit": 1_000_000.0},
         notes="$500K is below the required $1M minimum."),
    case("auto-01", ["auto_liability", "clean"],
         "9. Insurance. Vendor shall maintain Automobile Liability insurance with limits of not "
         "less than $1,000,000 per occurrence.",
         "ACCEPT", policy_overrides={"require_auto_liability": True, "auto_liability_minimum_limit": 1_000_000.0},
         notes="Auto Liability limit satisfied."),
    case("auto-02", ["auto_liability", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "MUST_REDLINE", policy_overrides={"require_auto_liability": True, "auto_liability_minimum_limit": 1_000_000.0},
         notes="Auto Liability required but not addressed."),
]

# ---------------------------------------------------------------------------
# Obligated-party resolution (insured party clarity).
# ---------------------------------------------------------------------------
CASES += [
    case("party-01", ["obligated_party", "counterparty_clean"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "ACCEPT",
         policy_overrides={"contract_side": "buy_side", "require_cgl": True,
                            "cgl_minimum_per_occurrence": 1_000_000.0, "require_counterparty_obligated": True},
         notes="We are Customer (buy_side); Vendor (sell_side) is correctly resolved as the "
               "counterparty obligated to carry the coverage."),
    case("party-02", ["obligated_party", "wrong_party"],
         "9. Insurance. Customer shall maintain Commercial General Liability insurance with "
         "limits of not less than $1,000,000 per occurrence.",
         "MUST_REDLINE",
         policy_overrides={"contract_side": "buy_side", "require_cgl": True,
                            "cgl_minimum_per_occurrence": 1_000_000.0, "require_counterparty_obligated": True},
         notes="We are Customer (buy_side); the clause obligates US, not the counterparty — "
               "wrong party for a policy requiring the counterparty to carry it."),
    case("party-03", ["obligated_party", "conflicting"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence. Customer shall maintain Commercial General "
         "Liability insurance with limits of not less than $1,000,000 per occurrence.",
         "REQUIRES_REVIEW",
         policy_overrides={"contract_side": "buy_side", "require_cgl": True,
                            "cgl_minimum_per_occurrence": 1_000_000.0, "require_counterparty_obligated": True},
         notes="Both Vendor and Customer are stated as obligated to carry CGL — genuine "
               "ambiguity about who is actually required to maintain it."),
    case("party-04", ["obligated_party", "mutual_directional"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "REQUIRES_REVIEW",
         policy_overrides={"contract_side": "mutual", "require_cgl": True,
                            "cgl_minimum_per_occurrence": 1_000_000.0, "require_counterparty_obligated": True},
         notes="Directional obligated-party statement under a mutual-position playbook — cannot "
               "determine whether Vendor is 'us' or 'counterparty'."),
    case("party-05", ["obligated_party", "not_required"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "ACCEPT",
         policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                            "require_counterparty_obligated": False},
         notes="require_counterparty_obligated is off — coverage satisfied regardless of which "
               "party is named as obligated."),
]

# ---------------------------------------------------------------------------
# Claims-made / occurrence basis ambiguity.
# ---------------------------------------------------------------------------
CASES += [
    case("basis-01", ["claims_made_occurrence", "conflict"],
         "9. Insurance. Vendor's Professional Liability insurance shall be maintained on a "
         "claims-made basis. Notwithstanding the foregoing, such Professional Liability "
         "insurance shall be maintained on an occurrence basis.",
         "REQUIRES_REVIEW", policy_overrides={"require_professional_liability": True},
         notes="Both claims-made and occurrence basis stated for the same coverage — genuine "
               "conflict, cannot safely determine the basis."),
    case("basis-02", ["claims_made_occurrence", "claims_made_only"],
         "9. Insurance. Vendor's Professional Liability insurance shall be maintained on a "
         "claims-made basis.",
         "ACCEPT", policy_overrides={"require_professional_liability": True},
         notes="Only claims-made stated, no conflict — Professional Liability requirement "
               "itself (no limit configured) is satisfied by mere presence."),
]

# ---------------------------------------------------------------------------
# Ambiguous per-occurrence/aggregate basis (two unqualified amounts).
# ---------------------------------------------------------------------------
CASES += [
    case("ambiguous-amount-01", ["ambiguous_currency", "two_unqualified_amounts"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of $1,000,000 / $2,000,000.",
         "REQUIRES_REVIEW", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Two dollar amounts with no per-occurrence/aggregate qualifier on either — cannot "
               "safely determine which is which."),
    case("ambiguous-amount-02", ["ambiguous_currency", "single_unqualified_amount"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of $1,000,000.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="A single unqualified dollar figure is read as the per-occurrence-equivalent "
               "minimum limit (the ordinary, unambiguous single-number case) — not flagged as "
               "ambiguous since there's nothing to conflict with."),
]

# ---------------------------------------------------------------------------
# Schedule/exhibit cross-references; amendments.
# ---------------------------------------------------------------------------
CASES += [
    case("schedule-crossref-01", ["schedule_crossref", "nothing_else"],
         "9. Insurance. Insurance requirements, including coverage types and limits, shall be as "
         "set forth in the attached Insurance Schedule.",
         "REQUIRES_REVIEW",
         notes="Material insurance requirements are delegated wholesale to an external Schedule "
               "with no dimension independently established in-clause."),
    case("schedule-crossref-02", ["schedule_crossref", "supplementing"],
         FULLY_COMPLIANT_TEXT + " This Section is further supplemented by the attached Insurance "
         "Schedule.",
         "ACCEPT", policy_overrides=dict(FULLY_COMPLIANT_POLICY),
         notes="A Schedule cross-reference that supplements (rather than replaces) an "
               "otherwise-complete in-clause treatment does not block evaluation."),
    case("amendment-01", ["amendment", "consistent"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.\n\n18. Amendment to Insurance Terms. For "
         "the avoidance of doubt, Vendor confirms its Commercial General Liability insurance "
         "limits remain not less than $1,000,000 per occurrence, consistent with Section 9.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Two anchored windows restate the SAME limit — no conflict, values merge cleanly."),
    case("amendment-02", ["amendment", "changes_limit"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.\n\n18. First Amendment. Section 9 is "
         "hereby amended to require Commercial General Liability insurance with limits of not "
         "less than $2,000,000 per occurrence.",
         "REQUIRES_REVIEW", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="The original clause and the amendment state two DIFFERENT CGL limits — cannot "
               "determine which one controls without legal interpretation."),
]

# ---------------------------------------------------------------------------
# Missing insurance clause -> NOT_APPLICABLE.
# ---------------------------------------------------------------------------
CASES += [
    case("not-applicable-01", ["not_applicable"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware, without regard to its conflicts of laws principles.",
         "NOT_APPLICABLE", notes="No insurance clause anchor at all."),
    case("not-applicable-02", ["not_applicable", "commercial_only"],
         "9. Fees. Customer shall pay Vendor the fees set forth in the applicable Order Form "
         "within 30 days of invoice.",
         "NOT_APPLICABLE", notes="Ordinary commercial clause, no insurance content."),
]

# ---------------------------------------------------------------------------
# Malformed / degenerate clauses.
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-01", ["malformed", "fragment"],
         "9. Insurance. Coverage.",
         "MUST_REDLINE", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Anchor matches ('insurance') but the fragment contains no coverage-type anchor "
               "at all, so CGL is simply never established — required CGL with nothing "
               "addressed is the same MUST_REDLINE branch any other missing required coverage "
               "hits."),
    case("malformed-02", ["malformed", "heading_only"],
         "9. Insurance.",
         "ACCEPT",
         notes="The section heading itself ('Insurance') matches the anchor, so clause_found=True "
               "even with no body — with nothing required by default policy, no notes fire -> "
               "ACCEPT, not a fabricated NOT_APPLICABLE."),
    case("malformed-03", ["malformed", "ocr_noise"],
         "9.  Insurance .   Vendor  shall   maintain   Commercial   General   Liability  "
         "insurance  with  limits  of  not  less  than  $1,000,000   per   occurrence .",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Irregular whitespace (OCR-style artifact) should not defeat the anchor, coverage-"
               "type, or dollar-amount regexes, which tolerate \\s+ throughout."),
]

# ---------------------------------------------------------------------------
# Explicit negations.
# ---------------------------------------------------------------------------
CASES += [
    case("negation-01", ["negation", "no_additional_insured"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance. Customer "
         "shall not be named as an additional insured on any such policy.",
         "NEGOTIATE", policy_overrides={"require_additional_insured": True},
         notes="Explicit negation does not match the additional-insured presence regex (which "
               "only detects an affirmative naming) — additional_insured_required stays None, so "
               "the 'not found' NEGOTIATE note fires exactly as it would for silence; the "
               "explicit negation is not treated any differently, the conservative and correct "
               "behavior here."),
    case("negation-02", ["negation", "no_waiver"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance. Vendor's "
         "insurer shall not be required to waive any rights of subrogation.",
         "NEGOTIATE", policy_overrides={"require_waiver_of_subrogation": True},
         notes="Explicit negation similarly does not establish an affirmative waiver — treated "
               "as a gap, not a special negative signal."),
]

# ---------------------------------------------------------------------------
# Carve-outs / exceptions.
# ---------------------------------------------------------------------------
CASES += [
    case("exception-01", ["exception", "additional_insured_carveout"],
         "9. Insurance. Customer shall be named as an additional insured on all policies except "
         "Workers' Compensation and Employer's Liability insurance.",
         "ACCEPT", policy_overrides={"require_additional_insured": True},
         notes="The carve-out (WC/EL excluded) is a standard, minor exception — the dominant "
               "additional-insured commitment still satisfies the presence-only requirement."),
    case("exception-02", ["exception", "cgl_minimum_with_deductible"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence, subject to a deductible of not more than "
         "$50,000.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="A stated deductible does not reduce the per-occurrence limit itself — the "
               "deductible is extracted as an independent fact (deductible_or_sir) and does not "
               "affect the CGL limit check."),
]

# ---------------------------------------------------------------------------
# Additional coverage: deductible/SIR extraction, alternate rating
# phrasing, more negations, sell-side framing, boundary limits, and other
# required categories not yet independently exercised above.
# ---------------------------------------------------------------------------
CASES += [
    case("deductible-01", ["deductible", "extraction"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence, subject to a self-insured retention of "
         "$25,000.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Self-insured retention extracted as an independent fact; no policy dimension "
               "gates it directly, so it does not affect the CGL check."),
    case("rating-02", ["insurer_rating", "alternate_phrasing"],
         "9. Insurance. All insurers providing coverage hereunder shall be rated A- or better.",
         "ACCEPT", policy_overrides={"require_minimum_insurer_rating": True},
         notes="Alternate rating phrasing without the literal 'A.M. Best' name still satisfies "
               "the presence-only rating requirement."),
    case("negation-03", ["negation", "no_certificate"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance. Vendor "
         "shall not be required to provide Customer with a certificate of insurance.",
         "NEGOTIATE", policy_overrides={"require_certificate_of_insurance": True},
         notes="Explicit negation does not match the certificate-of-insurance presence regex "
               "(which only detects an affirmative requirement) — treated as a gap, same as "
               "silence."),
    case("negation-04", ["negation", "no_subcontractor"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance. Vendor "
         "shall have no obligation to require its subcontractors to maintain insurance.",
         "NEGOTIATE", policy_overrides={"require_subcontractor_coverage": True},
         notes="Explicit negation does not establish an affirmative subcontractor-coverage "
               "obligation — treated as a gap."),
    case("sellside-clean-01", ["clean_all", "sell_side"],
         "9. Insurance. Customer shall maintain Commercial General Liability insurance with "
         "limits of not less than $1,000,000 per occurrence for the benefit of Vendor.",
         "ACCEPT",
         policy_overrides={"contract_side": "sell_side", "require_cgl": True,
                            "cgl_minimum_per_occurrence": 1_000_000.0, "require_counterparty_obligated": True},
         notes="We are Vendor (sell_side); Customer (buy_side) is correctly resolved as the "
               "counterparty obligated to carry the coverage."),
    case("cgl-boundary-01", ["cgl", "exact_boundary"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Limit exactly equal to the required minimum satisfies it (>= comparison, not "
               "strictly >)."),
    case("multi-obligated-party-01", ["multi_type", "obligated_party", "consistent"],
         "9. Insurance. Vendor shall maintain the following coverages: (a) Commercial General "
         "Liability with limits of not less than $1,000,000 per occurrence; (b) Cyber Liability "
         "with limits of not less than $2,000,000 per claim.",
         "ACCEPT",
         policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                            "require_cyber_liability": True, "cyber_liability_minimum_limit": 2_000_000.0,
                            "contract_side": "buy_side", "require_counterparty_obligated": True},
         notes="A single obligated party ('Vendor') stated once governs both coverage types "
               "listed afterward — both resolve consistently to 'counterparty'."),
    case("exclusivity-not-required-01", ["insurer_rating", "not_required"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance with limits "
         "of not less than $1,000,000 per occurrence.",
         "ACCEPT", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0,
                                      "require_minimum_insurer_rating": False},
         notes="No insurer-rating language present, but the requirement is off — not held "
               "against the clause."),
    case("cancellation-conflict-01", ["cancellation_notice", "conflict"],
         "9. Insurance. Vendor shall provide Customer with 30 days' prior written notice of "
         "cancellation of any required policy. Notwithstanding the foregoing, Vendor shall "
         "provide Customer with 15 days' prior written notice of cancellation of any required "
         "policy.",
         "REQUIRES_REVIEW", policy_overrides={"require_notice_of_cancellation": True, "minimum_cancellation_notice_days": 30.0},
         notes="Two different cancellation-notice periods stated — genuine conflict, must "
               "abstain."),
    case("malformed-04", ["malformed", "no_amount_no_party"],
         "9. Insurance. Coverage shall be maintained at all times.",
         "MUST_REDLINE", policy_overrides={"require_cgl": True, "cgl_minimum_per_occurrence": 1_000_000.0},
         notes="Generic 'coverage shall be maintained' names no coverage type and no party — "
               "CGL never established, same MUST_REDLINE branch as any missing required "
               "coverage."),
    case("employers-liability-missing-01", ["employers_liability", "missing"],
         "9. Insurance. Vendor shall maintain Commercial General Liability insurance.",
         "MUST_REDLINE", policy_overrides={"require_employers_liability": True, "employers_liability_minimum_limit": 1_000_000.0},
         notes="Employer's Liability required but not addressed at all."),
    case("professional-liability-tail-not-required-01", ["claims_made_tail", "not_required"],
         "9. Insurance. Vendor shall maintain Professional Liability insurance on a claims-made "
         "basis.",
         "ACCEPT", policy_overrides={"require_professional_liability": True},
         notes="Claims-made basis stated with no limit configured and tail not required — "
               "presence-only requirement satisfied."),
]
