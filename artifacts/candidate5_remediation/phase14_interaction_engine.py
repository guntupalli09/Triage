#!/usr/bin/env python3
"""Phase 6 -- exercise the REAL interaction engine (via policy_enforcement.
apply_policies_for_review, the exact production entry point) against the
3 composite interaction-scenario documents from the frozen independent
corpus, under real cutover with real AI. Unlike the per-adapter replay
harness (which evaluates each adapter against an isolated default policy
fixture), this runs the SAME document through BOTH participating adapters
simultaneously with a single playbook, exactly как cutover does it in
production."""
import os
import sys
import json

VALIDATION_DB_PATH = "/tmp/candidate5_phase14_validation.sqlite3"
if os.path.exists(VALIDATION_DB_PATH):
    os.remove(VALIDATION_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{VALIDATION_DB_PATH}"
os.environ["DEV_MODE"] = "true"
os.environ["FACT_ADMISSION_MODE"] = "enforced"
os.environ["POLICY_ENFORCEMENT_MODE"] = "cutover"
os.environ["INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED"] = "true"
os.environ["INDEMNIFICATION_RECONCILIATION_ENABLED"] = "true"
assert os.environ.get("OPENAI_API_KEY")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from database import SessionLocal, init_db  # noqa: E402
from models import Playbook  # noqa: E402
import playbook_authoring as pa  # noqa: E402
import policy_enforcement as pe  # noqa: E402

init_db()

import importlib.util
spec = importlib.util.spec_from_file_location("_p4_fixtures", os.path.join(REPO_ROOT, "tests", "test_phase4_policy_enforcement.py"))
_p4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_p4)

CASES = json.load(open(os.path.join(os.path.dirname(__file__), "..", "candidate3_independent_validation", "corpus", "cases.json")))
unique_docs = {}
for c in CASES:
    if "interaction" in c["family"] and c["text"] not in unique_docs:
        unique_docs[c["family"]] = c["text"]

db = SessionLocal()
results = []
try:
    playbook = Playbook(user_id=1, name="Phase6 Validation Playbook", template_text="x")
    db.add(playbook)
    db.flush()
    for clause_type in pa.CLAUSE_TYPES:
        _p4._make_active_position(db, playbook, clause_type)
    db.commit()
    db.refresh(playbook)

    for family, text in unique_docs.items():
        result = pe.apply_policies_for_review(db, playbook, text, [])
        entry = {
            "family": family,
            "policy_decisions": {k: (v.get("state") if isinstance(v, dict) else getattr(v, "state", None))
                                  for k, v in (result["policy_decisions"] or {}).items()},
            "interaction_decisions": {k: (v.get("state") if isinstance(v, dict) else getattr(v, "state", None))
                                       for k, v in (result["interaction_decisions"] or {}).items()},
        }
        results.append(entry)
        print(f"=== {family} ===", flush=True)
        print(f"  policy_decisions: {entry['policy_decisions']}", flush=True)
        print(f"  interaction_decisions: {entry['interaction_decisions']}", flush=True)

    with open(os.path.join(os.path.dirname(__file__), "phase14_result.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\nWrote phase14_result.json", flush=True)
finally:
    db.close()
    if os.path.exists(VALIDATION_DB_PATH):
        os.remove(VALIDATION_DB_PATH)
