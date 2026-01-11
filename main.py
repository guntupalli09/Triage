"""
FastAPI app for Contract Risk Triage Tool

- Upload -> Stripe Checkout -> Webhook confirms payment -> Results runs analysis
- No DB, no accounts. In-memory storage with TTL.
- Uses signed tokens so Stripe session IDs are not exposed in URLs.
"""

from __future__ import annotations

import os
import io
import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from dotenv import load_dotenv

import stripe
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from PyPDF2 import PdfReader
from docx import Document

from rules_engine import RuleEngine
from evaluator import LLMEvaluator

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

APP_HMAC_SECRET = os.getenv("APP_HMAC_SECRET", "dev_secret_change_me")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Development mode: bypasses Stripe payment for testing
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# In-memory session store:
# app_session_id -> {paid: bool, text: str, expires_at: datetime, filename: str, stripe_session_id: str}
session_store: Dict[str, Dict] = {}

templates = Jinja2Templates(directory="templates")
app = FastAPI(title="Contract Risk Triage Tool", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

rule_engine = RuleEngine()
llm_evaluator = LLMEvaluator()


def cleanup_expired_sessions() -> None:
    now = datetime.now()
    expired = [k for k, v in session_store.items() if v.get("expires_at") and v["expires_at"] < now]
    for k in expired:
        del session_store[k]


def sign_token(session_id: str) -> str:
    sig = hmac.new(APP_HMAC_SECRET.encode(), session_id.encode(), hashlib.sha256).hexdigest()
    return f"{session_id}:{sig}"


def verify_token(token: str) -> Optional[str]:
    try:
        session_id, sig = token.rsplit(":", 1)
        expected = hmac.new(APP_HMAC_SECRET.encode(), session_id.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected):
            return session_id
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
    return None


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".txt":
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return file_bytes.decode("latin-1", errors="ignore")

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            try:
                text_parts.append(page.extract_text() or "")
            except Exception:
                text_parts.append("")
        return "\n".join(text_parts)

    if ext == ".docx":
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    raise ValueError("Unsupported file type")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cleanup_expired_sessions()
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_contract(file: UploadFile = File(...)):
    cleanup_expired_sessions()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, or TXT files are allowed")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        contract_text = extract_text_from_file(file_bytes, file.filename)
        if not contract_text or not contract_text.strip():
            raise HTTPException(status_code=400, detail="File appears unreadable or empty after parsing")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to parse document")

    # Create an application-level session id (NOT Stripe session id) for URL safety
    app_session_id = secrets.token_urlsafe(18)
    token = sign_token(app_session_id)

    # Development mode: skip Stripe and mark as paid immediately
    if DEV_MODE:
        logger.info("DEV_MODE enabled: bypassing Stripe payment")
        session_store[app_session_id] = {
            "paid": True,  # Mark as paid in dev mode
            "text": contract_text,
            "filename": file.filename,
            "stripe_session_id": None,
            "expires_at": datetime.now() + timedelta(hours=24),
        }
        return RedirectResponse(url=f"{BASE_URL}/results?token={token}", status_code=303)

    # Production mode: require Stripe
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    # Create Stripe Checkout Session and map it back via client_reference_id
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            client_reference_id=app_session_id,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Contract Risk Triage",
                            "description": "Automated risk triage for commercial NDAs and MSAs",
                        },
                        "unit_amount": 4900,  # $49.00
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{BASE_URL}/results?token={token}",
            cancel_url=f"{BASE_URL}/",
            metadata={"filename": file.filename},
        )
    except Exception as e:
        logger.error(f"Stripe checkout session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment session")

    # Store contract text (TTL)
    session_store[app_session_id] = {
        "paid": False,
        "text": contract_text,
        "filename": file.filename,
        "stripe_session_id": checkout.id,
        "expires_at": datetime.now() + timedelta(hours=24),
    }

    return RedirectResponse(url=checkout.url, status_code=303)


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        app_session_id = session.get("client_reference_id")
        stripe_session_id = session.get("id")

        if app_session_id and app_session_id in session_store:
            # Optional sanity check:
            stored_stripe = session_store[app_session_id].get("stripe_session_id")
            if stored_stripe and stored_stripe != stripe_session_id:
                logger.warning("Stripe session id mismatch; refusing to mark paid")
            else:
                session_store[app_session_id]["paid"] = True
                logger.info(f"Marked paid: app_session_id={app_session_id}")
        else:
            logger.warning("Webhook received for unknown app_session_id")

    return {"status": "ok"}


@app.get("/results", response_class=HTMLResponse)
async def results(request: Request, token: str):
    cleanup_expired_sessions()

    app_session_id = verify_token(token)
    if not app_session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if app_session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    entry = session_store[app_session_id]
    if not entry.get("paid") and not DEV_MODE:
        # Payment may not be confirmed yet; show a safe pending page
        return HTMLResponse(
            content="""
            <html><head><meta charset="utf-8"><title>Payment Pending</title></head>
            <body style="font-family: system-ui; max-width: 720px; margin: 40px auto;">
              <h2>Payment pending</h2>
              <p>Your payment has not been confirmed yet. This can take a few seconds.</p>
              <p>Please refresh this page shortly.</p>
            </body></html>
            """,
            status_code=202,
        )

    contract_text = entry.get("text", "")
    if not contract_text:
        raise HTTPException(status_code=500, detail="Contract text missing")

    try:
        analysis = rule_engine.analyze(contract_text)
        findings = analysis["findings"]
        overall_risk = analysis["overall_risk"]

        # ✅ VERIFICATION 1: Log deterministic engine output (ground truth)
        logger.info(
            f"Deterministic findings count={len(findings)}, "
            f"overall_risk={overall_risk}"
        )
        for f in findings:
            logger.info(
                f"RULE HIT: {f.rule_id} | {f.severity.value} | {f.title}"
            )

        findings_dict = [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "title": f.title,
                "severity": f.severity.value,
                "rationale": f.rationale,
                "matched_excerpt": f.matched_excerpt,
                "position": f.position,
                "context": f.context,
                "clause_number": f.clause_number,
                "matched_keywords": f.matched_keywords,
                "aliases": f.aliases,
            }
            for f in findings
        ]

        # ✅ VERIFICATION 2: LLM only receives findings, NOT contract text
        # The evaluator.evaluate() method receives only findings_dict, never contract_text
        llm_result = llm_evaluator.evaluate(findings=findings_dict, overall_risk=overall_risk)
        if not llm_result:
            logger.warning("LLM evaluation returned None, using fallback")
            llm_result = llm_evaluator.create_fallback_response(findings=findings_dict, overall_risk=overall_risk)

        # Calculate statistics
        rule_counts = {"high": 0, "medium": 0, "low": 0}
        for f in findings_dict:
            severity = f.get("severity", "low")
            if severity in rule_counts:
                rule_counts[severity] += 1
        
        # ✅ VERIFICATION 5: Output-level verification (UI proof)
        # Every top_issue.title in llm_result must correspond to a deterministic rule_id
        # If you see an issue not in "Detected Risk Indicators" or new risks in summary → bug
        # The template displays:
        #   - "Detected Risk Indicators" section (from top_issues)
        #   - Executive summary (from summary_bullets)
        #   - Statistics (from findings_count and rule_counts)
        # All must map back to deterministic findings only

        # Map raw findings to top_issues for clause numbers and keywords
        # Create a lookup by rule_name and title
        findings_lookup = {}
        for finding in findings_dict:
            key = finding.get("rule_name", "")
            if key not in findings_lookup:
                findings_lookup[key] = []
            findings_lookup[key].append(finding)
        
        # Enhance top_issues with clause numbers and keywords from raw findings
        enhanced_top_issues = []
        for issue in llm_result.get("top_issues", []):
            issue_title = issue.get("title", "")
            # Try to find matching finding by normalized title
            matched_finding = None
            for rule_name, findings_list in findings_lookup.items():
                for finding in findings_list:
                    finding_title = finding.get("title", "").lower()
                    if issue_title.lower() in finding_title or finding_title in issue_title.lower():
                        matched_finding = finding
                        break
                if matched_finding:
                    break
            
            # Enhance issue with clause number and keywords
            enhanced_issue = issue.copy()
            if matched_finding:
                if matched_finding.get("clause_number"):
                    enhanced_issue["clause_number"] = matched_finding["clause_number"]
                if matched_finding.get("matched_keywords"):
                    enhanced_issue["matched_keywords"] = matched_finding["matched_keywords"]
            
            enhanced_top_issues.append(enhanced_issue)

        # Render results
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "filename": entry.get("filename", "document"),
                "overall_risk": llm_result.get("overall_risk", overall_risk),
                "summary_bullets": llm_result.get("summary_bullets", []),
                "top_issues": enhanced_top_issues,
                "possible_missing_sections": llm_result.get("possible_missing_sections", []),
                "disclaimer": llm_result.get("disclaimer", "This is automated risk triage, not legal advice."),
                "findings_count": len(findings_dict),
                "rule_counts": rule_counts,
                "rule_engine_version": analysis.get("version", "1.0.3"),
            },
        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")
