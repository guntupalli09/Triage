"""Regression tests for v7.1's 5 new rules, added to cover material gaps
surfaced by running the engine against real, party-named SEC EDGAR
contracts (tests/fixtures/real_contracts/): reserve-based lending borrowing
base redetermination, uncapped construction liquidated damages, franchise
advertising fund accounting, standalone mandatory employment arbitration,
and government-subcontract organizational-conflict-of-interest termination."""

from rules_engine import RuleEngine, Severity


def _rule_ids(text: str):
    return {f.rule_id: f for f in RuleEngine().analyze(text)["findings"]}


def test_lending_borrowing_base_redetermination_rule():
    findings = _rule_ids(
        "The Lenders may redetermine the Borrowing Base in their sole "
        "discretion, and any deficiency shall trigger a mandatory "
        "prepayment of the excess amount."
    )
    assert findings["M_LENDING_BORROWING_BASE_REDETERMINATION_01"].severity == Severity.MEDIUM


def test_lending_borrowing_base_not_flagged_with_floor_and_cure():
    findings = _rule_ids(
        "The Borrowing Base shall be redetermined semi-annually by the "
        "Lenders in accordance with the agreed reserve report methodology "
        "set forth in Exhibit C, subject to a floor of $10,000,000 and a "
        "30-day cure period before Borrower is required to make any "
        "resulting payment."
    )
    assert "M_LENDING_BORROWING_BASE_REDETERMINATION_01" not in findings


def test_constr_liquidated_damages_uncapped_rule():
    findings = _rule_ids(
        "Contractor shall pay liquidated damages of $1,000 per day for "
        "each day beyond the Substantial Completion date that the Work "
        "remains incomplete, in addition to any other remedies available "
        "to Owner under this Agreement or at law."
    )
    assert findings["M_CONSTR_LIQUIDATED_DAMAGES_UNCAPPED_01"].severity == Severity.MEDIUM


def test_constr_liquidated_damages_not_flagged_with_aggregate_cap():
    findings = _rule_ids(
        "Contractor shall pay liquidated damages of $1,000 per day for "
        "each day beyond Substantial Completion, provided that liquidated "
        "damages shall not exceed a maximum of $100,000 in the aggregate."
    )
    assert "M_CONSTR_LIQUIDATED_DAMAGES_UNCAPPED_01" not in findings


def test_franchise_adfund_no_accounting_rule():
    findings = _rule_ids(
        "Franchisee shall contribute 2% of gross sales to the Advertising "
        "Fund, which Franchisor shall administer in its sole discretion."
    )
    assert findings["M_FRANCHISE_ADFUND_NO_ACCOUNTING_01"].severity == Severity.LOW


def test_franchise_adfund_not_flagged_with_accounting_right():
    findings = _rule_ids(
        "Franchisee shall contribute 2% of gross sales to the Advertising "
        "Fund, and Franchisor shall provide Franchisee an annual "
        "accounting of Advertising Fund expenditures upon request."
    )
    assert "M_FRANCHISE_ADFUND_NO_ACCOUNTING_01" not in findings


def test_employ_mandatory_arbitration_rule():
    findings = _rule_ids(
        "Any dispute arising under this Agreement shall be settled "
        "exclusively by arbitration conducted before a panel of three "
        "arbitrators."
    )
    assert findings["M_EMPLOY_MANDATORY_ARBITRATION_01"].severity == Severity.LOW


def test_employ_mandatory_arbitration_also_fires_alongside_class_waiver_rule():
    # The two rules are deliberately not mutually exclusive: a class-action
    # waiver on top of mandatory arbitration is a strictly bigger rights
    # reduction, and both should surface for review.
    findings = _rule_ids(
        "Employee agrees to mandatory arbitration of any dispute, and "
        "Employee agrees to a class action waiver of any right to bring "
        "or participate in a collective action."
    )
    assert "M_EMPLOY_MANDATORY_ARBITRATION_01" in findings
    assert "M_EMPLOY_ARBITRATION_CLASS_WAIVER_01" in findings


def test_govcon_oci_termination_rule():
    findings = _rule_ids(
        "Should either Party determine, in its sole discretion, that an "
        "organizational conflict of interest exists, this Subcontract may "
        "be terminated at the request of either Party."
    )
    assert findings["M_GOVCON_OCI_TERMINATION_01"].severity == Severity.MEDIUM


def test_govcon_oci_not_flagged_when_absent():
    findings = _rule_ids(
        "The parties acknowledge that no organizational conflict of "
        "interest exists as of the Effective Date."
    )
    assert "M_GOVCON_OCI_TERMINATION_01" not in findings


def test_v7_1_real_document_evidence_still_detected():
    """The 5 rules were motivated by specific real EDGAR filings; confirm
    each still fires on the actual document that surfaced the gap."""
    import os
    engine = RuleEngine()
    root = os.path.join(os.path.dirname(__file__), "fixtures", "real_contracts")
    cases = {
        "M_LENDING_BORROWING_BASE_REDETERMINATION_01": "03_credit_agreement/03a_credit_agreement_callon_petroleum_regions_bank_2010.txt",
        "M_CONSTR_LIQUIDATED_DAMAGES_UNCAPPED_01": "12_construction/century_casinos_sprung_aia_a111_gmp_construction_2005.txt",
        "M_FRANCHISE_ADFUND_NO_ACCOUNTING_01": "07_franchise/07_master_franchise_agreement_wayback_burgers_japan_2021.txt",
        "M_EMPLOY_MANDATORY_ARBITRATION_01": "09_executive_employment/transdigm_amended_restated_employment_agreement_2016.txt",
        "M_GOVCON_OCI_TERMINATION_01": "04_government_subcontract/force_protection_general_dynamics_mrap_subcontract_2008.txt",
    }
    for rule_id, relpath in cases.items():
        with open(os.path.join(root, relpath), errors="replace") as f:
            text = f.read()
        findings = {f.rule_id for f in engine.analyze(text)["findings"]}
        assert rule_id in findings, f"{rule_id} no longer fires on the real document that motivated it"
