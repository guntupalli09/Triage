"""Regression tests for v7.0 broad small/midsize law firm coverage expansion
(63 new rules: real estate, insurance, lending, government contracting,
healthcare, IP licensing, and deeper franchise/settlement/employment/M&A/
construction coverage). Each rule has a positive-match test; rules whose
detection design can plausibly produce a false positive on protective or
unrelated language also have a negative test."""

from rules_engine import RuleEngine, Severity


def _rule_ids(text: str):
    return {f.rule_id: f for f in RuleEngine().analyze(text)["findings"]}


# -- Real estate purchase & sale --

def test_realestate_title_defect_rule():
    findings = _rule_ids(
        "Buyer shall have no right to object to any title defect or survey defect "
        "discovered prior to Closing."
    )
    assert findings["H_REALESTATE_TITLE_DEFECT_01"].severity == Severity.MEDIUM


def test_realestate_title_defect_not_flagged_with_objection_period():
    findings = _rule_ids(
        "Buyer shall have a 15-day objection period to raise any title defect, and "
        "the right to terminate or require Seller to cure prior to Closing."
    )
    assert "H_REALESTATE_TITLE_DEFECT_01" not in findings


def test_realestate_earnest_money_forfeiture_rule():
    findings = _rule_ids(
        "If Buyer defaults, Seller shall retain the entire earnest money deposit "
        "as liquidated damages."
    )
    assert findings["M_REALESTATE_EARNEST_FORFEIT_01"].severity == Severity.MEDIUM


def test_realestate_as_is_no_inspection_rule():
    findings = _rule_ids(
        "The Property is sold as-is, where-is, and Buyer waives any right to "
        "inspection of the Property."
    )
    assert findings["H_REALESTATE_AS_IS_NO_INSPECTION_01"].severity == Severity.MEDIUM


def test_realestate_as_is_not_flagged_with_inspection_period():
    findings = _rule_ids(
        "The Property is sold as-is, and Buyer shall have a 15-day inspection "
        "period to conduct due diligence."
    )
    assert "H_REALESTATE_AS_IS_NO_INSPECTION_01" not in findings


def test_realestate_closing_extension_sole_discretion_rule():
    findings = _rule_ids(
        "Seller may extend the Closing date at Seller's sole discretion without "
        "Buyer's consent."
    )
    assert findings["M_REALESTATE_CLOSING_EXTENSION_SOLE_01"].severity == Severity.MEDIUM


def test_realestate_closing_extension_not_flagged_with_mutual_agreement():
    findings = _rule_ids(
        "Either party may extend the Closing date by mutual written agreement, "
        "for a period not to exceed 10 days."
    )
    assert "M_REALESTATE_CLOSING_EXTENSION_SOLE_01" not in findings


def test_realestate_easement_undisclosed_rule():
    findings = _rule_ids(
        "The Property is conveyed subject to an existing easement as of record, "
        "without warranty."
    )
    assert findings["M_REALESTATE_EASEMENT_UNDISCLOSED_01"].severity == Severity.MEDIUM


def test_realestate_proration_undefined_rule():
    findings = _rule_ids(
        "Property taxes shall be prorated at Closing using a method to be "
        "determined by the parties."
    )
    assert findings["M_REALESTATE_PRORATION_UNDEFINED_01"].severity == Severity.LOW


def test_realestate_proration_not_flagged_with_defined_method():
    findings = _rule_ids(
        "Property taxes and utilities shall be prorated as of the Closing Date "
        "based on the most recent tax bill."
    )
    assert "M_REALESTATE_PRORATION_UNDEFINED_01" not in findings


def test_realestate_seller_financing_balloon_rule():
    findings = _rule_ids(
        "The Note includes a balloon payment due at maturity, and upon any "
        "missed payment the entire balance shall accelerate and become "
        "immediately due and payable without notice."
    )
    assert findings["H_REALESTATE_SELLER_FINANCING_BALLOON_01"].severity == Severity.MEDIUM


def test_realestate_seller_financing_not_flagged_when_no_financing():
    findings = _rule_ids(
        "The purchase price shall be paid in full in cash at Closing; no seller "
        "financing or promissory note is involved in this transaction."
    )
    assert "H_REALESTATE_SELLER_FINANCING_BALLOON_01" not in findings


# -- Insurance policies / certificates of insurance --

def test_insurance_claims_made_gap_rule():
    findings = _rule_ids(
        "Consultant shall maintain a claims-made professional liability policy, "
        "with no requirement to maintain tail coverage after termination."
    )
    assert findings["H_INSURANCE_CLAIMS_MADE_GAP_01"].severity == Severity.MEDIUM


def test_insurance_claims_made_not_flagged_with_tail_coverage():
    findings = _rule_ids(
        "Consultant shall maintain a claims-made professional liability policy "
        "and shall maintain tail coverage / an extended reporting period for "
        "three years after termination."
    )
    assert "H_INSURANCE_CLAIMS_MADE_GAP_01" not in findings


def test_insurance_subrogation_waiver_missing_rule():
    findings = _rule_ids(
        "Each party's insurer retains all rights of subrogation against the "
        "other party."
    )
    assert findings["M_INSURANCE_SUBROGATION_WAIVER_MISSING_01"].severity == Severity.LOW


def test_insurance_subrogation_not_flagged_when_waived():
    findings = _rule_ids(
        "Each party's insurer shall waive any right of subrogation against the "
        "other party."
    )
    assert "M_INSURANCE_SUBROGATION_WAIVER_MISSING_01" not in findings


def test_insurance_additional_insured_missing_rule():
    findings = _rule_ids(
        "Contractor shall maintain commercial general liability insurance in "
        "an amount not less than $1,000,000 per occurrence covering its "
        "operations under this services Agreement."
    )
    assert findings["M_INSURANCE_ADDITIONAL_INSURED_MISSING_01"].severity == Severity.LOW


def test_insurance_additional_insured_not_flagged_when_named():
    findings = _rule_ids(
        "Contractor's commercial general liability insurance policy shall name "
        "Owner as an additional insured."
    )
    assert "M_INSURANCE_ADDITIONAL_INSURED_MISSING_01" not in findings


def test_insurance_self_insurance_uncapped_rule():
    findings = _rule_ids(
        "Vendor may self-insure any of the coverages required herein, and such "
        "self-insurance is permitted without a minimum net worth requirement."
    )
    assert findings["H_INSURANCE_SELF_INSURANCE_UNCAPPED_01"].severity == Severity.MEDIUM


def test_insurance_self_insurance_not_flagged_when_third_party_required():
    findings = _rule_ids(
        "Vendor shall maintain commercial general liability insurance through a "
        "licensed third-party insurer meeting the minimum coverage requirements "
        "set forth in Exhibit B."
    )
    assert "H_INSURANCE_SELF_INSURANCE_UNCAPPED_01" not in findings


def test_insurance_notice_cancellation_short_rule():
    findings = _rule_ids(
        "Each party's insurance policy may be cancelled without notice to the "
        "other party."
    )
    assert findings["M_INSURANCE_NOTICE_CANCELLATION_SHORT_01"].severity == Severity.MEDIUM


def test_insurance_notice_cancellation_not_flagged_with_notice_required():
    findings = _rule_ids(
        "The insurer shall provide at least 30 days written notice to the other "
        "party prior to cancellation of the policy."
    )
    assert "M_INSURANCE_NOTICE_CANCELLATION_SHORT_01" not in findings


def test_insurance_deductible_uncapped_rule():
    findings = _rule_ids(
        "Coverage may be subject to a deductible in any amount with no maximum "
        "specified."
    )
    assert findings["M_INSURANCE_DEDUCTIBLE_UNCAPPED_01"].severity == Severity.LOW


# -- Lending / financial services --

def test_lending_tila_disclosure_missing_rule():
    findings = _rule_ids(
        "This is a consumer loan for personal, family, and household purposes "
        "in the original principal amount stated above. Borrower shall repay "
        "the loan in accordance with the payment schedule set forth herein."
    )
    assert findings["M_LENDING_TILA_DISCLOSURE_MISSING_01"].severity == Severity.MEDIUM


def test_lending_tila_disclosure_not_flagged_when_referenced():
    findings = _rule_ids(
        "This consumer loan is accompanied by the Truth in Lending Act "
        "disclosure statement showing the APR and finance charge."
    )
    assert "M_LENDING_TILA_DISCLOSURE_MISSING_01" not in findings


def test_lending_balloon_payment_rule():
    findings = _rule_ids("This Note includes a balloon payment due in full at maturity.")
    assert findings["H_LENDING_BALLOON_PAYMENT_01"].severity == Severity.MEDIUM


def test_lending_balloon_not_flagged_when_fully_amortizing():
    findings = _rule_ids(
        "This Note shall be repaid in 60 equal monthly installments of "
        "principal and interest, fully amortizing over the loan term."
    )
    assert "H_LENDING_BALLOON_PAYMENT_01" not in findings


def test_lending_cross_collateralization_rule():
    findings = _rule_ids(
        "The collateral securing this loan shall be cross-collateralized with "
        "all other loans and obligations of Borrower to Lender."
    )
    assert findings["M_LENDING_CROSS_COLLATERAL_01"].severity == Severity.LOW


def test_lending_default_interest_punitive_rule():
    findings = _rule_ids(
        "Upon any default, the interest rate shall increase to the default "
        "rate, an additional 10% per annum above the note rate."
    )
    assert findings["H_LENDING_DEFAULT_INTEREST_PUNITIVE_01"].severity == Severity.MEDIUM


def test_lending_default_interest_not_flagged_when_fixed():
    findings = _rule_ids(
        "The interest rate under this Note shall remain fixed at 6% per annum "
        "regardless of any default."
    )
    assert "H_LENDING_DEFAULT_INTEREST_PUNITIVE_01" not in findings


def test_lending_financial_covenant_vague_rule():
    findings = _rule_ids(
        "Borrower shall maintain a debt service coverage ratio satisfactory to "
        "Lender, and any failure shall immediately be in default without cure."
    )
    assert findings["M_LENDING_FINANCIAL_COVENANT_VAGUE_01"].severity == Severity.MEDIUM


def test_lending_blanket_lien_all_assets_rule():
    findings = _rule_ids(
        "Borrower grants Lender a security interest in all assets of Borrower, "
        "now owned or hereafter acquired."
    )
    assert findings["H_LENDING_PERSONAL_PROPERTY_LIEN_ALL_ASSETS_01"].severity == Severity.HIGH


def test_lending_blanket_lien_not_flagged_when_scoped():
    findings = _rule_ids(
        "Borrower grants Lender a security interest limited solely to the "
        "specific equipment identified in Schedule A."
    )
    assert "H_LENDING_PERSONAL_PROPERTY_LIEN_ALL_ASSETS_01" not in findings


def test_lending_ach_autodebit_unlimited_rule():
    findings = _rule_ids(
        "Borrower authorizes Lender to initiate ACH debits from Borrower's "
        "account for any amount owed under this Note."
    )
    assert findings["M_LENDING_ACH_AUTODEBIT_UNLIMITED_01"].severity == Severity.MEDIUM


# -- Government contracts --

def test_govcon_termination_convenience_no_comp_rule():
    findings = _rule_ids(
        "This Contract may be subject to a termination for convenience by the "
        "Government, and Contractor shall have no right to compensation for "
        "costs incurred."
    )
    assert findings["H_GOVCON_TERMINATION_CONVENIENCE_NO_COMP_01"].severity == Severity.LOW


def test_govcon_termination_convenience_not_flagged_with_settlement_terms():
    findings = _rule_ids(
        "Upon a termination for convenience by the Government, Contractor may "
        "submit a settlement proposal for costs incurred plus a reasonable "
        "profit on completed work."
    )
    assert "H_GOVCON_TERMINATION_CONVENIENCE_NO_COMP_01" not in findings


def test_govcon_flowdown_missing_rule():
    findings = _rule_ids(
        "This subcontract is issued under a prime contract with the federal "
        "government, but no FAR or DFARS flow-down clauses are incorporated "
        "herein."
    )
    assert findings["M_GOVCON_FLOWDOWN_MISSING_01"].severity == Severity.MEDIUM


def test_govcon_flowdown_not_flagged_when_incorporated():
    findings = _rule_ids(
        "This subcontract, issued under the prime contract, incorporates by "
        "reference all applicable FAR flow-down clauses required by the prime "
        "contract."
    )
    assert "M_GOVCON_FLOWDOWN_MISSING_01" not in findings


def test_govcon_dcaa_audit_unlimited_rule():
    findings = _rule_ids(
        "The Government's authorized representatives shall have the right to "
        "audit Contractor's books and records at any time, with no limit on "
        "the audit period."
    )
    assert findings["M_GOVCON_DCAA_AUDIT_UNLIMITED_01"].severity == Severity.MEDIUM


def test_govcon_small_business_subk_plan_missing_rule():
    findings = _rule_ids(
        "Contractor shall comply with the small business subcontracting plan, "
        "which is to be provided under separate cover."
    )
    assert findings["M_GOVCON_SMALL_BUSINESS_SUBK_PLAN_MISSING_01"].severity == Severity.LOW


def test_govcon_changes_clause_unilateral_rule():
    findings = _rule_ids(
        "The Government may unilaterally change the scope of work pursuant to "
        "the changes clause, without an equitable adjustment to price or "
        "schedule."
    )
    assert findings["M_GOVCON_CHANGES_CLAUSE_UNILATERAL_01"].severity == Severity.MEDIUM


# -- Healthcare --

def test_healthcare_stark_kickback_risk_rule():
    findings = _rule_ids(
        "Physician's compensation under this Agreement shall be based on the "
        "volume of referrals made to the Hospital."
    )
    assert findings["H_HEALTHCARE_STARK_KICKBACK_RISK_01"].severity == Severity.CRITICAL


def test_healthcare_stark_kickback_not_flagged_with_fair_market_rate():
    findings = _rule_ids(
        "Physician's compensation under this Agreement shall be a fixed "
        "fair-market-value hourly rate, unrelated to the volume or value of "
        "any referrals."
    )
    assert "H_HEALTHCARE_STARK_KICKBACK_RISK_01" not in findings


def test_healthcare_credentialing_delay_rule():
    findings = _rule_ids(
        "Provider shall not be compensated for services rendered until "
        "Provider is fully credentialed by the Facility."
    )
    assert findings["M_HEALTHCARE_CREDENTIALING_DELAY_01"].severity == Severity.LOW


def test_healthcare_credentialing_not_flagged_with_timeline():
    findings = _rule_ids(
        "Provider's credentialing with the Facility shall be completed within "
        "30 days of the Effective Date, after which Provider shall be paid for "
        "services rendered."
    )
    assert "M_HEALTHCARE_CREDENTIALING_DELAY_01" not in findings


def test_healthcare_exclusive_dealing_rule():
    findings = _rule_ids(
        "Physician agrees to an exclusive arrangement and shall not provide "
        "services to any other hospital or facility for the duration of this "
        "Agreement."
    )
    assert findings["H_HEALTHCARE_EXCLUSIVE_DEALING_01"].severity == Severity.MEDIUM


def test_healthcare_termination_without_cause_short_rule():
    findings = _rule_ids(
        "Either party may terminate this Agreement without cause upon 10 days "
        "written notice."
    )
    assert findings["M_HEALTHCARE_TERMINATION_WITHOUT_CAUSE_SHORT_01"].severity == Severity.MEDIUM


def test_healthcare_licensure_rep_missing_rule():
    findings = _rule_ids(
        "Physician is a licensed physician who shall provide services under "
        "this Agreement at the Facility, in accordance with the schedule "
        "and scope of services set forth in Exhibit A."
    )
    assert findings["M_HEALTHCARE_LICENSURE_REP_MISSING_01"].severity == Severity.MEDIUM


def test_healthcare_licensure_rep_not_flagged_when_represented():
    findings = _rule_ids(
        "Physician, a licensed physician providing services at the Facility, "
        "represents and warrants that Physician remains licensed and is not "
        "excluded from any federal healthcare program."
    )
    assert "M_HEALTHCARE_LICENSURE_REP_MISSING_01" not in findings


def test_healthcare_patient_data_sale_rule():
    findings = _rule_ids(
        "Company may sell patient data collected through the platform to "
        "third-party data brokers."
    )
    assert findings["H_HEALTHCARE_PATIENT_DATA_SALE_01"].severity == Severity.HIGH


def test_healthcare_patient_data_not_flagged_when_restricted():
    findings = _rule_ids(
        "Patient data collected through the platform shall be used solely for "
        "treatment, payment, and healthcare operations, and shall never be "
        "sold to any third party."
    )
    assert "H_HEALTHCARE_PATIENT_DATA_SALE_01" not in findings


# -- IP licensing --

def test_iplicense_no_quality_control_rule():
    findings = _rule_ids(
        "Licensor hereby grants Licensee a trademark license to use the Mark, "
        "with no quality control standards imposed on Licensee's use."
    )
    assert findings["H_IPLICENSE_NO_QUALITY_CONTROL_01"].severity == Severity.MEDIUM


def test_iplicense_no_quality_control_not_flagged_when_present():
    findings = _rule_ids(
        "Licensor grants Licensee a trademark license to use the Mark, subject "
        "to the quality control standards set forth in Exhibit A, which "
        "Licensor may inspect for quality at any time."
    )
    assert "H_IPLICENSE_NO_QUALITY_CONTROL_01" not in findings


def test_iplicense_royalty_audit_missing_rule():
    findings = _rule_ids(
        "Licensee shall pay Licensor a royalty of 5% of Net Sales, calculated "
        "and reported quarterly."
    )
    assert findings["M_IPLICENSE_ROYALTY_AUDIT_MISSING_01"].severity == Severity.LOW


def test_iplicense_royalty_audit_not_flagged_when_present():
    findings = _rule_ids(
        "Licensee shall pay Licensor a royalty of 5% of Net Sales, and Licensor "
        "may audit Licensee's royalty records upon reasonable notice."
    )
    assert "M_IPLICENSE_ROYALTY_AUDIT_MISSING_01" not in findings


def test_iplicense_perpetual_exclusive_no_termination_rule():
    findings = _rule_ids(
        "Licensor grants Licensee a perpetual, exclusive license to the "
        "Licensed IP, and Licensor shall have no right to terminate this "
        "license."
    )
    assert findings["H_IPLICENSE_PERPETUAL_EXCLUSIVE_NO_TERMINATION_01"].severity == Severity.HIGH


def test_iplicense_perpetual_exclusive_not_flagged_with_termination_right():
    findings = _rule_ids(
        "Licensor grants Licensee a five-year exclusive license to the "
        "Licensed IP, terminable by Licensor for uncured material breach."
    )
    assert "H_IPLICENSE_PERPETUAL_EXCLUSIVE_NO_TERMINATION_01" not in findings


def test_iplicense_unrestricted_sublicense_rule():
    findings = _rule_ids(
        "Licensee may sublicense the Licensed IP to any third party without "
        "the Licensor's consent."
    )
    assert findings["M_IPLICENSE_SUBLICENSE_UNRESTRICTED_01"].severity == Severity.MEDIUM


def test_iplicense_improvements_assigned_rule():
    findings = _rule_ids(
        "Any improvements or modifications developed by Licensee shall be "
        "owned by and hereby assigns to Licensor."
    )
    assert findings["H_IPLICENSE_IMPROVEMENTS_ASSIGNED_01"].severity == Severity.HIGH


def test_iplicense_termination_no_winddown_rule():
    findings = _rule_ids(
        "Upon termination of this license, Licensee shall immediately cease "
        "all use of the Licensed IP."
    )
    assert findings["M_IPLICENSE_TERMINATION_NO_WINDDOWN_01"].severity == Severity.MEDIUM


# -- Franchise (deeper coverage) --

def test_franchise_encroachment_rule():
    findings = _rule_ids(
        "Franchisor may open additional units within Franchisee's territory, "
        "and Franchisee shall have no right to object to such encroachment."
    )
    assert findings["H_FRANCHISE_ENCROACHMENT_01"].severity == Severity.LOW


def test_franchise_encroachment_not_flagged_when_prohibited():
    findings = _rule_ids(
        "Franchisor shall not encroach upon Franchisee's designated territory, "
        "and any encroachment by Franchisor within the territory is expressly "
        "prohibited under this Agreement."
    )
    assert "H_FRANCHISE_ENCROACHMENT_01" not in findings


def test_franchise_royalty_audit_one_sided_rule():
    findings = _rule_ids(
        "Franchisor may audit Franchisee's royalty reports at any time, and "
        "Franchisor's determination of any discrepancy shall be final and "
        "binding."
    )
    assert findings["M_FRANCHISE_ROYALTY_AUDIT_ONE_SIDED_01"].severity == Severity.MEDIUM


def test_franchise_personal_guaranty_uncapped_rule():
    findings = _rule_ids(
        "The principal of Franchisee shall personally guarantee all "
        "obligations of Franchisee under this franchise Agreement."
    )
    assert findings["H_FRANCHISE_PERSONAL_GUARANTY_UNCAPPED_01"].severity == Severity.CRITICAL


def test_franchise_personal_guaranty_not_flagged_when_absent():
    findings = _rule_ids(
        "Franchisee shall operate the franchise as a corporate entity, and the "
        "Franchise Agreement contains no personal guaranty requirement of any "
        "kind."
    )
    assert "H_FRANCHISE_PERSONAL_GUARANTY_UNCAPPED_01" not in findings


def test_franchise_noncompete_post_term_broad_rule():
    findings = _rule_ids(
        "Following post-termination of this Agreement, Franchisee agrees to a "
        "non-compete covering a 50 mile radius for five years."
    )
    assert findings["M_FRANCHISE_NONCOMPETE_POST_TERM_BROAD_01"].severity == Severity.MEDIUM


def test_franchise_transfer_fee_uncapped_rule():
    findings = _rule_ids(
        "Any transfer of the franchise shall be subject to a transfer fee "
        "payable to Franchisor."
    )
    assert findings["M_FRANCHISE_TRANSFER_FEE_UNCAPPED_01"].severity == Severity.LOW


# -- Settlement (deeper coverage) --

def test_settlement_structured_payment_acceleration_rule():
    findings = _rule_ids(
        "If any settlement payment is missed, the entire remaining balance "
        "shall immediately accelerate and become due."
    )
    assert findings["H_SETTLEMENT_STRUCTURED_PAYMENT_ACCELERATION_01"].severity == Severity.MEDIUM


def test_settlement_tax_characterization_missing_rule():
    findings = _rule_ids(
        "The settlement amount shall be paid by Defendant to Plaintiff within "
        "30 days of execution of this Agreement."
    )
    assert findings["M_SETTLEMENT_TAX_CHARACTERIZATION_MISSING_01"].severity == Severity.LOW


def test_settlement_tax_characterization_not_flagged_when_allocated():
    findings = _rule_ids(
        "The settlement amount shall be allocated for tax purposes as "
        "follows: 50% as wages and 50% as non-wage damages, characterized "
        "accordingly on IRS Form 1099 and W-2 as applicable."
    )
    assert "M_SETTLEMENT_TAX_CHARACTERIZATION_MISSING_01" not in findings


def test_settlement_mutual_release_asymmetric_rule():
    findings = _rule_ids(
        "This is a mutual release. Releasor releases Releasee from any and "
        "all claims arising out of the dispute."
    )
    assert findings["H_SETTLEMENT_MUTUAL_RELEASE_ASYMMETRIC_01"].severity == Severity.HIGH


def test_settlement_mutual_release_not_flagged_when_truly_mutual():
    findings = _rule_ids(
        "This is a mutual release. Releasor releases Releasee, and Releasee "
        "releases Releasor, from any and all claims arising out of the "
        "dispute."
    )
    assert "H_SETTLEMENT_MUTUAL_RELEASE_ASYMMETRIC_01" not in findings


def test_settlement_nondisparagement_perpetual_rule():
    findings = _rule_ids(
        "Each party agrees not to disparage the other party, and this "
        "non-disparagement obligation shall continue in perpetuity."
    )
    assert findings["M_SETTLEMENT_NONDISPARAGEMENT_PERPETUAL_01"].severity == Severity.HIGH


def test_settlement_enforcement_fee_shift_rule():
    findings = _rule_ids(
        "If Plaintiff must enforce this settlement, Plaintiff shall be "
        "entitled to recover its attorneys' fees incurred."
    )
    assert findings["M_SETTLEMENT_ENFORCEMENT_FEE_SHIFT_01"].severity == Severity.LOW


# -- Employment (deeper coverage) --

def test_employ_arbitration_class_waiver_rule():
    findings = _rule_ids(
        "Employee agrees to mandatory arbitration of any dispute, and "
        "Employee agrees to a class action waiver of any right to bring or "
        "participate in a collective action."
    )
    assert findings["M_EMPLOY_ARBITRATION_CLASS_WAIVER_01"].severity == Severity.MEDIUM


def test_employ_commission_clawback_rule():
    findings = _rule_ids(
        "The Company may claw back any commission previously paid to Employee "
        "if the underlying account becomes unprofitable at any time."
    )
    assert findings["H_EMPLOY_COMMISSION_CLAWBACK_01"].severity == Severity.HIGH


def test_employ_garden_leave_unpaid_rule():
    findings = _rule_ids(
        "During the garden leave notice period, Employee shall not work for "
        "any other employer and shall receive compensation without pay."
    )
    assert findings["M_EMPLOY_GARDEN_LEAVE_UNPAID_01"].severity == Severity.MEDIUM


def test_employ_forced_stock_repurchase_rule():
    findings = _rule_ids(
        "Upon termination, the Company may repurchase Employee's vested "
        "shares at the original purchase price."
    )
    assert findings["H_EMPLOY_FORCED_STOCK_REPURCHASE_01"].severity == Severity.HIGH


def test_employ_relocation_mandatory_rule():
    findings = _rule_ids(
        "The Company may require Employee to relocate to any location at the "
        "Company's sole discretion."
    )
    assert findings["M_EMPLOY_RELOCATION_MANDATORY_01"].severity == Severity.MEDIUM


def test_employ_pto_forfeiture_rule():
    findings = _rule_ids(
        "Any accrued vacation not used by the end of the year shall be "
        "forfeited, with no payout upon termination."
    )
    assert findings["M_EMPLOY_PTO_FORFEITURE_01"].severity == Severity.LOW


# -- M&A / partnership (deeper coverage) --

def test_ma_mac_clause_broad_rule():
    findings = _rule_ids(
        "A material adverse effect shall include, but not be limited to, any "
        "change, event, or circumstance affecting the Company or the industry "
        "generally."
    )
    assert findings["H_MA_MAC_CLAUSE_BROAD_01"].severity == Severity.HIGH


def test_ma_mac_clause_not_flagged_when_narrowly_defined():
    findings = _rule_ids(
        "A material adverse effect means a change that has a disproportionate "
        "effect on the Company relative to other companies in its industry, "
        "excluding general economic or industry-wide conditions."
    )
    assert "H_MA_MAC_CLAUSE_BROAD_01" not in findings


def test_ma_working_capital_adjustment_undefined_rule():
    findings = _rule_ids(
        "The purchase price shall be subject to a working capital adjustment "
        "mechanism, the calculation of which is to be mutually agreed by the "
        "parties."
    )
    assert findings["M_MA_WORKING_CAPITAL_ADJUSTMENT_UNDEFINED_01"].severity == Severity.LOW


def test_ma_noncompete_seller_indefinite_rule():
    findings = _rule_ids(
        "Seller agrees to a non-compete restricting Seller from competing "
        "with the Company's business, which non-compete shall continue "
        "indefinitely."
    )
    assert findings["H_MA_NONCOMPETE_SELLER_INDEFINITE_01"].severity == Severity.MEDIUM


def test_ma_drag_along_no_minimum_price_rule():
    findings = _rule_ids(
        "If holders of a majority of the shares approve a sale of the "
        "Company, all other shareholders shall be subject to a drag-along "
        "right at any price with no minimum price."
    )
    assert findings["M_MA_DRAG_ALONG_NO_MINIMUM_PRICE_01"].severity == Severity.MEDIUM


def test_ma_escrow_release_sole_discretion_rule():
    findings = _rule_ids(
        "The Escrow Amount shall be released to Seller subject to Buyer's "
        "sole discretion."
    )
    assert findings["H_MA_ESCROW_RELEASE_SOLE_DISCRETION_01"].severity == Severity.HIGH


def test_ma_escrow_release_not_flagged_with_fixed_schedule():
    findings = _rule_ids(
        "The Escrow Amount shall be released to Seller automatically on the "
        "18-month anniversary of Closing, less any pending indemnification "
        "claims."
    )
    assert "H_MA_ESCROW_RELEASE_SOLE_DISCRETION_01" not in findings


def test_partnership_fiduciary_duty_waiver_rule():
    findings = _rule_ids(
        "The Managing Member's fiduciary duties to the Company and its "
        "Members are hereby waived to the fullest extent permitted by law."
    )
    assert findings["M_PARTNERSHIP_FIDUCIARY_DUTY_WAIVER_01"].severity == Severity.LOW


# -- Construction (deeper coverage) --

def test_constr_no_damages_for_delay_rule():
    findings = _rule_ids(
        "Contractor agrees that there shall be no damages for delay of any "
        "kind, regardless of cause."
    )
    assert findings["H_CONSTR_NO_DAMAGES_FOR_DELAY_01"].severity == Severity.MEDIUM


def test_constr_change_order_unilateral_pricing_rule():
    findings = _rule_ids(
        "For any change order, the Owner shall determine the price of the "
        "additional work in Owner's sole discretion."
    )
    assert findings["M_CONSTR_CHANGE_ORDER_UNILATERAL_PRICING_01"].severity == Severity.MEDIUM


def test_constr_indemnity_sole_negligence_rule():
    findings = _rule_ids(
        "Contractor shall indemnify Owner from any claim, including claims "
        "arising from Owner's sole negligence."
    )
    assert findings["H_CONSTR_INDEMNITY_SOLE_NEGLIGENCE_01"].severity == Severity.MEDIUM


def test_constr_indemnity_not_flagged_when_negligence_excluded():
    findings = _rule_ids(
        "Contractor shall indemnify Owner for claims arising from "
        "Contractor's negligence, excluding claims arising from Owner's own "
        "sole negligence."
    )
    assert "H_CONSTR_INDEMNITY_SOLE_NEGLIGENCE_01" not in findings


def test_constr_warranty_period_extended_rule():
    findings = _rule_ids(
        "Contractor warrants its work for a warranty period of five years "
        "from the date of substantial completion."
    )
    assert findings["M_CONSTR_WARRANTY_PERIOD_EXTENDED_01"].severity == Severity.MEDIUM


# -- Messy-formatting tolerance spot checks (extra whitespace / line breaks,
# matching the same tolerance discipline used for the original 117 rules) --

def test_franchise_personal_guaranty_tolerates_messy_whitespace():
    findings = _rule_ids(
        "The   principal  of Franchisee\nshall personally    guarantee all\n"
        "obligations of Franchisee under this franchise   Agreement."
    )
    assert findings["H_FRANCHISE_PERSONAL_GUARANTY_UNCAPPED_01"].severity == Severity.CRITICAL


def test_healthcare_stark_kickback_tolerates_messy_whitespace():
    findings = _rule_ids(
        "Physician's   compensation\nunder this Agreement shall be based on "
        "the volume  of\nreferrals made to the Hospital."
    )
    assert findings["H_HEALTHCARE_STARK_KICKBACK_RISK_01"].severity == Severity.CRITICAL


def test_lending_blanket_lien_tolerates_hyphenated_line_break():
    findings = _rule_ids(
        "Borrower grants Lender a security interest in all assets of\n"
        "Borrower, now owned or hereafter acquired."
    )
    assert findings["H_LENDING_PERSONAL_PROPERTY_LIEN_ALL_ASSETS_01"].severity == Severity.HIGH
