"""
Phase 4.1: end-to-end rollback verification.

Proves the full mode cycle shadow -> cutover -> legacy against a
controlled fixture: (1) each mode produces the result its own contract
promises, (2) rolling back to legacy restores exactly the original
legacy-authoritative result, and (3) PolicyPosition/PolicyPositionField/
PolicyPositionApproval rows are never deleted or mutated by a mode
change — flipping POLICY_ENFORCEMENT_MODE is purely which path main.py
reads, never a write to authoring data.
"""
import os
from datetime import datetime

os.environ.setdefault("DEV_MODE", "true")

import pytest

import playbook_authoring as pa
import policy_enforcement as pe
from database import SessionLocal, init_db
from models import Playbook, PolicyPosition, PolicyPositionApproval, PolicyPositionField, PolicyRule, User


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema():
    init_db()


ROLLBACK_CONTRACT_TEXT = (
    "12. Limitation of Liability. In no event shall either party's aggregate liability under this "
    "Agreement exceed 5 times the total annual fees paid in the twelve (12) months preceding the claim."
)


def _snapshot_authoring_rows(db, position_id):
    """Every field on the row-family this test must prove untouched by a
    mode flip: the position itself, its field rows, and its approval
    history — content, not just row count, so a silent mutation of a
    single column would still be caught."""
    position = db.query(PolicyPosition).filter(PolicyPosition.id == position_id).first()
    fields = db.query(PolicyPositionField).filter(PolicyPositionField.policy_position_id == position_id).order_by(PolicyPositionField.id).all()
    approvals = db.query(PolicyPositionApproval).filter(PolicyPositionApproval.policy_position_id == position_id).order_by(PolicyPositionApproval.id).all()
    return {
        "position": (position.status, position.config_json, position.contract_side,
                     position.escalation_approval_authority, position.fallback_text, position.source_type),
        "fields": [(f.field_name, f.value_json, f.source, f.status) for f in fields],
        "approvals": [(a.action, a.from_status, a.to_status, a.reason) for a in approvals],
    }


class TestFullRollbackCycle:
    def test_shadow_cutover_legacy_cycle_restores_legacy_result_and_preserves_authoring_data(self, monkeypatch):
        db = SessionLocal()
        try:
            user = User(email="rollback-cycle@example.com", password_hash="x")
            db.add(user)
            db.flush()
            playbook = Playbook(user_id=user.id, name="Rollback Cycle PB", template_text="x")
            db.add(playbook)
            db.flush()

            # Legacy PolicyRule — the pre-Phase-4 world.
            legacy_rule = PolicyRule(
                playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual",
                preferred_multiplier=1.0, acceptable_max_multiplier=2.0, negotiate_max_multiplier=3.0,
                prohibit_unlimited=True,
            )
            db.add(legacy_rule)
            db.flush()

            # Migrated ACTIVE PolicyPosition — Phase 0's migration path,
            # equivalent content to the legacy rule (so shadow mode should
            # show zero divergence for this fixture, matching the release
            # gate's own claim).
            migrated_position = pa.migrate_legacy_policy_rule(db, legacy_rule)
            db.commit()
            position_id = migrated_position.id

            # Record an approval-history entry too, so the "nothing
            # mutated" check below isn't just checking an empty table.
            db.add(PolicyPositionApproval(
                policy_position_id=position_id, actor_user_id=user.id,
                action="ACTIVATED", from_status="APPROVED", to_status="ACTIVE", reason="initial migration",
            ))
            db.commit()

            before_authoring_state = _snapshot_authoring_rows(db, position_id)

            # ---- 1. SHADOW: user-visible result comes from legacy path ----
            monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "shadow")
            findings_shadow = []
            result_shadow = pe.apply_policies_for_review(db, playbook, ROLLBACK_CONTRACT_TEXT, findings_shadow)
            db.commit()
            shadow_state = result_shadow["policy_decisions"]["limitation_of_liability"]["state"]
            # Revision metadata is never populated by the legacy path.
            assert result_shadow["policy_revision_metadata"] is None

            # Shadow mode must ALSO have logged a comparison, and — because
            # this fixture's migrated position is a byte-for-byte migration
            # of the legacy rule — it must show zero divergence.
            comparisons = pe.run_shadow_comparison(db, playbook, ROLLBACK_CONTRACT_TEXT)
            db.commit()
            assert comparisons is not None
            assert comparisons["diverged"] is False
            assert comparisons["is_error"] is False

            # ---- 2. CUTOVER: user-visible result now comes from the ACTIVE PolicyPosition ----
            monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
            findings_cutover = []
            result_cutover = pe.apply_policies_for_review(db, playbook, ROLLBACK_CONTRACT_TEXT, findings_cutover)
            db.commit()
            cutover_state = result_cutover["policy_decisions"]["limitation_of_liability"]["state"]
            assert result_cutover["policy_revision_metadata"]["limitation_of_liability"]["policy_position_id"] == position_id

            # Because the fixture is a genuine equivalence, cutover's state
            # must match shadow's (legacy-sourced) state exactly.
            assert cutover_state == shadow_state

            # ---- 3. ROLLBACK to legacy ----
            monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "legacy")
            findings_legacy = []
            result_legacy = pe.apply_policies_for_review(db, playbook, ROLLBACK_CONTRACT_TEXT, findings_legacy)
            db.commit()
            legacy_state_after_rollback = result_legacy["policy_decisions"]["limitation_of_liability"]["state"]
            assert result_legacy["policy_revision_metadata"] is None

            # The rollback restores EXACTLY the original legacy-authoritative
            # result — same state as step 1, byte-identical decision dict
            # modulo nothing (both came from the same evaluator + same rule).
            assert legacy_state_after_rollback == shadow_state
            assert result_legacy["policy_decisions"] == result_shadow["policy_decisions"]

            # ---- 4. Authoring data was never deleted or mutated by any mode flip ----
            after_authoring_state = _snapshot_authoring_rows(db, position_id)
            assert after_authoring_state == before_authoring_state

            # And the legacy PolicyRule itself is untouched too — Phase 4
            # never writes to PolicyRule.
            db.refresh(legacy_rule)
            assert legacy_rule.preferred_multiplier == 1.0
            assert legacy_rule.acceptable_max_multiplier == 2.0
            assert legacy_rule.negotiate_max_multiplier == 3.0
        finally:
            db.close()

    def test_rollback_switch_takes_effect_without_any_db_write(self, monkeypatch):
        """The rollback switch is purely an environment-variable read
        (policy_enforcement.get_enforcement_mode) — flipping it must not
        require, and must not perform, any database write of its own."""
        db = SessionLocal()
        try:
            user = User(email="rollback-no-write@example.com", password_hash="x")
            db.add(user)
            db.flush()
            playbook = Playbook(user_id=user.id, name="No-Write Rollback PB", template_text="x")
            db.add(playbook)
            db.flush()
            rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual",
                               preferred_multiplier=1.0, prohibit_unlimited=True)
            db.add(rule)
            db.flush()
            position = pa.migrate_legacy_policy_rule(db, rule)
            db.commit()

            position_count_before = db.query(PolicyPosition).count()
            field_count_before = db.query(PolicyPositionField).count()

            for mode in ("shadow", "cutover", "legacy", "cutover", "legacy"):
                monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", mode)
                assert pe.get_enforcement_mode() == mode  # pure env read, no I/O

            assert db.query(PolicyPosition).count() == position_count_before
            assert db.query(PolicyPositionField).count() == field_count_before
        finally:
            db.close()
