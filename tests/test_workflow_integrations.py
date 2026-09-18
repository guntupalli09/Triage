"""
Workflow layer: tenancy, integration API, canonical-fact index, portfolio
search/reporting, change-aware reconfirm, intake, and revisions.

These tests hit real FastAPI routes and the SQLite test DB. They do not
mock the policy engine's decisions — they persist known fact snapshots and
query the index, which is the product requirement (historical facts remain
the source of truth; the LLM never answers portfolio questions).
"""
from __future__ import annotations

import io
import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
import rbac
import tenancy
import canonical_index
import portfolio_query
import change_aware
from database import SessionLocal, init_db
from models import Contract, ContractFactIndex, User, Playbook, IntakeRequest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _csrf(client, path="/login"):
    r = client.get(path)
    assert r.status_code == 200
    return client.cookies.get("csrf_token")


def _register(client, email=None, password="password123"):
    email = email or f"u-{uuid.uuid4().hex[:10]}@example.com"
    token = _csrf(client, "/register")
    r = client.post("/register", data={
        "csrf_token": token, "email": email, "password": password,
        "confirm_password": password, "name": "Tester", "accept_terms": "on",
    }, follow_redirects=False)
    assert r.status_code in (302, 303), r.text
    return email, password


def _login_api(client, email, password, client_kind="api"):
    r = client.post("/api/v1/auth/login", json={
        "email": email, "password": password, "client_kind": client_kind,
    })
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_indexed_contract(db, user, **fields):
    tenancy.ensure_user_tenant(db, user)
    contract = Contract(
        user_id=user.id,
        tenant_id=user.tenant_id,
        workspace_id=user.workspace_id,
        filename=fields.get("filename", "msa.txt"),
        display_name=fields.get("display_name", "Acme MSA"),
        contract_text=fields.get("contract_text", "Limitation of Liability. Liability shall not exceed $2,000,000."),
        analysis_completed=True,
        overall_risk=fields.get("overall_risk", "medium"),
        source=fields.get("source", "web"),
        review_status=fields.get("review_status", "in_review"),
        contract_type=fields.get("contract_type", "MSA"),
        counterparty=fields.get("counterparty", "Acme Corp"),
        findings_json=fields.get("findings_json", [{"rule_id": "H_LOL_01", "severity": "high", "title": "Cap"}]),
        policy_decisions_json=fields.get("policy_decisions_json") or {
            "limitation_of_liability": {
                "clause_type": "limitation_of_liability",
                "state": "NEGOTIATE",
                "extracted_summary": fields.get("cap_summary", "$2,000,000"),
                "contract_language": fields.get(
                    "contract_language",
                    "Liability shall not exceed $2,000,000.",
                ),
                "start_index": 0,
                "end_index": 40,
            },
            "governing_law": {
                "clause_type": "governing_law",
                "extracted_summary": fields.get("governing_law", "Texas"),
                "contract_language": "This Agreement is governed by the laws of Texas.",
            },
            "termination": {
                "extracted_summary": fields.get("termination_summary", "either party may terminate for convenience"),
                "contract_language": fields.get("termination_language", "either party may terminate for convenience"),
            },
            "assignment": {
                "extracted_summary": fields.get("assignment_summary", "may not assign without the prior written consent of the other party"),
                "contract_language": "may not assign without the prior written consent of the other party",
            },
            "indemnification": {
                "extracted_summary": fields.get("indem_summary", "mutual indemnification"),
            },
        },
        interaction_decisions_json=fields.get("interaction_decisions_json"),
        document_facts_json=fields.get("document_facts_json"),
        payment_terms_json=fields.get("payment_terms_json"),
        review_decisions_json=fields.get("review_decisions_json"),
    )
    db.add(contract)
    db.flush()
    canonical_index.upsert_fact_index(db, contract)
    db.commit()
    db.refresh(contract)
    return contract


class TestTenantIsolation:
    def test_api_cannot_read_other_tenant_contract(self, client):
        email_a, pw_a = _register(client, email=f"a-{uuid.uuid4().hex[:8]}@ex.com")
        token_a = _login_api(client, email_a, pw_a)
        db = SessionLocal()
        user_a = db.query(User).filter(User.email == email_a).first()
        contract = _seed_indexed_contract(db, user_a, filename="secret-a.txt")
        contract_id = contract.id
        db.close()

        client.cookies.clear()
        email_b, pw_b = _register(client, email=f"b-{uuid.uuid4().hex[:8]}@ex.com")
        token_b = _login_api(client, email_b, pw_b)

        r = client.get(f"/api/v1/reviews/{contract_id}", headers=_auth(token_b))
        assert r.status_code == 404

        r = client.get("/api/v1/contracts", headers=_auth(token_b))
        ids = [c["id"] for c in r.json()["contracts"]]
        assert contract_id not in ids

        r = client.post("/api/v1/portfolio/search", headers=_auth(token_b), json={
            "filters": [{"field": "contract_type", "op": "eq", "value": "MSA"}],
        })
        assert r.status_code == 200
        assert all(row["contract_id"] != contract_id for row in r.json()["results"])

        r = client.get("/api/v1/portfolio/report", headers=_auth(token_b))
        assert r.status_code == 200
        assert r.json()["total_contracts"] == 0

        # Owner can still see it.
        r = client.get(f"/api/v1/reviews/{contract_id}", headers=_auth(token_a))
        assert r.status_code == 200
        assert r.json()["id"] == contract_id


class TestPermissions:
    def test_requester_cannot_modify_playbooks_or_run_review(self, client):
        email, pw = _register(client)
        db = SessionLocal()
        rbac.ensure_seed_roles_and_permissions(db)
        user = db.query(User).filter(User.email == email).first()
        # Strip account-owner role and leave requester only.
        rbac.revoke_role(db, user, "user")
        rbac.grant_role(db, user, "requester")
        db.commit()
        db.close()
        token = _login_api(client, email, pw)
        r = client.get("/api/v1/playbooks", headers=_auth(token))
        assert r.status_code == 403
        r = client.post("/api/v1/reviews", headers=_auth(token), json={
            "document_text": "A short agreement.", "filename": "x.txt", "source": "web",
        })
        assert r.status_code == 403
        r = client.post("/api/v1/intake", headers=_auth(token), json={
            "document_text": "A short agreement.", "filename": "x.txt",
            "requested_contract_type": "MSA",
        })
        assert r.status_code == 200


class TestCanonicalFactIndexAndSearch:
    def test_numeric_cap_unlimited_type_and_interactions(self, client):
        email, pw = _register(client)
        token = _login_api(client, email, pw)
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        facts_fixed = {
            "schema_version": 1,
            "commercial": {"payment_due": {"presence": "PRESENT", "value": {"days": 45, "basis": "net"}}},
            "liability": {
                "provisions": [{
                    "provision_id": "p1",
                    "general_cap": {
                        "presence": "PRESENT",
                        "value": {"operator": "SIMPLE", "operands": [
                            {"type": "fixed_amount", "money": {"amount": "2500000", "currency": "USD"}}
                        ]},
                    },
                }],
                "controlling_provision_id": "p1",
            },
            "indemnification": {"obligations": [
                {"indemnifying_party": "Vendor", "indemnified_party": "Customer"},
                {"indemnifying_party": "Customer", "indemnified_party": "Vendor"},
            ]},
        }
        hi = _seed_indexed_contract(
            db, user, filename="big.txt", contract_type="MSA",
            document_facts_json=facts_fixed,
            payment_terms_json={"days": 45},
            interaction_decisions_json={"IX_A": {"state": "NEGOTIATE", "participating_clause_types": ["limitation_of_liability"]}},
            findings_json=[{"rule_id": "H_LOL_01", "severity": "high", "title": "Cap", "finding_type": "policy_decision", "policy_state": "NEGOTIATE"}],
        )
        hi_id = hi.id
        _seed_indexed_contract(
            db, user, filename="uncapped.txt", contract_type="NDA",
            document_facts_json={
                "liability": {
                    "provisions": [{
                        "provision_id": "p1",
                        "general_cap": {
                            "presence": "PRESENT",
                            "value": {"operator": "SIMPLE", "operands": [{"type": "unlimited"}]},
                        },
                    }],
                    "controlling_provision_id": "p1",
                },
            },
            policy_decisions_json={"limitation_of_liability": {"extracted_summary": "unlimited", "contract_language": "unlimited liability"}},
            findings_json=[{"rule_id": "X", "severity": "low", "title": "ok"}],
        )
        db.close()

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [
                {"field": "contract_type", "op": "eq", "value": "MSA"},
                {"field": "liability_cap", "op": "gt", "value": 1000000},
            ],
        })
        assert r.status_code == 200, r.text
        ids = [row["contract_id"] for row in r.json()["results"]]
        assert hi_id in ids
        assert r.json()["authoritative"] is True

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "liability_unlimited", "op": "eq", "value": True}],
        })
        names = [row["original_filename"] for row in r.json()["results"]]
        assert "uncapped.txt" in names
        assert "big.txt" not in names

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "has_interactions", "op": "eq", "value": True}],
        })
        assert any(row["contract_id"] == hi_id for row in r.json()["results"])

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "payment_terms_days", "op": "gt", "value": 30}],
        })
        assert any(row["contract_id"] == hi_id for row in r.json()["results"])

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "indemnification", "op": "eq", "value": "mutual"}],
        })
        assert any(row["contract_id"] == hi_id for row in r.json()["results"])

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "highest_severity", "op": "eq", "value": "high"}],
        })
        assert any(row["contract_id"] == hi_id for row in r.json()["results"])

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "has_unresolved", "op": "eq", "value": True}],
        })
        assert any(row["contract_id"] == hi_id for row in r.json()["results"])

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "termination_for_convenience", "op": "eq", "value": True}],
        })
        assert r.status_code == 200

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "assignment_requires_consent", "op": "eq", "value": True}],
        })
        assert r.status_code == 200

        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "governing_law", "op": "contains", "value": "Texas"}],
        })
        assert any(row["contract_id"] == hi_id for row in r.json()["results"])

        db = SessionLocal()
        row = db.query(ContractFactIndex).filter(ContractFactIndex.contract_id == hi_id).first()
        assert row is not None
        assert row.liability_cap_amount == 2500000
        assert row.liability_unlimited is False
        db.close()

    def test_malformed_and_sql_rejected(self, client):
        email, pw = _register(client)
        token = _login_api(client, email, pw)
        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "sql": "SELECT * FROM contracts",
            "filters": [],
        })
        assert r.status_code == 400
        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "not_a_field", "op": "eq", "value": "x"}],
        })
        assert r.status_code == 400
        r = client.post("/api/v1/portfolio/search", headers=_auth(token), json={
            "filters": [{"field": "liability_cap", "op": "like", "value": "1"}],
        })
        assert r.status_code == 400


class TestNaturalLanguageSearch:
    def test_model_cannot_emit_sql(self, client, monkeypatch):
        email, pw = _register(client)
        token = _login_api(client, email, pw)

        def fake_sql(*args, **kwargs):
            return {"choices": [{"message": {"content": '{"sql": "SELECT * FROM contract_fact_index"}'}}]}

        monkeypatch.setattr("openai_provider.get_api_key", lambda explicit=None: "sk-test")
        monkeypatch.setattr("openai_provider.call_chat_completion", fake_sql)
        r = client.post("/api/v1/portfolio/search/nl", headers=_auth(token), json={
            "question": "show me everything",
        })
        assert r.status_code == 400
        assert "SQL" in r.json()["detail"]

    def test_model_output_is_validated_then_queried(self, client, monkeypatch):
        email, pw = _register(client)
        token = _login_api(client, email, pw)
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        contract = _seed_indexed_contract(
            db, user, contract_type="MSA",
            document_facts_json={
                "liability": {
                    "provisions": [{
                        "provision_id": "p1",
                        "general_cap": {"presence": "PRESENT", "value": {
                            "operator": "SIMPLE",
                            "operands": [{"type": "fixed_amount", "money": {"amount": "5000000", "currency": "USD"}}],
                        }},
                    }],
                    "controlling_provision_id": "p1",
                },
            },
        )
        contract_id = contract.id
        db.close()

        def fake_ok(*args, **kwargs):
            return {"choices": [{"message": {"content": '{"filters":[{"field":"contract_type","op":"eq","value":"MSA"},{"field":"liability_cap","op":"gt","value":1000000}],"combinator":"and"}'}}]}

        monkeypatch.setattr("openai_provider.get_api_key", lambda explicit=None: "sk-test")
        monkeypatch.setattr("openai_provider.call_chat_completion", fake_ok)
        r = client.post("/api/v1/portfolio/search/nl", headers=_auth(token), json={
            "question": "Show me MSAs where our liability exceeds $1M",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["authoritative"] is True
        assert data["source"] == "canonical_fact_index"
        assert any(row["contract_id"] == contract_id for row in data["results"])
        assert data["interpreted_query"]["filters"][0]["field"] == "contract_type"

    def test_unsupported_question(self, client, monkeypatch):
        email, pw = _register(client)
        token = _login_api(client, email, pw)

        def fake_unsup(*args, **kwargs):
            return {"choices": [{"message": {"content": '{"unsupported": true, "reason": "cannot express favorite color"}'}}]}

        monkeypatch.setattr("openai_provider.get_api_key", lambda explicit=None: "sk-test")
        monkeypatch.setattr("openai_provider.call_chat_completion", fake_unsup)
        r = client.post("/api/v1/portfolio/search/nl", headers=_auth(token), json={
            "question": "which contracts are red",
        })
        assert r.status_code == 422


class TestWordAndGoogleAuth:
    def test_word_login_and_bearer(self, client):
        email, pw = _register(client)
        r = client.post("/api/v1/auth/login", json={
            "email": email, "password": pw, "client_kind": "word",
        })
        assert r.status_code == 200
        token = r.json()["token"]
        r = client.get("/api/v1/me", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["email"] == email
        r = client.get("/integrations/word/manifest.xml")
        assert r.status_code == 200
        assert "TriageCounsel" in r.text
        r = client.get("/integrations/word/taskpane")
        assert r.status_code == 200
        assert "office.js" in r.text

    def test_google_login_and_sidebar(self, client):
        email, pw = _register(client)
        r = client.post("/api/v1/auth/login", json={
            "email": email, "password": pw, "client_kind": "google_docs",
        })
        assert r.status_code == 200
        token = r.json()["token"]
        r = client.get("/api/v1/me", headers=_auth(token))
        assert r.status_code == 200
        r = client.get("/integrations/google/sidebar")
        assert r.status_code == 200
        assert "google_docs" in r.text

    def test_missing_and_bad_token(self, client):
        r = client.get("/api/v1/me")
        assert r.status_code == 401
        r = client.get("/api/v1/me", headers=_auth("tc_not_a_real_token"))
        assert r.status_code == 401


class TestChangeAwareAndRevisions:
    def test_stale_decision_and_unaffected_preservation(self, client):
        email, pw = _register(client)
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        tenancy.ensure_user_tenant(db, user)
        original_text = (
            "1. Limitation of Liability. Vendor's liability shall not exceed $100.\n"
            "2. Governing Law. This Agreement is governed by the laws of Texas."
        )
        contract = Contract(
            user_id=user.id, tenant_id=user.tenant_id, workspace_id=user.workspace_id,
            filename="rev.txt", contract_text=original_text, analysis_completed=True,
            policy_decisions_json={
                "limitation_of_liability": {
                    "clause_type": "limitation_of_liability",
                    "state": "ACCEPT",
                    "contract_language": "Vendor's liability shall not exceed $100.",
                    "start_index": original_text.find("Vendor's"),
                    "end_index": original_text.find("Vendor's") + len("Vendor's liability shall not exceed $100."),
                },
                "governing_law": {
                    "clause_type": "governing_law",
                    "state": "ACCEPT",
                    "contract_language": "This Agreement is governed by the laws of Texas.",
                },
            },
            interaction_decisions_json={
                "IX_A": {
                    "state": "NEGOTIATE",
                    "participating_clause_types": ["limitation_of_liability", "indemnification"],
                },
                "IX_B": {
                    "state": "NEGOTIATE",
                    "participating_clause_types": ["governing_law"],
                },
            },
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        cid = contract.id
        db.close()

        new_text = original_text.replace("$100", "$5,000,000")
        db = SessionLocal()
        contract = db.query(Contract).filter(Contract.id == cid).first()
        result = change_aware.reconfirm_against_text(db, contract, new_text, reevaluate_affected=False)
        db.commit()
        assert "limitation_of_liability" in result["affected_clause_types"]
        assert "governing_law" in result["preserved_clause_types"]
        stale = contract.interaction_staleness_json or {}
        assert stale.get("IX_A", {}).get("stale") is True
        assert stale.get("IX_B", {}).get("stale") in (None, False)
        # Original governing-law decision remains the frozen snapshot.
        assert contract.policy_decisions_json["governing_law"]["state"] == "ACCEPT"
        db.close()

    def test_revision_import_preserves_prior_review(self, client):
        email, pw = _register(client)
        token = _login_api(client, email, pw)
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        original = _seed_indexed_contract(
            db, user, contract_text="Vendor's liability shall not exceed $100.",
            contract_language="Vendor's liability shall not exceed $100.",
        )
        oid = original.id
        db.close()
        r = client.post(f"/api/v1/reviews/{oid}/revisions", headers=_auth(token), json={
            "document_text": "Vendor's liability shall not exceed $9,000,000.",
            "filename": "counterparty.docx",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["prior_review_preserved"] is True
        assert data["original_contract_id"] == oid
        assert data["revision_contract_id"] != oid
        db = SessionLocal()
        prior = db.query(Contract).filter(Contract.id == oid).first()
        assert prior.contract_text.startswith("Vendor's liability shall not exceed $100")
        db.close()


class TestIntakeAndAudit:
    def test_intake_and_audit_trail(self, client):
        email, pw = _register(client)
        token = _login_api(client, email, pw)
        r = client.post("/api/v1/intake", headers=_auth(token), json={
            "document_text": "Master Services Agreement. Payment is due within 15 days.",
            "filename": "sales-msa.txt",
            "requested_contract_type": "MSA",
            "counterparty": "Globex",
        })
        assert r.status_code == 200, r.text
        intake_id = r.json()["id"]
        r = client.post(f"/api/v1/intake/{intake_id}/promote", headers=_auth(token), json={})
        assert r.status_code == 200, r.text
        contract_id = r.json()["contract_id"]
        r = client.get(f"/api/v1/reviews/{contract_id}/audit", headers=_auth(token))
        assert r.status_code == 200
        events = [e["event_type"] for e in r.json()["audit_log"]]
        assert any("integration" in e or "intake" in e or "token" in e for e in events) or r.json()["integration_actions"]


class TestRepositoryWeb:
    def test_history_and_portfolio_pages(self, client):
        _register(client)
        r = client.get("/history")
        assert r.status_code == 200
        assert "counterparty" in r.text.lower()
        r = client.get("/portfolio")
        assert r.status_code == 200
        assert "canonical facts" in r.text.lower() or "Portfolio" in r.text
        r = client.get("/intake")
        assert r.status_code == 200
        r = client.get("/integrations")
        assert r.status_code == 200
