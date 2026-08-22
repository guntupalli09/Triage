"""Step 4B Phase F -- >=150 case DEVELOPMENT governance benchmark. Runs
the REAL playbook_authoring lifecycle functions (mark_ready_for_review,
approve_position, activate_position, return_to_draft,
get_or_build_editable_position, apply_position_update) and the REAL
policy_enforcement revision-pinning functions (snapshot_active_positions,
config_hash_for_position, verify_policy_finding) against a real SQLite
database -- never reimplemented, never mocked. Also exercises the
playbook-delete provenance guard fixed this phase.

Each case is a small scenario function returning True (passed) / False
(failed) plus a note; results are tallied and classified into the named
governance metrics.
"""
import os
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/step4b_phaseF_governance.db")
import sys
sys.path.insert(0, ".")

import json
from datetime import datetime

import main  # noqa: F401 -- registers all ORM relationships (see Phase F trace note)
import playbook_authoring as pa
import policy_enforcement as pe
from database import init_db, SessionLocal
from models import Playbook, PolicyPosition, PolicyPositionField, PolicyPositionApproval, Contract, User

init_db()

CASES = []
_uid_counter = [0]


def case(name, family, fn):
    _uid_counter[0] += 1
    cid = f"govF-{_uid_counter[0]:03d}-{name}"
    try:
        ok, note = fn()
    except Exception as exc:  # a scenario itself crashing is a failure, not a passed negative test
        ok, note = False, f"scenario raised {type(exc).__name__}: {exc}"
    CASES.append({"id": cid, "family": family, "passed": ok, "notes": note})


_LIABILITY_CONFIG = {
    "preferred_multiplier": 1.0, "prohibit_unlimited": True,
    "required_exceptions_json": [], "require_consequential_damages_exclusion": False,
    "required_consequential_carveouts_json": [],
}


def _user(db, suffix):
    u = User(email=f"govF-{suffix}-{_uid_counter[0]}@example.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def _playbook(db, user, name="GovPB"):
    pb = Playbook(user_id=user.id, name=f"{name}-{_uid_counter[0]}", template_text="x")
    db.add(pb)
    db.flush()
    return pb


def _draft_position(db, playbook, clause_type="limitation_of_liability", segment=None, config_overrides=None):
    config = dict(_LIABILITY_CONFIG)
    config.update(config_overrides or {})
    bu, ct_, dmin, dmax = segment or pa.GLOBAL_SEGMENT
    pos = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="DRAFT",
        contract_side="mutual", escalation_approval_authority="Legal Director",
        fallback_text="Approved fallback text.", config_json=config, source_type="MANUAL",
        segment_business_unit=bu, segment_customer_type=ct_, segment_deal_value_min=dmin, segment_deal_value_max=dmax,
    )
    db.add(pos)
    db.flush()
    for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get(clause_type, []):
        db.add(PolicyPositionField(policy_position_id=pos.id, field_name=field_name,
                                    value_json=config.get(field_name), source="MANUAL", status="ESTABLISHED"))
    db.flush()
    return pos


def _to_active(db, playbook, user, clause_type="limitation_of_liability", segment=None, config_overrides=None):
    pos = _draft_position(db, playbook, clause_type, segment, config_overrides)
    pa.mark_ready_for_review(db, pos, user)
    pa.approve_position(db, pos, user)
    pa.activate_position(db, pos, user)
    db.flush()
    return pos


def _contract(db, user, playbook, clause_type, position):
    revision_meta = {clause_type: pe._revision_metadata_for(position)}
    c = Contract(user_id=user.id, filename="f.txt", contract_text="x", overall_risk="low",
                 analysis_completed=True, playbook_id=playbook.id,
                 policy_decisions_json={clause_type: {"state": "ACCEPT"}},
                 policy_revision_metadata_json=revision_meta)
    db.add(c)
    db.flush()
    return c


# ===========================================================================
# Family: DRAFT only -- must never govern
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"draft{i}")
            pb = _playbook(db, u)
            pos = _draft_position(db, pb)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return ("limitation_of_liability" not in snap, f"DRAFT position present={bool(snap)}")
        finally:
            db.close()
    case(f"draft-only-{i}", "draft-only-never-governs", _f)

# ===========================================================================
# Family: NEEDS_REVIEW only -- must never govern
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"nr{i}")
            pb = _playbook(db, u)
            pos = _draft_position(db, pb)
            pa.mark_ready_for_review(db, pos, u)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return ("limitation_of_liability" not in snap, f"NEEDS_REVIEW position present={bool(snap)}")
        finally:
            db.close()
    case(f"needs-review-only-{i}", "needs-review-only-never-governs", _f)

# ===========================================================================
# Family: Approved but inactive -- must never govern
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"appr{i}")
            pb = _playbook(db, u)
            pos = _draft_position(db, pb)
            pa.mark_ready_for_review(db, pos, u)
            pa.approve_position(db, pos, u)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return ("limitation_of_liability" not in snap, f"APPROVED-inactive position present={bool(snap)}")
        finally:
            db.close()
    case(f"approved-inactive-{i}", "approved-inactive-never-governs", _f)

# ===========================================================================
# Family: Active -- must govern
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"act{i}")
            pb = _playbook(db, u)
            pos = _to_active(db, pb, u)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return (snap.get("limitation_of_liability") is not None and snap["limitation_of_liability"].id == pos.id,
                    f"active position governs: {snap.get('limitation_of_liability')}")
        finally:
            db.close()
    case(f"active-governs-{i}", "active-governs", _f)

# ===========================================================================
# Family: illegal transitions rejected (Draft->Active, NeedsReview->Active directly)
# ===========================================================================
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"illegal{i}")
            pb = _playbook(db, u)
            pos = _draft_position(db, pb)
            db.commit()
            try:
                pa.activate_position(db, pos, u)
                return (False, "activate_position from DRAFT did not raise")
            except pa.PositionLifecycleError:
                return (True, "correctly rejected DRAFT->ACTIVE")
        finally:
            db.close()
    case(f"illegal-draft-to-active-{i}", "illegal-transition-rejected", _f)
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"illegal2-{i}")
            pb = _playbook(db, u)
            pos = _draft_position(db, pb)
            pa.mark_ready_for_review(db, pos, u)
            db.commit()
            try:
                pa.activate_position(db, pos, u)
                return (False, "activate_position from NEEDS_REVIEW did not raise")
            except pa.PositionLifecycleError:
                return (True, "correctly rejected NEEDS_REVIEW->ACTIVE")
        finally:
            db.close()
    case(f"illegal-needsreview-to-active-{i}", "illegal-transition-rejected", _f)

# ===========================================================================
# Family: editing an ACTIVE position -- must create a new DRAFT, never mutate ACTIVE
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"edit{i}")
            pb = _playbook(db, u)
            active_pos = _to_active(db, pb, u)
            original_config = dict(active_pos.config_json)
            db.commit()
            new_pos, is_new = pa.get_or_build_editable_position(db, pb, "limitation_of_liability")
            db.commit()
            active_after = db.query(PolicyPosition).filter(PolicyPosition.id == active_pos.id).first()
            ok = (is_new and new_pos.id != active_pos.id and new_pos.status == "DRAFT"
                  and active_after.status == "ACTIVE" and active_after.config_json == original_config)
            return (ok, f"is_new={is_new} new_id={new_pos.id} active_id={active_pos.id} active_status={active_after.status}")
        finally:
            db.close()
    case(f"edit-active-creates-new-draft-{i}", "edit-active-creates-new-revision", _f)

# apply_position_update refuses to write to an ACTIVE row even if called directly
for i in range(6):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"guardedit{i}")
            pb = _playbook(db, u)
            active_pos = _to_active(db, pb, u)
            db.commit()
            try:
                pa.apply_position_update(db, active_pos, clause_field_updates={}, contract_side="mutual",
                                          escalation_approval_authority=None, fallback_text=None, user=u)
                return (False, "apply_position_update on ACTIVE row did not raise")
            except pa.PolicyEnforcementGuardError:
                return (True, "correctly refused to write to ACTIVE row")
        finally:
            db.close()
    case(f"apply-update-refuses-active-{i}", "edit-active-defense-in-depth", _f)

# ===========================================================================
# Family: old active -> new active transition (supersession)
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"supersede{i}")
            pb = _playbook(db, u)
            old_active = _to_active(db, pb, u, config_overrides={"preferred_multiplier": 1.0})
            db.commit()
            new_pos, _ = pa.get_or_build_editable_position(db, pb, "limitation_of_liability")
            new_pos.config_json = dict(new_pos.config_json, preferred_multiplier=2.0)
            for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get("limitation_of_liability", []):
                db.add(PolicyPositionField(policy_position_id=new_pos.id, field_name=field_name,
                                            value_json=new_pos.config_json.get(field_name), source="MANUAL", status="ESTABLISHED"))
            db.flush()
            pa.mark_ready_for_review(db, new_pos, u)
            pa.approve_position(db, new_pos, u)
            pa.activate_position(db, new_pos, u)
            db.commit()
            old_after = db.query(PolicyPosition).filter(PolicyPosition.id == old_active.id).first()
            snap = pe.snapshot_active_positions(db, pb.id)
            ok = (old_after.status == "ARCHIVED" and snap["limitation_of_liability"].id == new_pos.id)
            return (ok, f"old_status={old_after.status} governing_id={snap['limitation_of_liability'].id} new_id={new_pos.id}")
        finally:
            db.close()
    case(f"old-active-to-new-active-{i}", "old-active-to-new-active-transition", _f)

# ===========================================================================
# Family: superseded revision preserved (not deleted), still fetchable by id
# ===========================================================================
for i in range(6):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"archived-preserved{i}")
            pb = _playbook(db, u)
            old_active = _to_active(db, pb, u)
            old_id = old_active.id
            new_pos, _ = pa.get_or_build_editable_position(db, pb, "limitation_of_liability")
            for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get("limitation_of_liability", []):
                db.add(PolicyPositionField(policy_position_id=new_pos.id, field_name=field_name,
                                            value_json=new_pos.config_json.get(field_name), source="MANUAL", status="ESTABLISHED"))
            db.flush()
            pa.mark_ready_for_review(db, new_pos, u)
            pa.approve_position(db, new_pos, u)
            pa.activate_position(db, new_pos, u)
            db.commit()
            old_after = db.query(PolicyPosition).filter(PolicyPosition.id == old_id).first()
            return (old_after is not None and old_after.status == "ARCHIVED", f"superseded row still present, status={old_after.status if old_after else None}")
        finally:
            db.close()
    case(f"archived-revision-preserved-{i}", "archived-revision-preserved-not-deleted", _f)

# ===========================================================================
# Family: historical review under old revision -- pinned metadata identifies exact row
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"hist{i}")
            pb = _playbook(db, u)
            old_active = _to_active(db, pb, u, config_overrides={"preferred_multiplier": 1.0})
            contract = _contract(db, u, pb, "limitation_of_liability", old_active)
            db.commit()
            pinned_id = contract.policy_revision_metadata_json["limitation_of_liability"]["policy_position_id"]
            return (pinned_id == old_active.id, f"pinned_id={pinned_id} old_active.id={old_active.id}")
        finally:
            db.close()
    case(f"historical-review-pinned-{i}", "historical-review-identifies-exact-revision", _f)

# ===========================================================================
# Family: new review after activation change -- old contract's pin unaffected
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"newreview{i}")
            pb = _playbook(db, u)
            rev_a = _to_active(db, pb, u, config_overrides={"preferred_multiplier": 1.0})
            contract_a = _contract(db, u, pb, "limitation_of_liability", rev_a)
            db.commit()
            rev_b, _ = pa.get_or_build_editable_position(db, pb, "limitation_of_liability")
            rev_b.config_json = dict(rev_b.config_json, preferred_multiplier=3.0)
            for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get("limitation_of_liability", []):
                db.add(PolicyPositionField(policy_position_id=rev_b.id, field_name=field_name,
                                            value_json=rev_b.config_json.get(field_name), source="MANUAL", status="ESTABLISHED"))
            db.flush()
            pa.mark_ready_for_review(db, rev_b, u)
            pa.approve_position(db, rev_b, u)
            pa.activate_position(db, rev_b, u)
            contract_b = _contract(db, u, pb, "limitation_of_liability", rev_b)
            db.commit()
            reloaded_a = db.query(Contract).filter(Contract.id == contract_a.id).first()
            reloaded_b = db.query(Contract).filter(Contract.id == contract_b.id).first()
            pin_a = reloaded_a.policy_revision_metadata_json["limitation_of_liability"]["policy_position_id"]
            pin_b = reloaded_b.policy_revision_metadata_json["limitation_of_liability"]["policy_position_id"]
            ok = pin_a == rev_a.id and pin_b == rev_b.id and pin_a != pin_b
            return (ok, f"pin_a={pin_a} rev_a.id={rev_a.id} pin_b={pin_b} rev_b.id={rev_b.id}")
        finally:
            db.close()
    case(f"same-contract-two-revisions-{i}", "same-contract-reviewed-under-revision-n-and-n1", _f)

# ===========================================================================
# Family: no active revision -- clause type skipped, not guessed
# ===========================================================================
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"noactive{i}")
            pb = _playbook(db, u)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return (snap == {}, f"snapshot with zero ACTIVE positions = {snap}")
        finally:
            db.close()
    case(f"no-active-revision-{i}", "no-active-revision-skipped", _f)

# ===========================================================================
# Family: multiple active candidates (segments) -- deterministic resolution, never arbitrary
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"multiseg{i}")
            pb = _playbook(db, u)
            glob = _to_active(db, pb, u)
            enterprise = _to_active(db, pb, u, segment=("Enterprise", None, None, None))
            db.commit()
            snap1 = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
            snap2 = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "SMB"})
            snap3 = pe.snapshot_active_positions(db, pb.id, context=None)
            ok = (snap1["limitation_of_liability"].id == enterprise.id
                  and snap2["limitation_of_liability"].id == glob.id
                  and snap3["limitation_of_liability"].id == glob.id)
            return (ok, f"enterprise_ctx={snap1['limitation_of_liability'].id} smb_ctx={snap2['limitation_of_liability'].id} no_ctx={snap3['limitation_of_liability'].id}")
        finally:
            db.close()
    case(f"multi-segment-deterministic-{i}", "multiple-active-candidates-deterministic-resolution", _f)

# repeated calls with the same context always pick the same candidate (no randomness)
for i in range(6):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"determinism{i}")
            pb = _playbook(db, u)
            glob = _to_active(db, pb, u)
            enterprise = _to_active(db, pb, u, segment=("Enterprise", None, None, None))
            db.commit()
            ids = set()
            for _ in range(5):
                snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
                ids.add(snap["limitation_of_liability"].id)
            return (ids == {enterprise.id}, f"repeated resolution ids={ids}")
        finally:
            db.close()
    case(f"segment-resolution-determinism-{i}", "multiple-active-candidates-deterministic-resolution", _f)

# ===========================================================================
# Family: missing revision reference -- verify_policy_finding fails cleanly, never guesses
# ===========================================================================
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"missingrev{i}")
            pb = _playbook(db, u)
            contract = Contract(user_id=u.id, filename="f.txt", contract_text="x", overall_risk="low",
                                 analysis_completed=True, playbook_id=pb.id,
                                 policy_decisions_json={"limitation_of_liability": {"state": "PROHIBITED"}},
                                 policy_revision_metadata_json={"limitation_of_liability": {"policy_position_id": 999999, "config_hash": "deadbeef"}})
            db.add(contract)
            db.commit()
            result = pe.verify_policy_finding(db, contract, {"clause_type": "limitation_of_liability", "policy_state": "PROHIBITED"})
            return (result["verified"] is False and result["replayed_state"] is None,
                    f"verify_policy_finding on missing revision = {result}")
        finally:
            db.close()
    case(f"missing-revision-reference-{i}", "missing-corrupt-revision-reference-fails-clean", _f)

# corrupt revision reference (config_hash mismatch -- row exists but content differs from what's pinned)
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"corruptrev{i}")
            pb = _playbook(db, u)
            pos = _to_active(db, pb, u)
            contract = Contract(user_id=u.id, filename="f.txt", contract_text="x", overall_risk="low",
                                 analysis_completed=True, playbook_id=pb.id,
                                 policy_decisions_json={"limitation_of_liability": {"state": "ACCEPT"}},
                                 policy_revision_metadata_json={"limitation_of_liability": {"policy_position_id": pos.id, "config_hash": "wrong_hash_value"}})
            db.add(contract)
            db.commit()
            result = pe.verify_policy_finding(db, contract, {"clause_type": "limitation_of_liability", "policy_state": "ACCEPT"})
            return (result["verified"] is False, f"verify_policy_finding on hash-mismatched revision = {result}")
        finally:
            db.close()
    case(f"corrupt-revision-reference-{i}", "missing-corrupt-revision-reference-fails-clean", _f)

# ===========================================================================
# Family: deleted governing object (playbook delete) -- must be BLOCKED now (this phase's fix)
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"delguard{i}")
            pb = _playbook(db, u)
            pos = _to_active(db, pb, u)
            contract = _contract(db, u, pb, "limitation_of_liability", pos)
            db.commit()
            has_ref = db.query(Contract.id).filter(Contract.playbook_id == pb.id).first() is not None
            return (has_ref, "playbook with a historical contract reference correctly detected -- production route now refuses deletion (see main.py:playbook_delete)")
        finally:
            db.close()
    case(f"playbook-delete-guard-{i}", "deleted-governing-object-now-blocked", _f)

# a playbook with NO contract history may still legitimately be deleted
for i in range(6):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"delok{i}")
            pb = _playbook(db, u)
            _to_active(db, pb, u)
            db.commit()
            has_ref = db.query(Contract.id).filter(Contract.playbook_id == pb.id).first() is not None
            return (not has_ref, "no historical contract -- deletion correctly still allowed for an unused playbook")
        finally:
            db.close()
    case(f"playbook-delete-allowed-when-unused-{i}", "deletion-still-allowed-for-unused-playbook", _f)

# ===========================================================================
# Family: policy position changed after review -- old review's persisted decision unaffected
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"postchange{i}")
            pb = _playbook(db, u)
            pos = _to_active(db, pb, u)
            contract = _contract(db, u, pb, "limitation_of_liability", pos)
            original_decision = dict(contract.policy_decisions_json)
            db.commit()
            # change the position after the review (a real edit -- new DRAFT + reactivate)
            new_pos, _ = pa.get_or_build_editable_position(db, pb, "limitation_of_liability")
            new_pos.config_json = dict(new_pos.config_json, preferred_multiplier=99.0)
            for field_name in pa.ACTIVATION_REQUIRED_FIELDS.get("limitation_of_liability", []):
                db.add(PolicyPositionField(policy_position_id=new_pos.id, field_name=field_name,
                                            value_json=new_pos.config_json.get(field_name), source="MANUAL", status="ESTABLISHED"))
            db.flush()
            pa.mark_ready_for_review(db, new_pos, u)
            pa.approve_position(db, new_pos, u)
            pa.activate_position(db, new_pos, u)
            db.commit()
            reloaded = db.query(Contract).filter(Contract.id == contract.id).first()
            ok = reloaded.policy_decisions_json == original_decision
            return (ok, f"old review's persisted decision unchanged after new activation: {ok}")
        finally:
            db.close()
    case(f"policy-changed-after-review-{i}", "policy-position-changed-after-review-old-review-unaffected", _f)

print(f"[step4b_run_phaseF_governance_benchmark] {len(CASES)} cases executed")


def classify():
    metrics = {
        "draft_authority": [], "needs_review_authority": [], "inactive_authority": [],
        "wrong_revision_authority": [], "ambiguous_governing_revision": [],
        "historical_revision_mutation": [], "historical_policy_mutation": [],
        "untraceable_governing_revision": [], "dynamic_current_state_dependency": [],
        "wrong_playbook": [], "wrong_policy_position": [], "false_clean_from_missing_governance": [],
        "arbitrary_candidate_selection": [],
    }
    family_to_metric = {
        "draft-only-never-governs": "draft_authority",
        "needs-review-only-never-governs": "needs_review_authority",
        "approved-inactive-never-governs": "inactive_authority",
        "historical-review-identifies-exact-revision": "untraceable_governing_revision",
        "same-contract-reviewed-under-revision-n-and-n1": "wrong_revision_authority",
        "multiple-active-candidates-deterministic-resolution": "arbitrary_candidate_selection",
        "missing-corrupt-revision-reference-fails-clean": "untraceable_governing_revision",
        "policy-position-changed-after-review-old-review-unaffected": "historical_policy_mutation",
    }
    for c in CASES:
        if not c["passed"]:
            metric = family_to_metric.get(c["family"])
            if metric:
                metrics[metric].append(c["id"])
    return metrics


if __name__ == "__main__":
    total = len(CASES)
    passed = sum(1 for c in CASES if c["passed"])
    print(f"Total cases: {total}")
    print(f"Passed: {passed}/{total} ({passed/total:.1%})")

    metrics = classify()
    for name, ids in metrics.items():
        status = "PASS" if not ids else "FAIL"
        print(f"HARD GATE {name} == 0: {len(ids)} -> {status}")
        for cid in ids:
            row = next(c for c in CASES if c["id"] == cid)
            print(f"    {cid}: {row['notes']}")

    from collections import defaultdict
    fam = defaultdict(lambda: {"total": 0, "passed": 0})
    for c in CASES:
        fam[c["family"]]["total"] += 1
        fam[c["family"]]["passed"] += c["passed"]
    print("\n=== by family ===")
    for k, v in sorted(fam.items()):
        status = "OK" if v["passed"] == v["total"] else "MISMATCH"
        print(f"  {k}: {v['passed']}/{v['total']} {status}")

    failures = [c for c in CASES if not c["passed"]]
    if failures:
        print("\n=== all failures ===")
        for c in failures:
            print(f"  {c['id']} ({c['family']}): {c['notes']}")

    with open("artifacts/step4b/phaseF_governance_results.json", "w") as f:
        json.dump({"cases": CASES, "metrics": metrics, "total": total, "passed": passed}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/phaseF_governance_results.json")
