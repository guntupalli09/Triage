"""Unit tests for playbook/topic_binding.py."""
from types import SimpleNamespace

from playbook.topic_binding import derive_policy_topic, bind


def test_derive_policy_topic_matches_main_py_convention():
    assert derive_policy_topic("H_INDEM_01") == "INDEM"
    assert derive_policy_topic("M_ASYMMETRIC_LIABILITY_02") == "ASYMMETRIC_LIABILITY"
    assert derive_policy_topic("") == ""
    assert derive_policy_topic("NOUNDERSCORE") == "NOUNDERSCORE"


def _fake_rule(id_, topic, bound_ids=None):
    return SimpleNamespace(id=id_, policy_topic=topic, bound_rule_ids_json=bound_ids)


def test_bind_prefers_explicit_rule_id_binding_over_topic():
    topic_rule = _fake_rule(1, "INDEM")
    explicit_rule = _fake_rule(2, "OTHER_TOPIC", bound_ids=["H_INDEM_01"])
    effective = {"INDEM": topic_rule, "OTHER_TOPIC": explicit_rule}

    finding = SimpleNamespace(rule_id="H_INDEM_01")
    assert bind(finding, effective) is explicit_rule


def test_bind_falls_back_to_topic_when_no_explicit_binding():
    topic_rule = _fake_rule(1, "INDEM")
    effective = {"INDEM": topic_rule}
    finding = SimpleNamespace(rule_id="H_INDEM_02")
    assert bind(finding, effective) is topic_rule


def test_bind_returns_none_for_unbound_topic():
    effective = {"INDEM": _fake_rule(1, "INDEM")}
    finding = SimpleNamespace(rule_id="L_UNKNOWN_TOPIC_01")
    assert bind(finding, effective) is None


def test_bind_works_with_dict_findings():
    topic_rule = _fake_rule(1, "LOL")
    effective = {"LOL": topic_rule}
    finding = {"rule_id": "M_LOL_01"}
    assert bind(finding, effective) is topic_rule
