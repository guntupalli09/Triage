"""Regression family for Candidate 2 defects #2 (time normalization) and
#3 (negated obligation) in data_security_policy_engine.
"""
import data_security_policy_engine as dse


BASE_POLICY_KWARGS = dict(
    contract_side="sell_side", escalation_approval_authority=None, fallback_text=None,
    require_processor_role=False, prohibit_unrestricted_subprocessors=False,
    require_subprocessor_notice_or_consent="not_required",
    require_scc_or_adequacy_for_transfers=False, prohibit_data_transfer=False,
    require_deletion_or_return=False, max_retention_days=None, require_audit_rights=False,
    require_named_security_certification=False, require_cooperation_obligation=False,
    require_confidentiality_of_personal_data=False, require_data_residency=False,
    require_fixed_breach_notification_period=False, require_international_transfer_safeguard=False,
    required_data_residency_regions_json=[],
)


class FakePolicy:
    def __init__(self, **overrides):
        kwargs = dict(BASE_POLICY_KWARGS)
        kwargs.update(overrides)
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.max_breach_notification_hours = overrides.get("max_breach_notification_hours", 72)
        self.acceptable_max_breach_notification_hours = overrides.get("acceptable_max_breach_notification_hours", 72)
        self.negotiate_max_breach_notification_hours = overrides.get("negotiate_max_breach_notification_hours", 96)
        self.preferred_breach_notification_hours = overrides.get("preferred_breach_notification_hours", 48)


def _evaluate(text, **policy_overrides):
    facts = dse.extract_data_security_facts(text)
    return facts, dse.evaluate_data_security_policy(facts, FakePolicy(**policy_overrides))


# --- Time normalization ------------------------------------------------------

def test_positive_control_hours_still_works():
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall notify Customer of any data breach within 48 hours of becoming aware of it."
    )
    assert facts.breach_notification_hours == 48
    assert decision.state == dse.ACCEPT


def test_digit_days_normalized_to_hours():
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall notify Customer of any data breach within 30 days of becoming aware of it."
    )
    assert facts.breach_notification_hours == 720
    assert decision.state != dse.ACCEPT


def test_spelled_out_days_normalized_same_as_digits():
    """Paraphrase: spelled-out number, not the digit form -- proves the
    fix generalizes past the exact failing sentence."""
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall notify Customer of any data breach within thirty days of becoming "
        "aware of it."
    )
    assert facts.breach_notification_hours == 720
    assert decision.state != dse.ACCEPT


def test_calendar_days_explicit_word_also_normalized():
    facts, _ = _evaluate(
        "11. Data Protection. Vendor shall notify Customer of any data breach within 10 calendar days of "
        "becoming aware of it."
    )
    assert facts.breach_notification_hours == 240


def test_business_days_fails_closed_not_manufactured():
    """Ambiguous unit -- must NOT be silently converted (e.g. treated as
    either 3*24=72 hours, which would coincidentally look compliant, or
    ignored, which would look absent). Must force review."""
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall notify Customer of any data breach within 3 business days of "
        "becoming aware of it."
    )
    assert facts.breach_notification_hours is None
    assert facts.breach_notification_ambiguous_unit is True
    assert decision.state == dse.REQUIRES_REVIEW


def test_business_days_spelled_out_also_ambiguous():
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall notify Customer of any data breach within three business days of "
        "becoming aware of it."
    )
    assert facts.breach_notification_ambiguous_unit is True
    assert decision.state == dse.REQUIRES_REVIEW


def test_near_miss_days_word_inside_unrelated_phrase_not_misparsed():
    """Near-miss: the word 'days' appears near the breach anchor but not
    in a notification-timing construct at all -- must not be
    misinterpreted as a 0-day or otherwise fabricated commitment."""
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall investigate any data breach and, in the days following discovery, "
        "shall cooperate with Customer's own investigation."
    )
    assert facts.breach_notification_hours is None
    assert facts.breach_notification_ambiguous_unit is False


# --- Negated obligation -------------------------------------------------------

def test_positive_control_ordinary_obligation_not_flagged_as_negated():
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall notify Customer of any data breach within 48 hours."
    )
    assert facts.breach_notification_explicitly_disclaimed is False


def test_negation_shall_have_no_obligation():
    facts, decision = _evaluate(
        "11. Miscellaneous. Vendor shall have no obligation to notify Customer of any personal data breach "
        "under this Agreement."
    )
    assert facts.breach_notification_explicitly_disclaimed is True
    assert decision.state == dse.MUST_REDLINE


def test_negation_paraphrase_shall_not_be_required_to_notify():
    """Paraphrase: different negation verb phrase entirely."""
    facts, decision = _evaluate(
        "11. Miscellaneous. Vendor shall not be required to notify Customer of any security incident."
    )
    assert facts.breach_notification_explicitly_disclaimed is True
    assert decision.state == dse.MUST_REDLINE


def test_negation_paraphrase_under_no_obligation():
    facts, decision = _evaluate(
        "11. Miscellaneous. Vendor is under no obligation to notify Customer of any data breach affecting "
        "personal data."
    )
    assert facts.breach_notification_explicitly_disclaimed is True


def test_negation_preceding_the_anchor_word_order():
    """Direct proof of the window-direction masking sub-defect: the
    negation verb phrase precedes the anchor phrase in natural sentence
    order -- must still be caught."""
    facts, decision = _evaluate(
        "This Agreement addresses several topics. Vendor will not notify Customer of any personal data "
        "breach, regardless of severity."
    )
    assert facts.breach_notification_explicitly_disclaimed is True


def test_ambiguous_form_negation_of_unrelated_obligation_not_flagged():
    """Negative control: negating a DIFFERENT obligation entirely (not
    notification) must not be misread as disclaiming notification."""
    facts, decision = _evaluate(
        "11. Data Protection. Vendor shall have no obligation to indemnify Customer for a data breach caused "
        "by Customer's own negligence. Vendor shall notify Customer of any data breach within 48 hours."
    )
    assert facts.breach_notification_explicitly_disclaimed is False
    assert facts.breach_notification_hours == 48
