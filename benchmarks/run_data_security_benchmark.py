#!/usr/bin/env python3
"""
Benchmark harness for the Data Protection / Security policy engine —
adapter #7. Structurally mirrors run_confidentiality_benchmark.py.

Usage:
    python3 benchmarks/run_data_security_benchmark.py [--out FILE.md]

Exit code is non-zero only when the false-safe count is non-zero.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import data_security_policy_engine as dse
import policy_engine_core as core
from benchmarks.data_security_corpus import CASES, DEFAULT_POLICY


@dataclass
class Policy:
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    require_processor_role: bool
    prohibit_unrestricted_subprocessors: bool
    require_subprocessor_notice_or_consent: str
    preferred_breach_notification_hours: Optional[float]
    acceptable_max_breach_notification_hours: Optional[float]
    negotiate_max_breach_notification_hours: Optional[float]
    require_fixed_breach_notification_period: bool
    require_international_transfer_safeguard: bool
    require_data_residency: bool
    required_data_residency_regions_json: Optional[List[str]]
    require_deletion_or_return: bool
    max_retention_days: Optional[float]
    require_audit_rights: bool
    require_named_security_certification: bool
    require_cooperation_obligation: bool
    require_confidentiality_of_personal_data: bool


def _build_policy(overrides: Dict[str, Any]) -> Policy:
    merged = dict(DEFAULT_POLICY)
    merged.update(overrides)
    return Policy(**merged)


def run() -> Dict[str, Any]:
    results = []
    for c in CASES:
        policy = _build_policy(c["policy_overrides"])
        facts = dse.extract_data_security_facts(c["text"])
        decision = dse.evaluate_data_security_policy(facts, policy, source="Benchmark v1")

        row: Dict[str, Any] = {
            "id": c["id"], "tags": c["tags"], "notes": c["notes"],
            "expected_state": c["expected_state"], "actual_state": decision.state,
            "state_correct": decision.state == c["expected_state"],
        }

        clause_detected = facts is not None and facts.clause_found
        expected_clause_detected = c["expected_state"] != core.NOT_APPLICABLE
        row["provision_detection_correct"] = clause_detected == expected_clause_detected

        row["false_safe"] = core.is_false_safe(c["expected_state"], decision.state)
        row["false_escalation"] = core.is_false_escalation(c["expected_state"], decision.state)

        def _evaluate_once(text=c["text"], policy=policy):
            f = dse.extract_data_security_facts(text)
            return dse.evaluate_data_security_policy(f, policy, source="Benchmark v1")

        row["deterministic"] = core.check_deterministic(_evaluate_once, repeats=5)

        results.append(row)
    return {"rows": results}


def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
    rows = data["rows"]
    n = len(rows)

    provision_correct = sum(1 for r in rows if r["provision_detection_correct"])
    state_correct = sum(1 for r in rows if r["state_correct"])

    requires_review_expected = [r for r in rows if r["expected_state"] == core.REQUIRES_REVIEW]

    false_safe_rows = [r for r in rows if r["false_safe"]]
    false_escalation_rows = [r for r in rows if r["false_escalation"]]
    non_deterministic_rows = [r for r in rows if not r["deterministic"]]

    return {
        "total_cases": n,
        "provision_detection_accuracy": provision_correct / n if n else 0.0,
        "policy_state_accuracy": state_correct / n if n else 0.0,
        "ambiguity_recall": (
            len([r for r in requires_review_expected if r["actual_state"] == core.REQUIRES_REVIEW])
            / len(requires_review_expected) if requires_review_expected else None
        ),
        "requires_review_expected_n": len(requires_review_expected),
        "false_safe_count": len(false_safe_rows),
        "false_safe_rows": false_safe_rows,
        "false_escalation_count": len(false_escalation_rows),
        "false_escalation_rows": false_escalation_rows,
        "non_deterministic_count": len(non_deterministic_rows),
        "non_deterministic_rows": non_deterministic_rows,
    }


def failures_by_tag(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    by_tag: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in data["rows"]:
        is_failure = not r["state_correct"] or not r["provision_detection_correct"]
        if is_failure:
            for tag in r["tags"]:
                by_tag[tag].append(r)
    return by_tag


def render_report(data: Dict[str, Any], summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Data Protection / Security Policy Engine — Benchmark Report\n")
    lines.append(f"Corpus size: **{summary['total_cases']}** cases across "
                  f"{len({t for r in data['rows'] for t in r['tags']})} drafting-pattern tags. "
                  f"Adapter #7 — see data_security_policy_engine.py module docstring.\n")

    fs = summary["false_safe_count"]
    lines.append("## Headline safety metric\n")
    lines.append(f"**False-safe rate: {fs} / {summary['total_cases']} ({fs / summary['total_cases']:.1%})**\n")
    if fs:
        for r in summary["false_safe_rows"]:
            lines.append(f"- `{r['id']}` (tags: {', '.join(r['tags'])}) — expected `{r['expected_state']}`, got `{r['actual_state']}`")
        lines.append("")
    else:
        lines.append("Zero false-safe cases in this run.\n")

    fe = summary["false_escalation_count"]
    lines.append("## False-escalation\n")
    lines.append(f"**False-escalation rate: {fe} / {summary['total_cases']} ({fe / summary['total_cases']:.1%})**\n")
    if fe:
        for r in summary["false_escalation_rows"]:
            lines.append(f"- `{r['id']}` (tags: {', '.join(r['tags'])}) — expected `{r['expected_state']}`, got `{r['actual_state']}`")
        lines.append("")
    else:
        lines.append("Zero false-escalation cases in this run.\n")

    determinism_pct = 1 - summary["non_deterministic_count"] / summary["total_cases"]

    lines.append("## Metrics\n")
    lines.append("| Metric | Result | Scored on |")
    lines.append("|---|---|---|")
    lines.append(f"| Provision detection | {summary['provision_detection_accuracy']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| Policy-state accuracy | {summary['policy_state_accuracy']:.1%} | {summary['total_cases']} (all cases) |")
    if summary["ambiguity_recall"] is not None:
        lines.append(f"| Ambiguity (REQUIRES_REVIEW) recall | {summary['ambiguity_recall']:.1%} | {summary['requires_review_expected_n']} |")
    lines.append(f"| False-safe rate | {fs / summary['total_cases']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| False-escalation rate | {fe / summary['total_cases']:.1%} | {summary['total_cases']} (all cases) |")
    lines.append(f"| Determinism (5x repeat) | {determinism_pct:.1%} | {summary['total_cases']} (all cases) |")
    lines.append("")

    lines.append("## Release gate check\n")
    gates = [
        ("False-safe = 0", fs == 0, str(fs)),
        ("False-escalation = 0", fe == 0, str(fe)),
        ("Determinism = 100%", determinism_pct == 1.0, f"{determinism_pct:.1%}"),
        ("Policy-state accuracy > 95%", summary["policy_state_accuracy"] > 0.95, f"{summary['policy_state_accuracy']:.1%}"),
    ]
    for name, passed, value in gates:
        lines.append(f"- {'PASS' if passed else 'FAIL'} — {name} (actual: {value})")
    lines.append("")

    if summary["non_deterministic_count"]:
        lines.append("### Non-deterministic cases\n")
        for r in summary["non_deterministic_rows"]:
            lines.append(f"- `{r['id']}`")
        lines.append("")

    lines.append("## Failures by drafting pattern\n")
    by_tag = failures_by_tag(data)
    if not by_tag:
        lines.append("None.\n")
    for tag in sorted(by_tag, key=lambda t: -len(by_tag[t])):
        rows = by_tag[tag]
        lines.append(f"### `{tag}` — {len(rows)} failing case(s)\n")
        for r in rows:
            detail = [f"expected `{r['expected_state']}`, got `{r['actual_state']}`"]
            if not r["provision_detection_correct"]:
                detail.append("provision-detection mismatch")
            marker = " ⚠️ FALSE-SAFE" if r["false_safe"] else (" ⚠️ FALSE-ESCALATION" if r["false_escalation"] else "")
            lines.append(f"- `{r['id']}`{marker}: {'; '.join(detail)}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    data = run()
    summary = summarize(data)
    report = render_report(data, summary)
    print(report)

    if args.out:
        Path(args.out).write_text(report)
        print(f"\nReport written to {args.out}", file=sys.stderr)

    if summary["false_safe_count"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
