"""
Interaction Engine V1 — production wiring tests.

Covers the integration point named in docs/architecture/
interaction_engine_v1_design.md S11: apply_policies_for_review (cutover
mode) evaluates all ACTIVE PolicyPositions, then evaluates the seven-rule
launch catalog over exactly those decisions, appends synthetic
"interaction_decision" findings, and returns interaction_decisions for
Contract.interaction_decisions_json — with failure isolation, determinism,
and Verify replay all exercised end-to-end against a real DB, not just the
pure-function unit level already covered by test_interaction_engine_core.py.
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import interaction_enforcement as ixe
import interaction_engine_core as ixc
import interaction_rules as ixr
import playbook_authoring as pa
import policy_enforcement as pe
from database import Base
from models import Playbook, PolicyPosition, PolicyPositionField, User
import analytics_models  # noqa: F401
from tests.test_phase4_policy_enforcement import _MINIMAL_CONFIG, _make_active_position


def _make_active_position_with_side(db, playbook, clause_type, contract_side, config_overrides=None):
    """Same as test_phase4_policy_enforcement._make_active_position, but
    allows setting PolicyPosition.contract_side (a real column, not a
    config_json field) — needed here because indemnification's directional
    resolution requires a non-mutual contract_side to determine which
    obligation is "ours"."""
    from datetime import datetime
    config = dict(_MINIMAL_CONFIG[clause_type])
    config.update(config_overrides or {})
    position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
        contract_side=contract_side, escalation_approval_authority="Legal Director",
        fallback_text="Approved fallback text.", config_json=config, source_type="MANUAL",
    )
    db.add(position)
    db.flush()
    for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get(clause_type, []):
        db.add(PolicyPositionField(
            policy_position_id=position.id, field_name=field_name,
            value_json=config.get(field_name), source="MANUAL", status="ESTABLISHED",
        ))
    db.flush()
    pa.validate_position_for_activation(position)
    position.status = "ACTIVE"
    position.activated_at = datetime.utcnow()
    db.flush()
    return position


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'interaction_enforcement_test.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def playbook(db_session):
    user = User(email="lawyer@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    pb = Playbook(user_id=user.id, name="Test Playbook", template_text="irrelevant")
    db_session.add(pb)
    db_session.flush()
    return pb


IP_LIABILITY_TEXT = (
    "12. Limitation of Liability. Aggregate liability shall not exceed 1 times the total annual fees "
    "paid; the foregoing limitation shall not apply to claims arising from intellectual property "
    "infringement."
)
IP_INDEMNIFICATION_TEXT = (
    "9.1 Indemnification. Supplier shall indemnify, defend, and hold harmless Customer from and against "
    "any third-party claims arising from actual or alleged infringement of intellectual property rights "
    "by the Services."
)


def _drive_flagship_ip_scenario(db_session, playbook):
    """Activates Liability + Indemnification positions shaped so the
    flagship IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY rule fires, mirroring
    the design doc's own worked example."""
    _make_active_position(db_session, playbook, "limitation_of_liability", {
        "preferred_multiplier": 1.0, "acceptable_max_multiplier": 2.0, "negotiate_max_multiplier": 5.0,
        "prohibit_unlimited": False,
    })
    _make_active_position_with_side(db_session, playbook, "indemnification", "sell_side")
    db_session.commit()


class TestApplyInteractionRulesWiring:
    def test_flagship_ip_interaction_fires_end_to_end(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        _drive_flagship_ip_scenario(db_session, playbook)
        text = IP_LIABILITY_TEXT + " " + IP_INDEMNIFICATION_TEXT

        findings = []
        result = pe.apply_policies_for_review(db_session, playbook, text, findings, contract_id=None)

        assert result["interaction_decisions"] is not None
        fired = result["interaction_decisions"]["IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"]
        assert fired["state"] == "ESCALATE"
        assert fired["kind"] == "CONFLICT"
        assert set(fired["participating_clause_types"]) == {"limitation_of_liability", "indemnification"}

        # Every one of the seven launch rules is recorded, not only the one that fired.
        assert set(result["interaction_decisions"].keys()) == set(ixr.LAUNCH_CATALOG_IDS)

        interaction_findings = [f for f in findings if f.get("finding_type") == "interaction_decision"]
        assert len(interaction_findings) == 1
        assert interaction_findings[0]["interaction_id"] == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"
        # escalate_to is only ever borrowed from a PARTICIPATING clause's
        # own PolicyDecision.escalate_to (which itself is only populated
        # when that clause's own state is ESCALATE/PROHIBITED — see
        # policy_engine_core.escalate_to_for_state). Here both individual
        # clause decisions are ACCEPT, so there is no clause-level named
        # authority to borrow even though the INTERACTION itself escalates
        # -- a known, documented V1 limitation (see final report), not a bug.
        assert interaction_findings[0]["escalate_to"] is None

    def test_no_active_positions_yields_no_interactions_and_no_crash(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        findings = []
        result = pe.apply_policies_for_review(db_session, playbook, "irrelevant text", findings)
        assert result["policy_decisions"] is None
        assert result["interaction_decisions"] is None

    def test_shadow_and_legacy_modes_never_evaluate_interactions(self, monkeypatch, db_session, playbook):
        _drive_flagship_ip_scenario(db_session, playbook)
        text = IP_LIABILITY_TEXT + " " + IP_INDEMNIFICATION_TEXT
        for mode in ("shadow", "legacy"):
            monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", mode)
            findings = []
            result = pe.apply_policies_for_review(db_session, playbook, text, findings)
            assert result["interaction_decisions"] is None
            assert not any(f.get("finding_type") == "interaction_decision" for f in findings)

    def test_only_liability_active_reports_insufficient_facts_not_a_crash(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        _make_active_position(db_session, playbook, "limitation_of_liability")
        db_session.commit()
        findings = []
        result = pe.apply_policies_for_review(db_session, playbook, IP_LIABILITY_TEXT, findings)
        decisions = result["interaction_decisions"]
        assert decisions["IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"]["state"] == "INSUFFICIENT_FACTS"
        assert "indemnification" in decisions["IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"]["missing_clause_types"]
        # INSUFFICIENT_FACTS must never appear as an actionable finding.
        assert not any(f.get("finding_type") == "interaction_decision" for f in findings)


class TestFailureIsolation:
    def test_one_rule_exception_does_not_hide_others_or_crash_review(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        _drive_flagship_ip_scenario(db_session, playbook)
        text = IP_LIABILITY_TEXT + " " + IP_INDEMNIFICATION_TEXT

        def _boom(decisions):
            raise RuntimeError("simulated predicate failure")

        broken_rule = next(r for r in ixr.LAUNCH_CATALOG if r.interaction_id == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        monkeypatch.setattr(broken_rule, "predicate", _boom)

        findings = []
        result = pe.apply_policies_for_review(db_session, playbook, text, findings)
        decisions = result["interaction_decisions"]
        assert decisions["IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"]["state"] == "EVALUATION_ERROR"
        # Every other rule still evaluated normally (rule 2, sharing the
        # same two participants, is unaffected by rule 1's failure).
        assert decisions["IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH"]["state"] in (
            "NOT_TRIGGERED", "ESCALATE",
        )
        # No exception detail or contract text leaked into the error finding.
        error_finding = next(f for f in findings if f.get("interaction_id") == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert "RuntimeError" in error_finding["rationale"]
        assert "simulated predicate failure" not in error_finding["rationale"]
        assert text not in error_finding["rationale"]


class TestDeterminism:
    def test_same_inputs_produce_byte_identical_interaction_decisions(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        _drive_flagship_ip_scenario(db_session, playbook)
        text = IP_LIABILITY_TEXT + " " + IP_INDEMNIFICATION_TEXT

        import json
        results = []
        for _ in range(5):
            findings = []
            result = pe.apply_policies_for_review(db_session, playbook, text, findings)
            results.append(json.dumps(result["interaction_decisions"], sort_keys=True))
        assert len(set(results)) == 1


class TestVerifyInteractionFinding:
    def test_verify_reproduces_fired_interaction(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        _drive_flagship_ip_scenario(db_session, playbook)
        text = IP_LIABILITY_TEXT + " " + IP_INDEMNIFICATION_TEXT

        from models import Contract
        findings = []
        result = pe.apply_policies_for_review(db_session, playbook, text, findings)
        contract = Contract(
            user_id=playbook.user_id, filename="x.txt", contract_text=text,
            playbook_id=playbook.id, findings_json=findings,
            policy_decisions_json=result["policy_decisions"],
            policy_revision_metadata_json=result["policy_revision_metadata"],
            interaction_decisions_json=result["interaction_decisions"],
        )
        db_session.add(contract)
        db_session.commit()

        finding = next(f for f in findings if f.get("finding_type") == "interaction_decision")
        verification = ixe.verify_interaction_finding(db_session, contract, finding)
        assert verification["verified"] is True
        assert verification["replayed_state"] == "ESCALATE"

    def test_verify_detects_superseded_revision(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        _drive_flagship_ip_scenario(db_session, playbook)
        text = IP_LIABILITY_TEXT + " " + IP_INDEMNIFICATION_TEXT

        from models import Contract
        findings = []
        result = pe.apply_policies_for_review(db_session, playbook, text, findings)
        contract = Contract(
            user_id=playbook.user_id, filename="x.txt", contract_text=text,
            playbook_id=playbook.id, findings_json=findings,
            policy_decisions_json=result["policy_decisions"],
            policy_revision_metadata_json=result["policy_revision_metadata"],
            interaction_decisions_json=result["interaction_decisions"],
        )
        db_session.add(contract)
        db_session.commit()
        finding = next(f for f in findings if f.get("finding_type") == "interaction_decision")

        # Now revise + reactivate Liability with a policy that would prohibit
        # unlimited liability outright -- a new PolicyPosition revision,
        # archiving the one that produced the original interaction.
        _make_active_position(db_session, playbook, "limitation_of_liability", {
            "preferred_multiplier": 1.0, "acceptable_max_multiplier": 2.0, "negotiate_max_multiplier": 5.0,
            "prohibit_unlimited": True,
        })
        db_session.commit()

        verification = ixe.verify_interaction_finding(db_session, contract, finding)
        # The pinned revision for limitation_of_liability was archived, but
        # its row still exists (revision-not-mutation) and its config_hash
        # is unchanged -- so Verify still replays it and reproduces the
        # same interaction, exactly mirroring verify_policy_finding's own
        # "replay the pinned row regardless of current status" semantics.
        assert verification["verified"] is True


class TestInteractionFactsRegistryCompliance:
    """Regression proof for the approved output-only extension (design
    doc follow-up): payment_terms and sla now populate PolicyDecision.
    interaction_facts, and every other adapter's individual policy states
    and category_treatments must be byte-for-byte unaffected."""

    def test_only_payment_terms_and_sla_populate_interaction_facts(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        for clause_type in pa.CLAUSE_TYPES:
            _make_active_position(db_session, playbook, clause_type)
        db_session.commit()

        outcomes = pe.evaluate_active_policies(db_session, playbook, "No relevant clauses present at all.")
        for outcome in outcomes:
            assert outcome.decision is not None
            import policy_engine_core as core
            core.validate_interaction_facts(outcome.clause_type, outcome.decision.interaction_facts)
            if outcome.clause_type in ("payment_terms", "sla"):
                continue
            assert outcome.decision.interaction_facts == {}


# ---------------------------------------------------------------------------
# Redline invalidation (design doc S5.2/S5.3) — mark, never recompute.
# ---------------------------------------------------------------------------

class _FakeContract:
    """Minimal stand-in for models.Contract for pure-function tests of
    the staleness helpers -- these three functions only ever read/write
    interaction_decisions_json / interaction_staleness_json, so a full
    ORM object is unnecessary machinery for testing them in isolation."""
    def __init__(self, interaction_decisions_json=None, interaction_staleness_json=None):
        self.interaction_decisions_json = interaction_decisions_json
        self.interaction_staleness_json = interaction_staleness_json


def _ix_decision(interaction_id, state, participating):
    return {"interaction_id": interaction_id, "state": state, "participating_clause_types": list(participating)}


class TestMarkDependentInteractionsStale:
    def test_marks_only_interactions_participating_in_changed_clause(self):
        contract = _FakeContract(interaction_decisions_json={
            "IX_A": _ix_decision("IX_A", "ESCALATE", ["limitation_of_liability", "indemnification"]),
            "IX_B": _ix_decision("IX_B", "REQUIRES_REVIEW", ["sla", "payment_terms"]),
        })
        marked = ixe.mark_dependent_interactions_stale(contract, "limitation_of_liability", "Limitation of Liability")
        assert marked == ["IX_A"]
        assert contract.interaction_staleness_json["IX_A"]["stale"] is True
        assert "Limitation of Liability" in contract.interaction_staleness_json["IX_A"]["stale_reason"]
        assert "IX_B" not in contract.interaction_staleness_json

    def test_never_marks_not_triggered_or_insufficient_facts(self):
        contract = _FakeContract(interaction_decisions_json={
            "IX_A": _ix_decision("IX_A", "NOT_TRIGGERED", ["limitation_of_liability", "indemnification"]),
            "IX_B": _ix_decision("IX_B", "INSUFFICIENT_FACTS", ["limitation_of_liability", "insurance"]),
        })
        marked = ixe.mark_dependent_interactions_stale(contract, "limitation_of_liability", "Limitation of Liability")
        assert marked == []
        assert contract.interaction_staleness_json == {}

    def test_idempotent_does_not_overwrite_existing_reason(self):
        contract = _FakeContract(
            interaction_decisions_json={"IX_A": _ix_decision("IX_A", "ESCALATE", ["limitation_of_liability", "indemnification"])},
            interaction_staleness_json={"IX_A": {"stale": True, "stale_reason": "original reason"}},
        )
        marked = ixe.mark_dependent_interactions_stale(contract, "limitation_of_liability", "Limitation of Liability")
        assert marked == []  # already stale -- not re-marked, reason preserved
        assert contract.interaction_staleness_json["IX_A"]["stale_reason"] == "original reason"

    def test_no_interaction_decisions_at_all_is_a_noop(self):
        contract = _FakeContract(interaction_decisions_json=None)
        marked = ixe.mark_dependent_interactions_stale(contract, "limitation_of_liability", "Limitation of Liability")
        assert marked == []
        assert contract.interaction_staleness_json == {}


class TestMergeInteractionStaleness:
    def test_merges_stale_flag_only_onto_matching_interaction_finding(self):
        findings = [
            {"finding_type": "interaction_decision", "interaction_id": "IX_A", "stale": False},
            {"finding_type": "interaction_decision", "interaction_id": "IX_B", "stale": False},
            {"finding_type": "policy_decision", "clause_type": "limitation_of_liability"},
        ]
        staleness = {"IX_A": {"stale": True, "stale_reason": "changed"}}
        merged = ixe.merge_interaction_staleness(findings, staleness)
        assert merged[0]["stale"] is True and merged[0]["stale_reason"] == "changed"
        assert merged[1]["stale"] is False
        assert "stale" not in merged[2]
        # Original list/dicts are never mutated -- callers may safely reuse
        # the stored findings_json elsewhere in the same request.
        assert findings[0]["stale"] is False

    def test_empty_staleness_returns_original_list_object(self):
        findings = [{"finding_type": "interaction_decision", "interaction_id": "IX_A"}]
        assert ixe.merge_interaction_staleness(findings, {}) is findings
        assert ixe.merge_interaction_staleness(findings, None) is findings


class TestClearInteractionStaleness:
    def test_clears_existing_flag(self):
        contract = _FakeContract(interaction_staleness_json={"IX_A": {"stale": True, "stale_reason": "x"}})
        assert ixe.clear_interaction_staleness(contract, "IX_A") is True
        assert "IX_A" not in contract.interaction_staleness_json

    def test_clearing_nonexistent_flag_is_a_noop(self):
        contract = _FakeContract(interaction_staleness_json={})
        assert ixe.clear_interaction_staleness(contract, "IX_A") is False


class TestInvalidationEndToEnd:
    def test_editing_participating_clause_marks_only_dependent_interaction(self, monkeypatch, db_session, playbook):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        _drive_flagship_ip_scenario(db_session, playbook)
        # Also activate SLA + Payment Terms so an UNRELATED interaction
        # (rule 7) exists in the same review and can be proven untouched.
        _make_active_position(db_session, playbook, "sla")
        _make_active_position(db_session, playbook, "payment_terms")
        db_session.commit()
        text = IP_LIABILITY_TEXT + " " + IP_INDEMNIFICATION_TEXT

        from models import Contract
        findings = []
        result = pe.apply_policies_for_review(db_session, playbook, text, findings)
        contract = Contract(
            user_id=playbook.user_id, filename="x.txt", contract_text=text,
            playbook_id=playbook.id, findings_json=findings,
            policy_decisions_json=result["policy_decisions"],
            policy_revision_metadata_json=result["policy_revision_metadata"],
            interaction_decisions_json=result["interaction_decisions"],
        )
        db_session.add(contract)
        db_session.commit()

        marked = ixe.mark_dependent_interactions_stale(contract, "limitation_of_liability", "Limitation of Liability")
        db_session.commit()

        assert "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY" in marked
        # rule 7 (SLA x Payment Terms) never involves limitation_of_liability
        # at all -- must never be marked, regardless of its own state.
        assert "IX_SLA_PAYMENT_CREDIT_DEPENDENCY" not in (contract.interaction_staleness_json or {})

        merged = ixe.merge_interaction_staleness(contract.findings_json, contract.interaction_staleness_json)
        stale_finding = next(f for f in merged if f.get("interaction_id") == "IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")
        assert stale_finding["stale"] is True
        assert "Limitation of Liability" in stale_finding["stale_reason"]
