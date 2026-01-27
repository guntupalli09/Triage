"""
Investigate suppression discrepancy: Why 0% FP reduction?
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rules_engine import RuleEngine
from experiments.utils_io import read_text, find_doc_file, load_json
from experiments.config import DATA_DIR
from experiments.metrics import compute_fp_fn_hybrid
from experiments.run_hybrid import run_hybrid_engine


def investigate_suppression():
    """Investigate why suppression shows 0% FP reduction."""
    print("=" * 80)
    print("INVESTIGATING SUPPRESSION DISCREPANCY")
    print("=" * 80)
    
    # Get synthetic NDA documents
    doc_ids = [f"synthetic_{i:02d}" for i in range(1, 31)]
    
    total_fp_on = 0
    total_fp_off = 0
    total_suppressions = 0
    docs_with_suppression = 0
    docs_with_fp_reduction = 0
    
    sample_docs = []
    
    for doc_id in doc_ids[:10]:  # Check first 10 for detailed analysis
        text_path = find_doc_file(DATA_DIR, doc_id, ".txt")
        truth_path = find_doc_file(DATA_DIR, doc_id, ".truth.json")
        
        if not text_path or not truth_path:
            continue
        
        text = read_text(text_path)
        truth = load_json(truth_path)
        
        # Run with suppression ON and OFF
        result_on = run_hybrid_engine(text, suppression_enabled=True)
        result_off = run_hybrid_engine(text, suppression_enabled=False)
        
        fp_on, fn_on = compute_fp_fn_hybrid(result_on, truth)
        fp_off, fn_off = compute_fp_fn_hybrid(result_off, truth)
        
        suppressions_on = len(result_on.get("suppression_log", {}))
        findings_on = len(result_on.get("findings", []))
        findings_off = len(result_off.get("findings", []))
        
        total_fp_on += fp_on
        total_fp_off += fp_off
        total_suppressions += suppressions_on
        
        if suppressions_on > 0:
            docs_with_suppression += 1
        
        if fp_off > fp_on:
            docs_with_fp_reduction += 1
        
        # Detailed analysis for first few docs
        if doc_id in ["synthetic_01", "synthetic_02", "synthetic_03"]:
            expected_absent = set(truth.get("expected_rule_ids_absent", []))
            found_on = {f.get("rule_id") for f in result_on.get("findings", [])}
            found_off = {f.get("rule_id") for f in result_off.get("findings", [])}
            
            fp_rules_on = found_on & expected_absent
            fp_rules_off = found_off & expected_absent
            
            sample_docs.append({
                "doc_id": doc_id,
                "fp_on": fp_on,
                "fp_off": fp_off,
                "findings_on": findings_on,
                "findings_off": findings_off,
                "suppressions": suppressions_on,
                "fp_rules_on": list(fp_rules_on),
                "fp_rules_off": list(fp_rules_off),
                "suppression_log": result_on.get("suppression_log", {}),
                "expected_absent": list(expected_absent),
            })
    
    print(f"\nSummary (first 10 synthetic NDAs):")
    print(f"  Total FP ON: {total_fp_on}")
    print(f"  Total FP OFF: {total_fp_off}")
    print(f"  FP Reduction: {total_fp_off - total_fp_on}")
    print(f"  Total Suppressions: {total_suppressions}")
    print(f"  Docs with Suppressions: {docs_with_suppression}")
    print(f"  Docs with FP Reduction: {docs_with_fp_reduction}")
    
    print(f"\nDetailed Analysis (sample docs):")
    for doc in sample_docs:
        print(f"\n  {doc['doc_id']}:")
        print(f"    FP ON: {doc['fp_on']}, FP OFF: {doc['fp_off']}")
        print(f"    Findings ON: {doc['findings_on']}, Findings OFF: {doc['findings_off']}")
        print(f"    Suppressions: {doc['suppressions']}")
        print(f"    Expected Absent: {doc['expected_absent']}")
        print(f"    FP Rules ON: {doc['fp_rules_on']}")
        print(f"    FP Rules OFF: {doc['fp_rules_off']}")
        if doc['suppression_log']:
            print(f"    Suppression Log: {doc['suppression_log']}")
    
    # Check all 30 synthetic NDAs
    print(f"\n" + "=" * 80)
    print("FULL ANALYSIS (all 30 synthetic NDAs)")
    print("=" * 80)
    
    total_fp_on_all = 0
    total_fp_off_all = 0
    total_suppressions_all = 0
    
    for doc_id in doc_ids:
        text_path = find_doc_file(DATA_DIR, doc_id, ".txt")
        truth_path = find_doc_file(DATA_DIR, doc_id, ".truth.json")
        
        if not text_path or not truth_path:
            continue
        
        text = read_text(text_path)
        truth = load_json(truth_path)
        
        result_on = run_hybrid_engine(text, suppression_enabled=True)
        result_off = run_hybrid_engine(text, suppression_enabled=False)
        
        fp_on, fn_on = compute_fp_fn_hybrid(result_on, truth)
        fp_off, fn_off = compute_fp_fn_hybrid(result_off, truth)
        
        total_fp_on_all += fp_on
        total_fp_off_all += fp_off
        total_suppressions_all += len(result_on.get("suppression_log", {}))
    
    print(f"\nTotal across all 30 synthetic NDAs:")
    print(f"  FP ON: {total_fp_on_all}")
    print(f"  FP OFF: {total_fp_off_all}")
    print(f"  FP Reduction: {total_fp_off_all - total_fp_on_all}")
    print(f"  Total Suppressions: {total_suppressions_all}")
    print(f"  Reduction %: {(total_fp_off_all - total_fp_on_all) / total_fp_off_all * 100 if total_fp_off_all > 0 else 0:.1f}%")


if __name__ == "__main__":
    investigate_suppression()
