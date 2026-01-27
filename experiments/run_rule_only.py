"""
Rule-only baseline runner (deterministic engine without LLM).
This is an ablation study to measure LLM contribution.
"""
import sys
from pathlib import Path

# Add parent directory to path to import rules_engine
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from rules_engine import RuleEngine
from experiments.utils_io import read_text, save_json
from experiments.config import ARTIFACTS_DIR


def run_rule_only_engine(text: str, suppression_enabled: bool = True) -> dict:
    """
    Run deterministic rule engine only (no LLM explanation).
    
    This is an ablation baseline to measure:
    - What the deterministic engine finds without LLM enhancement
    - How LLM explanation layer affects user perception
    
    Args:
        text: Contract text to analyze
        suppression_enabled: Whether to apply false-positive suppression
    
    Returns:
        Analysis result dict (same schema as hybrid, but no LLM explanations)
    """
    engine = RuleEngine()
    
    # Run deterministic engine only
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
        "llm_enabled": False,  # Mark as rule-only baseline
    }


def run_rule_only_on_file(input_path: Path, output_path: Path, suppression_enabled: bool = True) -> None:
    """Run rule-only engine on a text file and save output."""
    text = read_text(input_path)
    result = run_rule_only_engine(text, suppression_enabled)
    save_json(result, output_path)


if __name__ == "__main__":
    # CLI usage: python run_rule_only.py <input.txt> <output.json>
    if len(sys.argv) < 3:
        print("Usage: python run_rule_only.py <input.txt> <output.json>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    run_rule_only_on_file(input_path, output_path)
