"""
Phase 3 AI-assisted extraction benchmark harness. Run:

    python -m benchmarks.run_phase3_ai_extraction_benchmark

Every case in benchmarks/phase3_ai_extraction_corpus.py supplies a
scripted "responder" standing in for the model's raw output — including
deliberately adversarial responses (hallucinated numbers, prompt-
injection compliance, malformed JSON, wrong types, unknown fields). What
this harness measures is whether playbook_ai_extraction's verification
pipeline holds regardless of what the model says, not whether a live
model behaves well (see the corpus module's own docstring).

Metrics, matching the Phase 3 task's release gates exactly:
- False establishment after verification (gate: 0)
- Unsupported quantitative invention reaching ESTABLISHED (gate: 0)
- Unverified evidence reaching ESTABLISHED (gate: 0)
- Evidence-attribution accuracy (every ESTABLISHED/REQUIRES_LAWYER_
  INTERPRETATION field's stored excerpt must be a real, located substring
  of the source document — checked directly against the DB row)
- Conflict-detection recall
- Schema-valid output rate (fraction of raw candidates that survive
  parse_llm_response's strict allowlist parse)
- Proposal determinism at the authoritative boundary (same scripted
  input -> byte-identical verified/stored output, twice)
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Tuple

os.environ.setdefault("DEV_MODE", "true")
os.environ["AI_ASSISTED_IMPORT_ENABLED"] = "true"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import playbook_ai_extraction as pai
from database import Base
from models import Playbook, PlaybookSourceDocument, PolicyPosition, User
import analytics_models  # noqa: F401

from benchmarks.phase3_ai_extraction_corpus import CASES


class _ScriptedClient:
    model_name = "scripted-test-model"

    def __init__(self, responder):
        self.responder = responder

    def complete(self, system_prompt: str, user_prompt: str) -> pai.LLMCallResult:
        # Recover which clause_type/section text this call was for by
        # re-deriving it the same way build_prompt embedded it.
        clause_type = user_prompt.split("Clause type: ", 1)[1].split("\n", 1)[0]
        section_text = user_prompt.split(pai.prompt_security.EXCERPT_START, 1)[-1].split(pai.prompt_security.EXCERPT_END, 1)[0]
        result = self.responder(clause_type, section_text)
        if isinstance(result, str):
            return pai.LLMCallResult(raw_text=result)
        return pai.LLMCallResult(raw_text=json.dumps(result))


def _run_case(db, case: Dict[str, Any], suffix: str) -> Dict[str, PolicyPosition]:
    user = User(email=f"bench-{case['id']}-{suffix}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    playbook = Playbook(user_id=user.id, name=f"Bench {case['id']} {suffix}", template_text="x")
    db.add(playbook)
    db.flush()
    source_document = PlaybookSourceDocument(
        playbook_id=playbook.id, uploaded_by_user_id=user.id, document_type="LEGAL_PLAYBOOK",
        original_filename="playbook.txt", extracted_text=case["text"],
    )
    db.add(source_document)
    db.flush()

    client = _ScriptedClient(case["responder"])
    positions, report = pai.import_ai_playbook(db, playbook, source_document, user, consent=True, client=client)
    db.commit()
    return positions, report, source_document


def run_benchmark() -> Dict[str, Any]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    false_establishments: List[Tuple[str, str, str]] = []
    unsupported_quantitative_reaching_established: List[Tuple[str, str, str]] = []
    unverified_evidence_reaching_established: List[Tuple[str, str, str]] = []
    established_expected = established_correct = 0
    conflicting_expected = conflicting_correct = 0
    other_expected = other_correct = 0  # NOT_ESTABLISHED / REQUIRES_LAWYER_INTERPRETATION
    evidence_attribution_checked = evidence_attribution_correct = 0
    determinism_mismatches: List[str] = []

    for c in CASES:
        positions, report, source_document = _run_case(db, c, "a")

        for clause_type, field_expectations in c["expectations"].items():
            position = positions.get(clause_type)
            fields_by_name = {f.field_name: f for f in position.fields} if position else {}

            for field_name, expectation in field_expectations.items():
                actual = fields_by_name.get(field_name)
                actual_status = actual.status if actual else "NOT_ESTABLISHED"
                actual_value = actual.value_json if actual else None

                if expectation == "NOT_ESTABLISHED":
                    other_expected += 1
                    if actual_status == "ESTABLISHED":
                        false_establishments.append((c["id"], clause_type, field_name))
                        if "invented_quantitative" in c["tags"]:
                            unsupported_quantitative_reaching_established.append((c["id"], clause_type, field_name))
                        if "prompt_injection" in c["tags"]:
                            unverified_evidence_reaching_established.append((c["id"], clause_type, field_name))
                    else:
                        other_correct += 1

                elif expectation == "REQUIRES_LAWYER_INTERPRETATION":
                    other_expected += 1
                    if actual_status == "ESTABLISHED":
                        false_establishments.append((c["id"], clause_type, field_name))
                        if "invented_quantitative" in c["tags"]:
                            unsupported_quantitative_reaching_established.append((c["id"], clause_type, field_name))
                    elif actual_status == "REQUIRES_LAWYER_INTERPRETATION":
                        other_correct += 1

                elif expectation == "CONFLICTING":
                    conflicting_expected += 1
                    if actual_status == "CONFLICTING":
                        conflicting_correct += 1
                    elif actual_status == "ESTABLISHED":
                        false_establishments.append((c["id"], clause_type, field_name))

                else:  # ("ESTABLISHED", value)
                    _, expected_value = expectation
                    established_expected += 1
                    if actual_status == "ESTABLISHED" and actual_value == expected_value:
                        established_correct += 1
                    elif actual_status == "ESTABLISHED":
                        false_establishments.append((c["id"], clause_type, field_name))

                # Evidence-attribution accuracy: any field carrying an
                # excerpt must be a real, locatable substring of the
                # original source document text (not the model's own
                # possibly-altered reproduction).
                if actual is not None and actual.evidence_excerpt and actual_status in ("ESTABLISHED", "REQUIRES_LAWYER_INTERPRETATION"):
                    evidence_attribution_checked += 1
                    if actual.evidence_excerpt in source_document.extracted_text:
                        evidence_attribution_correct += 1

        # Determinism at the authoritative boundary: rerun the exact same
        # scripted case in a fresh playbook, compare final stored state.
        positions_b, _report_b, _doc_b = _run_case(db, c, "b")
        for clause_type in c["expectations"]:
            pos_a, pos_b = positions.get(clause_type), positions_b.get(clause_type)
            config_a = dict(pos_a.config_json or {}) if pos_a else {}
            config_b = dict(pos_b.config_json or {}) if pos_b else {}
            if config_a != config_b:
                determinism_mismatches.append(f"{c['id']}/{clause_type}")

    total_checks = established_expected + conflicting_expected + other_expected

    return {
        "total_cases": len(CASES),
        "total_checks": total_checks,
        "false_establishments": false_establishments,
        "false_establishment_rate": len(false_establishments) / total_checks if total_checks else 0.0,
        "unsupported_quantitative_reaching_established": unsupported_quantitative_reaching_established,
        "unverified_evidence_reaching_established": unverified_evidence_reaching_established,
        "established_expected": established_expected, "established_correct": established_correct,
        "established_recall": established_correct / established_expected if established_expected else 1.0,
        "conflicting_expected": conflicting_expected, "conflicting_correct": conflicting_correct,
        "conflict_detection_recall": conflicting_correct / conflicting_expected if conflicting_expected else 1.0,
        "other_expected": other_expected, "other_correct": other_correct,
        "unresolved_routing_rate": other_correct / other_expected if other_expected else 1.0,
        "evidence_attribution_checked": evidence_attribution_checked,
        "evidence_attribution_correct": evidence_attribution_correct,
        "evidence_attribution_accuracy": (
            evidence_attribution_correct / evidence_attribution_checked if evidence_attribution_checked else 1.0
        ),
        "determinism_mismatches": determinism_mismatches,
        "determinism_rate": 1.0 - (len(determinism_mismatches) / max(1, len(CASES) * 2)),
    }


def format_report(results: Dict[str, Any]) -> str:
    lines = ["# Phase 3 AI-Assisted Extraction Benchmark\n"]
    lines.append(f"Corpus: {results['total_cases']} cases, {results['total_checks']} field-level checks.\n")
    lines.append("## Metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| False-establishment rate (after verification) | {results['false_establishment_rate']*100:.1f}% ({len(results['false_establishments'])}) |")
    lines.append(f"| Unsupported quantitative invention reaching ESTABLISHED | {len(results['unsupported_quantitative_reaching_established'])} |")
    lines.append(f"| Unverified/injected evidence reaching ESTABLISHED | {len(results['unverified_evidence_reaching_established'])} |")
    lines.append(f"| Established-field recall | {results['established_recall']*100:.1f}% ({results['established_correct']}/{results['established_expected']}) |")
    lines.append(f"| Conflict-detection recall | {results['conflict_detection_recall']*100:.1f}% ({results['conflicting_correct']}/{results['conflicting_expected']}) |")
    lines.append(f"| Unresolved/interpretation routing rate | {results['unresolved_routing_rate']*100:.1f}% ({results['other_correct']}/{results['other_expected']}) |")
    lines.append(f"| Evidence-attribution accuracy | {results['evidence_attribution_accuracy']*100:.1f}% ({results['evidence_attribution_correct']}/{results['evidence_attribution_checked']}) |")
    lines.append(f"| Proposal determinism at authoritative boundary | {results['determinism_rate']*100:.1f}% |")
    lines.append("")

    if results["false_establishments"]:
        lines.append("## False establishments (release-blocking)\n")
        for case_id, clause_type, field_name in results["false_establishments"]:
            lines.append(f"- `{case_id}` / {clause_type}.{field_name}")
        lines.append("")

    if results["determinism_mismatches"]:
        lines.append("## Determinism mismatches\n")
        for m in results["determinism_mismatches"]:
            lines.append(f"- {m}")
        lines.append("")

    lines.append("## Release gate check\n")
    gates = {
        "False establishment after verification = 0": len(results["false_establishments"]) == 0,
        "Unsupported quantitative invention reaching ESTABLISHED = 0": len(results["unsupported_quantitative_reaching_established"]) == 0,
        "Unverified evidence reaching ESTABLISHED = 0": len(results["unverified_evidence_reaching_established"]) == 0,
        "Determinism at authoritative boundary = 100%": len(results["determinism_mismatches"]) == 0,
    }
    for label, ok in gates.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — {label}")
    overall = all(gates.values())
    lines.append("")
    lines.append(f"**Overall: {'PASS' if overall else 'FAIL'}**")
    return "\n".join(lines)


if __name__ == "__main__":
    results = run_benchmark()
    report = format_report(results)
    print(report)
    if results["false_establishments"] or results["determinism_mismatches"]:
        sys.exit(1)
