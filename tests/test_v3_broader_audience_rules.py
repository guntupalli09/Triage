"""Regression tests for v3.0 broader-audience rule coverage."""

from collections import Counter

from rules_engine import RuleEngine, Severity


def _rule_ids(text: str):
    return {f.rule_id: f for f in RuleEngine().analyze(text)["findings"]}


def test_v3_rule_inventory_counts_and_version():
    engine = RuleEngine()
    counts = Counter(rule.severity.value for rule in engine.rules)

    assert engine.version == "5.0.0"
    # 80 rules through v4.0 (see rules/version.json) + 11 rules added in the
    # v5.0 independent-audit hardening pass: H_LOL_NO_CARVEOUT_01,
    # H_INDEM_SCOPE_NARROW_01, M_DPA_MISSING_01, M_BAA_MISSING_01,
    # M_SUBPROCESSOR_MISSING_01, M_AUDIT_RIGHTS_CUSTOMER_01,
    # M_DELETION_CERT_MISSING_01, M_SLA_REMEDY_EXCLUSIVITY_01,
    # M_INSURANCE_MINIMUM_MISSING_01, M_REG_RESPONSIBILITY_UNALLOCATED_01,
    # M_DATA_RETURN_CONDITIONAL_01.
    assert len(engine.rules) == 91
    # 5 rules raised to the new CRITICAL tier (H_ASYMMETRIC_LIABILITY_01,
    # H_LOL_NO_CARVEOUT_01, H_PERSONAL_01, H_DATA_PRIVACY_01,
    # H_AI_TRAINING_01); M_BREACH_NOTIFY_01 raised Medium -> High.
    assert counts == {"critical": 5, "high": 22, "medium": 53, "low": 11}


def test_high_stored_card_authorization_rule():
    findings = _rule_ids(
        "You authorize us to store your payment method and automatically charge your credit card "
        "for recurring fees and future charges without further authorization."
    )

    assert findings["H_CARD_AUTH_01"].severity == Severity.HIGH


def test_high_content_license_rule():
    findings = _rule_ids(
        "By uploading user content, photos, reviews, or your likeness, you grant us a perpetual, "
        "worldwide, royalty-free, sublicensable license."
    )

    assert findings["H_CONTENT_LICENSE_01"].severity == Severity.HIGH


def test_high_wage_deduction_rule():
    findings = _rule_ids(
        "The platform may withhold payouts, apply chargebacks, or offset earnings and invoice amounts "
        "in its discretion."
    )

    assert findings["H_WAGE_DEDUCTION_01"].severity == Severity.HIGH


def test_high_worker_classification_rule():
    findings = _rule_ids(
        "Contractor is an independent contractor and not an employee. Contractor is responsible for all "
        "tax withholding and receives no benefits."
    )

    assert findings["H_CLASSIFICATION_01"].severity == Severity.HIGH


def test_medium_refund_and_cancellation_rules():
    findings = _rule_ids(
        "All sales final. No refunds will be provided. Cancellation within 48 hours is subject to a fee."
    )

    assert findings["M_REFUND_01"].severity == Severity.MEDIUM
    assert findings["M_CANCEL_FEE_01"].severity == Severity.MEDIUM


def test_medium_account_suspension_and_privacy_sharing_rules():
    findings = _rule_ids(
        "We may suspend your account or disable access to the service without notice and for any reason. "
        "We may share personal information with third parties and marketing partners."
    )

    assert findings["M_ACCOUNT_SUSPEND_01"].severity == Severity.MEDIUM
    assert findings["M_PRIVACY_SHARING_01"].severity == Severity.MEDIUM


def test_medium_non_disparagement_and_photo_release_rules():
    findings = _rule_ids(
        "Customer shall not disparage the company or publish any negative review. Attendee consents to "
        "photo, video, voice, name, and likeness use for marketing and promotional materials."
    )

    assert findings["M_NONDISPARAGE_01"].severity == Severity.MEDIUM
    assert findings["M_PHOTO_RELEASE_01"].severity == Severity.MEDIUM


def test_low_electronic_notice_and_communications_rules():
    findings = _rule_ids(
        "Electronic notice by email or portal is deemed received when sent. You consent to marketing SMS, "
        "texts, automated calls, and promotional email messages."
    )

    assert findings["L_ELECTRONIC_NOTICE_01"].severity == Severity.LOW
    assert findings["L_COMMUNICATION_CONSENT_01"].severity == Severity.LOW
