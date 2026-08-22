"""Step 4B — dashboard/history integration tests, exercised end-to-end
through the real app (TestClient + real DB rows), not the pure
document_aggregation function alone.

Relies on two stable markers the implementation is required to render:
  - dashboard: <span id="stat-attention-count">N</span>
  - history row: <tr ... data-document-state="STATE" ...>
  - history filter: /history?risk=attention

Run once as PRE (before wiring aggregate_document_state into main.py) and
again as POST (after) -- see
artifacts/step4b/dashboard_listing_integration_report.md for both results.
"""
import io
import os
import re

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal
from models import Contract

NDA_BYTES = b"Confidentiality Agreement between Acme Corp and Beta LLC regarding arbitration and termination."


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register(client, email):
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Firm", "company": "", "csrf_token": token,
    })
    return token


def _upload_contract(client, token, filename="nda.txt") -> int:
    files = {"file": (filename, io.BytesIO(NDA_BYTES), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303
    return int(r.headers["location"].split("/")[2])


def _set_contract(contract_id, overall_risk, policy_decisions=None, interaction_decisions=None):
    db = SessionLocal()
    try:
        c = db.query(Contract).filter(Contract.id == contract_id).first()
        c.overall_risk = overall_risk
        c.policy_decisions_json = policy_decisions
        c.interaction_decisions_json = interaction_decisions
        db.commit()
    finally:
        db.close()


def pdec(state):
    return {"state": state, "clause_type": "indemnification"}


def idec(state):
    return {"state": state, "interaction_id": "IX_TEST"}


def _clean_interactions():
    return {f"IX_{i}": idec("NOT_TRIGGERED") for i in range(7)}


def _attention_count(dashboard_html: str):
    m = re.search(r'id="stat-attention-count"[^>]*>\s*(\d+)', dashboard_html)
    return int(m.group(1)) if m else None


def _row_document_state(history_html: str, contract_id: int):
    m = re.search(rf'data-contract-id="{contract_id}"[^>]*data-document-state="([A-Z_]+)"', history_html)
    return m.group(1) if m else None


MATERIAL_STATES = {"HAS_CRITICAL_INTERACTION", "HAS_POLICY_VIOLATION", "REQUIRES_REVIEW", "CONFIGURATION_UNRESOLVED"}

# The 15 required scenarios (name, overall_risk, policy_decisions, interaction_decisions, expected_material)
SCENARIOS = [
    ("legacy_low_policy_clean", "low", {"indemnification": pdec("ACCEPT")}, None, False),
    ("legacy_low_policy_violation", "low", {"indemnification": pdec("PROHIBITED")}, None, True),
    ("legacy_low_requires_review", "low", {"indemnification": pdec("REQUIRES_REVIEW")}, None, True),
    ("legacy_low_evaluation_error", "low", {"indemnification": pdec("EVALUATION_ERROR")}, None, True),
    # legacy_high_policy_clean / _not_applicable: expected_material is
    # deliberately False here, not True -- GTD correction (an earlier draft
    # of this file had True). A high-legacy-risk document with an
    # otherwise-clean/not-applicable policy layer resolves to
    # CLEAN_LEGACY_ATTENTION (document_aggregation.py), which is
    # INTENTIONALLY excluded from the material-state set that drives the
    # NEW "Needs Attention" badge/count -- the existing "High Risk" badge
    # already flags it, and the new marker exists specifically to catch
    # cases the legacy signal MISSES, not to duplicate ones it already
    # catches (see document_aggregation_spec.md §3's CLEAN_LEGACY_ATTENTION
    # rationale). Verified against the spec before correcting, not against
    # production's behavior alone.
    ("legacy_high_policy_clean", "high", {"indemnification": pdec("ACCEPT")}, None, False),
    ("legacy_high_policy_not_applicable", "high", {"indemnification": pdec("NOT_APPLICABLE")}, None, False),
    ("legacy_high_policy_violation", "high", {"indemnification": pdec("PROHIBITED")}, None, True),
    ("multiple_policy_violations", "low", {"indemnification": pdec("PROHIBITED"), "termination": pdec("ESCALATE")}, None, True),
    ("one_critical_among_many_clean", "low",
     ({f"clause_{i}": pdec("ACCEPT") for i in range(11)} | {"indemnification": pdec("PROHIBITED")}), None, True),
    ("policy_unresolved_among_many_clean", "low",
     ({f"clause_{i}": pdec("ACCEPT") for i in range(11)} | {"sla": pdec("REQUIRES_REVIEW")}), None, True),
    ("shadow_behavior_liability_violation", "low", {"limitation_of_liability": pdec("PROHIBITED")}, None, True),
    ("legacy_behavior_clean", "low", {"limitation_of_liability": pdec("ACCEPT")}, None, False),
]

SCENARIOS_WITH_INTERACTIONS = [
    ("legacy_low_interaction_violation_ix", "low", {"indemnification": pdec("ACCEPT")}, {**_clean_interactions(), "IX_0": idec("ESCALATE")}, True),
    ("multiple_interactions_ix", "low", {"indemnification": pdec("ACCEPT")}, {**_clean_interactions(), "IX_0": idec("ESCALATE"), "IX_1": idec("ESCALATE")}, True),
    ("cutover_clean_ix", "low", {"indemnification": pdec("ACCEPT")}, _clean_interactions(), False),
]


@pytest.mark.parametrize("name,overall_risk,policy_decisions,interaction_decisions,expected_material",
                          SCENARIOS + SCENARIOS_WITH_INTERACTIONS)
def test_material_case_visible_on_dashboard_and_history(client, name, overall_risk, policy_decisions, interaction_decisions, expected_material):
    token = _register(client, f"{name}@example.com")
    cid = _upload_contract(client, token, filename=f"{name}.txt")
    _set_contract(cid, overall_risk, policy_decisions, interaction_decisions)

    dash = client.get("/dashboard")
    assert dash.status_code == 200

    hist = client.get("/history")
    assert hist.status_code == 200
    doc_state = _row_document_state(hist.text, cid)

    if expected_material:
        assert doc_state in MATERIAL_STATES, (
            f"{name}: expected a material document_state marker on /history row for contract {cid}, "
            f"got {doc_state!r}. Full row marker absent means the dashboard/listing wiring gap is "
            f"still present for this scenario."
        )
    else:
        assert doc_state is not None, f"{name}: expected a document_state marker to exist at all (got None -- marker infra missing)"
        assert doc_state not in MATERIAL_STATES, f"{name}: clean contract incorrectly marked material ({doc_state})"


def test_attention_filter_includes_low_risk_material_contract(client):
    token = _register(client, "attention-filter-include@example.com")
    cid = _upload_contract(client, token, filename="material-low-risk.txt")
    _set_contract(cid, "low", {"indemnification": pdec("PROHIBITED")}, None)

    resp = client.get("/history?risk=attention")
    assert resp.status_code == 200, "the /history?risk=attention filter must exist and succeed"
    assert "material-low-risk.txt" in resp.text, (
        "a contract with overall_risk=low but a confirmed policy violation must appear in the "
        "attention filter -- policy-important contract omitted from attention filter"
    )


def test_attention_filter_excludes_genuinely_clean_contract(client):
    token = _register(client, "attention-filter-exclude@example.com")
    cid = _upload_contract(client, token, filename="genuinely-clean.txt")
    _set_contract(cid, "low", {"indemnification": pdec("ACCEPT")}, _clean_interactions())

    resp = client.get("/history?risk=attention")
    assert resp.status_code == 200
    assert "genuinely-clean.txt" not in resp.text, "a genuinely clean contract must not be swept into the attention bucket"


def test_dashboard_attention_count_reflects_low_risk_violation(client):
    token = _register(client, "dashboard-attention-count@example.com")
    cid = _upload_contract(client, token, filename="dash-attn.txt")
    _set_contract(cid, "low", {"indemnification": pdec("PROHIBITED")}, None)

    dash = client.get("/dashboard")
    assert dash.status_code == 200
    count = _attention_count(dash.text)
    assert count is not None, "dashboard must render a stat-attention-count marker"
    assert count >= 1, "attention count must include the low-legacy-risk, policy-violating contract"
