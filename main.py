"""
FastAPI app for Contract Risk TriageCounsel Tool

Phase 1: User accounts, subscription billing, contract history, batch upload
Phase 2: Playbook comparison, dashboard, report sharing
"""
from __future__ import annotations

import os
import io
import time
import zipfile
import hmac
import hashlib
import html
import json
import logging
import secrets
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    try:
        with open(env_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        pass
    load_dotenv(dotenv_path=env_path, override=False)
else:
    load_dotenv(override=False)

import stripe
from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from security_headers import SecurityHeadersMiddleware
from rate_limit import rate_limit
from csrf import CSRFCookieMiddleware, csrf_protect, get_csrf_token
from fpdf import FPDF
from PyPDF2 import PdfReader
from docx import Document
from sqlalchemy.orm import Session as DBSession

from rules_engine import RuleEngine, FINDING_TYPE_LABELS
from confidence_index import build_confidence_breakdown
from redline_templates import render_redline
import review_workflow
from review_workflow import (
    DecisionValidationError,
    build_audit_trail_text,
    build_cover_memo_text,
    compute_progress,
    finding_key,
    validate_decision,
)
from docx_export import build_redlined_docx
from evaluator import LLMEvaluator
from database import get_db, db_session, check_db_health, check_redis_health
from auth import (
    hash_password, verify_password, create_session, get_current_user,
    logout as auth_logout, check_usage_limit, SESSION_SECRET,
    create_mfa_pending, get_mfa_pending_user_id, clear_mfa_pending,
)
import mfa
from models import User, Contract, Playbook, PolicyRule
from encryption import validate_startup as validate_encryption_startup, EncryptionConfigError
from analytics_models import UserAcquisition, UserSession, UserEvent, ContractEvent
from playbook_engine import PlaybookEngine
import liability_policy_engine
import google_oauth
import emailer
import analytics
import audit_log
import upload_security
import rbac
import retention
import playbook_workbench
import playbook_authoring as pa
import policy_enforcement
import review_queue
import document_aggregation
from analytics_middleware import AnalyticsMiddleware
from channel_classifier import CHANNELS as ACQUISITION_CHANNELS

import uuid

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    OPENAI_API_KEY = os.getenv("﻿OPENAI_API_KEY")

APP_HMAC_SECRET = os.getenv("APP_HMAC_SECRET", "dev_secret_change_me")

BASE_URL_RAW = os.getenv("BASE_URL", "").strip()
if BASE_URL_RAW:
    BASE_URL = BASE_URL_RAW.rstrip("/")
    if not BASE_URL.startswith(("http://", "https://")):
        BASE_URL = f"https://{BASE_URL}" if "localhost" not in BASE_URL else f"http://{BASE_URL}"
else:
    BASE_URL = "http://localhost:8000"

DEV_MODE = os.getenv("DEV_MODE", "false").strip().lower() == "true"

# Secure cookies by default outside dev mode. auth.py reads SECURE_COOKIES
# via os.getenv() at cookie-set time (not at import time), so setting this
# default here — before any request is served — is enough; an operator can
# still explicitly set SECURE_COOKIES=false to opt out (e.g. an internal
# deployment behind a TLS-terminating proxy that strips the scheme), but the
# default no longer silently ships session cookies over plaintext HTTP.
os.environ.setdefault("SECURE_COOKIES", "false" if DEV_MODE else "true")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

# Secrets that must never reach production: the hardcoded development
# fallbacks from auth.py / this module, and anything implausibly short to be
# a real random secret (openssl rand -hex 32 produces 64 hex chars).
_DEV_DEFAULT_SECRETS = {"dev_secret_change_me", "dev_session_secret_change_me"}
_MIN_SECRET_LENGTH = 32

if not DEV_MODE:
    if not STRIPE_SECRET_KEY:
        raise ValueError("STRIPE_SECRET_KEY required in production mode")
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET required in production mode")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY required in production mode")
    if APP_HMAC_SECRET in _DEV_DEFAULT_SECRETS or len(APP_HMAC_SECRET) < _MIN_SECRET_LENGTH:
        raise ValueError(
            "APP_HMAC_SECRET must be set to a strong random value "
            f"(>={_MIN_SECRET_LENGTH} chars) in production. "
            "Generate one with: openssl rand -hex 32"
        )
    if SESSION_SECRET in _DEV_DEFAULT_SECRETS or len(SESSION_SECRET) < _MIN_SECRET_LENGTH:
        raise ValueError(
            "SESSION_SECRET must be set to a strong random value "
            f"(>={_MIN_SECRET_LENGTH} chars) in production. "
            "Generate one with: openssl rand -hex 32"
        )
    try:
        validate_encryption_startup(dev_mode=False)
    except EncryptionConfigError as e:
        raise ValueError(f"Encryption configuration invalid: {e}") from e
    stripe.api_key = STRIPE_SECRET_KEY
else:
    validate_encryption_startup(dev_mode=True)
    stripe.api_key = STRIPE_SECRET_KEY if STRIPE_SECRET_KEY else ""

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# Plan limits
PLAN_LIMITS = {
    "starter": {
        "monthly_limit": 10, "batch_max": 3, "playbooks_max": 1,
        "monthly_price": 900, "yearly_price": 8900,
        "stripe_monthly_price_id": os.getenv("STRIPE_STARTER_MONTHLY_PRICE_ID", "").strip(),
        "stripe_yearly_price_id": os.getenv("STRIPE_STARTER_YEARLY_PRICE_ID", "").strip(),
    },
    "professional": {
        "monthly_limit": 150, "batch_max": 10, "playbooks_max": 5,
        "monthly_price": 4900, "yearly_price": 47000,
        "stripe_monthly_price_id": os.getenv("STRIPE_PROFESSIONAL_MONTHLY_PRICE_ID", "").strip(),
        "stripe_yearly_price_id": os.getenv("STRIPE_PROFESSIONAL_YEARLY_PRICE_ID", "").strip(),
    },
    "team": {
        "monthly_limit": 999999, "batch_max": 50, "playbooks_max": 50,
        "monthly_price": 19900, "yearly_price": 189900,
        "stripe_monthly_price_id": os.getenv("STRIPE_TEAM_MONTHLY_PRICE_ID", "").strip(),
        "stripe_yearly_price_id": os.getenv("STRIPE_TEAM_YEARLY_PRICE_ID", "").strip(),
    },
    "unlimited": {
        "monthly_limit": 999999, "batch_max": 50, "playbooks_max": 50,
        "monthly_price": 19900, "yearly_price": 189900,
        "stripe_monthly_price_id": os.getenv("STRIPE_UNLIMITED_MONTHLY_PRICE_ID", "").strip(),
        "stripe_yearly_price_id": os.getenv("STRIPE_UNLIMITED_YEARLY_PRICE_ID", "").strip(),
    },
}

# --- App setup ---
templates = Jinja2Templates(directory="templates")
templates.env.globals["google_signin_enabled"] = google_oauth.is_configured()
templates.env.globals["csrf_token"] = get_csrf_token
app = FastAPI(title="Contract Risk TriageCounsel Tool", version="2.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", BASE_URL).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

app.add_middleware(AnalyticsMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFCookieMiddleware)

app.include_router(playbook_workbench.router)

rule_engine = RuleEngine()
llm_evaluator = LLMEvaluator()
playbook_engine = PlaybookEngine()

# Legacy in-memory session store (for backward compat with unsigned uploads)
session_store: Dict[str, Dict] = {}


@app.on_event("startup")
def on_startup():
    from database import DATABASE_URL, init_db, SessionLocal
    # Ensure tables exist regardless of server (gunicorn hooks don't run under
    # uvicorn or serverless); create_all is a no-op when the schema is present.
    init_db()

    _rbac_db = SessionLocal()
    try:
        rbac.ensure_seed_roles_and_permissions(_rbac_db)
        rbac.bootstrap_initial_admin(_rbac_db)
    except Exception:
        logger.exception("RBAC startup seeding failed — admin access may not work until resolved")
    finally:
        _rbac_db.close()

    db_type = "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"
    redis_url = os.getenv("REDIS_URL")
    logger.info(f"Triage Counsel worker ready | mode={'DEMO' if DEV_MODE else 'PROD'} | db={db_type} | redis={'yes' if redis_url else 'no'} | pid={os.getpid()}")
    if not DEV_MODE and "sqlite" in DATABASE_URL:
        logger.warning("Running production mode with SQLite — use PostgreSQL for reliability")

    # Phase 4 release gate (requirement 7): refuse to boot in cutover mode
    # if any legacy limitation_of_liability PolicyRule lacks an equivalent
    # ACTIVE PolicyPosition — fail closed rather than silently dropping
    # enforcement for that playbook's live contract review.
    if policy_enforcement.get_enforcement_mode() == "cutover":
        _gate_db = SessionLocal()
        try:
            policy_enforcement.verify_migration_coverage_or_fail_closed(_gate_db)
        finally:
            _gate_db.close()


@app.on_event("shutdown")
def on_shutdown():
    logger.info(f"Triage Counsel worker shutting down | pid={os.getpid()}")


# --- Helpers ---

def require_user(request: Request, db: DBSession) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Single choke point for every upload path (single/batch contract
    upload, playbook create/edit) — see upload_security.py. Magic-byte
    validation, malware scanning, and the zip/PDF-bomb guards all happen
    here so every call site gets them without duplicating the checks."""
    ext = os.path.splitext(filename.lower())[1]

    upload_security.validate_magic_bytes(file_bytes, ext)
    upload_security.scan_for_malware(file_bytes)

    if ext == ".txt":
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return file_bytes.decode("latin-1", errors="ignore")
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        upload_security.validate_pdf_page_count(len(reader.pages))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        return upload_security.enforce_extracted_text_limit(text)
    if ext == ".docx":
        upload_security.validate_docx_zip_safety(file_bytes)
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in doc.paragraphs)
        return upload_security.enforce_extracted_text_limit(text)
    raise ValueError("Unsupported file type")


def run_analysis(contract_text: str) -> Dict:
    """Run rule engine + LLM evaluation, return full analysis dict."""
    analysis = rule_engine.analyze(contract_text)
    findings = analysis["findings"]
    overall_risk = analysis["overall_risk"]

    contradiction_log = analysis.get("contradiction_log", {})
    metadata = analysis.get("metadata", {})
    findings_dict = [
        {
            "rule_id": f.rule_id, "rule_name": f.rule_name, "title": f.title,
            "severity": f.severity.value, "rationale": f.rationale,
            "matched_excerpt": f.matched_excerpt, "position": f.position,
            "context": f.context, "clause_number": f.clause_number,
            "matched_keywords": f.matched_keywords, "aliases": f.aliases,
            "start_index": f.start_index, "end_index": f.end_index,
            "exact_snippet": f.exact_snippet, "evidence": f.evidence,
            "party_direction": f.party_direction,
            "finding_type": f.finding_type,
            "finding_type_label": FINDING_TYPE_LABELS.get(f.finding_type, f.finding_type),
            # Lawyer Confidence Index — see confidence_index.py. Restructures
            # the confidence/confidence_reason this finding already carries
            # into an explicit, checkable breakdown; no new detection.
            "confidence_breakdown": build_confidence_breakdown(f, contradiction_log).as_dict(),
            # Deterministic Legal Work Product — see redline_templates.py.
            # One reviewed default redline per rule_id; None when this
            # finding's rule isn't in the curated covered set yet — never a
            # generated fallback.
            "redline": render_redline(f, metadata),
        }
        for f in findings
    ]

    try:
        llm_result = llm_evaluator.evaluate(findings=findings_dict, overall_risk=overall_risk, contract_text=None)
        if not llm_result:
            llm_result = llm_evaluator.create_fallback_response(findings=findings_dict, overall_risk=overall_risk)
            llm_result["explanation_source"] = "rules_fallback"
        else:
            llm_result["explanation_source"] = "llm"
    except Exception:
        llm_result = llm_evaluator.create_fallback_response(findings=findings_dict, overall_risk=overall_risk)
        llm_result["explanation_source"] = "rules_fallback"

    return {
        "findings_dict": findings_dict,
        "overall_risk": overall_risk,
        "llm_result": llm_result,
        "rule_counts": analysis.get("rule_counts", {"critical": 0, "high": 0, "medium": 0, "low": 0}),
        "version": analysis.get("version", "1.0.3"),
        # Business workflow decision layer, additive to overall_risk: what
        # should happen to this contract next (ready to send / commercial
        # review / legal review / blocked by policy), not just how risky it is.
        "signature_readiness": analysis.get("signature_readiness"),
        "blocking_findings": analysis.get("blocking_findings", []),
        "policy_blocked_findings": analysis.get("policy_blocked_findings", []),
        "non_blocking_findings": analysis.get("non_blocking_findings", []),
        # Structured contract-to-cash terms for comparison against an actual
        # invoice configuration (due_days, currency, billing_frequency, invoice_trigger).
        "payment_terms": analysis.get("payment_terms", {}),
        # Three-score risk dashboard (Legal Risk / Business Risk /
        # Negotiation Difficulty) — see risk_dashboard.py.
        "risk_dashboard": analysis.get("risk_dashboard", {}),
        # Defined-terms & cross-reference integrity — see structure_checker.py.
        "structure_report": analysis.get("structure_report", {}),
        # Deterministic Clause Quality Engine — see clause_quality.py.
        "clause_quality": analysis.get("clause_quality", {}),
        # Deterministic party/effective-date/contract-type extraction — see
        # metadata_extractor.py.
        "metadata": analysis.get("metadata", {}),
        # Risk Allocation & Clause Balance Score — see risk_balance.py.
        "risk_balance": analysis.get("risk_balance", {}),
    }


# Phase 4: policy enforcement (which policy source is authoritative — legacy
# PolicyRule vs ACTIVE PolicyPosition — and how each is evaluated) now lives
# entirely in policy_enforcement.py; apply_liability_policy is re-exported
# here unchanged so nothing else in this file (or any external call site)
# needs to change its import. See policy_enforcement.apply_policies_for_review
# for the mode-dispatching entry point this file actually calls below.
apply_liability_policy = policy_enforcement.apply_liability_policy


def build_enhanced_issues(findings_dict: List[Dict], llm_result: Dict) -> List[Dict]:
    """Build complete list of findings enhanced with LLM explanations."""
    llm_issues_map = {}
    for issue in llm_result.get("top_issues", []):
        llm_issues_map[issue.get("title", "").lower()] = issue

    all_issues = []
    seen_finding_keys = set()

    for finding in findings_dict:
        rule_id = finding.get("rule_id", "")
        # Dedup key includes location (start_index/end_index/clause_number),
        # not rule_id alone -- rules_engine.analyze() already documents its
        # own internal dedup as "(rule_id, clause_number)" (step 4 of its
        # docstring), meaning it deliberately PRESERVES the same rule firing
        # on two genuinely different clause occurrences in one document
        # (e.g. the same uncapped-liability pattern matched in two separate
        # provisions). A rule_id-only key here silently collapsed that back
        # down to one, discarding a materially distinct finding -- found via
        # Step 4B Phase B's deduplication inventory, reproduced directly
        # against this function before fixing. policy_decision/
        # interaction_decision synthetic findings are unaffected (each
        # clause_type/interaction_id already produces at most one finding
        # per review by construction, so this key is still exactly as
        # unique for them as rule_id alone was).
        finding_key = (rule_id, finding.get("start_index"), finding.get("end_index"), finding.get("clause_number"))
        if finding_key in seen_finding_keys:
            continue
        seen_finding_keys.add(finding_key)

        finding_title = finding.get("title", "").lower()
        llm_issue = None
        for llm_title, llm_data in llm_issues_map.items():
            if finding_title in llm_title or llm_title in finding_title:
                llm_issue = llm_data
                break

        if llm_issue:
            enhanced = llm_issue.copy()
            enhanced["severity"] = finding.get("severity", llm_issue.get("severity", "low"))
        else:
            # No LLM explanation for this finding — surface only the
            # deterministic rationale rather than repeating canned filler text
            # (identical "analysis"/"negotiation" lines on every finding read
            # as fake and undermine trust in the report).
            enhanced = {
                "title": finding.get("title", ""),
                "severity": finding.get("severity", "low"),
            }

        enhanced["rule_id"] = finding.get("rule_id", "")
        enhanced["rationale"] = finding.get("rationale", "")
        enhanced["exact_snippet"] = finding.get("exact_snippet", "")
        enhanced["context"] = finding.get("context", "")
        if finding.get("clause_number"):
            enhanced["clause_number"] = finding["clause_number"]
        if finding.get("matched_keywords"):
            enhanced["matched_keywords"] = finding["matched_keywords"]
        if finding.get("matched_excerpt"):
            enhanced["matched_excerpt"] = finding["matched_excerpt"]
        if finding.get("evidence"):
            # Proximity-rule findings: anchor trigger word, the actual risky
            # phrase found near it, and the surrounding clause — not just the
            # bare anchor keyword.
            enhanced["evidence"] = finding["evidence"]
        if finding.get("party_direction"):
            # "One-way"/unilateral rules: obligor, beneficiary, applies_to,
            # and mutuality_status, so the UI never asserts one-sidedness
            # the engine hasn't actually established.
            enhanced["party_direction"] = finding["party_direction"]
        # "Adverse language detected" / "Expected protection not found" /
        # "Unable to determine" are different claims with different
        # evidentiary weight — always surface which one this is so the UI
        # never presents them as the same thing.
        enhanced["finding_type"] = finding.get("finding_type", "adverse_language_detected")
        enhanced["finding_type_label"] = finding.get(
            "finding_type_label", FINDING_TYPE_LABELS.get(enhanced["finding_type"], enhanced["finding_type"])
        )
        if finding.get("confidence_breakdown"):
            enhanced["confidence_breakdown"] = finding["confidence_breakdown"]
        if finding.get("redline"):
            enhanced["redline"] = finding["redline"]

        all_issues.append(enhanced)

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_issues.sort(key=lambda x: (severity_order.get(x.get("severity", "low"), 9), x.get("title", "")))
    return all_issues


def display_rule_stats(all_issues: List[Dict]) -> Dict[str, int]:
    """Severity counts over the deduplicated issue list shown to the user.

    Raw engine counts include multiple matches of the same rule, but the
    report renders one card per rule — summary tiles must match the cards
    or the numbers look wrong to the reader.
    """
    # "critical" is a distinct top tier (see rules_engine.Severity), not a
    # variant of "high" — without its own bucket here, a critical finding
    # would silently fall into the "low" count via the unrecognized-value
    # fallback below, which is actively misleading for the most severe
    # findings in the report.
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for issue in all_issues:
        sev = (issue.get("severity") or "low").lower()
        counts[sev if sev in counts else "low"] += 1
    return counts


def sanitize_filename(filename: str) -> str:
    name_without_ext = Path(filename).stem
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name_without_ext)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized[:50] if len(sanitized) > 50 else sanitized


def get_base_url(request: Request) -> str:
    if BASE_URL and BASE_URL != "http://localhost:8000":
        return BASE_URL
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.hostname)
    return f"{scheme}://{host}".rstrip("/")


# --- Error handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        if exc.status_code == 302:
            return RedirectResponse(url=exc.headers.get("Location", "/login"), status_code=302)
        raise exc
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return HTMLResponse(
        content='<html><body style="font-family:system-ui;max-width:600px;margin:60px auto;text-align:center">'
        '<h2>Something went wrong</h2><p>Please try again.</p>'
        '<a href="/" style="color:#FF7A18">Back to Home</a></body></html>',
        status_code=500,
    )


# ============================================================
# AUTH ROUTES
# ============================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    notice = "Your password has been updated. Log in with your new password." \
        if request.query_params.get("reset") == "success" else None
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "notice": notice})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request, email: str = Form(...), password: str = Form(...), db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("login", limit=10, window_seconds=60)),
    _csrf: None = Depends(csrf_protect),
):
    normalized_email = email.lower().strip()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(password, user.password_hash):
        audit_log.record_event(
            db, "login_failed", request=request, actor_user_id=user.id if user else None,
            target_type="user", target_id=user.id if user else None,
            success=False, detail="invalid_credentials", metadata={"email": normalized_email},
        )
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password."})
    if user.mfa_enabled:
        response = RedirectResponse(url="/login/mfa", status_code=302)
        create_mfa_pending(user.id, response)
        audit_log.record_event(
            db, "login_mfa_challenge", request=request, actor_user_id=user.id,
            target_type="user", target_id=user.id, success=True,
        )
        return response

    response = RedirectResponse(url="/dashboard", status_code=302)
    create_session(user.id, response)
    analytics.mark_session_authenticated(request, user)
    analytics.record_event(request, "login", user=user)
    audit_log.record_event(
        db, "login", request=request, actor_user_id=user.id,
        target_type="user", target_id=user.id, success=True,
    )
    return response


@app.get("/login/mfa", response_class=HTMLResponse)
async def login_mfa_page(request: Request, db: DBSession = Depends(get_db)):
    user_id = get_mfa_pending_user_id(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("login_mfa.html", {"request": request, "error": None})


@app.post("/login/mfa", response_class=HTMLResponse)
async def login_mfa_submit(
    request: Request, code: str = Form(...), db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("login-mfa", limit=8, window_seconds=300)),
    _csrf: None = Depends(csrf_protect),
):
    user_id = get_mfa_pending_user_id(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.mfa_enabled:
        return RedirectResponse(url="/login", status_code=302)

    used_recovery_code = False
    ok = mfa.verify_totp_code(user.mfa_secret, code)
    if not ok:
        matched, updated_codes = mfa.verify_and_consume_recovery_code(user.mfa_recovery_codes_json, code)
        if matched:
            ok = True
            used_recovery_code = True
            user.mfa_recovery_codes_json = updated_codes
            db.commit()

    if not ok:
        audit_log.record_event(
            db, "login_mfa_failed", request=request, actor_user_id=user.id,
            target_type="user", target_id=user.id, success=False,
        )
        return templates.TemplateResponse("login_mfa.html", {
            "request": request, "error": "That code isn’t valid. Please try again.",
        })

    response = RedirectResponse(url="/dashboard", status_code=302)
    create_session(user.id, response)
    clear_mfa_pending(request, response)
    analytics.mark_session_authenticated(request, user)
    analytics.record_event(request, "login", user=user)
    audit_log.record_event(
        db, "login", request=request, actor_user_id=user.id,
        target_type="user", target_id=user.id, success=True,
        detail="mfa_recovery_code" if used_recovery_code else "mfa_totp",
    )
    if used_recovery_code:
        audit_log.record_event(
            db, "mfa_recovery_code_used", request=request, actor_user_id=user.id,
            target_type="user", target_id=user.id, success=True,
            metadata={"remaining_codes": mfa.count_remaining_recovery_codes(user.mfa_recovery_codes_json)},
        )
    return response


def _is_guest_account(user: Optional[User]) -> bool:
    return bool(user and user.email.endswith("@guest.triagecounsel.local"))


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: DBSession = Depends(get_db)):
    current = get_current_user(request, db)
    analytics.record_event(request, "signup_started")
    return templates.TemplateResponse("register.html", {
        "request": request, "error": None, "claiming": _is_guest_account(current),
    })


@app.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    name: str = Form(""),
    company: str = Form(""),
    db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("register", limit=5, window_seconds=60)),
    _csrf: None = Depends(csrf_protect),
):
    email = email.lower().strip()
    current = get_current_user(request, db)
    claiming = _is_guest_account(current)

    def error(message: str):
        return templates.TemplateResponse("register.html", {"request": request, "error": message, "claiming": claiming})

    if password != confirm_password:
        return error("Passwords do not match.")
    if len(password) < 8:
        return error("Password must be at least 8 characters.")
    existing = db.query(User).filter(User.email == email).first()
    if existing and not (claiming and existing.id == current.id):
        return error("An account with this email already exists.")

    if claiming:
        # Upgrade the existing guest account in place — same row, same id,
        # so every contract it already owns (from the demo or from an
        # anonymous "Start Free Review" upload) stays exactly where it is,
        # just now reachable from a real, permanent, password-protected
        # account instead of a throwaway one nobody could log back into.
        user = current
        user.email = email
        user.password_hash = hash_password(password)
        user.name = name.strip() or None
        user.company = company.strip() or None
        db.commit()
        analytics.record_event(request, "guest_account_claimed", user=user)
        audit_log.record_event(
            db, "account_created", request=request, actor_user_id=user.id,
            target_type="user", target_id=user.id, success=True,
            metadata={"claimed_guest_account": True},
        )
        return RedirectResponse(url="/dashboard", status_code=302)

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name.strip() or None,
        company=company.strip() or None,
        plan="free",
        monthly_limit=3,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    rbac.grant_role(db, user, "user")

    analytics.persist_user_acquisition(db, user, request)
    analytics.mark_session_authenticated(request, user)
    analytics.record_event(request, "signup_completed", user=user)
    audit_log.record_event(
        db, "account_created", request=request, actor_user_id=user.id,
        target_type="user", target_id=user.id, success=True,
    )

    response = RedirectResponse(url="/dashboard", status_code=302)
    create_session(user.id, response)
    return response


@app.get("/logout")
async def logout_route(request: Request, db: DBSession = Depends(get_db)):
    current = get_current_user(request, db)
    if current:
        analytics.record_event(request, "logout", user=current)
        audit_log.record_event(
            db, "logout", request=request, actor_user_id=current.id,
            target_type="user", target_id=current.id, success=True,
        )
    analytics.end_session(request)
    response = RedirectResponse(url="/", status_code=302)
    auth_logout(request, response)
    return response


# ============================================================
# GOOGLE SIGN-IN
# ============================================================

GOOGLE_STATE_COOKIE = "g_oauth_state"


@app.get("/auth/google")
def google_signin_start(request: Request):
    if not google_oauth.is_configured():
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Google sign-in is not configured.",
        })
    state = secrets.token_urlsafe(24)
    redirect_uri = f"{get_base_url(request)}/auth/google/callback"
    response = RedirectResponse(url=google_oauth.build_auth_url(redirect_uri, state), status_code=302)
    response.set_cookie(
        GOOGLE_STATE_COOKIE, state,
        max_age=600, httponly=True, samesite="lax",
        secure=os.getenv("SECURE_COOKIES", "false").lower() == "true",
    )
    # Acquisition context (referrer/UTM/landing page/session id) is already
    # captured by AnalyticsMiddleware's first-touch cookie before we ever
    # get here, and that cookie rides along through the Google redirect
    # round-trip since it's scoped to this domain — no extra stash needed.
    analytics.record_event(request, "google_oauth_redirect")
    return response


@app.get("/auth/google/callback")
def google_signin_callback(request: Request, code: str = "", state: str = "", error: str = "", db: DBSession = Depends(get_db)):
    def fail(message: str):
        return templates.TemplateResponse("login.html", {"request": request, "error": message})

    if error or not code:
        return fail("Google sign-in was cancelled.")

    expected_state = request.cookies.get(GOOGLE_STATE_COOKIE, "")
    if not expected_state or not hmac.compare_digest(expected_state, state):
        return fail("Sign-in session expired. Please try again.")

    redirect_uri = f"{get_base_url(request)}/auth/google/callback"
    try:
        tokens = google_oauth.exchange_code(code, redirect_uri)
        claims = google_oauth.decode_id_token(tokens["id_token"])
    except Exception:
        logger.exception("Google sign-in token exchange failed")
        return fail("Google sign-in failed. Please try again.")

    if not claims.get("email_verified"):
        return fail("Your Google account's email address is not verified.")
    email = claims.get("email", "").lower().strip()
    google_sub = claims.get("sub", "")
    if not email or not google_sub:
        return fail("Google did not return the required account details.")

    user = db.query(User).filter(User.google_sub == google_sub).first()
    is_new_user = False
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Existing email/password account — link it (Google verified the email)
            user.google_sub = google_sub
            if not user.name and claims.get("name"):
                user.name = claims["name"]
        else:
            is_new_user = True
            user = User(
                email=email,
                password_hash=None,
                name=claims.get("name"),
                google_sub=google_sub,
                plan="free",
                monthly_limit=3,
            )
            db.add(user)
        db.commit()
        db.refresh(user)

    analytics.record_event(request, "google_oauth_callback", user=user)
    # Never lose acquisition info to the OAuth redirect: this persists once,
    # immutably, using the first-touch cookie captured before Google ever
    # saw this browser (see google_signin_start above).
    analytics.persist_user_acquisition(db, user, request)
    analytics.mark_session_authenticated(request, user)
    analytics.record_event(request, "signup_completed" if is_new_user else "login", user=user)
    if is_new_user:
        rbac.grant_role(db, user, "user")

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.delete_cookie(GOOGLE_STATE_COOKIE)
    create_session(user.id, response)
    return response


# ============================================================
# PASSWORD RESET
# ============================================================

RESET_TOKEN_MAX_AGE = timedelta(hours=1)


def _find_user_by_reset_token(db: DBSession, token: str) -> Optional[User]:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()
    if not user or not user.reset_token_expires_at:
        return None
    if datetime.utcnow() > user.reset_token_expires_at:
        return None
    return user


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {
        "request": request, "error": None, "sent": False,
    })


@app.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request, email: str = Form(...), db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("forgot-password", limit=5, window_seconds=900)),
    _csrf: None = Depends(csrf_protect),
):
    if not emailer.is_configured():
        return templates.TemplateResponse("forgot_password.html", {
            "request": request, "sent": False,
            "error": "Password reset email is temporarily unavailable. Please reach out via the contact page and we'll restore your access.",
        })

    email = email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token_hash = hashlib.sha256(token.encode()).hexdigest()
        user.reset_token_expires_at = datetime.utcnow() + RESET_TOKEN_MAX_AGE
        db.commit()
        reset_url = f"{get_base_url(request)}/reset-password?token={token}"
        try:
            emailer.send_email(
                to=user.email,
                subject="Reset your Triage Counsel password",
                html=(
                    f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto">'
                    f'<h2 style="color:#0F172A">Reset your password</h2>'
                    f'<p>We received a request to reset the password for <strong>{user.email}</strong>.</p>'
                    f'<p><a href="{reset_url}" style="display:inline-block;background:#0F172A;color:#fff;'
                    f'padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">Choose a new password</a></p>'
                    f'<p style="color:#64748B;font-size:13px">This link expires in 1 hour and can be used once. '
                    f'If you didn\'t request this, you can safely ignore this email — your password will not change.</p>'
                    f'</div>'
                ),
                text=(
                    f"We received a request to reset the password for {user.email}.\n\n"
                    f"Choose a new password: {reset_url}\n\n"
                    f"This link expires in 1 hour and can be used once. "
                    f"If you didn't request this, you can safely ignore this email."
                ),
            )
        except Exception:
            logger.exception(f"Failed to send password reset email to {user.email}")
            return templates.TemplateResponse("forgot_password.html", {
                "request": request, "sent": False,
                "error": "We couldn't send the email. Please try again in a few minutes or reach out via the contact page.",
            })

    # Same response whether or not the account exists (prevents email enumeration)
    return templates.TemplateResponse("forgot_password.html", {
        "request": request, "error": None, "sent": True,
    })


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = "", db: DBSession = Depends(get_db)):
    user = _find_user_by_reset_token(db, token)
    if not user:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "token": None, "error": None,
        })
    return templates.TemplateResponse("reset_password.html", {
        "request": request, "token": token, "error": None,
    })


@app.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("reset-password", limit=10, window_seconds=3600)),
    _csrf: None = Depends(csrf_protect),
):
    user = _find_user_by_reset_token(db, token)
    if not user:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "token": None, "error": None,
        })

    error = None
    if password != confirm_password:
        error = "Passwords do not match."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    if error:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, "token": token, "error": error,
        })

    user.password_hash = hash_password(password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.commit()
    return RedirectResponse(url="/login?reset=success", status_code=302)


# ============================================================
# ACCOUNT
# ============================================================

@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    return templates.TemplateResponse("account.html", {
        "request": request, "user": user, "error": None, "success": None,
        "current_year": datetime.now().year,
    })


@app.post("/account", response_class=HTMLResponse)
async def account_update(
    request: Request, name: str = Form(""), company: str = Form(""), db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    user.name = name.strip() or None
    user.company = company.strip() or None
    db.commit()
    return templates.TemplateResponse("account.html", {
        "request": request, "user": user, "error": None, "success": "Profile updated.",
        "current_year": datetime.now().year,
    })


@app.post("/account/password", response_class=HTMLResponse)
async def account_change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)

    error = None
    if not verify_password(current_password, user.password_hash):
        error = "Current password is incorrect."
    elif new_password != confirm_password:
        error = "New passwords do not match."
    elif len(new_password) < 8:
        error = "New password must be at least 8 characters."

    if error:
        return templates.TemplateResponse("account.html", {
            "request": request, "user": user, "error": error, "success": None,
            "current_year": datetime.now().year,
        })

    user.password_hash = hash_password(new_password)
    db.commit()
    return templates.TemplateResponse("account.html", {
        "request": request, "user": user, "error": None, "success": "Password updated.",
        "current_year": datetime.now().year,
    })


# ============================================================
# BILLING
# ============================================================

@app.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    return templates.TemplateResponse("billing.html", {
        "request": request, "user": user, "error": None, "success": None,
        "current_year": datetime.now().year,
    })


@app.post("/billing/cancel")
async def billing_cancel(request: Request, db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect)):
    user = require_user(request, db)

    if user.stripe_subscription_id and stripe.api_key:
        try:
            stripe.Subscription.modify(user.stripe_subscription_id, cancel_at_period_end=True)
        except Exception as e:
            logger.warning(f"Failed to cancel Stripe subscription for user {user.id}: {e}")
            return templates.TemplateResponse("billing.html", {
                "request": request, "user": user, "success": None,
                "error": "Failed to cancel subscription. Please try again or contact support.",
                "current_year": datetime.now().year,
            })

    user.subscription_status = "canceled"
    db.commit()
    return templates.TemplateResponse("billing.html", {
        "request": request, "user": user, "error": None,
        "success": "Your subscription has been canceled and will not renew.",
        "current_year": datetime.now().year,
    })


# ============================================================
# SETTINGS
# ============================================================

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    return templates.TemplateResponse("settings.html", {
        "request": request, "user": user, "error": None,
        "current_year": datetime.now().year,
    })


# ============================================================
# TWO-FACTOR AUTHENTICATION (TOTP) — see mfa.py. Opt-in per user.
# ============================================================

@app.get("/settings/mfa", response_class=HTMLResponse)
async def mfa_settings_page(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    return templates.TemplateResponse("mfa_settings.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
        "remaining_recovery_codes": mfa.count_remaining_recovery_codes(user.mfa_recovery_codes_json),
    })


@app.get("/settings/mfa/setup", response_class=HTMLResponse)
async def mfa_setup_page(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    if user.mfa_enabled:
        return RedirectResponse(url="/settings/mfa", status_code=302)
    # A secret already exists from a previous, unfinished setup attempt —
    # reuse it so the QR code the user is looking at stays valid instead
    # of silently going stale if they reload this page.
    if not user.mfa_secret:
        user.mfa_secret = mfa.generate_secret()
        db.commit()
    uri = mfa.provisioning_uri(user.mfa_secret, user.email)
    return templates.TemplateResponse("mfa_setup.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
        "qr_code_data_uri": mfa.qr_code_svg_data_uri(uri),
        "manual_key": user.mfa_secret, "error": None,
    })


@app.post("/settings/mfa/setup", response_class=HTMLResponse)
async def mfa_setup_confirm(
    request: Request, code: str = Form(...), db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("mfa-setup", limit=8, window_seconds=300)),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    if user.mfa_enabled:
        return RedirectResponse(url="/settings/mfa", status_code=302)
    if not user.mfa_secret:
        return RedirectResponse(url="/settings/mfa/setup", status_code=302)

    if not mfa.verify_totp_code(user.mfa_secret, code):
        uri = mfa.provisioning_uri(user.mfa_secret, user.email)
        return templates.TemplateResponse("mfa_setup.html", {
            "request": request, "user": user, "current_year": datetime.now().year,
            "qr_code_data_uri": mfa.qr_code_svg_data_uri(uri),
            "manual_key": user.mfa_secret,
            "error": "That code isn’t valid. Make sure your authenticator app’s clock is correct, then try again.",
        })

    recovery_codes = mfa.generate_recovery_codes()
    user.mfa_enabled = True
    user.mfa_enrolled_at = datetime.utcnow()
    user.mfa_recovery_codes_json = mfa.build_recovery_codes_record(recovery_codes)
    db.commit()

    audit_log.record_event(
        db, "mfa_enabled", request=request, actor_user_id=user.id,
        target_type="user", target_id=user.id, success=True,
    )
    return templates.TemplateResponse("mfa_recovery_codes.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
        "recovery_codes": recovery_codes,
    })


@app.post("/settings/mfa/disable")
async def mfa_disable(
    request: Request, password: str = Form(""), db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("mfa-disable", limit=8, window_seconds=300)),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    # Re-confirms the current password so a hijacked session token alone
    # can't silently turn off MFA. Google-only accounts have no password
    # to check (password_hash is None) — nothing further to verify here
    # within this codebase's scope for that case.
    if user.password_hash and not verify_password(password, user.password_hash):
        return templates.TemplateResponse("mfa_settings.html", {
            "request": request, "user": user, "current_year": datetime.now().year,
            "remaining_recovery_codes": mfa.count_remaining_recovery_codes(user.mfa_recovery_codes_json),
            "error": "Incorrect password.",
        }, status_code=403)

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_recovery_codes_json = None
    user.mfa_enrolled_at = None
    db.commit()

    audit_log.record_event(
        db, "mfa_disabled", request=request, actor_user_id=user.id,
        target_type="user", target_id=user.id, success=True,
    )
    return RedirectResponse(url="/settings/mfa", status_code=302)


@app.post("/settings/delete-account")
async def delete_account(request: Request, db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect)):
    user = require_user(request, db)
    user_id, user_email = user.id, user.email

    db.query(Contract).filter(Contract.user_id == user.id).delete()
    db.query(Playbook).filter(Playbook.user_id == user.id).delete()
    db.delete(user)
    db.commit()

    # Logged after the deletion commits (not before): AuditLog.target_id has
    # no FK constraint specifically so this record can outlive the user row
    # it describes, but record_event() does its own commit — running it
    # first would just commit this transaction early rather than after.
    audit_log.record_event(
        db, "account_deleted", request=request, actor_user_id=user_id,
        target_type="user", target_id=user_id, success=True,
        metadata={"email": user_email},
    )

    response = RedirectResponse(url="/", status_code=302)
    auth_logout(request, response)
    return response


# ============================================================
# DOCUMENT-LEVEL AGGREGATION (Step 4B) -- attention-queue safety
# ============================================================
#
# Contract.overall_risk (legacy pattern-match risk, computed before the
# policy/interaction layers ever run -- see
# artifacts/step4b/document_aggregation_spec.md) is not sufficient, on its
# own, to decide whether a contract needs a lawyer's attention: a contract
# can have overall_risk == "low" while the deterministic policy layer (in
# cutover mode) finds a PROHIBITED clause, or the Interaction Engine finds
# a critical cross-policy conflict. document_aggregation.aggregate_document_state
# is the single aggregation authority for that richer signal -- this
# module never recomputes policy truth itself, only reads what the policy
# and interaction layers already decided and persisted.
#
# `policy_decisions_json`/`interaction_decisions_json` are EncryptedJSON
# columns (see encryption.py) -- their content cannot be filtered or
# aggregated in SQL, so this is computed here, in Python, per already-
# fetched row, not as a query. See the consumer map/mode-contract doc
# (artifacts/step4b/consumer_map_and_mode_contract.md §4) for why no
# schema migration or persisted summary column was added for this.
_DOCUMENT_MATERIAL_STATES = frozenset({
    document_aggregation.DOC_HAS_CRITICAL_INTERACTION,
    document_aggregation.DOC_HAS_POLICY_VIOLATION,
    document_aggregation.DOC_REQUIRES_REVIEW,
    document_aggregation.DOC_CONFIGURATION_UNRESOLVED,
})


def _document_state_for_contract(contract: "Contract") -> str:
    """Read-time-only aggregation (no write, no recomputation of policy
    truth) -- see module note above. `interaction_decisions_json is not
    None` is used as a positive signal that this contract's review ran
    under cutover mode (only the cutover branch of
    policy_enforcement.apply_policies_for_review ever populates it, even
    with every rule NOT_TRIGGERED); this is an approximation, not a stored
    fact (no per-contract enforcement-mode column exists), and is
    deliberately conservative: an ambiguous legacy/shadow-shaped contract
    (interaction_decisions_json is None) is never escalated to
    CONFIGURATION_UNRESOLVED by this approximation, only ever a real
    cutover-shaped one. See consumer_map_and_mode_contract.md §2 mode
    contract for the full reasoning."""
    effective_mode = "cutover" if contract.interaction_decisions_json is not None else "shadow"
    result = document_aggregation.aggregate_document_state(
        contract.overall_risk, contract.policy_decisions_json, contract.interaction_decisions_json, effective_mode,
    )
    return result["document_state"]


def _needs_attention(contract: "Contract") -> bool:
    return _document_state_for_contract(contract) in _DOCUMENT_MATERIAL_STATES


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    analytics.record_event(request, "dashboard_view", user=user)
    contracts = db.query(Contract).filter(
        Contract.user_id == user.id, Contract.analysis_completed == True
    ).order_by(Contract.created_at.desc()).limit(20).all()

    total = db.query(Contract).filter(Contract.user_id == user.id, Contract.analysis_completed == True).count()
    high_count = db.query(Contract).filter(
        Contract.user_id == user.id, Contract.overall_risk == "high", Contract.analysis_completed == True
    ).count()
    # Attention count -- must include contracts a bare overall_risk=="high"
    # filter would miss (see _document_state_for_contract above). Computed
    # in Python (EncryptedJSON columns cannot be filtered in SQL), scoped
    # to this user only, same bound the pre-existing total/high_count
    # queries already use.
    all_user_contracts = db.query(Contract).filter(
        Contract.user_id == user.id, Contract.analysis_completed == True
    ).all()
    attention_count = sum(1 for c in all_user_contracts if _needs_attention(c))

    stats = {
        "total_contracts": total,
        "high_risk_count": high_count,
        "attention_count": attention_count,
        "contracts_this_month": user.contracts_this_month,
    }
    document_states = {c.id: _document_state_for_contract(c) for c in contracts}

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "contracts": contracts,
        "stats": stats, "document_states": document_states, "current_year": datetime.now().year,
    })


# ============================================================
# CONTRACT HISTORY
# ============================================================

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request, q: str = "", risk: str = "", page: int = 1, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    per_page = 25

    query = db.query(Contract).filter(Contract.user_id == user.id, Contract.analysis_completed == True)
    if q:
        query = query.filter(Contract.filename.ilike(f"%{q}%"))
    if risk in ("high", "medium", "low"):
        query = query.filter(Contract.overall_risk == risk)

    if risk == "attention":
        # Cannot be expressed as a SQL WHERE (EncryptedJSON content is not
        # filterable at the DB layer -- see _document_state_for_contract
        # module note). Fetch this user's matching rows and filter/paginate
        # in Python instead of the DB-level offset/limit used by every
        # other filter value.
        all_matching = query.order_by(Contract.created_at.desc()).all()
        attention_matching = [c for c in all_matching if _needs_attention(c)]
        total = len(attention_matching)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        contracts = attention_matching[(page - 1) * per_page: page * per_page]
    else:
        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        contracts = query.order_by(Contract.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    document_states = {c.id: _document_state_for_contract(c) for c in contracts}

    return templates.TemplateResponse("history.html", {
        "request": request, "user": user, "contracts": contracts,
        "q": q, "active_filter": risk or "all", "page": page, "total_pages": total_pages,
        "document_states": document_states, "current_year": datetime.now().year,
    })


# ============================================================
# SINGLE CONTRACT UPLOAD (real accounts and one-click guest trials)
# ============================================================

def _create_guest_user(db: DBSession, request: Request, name: str = "Guest") -> User:
    """A throwaway, no-password account for a visitor who hasn't created a
    real one — same mechanism whether they got here via the demo or via
    "Start Free Review" with their own contract. A recognizable
    @guest.triagecounsel.local address and free-tier limits (3
    contracts/month, same as a real free account) so every downstream
    route (ownership checks, ordinary usage limits, redline actions, PDF
    export, share links) works completely unmodified — the guest IS a
    real account, just one nobody had to fill out a form to create.
    """
    guest_email = f"demo-{secrets.token_hex(8)}@guest.triagecounsel.local"
    user = User(
        email=guest_email, password_hash=None, name=name,
        plan="free", monthly_limit=3,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    rbac.grant_role(db, user, "user")
    analytics.record_event(request, "guest_account_created", user=user)
    return user


@app.get("/upload-page", response_class=HTMLResponse)
async def upload_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).all() if user else []
    return templates.TemplateResponse("upload.html", {
        "request": request, "current_year": datetime.now().year,
        "dev_mode": DEV_MODE, "user": user, "playbooks": playbooks,
    })


@app.post("/upload")
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    playbook_id: Optional[int] = Form(None),
    business_unit: Optional[str] = Form(None),
    customer_type: Optional[str] = Form(None),
    deal_value: Optional[float] = Form(None),
    db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("upload", limit=30, window_seconds=3600)),
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request, db)

    def upload_error(message: str, status_code: int = 400):
        """Render the upload page with an inline error instead of a raw JSON
        response, so a browser form post never dead-ends on an error page."""
        accepts_html = "text/html" in (request.headers.get("accept") or "")
        if not accepts_html:
            raise HTTPException(status_code=status_code, detail=message)
        playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).all() if user else []
        return templates.TemplateResponse("upload.html", {
            "request": request, "error": message, "user": user,
            "playbooks": playbooks, "current_year": datetime.now().year,
            "dev_mode": DEV_MODE,
        }, status_code=status_code)

    if not file.filename:
        return upload_error("No file selected. Choose a PDF, DOCX, or TXT contract to analyze.")
    filename = upload_security.sanitize_filename(file.filename)
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        return upload_error(f"“{filename}” isn’t a supported format. Upload a PDF, DOCX, or TXT file.")

    file_bytes = await file.read()
    if not file_bytes:
        return upload_error("That file appears to be empty. Choose a different file and try again.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return upload_error("That file is larger than the 10MB limit. Try compressing it or splitting the document.")

    try:
        contract_text = extract_text_from_file(file_bytes, filename)
        if not contract_text or not contract_text.strip():
            return upload_error("We couldn’t find any text in that document. If it’s a scanned PDF, run OCR first and re-upload.")
    except HTTPException:
        raise
    except upload_security.UploadRejected as e:
        return upload_error(str(e))
    except Exception:
        return upload_error("We couldn’t read that document. Make sure it opens correctly, then try again.")

    # A visitor without an account yet gets a throwaway guest account here —
    # the same mechanism /demo/start uses — instead of being sent to a
    # signup form before they've seen any value. Created only now, after
    # the file has actually validated, so a bad/empty upload attempt never
    # burns an account on its own. From this point on a guest is handled
    # identically to a real logged-in user for the rest of this function.
    new_guest = user is None
    if new_guest:
        user = _create_guest_user(db, request)

    if not check_usage_limit(user):
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "error": "You’ve used all of this month’s reviews on your current plan.",
            "error_upgrade": True,
            "user": user,
            "playbooks": db.query(Playbook).filter(Playbook.user_id == user.id).all() if user else [],
            "current_year": datetime.now().year,
            "dev_mode": DEV_MODE,
        })

    analytics.record_event(request, "upload_started", user=user, metadata={"filename": filename})

    started_at = time.perf_counter()
    analytics.record_event(request, "analysis_started", user=user, metadata={"filename": filename})
    analysis = run_analysis(contract_text)
    analytics.record_event(request, "analysis_completed", user=user, metadata={
        "filename": filename, "overall_risk": analysis.get("overall_risk"),
    })
    processing_time = time.perf_counter() - started_at

    # Playbook comparison
    deviations = None
    playbook = None
    if playbook_id:
        playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
        if playbook and playbook.template_findings_json:
            comparison = playbook_engine.compare(analysis["findings_dict"], playbook.template_findings_json)
            deviations = comparison

    # Policy enforcement (Phase 4) — mutates analysis["findings_dict"] in
    # place (appends synthetic policy findings), so it must run before
    # Contract is constructed below (findings_json is set from that same
    # list at construction time; mutating it afterward without a
    # reassignment wouldn't reliably mark the encrypted JSON column dirty).
    # contract_id is not yet known at this point (no row exists yet) —
    # shadow-mode AuditLog entries from this call carry target_id=None,
    # which is fine since target_type="contract" combined with playbook_id
    # in the log payload is enough to trace it.
    # Segment context (deal size / business unit / customer type) — optional
    # reviewer input used only to select among segmented ACTIVE
    # PolicyPositions when the playbook has more than one for a clause
    # type (see policy_enforcement.resolve_segment_position). None of
    # these being set (the common case today) reproduces pre-segmentation
    # behavior exactly.
    business_unit = (business_unit or "").strip() or None
    customer_type = (customer_type or "").strip() or None
    review_context = {"business_unit": business_unit, "customer_type": customer_type, "deal_value": deal_value}

    policy_result = policy_enforcement.apply_policies_for_review(
        db, playbook, contract_text, analysis["findings_dict"], context=review_context,
    )

    contract = Contract(
        user_id=user.id,
        filename=filename,
        contract_text=contract_text,
        overall_risk=analysis["overall_risk"],
        findings_json=analysis["findings_dict"],
        llm_result_json=analysis["llm_result"],
        rule_counts_json=analysis["rule_counts"],
        rule_engine_version=analysis["version"],
        analysis_completed=True,
        playbook_id=playbook_id,
        deviations_json=deviations,
        review_business_unit=business_unit,
        review_customer_type=customer_type,
        review_deal_value=deal_value,
        policy_decisions_json=policy_result["policy_decisions"],
        policy_revision_metadata_json=policy_result["policy_revision_metadata"],
        interaction_decisions_json=policy_result.get("interaction_decisions"),
        signature_readiness=analysis.get("signature_readiness"),
        payment_terms_json=analysis.get("payment_terms"),
        blocking_findings_json=analysis.get("blocking_findings"),
        policy_blocked_findings_json=analysis.get("policy_blocked_findings"),
        legal_risk_score=analysis.get("risk_dashboard", {}).get("legal_risk_score"),
        business_risk_score=analysis.get("risk_dashboard", {}).get("business_risk_score"),
        negotiation_difficulty_score=analysis.get("risk_dashboard", {}).get("negotiation_difficulty_score"),
        risk_dashboard_json=analysis.get("risk_dashboard"),
        structure_report_json=analysis.get("structure_report"),
        clause_quality_json=analysis.get("clause_quality"),
        metadata_json=analysis.get("metadata"),
        risk_balance_json=analysis.get("risk_balance"),
    )
    db.add(contract)
    db.flush()  # assigns contract.id without ending the transaction

    contract_event = analytics.build_contract_event(
        request, contract_id=contract.id, user_id=user.id,
        filename=filename, file_bytes=file_bytes,
        status="completed", processing_time=processing_time,
    )
    db.add(contract_event)

    user.contracts_this_month += 1
    db.commit()
    db.refresh(contract)

    analytics.record_event(request, "upload_completed", user=user, metadata={
        "contract_id": contract.id, "filename": filename, "overall_risk": contract.overall_risk,
    })
    audit_log.record_event(
        db, "contract_uploaded", request=request, actor_user_id=user.id,
        target_type="contract", target_id=contract.id, success=True,
        metadata={"filename": filename, "overall_risk": contract.overall_risk},
    )

    response = RedirectResponse(url=f"/contract/{contract.id}/review", status_code=303)
    if new_guest:
        create_session(user.id, response)
    return response


# ============================================================
# BATCH UPLOAD
# ============================================================

@app.get("/batch-upload", response_class=HTMLResponse)
async def batch_upload_page(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).all()
    return templates.TemplateResponse("batch_upload.html", {
        "request": request, "user": user, "playbooks": playbooks,
        "current_year": datetime.now().year,
    })


@app.post("/batch-upload")
async def batch_upload_submit(
    request: Request,
    files: List[UploadFile] = File(...),
    playbook_id: Optional[int] = Form(None),
    db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("batch-upload", limit=10, window_seconds=3600)),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)

    def batch_error(message: str, status_code: int = 400):
        """Inline error on the batch page instead of a raw JSON dead end."""
        if "text/html" not in (request.headers.get("accept") or ""):
            raise HTTPException(status_code=status_code, detail=message)
        playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).all()
        return templates.TemplateResponse("batch_upload.html", {
            "request": request, "user": user, "playbooks": playbooks,
            "error": message, "current_year": datetime.now().year,
        }, status_code=status_code)

    plan = PLAN_LIMITS.get(user.plan, {"monthly_limit": 0, "batch_max": 1, "playbooks_max": 0})
    if len(files) > plan["batch_max"]:
        return batch_error(f"Your plan supports up to {plan['batch_max']} files per batch. Remove some files or upgrade your plan.")

    remaining = user.monthly_limit - user.contracts_this_month
    if len(files) > remaining:
        return batch_error(f"You have {remaining} review{'s' if remaining != 1 else ''} left this month, but selected {len(files)} files. Remove some files or upgrade your plan.", 402)

    playbook = None
    template_findings = None
    if playbook_id:
        playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
        if playbook:
            template_findings = playbook.template_findings_json

    batch_id = secrets.token_urlsafe(16)
    contracts = []

    for f in files:
        if not f.filename:
            continue
        batch_filename = upload_security.sanitize_filename(f.filename)
        ext = os.path.splitext(batch_filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            continue

        file_bytes = await f.read()
        if not file_bytes or len(file_bytes) > MAX_UPLOAD_BYTES:
            continue

        try:
            text = extract_text_from_file(file_bytes, batch_filename)
            if not text or not text.strip():
                continue
        except Exception:
            continue

        analysis = run_analysis(text)

        deviations = None
        if template_findings:
            comparison = playbook_engine.compare(analysis["findings_dict"], template_findings)
            deviations = comparison

        policy_result = policy_enforcement.apply_policies_for_review(
            db, playbook, text, analysis["findings_dict"],
        )

        contract = Contract(
            user_id=user.id, filename=batch_filename, contract_text=text,
            overall_risk=analysis["overall_risk"], findings_json=analysis["findings_dict"],
            llm_result_json=analysis["llm_result"], rule_counts_json=analysis["rule_counts"],
            rule_engine_version=analysis["version"], analysis_completed=True,
            playbook_id=playbook_id, deviations_json=deviations,
            policy_decisions_json=policy_result["policy_decisions"],
            policy_revision_metadata_json=policy_result["policy_revision_metadata"],
            interaction_decisions_json=policy_result.get("interaction_decisions"),
            batch_id=batch_id,
            signature_readiness=analysis.get("signature_readiness"),
            payment_terms_json=analysis.get("payment_terms"),
            blocking_findings_json=analysis.get("blocking_findings"),
            policy_blocked_findings_json=analysis.get("policy_blocked_findings"),
            legal_risk_score=analysis.get("risk_dashboard", {}).get("legal_risk_score"),
            business_risk_score=analysis.get("risk_dashboard", {}).get("business_risk_score"),
            negotiation_difficulty_score=analysis.get("risk_dashboard", {}).get("negotiation_difficulty_score"),
            risk_dashboard_json=analysis.get("risk_dashboard"),
            structure_report_json=analysis.get("structure_report"),
            clause_quality_json=analysis.get("clause_quality"),
            metadata_json=analysis.get("metadata"),
            risk_balance_json=analysis.get("risk_balance"),
        )
        db.add(contract)
        contracts.append(contract)

    user.contracts_this_month += len(contracts)
    db.commit()

    # Post/Redirect/Get: a refresh on the results page must not re-run the
    # batch (it would re-analyze every file and consume quota again).
    return RedirectResponse(url=f"/batch/{batch_id}", status_code=303)


@app.get("/batch/{batch_id}", response_class=HTMLResponse)
async def batch_results_page(request: Request, batch_id: str, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    contracts = db.query(Contract).filter(
        Contract.batch_id == batch_id, Contract.user_id == user.id
    ).all()
    if not contracts:
        raise HTTPException(status_code=404, detail="Batch not found")

    playbook = None
    if contracts[0].playbook_id:
        playbook = db.query(Playbook).filter(
            Playbook.id == contracts[0].playbook_id, Playbook.user_id == user.id
        ).first()

    batch_stats = {"total": len(contracts), "high": 0, "medium": 0, "low": 0}
    for c in contracts:
        if c.overall_risk == "high":
            batch_stats["high"] += 1
        elif c.overall_risk == "medium":
            batch_stats["medium"] += 1
        else:
            batch_stats["low"] += 1

    return templates.TemplateResponse("batch_results.html", {
        "request": request, "user": user, "contracts": contracts,
        "batch_id": batch_id, "playbook_name": playbook.name if playbook else None,
        "stats": batch_stats, "current_year": datetime.now().year,
    })


@app.get("/batch/{batch_id}/download-all")
async def download_batch_pdfs(request: Request, batch_id: str, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    contracts = db.query(Contract).filter(Contract.batch_id == batch_id, Contract.user_id == user.id).all()
    if not contracts:
        raise HTTPException(status_code=404, detail="Batch not found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for contract in contracts:
            findings_dict = contract.findings_json or []
            llm_result = contract.llm_result_json or {}
            all_issues = build_enhanced_issues(findings_dict, llm_result)
            rule_counts = display_rule_stats(all_issues)
            pdf_bytes = _build_pdf_bytes(
                contract.filename, contract.overall_risk, rule_counts,
                contract.rule_engine_version, llm_result.get("summary_bullets", []), all_issues,
                metadata=contract.metadata_json,
                legal_risk_score=contract.legal_risk_score,
                business_risk_score=contract.business_risk_score,
                negotiation_difficulty_score=contract.negotiation_difficulty_score,
                risk_balance=contract.risk_balance_json,
                structure_report=contract.structure_report_json,
                clause_quality=contract.clause_quality_json,
            )
            safe_name = sanitize_filename(contract.filename)
            zf.writestr(f"TriageAI_{safe_name}_{contract.id}.pdf", pdf_bytes)

    return Response(
        content=zip_buffer.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="TriageAI_batch_{batch_id}.zip"'},
    )


RULE_CATEGORY_MAP = {
    "INDEM": "Indemnification", "LOL": "Liability", "IP": "Intellectual Property",
    "PERSONAL": "Personal Liability", "ATTFEE": "Attorneys Fees", "ASSIGN": "Assignment",
    "PUBLICITY": "Publicity", "UNILATERAL": "Unilateral Modification",
    "CONSEQUENTIAL": "Consequential Damages", "TERM": "Termination", "DATA": "Data Portability",
    "ASYMMETRIC": "Asymmetric Liability", "CONF": "Confidentiality", "RENEW": "Auto-Renewal",
    "NONCOMP": "Non-Compete", "DEV": "Development Restrictions", "RESIDUALS": "Residual Rights",
    "INJUNCT": "Injunctive Relief", "EQUIT": "Equitable Relief", "AUDIT": "Audit Rights",
    "SURVIVAL": "Survival", "WAIVER": "Waiver of Defenses", "ARBITRATION": "Arbitration",
    "WARRANTY": "Warranty", "BREACH": "Breach Notification", "INSURANCE": "Insurance",
    "FORCE": "Force Majeure", "SLA": "Service Levels", "MFN": "Most Favored Nation",
    "LATEFEE": "Late Fees", "BROADDEF": "Definitions", "GOVLAW": "Governing Law",
    "COMPLIANCE": "Compliance", "ESCROW": "Escrow", "SUBCONTRACT": "Subcontracting",
    "LOL_CARVEOUT": "Liability Carveouts", "IP_WORK_PRODUCT": "Work Product IP",
    "INDEM_ONEWAY": "One-Way Indemnification", "TERM_CONVENIENCE": "Termination for Convenience",
    "DATA_TERMINATION": "Data on Termination", "ASYMMETRIC_LIABILITY": "Asymmetric Liability",
    "CONF_SCOPE": "Confidentiality Scope", "TERM_NOTICE": "Termination Notice",
    "SURVIVAL_SCOPE": "Survival Scope", "WAIVER_DEFENSE": "Waiver of Defenses",
    "WARRANTY_DISCLAIM": "Warranty Disclaimer", "BREACH_NOTIFY": "Breach Notification",
    "FORCE_MAJEURE": "Force Majeure", "ASSIGN_CHANGE_CTRL": "Assignment / Change of Control",
    "UNILATERAL_MOD": "Unilateral Modification",
    # v2.1 additions
    "AI_TRAINING": "AI / Model Training",
    "PRICE_ESCAL": "Price Escalation",
    "DATA_PRIVACY": "Data Privacy",
    "DATA_PORTABILITY": "Data Portability",
    "DATA_DELETION": "Data Deletion",
    "BENCHMARKING": "Benchmarking",
    "MIN_COMMIT": "Minimum Commitment",
    "CROSS_BORDER": "Cross-Border Transfers",
    "USE_RESTRICT": "Use Restrictions",
    "RENEWAL_PRICE": "Renewal Pricing",
    "PAYMENT_TERMS": "Payment Terms",
    "EXPORT_CTRL": "Export Controls",
}

def _get_rule_category(rule_id: str) -> str:
    prefix = rule_id.split("_", 1)[1].rsplit("_", 1)[0] if "_" in rule_id else rule_id
    return RULE_CATEGORY_MAP.get(prefix, prefix.replace("_", " ").title())

def _build_rule_categories(findings_dict, engine):
    all_categories = {}
    for rule in engine.rules:
        cat = _get_rule_category(rule.rule_id)
        if cat not in all_categories:
            all_categories[cat] = "PASS"
    triggered_ids = {f.get("rule_id", "") for f in findings_dict}
    for f in findings_dict:
        cat = _get_rule_category(f.get("rule_id", ""))
        sev = f.get("severity", "low")
        if sev in ("critical", "high"):
            all_categories[cat] = "FAIL"
        elif sev == "medium" and all_categories.get(cat) != "FAIL":
            all_categories[cat] = "WARNING"
    return dict(sorted(all_categories.items()))


# ============================================================
# VIEW SINGLE CONTRACT
# ============================================================

@app.get("/contract/{contract_id}", response_class=HTMLResponse)
async def view_contract(request: Request, contract_id: int, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    findings_dict = contract.findings_json or []
    llm_result = contract.llm_result_json or {}
    all_issues = build_enhanced_issues(findings_dict, llm_result)
    rule_counts = display_rule_stats(all_issues)

    rule_based_sections = rule_engine.build_missing_sections(
        [type('F', (), {"rule_id": f["rule_id"]})() for f in findings_dict]
    )
    llm_sections = llm_result.get("possible_missing_sections", [])
    all_missing = rule_based_sections.copy()
    for s in llm_sections:
        if not any(s.lower() in e.lower() or e.lower() in s.lower() for e in all_missing):
            all_missing.append(s)
    all_missing = all_missing[:6]

    import json as _json
    version_path = Path(__file__).parent / "rules" / "version.json"
    try:
        ruleset_meta = _json.loads(version_path.read_text())
    except Exception:
        ruleset_meta = {}
    total_rule_count = sum(ruleset_meta.get("rule_count", {}).values()) if ruleset_meta.get("rule_count") else len(rule_engine.rules)

    rule_categories = _build_rule_categories(findings_dict, rule_engine)

    return templates.TemplateResponse("results.html", {
        "request": request, "user": user,
        "filename": contract.filename,
        "overall_risk": contract.overall_risk,
        "summary_bullets": llm_result.get("summary_bullets", []),
        "top_issues": all_issues,
        "possible_missing_sections": all_missing,
        "disclaimer": llm_result.get("disclaimer", "This is automated risk triage, not legal advice."),
        "findings_count": len(all_issues),
        "rule_counts": rule_counts,
        "rule_engine_version": contract.rule_engine_version or "2.0.0",
        "current_year": datetime.now().year,
        "token": None,
        "contract_id": contract.id,
        "deviations": contract.deviations_json,
        "explanation_source": llm_result.get("explanation_source"),
        "total_rule_count": total_rule_count,
        "rule_categories": rule_categories,
        "findings_dict": findings_dict,
        "analysis_id": f"TR-{contract.created_at.year}-{contract.id:06d}" if contract.created_at else f"TR-2026-{contract.id:06d}",
        "generated_at": contract.created_at.strftime("%Y-%m-%d %I:%M %p UTC") if contract.created_at else "N/A",
        # Workflow decision layer + structured payment terms. May be None for
        # contracts analyzed before this field was persisted.
        "signature_readiness": contract.signature_readiness,
        "payment_terms": contract.payment_terms_json,
        "blocking_findings": contract.blocking_findings_json or [],
        "policy_blocked_findings": contract.policy_blocked_findings_json or [],
        # Three-score risk dashboard. May be None for contracts analyzed
        # before this field was persisted.
        "legal_risk_score": contract.legal_risk_score,
        "business_risk_score": contract.business_risk_score,
        "negotiation_difficulty_score": contract.negotiation_difficulty_score,
        "risk_dashboard": contract.risk_dashboard_json,
        "structure_report": contract.structure_report_json,
        "clause_quality": contract.clause_quality_json,
        "metadata": contract.metadata_json,
        "risk_balance": contract.risk_balance_json,
        "progress": compute_progress(contract.findings_json or [], contract.review_decisions_json or {}).as_dict(),
    })


# ============================================================
# PDF DOWNLOAD (authenticated)
# ============================================================

def _truncate_excerpt_for_display(excerpt: str, max_len: int = 300) -> str:
    """
    Truncate an evidence excerpt for PDF display without cutting mid-word
    and without silently hiding that truncation happened.

    The previous behavior (`excerpt[:300]`) cut at an arbitrary character
    boundary with no indicator — verified on a real report, this cut off
    before reaching the actual clause language a finding cited as its
    evidence, with no way for the reader to know text was missing. This
    truncates at the nearest whitespace boundary at or before max_len (so
    it never splits a word) and appends how many characters were omitted.
    """
    if len(excerpt) <= max_len:
        return excerpt
    cut = excerpt.rfind(" ", 0, max_len)
    if cut == -1 or cut < max_len * 0.6:
        cut = max_len
    omitted = len(excerpt) - cut
    return f"{excerpt[:cut].rstrip()} ... [{omitted} more characters omitted]"


_PDF_CHAR_TRANSLATIONS = str.maketrans({
    "‘": "'", "’": "'",   # curly single quotes
    "“": '"', "”": '"',   # curly double quotes
    "–": "-", "—": "-",   # en dash, em dash
    "…": "...",                # ellipsis
    "•": "-",                  # bullet
    "\xa0": " ",                    # non-breaking space
})


def _pdf_safe(text: str) -> str:
    """
    Make text safe for the core Helvetica PDF font (latin-1 only), which
    raises FPDFUnicodeEncodingException (a 500) on rule titles/rationale/LLM
    output containing curly quotes, em/en dashes, ellipses, etc. Common
    punctuation is transliterated to a plain-ASCII equivalent so the report
    stays readable; anything else falls back to being dropped.
    """
    translated = text.translate(_PDF_CHAR_TRANSLATIONS)
    return translated.encode("latin-1", "replace").decode("latin-1")


_CLAUSE_QUALITY_MODULE_LABELS = {
    "arbitration": "Arbitration Clause Inspector",
    "liability": "Liability Clause Inspector",
    "confidentiality": "Confidentiality Clause Inspector",
    "indemnification": "Indemnification Clause Inspector",
    "termination": "Termination Clause Inspector",
    "ip": "Intellectual Property Clause Inspector",
}


def _pdf_section_heading(pdf: "FPDF", text: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)


def _build_pdf_bytes(filename: str, overall_risk: str, rule_counts: dict, rule_engine_version: str,
                      summary_bullets: list, all_issues: list, *,
                      metadata: Optional[dict] = None,
                      legal_risk_score: Optional[int] = None,
                      business_risk_score: Optional[int] = None,
                      negotiation_difficulty_score: Optional[int] = None,
                      risk_balance: Optional[dict] = None,
                      structure_report: Optional[dict] = None,
                      clause_quality: Optional[dict] = None) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Triage Counsel - Contract Risk Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"File: {_pdf_safe(filename)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Date: {datetime.utcnow().strftime('%B %d, %Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Rule Engine: v{rule_engine_version or '2.0.0'}", new_x="LMARGIN", new_y="NEXT")

    if metadata:
        if metadata.get("contract_type"):
            pdf.cell(0, 6, f"Contract Type: {_pdf_safe(metadata['contract_type'])}", new_x="LMARGIN", new_y="NEXT")
        if metadata.get("effective_date"):
            pdf.cell(0, 6, f"Effective Date: {_pdf_safe(metadata['effective_date'])}", new_x="LMARGIN", new_y="NEXT")
        parties = metadata.get("parties") or []
        if parties:
            names = ", ".join(_pdf_safe(p.get("full_name") or p.get("short_name") or "") for p in parties if p.get("full_name") or p.get("short_name"))
            if names:
                pdf.cell(0, 6, f"Parties: {names}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    risk_label = (overall_risk or "low").upper()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Overall Risk: {risk_label}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"High: {rule_counts.get('high', 0)}  |  Medium: {rule_counts.get('medium', 0)}  |  Low: {rule_counts.get('low', 0)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if legal_risk_score is not None and business_risk_score is not None and negotiation_difficulty_score is not None:
        _pdf_section_heading(pdf, "Risk Dashboard (three independent readings, not a blended score)")
        pdf.cell(0, 6, f"Legal Risk: {legal_risk_score}/100  |  Business Risk: {business_risk_score}/100  |  Negotiation Difficulty: {negotiation_difficulty_score}/100", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    if risk_balance and risk_balance.get("applicable"):
        _pdf_section_heading(pdf, "Risk Allocation Balance")
        pdf.multi_cell(
            0, 5,
            f"{risk_balance.get('balance_score', 0)}/100 - of the one-sided clauses this engine could classify, "
            f"{risk_balance.get('balance_score', 0)}% favor the counterparty rather than the reviewing party "
            f"({risk_balance.get('unfavorable_count', 0)} unfavorable vs. {risk_balance.get('favorable_count', 0)} favorable).",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(4)

    if structure_report and structure_report.get("total_issue_count"):
        _pdf_section_heading(pdf, f"Document Structure Check ({structure_report['total_issue_count']} issue(s))")
        for i in structure_report.get("used_but_undefined", []):
            pdf.multi_cell(0, 5, f"  - Used but undefined: {_pdf_safe(i.get('term', ''))} - {_pdf_safe(i.get('detail', ''))}", new_x="LMARGIN", new_y="NEXT")
        for i in structure_report.get("duplicate_definitions", []):
            pdf.multi_cell(0, 5, f"  - Duplicate definition: {_pdf_safe(i.get('term', ''))} - {_pdf_safe(i.get('detail', ''))}", new_x="LMARGIN", new_y="NEXT")
        for r in structure_report.get("broken_cross_references", []):
            pdf.multi_cell(0, 5, f"  - Broken cross-reference: {_pdf_safe(r.get('reference_text', ''))}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    if clause_quality:
        for key, label in _CLAUSE_QUALITY_MODULE_LABELS.items():
            module = clause_quality.get(key)
            if not module or not module.get("applicable"):
                continue
            _pdf_section_heading(pdf, f"{label} ({module.get('score', 0)}/100)")
            for el in module.get("elements", []):
                mark = "[x]" if el.get("present") else "[ ]"
                pdf.set_font("Helvetica", "B" if not el.get("present") else "", 9)
                pdf.multi_cell(0, 5, f"  {mark} {_pdf_safe(el.get('label', ''))}", new_x="LMARGIN", new_y="NEXT")
                if el.get("detail"):
                    pdf.set_font("Helvetica", "", 8)
                    pdf.multi_cell(0, 4, f"      {_pdf_safe(el['detail'])}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.ln(3)

    if summary_bullets:
        _pdf_section_heading(pdf, "Executive Summary")
        for bullet in summary_bullets:
            pdf.multi_cell(0, 5, f"  - {_pdf_safe(bullet)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    if all_issues:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Findings", new_x="LMARGIN", new_y="NEXT")
        for i, issue in enumerate(all_issues, 1):
            severity = issue.get("severity", "medium").upper()
            title = _pdf_safe(issue.get("title", "Finding"))
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 6, f"{i}. [{severity}] {title}", new_x="LMARGIN", new_y="NEXT")
            rationale = issue.get("rationale", "")
            if rationale:
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, f"   {_pdf_safe(rationale)}", new_x="LMARGIN", new_y="NEXT")
            excerpt = issue.get("matched_excerpt", "")
            if excerpt:
                pdf.set_font("Helvetica", "I", 8)
                displayed_excerpt = _truncate_excerpt_for_display(excerpt)
                clean_excerpt = _pdf_safe(displayed_excerpt)
                pdf.multi_cell(0, 4, f'   "{clean_excerpt}"', new_x="LMARGIN", new_y="NEXT")

            confidence_breakdown = issue.get("confidence_breakdown")
            if confidence_breakdown:
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(0, 5, f"   Confidence: {str(confidence_breakdown.get('confidence', '')).upper()}", new_x="LMARGIN", new_y="NEXT")
                if confidence_breakdown.get("reason"):
                    pdf.set_font("Helvetica", "", 8)
                    pdf.multi_cell(0, 4, f"   {_pdf_safe(confidence_breakdown['reason'])}", new_x="LMARGIN", new_y="NEXT")

            redline = issue.get("redline")
            if redline:
                pdf.ln(1)
                pdf.set_font("Helvetica", "B", 9)
                pdf.multi_cell(
                    0, 5,
                    f"   DETERMINISTIC REDLINE - {_pdf_safe(redline.get('issue', ''))} "
                    f"({redline.get('negotiation_difficulty', '')} friction, {redline.get('confidence', '')} confidence)",
                    new_x="LMARGIN", new_y="NEXT",
                )
                redline_fields = [
                    ("Problem", "problem"),
                    ("Legal Rationale", "legal_rationale"),
                    ("Business Impact", "business_impact"),
                    ("Recommended Change", "recommended_change"),
                    ("Suggested Redline", "suggested_redline"),
                    ("Why This Wording", "why_this_wording"),
                    ("Expected Counterparty Position", "expected_counterparty_position"),
                    ("Fallback Position", "fallback_position"),
                ]
                for field_label, field_key in redline_fields:
                    value = redline.get(field_key)
                    if not value:
                        continue
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.multi_cell(0, 4, f"   {field_label}:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "", 8)
                    pdf.multi_cell(0, 4, f"   {_pdf_safe(value)}", new_x="LMARGIN", new_y="NEXT")
                rules = redline.get("supporting_deterministic_rules") or []
                if rules:
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.multi_cell(0, 4, f"   Supporting Deterministic Rule(s): {', '.join(rules)}", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font("Helvetica", "", 10)
            pdf.ln(2)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, f"(c) {datetime.now().year} Triage Counsel - Contract Risk Intelligence. Not legal advice.", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


@app.get("/contract/{contract_id}/pdf")
async def download_contract_pdf(request: Request, contract_id: int, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    findings_dict = contract.findings_json or []
    llm_result = contract.llm_result_json or {}
    all_issues = build_enhanced_issues(findings_dict, llm_result)
    rule_counts = display_rule_stats(all_issues)

    pdf_bytes = _build_pdf_bytes(
        contract.filename, contract.overall_risk, rule_counts,
        contract.rule_engine_version, llm_result.get("summary_bullets", []), all_issues,
        metadata=contract.metadata_json,
        legal_risk_score=contract.legal_risk_score,
        business_risk_score=contract.business_risk_score,
        negotiation_difficulty_score=contract.negotiation_difficulty_score,
        risk_balance=contract.risk_balance_json,
        structure_report=contract.structure_report_json,
        clause_quality=contract.clause_quality_json,
    )

    safe_name = sanitize_filename(contract.filename)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    analytics.record_event(request, "download_pdf", user=user, metadata={"contract_id": contract.id})
    audit_log.record_event(
        db, "contract_exported", request=request, actor_user_id=user.id,
        target_type="contract", target_id=contract.id, success=True, detail="pdf",
    )

    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="TriageAI_{safe_name}_{date_str}.pdf"'},
    )


@app.get("/download-pdf")
async def download_pdf_token(request: Request, token: str):
    """PDF export for anonymous, token-based sessions (legacy pay-per-use flow)."""
    try:
        session_id, sig = token.rsplit(":", 1)
        expected = hmac.new(APP_HMAC_SECRET.encode(), session_id.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=400, detail="Invalid token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token")

    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session expired")

    entry = session_store[session_id]
    if not entry.get("paid") and not DEV_MODE:
        raise HTTPException(status_code=402, detail="Payment required")

    filename = entry.get("filename", "document")
    analysis = run_analysis(entry.get("text", ""))
    all_issues = build_enhanced_issues(analysis["findings_dict"], analysis["llm_result"])

    risk_dashboard = analysis.get("risk_dashboard") or {}
    pdf_bytes = _build_pdf_bytes(
        filename, analysis["overall_risk"], analysis["rule_counts"],
        analysis["version"], analysis["llm_result"].get("summary_bullets", []), all_issues,
        metadata=analysis.get("metadata"),
        legal_risk_score=risk_dashboard.get("legal_risk_score"),
        business_risk_score=risk_dashboard.get("business_risk_score"),
        negotiation_difficulty_score=risk_dashboard.get("negotiation_difficulty_score"),
        risk_balance=analysis.get("risk_balance"),
        structure_report=analysis.get("structure_report"),
        clause_quality=analysis.get("clause_quality"),
    )

    safe_name = sanitize_filename(filename)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="TriageAI_{safe_name}_{date_str}.pdf"'},
    )


# ============================================================
# REPORT SHARING
# ============================================================

SHARE_MAX_EXPIRY_DAYS = 365
SHARE_MAX_VIEWS_LIMIT = 100_000


def _parse_positive_int_form_field(raw: str, field_name: str, max_value: int) -> Optional[int]:
    """Blank/whitespace-only means "no limit" (None). A present value must
    be a positive integer within a sane bound — otherwise a typo like
    "999999999999" could effectively disable the limit anyway."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} must be a whole number")
    if value < 1 or value > max_value:
        raise HTTPException(status_code=400, detail=f"{field_name} must be between 1 and {max_value}")
    return value


@app.post("/contract/{contract_id}/share")
async def create_share_link(
    request: Request, contract_id: int,
    password: str = Form(""),
    expires_in_days: str = Form(""),
    max_views: str = Form(""),
    db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    expires_days = _parse_positive_int_form_field(expires_in_days, "expires_in_days", SHARE_MAX_EXPIRY_DAYS)
    views_limit = _parse_positive_int_form_field(max_views, "max_views", SHARE_MAX_VIEWS_LIMIT)

    is_new_link = not contract.share_token
    if is_new_link:
        contract.generate_share_token()
    if password:
        contract.share_password_hash = hash_password(password)
    contract.share_expires_at = (datetime.utcnow() + timedelta(days=expires_days)) if expires_days else None
    contract.share_max_views = views_limit
    # (Re)sharing un-revokes a previously revoked link and starts the view
    # count fresh under the new settings — an explicit, visible action the
    # owner took, not something that happens silently on its own.
    contract.share_revoked_at = None
    contract.share_view_count = 0
    db.commit()

    analytics.record_event(request, "share_report", user=user, metadata={"contract_id": contract.id})
    audit_log.record_event(
        db, "share_link_created" if is_new_link else "share_link_updated",
        request=request, actor_user_id=user.id, target_type="contract", target_id=contract.id,
        success=True,
        metadata={
            "has_password": bool(contract.share_password_hash),
            "expires_in_days": expires_days,
            "max_views": views_limit,
        },
    )

    share_url = f"{get_base_url(request)}/shared/{contract.share_token}"
    return {
        "share_url": share_url,
        "token": contract.share_token,
        "expires_at": contract.share_expires_at.isoformat() if contract.share_expires_at else None,
        "max_views": contract.share_max_views,
    }


@app.post("/contract/{contract_id}/share/revoke")
async def revoke_share_link(
    request: Request, contract_id: int, db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if not contract.share_token:
        raise HTTPException(status_code=400, detail="This contract has no share link to revoke")

    contract.share_revoked_at = datetime.utcnow()
    db.commit()

    audit_log.record_event(
        db, "share_link_revoked", request=request, actor_user_id=user.id,
        target_type="contract", target_id=contract.id, success=True,
    )
    return {"revoked": True}


@app.get("/contract/{contract_id}/share/status")
async def share_link_status(request: Request, contract_id: int, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if not contract.share_token:
        return {"has_link": False}

    return {
        "has_link": True,
        "share_url": f"{get_base_url(request)}/shared/{contract.share_token}",
        "has_password": bool(contract.share_password_hash),
        "expires_at": contract.share_expires_at.isoformat() if contract.share_expires_at else None,
        "max_views": contract.share_max_views,
        "view_count": contract.share_view_count,
        "revoked": contract.share_revoked_at is not None,
    }


# ============================================================
# REVIEW WORKFLOW — the merged findings+redlines review pass.
# See review_workflow.py (decision logic) and docx_export.py (the
# Negotiation Package's redlined .docx). One decision per finding, in-
# document, with a real re-run of the deterministic engine backing the
# "Verify" action — not a canned animation.
# ============================================================

def _get_owned_contract(db: DBSession, user, contract_id: int) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@app.post("/contract/{contract_id}/delete")
async def delete_contract(
    request: Request, contract_id: int, db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    """Permanently deletes a single contract: extracted text, findings,
    every derived analysis field (LLM output, risk scores, structure/clause-
    quality/metadata reports, review decisions), and its share link/settings
    — the whole row. ContractEvent rows cascade-delete with it (see
    analytics_models.py's ondelete="CASCADE" + the ORM relationship's
    cascade="all, delete-orphan" on Contract.events). Exported PDFs/DOCX are
    generated on demand from this row and never written to disk (see
    docx_export.py / _build_pdf_bytes), so there is nothing else to clean up.
    The playbook this contract was compared against is a reusable template
    owned separately and is not affected."""
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)

    filename = contract.filename
    db.delete(contract)
    db.commit()

    audit_log.record_event(
        db, "contract_deleted", request=request, actor_user_id=user.id,
        target_type="contract", target_id=contract_id, success=True,
        metadata={"filename": filename},
    )
    return {"deleted": True}


@app.get("/contract/{contract_id}/review", response_class=HTMLResponse)
async def review_contract(request: Request, contract_id: int, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)

    import interaction_enforcement
    findings = interaction_enforcement.merge_interaction_staleness(
        contract.findings_json or [], contract.interaction_staleness_json,
    )
    decisions = contract.review_decisions_json or {}
    progress = compute_progress(findings, decisions)
    # Exception-queue view-model (P0 remediation of
    # docs/architecture/contract_review_exception_ux.md) — computed here,
    # server-side, so the passed-vs-actionable-vs-not-applicable-vs-
    # evaluation-error classification is unit-tested against real
    # PolicyDecision output (see review_queue.py and
    # tests/test_review_queue.py) rather than inferred client-side in
    # JavaScript from the mere absence of a finding.
    queue = review_queue.build_review_queue(findings, contract.policy_decisions_json)

    return templates.TemplateResponse("review.html", {
        "request": request, "user": user, "contract_id": contract.id,
        "filename": contract.filename, "overall_risk": contract.overall_risk,
        "rule_engine_version": contract.rule_engine_version or "2.0.0",
        "contract_text": contract.contract_text,
        "findings": findings, "decisions": decisions, "progress": progress.as_dict(),
        "clause_quality": contract.clause_quality_json,
        "legal_risk_score": contract.legal_risk_score,
        "business_risk_score": contract.business_risk_score,
        "negotiation_difficulty_score": contract.negotiation_difficulty_score,
        "metadata": contract.metadata_json,
        "policy_decisions": contract.policy_decisions_json,
        "queue": queue.as_dict(),
        "clause_labels": pa.CLAUSE_TYPE_LABELS,
        # Lifecycle "Active" != production authority — P0-2.
        "enforcement": policy_enforcement.enforcement_disclosure(),
        "is_finalized": contract.review_finalized_at is not None,
        "current_year": datetime.now().year,
    })


def _get_finding_by_index(contract: Contract, finding_index: int) -> Dict:
    findings = contract.findings_json or []
    if finding_index < 0 or finding_index >= len(findings):
        raise HTTPException(status_code=404, detail="Finding not found on this contract")
    return findings[finding_index]


@app.post("/contract/{contract_id}/review/decision")
async def submit_review_decision(
    request: Request, contract_id: int,
    finding_index: int = Form(...), action: str = Form(...),
    reason: str = Form(""), edited_text: str = Form(""),
    db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)

    findings = contract.findings_json or []
    finding = _get_finding_by_index(contract, finding_index)
    key = finding_key(finding_index, finding["rule_id"])

    try:
        # policy_state/finding_type are read from the STORED finding, never
        # from the request body — a client cannot downgrade a governance
        # finding to skip the reason requirement (P0-5).
        validate_decision(
            key, action, bool(finding.get("redline")), reason, edited_text,
            policy_state=finding.get("policy_state"), finding_type=finding.get("finding_type"),
        )
    except DecisionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    decisions = dict(contract.review_decisions_json or {})
    entry = {
        "action": action, "rule_id": finding["rule_id"], "decided_at": datetime.utcnow().isoformat(),
        "decided_by": user.name or user.email,
    }
    if finding.get("finding_type") == "policy_decision":
        # Policy overrides must never be silent: the finding already carries
        # the original deterministic recommendation (policy_state) in
        # findings_json, permanently, regardless of what's decided here —
        # this just records which decision it was overridden with and why.
        entry["policy_original_recommendation"] = finding.get("policy_state")
        # Pin the policy revision this decision was taken against, reusing
        # the revision metadata Phase 4 already records on the contract —
        # not a second, parallel revision store (P0-5).
        revision_meta = (contract.policy_revision_metadata_json or {}).get(finding.get("clause_type")) or {}
        if revision_meta.get("policy_position_id") is not None:
            entry["policy_position_id"] = revision_meta["policy_position_id"]
        if revision_meta.get("config_hash"):
            entry["policy_config_hash"] = revision_meta["config_hash"]
        if review_workflow.requires_policy_exception_reason(
            action, finding.get("policy_state"), finding.get("finding_type")
        ):
            entry["policy_exception"] = True
    if reason.strip():
        entry["reason"] = reason.strip()
    if action == "edited":
        entry["edited_text"] = edited_text.strip()
    # a decision replaces any prior decision on this finding, but a comment
    # left before the decision was made should survive the overwrite
    prior_comment = (contract.review_decisions_json or {}).get(key, {}).get("comment")
    if prior_comment:
        entry["comment"] = prior_comment
    decisions[key] = entry
    contract.review_decisions_json = decisions

    # Interaction Engine V1 — redline invalidation (design doc S5.2). An
    # edit or rejection of a policy_decision finding means the clause's
    # effective treatment may no longer match what any interaction
    # involving it was evaluated against; never silently recompute (the
    # edited text is free-form lawyer prose, not re-extracted anywhere)
    # — only flag every dependent interaction for reconfirmation. Every
    # OTHER interaction is untouched by construction (participating_
    # clause_types is the sole filter).
    if finding.get("finding_type") == "policy_decision" and action in ("edited", "rejected") and finding.get("clause_type"):
        import interaction_enforcement
        interaction_enforcement.mark_dependent_interactions_stale(
            contract, finding["clause_type"], pa.CLAUSE_TYPE_LABELS.get(finding["clause_type"], finding["clause_type"]),
        )

    db.commit()

    progress = compute_progress(findings, decisions)
    analytics.record_event(request, "review_decision", user=user, metadata={"contract_id": contract.id, "rule_id": finding["rule_id"], "finding_index": finding_index, "action": action})
    # `entry` (not just `progress`) is returned so the client can show the
    # authoritative record immediately — including decided_by and, for a
    # policy_decision finding, policy_original_recommendation — without
    # waiting for a page reload to see what the server actually stored
    # (Phase 4.1 UX remediation: override history must be visible right
    # away, not just after a refresh).
    return {"progress": progress.as_dict(), "entry": entry}


@app.post("/contract/{contract_id}/review/interaction/dismiss-stale")
async def dismiss_interaction_staleness(
    request: Request, contract_id: int, interaction_id: str = Form(...),
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    """The 'Dismiss' half of redline invalidation (design doc S5.2/S9.5):
    a lawyer has looked at a flagged interaction again and confirms its
    original evidence is still acceptable. Never recomputes the
    interaction — see interaction_enforcement.clear_interaction_staleness's
    docstring for why that would be dishonest given edited_text is never
    re-extracted."""
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)
    import interaction_enforcement
    cleared = interaction_enforcement.clear_interaction_staleness(contract, interaction_id)
    if cleared:
        db.commit()
    return {"cleared": cleared}


@app.post("/contract/{contract_id}/review/comment")
async def submit_review_comment(
    request: Request, contract_id: int, finding_index: int = Form(...), comment: str = Form(...),
    db: DBSession = Depends(get_db), _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)

    finding = _get_finding_by_index(contract, finding_index)
    key = finding_key(finding_index, finding["rule_id"])
    if not comment.strip():
        raise HTTPException(status_code=400, detail="comment cannot be empty")

    decisions = dict(contract.review_decisions_json or {})
    entry = dict(decisions.get(key, {}))
    entry["comment"] = comment.strip()
    decisions[key] = entry
    contract.review_decisions_json = decisions
    db.commit()

    return {"ok": True}


@app.post("/contract/{contract_id}/review/verify")
async def verify_review_finding(
    request: Request, contract_id: int, finding_index: int = Form(...), db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    """The Deterministic Replay 'aha' moment, done for real: re-runs the full
    rule engine against the stored contract text and confirms the same rule
    still fires against the same exact text — not a canned animation. Matches
    the replayed finding by rule_id AND exact position, not rule_id alone —
    the same rule can fire more than once in one document, and verifying
    finding #2 must not silently compare against finding #1's match.

    A policy_decision finding (from the deterministic policy engine, not
    the pattern rule engine) is a different verification question and is
    routed to policy_enforcement.verify_policy_finding instead — see that
    function's docstring for why the two are structurally distinct in
    what "verified" even means. This branch is what fixes the Phase 4.1
    UX audit's P0-2 finding: verifying a policy_decision finding through
    this rule-engine-only path always returned verified=False regardless
    of whether the policy actually changed, since policy engines' RULE_IDs
    (e.g. "POLICY_LOL_CAP") never appear in rule_engine.analyze()'s output."""
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)

    original = _get_finding_by_index(contract, finding_index)

    if original.get("finding_type") == "policy_decision":
        return policy_enforcement.verify_policy_finding(db, contract, original)

    if original.get("finding_type") == "interaction_decision":
        import interaction_enforcement
        return interaction_enforcement.verify_interaction_finding(db, contract, original)

    replay = rule_engine.analyze(contract.contract_text)
    match = next(
        (
            f for f in replay["findings"]
            if f.rule_id == original["rule_id"] and f.start_index == original.get("start_index")
        ),
        None,
    )
    verified = bool(match) and match.exact_snippet == original.get("exact_snippet")

    return {
        "verified": verified,
        "rule_id": original["rule_id"],
        "exact_snippet": match.exact_snippet if match else None,
    }


@app.post("/contract/{contract_id}/review/finalize")
async def finalize_review(
    request: Request, contract_id: int, db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)

    findings = contract.findings_json or []
    decisions = contract.review_decisions_json or {}
    progress = compute_progress(findings, decisions)
    if not progress.is_complete:
        raise HTTPException(status_code=400, detail=f"{progress.total - progress.resolved} finding(s) still need a decision")

    contract.review_finalized_at = datetime.utcnow()
    db.commit()
    analytics.record_event(request, "review_finalized", user=user, metadata={"contract_id": contract.id})
    return {"progress": progress.as_dict(), "finalized_at": contract.review_finalized_at.isoformat()}


@app.get("/contract/{contract_id}/review/package")
async def download_negotiation_package(request: Request, contract_id: int, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    contract = _get_owned_contract(db, user, contract_id)

    findings = contract.findings_json or []
    decisions = contract.review_decisions_json or {}
    progress = compute_progress(findings, decisions)
    if not progress.is_complete:
        raise HTTPException(status_code=400, detail="Finish reviewing every finding before generating the package")

    docx_bytes, skipped = build_redlined_docx(
        contract.filename, contract.contract_text, findings, decisions,
        author=user.name or user.email,
    )
    memo_text = build_cover_memo_text(contract.filename, findings, decisions)
    audit_text = build_audit_trail_text(contract.filename, contract.rule_engine_version or "2.0.0", findings, decisions)

    safe_name = sanitize_filename(contract.filename)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Redlined_{safe_name}.docx", docx_bytes)
        zf.writestr("Cover_Memo.txt", memo_text)
        zf.writestr("Audit_Trail.txt", audit_text)

    analytics.record_event(
        request, "negotiation_package_generated", user=user,
        metadata={"contract_id": contract.id, "skipped_redlines": skipped},
    )
    audit_log.record_event(
        db, "contract_exported", request=request, actor_user_id=user.id,
        target_type="contract", target_id=contract.id, success=True, detail="negotiation_package",
    )

    return Response(
        content=zip_buffer.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="NegotiationPackage_{safe_name}.zip"'},
    )


def _evaluate_share_link_access(contract: Contract) -> Optional[str]:
    """Returns None if the link currently grants access, or a short reason
    code otherwise ("revoked", "expired", "max_views_exceeded"). Checked
    before the password gate — a revoked/expired/exhausted link is
    unavailable regardless of whether the visitor has the password."""
    if contract.share_revoked_at is not None:
        return "revoked"
    if contract.share_expires_at is not None and datetime.utcnow() > contract.share_expires_at:
        return "expired"
    if contract.share_max_views is not None and contract.share_view_count >= contract.share_max_views:
        return "max_views_exceeded"
    return None


_SHARE_UNAVAILABLE_MESSAGES = {
    "revoked": "This link has been revoked by its owner and is no longer available.",
    "expired": "This link has expired and is no longer available.",
    "max_views_exceeded": "This link has reached its maximum number of views and is no longer available.",
}


def _share_unavailable_response(request: Request, contract: Contract, reason: str) -> HTMLResponse:
    return templates.TemplateResponse("shared_report.html", {
        "request": request, "link_unavailable": True,
        "link_unavailable_message": _SHARE_UNAVAILABLE_MESSAGES[reason],
        "password_required": False, "password_error": False,
        "filename": contract.filename, "current_year": datetime.now().year,
    })


@app.get("/shared/{share_token}", response_class=HTMLResponse)
async def view_shared_report(request: Request, share_token: str, db: DBSession = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.share_token == share_token).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Report not found")

    denial_reason = _evaluate_share_link_access(contract)
    if denial_reason:
        audit_log.record_event(
            db, "share_link_accessed", request=request, target_type="contract",
            target_id=contract.id, success=False, detail=denial_reason,
        )
        return _share_unavailable_response(request, contract, denial_reason)

    if contract.share_password_hash:
        return templates.TemplateResponse("shared_report.html", {
            "request": request, "password_required": True, "password_error": False,
            "filename": contract.filename, "current_year": datetime.now().year,
        })

    return _render_shared_report(request, contract, db)


@app.post("/shared/{share_token}", response_class=HTMLResponse)
async def view_shared_report_auth(
    request: Request, share_token: str, password: str = Form(...), db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("shared-report-password", limit=10, window_seconds=300)),
    _csrf: None = Depends(csrf_protect),
):
    contract = db.query(Contract).filter(Contract.share_token == share_token).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Report not found")

    denial_reason = _evaluate_share_link_access(contract)
    if denial_reason:
        audit_log.record_event(
            db, "share_link_accessed", request=request, target_type="contract",
            target_id=contract.id, success=False, detail=denial_reason,
        )
        return _share_unavailable_response(request, contract, denial_reason)

    if contract.share_password_hash and not verify_password(password, contract.share_password_hash):
        audit_log.record_event(
            db, "share_link_accessed", request=request, target_type="contract",
            target_id=contract.id, success=False, detail="wrong_password",
        )
        return templates.TemplateResponse("shared_report.html", {
            "request": request, "password_required": True, "password_error": True,
            "filename": contract.filename, "current_year": datetime.now().year,
        })

    return _render_shared_report(request, contract, db)


def _render_shared_report(request: Request, contract: Contract, db: DBSession) -> HTMLResponse:
    contract.share_view_count += 1
    db.commit()
    audit_log.record_event(
        db, "share_link_accessed", request=request, target_type="contract",
        target_id=contract.id, success=True, detail="viewed",
    )

    findings_dict = contract.findings_json or []
    llm_result = contract.llm_result_json or {}
    all_issues = build_enhanced_issues(findings_dict, llm_result)
    rule_counts = display_rule_stats(all_issues)

    return templates.TemplateResponse("shared_report.html", {
        "request": request, "password_required": False, "password_error": False,
        "filename": contract.filename,
        "overall_risk": contract.overall_risk,
        "summary_bullets": llm_result.get("summary_bullets", []),
        "top_issues": all_issues,
        "disclaimer": llm_result.get("disclaimer", "This is automated risk triage, not legal advice."),
        "findings_count": len(all_issues),
        "rule_counts": rule_counts,
        "rule_engine_version": contract.rule_engine_version or "1.0.3",
        "current_year": datetime.now().year,
        "legal_risk_score": contract.legal_risk_score,
        "business_risk_score": contract.business_risk_score,
        "negotiation_difficulty_score": contract.negotiation_difficulty_score,
    })


# ============================================================
# PLAYBOOKS
# ============================================================

@app.get("/playbooks", response_class=HTMLResponse)
async def playbooks_list(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).order_by(Playbook.created_at.desc()).all()
    plan = PLAN_LIMITS.get(user.plan, {"monthly_limit": 0, "batch_max": 1, "playbooks_max": 0})
    return templates.TemplateResponse("playbooks.html", {
        "request": request, "user": user, "playbooks": playbooks,
        "playbooks_max": plan.get("playbooks_max", 0),
        "can_create": len(playbooks) < plan.get("playbooks_max", 0),
        "current_year": datetime.now().year,
    })


@app.get("/playbooks/new", response_class=HTMLResponse)
async def playbook_new_page(request: Request, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    plan = PLAN_LIMITS.get(user.plan, {"monthly_limit": 0, "batch_max": 1, "playbooks_max": 0})
    existing = db.query(Playbook).filter(Playbook.user_id == user.id).count()
    if existing >= plan["playbooks_max"]:
        return RedirectResponse(url="/playbooks", status_code=302)
    return templates.TemplateResponse("playbook_form.html", {
        "request": request, "user": user, "playbook": None, "policy_rule": None,
        "exception_types": liability_policy_engine.EXCEPTION_TYPES,
        "error": None, "current_year": datetime.now().year,
    })


def _upsert_liability_policy_rule(
    db: DBSession, playbook: Playbook,
    lol_enabled: str, lol_side: str,
    lol_preferred: str, lol_acceptable_max: str, lol_negotiate_max: str,
    lol_prohibit_unlimited: str, lol_required_exceptions: List[str],
    lol_fallback_text: str, lol_escalation_authority: str,
    lol_require_consequential_exclusion: str = "",
    lol_required_consequential_carveouts: Optional[List[str]] = None,
):
    """Creates/updates/removes the playbook's limitation-of-liability
    PolicyRule from the submitted form fields. Deleting is legitimate (the
    lawyer unchecked "enable policy") — always look up the existing row
    first so a re-save with the checkbox off actually removes it rather
    than leaving a stale rule the engine would keep enforcing silently."""
    existing = db.query(PolicyRule).filter(
        PolicyRule.playbook_id == playbook.id, PolicyRule.clause_type == "limitation_of_liability",
    ).first()

    if lol_enabled != "on":
        if existing:
            db.delete(existing)
        return

    def _to_float(v: str) -> Optional[float]:
        v = (v or "").strip()
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    rule = existing or PolicyRule(playbook_id=playbook.id, clause_type="limitation_of_liability")
    rule.contract_side = lol_side if lol_side in ("buy_side", "sell_side", "mutual") else "mutual"
    rule.preferred_multiplier = _to_float(lol_preferred)
    rule.acceptable_max_multiplier = _to_float(lol_acceptable_max)
    rule.negotiate_max_multiplier = _to_float(lol_negotiate_max)
    rule.prohibit_unlimited = lol_prohibit_unlimited == "on"
    rule.required_exceptions_json = [e for e in (lol_required_exceptions or []) if e in liability_policy_engine.EXCEPTION_TYPES]
    rule.fallback_text = lol_fallback_text.strip() or None
    rule.escalation_approval_authority = lol_escalation_authority.strip() or None
    rule.require_consequential_damages_exclusion = lol_require_consequential_exclusion == "on"
    rule.required_consequential_carveouts_json = [
        e for e in (lol_required_consequential_carveouts or []) if e in liability_policy_engine.EXCEPTION_TYPES
    ]
    if existing:
        rule.version = (existing.version or 1) + 1
    if not existing:
        db.add(rule)


@app.post("/playbooks/new")
async def playbook_new_submit(
    request: Request,
    name: str = Form(...),
    contract_type: str = Form(""),
    description: str = Form(""),
    file: UploadFile = File(...),
    lol_enabled: str = Form(""),
    lol_side: str = Form("mutual"),
    lol_preferred: str = Form(""),
    lol_acceptable_max: str = Form(""),
    lol_negotiate_max: str = Form(""),
    lol_prohibit_unlimited: str = Form(""),
    lol_required_exceptions: List[str] = Form([]),
    lol_fallback_text: str = Form(""),
    lol_escalation_authority: str = Form(""),
    lol_require_consequential_exclusion: str = Form(""),
    lol_required_consequential_carveouts: List[str] = Form([]),
    db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)

    if not file.filename:
        return templates.TemplateResponse("playbook_form.html", {
            "request": request, "user": user, "playbook": None,
            "error": "Please upload a template file.", "current_year": datetime.now().year,
        })

    playbook_filename = upload_security.sanitize_filename(file.filename)
    ext = os.path.splitext(playbook_filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        return templates.TemplateResponse("playbook_form.html", {
            "request": request, "user": user, "playbook": None,
            "error": "Only PDF, DOCX, or TXT files.", "current_year": datetime.now().year,
        })

    file_bytes = await file.read()
    try:
        template_text = extract_text_from_file(file_bytes, playbook_filename)
    except upload_security.UploadRejected as e:
        return templates.TemplateResponse("playbook_form.html", {
            "request": request, "user": user, "playbook": None,
            "error": str(e), "current_year": datetime.now().year,
        })
    except Exception:
        return templates.TemplateResponse("playbook_form.html", {
            "request": request, "user": user, "playbook": None,
            "error": "Failed to parse template file.", "current_year": datetime.now().year,
        })

    # Pre-analyze the template
    analysis = rule_engine.analyze(template_text)
    template_findings = [
        {"rule_id": f.rule_id, "rule_name": f.rule_name, "title": f.title,
         "severity": f.severity.value, "rationale": f.rationale,
         "matched_excerpt": f.matched_excerpt}
        for f in analysis["findings"]
    ]

    playbook = Playbook(
        user_id=user.id, name=name.strip(), contract_type=contract_type.strip() or None,
        description=description.strip() or None, template_text=template_text,
        template_findings_json=template_findings, template_risk=analysis["overall_risk"],
    )
    db.add(playbook)
    db.flush()  # assigns playbook.id without ending the transaction
    _upsert_liability_policy_rule(
        db, playbook, lol_enabled, lol_side, lol_preferred, lol_acceptable_max, lol_negotiate_max,
        lol_prohibit_unlimited, lol_required_exceptions, lol_fallback_text, lol_escalation_authority,
        lol_require_consequential_exclusion, lol_required_consequential_carveouts,
    )
    db.commit()

    analytics.record_event(request, "playbook_created", user=user, metadata={"playbook_id": playbook.id})
    audit_log.record_event(
        db, "playbook_created", request=request, actor_user_id=user.id,
        target_type="playbook", target_id=playbook.id, success=True,
        metadata={"name": playbook.name},
    )

    # Phase 4.1 UX remediation (P0-1, docs/architecture/playbook_ux_audit.md):
    # a new playbook has no policy configured yet — route straight into the
    # three-path setup chooser rather than back to the plain playbooks list,
    # so a lawyer can never mistake "I uploaded a template" for "my policy
    # is configured." /playbooks/{id}/setup is the one entry point into the
    # Workbench/PolicyPosition authoring system from here on.
    return RedirectResponse(url=f"/playbooks/{playbook.id}/setup", status_code=302)


@app.get("/playbooks/{playbook_id}/setup", response_class=HTMLResponse)
async def playbook_setup_choice(request: Request, playbook_id: int, db: DBSession = Depends(get_db)):
    """The one entry point into the Policy Workbench authoring system
    (Phase 4.1 UX remediation, P0-1). Presents the three ways to populate
    a playbook's policy positions — AI-assisted import, deterministic/
    private template import, or manual setup — all of which converge on
    the same Workbench -> Review -> Approve -> Activate lifecycle. This
    page deliberately does not offer the legacy single-clause PolicyRule
    checkbox form (still reachable at /playbooks/{id}/edit for
    compatibility with playbooks configured before this change, never
    removed — see docs/architecture/phase4_cutover.md's rollback
    requirements) as a way to "finish setting up" a playbook."""
    user = require_user(request, db)
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return templates.TemplateResponse("playbook_setup_choice.html", {
        "request": request, "user": user, "playbook": playbook, "current_year": datetime.now().year,
    })


@app.get("/playbooks/{playbook_id}/edit", response_class=HTMLResponse)
async def playbook_edit_page(request: Request, playbook_id: int, db: DBSession = Depends(get_db)):
    user = require_user(request, db)
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    policy_rule = db.query(PolicyRule).filter(
        PolicyRule.playbook_id == playbook.id, PolicyRule.clause_type == "limitation_of_liability",
    ).first()
    return templates.TemplateResponse("playbook_form.html", {
        "request": request, "user": user, "playbook": playbook, "policy_rule": policy_rule,
        "exception_types": liability_policy_engine.EXCEPTION_TYPES,
        "error": None, "current_year": datetime.now().year,
    })


@app.post("/playbooks/{playbook_id}/edit")
async def playbook_edit_submit(
    request: Request, playbook_id: int,
    name: str = Form(...), contract_type: str = Form(""),
    description: str = Form(""), file: Optional[UploadFile] = File(None),
    lol_enabled: str = Form(""),
    lol_side: str = Form("mutual"),
    lol_preferred: str = Form(""),
    lol_acceptable_max: str = Form(""),
    lol_negotiate_max: str = Form(""),
    lol_prohibit_unlimited: str = Form(""),
    lol_required_exceptions: List[str] = Form([]),
    lol_fallback_text: str = Form(""),
    lol_escalation_authority: str = Form(""),
    lol_require_consequential_exclusion: str = Form(""),
    lol_required_consequential_carveouts: List[str] = Form([]),
    db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    playbook.name = name.strip()
    playbook.contract_type = contract_type.strip() or None
    playbook.description = description.strip() or None
    _upsert_liability_policy_rule(
        db, playbook, lol_enabled, lol_side, lol_preferred, lol_acceptable_max, lol_negotiate_max,
        lol_prohibit_unlimited, lol_required_exceptions, lol_fallback_text, lol_escalation_authority,
        lol_require_consequential_exclusion, lol_required_consequential_carveouts,
    )

    if file and file.filename:
        edit_filename = upload_security.sanitize_filename(file.filename)
        ext = os.path.splitext(edit_filename.lower())[1]
        if ext in ALLOWED_EXTENSIONS:
            file_bytes = await file.read()
            try:
                template_text = extract_text_from_file(file_bytes, edit_filename)
                playbook.template_text = template_text
                analysis = rule_engine.analyze(template_text)
                playbook.template_findings_json = [
                    {"rule_id": f.rule_id, "rule_name": f.rule_name, "title": f.title,
                     "severity": f.severity.value, "rationale": f.rationale,
                     "matched_excerpt": f.matched_excerpt}
                    for f in analysis["findings"]
                ]
                playbook.template_risk = analysis["overall_risk"]
            except Exception:
                pass

    db.commit()
    analytics.record_event(request, "playbook_updated", user=user, metadata={"playbook_id": playbook.id})
    audit_log.record_event(
        db, "playbook_updated", request=request, actor_user_id=user.id,
        target_type="playbook", target_id=playbook.id, success=True,
    )
    return RedirectResponse(url="/playbooks", status_code=302)


@app.post("/playbooks/{playbook_id}/delete")
async def playbook_delete(
    request: Request, playbook_id: int, db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    playbook_name = playbook.name
    db.delete(playbook)
    db.commit()
    audit_log.record_event(
        db, "playbook_deleted", request=request, actor_user_id=user.id,
        target_type="playbook", target_id=playbook_id, success=True,
        metadata={"name": playbook_name},
    )
    return RedirectResponse(url="/playbooks", status_code=302)


# ============================================================
# PRICING PAGE
# ============================================================

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    analytics.record_event(request, "pricing_view", user=user)
    return templates.TemplateResponse("pricing.html", {
        "request": request, "user": user, "plans": PLAN_LIMITS,
        "current_year": datetime.now().year,
    })


@app.post("/early-access", response_class=HTMLResponse)
async def early_access_submit(
    request: Request, db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(...),
    team_type: str = Form(...),
    team_size: str = Form(...),
    monthly_volume: str = Form(...),
    current_solution: str = Form(...),
    current_tooling: str = Form(...),
    message: str = Form(""),
):
    user = get_current_user(request, db)
    lead = {
        "name": name.strip()[:200],
        "email": email.strip()[:200],
        "company": company.strip()[:200],
        "team_type": team_type.strip()[:50],
        "team_size": team_size.strip()[:20],
        "monthly_volume": monthly_volume.strip()[:20],
        "current_solution": current_solution.strip()[:50],
        "current_tooling": current_tooling.strip()[:50],
        "message": message.strip()[:2000],
    }
    # Persist first — a notification-email failure must never lose the lead.
    audit_log.record_event(
        db, "early_access_request", request=request,
        actor_user_id=user.id if user else None,
        detail=f"{lead['name']} <{lead['email']}> ({lead['team_type']})",
        metadata=lead,
    )
    notify_to = os.getenv("EARLY_ACCESS_NOTIFY_EMAIL", "").strip()
    if notify_to and emailer.is_configured():
        try:
            body_lines = "\n".join(f"{k}: {v}" for k, v in lead.items())
            emailer.send_email(
                to=notify_to,
                subject=f"Early access request: {lead['name']} ({lead['team_type']})",
                html=f"<pre>{html.escape(body_lines)}</pre>",
                text=body_lines,
            )
        except Exception:
            logging.getLogger(__name__).exception("Failed to send early-access notification email")
    return templates.TemplateResponse("pricing.html", {
        "request": request, "user": user, "plans": PLAN_LIMITS,
        "current_year": datetime.now().year, "success": True,
    })


# ============================================================
# RESEARCH PAGE
# ============================================================

@app.get("/research", response_class=HTMLResponse)
async def research_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    analytics.record_event(request, "research_view", user=user)
    return templates.TemplateResponse("research.html", {
        "request": request, "user": user,
        "current_year": datetime.now().year,
    })


@app.get("/benchmark", response_class=HTMLResponse)
async def benchmark_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    analytics.record_event(request, "benchmark_view", user=user)
    return templates.TemplateResponse("benchmark.html", {
        "request": request, "user": user,
        "current_year": datetime.now().year,
    })


# ============================================================
# STRIPE SUBSCRIPTION
# ============================================================

@app.post("/subscribe/{plan}")
async def subscribe(
    request: Request, plan: str, db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = require_user(request, db)

    if plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    plan_config = PLAN_LIMITS[plan]

    form = await request.form()
    billing_period = form.get("billing_period", "monthly")
    if billing_period not in ("monthly", "yearly"):
        billing_period = "monthly"

    if DEV_MODE:
        user.plan = plan if plan != "unlimited" else "team"
        user.monthly_limit = plan_config["monthly_limit"]
        user.subscription_status = "active"
        user.contracts_this_month = 0
        db.commit()
        return RedirectResponse(url="/dashboard", status_code=302)

    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    current_base_url = get_base_url(request)
    interval = "month" if billing_period == "monthly" else "year"
    price_key = f"stripe_{billing_period}_price_id"
    stripe_price_id = plan_config.get(price_key, "")
    unit_amount = plan_config[f"{billing_period}_price"]

    if stripe_price_id:
        line_item = {"price": stripe_price_id, "quantity": 1}
    else:
        line_item = {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Triage Counsel — {plan.title()} Plan"},
                "unit_amount": unit_amount,
                "recurring": {"interval": interval},
            },
            "quantity": 1,
        }

    checkout = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        customer_email=user.email,
        client_reference_id=str(user.id),
        line_items=[line_item],
        allow_promotion_codes=True,
        success_url=f"{current_base_url}/dashboard?upgraded=true",
        cancel_url=f"{current_base_url}/pricing",
        metadata={"plan": plan, "user_id": str(user.id), "billing_period": billing_period},
    )
    return RedirectResponse(url=checkout.url, status_code=303)


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: DBSession = Depends(get_db)):
    if DEV_MODE:
        return {"status": "ignored"}

    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")


    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        plan = session.get("metadata", {}).get("plan")
        if user_id and plan:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                plan_config = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])
                user.plan = plan
                user.monthly_limit = plan_config["monthly_limit"]
                user.subscription_status = "active"
                user.contracts_this_month = 0
                user.stripe_customer_id = session.get("customer")
                user.stripe_subscription_id = session.get("subscription")
                db.commit()
                analytics.record_event(None, "subscription_started", user_id=user.id, metadata={
                    "plan": plan, "billing_period": session.get("metadata", {}).get("billing_period"),
                })

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                cancelled_plan = user.plan
                user.plan = "none"
                user.monthly_limit = 0
                user.subscription_status = "canceled"
                db.commit()
                analytics.record_event(None, "subscription_cancelled", user_id=user.id, metadata={
                    "previous_plan": cancelled_plan,
                })

    return {"status": "ok"}


# ============================================================
# FREE DEMO (no account required)
# ============================================================

DEMO_CONTRACT = """MUTUAL NON-DISCLOSURE AGREEMENT

1. Confidentiality. The Receiving Party agrees that all Confidential Information disclosed by the Disclosing Party shall remain confidential in perpetuity and shall not be disclosed to any third party without prior written consent.

2. Indemnification. The Receiving Party shall indemnify, defend, and hold harmless the Disclosing Party from and against any and all claims, damages, losses, and expenses without limit arising from any breach of this Agreement.

3. Intellectual Property. The Receiving Party hereby assigns all right, title, and interest in any work product, inventions, or improvements developed during the term of this Agreement.

4. Limitation of Liability. The limitation of liability set forth herein shall not apply to breaches of confidentiality, indemnification obligations, or intellectual property infringement.

5. Term. This Agreement shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least 30 days prior to expiration.

6. Governing Law. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, and the parties submit to the exclusive jurisdiction of the courts of Delaware.

7. Injunctive Relief. The parties agree that the Disclosing Party shall be entitled to injunctive relief and equitable relief without the requirement of posting a bond or other security in the event of any breach.

8. Attorneys' Fees. In the event of any dispute, the prevailing party shall be entitled to recover reasonable attorneys' fees and costs from the non-prevailing party.
"""

# A real, messy, real-world executive employment agreement — sourced from a
# public SEC EDGAR filing (see sample_contracts/ — same corpus as
# tests/fixtures/real_contracts), party names swapped for fictional ones
# since a live public demo shouldn't put a real named executive's actual
# compensation terms under a "HIGH RISK" banner. Every formatting quirk (a
# single ~30,000-character paragraph with no line breaks, "EX-10.1" filing
# header cruft) is untouched — that messiness is the point: it shows the
# engine working on the kind of extraction quality a lawyer actually gets
# from a scanned or HTML-derived exhibit, not a hand-formatted sample.
_MESSY_DEMO_CONTRACT_PATH = Path(__file__).parent / "sample_contracts" / "messy_executive_employment_agreement.txt"
try:
    MESSY_DEMO_CONTRACT = _MESSY_DEMO_CONTRACT_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    MESSY_DEMO_CONTRACT = DEMO_CONTRACT

DEMO_SAMPLES = {
    "clean": {
        "text": DEMO_CONTRACT,
        "filename": "Sample NDA (Demo)",
        "label": "Clean NDA",
        "doc_label": "Sample_Mutual_NDA.txt",
        "description": "A short, cleanly formatted mutual NDA — good for seeing every part of a report at a glance.",
        "highlights": ("in perpetuity", "without limit"),
    },
    "messy": {
        "text": MESSY_DEMO_CONTRACT,
        "filename": "Sample Executive Employment Agreement (Messy, Demo)",
        "label": "Messy Real-World Contract",
        "doc_label": "exhibit_10.1_employment_agreement.txt",
        "description": "See how our tool works with messy contracts — this one is a single ~30,000-character block with no paragraph breaks and leftover SEC filing header text, exactly as it came out of the original exhibit.",
        "highlights": (),
    },
}
_DEFAULT_DEMO_SAMPLE = "clean"


def _demo_sample_key(raw: Optional[str]) -> str:
    return raw if raw in DEMO_SAMPLES else _DEFAULT_DEMO_SAMPLE


def _build_demo_preview_html(contract_text: str, highlights: Tuple[str, ...], max_chars: int = 900) -> str:
    """Escape the sample contract for safe HTML display and wrap any known
    one-sided phrases in the same red "finding" mark styling the real
    redline workspace uses, so the preview reads as a teaser of that
    feature rather than a plain text dump. Truncates to max_chars at the
    last word boundary rather than splitting on blank lines — some real
    contracts (see the messy sample) have no blank-line paragraph breaks at
    all, so a paragraph-based cut would grab the entire document instead of
    a short preview."""
    source = contract_text.strip()
    truncated = len(source) > max_chars
    if truncated:
        source = source[:max_chars].rsplit(" ", 1)[0]
    escaped = html.escape(source)
    for phrase in highlights:
        escaped = escaped.replace(
            html.escape(phrase),
            f'<span style="border-bottom:2px solid #DC2626;background:#FEF2F2;border-radius:2px;">{html.escape(phrase)}</span>',
        )
    result = escaped.replace("\n", "<br>")
    return result + "&hellip;" if truncated else result


@app.get("/demo", response_class=HTMLResponse)
async def demo_preview(request: Request, sample: str = "clean"):
    """Public, non-mutating preview of a sample contract analysis — no
    account, no database write. The CTA on this page posts to /demo/start,
    which is what actually provisions a live, interactive copy. `sample`
    toggles between the curated clean NDA and a real, messy SEC exhibit."""
    sample_key = _demo_sample_key(sample)
    sample_info = DEMO_SAMPLES[sample_key]
    analysis = run_analysis(sample_info["text"])
    return templates.TemplateResponse("demo_preview.html", {
        "request": request, "user": None,
        "current_year": datetime.now().year,
        "overall_risk": analysis["overall_risk"],
        "finding_count": len(analysis["findings_dict"]),
        "preview_html": _build_demo_preview_html(sample_info["text"], sample_info["highlights"]),
        "samples": DEMO_SAMPLES,
        "sample_key": sample_key,
        "sample_info": sample_info,
    })


@app.post("/demo/start")
async def demo_start(
    request: Request,
    sample: str = Form("clean"),
    db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("demo_start", limit=10, window_seconds=3600)),
    _csrf: None = Depends(csrf_protect),
):
    """Provisions a live, private copy of the demo analysis so a visitor can
    use the real product end to end — the Verification Report, the risk
    dashboard, and the interactive redline workspace (accept/edit/reject/
    comment) — without creating an account first.

    An already-logged-in visitor gets the demo contract added to their own
    account, same as any upload. An anonymous visitor gets a throwaway
    guest account (no password, a recognizable @guest.triagecounsel.local
    address) created transparently and logged into via a normal session
    cookie, so every downstream route (ownership checks, redline actions,
    PDF export, share links) works completely unmodified — the guest IS a
    real account, just one nobody had to fill out a form to create.

    `sample` picks which DEMO_SAMPLES entry to provision — whichever one
    the visitor was previewing on /demo.
    """
    user = get_current_user(request, db)
    new_guest = user is None

    if not user:
        user = _create_guest_user(db, request, name="Demo Visitor")
        analytics.record_event(request, "demo_guest_created", user=user)

    sample_info = DEMO_SAMPLES[_demo_sample_key(sample)]
    analysis = run_analysis(sample_info["text"])
    contract = Contract(
        user_id=user.id,
        filename=sample_info["filename"],
        contract_text=sample_info["text"],
        overall_risk=analysis["overall_risk"],
        findings_json=analysis["findings_dict"],
        llm_result_json=analysis["llm_result"],
        rule_counts_json=analysis["rule_counts"],
        rule_engine_version=analysis["version"],
        analysis_completed=True,
        signature_readiness=analysis.get("signature_readiness"),
        payment_terms_json=analysis.get("payment_terms"),
        blocking_findings_json=analysis.get("blocking_findings"),
        policy_blocked_findings_json=analysis.get("policy_blocked_findings"),
        legal_risk_score=analysis.get("risk_dashboard", {}).get("legal_risk_score"),
        business_risk_score=analysis.get("risk_dashboard", {}).get("business_risk_score"),
        negotiation_difficulty_score=analysis.get("risk_dashboard", {}).get("negotiation_difficulty_score"),
        risk_dashboard_json=analysis.get("risk_dashboard"),
        structure_report_json=analysis.get("structure_report"),
        clause_quality_json=analysis.get("clause_quality"),
        metadata_json=analysis.get("metadata"),
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    analytics.record_event(request, "demo_started", user=user, metadata={"contract_id": contract.id})

    response = RedirectResponse(url=f"/contract/{contract.id}/review", status_code=303)
    if new_guest:
        create_session(user.id, response)
    return response


# ============================================================
# MARKETING PAGES
# ============================================================

@app.get("/security", response_class=HTMLResponse)
async def security_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("security.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    })


@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("faq.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    })


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("about.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    })


@app.get("/partners", response_class=HTMLResponse)
async def partners_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("partners.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    })


@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("contact.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    })


@app.post("/contact", response_class=HTMLResponse)
async def contact_submit(
    request: Request, db: DBSession = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request, db)
    return templates.TemplateResponse("contact.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
        "success": True,
    })


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("privacy.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    })


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("terms.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    with db_session() as db:
        user = get_current_user(request, db)
    return templates.TemplateResponse("errors/404.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    }, status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    with db_session() as db:
        try:
            user = get_current_user(request, db)
        except Exception:
            user = None
    return templates.TemplateResponse("errors/500.html", {
        "request": request, "user": user, "current_year": datetime.now().year,
    }, status_code=500)


# ============================================================
# LEGACY ROUTES (anonymous/token-based)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: DBSession = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("home.html", {
        "request": request, "current_year": datetime.now().year,
        "user": user,
    })


@app.get("/health")
async def health_check():
    db_ok = check_db_health()
    redis_ok = check_redis_health()
    healthy = db_ok and redis_ok
    status_code = 200 if healthy else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if healthy else "degraded",
            "database": "ok" if db_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        },
    )


@app.get("/config")
async def get_config():
    return {"dev_mode": DEV_MODE, "stripe_enabled": not DEV_MODE and bool(STRIPE_SECRET_KEY)}


@app.post("/internal/retention/cleanup")
async def internal_retention_cleanup(
    request: Request, db: DBSession = Depends(get_db),
    _rl: None = Depends(rate_limit("retention-cleanup", limit=6, window_seconds=3600)),
):
    """Scheduled retention cleanup, triggered over HTTP (see retention.py's
    module docstring) — for platforms that schedule jobs via a URL rather
    than a shell, e.g. Vercel Cron Jobs. Requires CRON_SECRET to be
    configured; without it, this route always 404s rather than exposing an
    unauthenticated deletion endpoint by default. Not the primary path for
    the Docker deployment — see run_retention_cleanup.py for cron/systemd/
    Kubernetes CronJob use there."""
    cron_secret = os.getenv("CRON_SECRET", "").strip()
    if not cron_secret:
        raise HTTPException(status_code=404)

    auth_header = request.headers.get("authorization", "")
    provided = auth_header[len("Bearer "):] if auth_header.startswith("Bearer ") else ""
    if not provided or not hmac.compare_digest(provided, cron_secret):
        audit_log.record_event(
            db, "retention_cleanup_denied", request=request, target_type="route",
            target_id=None, success=False, detail="invalid_cron_secret",
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    stats = retention.run_cleanup(db)
    audit_log.record_event(
        db, "retention_cleanup_run", request=request, target_type="route",
        target_id=None, success=stats["errors"] == 0, metadata=stats,
    )
    return stats


@app.get("/results", response_class=HTMLResponse)
async def results_legacy(request: Request, token: str):
    """Legacy token-based results (for anonymous users)."""
    try:
        session_id, sig = token.rsplit(":", 1)
        expected = hmac.new(APP_HMAC_SECRET.encode(), session_id.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=400, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token")

    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session expired")

    entry = session_store[session_id]
    if not entry.get("paid") and not DEV_MODE:
        raise HTTPException(status_code=402, detail="Payment required")

    contract_text = entry.get("text", "")
    analysis = run_analysis(contract_text)
    all_issues = build_enhanced_issues(analysis["findings_dict"], analysis["llm_result"])

    findings_objs = [type('F', (), {"rule_id": f["rule_id"]})() for f in analysis["findings_dict"]]
    rule_based_sections = rule_engine.build_missing_sections(findings_objs)
    llm_sections = analysis["llm_result"].get("possible_missing_sections", [])
    all_missing = rule_based_sections.copy()
    for s in llm_sections:
        if not any(s.lower() in e.lower() or e.lower() in s.lower() for e in all_missing):
            all_missing.append(s)

    import json as _json
    version_path = Path(__file__).parent / "rules" / "version.json"
    try:
        ruleset_meta = _json.loads(version_path.read_text())
    except Exception:
        ruleset_meta = {}
    total_rule_count = sum(ruleset_meta.get("rule_count", {}).values()) if ruleset_meta.get("rule_count") else len(rule_engine.rules)

    rule_categories = _build_rule_categories(analysis["findings_dict"], rule_engine)

    return templates.TemplateResponse("results.html", {
        "request": request, "user": None,
        "filename": entry.get("filename", "document"),
        "overall_risk": analysis["overall_risk"],
        "summary_bullets": analysis["llm_result"].get("summary_bullets", []),
        "top_issues": all_issues,
        "possible_missing_sections": all_missing[:6],
        "disclaimer": analysis["llm_result"].get("disclaimer", "This is automated risk triage, not legal advice."),
        "findings_count": len(all_issues),
        "rule_counts": display_rule_stats(all_issues),
        "rule_engine_version": analysis["version"],
        "current_year": datetime.now().year,
        "token": token, "contract_id": None, "deviations": None,
        "explanation_source": analysis["llm_result"].get("explanation_source"),
        "total_rule_count": total_rule_count,
        "rule_categories": rule_categories,
        "findings_dict": analysis["findings_dict"],
        "analysis_id": f"TR-{datetime.now().year}-{session_id[:6].upper()}",
        "generated_at": datetime.now().strftime("%Y-%m-%d %I:%M %p UTC"),
        "signature_readiness": analysis.get("signature_readiness"),
        "payment_terms": analysis.get("payment_terms"),
        "blocking_findings": analysis.get("blocking_findings", []),
        "policy_blocked_findings": analysis.get("policy_blocked_findings", []),
        "legal_risk_score": analysis.get("risk_dashboard", {}).get("legal_risk_score"),
        "business_risk_score": analysis.get("risk_dashboard", {}).get("business_risk_score"),
        "negotiation_difficulty_score": analysis.get("risk_dashboard", {}).get("negotiation_difficulty_score"),
        "risk_dashboard": analysis.get("risk_dashboard"),
        "structure_report": analysis.get("structure_report"),
        "clause_quality": analysis.get("clause_quality"),
        "metadata": analysis.get("metadata"),
        "risk_balance": analysis.get("risk_balance"),
    })


# ============================================================
# ADMIN DASHBOARD
# ============================================================

def require_admin(request: Request, db: DBSession) -> User:
    """Role-based (P8) — see rbac.py. Replaces the previous single
    hardcoded-admin-email comparison; who holds the "admin" role is now
    data (the user_roles table), managed via manage_roles.py, not a
    constant baked into this file."""
    user = require_user(request, db)
    if not rbac.user_has_permission(db, user, "admin.dashboard.view"):
        audit_log.record_event(
            db, "admin_access_denied", request=request, actor_user_id=user.id,
            target_type="route", target_id=None, success=False,
            detail="missing_permission:admin.dashboard.view", metadata={"path": request.url.path},
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: DBSession = Depends(get_db)):
    user = require_admin(request, db)
    audit_log.record_event(
        db, "admin_dashboard_accessed", request=request, actor_user_id=user.id,
        target_type="route", target_id=None, success=True,
    )

    from sqlalchemy import func, cast, Date

    # --- Headline counts ---
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_contracts = db.query(func.count(Contract.id)).filter(Contract.analysis_completed == True).scalar() or 0
    total_playbooks = db.query(func.count(Playbook.id)).scalar() or 0

    # Users in last 30 days
    thirty_ago = datetime.utcnow() - timedelta(days=30)
    new_users_30d = db.query(func.count(User.id)).filter(User.created_at >= thirty_ago).scalar() or 0
    new_contracts_30d = db.query(func.count(Contract.id)).filter(
        Contract.created_at >= thirty_ago, Contract.analysis_completed == True
    ).scalar() or 0

    # Plan breakdown
    plan_counts = dict(
        db.query(User.plan, func.count(User.id))
        .group_by(User.plan)
        .all()
    )

    # Risk breakdown
    risk_counts = dict(
        db.query(Contract.overall_risk, func.count(Contract.id))
        .filter(Contract.analysis_completed == True)
        .group_by(Contract.overall_risk)
        .all()
    )

    # Users table: each user with job count, playbook count, latest activity
    users_raw = db.query(User).order_by(User.created_at.desc()).all()
    users_table = []
    for u in users_raw:
        job_count = db.query(func.count(Contract.id)).filter(
            Contract.user_id == u.id, Contract.analysis_completed == True
        ).scalar() or 0
        pb_count = db.query(func.count(Playbook.id)).filter(Playbook.user_id == u.id).scalar() or 0
        latest = db.query(Contract.created_at).filter(
            Contract.user_id == u.id, Contract.analysis_completed == True
        ).order_by(Contract.created_at.desc()).first()
        users_table.append({
            "id": u.id,
            "email": u.email,
            "name": u.name or "—",
            "company": u.company or "—",
            "plan": u.plan or "none",
            "sub_status": u.subscription_status or "inactive",
            "jobs": job_count,
            "playbooks": pb_count,
            "jobs_this_month": u.contracts_this_month,
            "monthly_limit": u.monthly_limit,
            "created_at": u.created_at.strftime("%Y-%m-%d") if u.created_at else "—",
            "last_job": latest[0].strftime("%Y-%m-%d") if latest else "never",
        })

    # Daily snapshots: contracts per day for last 30 days
    daily_jobs = db.query(
        cast(Contract.created_at, Date).label("day"),
        func.count(Contract.id).label("cnt")
    ).filter(
        Contract.created_at >= thirty_ago,
        Contract.analysis_completed == True
    ).group_by("day").order_by("day").all()

    daily_users = db.query(
        cast(User.created_at, Date).label("day"),
        func.count(User.id).label("cnt")
    ).filter(User.created_at >= thirty_ago).group_by("day").order_by("day").all()

    # Recent contracts (last 20)
    recent_contracts = (
        db.query(Contract, User)
        .join(User, Contract.user_id == User.id)
        .filter(Contract.analysis_completed == True)
        .order_by(Contract.created_at.desc())
        .limit(20)
        .all()
    )
    recent_list = [{
        "filename": c.filename,
        "risk": c.overall_risk or "—",
        "email": u.email,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
        "plan": u.plan or "none",
    } for c, u in recent_contracts]

    # Top users by job count (leaderboard)
    top_users = sorted(users_table, key=lambda x: x["jobs"], reverse=True)[:10]

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user": user,
        "total_users": total_users,
        "total_contracts": total_contracts,
        "total_playbooks": total_playbooks,
        "new_users_30d": new_users_30d,
        "new_contracts_30d": new_contracts_30d,
        "plan_counts": plan_counts,
        "risk_counts": risk_counts,
        "users_table": users_table,
        "recent_list": recent_list,
        "top_users": top_users,
        "daily_jobs": [(str(r.day), r.cnt) for r in daily_jobs],
        "daily_users": [(str(r.day), r.cnt) for r in daily_users],
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    })


# ============================================================
# ADMIN — ACQUISITION & PRODUCT ANALYTICS
# ============================================================

@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request, q: str = "", channel: str = "", db: DBSession = Depends(get_db)):
    user = require_admin(request, db)

    from sqlalchemy import func

    def top_n(column, limit: int = 10):
        rows = (
            db.query(column, func.count(UserAcquisition.id).label("cnt"))
            .filter(column.isnot(None), column != "")
            .group_by(column)
            .order_by(func.count(UserAcquisition.id).desc())
            .limit(limit)
            .all()
        )
        return [(value, cnt) for value, cnt in rows]

    top_channels = top_n(UserAcquisition.acquisition_channel)
    top_referrers = top_n(UserAcquisition.signup_referring_domain)
    top_landing_pages = top_n(UserAcquisition.landing_page)
    top_campaigns = top_n(UserAcquisition.utm_campaign)
    top_countries = top_n(UserAcquisition.signup_country)
    top_browsers = top_n(UserAcquisition.browser)
    top_devices = top_n(UserAcquisition.device_type)
    top_utm_sources = top_n(UserAcquisition.utm_source)

    # --- Acquisition funnel ---
    total_visitors = db.query(func.count(func.distinct(UserSession.session_id))).scalar() or 0
    signup_started = db.query(func.count(func.distinct(UserEvent.session_id))).filter(
        UserEvent.event_type.in_(["signup_started", "google_oauth_redirect"])
    ).scalar() or 0
    signup_completed = db.query(func.count(UserAcquisition.id)).scalar() or 0

    upload_counts_by_user = dict(
        db.query(ContractEvent.user_id, func.count(ContractEvent.id))
        .filter(ContractEvent.status == "completed", ContractEvent.user_id.isnot(None))
        .group_by(ContractEvent.user_id)
        .all()
    )
    first_upload_users = sum(1 for c in upload_counts_by_user.values() if c >= 1)
    second_upload_users = sum(1 for c in upload_counts_by_user.values() if c >= 2)

    subscribed_users = db.query(func.count(func.distinct(UserEvent.user_id))).filter(
        UserEvent.event_type == "subscription_started"
    ).scalar() or 0

    funnel = [
        ("Visitors", total_visitors),
        ("Signup Started", signup_started),
        ("Signup Completed", signup_completed),
        ("First Upload", first_upload_users),
        ("Second Upload", second_upload_users),
        ("Subscription", subscribed_users),
    ]

    # --- Acquisition table: most recent 500, filterable ---
    acq_query = db.query(UserAcquisition, User).join(User, UserAcquisition.user_id == User.id)
    if channel:
        acq_query = acq_query.filter(UserAcquisition.acquisition_channel == channel)
    if q:
        like = f"%{q}%"
        acq_query = acq_query.filter(
            User.email.ilike(like)
            | UserAcquisition.utm_source.ilike(like)
            | UserAcquisition.utm_campaign.ilike(like)
            | UserAcquisition.signup_referring_domain.ilike(like)
            | UserAcquisition.signup_country.ilike(like)
        )
    rows = acq_query.order_by(UserAcquisition.signup_timestamp.desc()).limit(500).all()

    acquisitions = [{
        "user_id": u.id,
        "email": u.email,
        "signup_date": a.signup_timestamp.strftime("%Y-%m-%d %H:%M") if a.signup_timestamp else "—",
        "channel": a.acquisition_channel or "Unknown",
        "country": a.signup_country or "—",
        "city": a.signup_city or "—",
        "referrer": a.signup_referring_domain or "Direct",
        "landing_page": a.landing_page or "—",
        "utm_source": a.utm_source or "—",
        "utm_campaign": a.utm_campaign or "—",
        "browser": a.browser or "—",
        "os": a.os or "—",
        "device": a.device_type or "—",
        "ip": a.signup_ip or a.signup_ipv6 or "—",
    } for a, u in rows]

    return templates.TemplateResponse("admin_analytics.html", {
        "request": request, "user": user,
        "top_channels": top_channels, "top_referrers": top_referrers,
        "top_landing_pages": top_landing_pages, "top_campaigns": top_campaigns,
        "top_countries": top_countries, "top_browsers": top_browsers,
        "top_devices": top_devices, "top_utm_sources": top_utm_sources,
        "funnel": funnel, "acquisitions": acquisitions,
        "channel_filter": channel, "q": q, "all_channels": sorted(ACQUISITION_CHANNELS),
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    })


@app.get("/admin/analytics/user/{target_user_id}", response_class=HTMLResponse)
async def admin_analytics_user_detail(request: Request, target_user_id: int, db: DBSession = Depends(get_db)):
    user = require_admin(request, db)

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    acquisition = db.query(UserAcquisition).filter(UserAcquisition.user_id == target_user_id).first()
    sessions = (
        db.query(UserSession).filter(UserSession.user_id == target_user_id)
        .order_by(UserSession.started_at.desc()).limit(50).all()
    )
    events = (
        db.query(UserEvent).filter(UserEvent.user_id == target_user_id)
        .order_by(UserEvent.event_timestamp.desc()).limit(200).all()
    )

    return templates.TemplateResponse("admin_analytics_user.html", {
        "request": request, "user": user, "target": target,
        "acquisition": acquisition, "sessions": sessions, "events": events,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    })


@app.get("/admin/analytics/export.csv")
async def admin_analytics_export_csv(request: Request, db: DBSession = Depends(get_db)):
    require_admin(request, db)

    import csv
    import io

    rows = (
        db.query(UserAcquisition, User)
        .join(User, UserAcquisition.user_id == User.id)
        .order_by(UserAcquisition.signup_timestamp.desc())
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "user_id", "email", "signup_timestamp", "acquisition_channel",
        "signup_country", "signup_region", "signup_city", "signup_referring_domain",
        "landing_page", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "browser", "browser_version", "os", "os_version", "device_type",
        "signup_ip", "signup_ipv6",
    ])
    for a, u in rows:
        writer.writerow([
            u.id, u.email,
            a.signup_timestamp.isoformat() if a.signup_timestamp else "",
            a.acquisition_channel or "", a.signup_country or "", a.signup_region or "", a.signup_city or "",
            a.signup_referring_domain or "", a.landing_page or "", a.utm_source or "", a.utm_medium or "",
            a.utm_campaign or "", a.utm_term or "", a.utm_content or "", a.browser or "", a.browser_version or "",
            a.os or "", a.os_version or "", a.device_type or "", a.signup_ip or "", a.signup_ipv6 or "",
        ])

    date_str = datetime.utcnow().strftime("%Y%m%d")
    return Response(
        content=buffer.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="acquisition_export_{date_str}.csv"'},
    )


# ============================================================
# SEO
# ============================================================

@app.get("/robots.txt", response_class=Response)
async def robots_txt(request: Request):
    content = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /dashboard
Disallow: /dashboard/
Disallow: /upload-page
Disallow: /history
Disallow: /batch-upload
Disallow: /playbooks
Disallow: /playbooks/
Disallow: /contract/
Disallow: /shared/
Disallow: /logout
Disallow: /login
Disallow: /register
Disallow: /private/
Disallow: /subscribe/
Disallow: /stripe-webhook
Disallow: /health
Disallow: /config

Host: https://triagecounsel.com
Sitemap: https://triagecounsel.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


@app.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(request: Request):
    base = "https://triagecounsel.com"
    today = datetime.now().strftime("%Y-%m-%d")
    pages = [
        ("/",         "1.0",  "weekly"),
        ("/pricing",  "0.9",  "monthly"),
        ("/research", "0.8",  "monthly"),
        ("/security", "0.8",  "monthly"),
        ("/faq",      "0.8",  "monthly"),
        ("/about",    "0.8",  "monthly"),
        ("/contact",  "0.7",  "monthly"),
        ("/demo",     "0.9",  "weekly"),
        ("/privacy",  "0.4",  "yearly"),
        ("/terms",    "0.4",  "yearly"),
    ]
    entries = "\n".join(
        f"""  <url>
    <loc>{base}{path}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>""" for path, priority, freq in pages
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>"""
    return Response(content=xml, media_type="application/xml")
