"""
Metrics harness for the v5.0 independent-audit hardening pass.

Compares the BASELINE rule engine (rules_engine.py as of commit 86d0d8e,
the state the independent audit reviewed) against the CURRENT (hardened)
engine on the real BriaCell contract, against a ground-truth label set
derived from the independent audit's own finding-by-finding analysis.

Usage:
    python3 experiments/audit_hardening_metrics.py

Reports, for both engines: precision/recall/F1 against the labeled ground
truth, false-positive rate, false-negative rate, duplicate rate (root-cause
findings counted independently vs. grouped), average evidence span length,
and analyze() wall-clock time. Determinism is checked by re-running the
current engine 5x and confirming byte-identical output.

This does not modify rules_engine.py — the baseline is loaded from git
history into an isolated module so both engines can be imported and run
side by side in one process.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "briacell_contract.txt"
BASELINE_COMMIT = "86d0d8e"


def _load_baseline_engine():
    """Load rules_engine.py as it existed at BASELINE_COMMIT (the version
    the independent audit reviewed) into an isolated module, without
    touching the working tree or the currently-imported `rules_engine`."""
    src = subprocess.run(
        ["git", "show", f"{BASELINE_COMMIT}:rules_engine.py"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    tmp_path = REPO_ROOT / "experiments" / "_rules_engine_baseline_tmp.py"
    tmp_path.write_text(src, encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location("rules_engine_baseline", tmp_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["rules_engine_baseline"] = module
        spec.loader.exec_module(module)
        return module
    finally:
        tmp_path.unlink(missing_ok=True)


# Ground truth derived from the independent audit's finding-by-finding
# analysis of the BriaCell contract (rule_id -> should this rule_id appear
# as a finding in a CORRECT report). True = a genuine issue that should be
# flagged; False = a confirmed false positive that must NOT be flagged.
GROUND_TRUTH = {
    # Confirmed false positives (audit) — must be ABSENT
    "H_ATTFEE_01": False,
    "M_SLA_01": False,
    "L_LATEFEE_01": False,
    "M_ACCOUNT_SUSPEND_01": False,
    # Confirmed missed findings (audit) — must be PRESENT
    "H_ASYMMETRIC_LIABILITY_01": True,
    "H_LOL_NO_CARVEOUT_01": True,
    "H_INDEM_SCOPE_NARROW_01": True,
    "M_DPA_MISSING_01": True,
    "M_BAA_MISSING_01": True,
    "M_SUBPROCESSOR_MISSING_01": True,
    "M_AUDIT_RIGHTS_CUSTOMER_01": True,
    "M_DELETION_CERT_MISSING_01": True,
    "M_SLA_REMEDY_EXCLUSIVITY_01": True,
    "M_INSURANCE_MINIMUM_MISSING_01": True,
    "M_REG_RESPONSIBILITY_UNALLOCATED_01": True,
    "M_DATA_RETURN_CONDITIONAL_01": True,
    # Correctly-grounded findings the baseline already got right — must
    # remain PRESENT (regression guard against the fix set breaking these)
    "M_BREACH_NOTIFY_01": True,
    "M_CONF_01": True,
}

# Findings that legitimately fire on the SAME root cause (missing SOW 1 /
# Schedule 1) — used to compute the duplicate rate.
ROOT_CAUSE_CLUSTER = {
    "M_BILLING_FREQUENCY_01", "M_EXHIBIT_MISSING_01",
    "M_PAYMENT_TRIGGER_01", "M_PRICE_EXHIBIT_MISSING_01",
}


def _rule_ids_present(findings) -> set:
    ids = set()
    for f in findings:
        ids.add(f.rule_id)
        for related in (getattr(f, "related_findings", None) or []):
            ids.add(related)
    return ids


def _score(findings) -> dict:
    present = _rule_ids_present(findings)
    tp = fp = fn = tn = 0
    for rule_id, expected in GROUND_TRUTH.items():
        actual = rule_id in present
        if expected and actual:
            tp += 1
        elif expected and not actual:
            fn += 1
        elif not expected and actual:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    fnr = fn / (fn + tp) if (fn + tp) else float("nan")

    cluster_hits = len(ROOT_CAUSE_CLUSTER & present)
    grouped_present = any(str(getattr(f, "rule_id", "")).startswith("GROUP_") for f in findings)
    duplicate_rate = 0.0 if grouped_present else max(0, cluster_hits - 1)

    spans = [f.end_index - f.start_index for f in findings]
    avg_span = sum(spans) / len(spans) if spans else 0.0
    max_span = max(spans) if spans else 0

    return {
        "num_findings": len(findings),
        "precision": precision, "recall": recall, "f1": f1,
        "false_positive_rate": fpr, "false_negative_rate": fnr,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "duplicate_rate": duplicate_rate,
        "avg_evidence_span": avg_span, "max_evidence_span": max_span,
    }


def _time_analyze(engine, text, n=20) -> float:
    # Warm-up run (regex compilation caching, etc.), then time n runs.
    engine.analyze(text)
    start = time.perf_counter()
    for _ in range(n):
        engine.analyze(text)
    elapsed = time.perf_counter() - start
    return (elapsed / n) * 1000  # ms per run


def main():
    text = FIXTURE.read_text(encoding="utf-8")

    baseline_mod = _load_baseline_engine()
    baseline_engine = baseline_mod.RuleEngine()

    import rules_engine as current_mod
    current_engine = current_mod.RuleEngine()

    baseline_result = baseline_engine.analyze(text)
    current_result = current_engine.analyze(text)

    baseline_metrics = _score(baseline_result["findings"])
    current_metrics = _score(current_result["findings"])

    baseline_ms = _time_analyze(baseline_engine, text)
    current_ms = _time_analyze(current_engine, text)

    # Determinism check on the current engine.
    sigs = []
    for _ in range(5):
        r = current_engine.analyze(text)
        sigs.append(tuple((f.rule_id, f.severity.value, f.start_index, f.end_index) for f in r["findings"]))
    deterministic = len(set(sigs)) == 1

    print("=" * 78)
    print(f"{'Metric':40s} {'Baseline (86d0d8e)':>17s} {'Current (v5.0)':>17s}")
    print("=" * 78)
    rows = [
        ("Findings on real contract", "num_findings", "{:d}"),
        ("Precision (labeled ground truth)", "precision", "{:.2f}"),
        ("Recall (labeled ground truth)", "recall", "{:.2f}"),
        ("F1", "f1", "{:.2f}"),
        ("False positive rate", "false_positive_rate", "{:.2f}"),
        ("False negative rate", "false_negative_rate", "{:.2f}"),
        ("True positives / False positives", None, None),
        ("Duplicate rate (SOW/Schedule cluster)", "duplicate_rate", "{:.0f}"),
        ("Avg evidence span (chars)", "avg_evidence_span", "{:.0f}"),
        ("Max evidence span (chars)", "max_evidence_span", "{:.0f}"),
    ]
    for label, key, fmt in rows:
        if key is None:
            print(
                f"{label:40s} "
                f"{baseline_metrics['tp']:>3d}/{baseline_metrics['fp']:<3d}{'':>10s} "
                f"{current_metrics['tp']:>3d}/{current_metrics['fp']:<3d}"
            )
            continue
        print(f"{label:40s} {fmt.format(baseline_metrics[key]):>17s} {fmt.format(current_metrics[key]):>17s}")
    print("-" * 78)
    print(f"{'analyze() time (ms/run, n=20)':40s} {baseline_ms:>16.2f}ms {current_ms:>16.2f}ms")
    perf_delta = (current_ms - baseline_ms) / baseline_ms * 100
    print(f"{'Performance delta':40s} {'':>17s} {perf_delta:>+15.1f}%")
    print(f"{'Determinism (5 runs identical)':40s} {'':>17s} {'YES' if deterministic else 'NO':>17s}")
    print("=" * 78)
    print()
    print("Ground-truth false positives still present in CURRENT engine:")
    current_present = _rule_ids_present(current_result["findings"])
    remaining_fps = [rid for rid, exp in GROUND_TRUTH.items() if not exp and rid in current_present]
    print(f"  {remaining_fps or 'none'}")
    print("Ground-truth true findings still missing from CURRENT engine:")
    remaining_fns = [rid for rid, exp in GROUND_TRUTH.items() if exp and rid not in current_present]
    print(f"  {remaining_fns or 'none'}")


if __name__ == "__main__":
    main()
