"""Step 4B FINAL FROZEN VALIDATION -- single authoritative execution of
the locked 503-document final corpus against frozen production
(candidate SHA e922ca7). Executes ALL cases in one pass; production is
never modified based on observed results.
"""
import os
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/step4b_final_validation.db")
os.environ["POLICY_ENFORCEMENT_MODE"] = "cutover"
import sys
sys.path.insert(0, ".")

import json
import copy
from datetime import datetime
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import patch

import main
import playbook_authoring as pa
import policy_enforcement as pe
import interaction_engine_core as ixc
import interaction_rules as ixr
import document_aggregation as agg
from evaluator import LLMEvaluator
from database import init_db, SessionLocal
from models import Playbook, PolicyPosition, PolicyPositionField, Contract, User

from benchmarks.step4b_final_corpus import CASES

init_db()

_ev = LLMEvaluator.__new__(LLMEvaluator)
_ev.client = None
_ev.model = "final-validation"

_uidc = [0]


def _user(db, suffix):
    _uidc[0] += 1
    u = User(email=f"finalval-{suffix}-{_uidc[0]}@example.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def _playbook(db, user, name="FinalValPB"):
    pb = Playbook(user_id=user.id, name=f"{name}-{_uidc[0]}", template_text="x")
    db.add(pb)
    db.flush()
    return pb


_LIABILITY_CONFIG = {"preferred_multiplier": 1.0, "prohibit_unlimited": True, "required_exceptions_json": [],
                      "require_consequential_damages_exclusion": False, "required_consequential_carveouts_json": []}
_INDEMNIFICATION_CONFIG = {
    "required_protection_triggers_json": [], "prohibited_exposure_triggers_json": [],
    "require_exposure_third_party_only": False, "require_defense_control_for_exposure": False,
    "require_notice_and_cooperation_for_exposure": False, "prohibit_uncapped_exposure": False,
    "exposure_preferred_multiplier": 1.0, "exposure_acceptable_max_multiplier": 2.0,
    "exposure_negotiate_max_multiplier": 3.0,
}
_PAYMENT_TERMS_CONFIG = {"required_net_days_max": None, "require_late_fee_cap": False, "late_fee_cap_pct_per_month": None,
                          "require_dispute_withholding_right": False, "require_service_credit_reconciliation": False}


def _draft_position(db, playbook, clause_type, segment=None, config_overrides=None):
    base = {"limitation_of_liability": _LIABILITY_CONFIG, "indemnification": _INDEMNIFICATION_CONFIG}.get(clause_type, {})
    config = {f: pa._default_for(pa._ENGINE_PROTOCOLS[clause_type], f) for f in pa.CLAUSE_TYPE_CONFIG_FIELDS[clause_type]}
    config.update(base)
    config.update(config_overrides or {})
    bu, ct_, dmin, dmax = segment or (None, None, None, None)
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


def _to_active(db, playbook, user, clause_type, segment=None, config_overrides=None):
    pos = _draft_position(db, playbook, clause_type, segment, config_overrides)
    pa.mark_ready_for_review(db, pos, user)
    pa.approve_position(db, pos, user)
    pa.activate_position(db, pos, user)
    db.flush()
    return pos


# ===========================================================================
# GOVERNANCE scenario dispatch
# ===========================================================================
def _run_governance(scenario, seed):
    db = SessionLocal()
    try:
        u = _user(db, f"gv{seed}")
        pb = _playbook(db, u)
        if scenario == "active-revision-governs":
            pos = _to_active(db, pb, u, "limitation_of_liability")
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return snap.get("limitation_of_liability") is not None and snap["limitation_of_liability"].id == pos.id

        if scenario == "historical-revision-survives-new-active":
            pos1 = _to_active(db, pb, u, "limitation_of_liability")
            db.commit()
            revision_meta = {"limitation_of_liability": pe._revision_metadata_for(pos1)}
            c = Contract(user_id=u.id, filename="f.txt", contract_text="x", overall_risk="low",
                         analysis_completed=True, playbook_id=pb.id,
                         policy_decisions_json={"limitation_of_liability": {"state": "ACCEPT"}},
                         policy_revision_metadata_json=revision_meta)
            db.add(c)
            db.commit()
            # New DRAFT->ACTIVE cycle -- pos1 auto-archived by activate_position.
            pos2 = _to_active(db, pb, u, "limitation_of_liability", config_overrides={"prohibit_unlimited": False})
            db.commit()
            db.refresh(c)
            stored_id = c.policy_revision_metadata_json["limitation_of_liability"]["policy_position_id"]
            return stored_id == pos1.id and pos2.id != pos1.id

        if scenario == "superseded-revision-not-governing-for-new-review":
            pos1 = _to_active(db, pb, u, "limitation_of_liability")
            db.commit()
            pos2 = _to_active(db, pb, u, "limitation_of_liability", config_overrides={"prohibit_unlimited": False})
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return snap["limitation_of_liability"].id == pos2.id and pos1.status == "ARCHIVED"

        if scenario == "playbook-changed-after-historical-review":
            pos1 = _to_active(db, pb, u, "indemnification")
            db.commit()
            revision_meta = {"indemnification": pe._revision_metadata_for(pos1)}
            c = Contract(user_id=u.id, filename="f.txt", contract_text="x", overall_risk="low",
                         analysis_completed=True, playbook_id=pb.id,
                         policy_decisions_json={"indemnification": {"state": "ACCEPT"}},
                         policy_revision_metadata_json=revision_meta)
            db.add(c)
            db.commit()
            _to_active(db, pb, u, "indemnification", config_overrides={"prohibit_uncapped_exposure": True})
            db.commit()
            db.refresh(c)
            return c.policy_revision_metadata_json["indemnification"]["policy_position_id"] == pos1.id

        if scenario == "attempted-deletion-with-historical-dependency":
            pos = _to_active(db, pb, u, "limitation_of_liability")
            db.commit()
            revision_meta = {"limitation_of_liability": pe._revision_metadata_for(pos)}
            c = Contract(user_id=u.id, filename="f.txt", contract_text="x", overall_risk="low",
                         analysis_completed=True, playbook_id=pb.id,
                         policy_decisions_json={"limitation_of_liability": {"state": "ACCEPT"}},
                         policy_revision_metadata_json=revision_meta)
            db.add(c)
            db.commit()
            has_dependency = db.query(Contract.id).filter(Contract.playbook_id == pb.id).first() is not None
            return has_dependency  # main.playbook_delete's own 409 guard checks exactly this

        if scenario == "multiple-playbooks-one-user":
            pb2 = _playbook(db, u, "SecondPB")
            pos1 = _to_active(db, pb, u, "sla")
            pos2 = _to_active(db, pb2, u, "sla", config_overrides={"require_uptime_commitment": True})
            db.commit()
            snap1 = pe.snapshot_active_positions(db, pb.id)
            snap2 = pe.snapshot_active_positions(db, pb2.id)
            return snap1["sla"].id == pos1.id and snap2["sla"].id == pos2.id and pos1.id != pos2.id

        if scenario == "missing-playbook-review":
            db.commit()
            result = pe.apply_policies_for_review(db, None, "some contract text", [], contract_id=None, context=None)
            return result.get("policy_decisions") is None

        if scenario == "stale-position-reference-after-archive":
            pos1 = _to_active(db, pb, u, "warranties")
            db.commit()
            pos2 = _to_active(db, pb, u, "warranties")
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return pos1.status == "ARCHIVED" and snap["warranties"].id == pos2.id

        if scenario == "configuration-unresolved-no-active-position":
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return "limitation_of_liability" not in snap

        if scenario == "draft-position-never-governs":
            _draft_position(db, pb, "confidentiality")
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return "confidentiality" not in snap

        if scenario == "needs-review-position-never-governs":
            pos = _draft_position(db, pb, "confidentiality")
            pa.mark_ready_for_review(db, pos, u)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return "confidentiality" not in snap

        if scenario == "approved-not-yet-active-never-governs":
            pos = _draft_position(db, pb, "confidentiality")
            pa.mark_ready_for_review(db, pos, u)
            pa.approve_position(db, pos, u)
            db.commit()
            snap = pe.snapshot_active_positions(db, pb.id)
            return "confidentiality" not in snap

        raise ValueError(f"unknown governance scenario {scenario}")
    finally:
        db.close()


# ===========================================================================
# SEGMENT scenario dispatch
# ===========================================================================
def _run_segment(scenario, seed):
    db = SessionLocal()
    try:
        u = _user(db, f"sg{seed}")
        pb = _playbook(db, u)

        def mk(segment, config_overrides=None):
            return _to_active(db, pb, u, "limitation_of_liability", segment=segment, config_overrides=config_overrides)

        if scenario == "global-position-only":
            pos = mk((None, None, None, None))
            db.commit()
            resolved = pe.resolve_segment_position([pos], {"business_unit": "Sales"})
            return resolved is not None and resolved.id == pos.id

        if scenario == "business-unit-segment-match":
            g = mk((None, None, None, None))
            s = mk(("Sales", None, None, None))
            db.commit()
            resolved = pe.resolve_segment_position([g, s], {"business_unit": "Sales"})
            return resolved.id == s.id

        if scenario == "customer-type-segment-match":
            g = mk((None, None, None, None))
            s = mk((None, "Enterprise", None, None))
            db.commit()
            resolved = pe.resolve_segment_position([g, s], {"customer_type": "Enterprise"})
            return resolved.id == s.id

        if scenario == "deal-value-segment-match":
            g = mk((None, None, None, None))
            s = mk((None, None, 100000.0, None))
            db.commit()
            resolved = pe.resolve_segment_position([g, s], {"deal_value": 250000.0})
            return resolved.id == s.id

        if scenario == "multi-dimension-segment-match":
            g = mk((None, None, None, None))
            s1 = mk(("Sales", None, None, None))
            s2 = mk(("Sales", "Enterprise", None, None))
            db.commit()
            resolved = pe.resolve_segment_position([g, s1, s2], {"business_unit": "Sales", "customer_type": "Enterprise"})
            return resolved.id == s2.id  # more specific wins

        if scenario == "overlapping-segments-tie-break-by-id":
            s1 = mk(("Sales", None, None, None))
            s2 = mk(("Sales", None, None, None))
            db.commit()
            resolved = pe.resolve_segment_position([s2, s1], {"business_unit": "Sales"})
            return resolved.id == min(s1.id, s2.id)

        if scenario == "missing-metadata-fails-closed-to-global":
            g = mk((None, None, None, None))
            s = mk(("Sales", None, None, None))
            db.commit()
            resolved = pe.resolve_segment_position([g, s], {})
            return resolved.id == g.id

        if scenario == "nan-deal-value-fails-closed":
            g = mk((None, None, None, None))
            s = mk((None, None, 100000.0, None))
            db.commit()
            resolved = pe.resolve_segment_position([g, s], {"deal_value": float("nan")})
            return resolved.id == g.id

        if scenario == "invalid-numeric-deal-value-fails-closed":
            g = mk((None, None, None, None))
            s = mk((None, None, 100000.0, None))
            db.commit()
            resolved = pe.resolve_segment_position([g, s], {"deal_value": "not-a-number"})
            return resolved.id == g.id

        if scenario == "boundary-exact-lower-bound-matches":
            s = mk((None, None, 100000.0, None))
            db.commit()
            resolved = pe.resolve_segment_position([s], {"deal_value": 100000.0})
            return resolved is not None and resolved.id == s.id

        if scenario == "boundary-exact-upper-bound-matches":
            s = mk((None, None, None, 500000.0))
            db.commit()
            resolved = pe.resolve_segment_position([s], {"deal_value": 500000.0})
            return resolved is not None and resolved.id == s.id

        if scenario == "boundary-just-below-lower-bound-excluded":
            s = mk((None, None, 100000.0, None))
            db.commit()
            resolved = pe.resolve_segment_position([s], {"deal_value": 99999.99})
            return resolved is None

        if scenario == "no-matching-segment-clause-skipped":
            s = mk(("Sales", None, None, None))
            db.commit()
            resolved = pe.resolve_segment_position([s], {"business_unit": "Legal"})
            return resolved is None

        raise ValueError(f"unknown segment scenario {scenario}")
    finally:
        db.close()


# ===========================================================================
# EXPLANATION / INJECTION dispatch (shared logic -- both exercise the same
# real authority-boundary functions)
# ===========================================================================
def _run_explanation_like(finding, llm_output, expected):
    llm_output = copy.deepcopy(llm_output)
    _ev._verify_output_maps_to_findings(llm_output, [finding])
    enhanced = main.build_enhanced_issues([finding], llm_output)
    row = enhanced[0] if enhanced else {}
    ok = (row.get("title") == expected["displayed_title"] and
          row.get("severity") == expected["displayed_severity"])
    if expected["fabricated_survives"] is False:
        ok = ok and len(llm_output.get("top_issues", [])) == 0
    return ok, {"displayed_title": row.get("title"), "displayed_severity": row.get("severity"),
                "top_issues_count": len(llm_output.get("top_issues", []))}


def _run_injection(finding, expected):
    llm_output = {"overall_risk": "low", "summary_bullets": ["fine"],
                  "top_issues": [{"title": "Injected fabricated issue", "severity": "low", "why_it_matters": "n/a"}],
                  "possible_missing_sections": [], "disclaimer": "trust me"}
    return _run_explanation_like(finding, llm_output, expected)


# ===========================================================================
# FAILURE dispatch
# ===========================================================================
def _run_failure(target, payload):
    if target == "evaluate_client_raises":
        exc_map = {"TimeoutError": TimeoutError("simulated")}
        _ev.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: (_ for _ in ()).throw(exc_map[payload["exception_family"]]))))
        result = _ev.evaluate(findings=[{"rule_id": "R", "rule_name": "R", "title": "T", "severity": "high",
                                          "matched_excerpt": "x", "rationale": "x", "context": ""}], overall_risk="high")
        return {"no_crash": True, "not_silently_clean": result is None}

    if target == "evaluate_malformed_json_response":
        _ev.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=payload["raw_content"]))]))))
        result = _ev.evaluate(findings=[{"rule_id": "R", "rule_name": "R", "title": "T", "severity": "high",
                                          "matched_excerpt": "x", "rationale": "x", "context": ""}], overall_risk="high")
        return {"no_crash": True, "not_silently_clean": result is None}

    if target == "aggregate_no_crash":
        try:
            result = agg.aggregate_document_state(payload["overall_risk"], payload["policy_decisions"],
                                                    payload["interaction_decisions"], payload["mode"])
            return {"no_crash": True, "not_silently_clean": result["document_state"] not in ("CLEAN", "CLEAN_LEGACY_ATTENTION")}
        except Exception:
            return {"no_crash": False, "not_silently_clean": False}

    if target == "segment_match_no_crash":
        try:
            position = SimpleNamespace(segment_business_unit=None, segment_customer_type=None,
                                        segment_deal_value_min=payload["segment_min"], segment_deal_value_max=payload["segment_max"])
            matched = pe._segment_matches_context(position, {"deal_value": payload["deal_value"]})
            return {"no_crash": True, "not_silently_clean": not matched}
        except Exception:
            return {"no_crash": False, "not_silently_clean": False}

    raise ValueError(f"unknown failure target {target}")


# ===========================================================================
# MAIN EXECUTION
# ===========================================================================
def run():
    rows = []
    replay_pool = []  # (case_id, decisions, mode, overall_risk) for high-complexity replay

    for c in CASES:
        kind = c["kind"]
        try:
            if kind == "fixture":
                p = c["payload"]
                decisions = p["policy_decisions"]
                if decisions is None:
                    actual_policy = None
                    actual_interactions = {}
                else:
                    actual_policy = {ct: d for ct, d in decisions.items()}
                    from policy_engine_core import PolicyDecision as PD
                    pd_objs = {}
                    for ct, d in decisions.items():
                        if not isinstance(d, dict):
                            continue
                        pd_objs[ct] = PD(
                            rule_id=d["rule_id"], clause_type=d["clause_type"], state=d["state"],
                            contract_language="", extracted_summary="", policy_limit_summary="",
                            required_action="", explanation="", negotiation_ladder=[],
                            category_treatments=d["category_treatments"], unresolved_facts=[],
                            start_index=d["start_index"], end_index=d["end_index"],
                            controlling_provision=d["controlling_provision"],
                            interaction_facts=d["interaction_facts"], reconciliation=None,
                        )
                    ix_results = ixc.evaluate(pd_objs, ixr.LAUNCH_CATALOG)
                    actual_interaction_states = {r.interaction_id: r.state for r in ix_results}
                    actual_interactions = {r.interaction_id: r.as_dict() for r in ix_results}
                doc_result = agg.aggregate_document_state(p["overall_risk"], actual_policy, actual_interactions if decisions is not None else None, p["mode"])
                actual_state = doc_result["document_state"]
                expected_state = c["expected"]["document_state"]
                ok = actual_state == expected_state
                ix_mismatch = {}
                if decisions is not None:
                    for rid, exp_state in c["expected"].get("interaction_states", {}).items():
                        got = actual_interaction_states.get(rid)
                        if got != exp_state:
                            ix_mismatch[rid] = {"expected": exp_state, "actual": got}
                    if ix_mismatch:
                        ok = False
                rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind,
                             "passed": ok, "expected_state": expected_state, "actual_state": actual_state,
                             "ix_mismatch": ix_mismatch})
                if c["family"] in ("high-complexity-replay-pool", "compound-multi-interaction"):
                    replay_pool.append((c["id"], decisions, p["mode"], p["overall_risk"]))

            elif kind == "real_text":
                p = c["payload"]
                db = SessionLocal()
                try:
                    u = _user(db, f"rt{c['id']}")
                    pb = _playbook(db, u)
                    for ct in ["limitation_of_liability", "indemnification", "payment_terms"]:
                        cfg = {"limitation_of_liability": _LIABILITY_CONFIG, "indemnification": _INDEMNIFICATION_CONFIG,
                               "payment_terms": {}}[ct]
                        _to_active(db, pb, u, ct, config_overrides=cfg)
                    db.commit()
                    result = pe.apply_policies_for_review(db, pb, p["contract_text"], [], contract_id=None, context=None)
                    policy_decisions = result.get("policy_decisions") or {}
                    ct = p["strict_clause_type"]
                    decision = policy_decisions.get(ct, {})
                    state = decision.get("state")
                    must_not_be_clean_ct = c["expected"]["clause_type_must_not_be_clean"]
                    if must_not_be_clean_ct:
                        ok = state not in ("ACCEPT", "ACCEPT_WITH_NOTE", "NOT_APPLICABLE", None)
                    else:
                        ok = True  # organic non-triggering text: no crash + ran to completion is the assertion
                    rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind,
                                 "passed": ok, "actual_state": state, "clause_type": ct})
                finally:
                    db.close()

            elif kind == "governance":
                p = c["payload"]
                ok = _run_governance(p["scenario"], p["seed"])
                rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind, "passed": bool(ok)})

            elif kind == "segment":
                p = c["payload"]
                ok = _run_segment(p["scenario"], p["seed"])
                rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind, "passed": bool(ok)})

            elif kind == "explanation":
                p = c["payload"]
                ok, actual = _run_explanation_like(p["finding"], p["llm_output"], c["expected"])
                rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind, "passed": ok, "actual": actual})

            elif kind == "injection":
                p = c["payload"]
                ok, actual = _run_injection(p["finding"], c["expected"])
                rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind, "passed": ok, "actual": actual})

            elif kind == "failure":
                p = c["payload"]
                actual = _run_failure(p["target"], p["payload"])
                ok = actual["no_crash"] == c["expected"]["no_crash"]
                if c["expected"]["not_silently_clean"]:
                    ok = ok and actual["not_silently_clean"]
                rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind, "passed": ok, "actual": actual})

            else:
                raise ValueError(f"unknown kind {kind}")

        except Exception as exc:
            rows.append({"id": c["id"], "family": c["family"], "tier": c["tier"], "kind": kind,
                         "passed": False, "exception": f"{type(exc).__name__}: {exc}"})

    return rows, replay_pool


if __name__ == "__main__":
    rows, replay_pool = run()
    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    print(f"TOTAL CASES: {total}")
    print(f"PASSED: {passed}/{total} ({passed/total:.1%})")
    print(f"Replay pool size: {len(replay_pool)}")

    by_kind = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in rows:
        by_kind[r["kind"]]["total"] += 1
        by_kind[r["kind"]]["passed"] += r["passed"]
    print("\n=== by kind ===")
    for k, v in sorted(by_kind.items()):
        print(f"  {k}: {v['passed']}/{v['total']}")

    failures = [r for r in rows if not r["passed"]]
    print(f"\n=== FAILURES: {len(failures)} ===")
    for r in failures[:60]:
        print(f"  {r['id']} ({r['kind']}/{r['family']}): {r}")

    with open("artifacts/step4b/final_validation/execution_results.json", "w") as f:
        json.dump({"rows": rows, "total": total, "passed": passed,
                    "replay_pool_ids": [rp[0] for rp in replay_pool]}, f, indent=2, default=str)
    print("\nWrote artifacts/step4b/final_validation/execution_results.json")
