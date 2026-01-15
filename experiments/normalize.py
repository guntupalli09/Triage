"""
Normalization utilities for comparing findings across runs.
"""
from typing import List, Dict, Any, Tuple
from experiments.utils_io import evidence_hash


def normalize_hybrid_findings(output_json: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """
    Normalize hybrid engine findings for comparison.
    
    Returns: List of (rule_id, severity, evidence_hash) tuples, sorted.
    """
    findings = output_json.get("findings", [])
    normalized = []
    
    for f in findings:
        rule_id = f.get("rule_id", "")
        severity = f.get("severity", "").lower()
        # Use exact_snippet if available, else matched_excerpt
        evidence = f.get("exact_snippet", "") or f.get("matched_excerpt", "")
        ev_hash = evidence_hash(evidence)
        normalized.append((rule_id, severity, ev_hash))
    
    # Sort for deterministic comparison
    return sorted(set(normalized))


def normalize_baseline_findings(output_json: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """
    Normalize baseline LLM findings for comparison.
    
    Returns: List of (risk_title, severity, evidence_hash) tuples, sorted.
    """
    findings = output_json.get("findings", [])
    normalized = []
    
    for f in findings:
        risk_title = f.get("risk_title", "").strip().lower()
        severity = f.get("severity", "").lower()
        evidence = f.get("evidence_quote", "")
        ev_hash = evidence_hash(evidence)
        normalized.append((risk_title, severity, ev_hash))
    
    # Sort for deterministic comparison
    return sorted(set(normalized))
