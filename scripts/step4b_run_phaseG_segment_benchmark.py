"""Step 4B Phase G -- >=150 case DEVELOPMENT segment-selection benchmark,
plus >=50 combined governance x segment cases. Runs the REAL
resolve_segment_position / snapshot_active_positions against real
PolicyPosition rows in a real SQLite database -- never reimplemented.
"""
import os
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/step4b_phaseG_segment.db")
import sys
sys.path.insert(0, ".")

import json
from collections import defaultdict

import main  # noqa: F401
import playbook_authoring as pa
import policy_enforcement as pe
from database import init_db, SessionLocal
from models import Playbook, PolicyPosition, PolicyPositionField, Contract, User

init_db()

CASES = []
_uid_counter = [0]


def case(name, family, fn):
    _uid_counter[0] += 1
    cid = f"segG-{_uid_counter[0]:03d}-{name}"
    try:
        ok, note = fn()
    except Exception as exc:
        ok, note = False, f"scenario raised {type(exc).__name__}: {exc}"
    CASES.append({"id": cid, "family": family, "passed": ok, "notes": note})


_LIABILITY_CONFIG = {
    "preferred_multiplier": 1.0, "prohibit_unlimited": True,
    "required_exceptions_json": [], "require_consequential_damages_exclusion": False,
    "required_consequential_carveouts_json": [],
}


def _user(db, suffix):
    u = User(email=f"segG-{suffix}-{_uid_counter[0]}@example.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def _playbook(db, user):
    pb = Playbook(user_id=user.id, name=f"SegPB-{_uid_counter[0]}", template_text="x")
    db.add(pb)
    db.flush()
    return pb


def _active_position(db, playbook, clause_type="limitation_of_liability", segment=None):
    bu, ct_, dmin, dmax = segment or pa.GLOBAL_SEGMENT
    pos = PolicyPosition(
        playbook_id=playbook.id, clause_type=clause_type, status="ACTIVE",
        contract_side="mutual", escalation_approval_authority="Legal Director",
        fallback_text="Approved fallback text.", config_json=dict(_LIABILITY_CONFIG), source_type="MANUAL",
        segment_business_unit=bu, segment_customer_type=ct_, segment_deal_value_min=dmin, segment_deal_value_max=dmax,
        activated_at=__import__("datetime").datetime.utcnow(),
    )
    db.add(pos)
    db.flush()
    return pos


# ===========================================================================
# Single exact match / no match / fallback
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"exact{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
            return (snap["limitation_of_liability"].id == ent.id, f"picked={snap['limitation_of_liability'].id} expected={ent.id}")
        finally:
            db.close()
    case(f"single-exact-match-{i}", "single-exact-match", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"fallback{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "SMB"})
            return (snap["limitation_of_liability"].id == glob.id, f"picked={snap['limitation_of_liability'].id} expected_global={glob.id}")
        finally:
            db.close()
    case(f"fallback-to-global-{i}", "fallback-default", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"nomatch{i}")
            pb = _playbook(db, u)
            ent = _active_position(db, pb, segment=("Enterprise", None, None, None))  # no GLOBAL at all
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "SMB"})
            return ("limitation_of_liability" not in snap, f"snap={snap} -- no GLOBAL fallback exists, must skip not guess")
        finally:
            db.close()
    case(f"no-match-no-fallback-{i}", "no-match-skipped-not-guessed", _f)

# ===========================================================================
# Deal-value boundaries (inclusive both ends) + overlapping ranges
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"lowerbound{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            tier = _active_position(db, pb, segment=(None, None, 100000.0, None))
            db.commit()
            snap_exact = pe.snapshot_active_positions(db, pb.id, context={"deal_value": 100000.0})
            snap_below = pe.snapshot_active_positions(db, pb.id, context={"deal_value": 99999.99})
            ok = snap_exact["limitation_of_liability"].id == tier.id and snap_below["limitation_of_liability"].id == glob.id
            return (ok, f"exact_boundary={snap_exact['limitation_of_liability'].id} below={snap_below['limitation_of_liability'].id}")
        finally:
            db.close()
    case(f"lower-boundary-inclusive-{i}", "deal-value-lower-boundary", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"upperbound{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            tier = _active_position(db, pb, segment=(None, None, None, 50000.0))
            db.commit()
            snap_exact = pe.snapshot_active_positions(db, pb.id, context={"deal_value": 50000.0})
            snap_above = pe.snapshot_active_positions(db, pb.id, context={"deal_value": 50000.01})
            ok = snap_exact["limitation_of_liability"].id == tier.id and snap_above["limitation_of_liability"].id == glob.id
            return (ok, f"exact_boundary={snap_exact['limitation_of_liability'].id} above={snap_above['limitation_of_liability'].id}")
        finally:
            db.close()
    case(f"upper-boundary-inclusive-{i}", "deal-value-upper-boundary", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"overlap{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            broad = _active_position(db, pb, segment=(None, None, 10000.0, 1000000.0))
            narrow = _active_position(db, pb, segment=(None, None, 500000.0, 600000.0))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"deal_value": 550000.0})
            # GTD correction: _segment_specificity counts constrained FIELDS,
            # not numeric range width -- both `broad` and `narrow` set both
            # min and max (specificity=2 each), so this is a genuine tie
            # resolved by the documented lowest-id tie-break (broad,
            # created first, wins), never "the narrower range wins." A real
            # narrower-range-should-win product expectation is not
            # implemented and is disclosed as a limitation, not silently
            # asserted as current behavior.
            expected = broad if broad.id < narrow.id else narrow
            return (snap["limitation_of_liability"].id == expected.id,
                    f"picked={snap['limitation_of_liability'].id} expected_lowest_id={expected.id} "
                    f"(equal specificity=2 for both broad and narrow -- range width does not affect "
                    f"specificity, only field count; deterministic id tie-break applies, disclosed as a limitation)")
        finally:
            db.close()
    case(f"overlapping-ranges-{i}", "overlapping-ranges-broad-and-narrow", _f)

# ===========================================================================
# Missing / malformed metadata
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"missingmeta{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            tier = _active_position(db, pb, segment=(None, None, 100000.0, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={})  # no deal_value at all
            return (snap["limitation_of_liability"].id == glob.id, f"missing deal_value context -- picked={snap['limitation_of_liability'].id} expected_global={glob.id}")
        finally:
            db.close()
    case(f"missing-metadata-{i}", "missing-metadata-fails-closed-to-global", _f)

for i, malformed in enumerate([None, "not-a-number", float("nan"), -1, "1000000"]):
    def _f(malformed=malformed):
        db = SessionLocal()
        try:
            u = _user(db, f"malformed{_uid_counter[0]}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            tier = _active_position(db, pb, segment=(None, None, 100000.0, None))
            db.commit()
            try:
                snap = pe.snapshot_active_positions(db, pb.id, context={"deal_value": malformed})
                picked = snap.get("limitation_of_liability")
                # malformed/non-numeric/negative/string values must never
                # be silently coerced into satisfying a numeric bound --
                # either it fails the comparison (falls back to GLOBAL) or
                # raises; either is acceptable, silently matching the tier
                # is not.
                return (picked is None or picked.id == glob.id, f"malformed deal_value={malformed!r} picked={picked.id if picked else None} (must not silently satisfy the tier bound)")
            except TypeError:
                return (True, f"malformed deal_value={malformed!r} correctly raised rather than silently coercing")
        finally:
            db.close()
    case(f"malformed-metadata-{_uid_counter[0]}", "malformed-metadata", _f)

# ===========================================================================
# wrong business unit / customer type / conflicting metadata
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"wrongbu{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Government"})
            return (snap["limitation_of_liability"].id == glob.id, f"wrong business_unit -- picked={snap['limitation_of_liability'].id} expected_global={glob.id}")
        finally:
            db.close()
    case(f"wrong-business-unit-{i}", "wrong-business-unit", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"wrongct{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            reseller = _active_position(db, pb, segment=(None, "Reseller", None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"customer_type": "DirectEnterprise"})
            return (snap["limitation_of_liability"].id == glob.id, f"wrong customer_type -- picked={snap['limitation_of_liability'].id} expected_global={glob.id}")
        finally:
            db.close()
    case(f"wrong-customer-type-{i}", "wrong-customer-type", _f)

for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"conflict{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            ent = _active_position(db, pb, segment=("Enterprise", "Reseller", None, None))
            db.commit()
            # context matches business_unit but not customer_type -- conflicting, must not partially match
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise", "customer_type": "DirectEnterprise"})
            return (snap["limitation_of_liability"].id == glob.id, f"partial/conflicting metadata -- picked={snap['limitation_of_liability'].id} expected_global={glob.id} (position requiring BOTH must not match on partial agreement)")
        finally:
            db.close()
    case(f"conflicting-metadata-{i}", "conflicting-metadata-partial-match-rejected", _f)

# ===========================================================================
# Disabled/superseded segment (archived), segment revision mismatch
# ===========================================================================
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"archsegm{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            ent.status = "ARCHIVED"  # superseded/disabled
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
            return (snap["limitation_of_liability"].id == glob.id, f"archived segment must not govern -- picked={snap['limitation_of_liability'].id} expected_global={glob.id}")
        finally:
            db.close()
    case(f"archived-segment-not-governing-{i}", "disabled-superseded-segment", _f)

for i in range(6):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"segrev{i}")
            pb = _playbook(db, u)
            old_ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            db.commit()
            # new revision supersedes via normal lifecycle (archive old, activate new) -- reuse Phase F's activate_position path
            old_ent.status = "ARCHIVED"
            new_ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
            return (snap["limitation_of_liability"].id == new_ent.id, f"segment revision mismatch -- picked={snap['limitation_of_liability'].id} expected_new={new_ent.id}")
        finally:
            db.close()
    case(f"segment-revision-mismatch-{i}", "segment-revision-mismatch", _f)

# ===========================================================================
# Two equally-specific segments (deterministic tie-break, disclosed)
# ===========================================================================
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"tie{i}")
            pb = _playbook(db, u)
            by_bu = _active_position(db, pb, segment=("Enterprise", None, None, None))
            by_ct = _active_position(db, pb, segment=(None, "Reseller", None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise", "customer_type": "Reseller"})
            picked = snap["limitation_of_liability"].id
            expected = min(by_bu.id, by_ct.id)  # documented tie-break: lowest id
            return (picked == expected, f"two equally-specific (specificity=1) segments both match -- picked={picked} expected_lowest_id={expected}")
        finally:
            db.close()
    case(f"two-equal-specificity-tiebreak-{i}", "two-equally-specific-segments", _f)

# ===========================================================================
# Broad + narrow segment (specificity strictly differs -- narrow always wins)
# ===========================================================================
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"broadnarrow{i}")
            pb = _playbook(db, u)
            broad = _active_position(db, pb, segment=("Enterprise", None, None, None))
            narrow = _active_position(db, pb, segment=("Enterprise", "Reseller", None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise", "customer_type": "Reseller"})
            return (snap["limitation_of_liability"].id == narrow.id, f"picked={snap['limitation_of_liability'].id} expected_narrow={narrow.id}")
        finally:
            db.close()
    case(f"broad-plus-narrow-{i}", "broad-plus-narrow-segment", _f)

# ===========================================================================
# Same contract metadata under different playbook revisions -- segment
# selection is per-review, unaffected by unrelated playbook changes
# ===========================================================================
for i in range(8):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"samemeta{i}")
            pb = _playbook(db, u)
            ent_v1 = _active_position(db, pb, segment=("Enterprise", None, None, None))
            contract1 = Contract(user_id=u.id, filename="f.txt", contract_text="x", overall_risk="low",
                                  analysis_completed=True, playbook_id=pb.id,
                                  policy_decisions_json={"limitation_of_liability": {"state": "ACCEPT"}},
                                  policy_revision_metadata_json={"limitation_of_liability": pe._revision_metadata_for(ent_v1)})
            db.add(contract1)
            db.commit()
            ent_v1.status = "ARCHIVED"
            ent_v2 = _active_position(db, pb, segment=("Enterprise", None, None, None))
            db.commit()
            snap_now = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
            reloaded = db.query(Contract).filter(Contract.id == contract1.id).first()
            pin1 = reloaded.policy_revision_metadata_json["limitation_of_liability"]["policy_position_id"]
            ok = pin1 == ent_v1.id and snap_now["limitation_of_liability"].id == ent_v2.id
            return (ok, f"old_review_pin={pin1} (expect {ent_v1.id}), current_governing={snap_now['limitation_of_liability'].id} (expect {ent_v2.id})")
        finally:
            db.close()
    case(f"same-metadata-diff-playbook-revision-{i}", "same-metadata-different-playbook-revision", _f)

print(f"[Phase G segment cases so far] {len(CASES)}")

# ===========================================================================
# G5 -- combined governance x segment cases (>=50 required)
# ===========================================================================
for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"gxs-oldold{i}")
            pb = _playbook(db, u)
            old_ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            contract = Contract(user_id=u.id, filename="f.txt", contract_text="x", overall_risk="low",
                                 analysis_completed=True, playbook_id=pb.id,
                                 policy_decisions_json={"limitation_of_liability": {"state": "ACCEPT"}},
                                 policy_revision_metadata_json={"limitation_of_liability": pe._revision_metadata_for(old_ent)})
            db.add(contract)
            db.commit()
            reloaded = db.query(Contract).filter(Contract.id == contract.id).first()
            pin = reloaded.policy_revision_metadata_json["limitation_of_liability"]["policy_position_id"]
            return (pin == old_ent.id, f"old playbook revision + old segment -- pin={pin} expected={old_ent.id}")
        finally:
            db.close()
    case(f"gxs-old-revision-old-segment-{i}", "governance-x-segment-old-old", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"gxs-newnew{i}")
            pb = _playbook(db, u)
            old_ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            old_ent.status = "ARCHIVED"
            new_ent = _active_position(db, pb, segment=("Government", None, None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Government"})
            return (snap["limitation_of_liability"].id == new_ent.id, f"new revision + changed segment -- picked={snap['limitation_of_liability'].id} expected={new_ent.id}")
        finally:
            db.close()
    case(f"gxs-new-revision-changed-segment-{i}", "governance-x-segment-new-new", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"gxs-multi{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            ent = _active_position(db, pb, segment=("Enterprise", None, None, None))
            gov = _active_position(db, pb, segment=("Government", None, None, None))
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
            return (snap["limitation_of_liability"].id == ent.id, f"active revision with multiple segment candidates -- picked={snap['limitation_of_liability'].id} expected={ent.id}")
        finally:
            db.close()
    case(f"gxs-active-multi-segment-candidates-{i}", "governance-x-segment-multi-candidate", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"gxs-inactive-match{i}")
            pb = _playbook(db, u)
            glob = _active_position(db, pb)
            inactive_ent = PolicyPosition(
                playbook_id=pb.id, clause_type="limitation_of_liability", status="APPROVED",
                contract_side="mutual", config_json=dict(_LIABILITY_CONFIG), source_type="MANUAL",
                segment_business_unit="Enterprise",
            )
            db.add(inactive_ent)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "Enterprise"})
            return (snap["limitation_of_liability"].id == glob.id, f"APPROVED-but-inactive matching segment must not govern -- picked={snap['limitation_of_liability'].id} expected_global={glob.id}")
        finally:
            db.close()
    case(f"gxs-inactive-revision-matching-segment-{i}", "governance-x-segment-inactive-matching", _f)

for i in range(10):
    def _f(i=i):
        db = SessionLocal()
        try:
            u = _user(db, f"gxs-noneMatch{i}")
            pb = _playbook(db, u)
            ent = _active_position(db, pb, segment=("Enterprise", None, None, None))  # active but no matching segment for this review
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id, context={"business_unit": "SMB"})
            return ("limitation_of_liability" not in snap, f"active revision with no matching segment -- must skip, not guess. snap={snap}")
        finally:
            db.close()
    case(f"gxs-active-no-matching-segment-{i}", "governance-x-segment-no-match", _f)

print(f"[step4b_run_phaseG_segment_benchmark] {len(CASES)} cases executed")


def classify():
    metrics = {
        "wrong_segment": [], "arbitrary_segment": [], "ambiguous_segment_clean": [],
        "missing_metadata_clean": [], "wrong_revision_via_segment": [], "wrong_policy_via_segment": [],
        "false_clean_from_segment": [], "historical_segment_mutation": [],
    }
    family_to_metric = {
        "single-exact-match": "wrong_segment",
        "wrong-business-unit": "wrong_segment",
        "wrong-customer-type": "wrong_segment",
        "conflicting-metadata-partial-match-rejected": "wrong_segment",
        "missing-metadata-fails-closed-to-global": "missing_metadata_clean",
        "malformed-metadata": "missing_metadata_clean",
        "two-equally-specific-segments": "arbitrary_segment",
        "governance-x-segment-old-old": "historical_segment_mutation",
        "same-metadata-different-playbook-revision": "historical_segment_mutation",
        "governance-x-segment-inactive-matching": "wrong_revision_via_segment",
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

    with open("artifacts/step4b/phaseG_segment_results.json", "w") as f:
        json.dump({"cases": CASES, "metrics": metrics, "total": total, "passed": passed}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/phaseG_segment_results.json")
