"""
Hybrid engine runner for experiments.
"""
import sys
from pathlib import Path

# Add parent directory to path to import rules_engine
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from rules_engine import RuleEngine
from experiments.utils_io import read_text, save_json
from experiments.config import HYBRID_ARTIFACTS


def run_hybrid_engine(text: str, suppression_enabled: bool = True) -> dict:
    """
    Run hybrid deterministic engine on text.
    
    Args:
        text: Contract text to analyze
        suppression_enabled: Whether to apply false-positive suppression
    
    Returns:
        Analysis result dict
    """
    engine = RuleEngine()
    
    # Pass suppression_enabled parameter to analyze() method
    result = engine.analyze(text, suppression_enabled=suppression_enabled)
    
    # Convert Finding objects to dicts for JSON serialization
    findings_dict = []
    for f in result["findings"]:
        findings_dict.append({
            "rule_id": f.rule_id,
            "rule_name": f.rule_name,
            "title": f.title,
            "severity": f.severity.value,
            "rationale": f.rationale,
            "matched_excerpt": f.matched_excerpt,
            "exact_snippet": f.exact_snippet,
            "start_index": f.start_index,
            "end_index": f.end_index,
            "position": f.position,
            "context": f.context,
            "clause_number": f.clause_number,
            "matched_keywords": f.matched_keywords,
            "aliases": f.aliases,
        })
    
    return {
        "findings": findings_dict,
        "overall_risk": result["overall_risk"],
        "rule_counts": result["rule_counts"],
        "version": result["version"],
        "ruleset_version_data": result.get("ruleset_version_data", {}),
        "suppression_log": result.get("suppression_log", {}),
        "suppression_enabled": suppression_enabled,
    }


def run_hybrid_on_file(input_path: Path, output_path: Path, suppression_enabled: bool = True) -> None:
    """Run hybrid engine on a text file and save output."""
    text = read_text(input_path)
    result = run_hybrid_engine(text, suppression_enabled)
    save_json(result, output_path)


if __name__ == "__main__":
    # CLI usage: python run_hybrid.py <input.txt> <output.json>
    if len(sys.argv) < 3:
        print("Usage: python run_hybrid.py <input.txt> <output.json>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    run_hybrid_on_file(input_path, output_path)
