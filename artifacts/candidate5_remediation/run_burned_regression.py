"""Candidate 4 remediation — burned 660-case corpus regression.
Replays the PREVIOUSLY-FROZEN independent-validation corpus (now burned,
permitted for regression/diagnostic use only, per this mission's explicit
instruction) against the current (Candidate 4) code, using the SAME real
OpenAI provider path and the SAME grading pipeline as the original run.
Never modifies, regenerates, or relabels the corpus.

Corpus-integrity check: reuses run_independent_corpus.py's OWN import-time
assertion (canonical `json.dumps(CASES, sort_keys=True)` hash against
corpus_sha256.txt) rather than re-implementing hashing here. An earlier
version of this script naively hashed the raw file bytes and got a
different value than corpus_sha256.txt — that was a mismatch between two
different (both internally consistent) hashing methodologies, not evidence
of corpus tampering (`git log`/`git show` confirm cases.json has not
changed since its one and only freeze commit, 658e829). See
ROOT_CAUSE_MAP.md's housekeeping note.
"""
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


def main():
    ric = import_module("run_independent_corpus")  # raises on hash mismatch at import time
    print(f"Burned corpus integrity verified (canonical hash): {ric.EXPECTED_SHA}")
    print(f"Total cases: {len(ric.CASES)}")

    out_path = Path(__file__).resolve().parent / "burned_regression_raw_results.jsonl"
    with out_path.open("w") as f:
        done = 0
        for case in ric.CASES:
            result = ric.run_case(case)
            f.write(json.dumps(result) + "\n")
            f.flush()
            done += 1
            if done % 25 == 0:
                print(f"{done}/{len(ric.CASES)}", flush=True)
    print(f"DONE: wrote {done} results to {out_path}")


if __name__ == "__main__":
    main()
