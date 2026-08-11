"""
Adversarial corpus for the Phase 2 deterministic extraction benchmark
(see benchmarks/run_phase2_extraction_benchmark.py).

Unlike the six policy-engine corpora (which label the correct ENFORCEMENT
decision against a fixed policy), this corpus labels the correct
EXTRACTION outcome against no policy at all: for a given document and a
given (clause_type, field_name), what should playbook_extraction.propose_
fields() produce — ESTABLISHED (with a specific value), NOT_ESTABLISHED,
or CONFLICTING?

The catastrophic failure this corpus exists to catch is false
establishment: the document does not actually support a value, but
extraction proposes it as ESTABLISHED anyway. Every case with an
"expected NOT_ESTABLISHED/CONFLICTING" entry is an adversarial probe for
exactly that failure — a document that contains something PLAUSIBLY
adjacent to the field (a favorable term, a single-direction clause, a
numeric value with no policy meaning) but does not actually establish it.
"""
from typing import Any, Dict, List, Optional, Tuple

Expectation = Any  # ("ESTABLISHED", value) | "NOT_ESTABLISHED" | "CONFLICTING"


def case(
    id: str, tags: List[str], text: str, contract_side: str = "mutual",
    expectations: Optional[Dict[str, Dict[str, Expectation]]] = None, notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "contract_side": contract_side,
        "expectations": expectations or {}, "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Clean single-clause cases — establishment where the document genuinely
# supports it.
# ---------------------------------------------------------------------------

CASES += [
    case("clean-liability-01", ["clean", "liability"],
         "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid "
         "in the preceding twelve (12) months, except for breaches of Confidentiality.",
         expectations={"limitation_of_liability": {
             "preferred_multiplier": ("ESTABLISHED", 2.0),
             "required_exceptions_json": ("ESTABLISHED", ["confidentiality"]),
             "acceptable_max_multiplier": "NOT_ESTABLISHED",
             "negotiate_max_multiplier": "NOT_ESTABLISHED",
             "prohibit_unlimited": "NOT_ESTABLISHED",
         }},
         notes="Textbook single-provision case: preferred + one carve-out established, ladder untouched."),

    case("clean-indemnification-01", ["clean", "indemnification"],
         "9. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
         "and against any third-party claims only, arising from Vendor's gross negligence; the "
         "indemnifying party shall control the defense.",
         contract_side="sell_side",
         expectations={"indemnification": {
             "require_exposure_third_party_only": ("ESTABLISHED", True),
             "require_defense_control_for_exposure": ("ESTABLISHED", True),
             "exposure_acceptable_max_multiplier": "NOT_ESTABLISHED",
         }}),

    case("clean-termination-01", ["clean", "termination"],
         "15. Termination. Either party may terminate this Agreement for convenience upon 60 "
         "days written notice. Sections regarding Confidentiality shall survive termination.",
         contract_side="sell_side",
         expectations={"termination": {
             "require_mutual_convenience_termination": ("ESTABLISHED", True),
             "min_notice_days_against_us": ("ESTABLISHED", 60),
             "required_survival_topics_json": ("ESTABLISHED", ["confidentiality"]),
             "fee_preferred_multiplier": "NOT_ESTABLISHED",
         }}),

    case("clean-confidentiality-01", ["clean", "confidentiality"],
         "10. Confidentiality. Each party shall protect the other party's Confidential "
         "Information for a period of 5 years using reasonable care, excluding "
         "information that was already known or independently developed.",
         contract_side="sell_side",
         expectations={"confidentiality": {
             "require_mutual_confidentiality": ("ESTABLISHED", True),
             "min_protection_duration_years": ("ESTABLISHED", 5),
         }}),

    case("clean-assignment-01", ["clean", "assignment"],
         "16. Assignment. Neither party may assign this Agreement without the other's prior "
         "written consent, which consent shall not be unreasonably withheld, except in "
         "connection with a merger, acquisition, or change of control.",
         contract_side="sell_side",
         expectations={"assignment": {
             "require_consent_for_counterparty_assignment": ("ESTABLISHED", True),
             "prohibit_sole_discretion_consent": "NOT_ESTABLISHED",
         }}),

    case("clean-governing-law-01", ["clean", "governing_law"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware. Any dispute arising under this Agreement shall be resolved by binding "
         "arbitration.",
         expectations={"governing_law": {
             "preferred_jurisdictions_json": ("ESTABLISHED", ["Delaware"]),
             "required_dispute_resolution": ("ESTABLISHED", "arbitration"),
             "acceptable_jurisdictions_json": "NOT_ESTABLISHED",
             "require_jury_trial_waiver": "NOT_ESTABLISHED",
         }}),
]

# ---------------------------------------------------------------------------
# Negative evidence — the core false-establishment adversarial probes.
# Each of these contains a plausible-looking but insufficient signal.
# ---------------------------------------------------------------------------

CASES += [
    case("negev-liability-cap-does-not-prohibit", ["negative_evidence", "liability"],
         "12. Limitation of Liability. Liability shall not exceed three (3) times the fees paid.",
         expectations={"limitation_of_liability": {"prohibit_unlimited": "NOT_ESTABLISHED"}},
         notes="A numeric cap is a favorable term, not proof unlimited would be refused."),

    case("negev-liability-silent-consequential", ["negative_evidence", "liability"],
         "12. Limitation of Liability. Liability shall not exceed one (1) times the fees paid.",
         expectations={"limitation_of_liability": {"require_consequential_damages_exclusion": "NOT_ESTABLISHED"}},
         notes="Consequential damages never mentioned at all -- must not become an affirmative False."),

    case("negev-indemnification-mutual-directional", ["negative_evidence", "indemnification"],
         "9. Indemnification. Vendor shall indemnify Customer from and against third-party "
         "claims only, arising from Vendor's gross negligence.",
         contract_side="mutual",
         expectations={"indemnification": {"require_exposure_third_party_only": "NOT_ESTABLISHED"}},
         notes="Directional clause with contract_side=mutual selected -- cannot resolve which obligation is ours."),

    case("negev-termination-asymmetric-convenience", ["negative_evidence", "termination"],
         "15. Termination. Customer may terminate this Agreement for convenience upon 30 days "
         "written notice.",
         contract_side="sell_side",
         expectations={"termination": {"require_mutual_convenience_termination": "NOT_ESTABLISHED"}},
         notes="Only Customer holds the right -- a one-sided template does not establish 'we don't require mutuality.'"),

    case("negev-termination-cure-present-not-prohibit", ["negative_evidence", "termination"],
         "15. Termination. Either party may terminate for cause upon a material breach of this "
         "Agreement by the other party that remains uncured for thirty (30) days.",
         contract_side="sell_side",
         expectations={"termination": {"prohibit_immediate_termination_for_cause": "NOT_ESTABLISHED"}},
         notes="A cure period being present in this deal doesn't prove immediate termination is categorically prohibited."),

    case("negev-confidentiality-one-directional", ["negative_evidence", "confidentiality"],
         "10. Confidentiality. Vendor shall protect Customer's Confidential Information for a "
         "period of five (5) years.",
         contract_side="sell_side",
         expectations={"confidentiality": {"require_mutual_confidentiality": "NOT_ESTABLISHED"}},
         notes="Only one direction of protection appears -- must not become an affirmative False for mutuality."),

    case("negev-assignment-reasonable-not-prohibit", ["negative_evidence", "assignment"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer, which consent shall not be unreasonably withheld.",
         contract_side="sell_side",
         expectations={"assignment": {"prohibit_sole_discretion_consent": "NOT_ESTABLISHED"}},
         notes="'Reasonable' consent standard is not evidence about sole-discretion language one way or the other."),

    case("negev-governing-law-jury-silent", ["negative_evidence", "governing_law"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "New York.",
         expectations={"governing_law": {"require_jury_trial_waiver": "NOT_ESTABLISHED"}},
         notes="The single highest-risk false-establishment trap named in the task: jury trial "
               "silence must never become an affirmative False."),

    case("negev-governing-law-no-alternatives", ["negative_evidence", "governing_law"],
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware.",
         expectations={"governing_law": {
             "acceptable_jurisdictions_json": "NOT_ESTABLISHED",
             "prohibited_jurisdictions_json": "NOT_ESTABLISHED",
         }},
         notes="One named jurisdiction never establishes a set of alternatives or exclusions."),
]

# ---------------------------------------------------------------------------
# Self-evident negative establishment — the one direction that IS safe to
# establish from a favorable-looking clause.
# ---------------------------------------------------------------------------

CASES += [
    case("selfevident-liability-unlimited", ["self_evident", "liability"],
         "12. Limitation of Liability. Each party shall have unlimited liability under this "
         "Agreement for breaches of this Section.",
         expectations={"limitation_of_liability": {"prohibit_unlimited": ("ESTABLISHED", False)}}),

    case("selfevident-termination-immediate", ["self_evident", "termination"],
         "15. Termination. Either party may terminate this Agreement immediately upon a "
         "material breach of this Agreement by the other party, without opportunity to cure.",
         contract_side="sell_side",
         expectations={"termination": {"prohibit_immediate_termination_for_cause": ("ESTABLISHED", False)}}),

    case("selfevident-assignment-sole-discretion", ["self_evident", "assignment"],
         "16. Assignment. Vendor may not assign this Agreement without the prior written "
         "consent of Customer, which consent may be withheld in its sole discretion.",
         contract_side="sell_side",
         expectations={"assignment": {"prohibit_sole_discretion_consent": ("ESTABLISHED", False)}}),
]

# ---------------------------------------------------------------------------
# Multiple clauses of the same type / amendments / conflicts
# ---------------------------------------------------------------------------

CASES += [
    case("conflict-liability-two-caps", ["conflict", "liability"],
         "12. Limitation of Liability. Aggregate liability shall not exceed 2 times the total "
         "annual fees paid."
         + (" Various other terms of this Agreement are set forth below and are not material " * 60)
         + " 30. Limitation of Liability. Liability shall not exceed 5 times the total annual fees paid.",
         expectations={"limitation_of_liability": {"preferred_multiplier": "CONFLICTING"}},
         notes="Two genuinely different, unreconciled caps, far enough apart that each resolves "
               "cleanly on its own (same pattern as "
               "tests/test_liability_policy_engine.py::test_two_unreconciled_provisions_require_review_not_first_pick) "
               "-- must not silently pick one."),

    case("amendment-liability-resolved", ["amendment", "liability"],
         "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid."
         + (" Various other terms of this Agreement are set forth below and are not material " * 60)
         + " Amendment No. 1 - Limitation of Liability. Section 12 is hereby amended and restated "
           "in its entirety: liability shall not exceed four (4) times the fees paid.",
         expectations={"limitation_of_liability": {"preferred_multiplier": ("ESTABLISHED", 4.0)}},
         notes="An explicit amendment restating the clause resolves to the amendment's value -- "
               "this is the engine's own existing document-wide reconciliation machinery, reused "
               "unmodified, not new Phase 2 logic."),

    case("consistent-duplicate-liability", ["duplicate", "liability"],
         "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid.\n\n"
         "Schedule 1. For the avoidance of doubt, liability under this Agreement, including "
         "this Schedule, shall not exceed two (2) times the fees paid.",
         expectations={"limitation_of_liability": {"preferred_multiplier": ("ESTABLISHED", 2.0)}},
         notes="Two provisions stating the SAME value are not a conflict."),

    # NOTE: a genuine same-field termination conflict (two differently-
    # worded convenience-notice rights for the same side) was attempted
    # here and removed — extract_termination_facts() does not perform
    # document-wide multi-right discovery the way extract_liability_facts()
    # does for provisions (confirmed by direct inspection: a second
    # same-role right elsewhere in the document is simply never returned).
    # This is a pre-existing engine-extraction-scope limitation, not
    # something Phase 2 introduces or may fix (no policy engine is
    # modified by this phase) — recorded here rather than silently
    # dropped, and called out in the Phase 2 report.
]

# ---------------------------------------------------------------------------
# Cross-references, asymmetric provisions
# ---------------------------------------------------------------------------

CASES += [
    case("crossref-liability-dpa", ["cross_reference", "liability"],
         "12. Limitation of Liability. Except as set forth in the Data Processing Addendum "
         "(\"DPA\"), liability shall not exceed two (2) times the fees paid. Liability for data "
         "breaches is addressed exclusively in the DPA, which is not part of this document.",
         expectations={"limitation_of_liability": {"preferred_multiplier": ("ESTABLISHED", 2.0)}},
         notes="A cross-reference to an absent document must not fabricate a value for the "
               "referenced dimension; the general cap itself is still establishable."),

    case("asymmetric-indemnification-reciprocal-unverified", ["asymmetric", "indemnification"],
         "9. Indemnification. Each party shall indemnify, defend, and hold harmless the other "
         "party from and against any third-party claims arising from the indemnifying party's "
         "gross negligence; provided, that Vendor's indemnification obligations under this "
         "Section apply to third-party claims only, and Customer's indemnification obligations "
         "under this Section apply to any claims, whether direct or third-party.",
         contract_side="sell_side",
         expectations={"indemnification": {"require_exposure_third_party_only": "NOT_ESTABLISHED"}},
         notes="A reciprocal opener whose symmetry claim is contradicted by differentiated "
               "per-party terms -- the engine's own reciprocal-asymmetry detection (reused via "
               "_resolve_obligations_for_side) already refuses to guess which named party's "
               "terms are ours; extraction must inherit that refusal, not paper over it."),

    case("asymmetric-confidentiality-different-durations", ["asymmetric", "confidentiality"],
         "10. Confidentiality. Vendor shall protect Customer's Confidential Information for a "
         "period of 5 years. Customer shall protect Vendor's Confidential Information "
         "for a period of 3 years.",
         contract_side="sell_side",
         expectations={"confidentiality": {
             "require_mutual_confidentiality": ("ESTABLISHED", True),
             # We are Vendor (sell_side): "Vendor protects Customer" is US
             # protecting THEM (max_exposure=5); "Customer protects Vendor"
             # is THEM protecting US (min_protection=3).
             "max_exposure_duration_years": ("ESTABLISHED", 5),
             "min_protection_duration_years": ("ESTABLISHED", 3),
         }},
         notes="Genuinely asymmetric but both directions independently well-evidenced -- both "
               "single numbers are establishable, not a conflict (they're not the same field)."),
]

# ---------------------------------------------------------------------------
# Missing dimensions, malformed sections, unsupported language, absent
# clauses, partial-coverage documents
# ---------------------------------------------------------------------------

CASES += [
    case("missing-liability-no-numeric-cap", ["missing_dimension", "liability"],
         "12. Limitation of Liability. The parties' liability shall be as set forth in the "
         "applicable Order Form.",
         expectations={"limitation_of_liability": {
             "preferred_multiplier": "NOT_ESTABLISHED",
             "prohibit_unlimited": "NOT_ESTABLISHED",
         }},
         notes="Clause exists but defers the actual number elsewhere -- nothing numeric to establish."),

    case("malformed-liability-fragment", ["malformed", "liability"],
         "12. Limit... [OCR ERROR] ...bility shall not [ILLEGIBLE] fees paid.",
         expectations={"limitation_of_liability": {"preferred_multiplier": "NOT_ESTABLISHED"}},
         notes="Garbled/OCR-damaged section -- must fail closed to NOT_ESTABLISHED, not guess a number."),

    case("unsupported-liability-vague-language", ["unsupported_language", "liability"],
         "12. Limitation of Liability. The parties agree that liability shall be reasonable "
         "and proportionate to the nature of the breach.",
         expectations={"limitation_of_liability": {"preferred_multiplier": "NOT_ESTABLISHED"}},
         notes="Qualitative, non-numeric liability language -- no multiplier to extract."),

    case("absent-clause-indemnification", ["absent_clause", "indemnification"],
         "This Agreement covers the license of software and contains no indemnification "
         "obligations of any kind.",
         expectations={"indemnification": {
             "require_exposure_third_party_only": "NOT_ESTABLISHED",
             "prohibit_uncapped_exposure": "NOT_ESTABLISHED",
         }},
         notes="No indemnification clause at all -- every field must stay unestablished, not "
               "'permissively' assume no obligations exist."),

    case("partial-coverage-liability-and-governing-law-only", ["partial_coverage"],
         "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid.\n\n"
         "20. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware.",
         expectations={
             "limitation_of_liability": {"preferred_multiplier": ("ESTABLISHED", 2.0)},
             "governing_law": {"preferred_jurisdictions_json": ("ESTABLISHED", ["Delaware"])},
             "indemnification": {"require_exposure_third_party_only": "NOT_ESTABLISHED"},
             "termination": {"require_mutual_convenience_termination": "NOT_ESTABLISHED"},
             "confidentiality": {"require_mutual_confidentiality": "NOT_ESTABLISHED"},
             "assignment": {"require_consent_for_counterparty_assignment": "NOT_ESTABLISHED"},
         },
         notes="A document that only addresses 2 of 6 supported clause types -- the other four "
               "must produce zero established fields, not fill in defaults."),

    case("empty-document", ["absent_clause", "all"],
         "This is a cover page with no substantive contract terms.",
         expectations={
             "limitation_of_liability": {"preferred_multiplier": "NOT_ESTABLISHED"},
             "indemnification": {"require_exposure_third_party_only": "NOT_ESTABLISHED"},
             "termination": {"require_mutual_convenience_termination": "NOT_ESTABLISHED"},
             "confidentiality": {"require_mutual_confidentiality": "NOT_ESTABLISHED"},
             "assignment": {"require_consent_for_counterparty_assignment": "NOT_ESTABLISHED"},
             "governing_law": {"preferred_jurisdictions_json": "NOT_ESTABLISHED"},
         }),
]
