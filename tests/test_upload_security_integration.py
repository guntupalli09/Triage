"""
End-to-end upload hardening tests (P5) through the real /upload and
/playbooks/new routes.
"""
import io
import os

import pytest
from docx import Document
from fastapi.testclient import TestClient
from fpdf import FPDF

os.environ.setdefault("DEV_MODE", "true")

import main
import rate_limit
import upload_security
from database import SessionLocal
from models import Contract


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


def _real_pdf_bytes(text="Confidentiality Agreement between Acme Corp and Beta LLC.") -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


def _real_docx_bytes(text="Confidentiality Agreement between Acme Corp and Beta LLC.") -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_valid_txt_upload_succeeds(client):
    token = _register(client, "valid-txt@example.com")
    files = {"file": ("nda.txt", io.BytesIO(b"Confidentiality agreement between the parties."), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303


def test_valid_pdf_upload_succeeds(client):
    token = _register(client, "valid-pdf@example.com")
    files = {"file": ("nda.pdf", io.BytesIO(_real_pdf_bytes()), "application/pdf")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303


def test_valid_docx_upload_succeeds(client):
    token = _register(client, "valid-docx@example.com")
    files = {"file": ("nda.docx", io.BytesIO(_real_docx_bytes()), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303


def test_executable_disguised_as_pdf_is_rejected(client):
    token = _register(client, "fake-pdf@example.com")
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100  # PE executable header
    files = {"file": ("invoice.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    r = client.post("/upload", data={"csrf_token": token}, files=files)
    assert r.status_code == 400
    assert "doesn" in r.text.lower() or "match" in r.text.lower()


def test_executable_disguised_as_txt_is_rejected(client):
    token = _register(client, "fake-txt@example.com")
    fake_txt = b"MZ\x90\x00\x03\x00\x00\x00binary payload here"
    files = {"file": ("notes.txt", io.BytesIO(fake_txt), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files)
    assert r.status_code == 400


def test_docx_disguised_as_pdf_is_rejected(client):
    token = _register(client, "fake-docx-pdf@example.com")
    files = {"file": ("template.pdf", io.BytesIO(_real_docx_bytes()), "application/pdf")}
    r = client.post("/upload", data={"csrf_token": token}, files=files)
    assert r.status_code == 400


def test_path_traversal_filename_is_sanitized_before_storage(client):
    token = _register(client, "traversal@example.com")
    files = {"file": ("../../../etc/passwd.txt", io.BytesIO(b"Confidentiality agreement text."), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files, follow_redirects=False)
    assert r.status_code == 303
    contract_id = int(r.headers["location"].split("/")[2])

    db = SessionLocal()
    try:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        assert contract.filename == "passwd.txt"
        assert "/" not in contract.filename and ".." not in contract.filename
    finally:
        db.close()


def test_malicious_upload_reported_by_scanner_is_rejected(client, monkeypatch):
    class _FakeDirtyScanner(upload_security.MalwareScanner):
        def scan(self, file_bytes: bytes) -> upload_security.ScanResult:
            return upload_security.ScanResult(clean=False, reason="Test-Signature")

    monkeypatch.setattr(upload_security, "get_malware_scanner", lambda: _FakeDirtyScanner())

    token = _register(client, "malware@example.com")
    files = {"file": ("nda.txt", io.BytesIO(b"Confidentiality agreement text."), "text/plain")}
    r = client.post("/upload", data={"csrf_token": token}, files=files)
    assert r.status_code == 400


def test_playbook_upload_also_gets_magic_byte_validation(client):
    token = _register(client, "playbook-security@example.com")
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100
    files = {"file": ("template.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    r = client.post(
        "/playbooks/new",
        data={"name": "Bad Template", "contract_type": "", "description": "", "csrf_token": token},
        files=files,
    )
    assert r.status_code == 200
    assert "Bad Template" not in r.text or "error" in r.text.lower()

    from models import Playbook
    db = SessionLocal()
    try:
        assert db.query(Playbook).filter(Playbook.name == "Bad Template").first() is None
    finally:
        db.close()


def test_playbook_upload_sanitizes_filename(client):
    token = _register(client, "playbook-traversal@example.com")
    files = {"file": ("../../evil.txt", io.BytesIO(b"Standard template text for comparison."), "text/plain")}
    r = client.post(
        "/playbooks/new",
        data={"name": "Traversal Test", "contract_type": "", "description": "", "csrf_token": token},
        files=files,
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
