"""Resume the burned-regression run after a confirmed data-loss incident
(git stash/pop run against the actively-being-written results file mid-run
truncated it from 660 to 424 records -- see PHASE12 report). Re-runs only
the missing case_ids and appends them; does not touch the 424 already-
present, still-valid records."""
import json
import os
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "artifacts" / "candidate3_independent_validation"))

os.environ.setdefault("FACT_ADMISSION_MODE", "enforced")
os.environ.setdefault("INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED", "true")
os.environ.setdefault("INDEMNIFICATION_RECONCILIATION_ENABLED", "true")

RESULTS_PATH = Path(__file__).resolve().parent / "burned_regression_raw_results.jsonl"


def main():
    ric = import_module("run_independent_corpus")
    present = set()
    with RESULTS_PATH.open() as f:
        for line in f:
            present.add(json.loads(line)["case_id"])
    missing = [c for c in ric.CASES if c["id"] not in present]
    print(f"Present: {len(present)}. Missing: {len(missing)}. Resuming.")

    with RESULTS_PATH.open("a") as f:
        done = 0
        for case in missing:
            result = ric.run_case(case)
            f.write(json.dumps(result) + "\n")
            f.flush()
            done += 1
            if done % 25 == 0:
                print(f"{done}/{len(missing)}", flush=True)
    print(f"DONE: appended {done} results.")


if __name__ == "__main__":
    main()
