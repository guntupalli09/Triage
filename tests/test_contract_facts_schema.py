"""Phase 1 canonical contract-fact schema invariants.

These tests lock the data contracts only. They do not wire extractors,
policy adapters, or generic rules.
"""
from __future__ import annotations

import pytest

from contract_facts import (
    SCHEMA_VERSION,
    BillingFrequency,
    CategoryTreatmentFact,
    CategoryTreatmentKind,
    ClaimScope,
    ClauseFamily,
    ContractCommercialFacts,
    ContractDocumentFacts,
    ContractIndemnificationFacts,
    ContractLiabilityFacts,
    ContextualRoleKind,
    CrossClauseGraph,
    CrossClauseKind,
    CrossClauseRelationship,
    DefenseControl,
    DefenseControlHolder,
    DocumentParty,
    DocumentRoleModel,
    EstablishedFact,
    EvidenceSpan,
    IndemnityObligationFacts,
    LiabilityProvisionFacts,
    MonetaryKind,
    MonetaryTreatmentFact,
    MutualityStatus,
    PaymentDueBasis,
    PaymentDueTerms,
    Presence,
    RoleBinding,
    SharedProcedure,
    TriggerCoverage,
    TriggerTreatmentFact,
    presence_from_optional_bool,
    simple_fee_period_cap,
)
from policy_grammar.cap_expression import CapOperator
from policy_grammar.cap_operands import FeeRelativeCap
from policy_grammar.fee_relative import FeeBasis, FeeScope
from policy_grammar.money import MoneyAmount
from policy_grammar.roles import NormalizedRole, TransactionOrientation


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

class TestPresenceAndEstablishedFact:
    def test_present_requires_value(self):
        with pytest.raises(ValueError):
            EstablishedFact(presence=Presence.PRESENT, value=None)

    def test_absent_forbids_value(self):
        with pytest.raises(ValueError):
            EstablishedFact(presence=Presence.ABSENT, value=True)

    def test_unknown_requires_reason(self):
        with pytest.raises(ValueError):
            EstablishedFact(presence=Presence.UNKNOWN, value=None)

    def test_unknown_not_coerced_to_false(self):
        fact = EstablishedFact.unknown("could not normalize")
        assert fact.presence is Presence.UNKNOWN
        assert fact.value is None
        assert fact.is_known is False

    def test_legacy_optional_bool_mapping(self):
        assert presence_from_optional_bool(True, established=True) is Presence.PRESENT
        assert presence_from_optional_bool(None, established=True) is Presence.ABSENT
        assert presence_from_optional_bool(None, established=False) is Presence.UNKNOWN

    def test_evidence_span_rejects_inverted_offsets(self):
        with pytest.raises(ValueError):
            EvidenceSpan(excerpt="x", start_index=10, end_index=5)


# ---------------------------------------------------------------------------
# Liability — fee-period first-class
# ---------------------------------------------------------------------------

class TestLiabilityFeePeriodCap:
    def test_simple_fee_period_cap_uses_policy_grammar_operand(self):
        expr = simple_fee_period_cap(6)
        assert expr.operator is CapOperator.SIMPLE
        assert len(expr.operands) == 1
        op = expr.operands[0]
        assert isinstance(op, FeeRelativeCap)
        assert op.months == 6
        assert op.basis is FeeBasis.FEES_PAID_OR_PAYABLE
        assert op.scope is FeeScope.AGREEMENT

    def test_provision_exposes_fee_period_months(self):
        evidence = EvidenceSpan(
            excerpt="EACH PARTY'S TOTAL AGGREGATE LIABILITY ... SIX (6) MONTH PERIOD",
            start_index=100, end_index=220, section_label="Section 6.1",
        )
        provision = LiabilityProvisionFacts(
            provision_id="lol-1",
            general_cap=EstablishedFact.present(simple_fee_period_cap(6), evidence),
            mutuality=EstablishedFact.present(MutualityStatus.MUTUAL, evidence),
            consequential_damages_excluded=EstablishedFact.present(True),
            category_treatments=(
                CategoryTreatmentFact(
                    category="indemnification",
                    treatment=CategoryTreatmentKind.WITHIN_GENERAL_CAP,
                    evidence=EvidenceSpan(excerpt="INCLUDING Section 5 indemnification"),
                ),
            ),
            evidence=evidence,
            section_label="Section 6",
        )
        assert provision.fee_period_months() == 6.0

        facts = ContractLiabilityFacts(
            clause_presence=Presence.PRESENT,
            provisions=(provision,),
            controlling_provision_id="lol-1",
            reconciliation="single",
            absence_state="PRESENT_AND_VERIFIED",
        )
        ix = facts.category_treatments_for_interactions()
        assert ix == [{
            "category": "indemnification",
            "treatment": "within_general_cap",
            "established": True,
            "raw_excerpt": "INCLUDING Section 5 indemnification",
        }]

    def test_unknown_cap_is_explicit(self):
        provision = LiabilityProvisionFacts(
            provision_id="lol-u",
            general_cap=EstablishedFact.unknown(
                "fee-period language outside truncated excerpt",
            ),
        )
        assert provision.fee_period_months() is None
        assert provision.general_cap.presence is Presence.UNKNOWN

    def test_super_cap_requires_category_cap(self):
        with pytest.raises(ValueError):
            CategoryTreatmentFact(
                category="data_breach",
                treatment=CategoryTreatmentKind.SUPER_CAP,
            )


# ---------------------------------------------------------------------------
# Indemnification — directional + shared procedure
# ---------------------------------------------------------------------------

class TestIndemnificationDirectionalProcedure:
    def _procedure(self) -> SharedProcedure:
        return SharedProcedure(
            procedure_id="proc-5.3",
            defense_control=EstablishedFact.present(
                DefenseControl(holder=DefenseControlHolder.INDEMNIFYING_PARTY),
            ),
            prompt_notice_required=EstablishedFact.present(True),
            cooperation_required=EstablishedFact.present(True),
            role_bindings=(
                RoleBinding.bound(ContextualRoleKind.INDEMNIFYING_PARTY, "Customer"),
                RoleBinding.bound(ContextualRoleKind.INDEMNIFIED_PARTY, "Provider"),
            ),
            section_label="Section 5.3",
            evidence=EvidenceSpan(
                excerpt="The indemnifying party will control the defense",
            ),
        )

    def test_shared_procedure_referenced_by_both_obligations(self):
        procedure = self._procedure()
        provider_to_customer = IndemnityObligationFacts(
            obligation_id="ind-5.1",
            indemnifying_party="Provider",
            indemnified_party="Customer",
            triggers=(
                TriggerTreatmentFact(
                    trigger="ip_infringement",
                    coverage=TriggerCoverage.COVERED,
                    evidence=EvidenceSpan(excerpt="infringes or misappropriates"),
                ),
            ),
            claim_scope=EstablishedFact.present(ClaimScope.THIRD_PARTY_ONLY),
            monetary=EstablishedFact.present(
                MonetaryTreatmentFact(kind=MonetaryKind.NOT_STATED),
            ),
            procedure_id="proc-5.3",
            section_label="Section 5.1",
        )
        customer_to_provider = IndemnityObligationFacts(
            obligation_id="ind-5.2",
            indemnifying_party="Customer",
            indemnified_party="Provider",
            triggers=(
                TriggerTreatmentFact(trigger="customer_materials", coverage=TriggerCoverage.COVERED),
                TriggerTreatmentFact(trigger="law_violations", coverage=TriggerCoverage.COVERED),
                TriggerTreatmentFact(trigger="negligence", coverage=TriggerCoverage.COVERED),
            ),
            claim_scope=EstablishedFact.present(ClaimScope.NOT_ADDRESSED),
            monetary=EstablishedFact.present(
                MonetaryTreatmentFact(kind=MonetaryKind.NOT_STATED),
            ),
            procedure_id="proc-5.3",
            section_label="Section 5.2",
        )
        facts = ContractIndemnificationFacts(
            clause_presence=Presence.PRESENT,
            obligations=(provider_to_customer, customer_to_provider),
            procedures=(procedure,),
            absence_state="PRESENT_AND_VERIFIED",
        )
        assert facts.procedure_for("proc-5.3") is procedure
        assert len(facts.obligations_where_indemnifying("Customer")) == 1
        assert facts.obligations_where_indemnified("Customer")[0].obligation_id == "ind-5.1"

        # Defense control binds to indemnifying party without needing "Customer controls" wording.
        defense = procedure.defense_control.value
        assert defense is not None
        assert defense.binds_to_indemnifying_party("Customer") is Presence.PRESENT

    def test_unknown_procedure_id_rejected(self):
        with pytest.raises(ValueError, match="unknown procedure_id"):
            ContractIndemnificationFacts(
                clause_presence=Presence.PRESENT,
                obligations=(
                    IndemnityObligationFacts(
                        obligation_id="x",
                        indemnifying_party="A",
                        indemnified_party="B",
                        triggers=(),
                        procedure_id="missing",
                    ),
                ),
                procedures=(),
                absence_state="PRESENT_AND_VERIFIED",
            )

    def test_monetary_cross_reference_is_not_cross_clause(self):
        """§6.3-style liability applicability must NOT live here as the only signal."""
        monetary = MonetaryTreatmentFact(
            kind=MonetaryKind.CROSS_REFERENCE,
            cross_reference_label="Section 6",
        )
        assert monetary.summary() == "per Section 6"
        # Cross-clause graph is the authoritative place for applicability.
        rel = CrossClauseRelationship(
            relationship_id="xr-1",
            kind=CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION,
            source_family=ClauseFamily.LIMITATION_OF_LIABILITY,
            target_family=ClauseFamily.INDEMNIFICATION,
            presence=Presence.PRESENT,
            source_section_label="Section 6.3",
            target_section_label="Section 5",
            evidence=EvidenceSpan(excerpt="INCLUDING Section 5 indemnification"),
        )
        assert rel.kind is CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION

    def test_directional_interaction_categories(self):
        facts = ContractIndemnificationFacts(
            clause_presence=Presence.PRESENT,
            obligations=(
                IndemnityObligationFacts(
                    obligation_id="p",
                    indemnifying_party="Provider",
                    indemnified_party="Customer",
                    triggers=(
                        TriggerTreatmentFact(trigger="ip_infringement", coverage=TriggerCoverage.COVERED),
                    ),
                ),
                IndemnityObligationFacts(
                    obligation_id="c",
                    indemnifying_party="Customer",
                    indemnified_party="Provider",
                    triggers=(
                        TriggerTreatmentFact(trigger="customer_materials", coverage=TriggerCoverage.COVERED),
                    ),
                ),
            ),
            absence_state="PRESENT_AND_VERIFIED",
        )
        exposure = facts.category_treatments_for_interactions(from_exposure_of="Customer")
        assert [c["category"] for c in exposure] == ["customer_materials"]


# ---------------------------------------------------------------------------
# Commercial + roles + document aggregate
# ---------------------------------------------------------------------------

class TestCommercialAndDocument:
    def test_payment_due_with_invoice_receipt_basis(self):
        due = PaymentDueTerms(days=30, basis=PaymentDueBasis.INVOICE_RECEIPT)
        commercial = ContractCommercialFacts(
            annual_fees=EstablishedFact.present(MoneyAmount.from_number(600000, "USD")),
            currency=EstablishedFact.present("USD"),
            billing_frequency=EstablishedFact.present(BillingFrequency.ANNUALLY),
            payment_due=EstablishedFact.present(due),
        )
        assert commercial.due_days_or_none() == 30
        legacy = commercial.legacy_payment_terms_dict()
        assert legacy == {
            "due_days": 30,
            "currency": "USD",
            "billing_frequency": "annually",
            "invoice_trigger": None,
        }

    def test_document_aggregate_golden_shape(self):
        """Schema-level golden object for the controlled LoL×Indemnity E2E contract."""
        roles = DocumentRoleModel(
            parties=(
                DocumentParty(
                    name="Provider",
                    normalized_role=NormalizedRole.VENDOR,
                    orientation=TransactionOrientation.SELL_SIDE,
                ),
                DocumentParty(
                    name="Customer",
                    normalized_role=NormalizedRole.CUSTOMER,
                    orientation=TransactionOrientation.BUY_SIDE,
                ),
            ),
            reviewing_orientation=TransactionOrientation.BUY_SIDE,
            mutuality=EstablishedFact.present("mutual"),
        )
        liability = ContractLiabilityFacts(
            clause_presence=Presence.PRESENT,
            provisions=(
                LiabilityProvisionFacts(
                    provision_id="lol-6",
                    general_cap=EstablishedFact.present(simple_fee_period_cap(6)),
                    mutuality=EstablishedFact.present(MutualityStatus.MUTUAL),
                    consequential_damages_excluded=EstablishedFact.present(True),
                    category_treatments=(
                        CategoryTreatmentFact(
                            category="indemnification",
                            treatment=CategoryTreatmentKind.WITHIN_GENERAL_CAP,
                        ),
                        CategoryTreatmentFact(
                            category="fraud",
                            treatment=CategoryTreatmentKind.WITHIN_GENERAL_CAP,
                        ),
                    ),
                    section_label="Section 6",
                ),
            ),
            controlling_provision_id="lol-6",
            reconciliation="single",
            absence_state="PRESENT_AND_VERIFIED",
        )
        indemnification = ContractIndemnificationFacts(
            clause_presence=Presence.PRESENT,
            obligations=(
                IndemnityObligationFacts(
                    obligation_id="5.1",
                    indemnifying_party="Provider",
                    indemnified_party="Customer",
                    triggers=(
                        TriggerTreatmentFact(trigger="ip_infringement", coverage=TriggerCoverage.COVERED),
                    ),
                    claim_scope=EstablishedFact.present(ClaimScope.THIRD_PARTY_ONLY),
                    monetary=EstablishedFact.present(MonetaryTreatmentFact(kind=MonetaryKind.NOT_STATED)),
                    procedure_id="5.3",
                ),
                IndemnityObligationFacts(
                    obligation_id="5.2",
                    indemnifying_party="Customer",
                    indemnified_party="Provider",
                    triggers=(
                        TriggerTreatmentFact(trigger="customer_materials", coverage=TriggerCoverage.COVERED),
                        TriggerTreatmentFact(trigger="unlawful_use", coverage=TriggerCoverage.NOT_ADDRESSED),
                    ),
                    procedure_id="5.3",
                ),
            ),
            procedures=(
                SharedProcedure(
                    procedure_id="5.3",
                    defense_control=EstablishedFact.present(
                        DefenseControl(holder=DefenseControlHolder.INDEMNIFYING_PARTY),
                    ),
                    prompt_notice_required=EstablishedFact.present(True),
                    cooperation_required=EstablishedFact.present(True),
                ),
            ),
            absence_state="PRESENT_AND_VERIFIED",
        )
        cross = CrossClauseGraph(
            relationships=(
                CrossClauseRelationship(
                    relationship_id="6.3-to-5",
                    kind=CrossClauseKind.LIABILITY_APPLIES_TO_INDEMNIFICATION,
                    source_family=ClauseFamily.LIMITATION_OF_LIABILITY,
                    target_family=ClauseFamily.INDEMNIFICATION,
                    presence=Presence.PRESENT,
                    source_section_label="Section 6.3",
                    target_section_label="Section 5",
                ),
            ),
        )
        doc = ContractDocumentFacts(
            roles=roles,
            commercial=ContractCommercialFacts(
                annual_fees=EstablishedFact.present(MoneyAmount.from_number("600000")),
                payment_due=EstablishedFact.present(
                    PaymentDueTerms(30, PaymentDueBasis.INVOICE_RECEIPT),
                ),
            ),
            liability=liability,
            indemnification=indemnification,
            cross_clause=cross,
        )
        payload = doc.as_dict()
        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["liability"]["provisions"][0]["fee_period_months"] == 6.0
        assert payload["cross_clause"]["relationships"][0]["kind"] == (
            "liability_applies_to_indemnification"
        )
        assert doc.cross_clause.liability_applies_to_indemnification() is not None

    def test_absent_cross_clause_rows_forbidden(self):
        with pytest.raises(ValueError, match="ABSENT"):
            CrossClauseRelationship(
                relationship_id="x",
                kind=CrossClauseKind.OTHER,
                source_family=ClauseFamily.OTHER,
                target_family=ClauseFamily.OTHER,
                presence=Presence.ABSENT,
            )
