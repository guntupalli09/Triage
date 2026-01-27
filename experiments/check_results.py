"""Quick check of experiment results."""
from experiments.config import RESULTS_DIR

exp3 = RESULTS_DIR / "exp3_suppression.csv"
exp4 = RESULTS_DIR / "exp4_errors.csv"

print("Experiment 3 CSV:")
print(f"  Exists: {exp3.exists()}")
if exp3.exists():
    with open(exp3, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"  Rows: {len(lines) - 1} (excluding header)")
        if len(lines) > 1:
            print(f"  Header: {lines[0].strip()}")

print("\nExperiment 4 CSV:")
print(f"  Exists: {exp4.exists()}")
if exp4.exists():
    with open(exp4, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"  Rows: {len(lines) - 1} (excluding header)")
        if len(lines) > 1:
            print(f"  Header: {lines[0].strip()}")
            print(f"  First data row: {lines[1].strip()[:100]}...")
