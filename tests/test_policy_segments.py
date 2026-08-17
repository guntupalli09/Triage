"""
Playbook segment conditionality — deal size / business unit / customer
type. Covers: resolve_segment_position specificity/matching rules,
snapshot_active_positions picking exactly one PolicyPosition per
clause_type under a given contract context, activate_position only
archiving a same-segment sibling (so a GLOBAL and a segment-specific
position for the same clause_type can both be ACTIVE at once), and
create_segment_position's cloning/duplicate-guard behavior.
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest

import playbook_authoring as pa
import policy_enforcement as pe
from database import SessionLocal, init_db
from models import Playbook, PolicyPosition, PolicyPositionField, User


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema():
    init_db()


def _register_db(db, email) -> int:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.flush()
    return user.id


def _create_playbook_direct(db, user_id, name="Segment Test Playbook") -> Playbook:
    playbook = Playbook(user_id=user_id, name=name, template_text="x")
    db.add(playbook)
    db.flush()
    return playbook


_LIABILITY_CONFIG = {
    "preferred_multiplier": 1.0, "prohibit_unlimited": True,
    "required_exceptions_json": [], "require_consequential_damages_exclusion": False,
    "required_consequential_carveouts_json": [],
}


def _make_active_position(db, playbook, clause_type, segment=None, config_overrides=None) -> PolicyPosition:
    config = dict(_LIABILITY_CONFIG)
    config.update(config_overrides or {})
    business_unit, customer_type, deal_min, deal_max = segment or pa.GLOBAL_SEGMENT
    position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
        contract_side="mutual", escalation_approval_authority="Legal Director",
        fallback_text="Approved fallback text.", config_json=config, source_type="MANUAL",
        segment_business_unit=business_unit, segment_customer_type=customer_type,
        segment_deal_value_min=deal_min, segment_deal_value_max=deal_max,
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
    from datetime import datetime
    position.activated_at = datetime.utcnow()
    db.flush()
    return position


class TestResolveSegmentPosition:
    def test_global_only_matches_any_context(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-global-only@example.com")
            playbook = _create_playbook_direct(db, uid)
            glob = _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()

            for ctx in (None, {}, {"business_unit": "Enterprise", "deal_value": 999}):
                snapshot = pe.snapshot_active_positions(db, playbook.id, context=ctx)
                assert snapshot["limitation_of_liability"].id == glob.id
        finally:
            db.close()

    def test_more_specific_segment_wins_over_global_when_both_match(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-specific-wins@example.com")
            playbook = _create_playbook_direct(db, uid)
            glob = _make_active_position(db, playbook, "limitation_of_liability")
            enterprise = _make_active_position(
                db, playbook, "limitation_of_liability",
                segment=("Enterprise", None, None, None),
                config_overrides={"preferred_multiplier": 3.0},
            )
            db.commit()

            snapshot = pe.snapshot_active_positions(
                db, playbook.id, context={"business_unit": "Enterprise"},
            )
            assert snapshot["limitation_of_liability"].id == enterprise.id

            # A different business unit falls back to GLOBAL, not to the
            # Enterprise segment it doesn't satisfy.
            snapshot_smb = pe.snapshot_active_positions(
                db, playbook.id, context={"business_unit": "SMB"},
            )
            assert snapshot_smb["limitation_of_liability"].id == glob.id

        finally:
            db.close()

    def test_deal_value_range_is_inclusive_and_open_ended(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-deal-value@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability")
            big_deal = _make_active_position(
                db, playbook, "limitation_of_liability",
                segment=(None, None, 100000.0, None),
                config_overrides={"preferred_multiplier": 2.0},
            )
            db.commit()

            assert pe.snapshot_active_positions(
                db, playbook.id, context={"deal_value": 100000.0},
            )["limitation_of_liability"].id == big_deal.id
            assert pe.snapshot_active_positions(
                db, playbook.id, context={"deal_value": 250000.0},
            )["limitation_of_liability"].id == big_deal.id
            assert pe.snapshot_active_positions(
                db, playbook.id, context={"deal_value": 99999.99},
            )["limitation_of_liability"].id != big_deal.id
            # No deal_value supplied at all can't satisfy a bounded segment.
            assert pe.snapshot_active_positions(
                db, playbook.id, context=None,
            )["limitation_of_liability"].id != big_deal.id
        finally:
            db.close()

    def test_clause_type_with_no_matching_segment_is_simply_skipped(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-no-match-skipped@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(
                db, playbook, "limitation_of_liability", segment=("Enterprise", None, None, None),
            )
            db.commit()

            snapshot = pe.snapshot_active_positions(db, playbook.id, context={"business_unit": "SMB"})
            assert "limitation_of_liability" not in snapshot
        finally:
            db.close()


class TestActivationScopedBySegment:
    def test_activating_a_segment_position_does_not_archive_global_sibling(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-activate-no-archive@example.com")
            playbook = _create_playbook_direct(db, uid)
            glob = _make_active_position(db, playbook, "limitation_of_liability")

            enterprise_draft = PolicyPosition(
                playbook_id=playbook.id, clause_type="limitation_of_liability", status="DRAFT",
                contract_side="mutual", escalation_approval_authority="Legal Director",
                fallback_text="Approved fallback text.", config_json=dict(_LIABILITY_CONFIG),
                source_type="MANUAL", segment_business_unit="Enterprise",
            )
            db.add(enterprise_draft)
            db.flush()
            for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get("limitation_of_liability", []):
                db.add(PolicyPositionField(
                    policy_position_id=enterprise_draft.id, field_name=field_name,
                    value_json=_LIABILITY_CONFIG.get(field_name), source="MANUAL", status="ESTABLISHED",
                ))
            db.flush()
            enterprise_draft.status = "APPROVED"
            db.flush()

            user = db.query(User).filter(User.id == uid).first()
            pa.activate_position(db, enterprise_draft, user)
            db.commit()

            db.refresh(glob)
            db.refresh(enterprise_draft)
            assert glob.status == "ACTIVE"
            assert enterprise_draft.status == "ACTIVE"
        finally:
            db.close()

    def test_activating_a_second_global_position_still_archives_the_first(self):
        """Same-segment (GLOBAL/GLOBAL) sibling archival is unchanged —
        this is the pre-existing one-ACTIVE-row-per-clause_type invariant,
        preserved exactly for the segment every playbook had before this
        feature."""
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-global-still-archives@example.com")
            playbook = _create_playbook_direct(db, uid)
            first = _make_active_position(db, playbook, "limitation_of_liability")

            second_draft = PolicyPosition(
                playbook_id=playbook.id, clause_type="limitation_of_liability", status="DRAFT",
                contract_side="mutual", escalation_approval_authority="Legal Director",
                fallback_text="Approved fallback text.", config_json=dict(_LIABILITY_CONFIG),
                source_type="MANUAL",
            )
            db.add(second_draft)
            db.flush()
            for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get("limitation_of_liability", []):
                db.add(PolicyPositionField(
                    policy_position_id=second_draft.id, field_name=field_name,
                    value_json=_LIABILITY_CONFIG.get(field_name), source="MANUAL", status="ESTABLISHED",
                ))
            db.flush()
            second_draft.status = "APPROVED"
            db.flush()

            user = db.query(User).filter(User.id == uid).first()
            pa.activate_position(db, second_draft, user)
            db.commit()

            db.refresh(first)
            db.refresh(second_draft)
            assert first.status == "ARCHIVED"
            assert second_draft.status == "ACTIVE"
        finally:
            db.close()


class TestCreateSegmentPosition:
    def test_clones_global_config_by_default(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-create-clone@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability", config_overrides={"preferred_multiplier": 1.5})
            db.commit()

            new_position = pa.create_segment_position(
                db, playbook, "limitation_of_liability", ("Enterprise", None, None, None),
            )
            db.commit()
            assert new_position.config_json["preferred_multiplier"] == 1.5
            assert new_position.status == "DRAFT"
            assert new_position.segment_business_unit == "Enterprise"
        finally:
            db.close()

    def test_rejects_global_segment(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-create-rejects-global@example.com")
            playbook = _create_playbook_direct(db, uid)
            db.commit()
            with pytest.raises(ValueError):
                pa.create_segment_position(db, playbook, "limitation_of_liability", pa.GLOBAL_SEGMENT)
        finally:
            db.close()

    def test_rejects_duplicate_segment(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "seg-create-rejects-dup@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability", segment=("Enterprise", None, None, None))
            db.commit()
            with pytest.raises(pa.DuplicateSegmentError):
                pa.create_segment_position(db, playbook, "limitation_of_liability", ("Enterprise", None, None, None))
        finally:
            db.close()
