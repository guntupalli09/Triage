"""Regression tests for v6.0 small/midsize law firm broad-practice rule coverage."""

from rules_engine import RuleEngine, Severity


def _rule_ids(text: str):
    return {f.rule_id: f for f in RuleEngine().analyze(text)["findings"]}


# -- Commercial leases --

def test_lease_personal_guaranty_rule():
    findings = _rule_ids(
        "Tenant's principal shall personally guarantee all obligations of Tenant "
        "under this Lease to Landlord for the full Term of the Lease."
    )
    assert findings["H_LEASE_PERSONAL_GUARANTY_01"].severity == Severity.HIGH


def test_lease_assignment_sublet_consent_rule():
    findings = _rule_ids(
        "Tenant shall not assign or sublet this Lease without the prior written "
        "consent of Landlord, which consent may be withheld in Landlord's sole "
        "and absolute discretion."
    )
    assert findings["H_LEASE_ASSIGN_SUBLET_01"].severity == Severity.HIGH


def test_lease_assignment_sublet_consent_not_flagged_with_reasonableness_standard():
    findings = _rule_ids(
        "Tenant shall not assign or sublet this Lease without the prior written "
        "consent of Landlord, which consent shall not be unreasonably withheld, "
        "conditioned, or delayed."
    )
    assert "H_LEASE_ASSIGN_SUBLET_01" not in findings


def test_lease_holdover_rule():
    findings = _rule_ids(
        "In the event Tenant remains in possession after expiration of the Term "
        "without Landlord's written consent, Tenant shall pay, for each month of "
        "such holding over, an amount equal to 200% of the Base Rent then in effect."
    )
    assert findings["H_LEASE_HOLDOVER_01"].severity == Severity.HIGH


def test_lease_relocation_rule():
    findings = _rule_ids(
        "Landlord may relocate Tenant to comparable space within the Building at "
        "Landlord's sole discretion upon 30 days written notice."
    )
    assert findings["H_LEASE_RELOCATION_01"].severity == Severity.HIGH


def test_lease_cam_uncapped_absence_rule():
    findings = _rule_ids(
        "Tenant shall pay its proportionate share of Common Area Maintenance "
        "charges as determined by Landlord in Landlord's sole discretion, "
        "without limitation, based on actual operating expenses incurred each year."
    )
    assert findings["M_LEASE_CAM_UNCAPPED_01"].severity == Severity.MEDIUM


def test_lease_escalation_uncapped_absence_rule():
    findings = _rule_ids(
        "Base Rent shall increase annually on each anniversary of the Commencement "
        "Date based on the then-current fair market rate for comparable space."
    )
    assert findings["M_LEASE_ESCALATION_UNCAPPED_01"].severity == Severity.MEDIUM


# -- Loans / promissory notes / personal guaranties --

def test_loan_confession_of_judgment_rule():
    findings = _rule_ids(
        "Borrower hereby authorizes any attorney to appear and confess judgment "
        "against Borrower for the entire unpaid balance of this Note."
    )
    assert findings["H_LOAN_CONFESSION_JUDGMENT_01"].severity == Severity.CRITICAL


def test_loan_confession_of_judgment_rule_alternate_phrasing():
    findings = _rule_ids(
        "This Note contains a confession of judgment provision and a cognovit "
        "clause permitting entry of judgment without notice or hearing."
    )
    assert findings["H_LOAN_CONFESSION_JUDGMENT_01"].severity == Severity.CRITICAL


def test_loan_guaranty_defense_waiver_rule():
    findings = _rule_ids(
        "This is an absolute and unconditional guaranty. Guarantor unconditionally "
        "and irrevocably waives notice, demand, presentment, and all suretyship defenses."
    )
    assert findings["H_LOAN_GUARANTY_WAIVER_01"].severity == Severity.CRITICAL


def test_loan_cross_default_rule():
    findings = _rule_ids(
        "A default under any other agreement or indebtedness of Borrower shall "
        "constitute a cross-default under this Note."
    )
    assert findings["M_LOAN_CROSS_DEFAULT_01"].severity == Severity.MEDIUM


def test_loan_prepayment_penalty_rule():
    findings = _rule_ids(
        "Borrower may prepay this Note in whole or in part, subject to a "
        "prepayment penalty equal to 3% of the amount prepaid."
    )
    assert findings["M_LOAN_PREPAY_PENALTY_01"].severity == Severity.MEDIUM


def test_loan_rate_discretion_rule():
    findings = _rule_ids(
        "Lender may adjust the interest rate at any time in Lender's sole "
        "discretion without notice to Borrower."
    )
    assert findings["M_LOAN_RATE_DISCRETION_01"].severity == Severity.MEDIUM


# -- Employment offer letters / severance --

def test_employment_atwill_waiver_rule():
    findings = _rule_ids(
        "The Company guarantees your continued employment as long as your "
        "performance remains satisfactory to the Company."
    )
    assert findings["H_EMPLOY_ATWILL_WAIVER_01"].severity == Severity.HIGH


def test_employment_ip_assignment_overbroad_absence_rule():
    findings = _rule_ids(
        "Employee hereby assigns to Company all inventions, discoveries, and "
        "work product conceived by Employee during the term of employment."
    )
    assert findings["H_EMPLOY_IP_ASSIGN_OVERBROAD_01"].severity == Severity.HIGH


def test_employment_severance_release_absence_rule():
    findings = _rule_ids(
        "In consideration for severance pay, Employee releases the Company from "
        "any and all claims of any kind, known or unknown, arising out of Employee's "
        "employment or its termination."
    )
    assert findings["M_EMPLOY_SEVERANCE_RELEASE_01"].severity == Severity.MEDIUM


def test_employment_nonsolicit_employee_rule():
    findings = _rule_ids(
        "For 24 months following termination, Contractor shall not solicit or "
        "hire any employees or personnel of the Company."
    )
    assert findings["M_EMPLOY_NONSOLICIT_EMPLOYEE_01"].severity == Severity.MEDIUM


# -- Franchise / distribution agreements --

def test_franchise_termination_no_cure_rule():
    findings = _rule_ids(
        "Franchisor may terminate this Agreement immediately upon notice to "
        "Franchisee, in Franchisor's sole discretion, without an opportunity to cure."
    )
    assert findings["H_FRANCHISE_TERMINATION_CAUSE_01"].severity == Severity.HIGH


def test_franchise_territory_absence_rule():
    findings = _rule_ids(
        "Franchisor grants Franchisee the right to operate a franchised business "
        "within the designated Territory described in Exhibit A. Franchisee shall "
        "operate solely within the Territory in accordance with Franchisor's standards."
    )
    assert findings["M_FRANCHISE_TERRITORY_01"].severity == Severity.MEDIUM


# -- M&A / partnership & operating agreements --

def test_ma_indemnification_basket_missing_rule():
    findings = _rule_ids(
        "Seller shall indemnify Buyer for any breach of any representation and "
        "warranty made by Seller in this Agreement, and Seller's indemnification "
        "obligations shall apply to the first dollar of any such claim."
    )
    assert findings["H_MA_INDEM_BASKET_MISSING_01"].severity == Severity.HIGH


def test_ma_earnout_discretion_rule():
    findings = _rule_ids(
        "The Earn-out Payment, if any, shall be determined and paid at Buyer's "
        "sole discretion based on post-closing performance of the business."
    )
    assert findings["M_MA_EARNOUT_DISCRETION_01"].severity == Severity.MEDIUM


def test_partnership_deadlock_absence_rule():
    findings = _rule_ids(
        "The Company shall be owned 50/50 by Member A and Member B, each holding "
        "equal voting rights on all matters requiring Member approval."
    )
    assert findings["M_PARTNERSHIP_DEADLOCK_01"].severity == Severity.MEDIUM


def test_partnership_capital_call_dilution_rule():
    findings = _rule_ids(
        "If a Partner fails to fund a capital call, that Partner's interest "
        "shall be subject to dilution as a penalty for such default."
    )
    assert findings["M_PARTNERSHIP_CAPITAL_CALL_01"].severity == Severity.MEDIUM


# -- Settlement agreements --

def test_settlement_release_overbroad_rule():
    findings = _rule_ids(
        "Releasor hereby releases Releasee from any and all claims, whether now "
        "known or unknown, arising out of or related to the disputed matter."
    )
    assert findings["H_SETTLEMENT_RELEASE_OVERBROAD_01"].severity == Severity.HIGH


def test_settlement_liquidated_damages_rule():
    findings = _rule_ids(
        "In addition to any other remedies, a breach of this settlement shall "
        "obligate the breaching party to pay liquidated damages of $50,000."
    )
    assert findings["M_SETTLEMENT_LIQUIDATED_DAMAGES_01"].severity == Severity.MEDIUM


# -- Construction contracts --

def test_construction_pay_if_paid_rule():
    findings = _rule_ids(
        "Payment to Subcontractor is a pay-if-paid condition precedent, "
        "contingent on payment by Owner to Contractor for the work performed."
    )
    assert findings["H_CONSTR_PAY_IF_PAID_01"].severity == Severity.HIGH


def test_construction_lien_waiver_premature_rule():
    findings = _rule_ids(
        "Subcontractor shall execute and deliver a lien waiver prior to payment "
        "being made by Owner for the applicable pay period."
    )
    assert findings["M_CONSTR_LIEN_WAIVER_01"].severity == Severity.MEDIUM


def test_construction_retainage_release_absence_rule():
    findings = _rule_ids(
        "Owner shall withhold retainage of 10 percent from each progress payment "
        "made to Contractor for work performed under this Agreement."
    )
    assert findings["M_CONSTR_RETAINAGE_01"].severity == Severity.MEDIUM


# -- Messy-document robustness: irregular whitespace/line-wraps, multiple --
# -- clauses in one chunk, should still anchor each match independently. --

def test_lease_rules_survive_messy_pdf_style_whitespace():
    messy = (
        "1. LEASE.  Tenant  shall  not  assign  or  sublet  this  Lease  or  any\n"
        "interest  therein  without  the  prior  written  consent  of  Landlord,\n"
        "which  consent  may  be  withheld  in  Landlord's  sole  and  absolute\n"
        "discretion.\n\n"
        "2. HOLDOVER. In the event Tenant remains in possession after the\n"
        "expiration of the Term without Landlord's written consent, Tenant shall\n"
        "pay, for each month of such holding over, an amount equal to 200% of the\n"
        "Base Rent then in effect.\n"
    )
    findings = _rule_ids(messy)
    assert "H_LEASE_ASSIGN_SUBLET_01" in findings
    assert "H_LEASE_HOLDOVER_01" in findings
