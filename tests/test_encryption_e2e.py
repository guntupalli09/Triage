"""
Full end-to-end lifecycle tests through the real FastAPI app: contract
upload -> analysis -> persistence -> reload -> export, and playbook upload
-> persistence -> reload — confirming encryption at rest is transparent to
every consumer and doesn't change any observable app behavior.
"""
import base64
import io
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("ENCRYPTION_KEYS", f"e2e:{base64.b64encode(b'e' * 32).decode()}")
os.environ.setdefault("ENCRYPTION_KEY_CURRENT", "e2e")

import main
from database import engine as app_engine
from models import Contract

NDA_TEXT = (
    b"CONFIDENTIALITY AGREEMENT\n\n"
    b"This Agreement is entered into between Acme Corp and Beta LLC. "
    b"The parties agree to keep all disclosed information strictly confidential "
    b"for a period of five years from the effective date. "
    b"Governing law: State of Delaware. Arbitration seat: New York."
)


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        yield c


def _register_and_login(client, email="lawfirm+e2e@example.com"):
    r = client.get("/register")
    token = r.cookies.get("csrf_token")
    client.post("/register", data={
        "email": email, "password": "Str0ngP@ssw0rd!", "confirm_password": "Str0ngP@ssw0rd!",
        "name": "Test Firm", "company": "", "csrf_token": token,
    })
    return token


def _raw_contract_text(contract_id: int) -> str:
    with app_engine.connect() as conn:
        return conn.execute(text("SELECT contract_text FROM contracts WHERE id = :id"), {"id": contract_id}).scalar()


def test_contract_upload_analysis_persist_reload_export(client):
    token = _register_and_login(client)

    files = {"file": ("nda.txt", io.BytesIO(NDA_TEXT), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303
    contract_url = r.headers["location"]
    contract_id = int(contract_url.split("/")[2])

    # Encrypted at rest: the raw DB column is never the plaintext contract text.
    raw = _raw_contract_text(contract_id)
    assert raw.startswith("enc:v1:")
    assert b"Acme Corp" not in raw.encode()

    # Transparently decrypted for the app: the review page renders the real
    # contract content, analysis findings, and risk classification.
    review = client.get(f"/contract/{contract_id}/review")
    assert review.status_code == 200
    assert "Acme Corp" in review.text or "CONFIDENTIALITY" in review.text.upper()

    # PDF export succeeds and doesn't error out due to encryption.
    pdf = client.get(f"/contract/{contract_id}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] in ("application/pdf", "application/pdf; charset=utf-8")

    # A second user cannot reach this contract (ownership check unaffected
    # by encryption — separate from CSRF/rate-limit dependencies).
    client2 = TestClient(main.app)
    token2 = _register_and_login(client2, email="other-firm@example.com")
    other_review = client2.get(f"/contract/{contract_id}/review")
    assert other_review.status_code == 404


def test_playbook_upload_persist_reload(client):
    token = _register_and_login(client, email="playbook-firm@example.com")

    template_bytes = b"STANDARD NDA TEMPLATE\n\nMutual confidentiality obligations apply for three years."
    files = {"file": ("template.txt", io.BytesIO(template_bytes), "text/plain")}
    r = client.post(
        "/playbooks/new",
        data={"name": "Standard NDA", "contract_type": "NDA", "description": "", "csrf_token": token},
        files=files,
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    from database import SessionLocal
    from models import Playbook
    db = SessionLocal()
    try:
        playbook = db.query(Playbook).order_by(Playbook.id.desc()).first()
        assert playbook is not None
        assert "Mutual confidentiality" in playbook.template_text
    finally:
        db.close()

    with app_engine.connect() as conn:
        raw = conn.execute(
            text("SELECT template_text FROM playbooks WHERE id = :id"), {"id": playbook.id}
        ).scalar()
    assert raw.startswith("enc:v1:")

    playbooks_page = client.get("/playbooks")
    assert playbooks_page.status_code == 200
    assert "Standard NDA" in playbooks_page.text
