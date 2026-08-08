"""
Regression tests for the anonymous "Start Free Review" flow and account
claiming.

Before this, an anonymous visitor hitting /upload-page was redirected to
/login (require_user), and every "Start Free Review" button on the
marketing site pointed straight at /register — a signup form before the
visitor had seen any product value, contradicting the landing page's own
"Upload your first contract free. No credit card required" copy.

/upload-page is now reachable anonymously, and POST /upload creates the
same kind of throwaway guest account /demo/start already used, so an
anonymous upload gets the full interactive product with no form. A guest
can then "claim" their account from /register — upgraded in place (same
user id, same contracts) rather than starting a fresh, disconnected
account.
"""
import io
import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
from database import SessionLocal
from models import Contract, User

NDA_BYTES = b"Confidentiality agreement between Acme Corp and Beta LLC with arbitration and termination clauses."


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit._memory_counters.clear()
    yield
    rate_limit._memory_counters.clear()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _csrf_token(client, path="/upload-page"):
    r = client.get(path)
    assert r.status_code == 200
    return client.cookies.get("csrf_token")


def _upload_anonymously(client):
    token = _csrf_token(client)
    files = {"file": ("nda.txt", io.BytesIO(NDA_BYTES), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/review")
    return int(r.headers["location"].split("/contract/")[1].split("/")[0])


class TestAnonymousUploadPage:
    def test_upload_page_is_reachable_without_logging_in(self, client):
        r = client.get("/upload-page")
        assert r.status_code == 200
        assert "Choose a file" in r.text

    def test_upload_page_does_not_error_on_missing_user_context(self, client):
        # Regression guard for the template footer line that used to
        # unconditionally read user.contracts_this_month / user.plan.
        r = client.get("/upload-page")
        assert "3 free reviews a month" in r.text


class TestAnonymousUpload:
    def test_anonymous_upload_creates_a_guest_account_and_a_real_contract(self, client):
        contract_id = _upload_anonymously(client)

        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            assert contract is not None
            assert contract.analysis_completed is True
            owner = db.query(User).filter(User.id == contract.user_id).first()
            assert owner.email.endswith("@guest.triagecounsel.local")
            assert owner.password_hash is None
        finally:
            db.close()

    def test_guest_account_is_not_created_until_a_valid_file_is_submitted(self, client):
        db = SessionLocal()
        try:
            users_before = db.query(User).count()
        finally:
            db.close()

        token = _csrf_token(client)
        # No file attached at all — should error out before ever touching
        # the User table, so a bad request never burns a throwaway account.
        r = client.post("/upload", data={"csrf_token": token}, files={}, follow_redirects=False)
        assert r.status_code in (400, 422)

        db = SessionLocal()
        try:
            assert db.query(User).count() == users_before
        finally:
            db.close()

    def test_second_anonymous_upload_in_the_same_session_reuses_the_guest_account(self, client):
        contract_id_1 = _upload_anonymously(client)
        contract_id_2 = _upload_anonymously(client)

        db = SessionLocal()
        try:
            c1 = db.query(Contract).filter(Contract.id == contract_id_1).first()
            c2 = db.query(Contract).filter(Contract.id == contract_id_2).first()
            assert c1.user_id == c2.user_id
        finally:
            db.close()


class TestClaimAccount:
    def test_register_page_shows_claim_copy_for_a_logged_in_guest(self, client):
        _upload_anonymously(client)
        r = client.get("/register")
        assert r.status_code == 200
        assert "Save your" in r.text
        assert "Save &amp; Create Account" in r.text or "Save & Create Account" in r.text

    def test_claiming_upgrades_the_existing_guest_account_in_place(self, client):
        contract_id = _upload_anonymously(client)

        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            guest_user_id = contract.user_id
        finally:
            db.close()

        real_email = f"claimed-{uuid.uuid4().hex[:8]}@example.com"
        token = _csrf_token(client, "/register")
        r = client.post("/register", data={
            "email": real_email, "password": "ClaimedPassw0rd!",
            "confirm_password": "ClaimedPassw0rd!", "name": "Jamie Rivera",
            "company": "", "csrf_token": token,
        }, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/dashboard"

        db = SessionLocal()
        try:
            claimed = db.query(User).filter(User.id == guest_user_id).first()
            assert claimed.email == real_email
            assert claimed.password_hash is not None
            assert claimed.name == "Jamie Rivera"
            assert not claimed.email.endswith("@guest.triagecounsel.local")

            # Same row, so the contract the guest already had is still
            # theirs — nothing was lost by claiming.
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            assert contract.user_id == claimed.id

            # No new row was created for the claim — the same id that was
            # a guest account before now IS the claimed one.
            assert db.query(User).filter(User.id == guest_user_id).count() == 1
        finally:
            db.close()

    def test_claiming_with_an_email_already_used_by_someone_else_is_rejected(self, client):
        other_email = f"someone-else-{uuid.uuid4().hex[:8]}@example.com"

        other_client_token_holder = TestClient(main.app)
        with other_client_token_holder as other:
            r = other.get("/register")
            token = other.cookies.get("csrf_token")
            other.post("/register", data={
                "email": other_email, "password": "Str0ngP@ssw0rd!",
                "confirm_password": "Str0ngP@ssw0rd!", "name": "Existing User",
                "company": "", "csrf_token": token,
            }, follow_redirects=False)

        _upload_anonymously(client)
        token = _csrf_token(client, "/register")
        r = client.post("/register", data={
            "email": other_email, "password": "ClaimedPassw0rd!",
            "confirm_password": "ClaimedPassw0rd!", "name": "Jamie Rivera",
            "company": "", "csrf_token": token,
        }, follow_redirects=False)
        assert r.status_code == 200
        assert "already exists" in r.text

    def test_normal_registration_for_a_visitor_with_no_guest_session_is_unaffected(self, client):
        email = f"brand-new-{uuid.uuid4().hex[:8]}@example.com"
        token = _csrf_token(client, "/register")
        r = client.post("/register", data={
            "email": email, "password": "Str0ngP@ssw0rd!",
            "confirm_password": "Str0ngP@ssw0rd!", "name": "New User",
            "company": "", "csrf_token": token,
        }, follow_redirects=False)
        assert r.status_code == 302

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            assert user is not None
            assert user.password_hash is not None
        finally:
            db.close()
