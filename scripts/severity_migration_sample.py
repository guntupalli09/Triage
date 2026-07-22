"""
Phase 2/3 migration sample (architecture doc §12) — a representative,
attorney-reviewable set of real rule_ids from rules_engine.py, scored
against the v1.0 factor model with legacy severity preserved alongside.

This is deliberately NOT the full 117-rule migration. Scoring all 117 (soon
500+) rules is real legal-review work requiring the §10 workflow (a second
contributor blind-re-scores each vector, a subject-matter reviewer signs
off) — it is not something to simulate or fabricate in bulk here. This file
demonstrates the migration *pipeline* end-to-end on 18 real rules chosen to
span every severity tier and several clause_categories, using factor
vectors already derived and justified in the architecture doc's stress test
(docs/rules_engine/severity_architecture.md §5) wherever a corpus row maps
directly onto a real rule.

Run `python3 scripts/generate_migration_report.py` to produce the
comparison report (Task 5) from this data.
"""

from rules_engine import Severity
from severity_scoring import FactorVector, ScoredRule

# Each entry's factor_vector cites which architecture-doc §5 stress-test row
# (if any) it corresponds to, in the justification strings, so the migration
# report's reasoning is traceable back to already-reviewed analysis rather
# than being scored fresh and silently here.

MIGRATION_SAMPLE = [
    ScoredRule(
        rule_id="H_LOL_01",
        clause_category="LiabilityCap",
        affected_party_role="Vendor",
        rationale="Liability may be uncapped or cap may be weakened",
        legacy_severity=Severity.HIGH,
        factor_vector=FactorVector.from_levels(
            FB=3,  # architecture doc §5 row 3: "shall not be limited" -- structurally uncapped
            REV=1,
        ),
    ),
    ScoredRule(
        rule_id="H_TERM_CONVENIENCE_01",
        clause_category="Termination",
        affected_party_role="Vendor",
        rationale="One-sided termination for convenience allows one party to exit the deal at will",
        legacy_severity=Severity.HIGH,
        factor_vector=FactorVector.from_levels(
            # NOTE: this rule's detection pattern does not currently
            # distinguish a noticed exit right from an immediate one (see
            # architecture doc §5.1's recommendation that legacy split this
            # into two rules). Scored here as the WORSE case (row 6: no
            # notice) since that is the pattern's plain-language title
            # ("termination for convenience" with no notice qualifier) --
            # flagged explicitly as a migration finding, not asserted quietly.
            UD=3, REV=1, OC=2,
        ),
    ),
    ScoredRule(
        rule_id="H_LOAN_GUARANTY_WAIVER_01",
        clause_category="PersonalGuaranty",
        affected_party_role="Guarantor",
        rationale="Absolute and unconditional guaranty waiving suretyship defenses",
        legacy_severity=Severity.CRITICAL,
        factor_vector=FactorVector.from_levels(PE=3, REV=1),  # doc §5 row 8 pattern
    ),
    ScoredRule(
        rule_id="H_LOAN_CONFESSION_JUDGMENT_01",
        clause_category="RightsWaiver",
        affected_party_role="Borrower",
        rationale="Confession of judgment / cognovit clause",
        legacy_severity=Severity.CRITICAL,
        factor_vector=FactorVector.from_levels(RW=3, REV=3),  # doc §5 row 10
    ),
    ScoredRule(
        rule_id="H_EMPLOY_IP_ASSIGN_OVERBROAD_01",
        clause_category="IPAssignment",
        affected_party_role="Employee",
        rationale="Broad invention assignment lacking statutory own-time carve-out",
        legacy_severity=Severity.HIGH,
        factor_vector=FactorVector.from_levels(AT=3, REV=3),  # doc §5 row 14
    ),
    ScoredRule(
        rule_id="M_LEASE_CAM_UNCAPPED_01",
        clause_category="FeeCap",
        affected_party_role="Tenant",
        rationale="CAM charges lack a cap",
        legacy_severity=Severity.MEDIUM,
        factor_vector=FactorVector.from_levels(FB=3, UD=2, REV=1),  # doc §5 row 20
    ),
    ScoredRule(
        rule_id="H_CONSTR_PAY_IF_PAID_01",
        clause_category="PaymentContingency",
        affected_party_role="Subcontractor",
        rationale="Pay-if-paid clause shifts owner non-payment risk to subcontractor",
        legacy_severity=Severity.HIGH,
        factor_vector=FactorVector.from_levels(FB=3, REV=2),  # doc §5 row 22
    ),
    ScoredRule(
        rule_id="M_CONSTR_LIEN_WAIVER_01",
        clause_category="RightsWaiver",
        affected_party_role="Subcontractor",
        rationale="Lien waiver required before payment is received",
        legacy_severity=Severity.MEDIUM,
        factor_vector=FactorVector.from_levels(RW=1, FB=2, REV=2),  # doc §5 row 23
    ),
    ScoredRule(
        rule_id="M_PARTNERSHIP_CAPITAL_CALL_01",
        clause_category="OwnershipDilution",
        affected_party_role="Partner",
        rationale="Capital call default triggers dilution penalty",
        legacy_severity=Severity.MEDIUM,
        factor_vector=FactorVector.from_levels(AT=3, UD=3, REV=3),  # doc §5 row 27
    ),
    ScoredRule(
        rule_id="M_MA_EARNOUT_DISCRETION_01",
        clause_category="UnilateralDiscretion",
        affected_party_role="Buyer",
        rationale="Earn-out payment subject to buyer's discretion",
        legacy_severity=Severity.MEDIUM,
        factor_vector=FactorVector.from_levels(FB=2, UD=3, REV=2),  # doc §5 row 29
    ),
    ScoredRule(
        rule_id="H_ASSIGN_CHANGE_CTRL_01",
        clause_category="AssignmentRestriction",
        affected_party_role="Company",
        rationale="Assignment restricted on change of control",
        legacy_severity=Severity.HIGH,
        factor_vector=FactorVector.from_levels(UD=2, REV=1),  # doc §5 row 40
        # architecture doc §5.1 names this the single most contestable
        # result in the entire stress test -- the framework's answer is
        # principled but genuinely deal-size-dependent in a way §3
        # deliberately excludes. Do not let automated confidence scoring
        # override that documented human call.
        known_contestable=True,
    ),
    ScoredRule(
        rule_id="M_NONCOMP_01",
        clause_category="RestrictiveCovenant",
        affected_party_role="Employee",
        rationale="Non-compete / non-solicit style restriction",
        legacy_severity=Severity.MEDIUM,
        factor_vector=FactorVector.from_levels(RS=1, REV=1, DUR=1),  # doc §5 row 17
    ),
    ScoredRule(
        rule_id="M_CONF_01",
        clause_category="ConfidentialityDuration",
        affected_party_role="Mutual",
        rationale="Indefinite confidentiality obligations",
        legacy_severity=Severity.MEDIUM,
        factor_vector=FactorVector.from_levels(DUR=2),  # doc §5 row 1
    ),
    ScoredRule(
        rule_id="M_RENEW_01",
        clause_category="AutoRenewal",
        affected_party_role="Mutual",
        rationale="Automatic renewal terms with notice requirements",
        legacy_severity=Severity.MEDIUM,
        factor_vector=FactorVector.from_levels(),  # doc §5 row 36 (disclosed, notice-based)
    ),
    ScoredRule(
        rule_id="L_GOVLAW_01",
        clause_category="Boilerplate",
        affected_party_role="Mutual",
        rationale="Specific governing law or exclusive jurisdiction clauses",
        legacy_severity=Severity.LOW,
        factor_vector=FactorVector.from_levels(),  # doc §5 row 38
    ),
    ScoredRule(
        rule_id="L_COUNTERPARTS_ESIGN_01",
        clause_category="Boilerplate",
        affected_party_role="Mutual",
        rationale="Counterparts / electronic signature clause",
        legacy_severity=Severity.LOW,
        factor_vector=FactorVector.from_levels(),  # doc §5 row 39
    ),
    ScoredRule(
        rule_id="H_IP_01",
        clause_category="IPAssignment",
        affected_party_role="Assignor",
        rationale="Broad IP assignment / ownership transfer language",
        legacy_severity=Severity.HIGH,
        factor_vector=FactorVector.from_levels(AT=3, REV=3),  # same clause_category/pattern as row 14
    ),
    ScoredRule(
        rule_id="H_PERSONAL_01",
        clause_category="PersonalGuaranty",
        affected_party_role="Individual",
        rationale="Potential personal liability exposure",
        legacy_severity=Severity.CRITICAL,
        factor_vector=FactorVector.from_levels(PE=3, REV=1),  # same clause_category/pattern as row 8
    ),
]
