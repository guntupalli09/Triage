"""
Regression tests for the /demo and /demo/start routes.

/demo used to render a static report (contract_id=None) that silently hid
the redline workspace, PDF export, and Share — the demo showed a report and
nothing else. /demo now previews a sample contract with no account and no
database write, and /demo/start provisions a real, live, interactive copy
(a throwaway guest account for an anonymous visitor, or the caller's own
account if already logged in) so the whole product — Verification Report,
risk dashboard, redline workspace — is reachable without a signup form.
"""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal
from models import Contract, User

DEMO_SAMPLE_KEYS = ("clean", "messy")


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _csrf_token(client, path="/demo"):
    r = client.get(path)
    assert r.status_code == 200
    # The CSRF cookie is only re-sent in *this* response if it didn't
    # already exist in the client's jar (CSRFCookieMiddleware mints it once
    # per visitor and never resets it) — read from the jar, which has it
    # either way, rather than this response's own Set-Cookie headers.
    return client.cookies.get("csrf_token")


def _register(client, email):
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    r = client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Firm", "company": "", "csrf_token": token,
    }, follow_redirects=False)
    assert r.status_code == 302
    return token


class TestDemoPreview:
    """GET /demo — public, non-mutating."""

    def test_default_sample_is_clean(self, client):
        r = client.get("/demo")
        assert r.status_code == 200
        assert "Clean NDA" in r.text
        assert "Messy Real-World Contract" in r.text

    def test_messy_sample_selectable_by_query_param(self, client):
        r = client.get("/demo?sample=messy")
        assert r.status_code == 200
        assert "exhibit_10.1_employment_agreement.txt" in r.text

    def test_unknown_sample_falls_back_to_default(self, client):
        r = client.get("/demo?sample=not-a-real-sample")
        assert r.status_code == 200
        # Falls back to the clean sample's doc label rather than erroring.
        assert "Sample_Mutual_NDA.txt" in r.text

    @pytest.mark.parametrize("sample_key", DEMO_SAMPLE_KEYS)
    def test_preview_does_not_write_to_the_database(self, client, sample_key):
        db = SessionLocal()
        try:
            contracts_before = db.query(Contract).count()
            users_before = db.query(User).count()
        finally:
            db.close()

        for _ in range(3):
            r = client.get(f"/demo?sample={sample_key}")
            assert r.status_code == 200

        db = SessionLocal()
        try:
            assert db.query(Contract).count() == contracts_before
            assert db.query(User).count() == users_before
        finally:
            db.close()

    def test_preview_html_does_not_leak_the_real_named_parties(self, client):
        """The messy sample's source SEC filing names a real company and
        executive — the live preview must only ever show the fictional
        stand-in names, never the real ones."""
        r = client.get("/demo?sample=messy")
        assert "TransDigm" not in r.text
        assert "Kevin Stein" not in r.text
        assert "Nicholas Howley" not in r.text


class TestDemoStart:
    """POST /demo/start — provisions a live, interactive copy."""

    def test_anonymous_visitor_gets_a_guest_account_and_lands_on_the_review_page(self, client):
        token = _csrf_token(client)
        r = client.post("/demo/start", data={"csrf_token": token, "sample": "clean"}, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"].endswith("/review")

        r2 = client.get(r.headers["location"], follow_redirects=False)
        assert r2.status_code == 200

    def test_guest_account_uses_a_recognizable_throwaway_address(self, client):
        token = _csrf_token(client)
        client.post("/demo/start", data={"csrf_token": token, "sample": "clean"}, follow_redirects=False)

        db = SessionLocal()
        try:
            guests = db.query(User).filter(User.email.like("demo-%@guest.triagecounsel.local")).all()
            assert len(guests) >= 1
            newest = max(guests, key=lambda u: u.id)
            assert newest.password_hash is None
            assert newest.name == "Demo Visitor"
        finally:
            db.close()

    def test_missing_csrf_token_is_rejected(self, client):
        client.get("/demo")  # mint the cookie
        r = client.post("/demo/start", data={"sample": "clean"}, follow_redirects=False)
        # 422: FastAPI's own "required form field missing" response (the
        # csrf_token form param itself is required); 400/403: csrf_protect's
        # own mismatch/missing-cookie check. Either is a correct rejection —
        # the request must not succeed either way.
        assert r.status_code in (400, 403, 422)

    @pytest.mark.parametrize("sample_key,expected_filename_fragment", [
        ("clean", "Sample NDA"),
        ("messy", "Messy"),
    ])
    def test_selected_sample_carries_through_to_the_provisioned_contract(
        self, client, sample_key, expected_filename_fragment
    ):
        token = _csrf_token(client)
        r = client.post(
            "/demo/start", data={"csrf_token": token, "sample": sample_key}, follow_redirects=False,
        )
        assert r.status_code == 303
        contract_id = int(r.headers["location"].split("/contract/")[1].split("/")[0])

        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            assert contract is not None
            assert expected_filename_fragment in contract.filename
            assert contract.analysis_completed is True
            assert contract.findings_json  # deterministic engine actually ran
        finally:
            db.close()

    def test_messy_sample_contract_has_no_ma_indemnification_finding(self, client):
        """End-to-end proof the contract-type gate is wired all the way
        through the real HTTP route, not just the engine in isolation."""
        token = _csrf_token(client)
        r = client.post(
            "/demo/start", data={"csrf_token": token, "sample": "messy"}, follow_redirects=False,
        )
        contract_id = int(r.headers["location"].split("/contract/")[1].split("/")[0])

        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            fired_rule_ids = {f["rule_id"] for f in contract.findings_json}
            assert "H_MA_INDEM_BASKET_MISSING_01" not in fired_rule_ids
        finally:
            db.close()

    def test_already_logged_in_visitor_does_not_get_a_second_guest_account(self, client):
        import uuid
        email = f"real-user-{uuid.uuid4().hex[:8]}@example.com"
        _register(client, email)

        db = SessionLocal()
        try:
            users_before = db.query(User).count()
        finally:
            db.close()

        token = _csrf_token(client)
        r = client.post("/demo/start", data={"csrf_token": token, "sample": "clean"}, follow_redirects=False)
        assert r.status_code == 303

        db = SessionLocal()
        try:
            users_after = db.query(User).count()
            owner = db.query(User).filter(User.email == email).first()
            contract_id = int(r.headers["location"].split("/contract/")[1].split("/")[0])
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            assert users_after == users_before  # no new guest account created
            assert contract.user_id == owner.id
        finally:
            db.close()

    def test_invalid_sample_falls_back_to_default_instead_of_erroring(self, client):
        token = _csrf_token(client)
        r = client.post(
            "/demo/start", data={"csrf_token": token, "sample": "not-a-real-sample"}, follow_redirects=False,
        )
        assert r.status_code == 303
