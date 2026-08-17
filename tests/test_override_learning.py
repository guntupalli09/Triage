"""
Override-pattern detection (override_learning.py). Covers: extracting
occurrences from Contract.review_decisions_json, clustering by (rule_id,
original_recommendation, overriding action), the distinct-contract
threshold, segment_context inference, and that non-override decisions
(accepted-as-recommended, or non-governance findings) never contribute.
"""
import os
from types import SimpleNamespace

os.environ.setdefault("DEV_MODE", "true")

import pytest

import override_learning as ol


def _contract(contract_id, findings, decisions, business_unit=None, customer_type=None, deal_value=None):
    return SimpleNamespace(
        id=contract_id, findings_json=findings, review_decisions_json=decisions,
        review_business_unit=business_unit, review_customer_type=customer_type, review_deal_value=deal_value,
    )


def _governance_finding(clause_type="limitation_of_liability"):
    return {"rule_id": "LOL-ESCALATE-001", "clause_type": clause_type, "finding_type": "policy_decision"}


def _override_entry(action="accepted"):
    return {
        "action": action, "rule_id": "LOL-ESCALATE-001", "policy_original_recommendation": "ESCALATE",
        "policy_exception": True, "reason": "Client relationship exception", "decided_at": "2026-01-01T00:00:00",
        "decided_by": "Jane Attorney",
    }


class TestExtractOverrideOccurrences:
    def test_extracts_flagged_exception_entries(self):
        contract = _contract(1, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()})
        occurrences = ol.extract_override_occurrences(contract)
        assert len(occurrences) == 1
        o = occurrences[0]
        assert o.contract_id == 1
        assert o.rule_id == "LOL-ESCALATE-001"
        assert o.clause_type == "limitation_of_liability"
        assert o.original_recommendation == "ESCALATE"
        assert o.action == "accepted"

    def test_ignores_decisions_without_policy_exception_flag(self):
        entry = {"action": "accepted", "rule_id": "LOL-ESCALATE-001"}  # no policy_exception
        contract = _contract(1, [_governance_finding()], {"LOL-ESCALATE-001#0": entry})
        assert ol.extract_override_occurrences(contract) == []

    def test_ignores_conforming_accept_of_a_non_governance_finding(self):
        entry = {"action": "accepted", "rule_id": "SOME-RULE", "policy_exception": False}
        contract = _contract(1, [{"rule_id": "SOME-RULE", "clause_type": "termination"}], {"SOME-RULE#0": entry})
        assert ol.extract_override_occurrences(contract) == []

    def test_carries_segment_context_from_contract(self):
        contract = _contract(
            1, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()},
            business_unit="Enterprise", customer_type="Strategic", deal_value=500000.0,
        )
        o = ol.extract_override_occurrences(contract)[0]
        assert o.business_unit == "Enterprise"
        assert o.customer_type == "Strategic"
        assert o.deal_value == 500000.0


class TestDetectOverridePatterns:
    def test_below_threshold_is_not_a_pattern(self):
        contracts = [
            _contract(1, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()}),
            _contract(2, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()}),
        ]
        assert ol.detect_override_patterns(contracts, min_occurrences=3) == []

    def test_meeting_threshold_across_distinct_contracts_is_a_pattern(self):
        contracts = [
            _contract(i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()})
            for i in range(1, 4)
        ]
        patterns = ol.detect_override_patterns(contracts, min_occurrences=3)
        assert len(patterns) == 1
        p = patterns[0]
        assert p.rule_id == "LOL-ESCALATE-001"
        assert p.original_recommendation == "ESCALATE"
        assert p.overriding_action == "accepted"
        assert p.count == 3
        assert p.contract_ids == [1, 2, 3]

    def test_multiple_overrides_on_same_contract_do_not_inflate_count(self):
        """Repeated occurrences of the SAME rule/action pair on one
        contract (e.g. the same fee-shifting clause appearing twice) must
        never manufacture a multi-contract pattern on their own — count
        is distinct contract_ids, not raw occurrence rows."""
        decisions = {
            "LOL-ESCALATE-001#0": _override_entry(), "LOL-ESCALATE-001#1": _override_entry(),
        }
        contracts = [_contract(1, [_governance_finding(), _governance_finding()], decisions)]
        patterns = ol.detect_override_patterns(contracts, min_occurrences=2)
        assert patterns == []  # only 1 distinct contract, threshold is 2

    def test_different_overriding_actions_form_separate_clusters(self):
        contracts_accept = [
            _contract(i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry("accepted")})
            for i in range(1, 4)
        ]
        contracts_edit = [
            _contract(i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry("edited")})
            for i in range(10, 12)
        ]
        patterns = ol.detect_override_patterns(contracts_accept + contracts_edit, min_occurrences=3)
        assert len(patterns) == 1
        assert patterns[0].overriding_action == "accepted"

    def test_segment_context_set_when_shared_across_cluster(self):
        contracts = [
            _contract(
                i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()},
                business_unit="Enterprise", customer_type=None,
            )
            for i in range(1, 4)
        ]
        patterns = ol.detect_override_patterns(contracts, min_occurrences=3)
        assert patterns[0].segment_context == {"business_unit": "Enterprise", "customer_type": None}

    def test_segment_context_none_when_mixed(self):
        contracts = [
            _contract(1, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()}, business_unit="Enterprise"),
            _contract(2, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()}, business_unit="SMB"),
            _contract(3, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()}, business_unit="SMB"),
        ]
        patterns = ol.detect_override_patterns(contracts, min_occurrences=3)
        assert patterns[0].segment_context is None

    def test_sorted_by_count_descending(self):
        big_cluster = [
            _contract(i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()})
            for i in range(1, 5)
        ]
        small_finding = {"rule_id": "TERM-ESC-002", "clause_type": "termination"}
        small_entry = {
            "action": "accepted", "rule_id": "TERM-ESC-002", "policy_original_recommendation": "ESCALATE",
            "policy_exception": True,
        }
        small_cluster = [
            _contract(100 + i, [small_finding], {"TERM-ESC-002#0": small_entry})
            for i in range(3)
        ]
        patterns = ol.detect_override_patterns(big_cluster + small_cluster, min_occurrences=3)
        assert [p.rule_id for p in patterns] == ["LOL-ESCALATE-001", "TERM-ESC-002"]

    def test_default_min_occurrences_is_three(self):
        contracts = [
            _contract(i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()})
            for i in range(1, 3)
        ]
        assert ol.detect_override_patterns(contracts) == []
        contracts.append(_contract(3, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()}))
        assert len(ol.detect_override_patterns(contracts)) == 1


class TestOverridePatternSuggestionText:
    def test_suggestion_mentions_rule_count_and_scope(self):
        contracts = [
            _contract(
                i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()}, business_unit="Enterprise",
            )
            for i in range(1, 4)
        ]
        pattern = ol.detect_override_patterns(contracts, min_occurrences=3)[0]
        text = pattern.suggestion_text()
        assert "LOL-ESCALATE-001" in text
        assert "ESCALATE" in text
        assert "3 separate contracts" in text
        assert "Enterprise" in text

    def test_as_dict_shape(self):
        contracts = [
            _contract(i, [_governance_finding()], {"LOL-ESCALATE-001#0": _override_entry()})
            for i in range(1, 4)
        ]
        d = ol.detect_override_patterns(contracts, min_occurrences=3)[0].as_dict()
        assert d["rule_id"] == "LOL-ESCALATE-001"
        assert d["count"] == 3
        assert d["contract_ids"] == [1, 2, 3]
        assert "suggestion" in d


class TestPatternsForPlaybookDBIntegration:
    """patterns_for_playbook against real Contract rows — the thin DB
    wrapper is untested by the pure-logic classes above."""

    def test_scoped_to_one_playbook_and_finds_real_pattern(self):
        from database import SessionLocal, init_db
        from models import Contract, Playbook, User

        init_db()
        db = SessionLocal()
        try:
            user = User(email="override-db-test@example.com", password_hash="x")
            db.add(user)
            db.flush()
            playbook_a = Playbook(user_id=user.id, name="A", template_text="x")
            playbook_b = Playbook(user_id=user.id, name="B", template_text="x")
            db.add_all([playbook_a, playbook_b])
            db.flush()

            findings = [_governance_finding()]
            decisions = {"LOL-ESCALATE-001#0": _override_entry()}
            for i in range(3):
                db.add(Contract(
                    user_id=user.id, filename=f"c{i}.txt", contract_text="x",
                    playbook_id=playbook_a.id, findings_json=findings, review_decisions_json=decisions,
                    analysis_completed=True,
                ))
            # A contract under playbook_b must never contribute to playbook_a's patterns.
            db.add(Contract(
                user_id=user.id, filename="other.txt", contract_text="x",
                playbook_id=playbook_b.id, findings_json=findings, review_decisions_json=decisions,
                analysis_completed=True,
            ))
            db.commit()

            patterns_a = ol.patterns_for_playbook(db, playbook_a.id)
            assert len(patterns_a) == 1
            assert patterns_a[0].count == 3

            patterns_b = ol.patterns_for_playbook(db, playbook_b.id)
            assert patterns_b == []
        finally:
            db.close()
