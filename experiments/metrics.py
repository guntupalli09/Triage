"""
Metrics computation for experiments.
"""
from typing import List, Dict, Any, Tuple
from experiments.normalize import normalize_hybrid_findings, normalize_baseline_findings


def check_determinism_hybrid(run_outputs: List[Dict[str, Any]]) -> bool:
    """Check if all hybrid runs produce identical normalized findings."""
    if len(run_outputs) < 2:
        return True
    
    normalized_sets = [normalize_hybrid_findings(run) for run in run_outputs]
    first_set = normalized_sets[0]
    
    for other_set in normalized_sets[1:]:
        if first_set != other_set:
            return False
    return True


def check_determinism_baseline(run_outputs: List[Dict[str, Any]]) -> bool:
    """Check if all baseline runs produce identical normalized findings."""
    if len(run_outputs) < 2:
        return True
    
    normalized_sets = [normalize_baseline_findings(run) for run in run_outputs]
    first_set = normalized_sets[0]
    
    for other_set in normalized_sets[1:]:
        if first_set != other_set:
            return False
    return True


def count_ungrounded_baseline(output_json: Dict[str, Any], doc_text: str) -> int:
    """
    Count baseline findings where evidence_quote is missing or not in document.
    """
    findings = output_json.get("findings", [])
    ungrounded = 0
    
    for f in findings:
        evidence = f.get("evidence_quote", "").strip()
        if not evidence:
            ungrounded += 1
        elif evidence not in doc_text:
            ungrounded += 1
    
    return ungrounded


def compute_traceability_hybrid(output_json: Dict[str, Any]) -> float:
    """Compute % of hybrid findings that contain rule_id (should be 100%)."""
    findings = output_json.get("findings", [])
    if not findings:
        return 1.0  # No findings = 100% traceable (vacuous truth)
    
    with_rule_id = sum(1 for f in findings if f.get("rule_id", ""))
    return with_rule_id / len(findings) if findings else 1.0


def compute_fp_fn_hybrid(
    output_json: Dict[str, Any],
    truth: Dict[str, Any]
) -> Tuple[int, int]:
    """
    Compute false positives and false negatives for hybrid engine.
    
    Returns: (fp_count, fn_count)
    """
    findings = output_json.get("findings", [])
    found_rule_ids = {f.get("rule_id", "") for f in findings}
    
    expected_present = set(truth.get("expected_rule_ids_present", []))
    expected_absent = set(truth.get("expected_rule_ids_absent", []))
    
    # FP: found rule_id that should be absent
    fp = len(found_rule_ids & expected_absent)
    
    # FN: expected present but not found
    fn = len(expected_present - found_rule_ids)
    
    return fp, fn


def compute_variance_count(run_outputs: List[Dict[str, Any]]) -> int:
    """
    Count how many runs differ from run_01 after normalization.
    Returns number of runs (excluding run_01) that differ.
    """
    if len(run_outputs) < 2:
        return 0
    
    baseline = normalize_hybrid_findings(run_outputs[0])
    variance_count = 0
    
    for run in run_outputs[1:]:
        normalized = normalize_hybrid_findings(run)
        if normalized != baseline:
            variance_count += 1
    
    return variance_count
