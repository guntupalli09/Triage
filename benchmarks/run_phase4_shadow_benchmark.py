#!/usr/bin/env python3
"""
Phase 4 zero-divergence release gate.

For every case in the existing, independently-labeled 109+-case liability
adversarial corpus (benchmarks/liability_corpus.py — the same corpus that
gates the liability engine's own false-safe metric), this builds a real
PolicyRule row from the case's policy, migrates it to an ACTIVE
PolicyPosition via playbook_authoring.migrate_legacy_policy_rule (the
exact Phase 0 migration path), evaluates the SAME contract text through
both:

    legacy PolicyRule -> liability_policy_engine.evaluate_liability_policy
    migrated ACTIVE PolicyPosition -> policy_enforcement.evaluate_active_policies
        (-> playbook_authoring.build_policy_rule_for_enforcement -> the
           same evaluate_liability_policy)

and requires the two PolicyDecision.as_dict() outputs to match on every
field except `source` (a free-text description of which path produced the
decision, not a legal conclusion). This is deliberately the SAME corpus
used to gate the engine's own accuracy — proving equivalence on cases the
engine is already known to handle well (and cases it's known to abstain
on) is a stronger claim than a fresh, smaller corpus would be.

Release gate: divergence count == 0.

Usage:
    python -m benchmarks.run_phase4_shadow_benchmark
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

os.environ.setdefault("DEV_MODE", "true")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import liability_policy_engine as lpe
import playbook_authoring as pa
import policy_enforcement as pe
from database import Base
from models import Playbook, PolicyRule, User
import analytics_models  # noqa: F401 — registers the full schema

from benchmarks.liability_corpus import CASES, DEFAULT_POLICY


def run_benchmark() -> Dict[str, Any]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    divergences: List[Dict[str, Any]] = []
    evaluation_errors: List[str] = []

    for c in CASES:
        merged = dict(DEFAULT_POLICY)
        merged.update(c["policy_overrides"])

        user = User(email=f"phase4-bench-{c['id']}@example.com", password_hash="x")
        db.add(user)
        db.flush()
        playbook = Playbook(user_id=user.id, name=f"Phase4 Bench {c['id']}", template_text="x")
        db.add(playbook)
        db.flush()
        rule = PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability", **merged)
        db.add(rule)
        db.flush()

        legacy_facts = lpe.extract_liability_facts(c["text"])
        legacy_decision = lpe.evaluate_liability_policy(legacy_facts, rule, source="legacy")

        position = pa.migrate_legacy_policy_rule(db, rule)
        db.flush()
        assert position.status == "ACTIVE", f"{c['id']}: migration did not produce an ACTIVE position"

        migrated_outcomes = pe.evaluate_active_policies(
            db, playbook, c["text"], active_positions={"limitation_of_liability": position},
        )
        outcome = migrated_outcomes[0] if migrated_outcomes else None

        if outcome is None or outcome.error is not None:
            evaluation_errors.append(c["id"])
            divergences.append({"id": c["id"], "diff_fields": ["EVALUATION_ERROR"]})
            continue

        legacy_dict = legacy_decision.as_dict()
        migrated_dict = outcome.decision.as_dict()
        diff_fields = pe._diff_decision_dicts(legacy_dict, migrated_dict)
        if diff_fields:
            divergences.append({
                "id": c["id"], "diff_fields": diff_fields,
                "legacy_state": legacy_dict["state"], "migrated_state": migrated_dict["state"],
            })

    return {
        "total_cases": len(CASES),
        "divergences": divergences,
        "evaluation_errors": evaluation_errors,
        "divergence_count": len(divergences),
    }


def format_report(results: Dict[str, Any]) -> str:
    lines = ["# Phase 4 Shadow-Mode Zero-Divergence Benchmark\n"]
    lines.append(
        f"Corpus: {results['total_cases']} cases (benchmarks/liability_corpus.py, shared with the "
        "liability engine's own false-safe benchmark).\n"
    )
    lines.append(f"Decision-level divergences (legacy PolicyRule vs migrated ACTIVE PolicyPosition): "
                  f"**{results['divergence_count']}**\n")
    if results["divergences"]:
        lines.append("## Divergences (release-blocking)\n")
        for d in results["divergences"]:
            lines.append(f"- `{d['id']}`: fields {d['diff_fields']}"
                          + (f" (legacy={d.get('legacy_state')}, migrated={d.get('migrated_state')})"
                             if "legacy_state" in d else ""))
        lines.append("")
    lines.append("## Release gate\n")
    ok = results["divergence_count"] == 0
    lines.append(f"- {'PASS' if ok else 'FAIL'} — decision-state divergence = 0")
    lines.append(f"- {'PASS' if ok else 'FAIL'} — evidence/provenance semantic divergence = 0")
    lines.append(f"- {'PASS' if ok else 'FAIL'} — redline/fallback divergence = 0")
    lines.append("")
    lines.append(f"**Overall: {'PASS' if ok else 'FAIL'}**")
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_benchmark()
    report = format_report(results)
    print(report)
    if results["divergence_count"]:
        sys.exit(1)
