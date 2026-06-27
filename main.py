"""
FastAPI app for Contract Risk Triage Tool

Phase 1: User accounts, subscription billing, contract history, batch upload
Phase 2: Playbook comparison, dashboard, report sharing
"""
from __future__ import annotations

import os
import io
import hmac
import hashlib
import json
import logging
import secrets
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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
from fpdf import FPDF
from PyPDF2 import PdfReader
from docx import Document
from sqlalchemy.orm import Session as DBSession

from rules_engine import RuleEngine
from evaluator import LLMEvaluator
from database import get_db, init_db
from auth import (
    hash_password, verify_password, create_session, get_current_user,
    logout as auth_logout, check_usage_limit,
)
from models import User, Contract, Playbook
from playbook_engine import PlaybookEngine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

if not DEV_MODE:
    if not STRIPE_SECRET_KEY:
        raise ValueError("STRIPE_SECRET_KEY required in production mode")
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET required in production mode")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY required in production mode")
    stripe.api_key = STRIPE_SECRET_KEY
else:
    stripe.api_key = STRIPE_SECRET_KEY if STRIPE_SECRET_KEY else ""

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# Plan limits
PLAN_LIMITS = {
    "starter": {"monthly_limit": 10, "batch_max": 3, "playbooks_max": 1, "price": 499, "price_type": "one_time"},
    "professional": {"monthly_limit": 150, "batch_max": 10, "playbooks_max": 5, "price": 4900, "price_type": "one_time"},
    "unlimited": {"monthly_limit": 999999, "batch_max": 50, "playbooks_max": 50, "price": 24900, "price_type": "recurring"},
}

# --- App setup ---
templates = Jinja2Templates(directory="templates")
app = FastAPI(title="Contract Risk Triage Tool", version="2.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

rule_engine = RuleEngine()
llm_evaluator = LLMEvaluator()
playbook_engine = PlaybookEngine()

# Legacy in-memory session store (for backward compat with unsigned uploads)
session_store: Dict[str, Dict] = {}


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info(f"Mode={'DEMO' if DEV_MODE else 'PROD'} | DB initialized")


# --- Helpers ---

def require_user(request: Request, db: DBSession) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".txt":
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return file_bytes.decode("latin-1", errors="ignore")
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    if ext == ".docx":
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError("Unsupported file type")


def run_analysis(contract_text: str) -> Dict:
    """Run rule engine + LLM evaluation, return full analysis dict."""
    analysis = rule_engine.analyze(contract_text)
    findings = analysis["findings"]
    overall_risk = analysis["overall_risk"]

    findings_dict = [
        {
            "rule_id": f.rule_id, "rule_name": f.rule_name, "title": f.title,
            "severity": f.severity.value, "rationale": f.rationale,
            "matched_excerpt": f.matched_excerpt, "position": f.position,
            "context": f.context, "clause_number": f.clause_number,
            "matched_keywords": f.matched_keywords, "aliases": f.aliases,
        }
        for f in findings
    ]

    try:
        llm_result = llm_evaluator.evaluate(findings=findings_dict, overall_risk=overall_risk, contract_text=None)
        if not llm_result:
            llm_result = llm_evaluator.create_fallback_response(findings=findings_dict, overall_risk=overall_risk)
    except Exception:
        llm_result = llm_evaluator.create_fallback_response(findings=findings_dict, overall_risk=overall_risk)

    return {
        "findings_dict": findings_dict,
        "overall_risk": overall_risk,
        "llm_result": llm_result,
        "rule_counts": analysis.get("rule_counts", {"high": 0, "medium": 0, "low": 0}),
        "version": analysis.get("version", "1.0.3"),
    }


def build_enhanced_issues(findings_dict: List[Dict], llm_result: Dict) -> List[Dict]:
    """Build complete list of findings enhanced with LLM explanations."""
    llm_issues_map = {}
    for issue in llm_result.get("top_issues", []):
        llm_issues_map[issue.get("title", "").lower()] = issue

    all_issues = []
    seen_rule_ids = set()

    for finding in findings_dict:
        rule_id = finding.get("rule_id", "")
        if rule_id in seen_rule_ids:
            continue
        seen_rule_ids.add(rule_id)

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
            enhanced = {
                "title": finding.get("title", ""),
                "severity": finding.get("severity", "low"),
                "why_it_matters": finding.get("rationale", "This may indicate increased contractual risk."),
                "negotiation_consideration": "Commonly negotiated; consider clarifying scope, caps, and mutuality.",
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

        all_issues.append(enhanced)

    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_issues.sort(key=lambda x: (severity_order.get(x.get("severity", "low"), 9), x.get("title", "")))
    return all_issues


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
async def login_page(request: Request):
    user = get_current_user(request, next(get_db()))
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    db = next(get_db())
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password."})
    response = RedirectResponse(url="/dashboard", status_code=302)
    create_session(user.id, response)
    return response


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    name: str = Form(""),
    company: str = Form(""),
):
    db = next(get_db())
    email = email.lower().strip()

    if password != confirm_password:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Passwords do not match."})
    if len(password) < 8:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Password must be at least 8 characters."})
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "An account with this email already exists."})

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name.strip() or None,
        company=company.strip() or None,
        plan="none",
        monthly_limit=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response = RedirectResponse(url="/dashboard", status_code=302)
    create_session(user.id, response)
    return response


@app.get("/logout")
async def logout_route(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    auth_logout(request, response)
    return response


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = next(get_db())
    user = require_user(request, db)
    contracts = db.query(Contract).filter(
        Contract.user_id == user.id, Contract.analysis_completed == True
    ).order_by(Contract.created_at.desc()).limit(20).all()

    total = db.query(Contract).filter(Contract.user_id == user.id, Contract.analysis_completed == True).count()
    high_count = db.query(Contract).filter(
        Contract.user_id == user.id, Contract.overall_risk == "high", Contract.analysis_completed == True
    ).count()

    stats = {
        "total_contracts": total,
        "high_risk_count": high_count,
        "contracts_this_month": user.contracts_this_month,
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "contracts": contracts,
        "stats": stats, "current_year": datetime.now().year,
    })


# ============================================================
# CONTRACT HISTORY
# ============================================================

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request, q: str = "", risk: str = "", page: int = 1):
    db = next(get_db())
    user = require_user(request, db)
    per_page = 25

    query = db.query(Contract).filter(Contract.user_id == user.id, Contract.analysis_completed == True)
    if q:
        query = query.filter(Contract.filename.ilike(f"%{q}%"))
    if risk in ("high", "medium", "low"):
        query = query.filter(Contract.overall_risk == risk)

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    contracts = query.order_by(Contract.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return templates.TemplateResponse("history.html", {
        "request": request, "user": user, "contracts": contracts,
        "q": q, "active_filter": risk or "all", "page": page, "total_pages": total_pages,
        "current_year": datetime.now().year,
    })


# ============================================================
# SINGLE CONTRACT UPLOAD (authenticated)
# ============================================================

@app.get("/upload-page", response_class=HTMLResponse)
async def upload_page(request: Request):
    db = next(get_db())
    user = require_user(request, db)
    playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).all()
    return templates.TemplateResponse("index.html", {
        "request": request, "current_year": datetime.now().year,
        "dev_mode": DEV_MODE, "user": user, "playbooks": playbooks,
    })


@app.post("/upload")
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    playbook_id: Optional[int] = Form(None),
):
    db = next(get_db())
    user = get_current_user(request, db)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, or TXT")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        contract_text = extract_text_from_file(file_bytes, file.filename)
        if not contract_text or not contract_text.strip():
            raise HTTPException(status_code=400, detail="File appears empty after parsing")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to parse document")

    # If user is logged in, save to DB
    if user:
        if not check_usage_limit(user):
            raise HTTPException(status_code=402, detail="Monthly contract limit reached. Please upgrade your plan.")

        analysis = run_analysis(contract_text)

        # Playbook comparison
        deviations = None
        if playbook_id:
            playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
            if playbook and playbook.template_findings_json:
                comparison = playbook_engine.compare(analysis["findings_dict"], playbook.template_findings_json)
                deviations = comparison

        contract = Contract(
            user_id=user.id,
            filename=file.filename,
            contract_text=contract_text,
            overall_risk=analysis["overall_risk"],
            findings_json=analysis["findings_dict"],
            llm_result_json=analysis["llm_result"],
            rule_counts_json=analysis["rule_counts"],
            rule_engine_version=analysis["version"],
            analysis_completed=True,
            playbook_id=playbook_id,
            deviations_json=deviations,
        )
        db.add(contract)
        user.contracts_this_month += 1
        db.commit()
        db.refresh(contract)

        return RedirectResponse(url=f"/contract/{contract.id}", status_code=303)

    # Anonymous flow (legacy: pay-per-use via Stripe)
    if DEV_MODE:
        app_session_id = secrets.token_urlsafe(18)
        sig = hmac.new(APP_HMAC_SECRET.encode(), app_session_id.encode(), hashlib.sha256).hexdigest()
        token = f"{app_session_id}:{sig}"
        session_store[app_session_id] = {
            "paid": True, "text": contract_text, "filename": file.filename,
            "stripe_session_id": None, "expires_at": datetime.now() + timedelta(hours=24),
        }
        current_base_url = get_base_url(request)
        return RedirectResponse(url=f"{current_base_url}/results?token={token}", status_code=303)

    raise HTTPException(status_code=401, detail="Please log in or create an account")


# ============================================================
# BATCH UPLOAD
# ============================================================

@app.get("/batch-upload", response_class=HTMLResponse)
async def batch_upload_page(request: Request):
    db = next(get_db())
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
):
    db = next(get_db())
    user = require_user(request, db)

    plan = PLAN_LIMITS.get(user.plan, {"monthly_limit": 0, "batch_max": 1, "playbooks_max": 0})
    if len(files) > plan["batch_max"]:
        raise HTTPException(status_code=400, detail=f"Batch limit is {plan['batch_max']} files on your plan.")

    remaining = user.monthly_limit - user.contracts_this_month
    if len(files) > remaining:
        raise HTTPException(status_code=402, detail=f"Only {remaining} contracts remaining this month.")

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
        ext = os.path.splitext(f.filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            continue

        file_bytes = await f.read()
        if not file_bytes or len(file_bytes) > MAX_UPLOAD_BYTES:
            continue

        try:
            text = extract_text_from_file(file_bytes, f.filename)
            if not text or not text.strip():
                continue
        except Exception:
            continue

        analysis = run_analysis(text)

        deviations = None
        if template_findings:
            comparison = playbook_engine.compare(analysis["findings_dict"], template_findings)
            deviations = comparison

        contract = Contract(
            user_id=user.id, filename=f.filename, contract_text=text,
            overall_risk=analysis["overall_risk"], findings_json=analysis["findings_dict"],
            llm_result_json=analysis["llm_result"], rule_counts_json=analysis["rule_counts"],
            rule_engine_version=analysis["version"], analysis_completed=True,
            playbook_id=playbook_id, deviations_json=deviations, batch_id=batch_id,
        )
        db.add(contract)
        contracts.append(contract)

    user.contracts_this_month += len(contracts)
    db.commit()

    for c in contracts:
        db.refresh(c)

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
        if sev == "high":
            all_categories[cat] = "FAIL"
        elif sev == "medium" and all_categories.get(cat) != "FAIL":
            all_categories[cat] = "WARNING"
    return dict(sorted(all_categories.items()))


# ============================================================
# VIEW SINGLE CONTRACT
# ============================================================

@app.get("/contract/{contract_id}", response_class=HTMLResponse)
async def view_contract(request: Request, contract_id: int):
    db = next(get_db())
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    findings_dict = contract.findings_json or []
    llm_result = contract.llm_result_json or {}
    all_issues = build_enhanced_issues(findings_dict, llm_result)
    rule_counts = contract.rule_counts_json or {"high": 0, "medium": 0, "low": 0}

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
        "findings_count": len(findings_dict),
        "rule_counts": rule_counts,
        "rule_engine_version": contract.rule_engine_version or "2.0.0",
        "current_year": datetime.now().year,
        "token": None,
        "contract_id": contract.id,
        "deviations": contract.deviations_json,
        "total_rule_count": total_rule_count,
        "rule_categories": rule_categories,
        "findings_dict": findings_dict,
        "analysis_id": f"TR-{contract.created_at.year}-{contract.id:06d}" if contract.created_at else f"TR-2026-{contract.id:06d}",
        "generated_at": contract.created_at.strftime("%Y-%m-%d %I:%M %p UTC") if contract.created_at else "N/A",
    })


# ============================================================
# PDF DOWNLOAD (authenticated)
# ============================================================

@app.get("/contract/{contract_id}/pdf")
async def download_contract_pdf(request: Request, contract_id: int):
    db = next(get_db())
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    findings_dict = contract.findings_json or []
    llm_result = contract.llm_result_json or {}
    all_issues = build_enhanced_issues(findings_dict, llm_result)
    rule_counts = contract.rule_counts_json or {"high": 0, "medium": 0, "low": 0}

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Triage AI - Contract Risk Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"File: {contract.filename}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Date: {datetime.utcnow().strftime('%B %d, %Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Rule Engine: v{contract.rule_engine_version or '2.0.0'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    risk_label = (contract.overall_risk or "low").upper()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Overall Risk: {risk_label}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"High: {rule_counts.get('high', 0)}  |  Medium: {rule_counts.get('medium', 0)}  |  Low: {rule_counts.get('low', 0)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    summary_bullets = llm_result.get("summary_bullets", [])
    if summary_bullets:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for bullet in summary_bullets:
            pdf.multi_cell(0, 5, f"  - {bullet}")
        pdf.ln(4)

    if all_issues:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Findings", new_x="LMARGIN", new_y="NEXT")
        for i, issue in enumerate(all_issues, 1):
            severity = issue.get("severity", "medium").upper()
            title = issue.get("title", "Finding")
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 6, f"{i}. [{severity}] {title}")
            rationale = issue.get("rationale", "")
            if rationale:
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, f"   {rationale}")
            excerpt = issue.get("matched_excerpt", "")
            if excerpt:
                pdf.set_font("Helvetica", "I", 8)
                clean_excerpt = excerpt[:300].encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 4, f'   "{clean_excerpt}"')
            pdf.ln(2)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, f"(c) {datetime.now().year} Triage AI - Contract Risk Intelligence. Not legal advice.", new_x="LMARGIN", new_y="NEXT")

    pdf_bytes = pdf.output()

    safe_name = sanitize_filename(contract.filename)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="TriageAI_{safe_name}_{date_str}.pdf"'},
    )


# ============================================================
# REPORT SHARING
# ============================================================

@app.post("/contract/{contract_id}/share")
async def create_share_link(request: Request, contract_id: int, password: str = Form("")):
    db = next(get_db())
    user = require_user(request, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if not contract.share_token:
        contract.generate_share_token()
    if password:
        contract.share_password_hash = hash_password(password)
    db.commit()

    share_url = f"{get_base_url(request)}/shared/{contract.share_token}"
    return {"share_url": share_url, "token": contract.share_token}


@app.get("/shared/{share_token}", response_class=HTMLResponse)
async def view_shared_report(request: Request, share_token: str):
    db = next(get_db())
    contract = db.query(Contract).filter(Contract.share_token == share_token).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Report not found")

    if contract.share_password_hash:
        return templates.TemplateResponse("shared_report.html", {
            "request": request, "password_required": True, "password_error": False,
            "filename": contract.filename, "current_year": datetime.now().year,
        })

    return _render_shared_report(request, contract)


@app.post("/shared/{share_token}", response_class=HTMLResponse)
async def view_shared_report_auth(request: Request, share_token: str, password: str = Form(...)):
    db = next(get_db())
    contract = db.query(Contract).filter(Contract.share_token == share_token).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Report not found")

    if contract.share_password_hash and not verify_password(password, contract.share_password_hash):
        return templates.TemplateResponse("shared_report.html", {
            "request": request, "password_required": True, "password_error": True,
            "filename": contract.filename, "current_year": datetime.now().year,
        })

    return _render_shared_report(request, contract)


def _render_shared_report(request: Request, contract: Contract) -> HTMLResponse:
    findings_dict = contract.findings_json or []
    llm_result = contract.llm_result_json or {}
    all_issues = build_enhanced_issues(findings_dict, llm_result)
    rule_counts = contract.rule_counts_json or {"high": 0, "medium": 0, "low": 0}

    return templates.TemplateResponse("shared_report.html", {
        "request": request, "password_required": False, "password_error": False,
        "filename": contract.filename,
        "overall_risk": contract.overall_risk,
        "summary_bullets": llm_result.get("summary_bullets", []),
        "top_issues": all_issues,
        "disclaimer": llm_result.get("disclaimer", "This is automated risk triage, not legal advice."),
        "findings_count": len(findings_dict),
        "rule_counts": rule_counts,
        "rule_engine_version": contract.rule_engine_version or "1.0.3",
        "current_year": datetime.now().year,
    })


# ============================================================
# PLAYBOOKS
# ============================================================

@app.get("/playbooks", response_class=HTMLResponse)
async def playbooks_list(request: Request):
    db = next(get_db())
    user = require_user(request, db)
    playbooks = db.query(Playbook).filter(Playbook.user_id == user.id).order_by(Playbook.created_at.desc()).all()
    return templates.TemplateResponse("playbooks.html", {
        "request": request, "user": user, "playbooks": playbooks,
        "current_year": datetime.now().year,
    })


@app.get("/playbooks/new", response_class=HTMLResponse)
async def playbook_new_page(request: Request):
    db = next(get_db())
    user = require_user(request, db)
    plan = PLAN_LIMITS.get(user.plan, {"monthly_limit": 0, "batch_max": 1, "playbooks_max": 0})
    existing = db.query(Playbook).filter(Playbook.user_id == user.id).count()
    if existing >= plan["playbooks_max"]:
        return RedirectResponse(url="/playbooks", status_code=302)
    return templates.TemplateResponse("playbook_form.html", {
        "request": request, "user": user, "playbook": None, "error": None,
        "current_year": datetime.now().year,
    })


@app.post("/playbooks/new")
async def playbook_new_submit(
    request: Request,
    name: str = Form(...),
    contract_type: str = Form(""),
    description: str = Form(""),
    file: UploadFile = File(...),
):
    db = next(get_db())
    user = require_user(request, db)

    if not file.filename:
        return templates.TemplateResponse("playbook_form.html", {
            "request": request, "user": user, "playbook": None,
            "error": "Please upload a template file.", "current_year": datetime.now().year,
        })

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        return templates.TemplateResponse("playbook_form.html", {
            "request": request, "user": user, "playbook": None,
            "error": "Only PDF, DOCX, or TXT files.", "current_year": datetime.now().year,
        })

    file_bytes = await file.read()
    try:
        template_text = extract_text_from_file(file_bytes, file.filename)
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
    db.commit()

    return RedirectResponse(url="/playbooks", status_code=302)


@app.get("/playbooks/{playbook_id}/edit", response_class=HTMLResponse)
async def playbook_edit_page(request: Request, playbook_id: int):
    db = next(get_db())
    user = require_user(request, db)
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return templates.TemplateResponse("playbook_form.html", {
        "request": request, "user": user, "playbook": playbook,
        "error": None, "current_year": datetime.now().year,
    })


@app.post("/playbooks/{playbook_id}/edit")
async def playbook_edit_submit(
    request: Request, playbook_id: int,
    name: str = Form(...), contract_type: str = Form(""),
    description: str = Form(""), file: Optional[UploadFile] = File(None),
):
    db = next(get_db())
    user = require_user(request, db)
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    playbook.name = name.strip()
    playbook.contract_type = contract_type.strip() or None
    playbook.description = description.strip() or None

    if file and file.filename:
        ext = os.path.splitext(file.filename.lower())[1]
        if ext in ALLOWED_EXTENSIONS:
            file_bytes = await file.read()
            try:
                template_text = extract_text_from_file(file_bytes, file.filename)
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
    return RedirectResponse(url="/playbooks", status_code=302)


@app.post("/playbooks/{playbook_id}/delete")
async def playbook_delete(request: Request, playbook_id: int):
    db = next(get_db())
    user = require_user(request, db)
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id, Playbook.user_id == user.id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    db.delete(playbook)
    db.commit()
    return RedirectResponse(url="/playbooks", status_code=302)


# ============================================================
# PRICING PAGE
# ============================================================

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    db = next(get_db())
    user = get_current_user(request, db)
    return templates.TemplateResponse("pricing.html", {
        "request": request, "user": user, "plans": PLAN_LIMITS,
        "current_year": datetime.now().year,
    })


# ============================================================
# STRIPE SUBSCRIPTION
# ============================================================

@app.post("/subscribe/{plan}")
async def subscribe(request: Request, plan: str):
    db = next(get_db())
    user = require_user(request, db)

    if plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    plan_config = PLAN_LIMITS[plan]

    if DEV_MODE:
        user.plan = plan
        user.monthly_limit = plan_config["monthly_limit"]
        user.subscription_status = "active"
        user.contracts_this_month = 0
        db.commit()
        return RedirectResponse(url="/dashboard", status_code=302)

    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    current_base_url = get_base_url(request)
    is_one_time = plan_config["price_type"] == "one_time"

    line_item = {
        "price_data": {
            "currency": "usd",
            "product_data": {"name": f"Triage AI — {plan.title()} Plan"},
            "unit_amount": plan_config["price"],
        },
        "quantity": 1,
    }
    if not is_one_time:
        line_item["price_data"]["recurring"] = {"interval": "month"}

    checkout = stripe.checkout.Session.create(
        mode="payment" if is_one_time else "subscription",
        payment_method_types=["card"],
        customer_email=user.email,
        client_reference_id=str(user.id),
        line_items=[line_item],
        success_url=f"{current_base_url}/dashboard?upgraded=true",
        cancel_url=f"{current_base_url}/pricing",
        metadata={"plan": plan, "user_id": str(user.id)},
    )
    return RedirectResponse(url=checkout.url, status_code=303)


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
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

    db = next(get_db())

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

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                user.plan = "none"
                user.monthly_limit = 0
                user.subscription_status = "canceled"
                db.commit()

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


@app.get("/demo", response_class=HTMLResponse)
async def demo_analysis(request: Request):
    """Free demo: pre-loaded sample contract analysis, no account needed."""
    analysis = run_analysis(DEMO_CONTRACT)
    all_issues = build_enhanced_issues(analysis["findings_dict"], analysis["llm_result"])

    findings_objs = [type('F', (), {"rule_id": f["rule_id"]})() for f in analysis["findings_dict"]]
    rule_based_sections = rule_engine.build_missing_sections(findings_objs)

    return templates.TemplateResponse("results.html", {
        "request": request, "user": None,
        "filename": "Sample NDA (Demo)",
        "overall_risk": analysis["overall_risk"],
        "summary_bullets": analysis["llm_result"].get("summary_bullets", []),
        "top_issues": all_issues,
        "possible_missing_sections": rule_based_sections[:6],
        "disclaimer": "This is a demo using a sample contract. Sign up to analyze your own contracts.",
        "findings_count": len(analysis["findings_dict"]),
        "rule_counts": analysis["rule_counts"],
        "rule_engine_version": analysis["version"],
        "current_year": datetime.now().year,
        "token": None, "contract_id": None, "deviations": None,
        "is_demo": True,
    })


# ============================================================
# LEGACY ROUTES (anonymous/token-based)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = next(get_db())
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("index.html", {
        "request": request, "current_year": datetime.now().year,
        "dev_mode": DEV_MODE, "user": None, "playbooks": [],
    })


@app.get("/config")
async def get_config():
    return {"dev_mode": DEV_MODE, "stripe_enabled": not DEV_MODE and bool(STRIPE_SECRET_KEY)}


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

    return templates.TemplateResponse("results.html", {
        "request": request, "user": None,
        "filename": entry.get("filename", "document"),
        "overall_risk": analysis["overall_risk"],
        "summary_bullets": analysis["llm_result"].get("summary_bullets", []),
        "top_issues": all_issues,
        "possible_missing_sections": all_missing[:6],
        "disclaimer": analysis["llm_result"].get("disclaimer", "This is automated risk triage, not legal advice."),
        "findings_count": len(analysis["findings_dict"]),
        "rule_counts": analysis["rule_counts"],
        "rule_engine_version": analysis["version"],
        "current_year": datetime.now().year,
        "token": token, "contract_id": None, "deviations": None,
    })
