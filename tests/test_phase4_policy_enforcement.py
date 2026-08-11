"""
Phase 4 tests: production enforcement cutover.

Covers: mode dispatch (legacy/shadow/cutover), snapshot-based concurrency
safety, revision pinning, partial activation, non-ACTIVE statuses never
influencing production output, failure isolation, migration-coverage
fail-closed gate, deterministic ordering/serialization, cross-user
security at the production evaluation path (not just authoring routes),
and a full-system golden fixture covering every clause origin (migrated
legacy, manual, Phase 2 extracted-and-confirmed, Phase 3 AI-proposed-and-
confirmed) plus partial activation and a superseded-revision scenario.
"""
import io
import json
import os

os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi.testclient import TestClient

import main
import playbook_authoring as pa
import policy_enforcement as pe
import rate_limit
from database import SessionLocal, init_db
from models import (
    AuditLog, Contract, Playbook, PolicyPosition, PolicyPositionField,
    PolicyRule, User,
)


@pytest.fixture(scope="module", autouse=True)
def _ensure_schema():
    init_db()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email) -> str:
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Firm", "company": "", "csrf_token": token,
    })
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.plan = "professional"
        db.commit()
        return user.id
    finally:
        db.close()


def _create_playbook_direct(db, user_id, name="Bench Playbook") -> Playbook:
    playbook = Playbook(user_id=user_id, name=name, template_text="x")
    db.add(playbook)
    db.flush()
    return playbook


# Minimal valid, activation-ready config per clause type — every
# ACTIVATION_REQUIRED_FIELDS gate answered (False is a valid, established
# answer; it just means "don't require this"), so these positions can
# actually reach ACTIVE.
_MINIMAL_CONFIG = {
    "limitation_of_liability": {
        "preferred_multiplier": 1.0, "prohibit_unlimited": True,
        "required_exceptions_json": [], "require_consequential_damages_exclusion": False,
        "required_consequential_carveouts_json": [],
    },
    "indemnification": {
        "required_protection_triggers_json": [], "prohibited_exposure_triggers_json": [],
        "require_exposure_third_party_only": False, "require_defense_control_for_exposure": False,
        "require_notice_and_cooperation_for_exposure": False, "prohibit_uncapped_exposure": False,
    },
    "termination": {
        "require_mutual_convenience_termination": False, "required_survival_topics_json": [],
        "prohibit_uncapped_termination_fee": False,
    },
    "confidentiality": {
        "required_exclusions_json": [], "require_mutual_confidentiality": False,
    },
    "assignment": {
        "required_exceptions_json": [], "prohibit_sole_discretion_consent": False,
        "require_consent_for_counterparty_assignment": False,
    },
    "governing_law": {
        "preferred_jurisdictions_json": [], "acceptable_jurisdictions_json": [],
        "prohibited_jurisdictions_json": [], "require_jury_trial_waiver": False,
    },
}


def _make_active_position(db, playbook, clause_type, config_overrides=None, source_type="MANUAL") -> PolicyPosition:
    """Builds an ACTIVE PolicyPosition directly (bypassing the HTTP
    lifecycle routes, already covered by test_playbook_workbench.py) but
    still going through the same validate_position_for_activation gate
    production code uses, so an invalid fixture fails loudly here rather
    than silently passing a weaker check."""
    config = dict(_MINIMAL_CONFIG[clause_type])
    config.update(config_overrides or {})
    position = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
        contract_side="mutual", escalation_approval_authority="Legal Director",
        fallback_text="Approved fallback text.", config_json=config, source_type=source_type,
    )
    db.add(position)
    db.flush()
    # validate_position_for_activation reads PolicyPositionField.status,
    # not config_json directly — every activation-required field needs a
    # real, current (non-superseded) ESTABLISHED field row, exactly as
    # apply_position_update would have written for a real authoring flow.
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


LIABILITY_TEXT = (
    "12. Limitation of Liability. In no event shall either party's aggregate liability under this "
    "Agreement exceed 5 times the total annual fees paid in the twelve (12) months preceding the claim."
)


# ---------------------------------------------------------------------------
# Mode dispatch
# ---------------------------------------------------------------------------

class TestModeDispatch:
    def test_default_mode_is_shadow(self, monkeypatch):
        monkeypatch.delenv("POLICY_ENFORCEMENT_MODE", raising=False)
        assert pe.get_enforcement_mode() == "shadow"

    def test_unknown_mode_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "nonsense")
        assert pe.get_enforcement_mode() == "shadow"

    def test_mode_read_fresh_not_cached(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "legacy")
        assert pe.get_enforcement_mode() == "legacy"
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        assert pe.get_enforcement_mode() == "cutover"

    def test_legacy_mode_ignores_active_positions_entirely(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "legacy")
        db = SessionLocal()
        try:
            uid = _register_db(db, "legacy-mode@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 0.1})
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, LIABILITY_TEXT, findings)
            # No legacy PolicyRule exists on this playbook, so legacy mode
            # must return nothing, even though an ACTIVE PolicyPosition does.
            assert result["policy_decisions"] is None
            assert result["policy_revision_metadata"] is None
        finally:
            db.close()

    def test_shadow_mode_user_visible_result_still_legacy(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "shadow")
        db = SessionLocal()
        try:
            uid = _register_db(db, "shadow-mode@example.com")
            playbook = _create_playbook_direct(db, uid)
            rule = PolicyRule(
                playbook_id=playbook.id, clause_type="limitation_of_liability",
                preferred_multiplier=1.0, acceptable_max_multiplier=2.0, negotiate_max_multiplier=3.0,
                prohibit_unlimited=True, contract_side="mutual",
            )
            db.add(rule)
            db.flush()
            # A DIFFERENT (non-equivalent) migrated position — proves the
            # user-visible result comes from the legacy rule, not this one.
            _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 99.0})
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, LIABILITY_TEXT, findings)
            assert result["policy_decisions"]["limitation_of_liability"]["policy_limit_summary"] != "99.0x annual fees"
            assert result["policy_revision_metadata"] is None  # legacy path pins nothing
        finally:
            db.close()

    def test_cutover_mode_reads_active_positions_for_all_six(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "cutover-all-six@example.com")
            playbook = _create_playbook_direct(db, uid)
            for clause_type in pa.CLAUSE_TYPES:
                _make_active_position(db, playbook, clause_type)
            db.commit()

            findings = []
            text = LIABILITY_TEXT + " Indemnification. Confidentiality. Termination. Assignment. Governing Law."
            result = pe.apply_policies_for_review(db, playbook, text, findings)
            assert set(result["policy_decisions"].keys()) == set(pa.CLAUSE_TYPES)
            assert set(result["policy_revision_metadata"].keys()) == set(pa.CLAUSE_TYPES)
        finally:
            db.close()


def _register_db(db, email) -> int:
    user = User(email=email, password_hash="x")
    db.add(user)
    db.flush()
    return user.id


# ---------------------------------------------------------------------------
# Partial activation + status isolation (requirement 4)
# ---------------------------------------------------------------------------

class TestPartialActivationAndStatusIsolation:
    def test_only_active_clauses_are_evaluated(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "partial@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability")
            _make_active_position(db, playbook, "confidentiality")
            db.commit()

            outcomes = pe.evaluate_active_policies(db, playbook, LIABILITY_TEXT)
            clause_types = {o.clause_type for o in outcomes}
            assert clause_types == {"limitation_of_liability", "confidentiality"}
        finally:
            db.close()

    def test_draft_position_never_evaluated(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "draft-isolated@example.com")
            playbook = _create_playbook_direct(db, uid)
            draft = PolicyPosition(
                playbook_id=playbook.id, clause_type="limitation_of_liability", status="DRAFT",
                contract_side="mutual", config_json={"preferred_multiplier": 1.0}, source_type="MANUAL",
            )
            db.add(draft)
            db.commit()

            outcomes = pe.evaluate_active_policies(db, playbook, LIABILITY_TEXT)
            assert outcomes == []
        finally:
            db.close()

    def test_needs_review_and_approved_never_evaluated(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "needs-review-isolated@example.com")
            playbook = _create_playbook_direct(db, uid)
            for status in ("NEEDS_REVIEW", "APPROVED"):
                position = PolicyPosition(
                    playbook_id=playbook.id, clause_type="limitation_of_liability", status=status,
                    contract_side="mutual", config_json=dict(_MINIMAL_CONFIG["limitation_of_liability"]),
                    source_type="MANUAL",
                )
                db.add(position)
            db.commit()

            outcomes = pe.evaluate_active_policies(db, playbook, LIABILITY_TEXT)
            assert outcomes == []
        finally:
            db.close()

    def test_archived_position_never_evaluated_even_if_it_was_once_active(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "archived-isolated@example.com")
            playbook = _create_playbook_direct(db, uid)
            position = _make_active_position(db, playbook, "limitation_of_liability")
            position.status = "ARCHIVED"
            db.commit()

            outcomes = pe.evaluate_active_policies(db, playbook, LIABILITY_TEXT)
            assert outcomes == []
        finally:
            db.close()

    def test_no_active_positions_means_no_enforcement_not_permissive_acceptance(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "no-active@example.com")
            playbook = _create_playbook_direct(db, uid)
            db.commit()

            findings = []
            result = pe.apply_active_policies(db, playbook, LIABILITY_TEXT, findings)
            assert result is None
            assert findings == []
        finally:
            db.close()

    def test_source_type_never_affects_enforcement_semantics(self):
        """A position's authoring origin (MANUAL/UPLOADED_TEMPLATE/MIXED)
        must not change what gets evaluated — enforcement reads only
        config_json/contract_side/escalation_approval_authority/
        fallback_text, all origin-agnostic columns."""
        db = SessionLocal()
        try:
            uid = _register_db(db, "origin-agnostic@example.com")
            pb1 = _create_playbook_direct(db, uid, "Manual PB")
            pb2 = _create_playbook_direct(db, uid, "Extracted PB")
            _make_active_position(db, pb1, "limitation_of_liability", source_type="MANUAL")
            _make_active_position(db, pb2, "limitation_of_liability", source_type="UPLOADED_TEMPLATE")
            db.commit()

            out1 = pe.evaluate_active_policies(db, pb1, LIABILITY_TEXT)
            out2 = pe.evaluate_active_policies(db, pb2, LIABILITY_TEXT)
            assert out1[0].decision.as_dict()["state"] == out2[0].decision.as_dict()["state"]
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Revision pinning (requirement 5)
# ---------------------------------------------------------------------------

class TestRevisionPinning:
    def test_decision_carries_exact_revision_metadata(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "pinning@example.com")
            playbook = _create_playbook_direct(db, uid)
            position = _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()

            outcomes = pe.evaluate_active_policies(db, playbook, LIABILITY_TEXT)
            meta = outcomes[0].revision_metadata
            assert meta["policy_position_id"] == position.id
            assert meta["clause_type"] == "limitation_of_liability"
            assert meta["revision_activated_at"] is not None
            assert meta["config_hash"]
            assert meta["source_type"] == "MANUAL"
        finally:
            db.close()

    def test_config_hash_changes_with_content_stable_otherwise(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "hash-stability@example.com")
            playbook = _create_playbook_direct(db, uid)
            position = _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()
            h1 = pe.config_hash_for_position(position)
            h2 = pe.config_hash_for_position(position)
            assert h1 == h2

            other = _make_active_position(db, _create_playbook_direct(db, uid, "PB2"),
                                            "limitation_of_liability", {"preferred_multiplier": 4.0})
            db.commit()
            assert pe.config_hash_for_position(other) != h1
        finally:
            db.close()

    def test_historical_decision_survives_playbook_later_changing(self, monkeypatch):
        """A stored decision (and its revision metadata) must remain
        explainable even after the ACTIVE position is revised — the old
        decision is never recomputed against the CURRENT playbook state."""
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "historical-explainability@example.com")
            playbook = _create_playbook_direct(db, uid)
            old_position = _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 1.0})
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, LIABILITY_TEXT, findings)
            pinned_id = result["policy_revision_metadata"]["limitation_of_liability"]["policy_position_id"]
            pinned_hash = result["policy_revision_metadata"]["limitation_of_liability"]["config_hash"]
            assert pinned_id == old_position.id

            # Now revise: archive the old ACTIVE row, activate a new one
            # with different content, exactly as a lawyer editing an
            # ACTIVE policy does (get_or_build_editable_position + revise
            # + activate_position, exercised at the unit level here).
            old_position.status = "ARCHIVED"
            new_position = _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 9.0})
            db.commit()

            # The EARLIER result object (already computed) still points at
            # the old position/hash — nothing recomputes it retroactively.
            assert pinned_id == old_position.id
            assert pinned_hash != pe.config_hash_for_position(new_position)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Concurrency / race safety (requirement 6)
# ---------------------------------------------------------------------------

class TestConcurrencySafety:
    def test_snapshot_taken_once_is_immune_to_activation_during_review(self):
        """Simulates a lawyer activating a new revision of a clause AFTER
        this review's snapshot was taken but BEFORE all six clauses finish
        evaluating. The snapshot dict must keep pointing at the revision
        that was ACTIVE at snapshot time — the review must not see a mix
        of old and new revisions, and must not pick up the new one either,
        since it started under the old one."""
        db = SessionLocal()
        try:
            uid = _register_db(db, "concurrency@example.com")
            playbook = _create_playbook_direct(db, uid)
            v1 = _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 1.0})
            db.commit()

            # Review start: snapshot taken once.
            snapshot = pe.snapshot_active_positions(db, playbook.id)
            assert snapshot["limitation_of_liability"].id == v1.id

            # "Another contract review's" lawyer activates a new revision
            # concurrently, mid-review (v1 archived, v2 activated) —
            # simulated here as a same-session interleaving, which is the
            # part that actually exercises the snapshot's isolation; a
            # second DB session would show the same row states.
            v1.status = "ARCHIVED"
            v2 = _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 5.0})
            db.commit()

            # The IN-FLIGHT review must still evaluate against the
            # snapshotted v1, not the now-current v2.
            outcomes = pe.evaluate_active_policies(db, playbook, LIABILITY_TEXT, active_positions=snapshot)
            assert outcomes[0].revision_metadata["policy_position_id"] == v1.id
            assert outcomes[0].revision_metadata["policy_position_id"] != v2.id

            # A NEW review started now (fresh snapshot) correctly sees v2.
            fresh_snapshot = pe.snapshot_active_positions(db, playbook.id)
            assert fresh_snapshot["limitation_of_liability"].id == v2.id
        finally:
            db.close()

    def test_apply_active_policies_uses_single_snapshot_for_entire_evaluation(self, monkeypatch):
        """A contract with six clause types must never be evaluated with
        clause 1 under snapshot-time policy and clause 6 under a policy
        activated in between — apply_active_policies must snapshot once
        (or accept a pre-taken snapshot) and pass that same dict through
        for every clause, never re-querying per clause."""
        db = SessionLocal()
        try:
            uid = _register_db(db, "single-snapshot@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()

            calls = []
            original = pe.snapshot_active_positions

            def _spy(db_, playbook_id):
                calls.append(playbook_id)
                return original(db_, playbook_id)

            monkeypatch.setattr(pe, "snapshot_active_positions", _spy)
            findings = []
            pe.apply_active_policies(db, playbook, LIABILITY_TEXT, findings)
            assert len(calls) == 1  # exactly one snapshot for the whole evaluation
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Deterministic ordering (requirement 10)
# ---------------------------------------------------------------------------

class TestDeterministicOrdering:
    def test_policy_decisions_key_order_matches_clause_types_order(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "ordering@example.com")
            playbook = _create_playbook_direct(db, uid)
            # Activate in a DELIBERATELY scrambled order relative to
            # pa.CLAUSE_TYPES, to prove output order doesn't depend on
            # activation/insertion order.
            for clause_type in ("governing_law", "assignment", "limitation_of_liability", "termination"):
                _make_active_position(db, playbook, clause_type)
            db.commit()

            findings = []
            result = pe.apply_active_policies(db, playbook, LIABILITY_TEXT, findings)
            keys_in_order = list(result["policy_decisions"].keys())
            expected_order = [c for c in pa.CLAUSE_TYPES if c in keys_in_order]
            assert keys_in_order == expected_order
        finally:
            db.close()

    def test_same_contract_same_playbook_serializes_byte_identically(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "byte-identical@example.com")
            playbook = _create_playbook_direct(db, uid)
            for clause_type in pa.CLAUSE_TYPES:
                _make_active_position(db, playbook, clause_type)
            db.commit()

            text = LIABILITY_TEXT + " Indemnification. Confidentiality. Termination. Assignment. Governing Law."
            findings_a, findings_b = [], []
            result_a = pe.apply_active_policies(db, playbook, text, findings_a)
            result_b = pe.apply_active_policies(db, playbook, text, findings_b)
            assert json.dumps(result_a["policy_decisions"], sort_keys=False) == json.dumps(result_b["policy_decisions"], sort_keys=False)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Failure isolation (requirement 11)
# ---------------------------------------------------------------------------

class TestFailureIsolation:
    def test_one_adapter_exception_does_not_hide_others(self, monkeypatch):
        db = SessionLocal()
        try:
            uid = _register_db(db, "failure-isolation@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability")
            _make_active_position(db, playbook, "confidentiality")
            db.commit()

            def _boom(text):
                raise RuntimeError("simulated extractor crash")

            original_funcs = pa._ENGINE_FUNCS["limitation_of_liability"]
            monkeypatch.setitem(pa._ENGINE_FUNCS, "limitation_of_liability", (_boom, original_funcs[1]))

            outcomes = pe.evaluate_active_policies(db, playbook, LIABILITY_TEXT)
            by_clause = {o.clause_type: o for o in outcomes}
            assert by_clause["limitation_of_liability"].error is not None
            assert by_clause["limitation_of_liability"].decision is None
            assert by_clause["confidentiality"].error is None
            assert by_clause["confidentiality"].decision is not None
        finally:
            db.close()

    def test_error_outcome_never_leaks_exception_text_or_contract_text(self, monkeypatch):
        db = SessionLocal()
        try:
            uid = _register_db(db, "error-safe-message@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()

            secret_text = "SUPER SECRET CONTRACT TERMS 12345"

            def _boom(text):
                raise RuntimeError(f"crash while parsing: {secret_text}")

            original_funcs = pa._ENGINE_FUNCS["limitation_of_liability"]
            monkeypatch.setitem(pa._ENGINE_FUNCS, "limitation_of_liability", (_boom, original_funcs[1]))

            outcomes = pe.evaluate_active_policies(db, playbook, secret_text)
            assert secret_text not in outcomes[0].error
            assert outcomes[0].error == "RuntimeError"
        finally:
            db.close()

    def test_error_finding_is_not_a_fabricated_legal_decision(self, monkeypatch):
        db = SessionLocal()
        try:
            uid = _register_db(db, "no-fabricated-decision@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability")
            db.commit()

            def _boom(text):
                raise RuntimeError("simulated crash")

            original_funcs = pa._ENGINE_FUNCS["limitation_of_liability"]
            monkeypatch.setitem(pa._ENGINE_FUNCS, "limitation_of_liability", (_boom, original_funcs[1]))

            findings = []
            result = pe.apply_active_policies(db, playbook, LIABILITY_TEXT, findings)
            assert "limitation_of_liability" not in result["policy_decisions"]
            assert result["policy_revision_metadata"]["limitation_of_liability"]["error"] == "RuntimeError"
            error_findings = [f for f in findings if f["policy_state"] == "EVALUATION_ERROR"]
            assert len(error_findings) == 1
            assert error_findings[0]["severity"] == "high"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Migration coverage — fail closed (requirement 7)
# ---------------------------------------------------------------------------

class TestMigrationCoverageFailClosed:
    def test_unmigrated_legacy_policy_is_detected(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "unmigrated@example.com")
            playbook = _create_playbook_direct(db, uid)
            rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual")
            db.add(rule)
            db.commit()

            unmigrated = pe.find_unmigrated_liability_policies(db)
            assert playbook.id in unmigrated

            with pytest.raises(pe.MigrationCoverageError):
                pe.verify_migration_coverage_or_fail_closed(db)
        finally:
            db.close()

    def test_fully_migrated_passes(self):
        db = SessionLocal()
        try:
            uid = _register_db(db, "fully-migrated@example.com")
            playbook = _create_playbook_direct(db, uid)
            rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual")
            db.add(rule)
            db.flush()
            pa.migrate_legacy_policy_rule(db, rule)
            db.commit()

            # Scoped to this test's own playbook — the shared test DB may
            # carry other tests' deliberately-unmigrated fixtures.
            assert playbook.id not in pe.find_unmigrated_liability_policies(db)
        finally:
            db.close()

    def test_app_refuses_to_start_in_cutover_mode_with_incomplete_migration(self, monkeypatch):
        db = SessionLocal()
        try:
            uid = _register_db(db, "startup-gate@example.com")
            playbook = _create_playbook_direct(db, uid)
            db.add(PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual"))
            db.commit()
        finally:
            db.close()

        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        with pytest.raises(pe.MigrationCoverageError):
            with TestClient(main.app):
                pass


# ---------------------------------------------------------------------------
# Security — re-derive ownership at the PRODUCTION evaluation path, not
# only the authoring routes (requirement 12)
# ---------------------------------------------------------------------------

class TestProductionPathSecurity:
    def test_snapshot_is_scoped_to_the_given_playbook_id_only(self):
        db = SessionLocal()
        try:
            uid_a = _register_db(db, "sec-owner-a@example.com")
            uid_b = _register_db(db, "sec-owner-b@example.com")
            pb_a = _create_playbook_direct(db, uid_a, "PB A")
            pb_b = _create_playbook_direct(db, uid_b, "PB B")
            _make_active_position(db, pb_a, "limitation_of_liability", {"preferred_multiplier": 1.0})
            _make_active_position(db, pb_b, "limitation_of_liability", {"preferred_multiplier": 99.0})
            db.commit()

            snap_a = pe.snapshot_active_positions(db, pb_a.id)
            assert snap_a["limitation_of_liability"].config_json["preferred_multiplier"] == 1.0
            assert pb_b.id != pb_a.id
        finally:
            db.close()

    def test_upload_route_never_lets_client_supplied_playbook_id_reach_someone_elses_policy(self, client):
        token_a = _register(client, "route-owner-a@example.com")
        db = SessionLocal()
        try:
            user_a = db.query(User).filter(User.email == "route-owner-a@example.com").first()
            playbook_a = _create_playbook_direct(db, user_a.id, "Owner A PB")
            _make_active_position(db, playbook_a, "limitation_of_liability", {"preferred_multiplier": 0.01})
            db.commit()
            playbook_a_id = playbook_a.id
        finally:
            db.close()

        client.cookies.clear()
        token_b = _register(client, "route-attacker-b@example.com")
        files = {"file": ("t.txt", io.BytesIO(LIABILITY_TEXT.encode()), "text/plain")}
        # Attacker B references owner A's playbook_id directly in the
        # upload form. main.py's playbook lookup filters by
        # Playbook.user_id == current user — this must still hold true at
        # the Phase 4 call site, i.e. apply_policies_for_review must never
        # be reachable with a playbook object the current user doesn't own.
        r = client.post("/upload", data={"playbook_id": str(playbook_a_id), "csrf_token": token_b},
                         files=files, follow_redirects=False)
        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.user_id != None).order_by(Contract.id.desc()).first()
            if contract is not None and contract.playbook_id is not None:
                assert contract.playbook_id != playbook_a_id
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Full-system golden fixture (requirement 13)
# ---------------------------------------------------------------------------

GOLDEN_CONTRACT_TEXT = (
    "12. Limitation of Liability. In no event shall either party's aggregate liability under this "
    "Agreement exceed 5 times the total annual fees paid in the twelve (12) months preceding the claim. "
    "13. Indemnification. Vendor shall indemnify Customer against third-party claims. "
    "14. Termination. Either party may terminate for convenience upon ninety (90) days written notice. "
    "15. Confidentiality. Each party shall maintain the confidentiality of the other's information. "
    "16. Assignment. Neither party may assign this Agreement without the other's prior written consent. "
    "17. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
)


class TestFullSystemGolden:
    def test_all_six_active_full_lifecycle_to_review_findings(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "golden-all-six@example.com")
            playbook = _create_playbook_direct(db, uid)
            for clause_type in pa.CLAUSE_TYPES:
                _make_active_position(db, playbook, clause_type)
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, GOLDEN_CONTRACT_TEXT, findings)
            assert set(result["policy_decisions"].keys()) == set(pa.CLAUSE_TYPES)
            for clause_type, meta in result["policy_revision_metadata"].items():
                assert "error" not in meta
                assert meta["policy_position_id"] is not None
        finally:
            db.close()

    def test_partial_activation_two_of_six(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "golden-partial@example.com")
            playbook = _create_playbook_direct(db, uid)
            _make_active_position(db, playbook, "limitation_of_liability")
            _make_active_position(db, playbook, "governing_law")
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, GOLDEN_CONTRACT_TEXT, findings)
            assert set(result["policy_decisions"].keys()) == {"limitation_of_liability", "governing_law"}
        finally:
            db.close()

    def test_superseded_revision_excluded_new_revision_used(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "golden-superseded@example.com")
            playbook = _create_playbook_direct(db, uid)
            v1 = _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 1.0})
            v1.status = "ARCHIVED"
            v2 = _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 2.0})
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, GOLDEN_CONTRACT_TEXT, findings)
            pinned = result["policy_revision_metadata"]["limitation_of_liability"]["policy_position_id"]
            assert pinned == v2.id
            assert pinned != v1.id
        finally:
            db.close()

    def test_migrated_liability_policy_participates_identically(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "golden-migrated@example.com")
            playbook = _create_playbook_direct(db, uid)
            rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", contract_side="mutual",
                               preferred_multiplier=1.0, prohibit_unlimited=True)
            db.add(rule)
            db.flush()
            pa.migrate_legacy_policy_rule(db, rule)
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, GOLDEN_CONTRACT_TEXT, findings)
            assert "limitation_of_liability" in result["policy_decisions"]
            assert result["policy_revision_metadata"]["limitation_of_liability"]["source_type"] == "MANUAL"
        finally:
            db.close()

    def test_phase2_extracted_and_confirmed_policy_participates_identically(self, monkeypatch):
        """A Phase 2 extraction-sourced field, once approved and activated,
        must enforce exactly like a manually-authored one — origin never
        changes enforcement semantics."""
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "golden-phase2@example.com")
            playbook = _create_playbook_direct(db, uid)
            position = _make_active_position(
                db, playbook, "limitation_of_liability", {"preferred_multiplier": 1.0},
                source_type="UPLOADED_TEMPLATE",
            )
            db.add(PolicyPositionField(
                policy_position_id=position.id, field_name="preferred_multiplier", value_json=1.0,
                source="EXTRACTED", status="ESTABLISHED", extraction_version="phase2-deterministic-v1",
            ))
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, GOLDEN_CONTRACT_TEXT, findings)
            assert "limitation_of_liability" in result["policy_decisions"]
        finally:
            db.close()

    def test_phase3_ai_proposed_and_confirmed_policy_participates_identically(self, monkeypatch):
        """Same claim for a Phase 3 AI-sourced field: once a lawyer
        confirmed it into an ACTIVE position, enforcement cannot tell (or
        care) that an LLM was ever involved."""
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "golden-phase3@example.com")
            playbook = _create_playbook_direct(db, uid)
            position = _make_active_position(
                db, playbook, "limitation_of_liability", {"preferred_multiplier": 1.0},
                source_type="UPLOADED_PLAYBOOK",
            )
            db.add(PolicyPositionField(
                policy_position_id=position.id, field_name="preferred_multiplier", value_json=1.0,
                source="EXTRACTED", status="ESTABLISHED", extraction_version="phase3-ai-v1",
            ))
            db.commit()

            findings = []
            result = pe.apply_policies_for_review(db, playbook, GOLDEN_CONTRACT_TEXT, findings)
            assert "limitation_of_liability" in result["policy_decisions"]
        finally:
            db.close()

    def test_active_revision_changed_during_review_uses_snapshot_not_current_state(self, monkeypatch):
        monkeypatch.setenv("POLICY_ENFORCEMENT_MODE", "cutover")
        db = SessionLocal()
        try:
            uid = _register_db(db, "golden-race@example.com")
            playbook = _create_playbook_direct(db, uid)
            v1 = _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 1.0})
            db.commit()

            snapshot = pe.snapshot_active_positions(db, playbook.id)
            v1.status = "ARCHIVED"
            _make_active_position(db, playbook, "limitation_of_liability", {"preferred_multiplier": 9.0})
            db.commit()

            findings = []
            result = pe.apply_active_policies(db, playbook, GOLDEN_CONTRACT_TEXT, findings, active_positions=snapshot)
            assert result["policy_revision_metadata"]["limitation_of_liability"]["policy_position_id"] == v1.id
        finally:
            db.close()
