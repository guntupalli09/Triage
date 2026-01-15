"""
Quick verification that experiment setup is correct.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rules_engine import RuleEngine
    from experiments.config import DATA_DIR
    from experiments.utils_io import get_doc_ids
    
    print("[OK] Imports successful")
    
    # Test engine
    engine = RuleEngine()
    result = engine.analyze("The party shall indemnify without limit.")
    print(f"[OK] Engine test: {len(result['findings'])} findings")
    
    # Check dataset
    doc_ids = get_doc_ids(DATA_DIR)
    print(f"[OK] Dataset: {len(doc_ids)} documents found")
    
    print("\nSetup verification complete!")
    
except Exception as e:
    print(f"[ERROR] Setup error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
