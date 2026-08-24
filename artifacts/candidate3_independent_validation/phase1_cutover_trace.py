#!/usr/bin/env python3
"""Phase 1 -- activate the intended architecture (FACT_ADMISSION_MODE=enforced,
POLICY_ENFORCEMENT_MODE=cutover, real OpenAI provider) in an isolated
validation environment ONLY, and trace one document through the actual
production entry point (policy_enforcement.apply_policies_for_review --
the exact function main.py calls) to prove cutover is genuinely reached.

Uses a FRESH, isolated sqlite database file (never the repo's dev.db) so
this validation run cannot affect any other state. Never writes any
repository file, .env, or deployment config. Never logs the API key.
"""
import os
import sys
import json

VALIDATION_DB_PATH = "/tmp/candidate3_independent_validation.sqlite3"
if os.path.exists(VALIDATION_DB_PATH):
    os.remove(VALIDATION_DB_PATH)

# --- Environment activation: THIS PROCESS ONLY, never written to disk ---
os.environ["DATABASE_URL"] = f"sqlite:///{VALIDATION_DB_PATH}"
os.environ["DEV_MODE"] = "true"
os.environ["FACT_ADMISSION_MODE"] = "enforced"
os.environ["POLICY_ENFORCEMENT_MODE"] = "cutover"
os.environ["INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED"] = "true"
os.environ["INDEMNIFICATION_RECONCILIATION_ENABLED"] = "true"
# OPENAI_API_KEY is expected to already be set in the calling shell's
# environment (sourced from a 600-permission scratch file) -- this script
# never reads, prints, or writes it itself beyond what os.environ already holds.
assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY must be set in the environment before running this script"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from database import SessionLocal, init_db  # noqa: E402
from models import Playbook, PolicyPosition, PolicyPositionField  # noqa: E402
import playbook_authoring as pa  # noqa: E402
import policy_enforcement as pe  # noqa: E402
import fact_admission as fa  # noqa: E402

init_db()

print("=== PHASE 1: Runtime configuration proof ===", flush=True)
print(f"POLICY_ENFORCEMENT_MODE (as read by the running app): {pe.get_enforcement_mode()}", flush=True)
print(f"FACT_ADMISSION_MODE global switch active: "
      f"{fa.semantic_discovery_enabled('DOES_NOT_EXIST_FORCES_GLOBAL_FALLBACK')}", flush=True)
for flag in [
    "LIABILITY_SEMANTIC_DISCOVERY_ENABLED", "INDEMNIFICATION_SEMANTIC_DISCOVERY_ENABLED",
    "CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED", "PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED",
    "IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED", "INSURANCE_SEMANTIC_DISCOVERY_ENABLED",
    "DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED", "GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED",
    "TERMINATION_SEMANTIC_DISCOVERY_ENABLED", "WARRANTIES_SEMANTIC_DISCOVERY_ENABLED",
    "SLA_SEMANTIC_DISCOVERY_ENABLED", "ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED",
]:
    print(f"  {flag}: {fa.semantic_discovery_enabled(flag)}", flush=True)

# --- Build an isolated playbook with ACTIVE positions for all 12 clause types ---
sys.path.insert(0, os.path.join(REPO_ROOT, "tests"))
import importlib.util
spec = importlib.util.spec_from_file_location("_p4_fixtures", os.path.join(REPO_ROOT, "tests", "test_phase4_policy_enforcement.py"))
_p4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_p4)

db = SessionLocal()
try:
    playbook = Playbook(user_id=1, name="Phase1 Validation Playbook", template_text="x")
    db.add(playbook)
    db.flush()
    for clause_type in pa.CLAUSE_TYPES:
        _p4._make_active_position(db, playbook, clause_type)
    db.commit()
    db.refresh(playbook)

    # A single, freshly-worded test document (NOT part of the independent
    # corpus built in Phase 2, NOT from any burned corpus) touching several
    # clause types, deliberately including one colloquial/AI-only-detectable
    # obligation to prove the AI discovery -> verification -> grounding ->
    # admission chain actually engages.
    test_document = (
        "MASTER SERVICES AGREEMENT\n\n"
        "1. Limitation of Liability. In no event shall either party's aggregate liability under "
        "this Agreement exceed three (3) times the total fees paid in the twelve (12) months "
        "preceding the claim, except that this cap shall not apply to claims arising from either "
        "party's gross negligence or willful misconduct.\n\n"
        "2. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from and "
        "against any third-party claims arising from Vendor's breach of this Agreement.\n\n"
        "3. Confidential Information. Each party shall protect the other's Confidential "
        "Information using no less than a reasonable standard of care.\n\n"
        "4. Data Security. Should Vendor discover that someone gained unauthorized access to "
        "personal data, Vendor will let Customer know within a reasonable time.\n\n"
        "5. Governing Law. This Agreement is governed by the laws of the State of Delaware.\n"
    )
    findings_dict = []

    result = pe.apply_policies_for_review(db, playbook, test_document, findings_dict)

    print("\n=== PHASE 1: Executable path trace ===", flush=True)
    print(f"mode dispatched: {pe.get_enforcement_mode()}", flush=True)
    print(f"policy_decisions present: {result['policy_decisions'] is not None}", flush=True)
    print(f"policy_revision_metadata present: {result['policy_revision_metadata'] is not None}", flush=True)
    print(f"interaction_decisions present (proves cutover branch, not shadow): "
          f"{result['interaction_decisions'] is not None}", flush=True)

    if result["policy_decisions"]:
        print("\nPer-clause-type decisions reached:", flush=True)
        for clause_type, decision in result["policy_decisions"].items():
            state = decision.get("state") if isinstance(decision, dict) else getattr(decision, "state", None)
            print(f"  {clause_type}: {state}", flush=True)

    if result["interaction_decisions"]:
        print("\nInteraction engine decisions reached:", flush=True)
        for ix_id, decision in result["interaction_decisions"].items():
            state = decision.get("state") if isinstance(decision, dict) else getattr(decision, "state", None)
            print(f"  {ix_id}: {state}", flush=True)
    else:
        print("\nInteraction engine: no rule's participating clause types were both present "
              "in this single test document (expected -- this document was authored to "
              "prove basic cutover reachability across many adapters, not to trigger a "
              "specific interaction rule; Phase 6 exercises the interaction engine directly).", flush=True)

    import document_aggregation as da
    agg = da.aggregate_document_state(
        "low",  # deliberately LOW, to also prove Blocker 5's authority contract in this same trace
        result["policy_decisions"],
        result["interaction_decisions"],
        "cutover",
    )
    print(f"\nAggregated authoritative document_state (with overall_risk forced to 'low'): "
          f"{agg['document_state']}", flush=True)
    print("If this is not 'CLEAN', Blocker 5's fix is proven live: the aggregated state "
          "overrides a misleadingly-clean legacy overall_risk.", flush=True)

    with open(os.path.join(os.path.dirname(__file__), "phase1_result.json"), "w") as f:
        json.dump({
            "mode": pe.get_enforcement_mode(),
            "policy_decisions": result["policy_decisions"],
            "interaction_decisions": result["interaction_decisions"],
            "aggregated_document_state": agg["document_state"],
        }, f, indent=2, default=str)
    print("\nWrote phase1_result.json", flush=True)
finally:
    db.close()
    if os.path.exists(VALIDATION_DB_PATH):
        os.remove(VALIDATION_DB_PATH)
