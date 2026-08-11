"""
Phase 2 deterministic-extraction benchmark harness. Run:

    python -m benchmarks.run_phase2_extraction_benchmark

Measures, against benchmarks/phase2_extraction_corpus.py's hand-labeled
expectations:

- **False-establishment rate** (release gate: must be 0) — the source
  document does not establish a field the way the corpus says it should
  (NOT_ESTABLISHED/CONFLICTING expected but ESTABLISHED produced, or
  ESTABLISHED with the wrong value produced). This is the Phase 2
  analogue of the six policy engines' false-safe gate.
- Established-field precision/recall
- Conflict-detection recall
- Unsupported/unresolved routing rate (of fields correctly left
  NOT_ESTABLISHED)
- Proposal determinism (two independent runs must match exactly)
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Tuple

import assignment_policy_engine as ape
import confidentiality_policy_engine as cpe
import governing_law_policy_engine as gpe
import indemnification_policy_engine as ipe
import liability_policy_engine as lpe
import playbook_extraction as pex
import termination_policy_engine as tpe

from benchmarks.phase2_extraction_corpus import CASES

_EXTRACT_FUNCS = {
    "limitation_of_liability": lpe.extract_liability_facts,
    "indemnification": ipe.extract_indemnification_facts,
    "termination": tpe.extract_termination_facts,
    "confidentiality": cpe.extract_confidentiality_facts,
    "assignment": ape.extract_assignment_facts,
    "governing_law": gpe.extract_governing_law_facts,
}


def _run_case(case: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    results = {}
    for clause_type in case["expectations"]:
        facts = _EXTRACT_FUNCS[clause_type](case["text"])
        results[clause_type] = pex.propose_fields(clause_type, facts, case["contract_side"])
    return results


def run_benchmark() -> Dict[str, Any]:
    false_establishments: List[Tuple[str, str, str, str, str]] = []
    established_expected = established_correct = 0
    conflicting_expected = conflicting_correct = 0
    not_established_expected = not_established_correct = 0

    for c in CASES:
        results = _run_case(c)
        for clause_type, field_expectations in c["expectations"].items():
            proposed = results[clause_type]
            for field_name, expectation in field_expectations.items():
                actual = proposed[field_name]

                if expectation == "NOT_ESTABLISHED":
                    not_established_expected += 1
                    if actual.status == "ESTABLISHED":
                        false_establishments.append((c["id"], clause_type, field_name, "NOT_ESTABLISHED", f"ESTABLISHED({actual.value!r})"))
                    else:
                        not_established_correct += 1

                elif expectation == "CONFLICTING":
                    conflicting_expected += 1
                    if actual.status == "CONFLICTING":
                        conflicting_correct += 1
                    elif actual.status == "ESTABLISHED":
                        false_establishments.append((c["id"], clause_type, field_name, "CONFLICTING", f"ESTABLISHED({actual.value!r})"))

                else:  # ("ESTABLISHED", value)
                    _, expected_value = expectation
                    established_expected += 1
                    if actual.status == "ESTABLISHED":
                        if actual.value == expected_value:
                            established_correct += 1
                        else:
                            false_establishments.append((
                                c["id"], clause_type, field_name,
                                f"ESTABLISHED({expected_value!r})", f"ESTABLISHED({actual.value!r})",
                            ))
                    # actual NOT_ESTABLISHED/CONFLICTING when ESTABLISHED
                    # was expected is a recall miss, not counted as a false
                    # establishment -- favoring NOT_ESTABLISHED over an
                    # unsupported inference is the explicitly safe
                    # direction per the task, never penalized as unsafe.

    # Determinism: two fully independent passes over the whole corpus.
    determinism_mismatches: List[Tuple[str, str, str]] = []
    pass_a = [_run_case(c) for c in CASES]
    pass_b = [_run_case(c) for c in CASES]
    for c, ra, rb in zip(CASES, pass_a, pass_b):
        for clause_type, field_expectations in c["expectations"].items():
            for field_name in field_expectations:
                a, b = ra[clause_type][field_name], rb[clause_type][field_name]
                if (a.status, a.value, a.evidence_excerpt) != (b.status, b.value, b.evidence_excerpt):
                    determinism_mismatches.append((c["id"], clause_type, field_name))

    total_checks = established_expected + conflicting_expected + not_established_expected

    return {
        "total_cases": len(CASES),
        "total_checks": total_checks,
        "false_establishments": false_establishments,
        "false_establishment_rate": len(false_establishments) / total_checks if total_checks else 0.0,
        "established_expected": established_expected,
        "established_correct": established_correct,
        "established_precision": (
            established_correct / (established_correct + sum(1 for f in false_establishments if f[3].startswith("ESTABLISHED")))
            if (established_correct + sum(1 for f in false_establishments if f[3].startswith("ESTABLISHED"))) else 1.0
        ),
        "established_recall": established_correct / established_expected if established_expected else 1.0,
        "conflicting_expected": conflicting_expected,
        "conflicting_correct": conflicting_correct,
        "conflict_detection_recall": conflicting_correct / conflicting_expected if conflicting_expected else 1.0,
        "not_established_expected": not_established_expected,
        "not_established_correct": not_established_correct,
        "unresolved_routing_rate": not_established_correct / not_established_expected if not_established_expected else 1.0,
        "determinism_mismatches": determinism_mismatches,
        "determinism_rate": 1.0 - (len(determinism_mismatches) / total_checks if total_checks else 0.0),
    }


def format_report(results: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Phase 2 Deterministic Extraction Benchmark\n")
    lines.append(f"Corpus: {results['total_cases']} cases, {results['total_checks']} field-level checks.\n")

    lines.append("## Metrics\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| False-establishment rate | {results['false_establishment_rate']*100:.1f}% ({len(results['false_establishments'])} case(s)) |")
    lines.append(f"| Established-field precision | {results['established_precision']*100:.1f}% |")
    lines.append(f"| Established-field recall | {results['established_recall']*100:.1f}% ({results['established_correct']}/{results['established_expected']}) |")
    lines.append(f"| Conflict-detection recall | {results['conflict_detection_recall']*100:.1f}% ({results['conflicting_correct']}/{results['conflicting_expected']}) |")
    lines.append(f"| Unresolved/unsupported routing rate | {results['unresolved_routing_rate']*100:.1f}% ({results['not_established_correct']}/{results['not_established_expected']}) |")
    lines.append(f"| Determinism (2x repeat) | {results['determinism_rate']*100:.1f}% |")
    lines.append("")

    if results["false_establishments"]:
        lines.append("## False establishments (release-blocking)\n")
        for case_id, clause_type, field_name, expected, actual in results["false_establishments"]:
            lines.append(f"- `{case_id}` / {clause_type}.{field_name}: expected {expected}, got {actual}")
        lines.append("")

    if results["determinism_mismatches"]:
        lines.append("## Determinism mismatches\n")
        for case_id, clause_type, field_name in results["determinism_mismatches"]:
            lines.append(f"- `{case_id}` / {clause_type}.{field_name}")
        lines.append("")

    lines.append("## Release gate check\n")
    gate_pass = len(results["false_establishments"]) == 0
    determinism_pass = len(results["determinism_mismatches"]) == 0
    lines.append(f"- {'PASS' if gate_pass else 'FAIL'} — False establishment = 0 (actual: {len(results['false_establishments'])})")
    lines.append(f"- {'PASS' if determinism_pass else 'FAIL'} — Determinism = 100% (actual: {results['determinism_rate']*100:.1f}%)")
    lines.append("")
    lines.append(f"**Overall: {'PASS' if gate_pass and determinism_pass else 'FAIL'}**")

    return "\n".join(lines)


if __name__ == "__main__":
    results = run_benchmark()
    report = format_report(results)
    print(report)
    if results["false_establishments"] or results["determinism_mismatches"]:
        sys.exit(1)
