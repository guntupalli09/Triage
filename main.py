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
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

# Load environment variables FIRST, before any other imports that might use them
from dotenv import load_dotenv

# Resolve .env file path relative to this script's directory (works from any CWD)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    # Handle BOM (Byte Order Mark) issue: strip BOM from .env file before loading
    # BOM can cause variable names to have \ufeff prefix, breaking lookups
    try:
        with open(env_path, 'r', encoding='utf-8-sig') as f:
            # utf-8-sig automatically strips BOM
            content = f.read()
        # Write back without BOM
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # Note: logger not initialized yet, will log later
        _bom_stripped = True
    except Exception as e:
        # Note: logger not initialized yet, will log later
        _bom_stripped = False
        _bom_error = str(e)
    
    load_dotenv(dotenv_path=env_path, override=False)
else:
    # Fallback to default load_dotenv() behavior (searches current working directory)
    load_dotenv(override=False)
    _bom_stripped = None

import stripe
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from PyPDF2 import PdfReader
from docx import Document

from rules_engine import RuleEngine
from evaluator import LLMEvaluator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Log BOM removal status (if it happened)
if '_bom_stripped' in globals():
    if _bom_stripped:
        logger.info("Stripped BOM from .env file")
    elif '_bom_error' in globals():
        logger.warning(f"Could not process .env file for BOM removal: {_bom_error}")

# Log .env file location for debugging (after logger initialization)
if env_path.exists():
    logger.info(f"Environment loaded from: {env_path}")
    # Diagnostic: Check .env file contents for OPENAI_API_KEY (without exposing values)
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
        openai_lines = [line.strip() for line in env_lines if 'OPENAI' in line.upper() and not line.strip().startswith('#')]
        if openai_lines:
            logger.info(f"Found {len(openai_lines)} OPENAI-related line(s) in .env file")
            for line in openai_lines:
                # Show the line structure but mask the actual key value
                if '=' in line:
                    var_name, var_value = line.split('=', 1)
                    var_name = var_name.strip()
                    var_value = var_value.strip()
                    # Remove quotes if present (common .env mistake)
                    if var_value.startswith('"') and var_value.endswith('"'):
                        var_value = var_value[1:-1]
                        logger.info(f"  {var_name} has quotes around value (will be handled)")
                    elif var_value.startswith("'") and var_value.endswith("'"):
                        var_value = var_value[1:-1]
                        logger.info(f"  {var_name} has single quotes around value (will be handled)")
                    # Show first 7 chars (sk-xxxxx) and length, but not full key
                    if var_value:
                        masked = var_value[:7] + "..." + f" (length={len(var_value)})"
                        logger.info(f"  {var_name} = {masked}")
                    else:
                        logger.warning(f"  {var_name} = (EMPTY VALUE)")
                else:
                    logger.warning(f"  Line format issue (no '=' found): {line[:50]}...")
        else:
            logger.warning("No OPENAI-related lines found in .env file")
    except Exception as e:
        logger.warning(f"Could not read .env file for diagnostics: {e}")
else:
    logger.info(f".env file not found at {env_path}, using default search path")

# Check os.environ directly after load_dotenv (diagnostic)
all_openai_env_vars = {k: "***" for k in os.environ.keys() if 'OPENAI' in k.upper()}
if all_openai_env_vars:
    logger.info(f"OPENAI variables in os.environ after load_dotenv: {list(all_openai_env_vars.keys())}")
else:
    logger.warning("No OPENAI variables found in os.environ after load_dotenv()")

# Validate OpenAI API key availability (before LLMEvaluator instantiation)
# Handle BOM issue: try both with and without BOM prefix
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Try with BOM prefix (common issue on Windows)
    OPENAI_API_KEY = os.getenv("\ufeffOPENAI_API_KEY")
    if OPENAI_API_KEY:
        logger.info("Found OPENAI_API_KEY with BOM prefix - using it (BOM should be stripped from .env file)")

# Debug: Check all environment variables that start with OPENAI
openai_vars = {k: v for k, v in os.environ.items() if k.upper().replace('\ufeff', '').startswith("OPENAI")}
if openai_vars:
    logger.info(f"Found OPENAI-related env vars: {list(openai_vars.keys())}")
else:
    logger.info("No OPENAI-related environment variables found")
if OPENAI_API_KEY:
    # Strip whitespace and validate it's not empty
    original_length = len(OPENAI_API_KEY)
    OPENAI_API_KEY = OPENAI_API_KEY.strip()
    if OPENAI_API_KEY:
        logger.info("OpenAI API key detected (length=%d, after strip=%d) - LLM evaluation enabled", 
                   original_length, len(OPENAI_API_KEY))
    else:
        logger.warning("OpenAI API key is empty after stripping whitespace - LLM will be disabled")
        OPENAI_API_KEY = None
else:
    # Enhanced debugging: Check for common naming variations
    variations = ["OPENAI_KEY", "OPENAI_APIKEY", "OPENAIAPIKEY", "OPENAI_API_KEY"]
    found_variations = [v for v in variations if os.getenv(v)]
    if found_variations:
        logger.warning(f"OPENAI_API_KEY not found, but found variations: {found_variations}")
    logger.warning("OpenAI API key NOT detected in environment - LLM will be disabled (fallback mode)")
    logger.info("Tip: Ensure .env file contains: OPENAI_API_KEY=sk-your-key-here (no quotes, no spaces around =)")

APP_HMAC_SECRET = os.getenv("APP_HMAC_SECRET", "dev_secret_change_me")

# BASE_URL: Read from environment, strip trailing slash, with safe defaults
BASE_URL_RAW = os.getenv("BASE_URL", "").strip()
if BASE_URL_RAW:
    BASE_URL = BASE_URL_RAW.rstrip("/")
else:
    # Safe default: allow localhost only if BASE_URL is missing (for local dev)
    BASE_URL = "http://localhost:8000"
    logger.warning(
        "BASE_URL not set in environment. Using localhost default. "
        "This will break on mobile/external devices. Set BASE_URL for production."
    )

# Development mode: bypasses Stripe payment for testing
# Production-safe default: missing DEV_MODE = False (production mode)
DEV_MODE_RAW = os.getenv("DEV_MODE", "false").strip().lower()
DEV_MODE = DEV_MODE_RAW in ("true", "1", "yes")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# REQUIRED startup log to prevent confusion
logger.info(f"Application started in DEV_MODE={DEV_MODE} (from env: '{DEV_MODE_RAW}')")
logger.info(f"Application BASE_URL set to: {BASE_URL}")
logger.info(f"BASE_URL will be used for all redirects (Stripe success/cancel URLs and internal redirects)")

# Warn if BASE_URL is localhost in production mode (but don't crash)
if BASE_URL.startswith("http://localhost") or BASE_URL.startswith("https://localhost"):
    if not DEV_MODE:
        logger.warning(
            "BASE_URL is set to localhost but DEV_MODE=false. "
            "This will break on mobile/external devices. Set BASE_URL to your public URL."
        )

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

    # DEV_MODE=true: DEMO/DEV MODE → SKIP Stripe payment
    logger.info(f"Upload endpoint: DEV_MODE={DEV_MODE}, checking payment requirement...")
    if DEV_MODE:
        redirect_url = f"{BASE_URL}/results?token={token}"
        logger.info(f"DEV_MODE enabled: bypassing Stripe payment - redirecting to: {redirect_url}")
        session_store[app_session_id] = {
            "paid": True,  # Mark as paid in dev mode
            "text": contract_text,
            "filename": file.filename,
            "stripe_session_id": None,
            "expires_at": datetime.now() + timedelta(hours=24),
        }
        return RedirectResponse(url=redirect_url, status_code=303)

    # DEV_MODE=false: PRODUCTION MODE → REQUIRE Stripe payment
    logger.info("DEV_MODE=false: Production mode - requiring Stripe payment")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured. Required in production mode.")

    # Create Stripe Checkout Session and map it back via client_reference_id
    success_url = f"{BASE_URL}/results?token={token}"
    cancel_url = f"{BASE_URL}/"
    logger.info(f"Creating Stripe checkout with success_url: {success_url}, cancel_url: {cancel_url}")
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
                            "description": "One-time risk triage before you sign.",
                        },
                        "unit_amount": 1900,  # $19.00
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
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
    # DEV_MODE=false: Require payment confirmation before showing results
    # DEV_MODE=true: Skip payment check (already marked as paid in upload endpoint)
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

        # Calculate statistics from deduplicated findings (already deduplicated in rule_engine.analyze)
        # Use the counts from the analysis result to ensure consistency
        rule_counts = analysis.get("rule_counts", {"high": 0, "medium": 0, "low": 0})
        
        # ✅ VERIFICATION 5: Output-level verification (UI proof)
        # Every top_issue.title in llm_result must correspond to a deterministic rule_id
        # If you see an issue not in "Detected Risk Indicators" or new risks in summary → bug
        # The template displays:
        #   - "Detected Risk Indicators" section (from top_issues)
        #   - Executive summary (from summary_bullets)
        #   - Statistics (from findings_count and rule_counts)
        # All must map back to deterministic findings only

        # Build complete list of ALL findings (not just LLM-selected top_issues)
        # Map LLM explanations to findings, but include ALL findings even if LLM didn't select them
        findings_lookup = {}
        for finding in findings_dict:
            key = finding.get("rule_name", "")
            if key not in findings_lookup:
                findings_lookup[key] = []
            findings_lookup[key].append(finding)
        
        # Create a map of LLM top_issues by title for quick lookup
        llm_issues_map = {}
        for issue in llm_result.get("top_issues", []):
            issue_title = issue.get("title", "").lower()
            llm_issues_map[issue_title] = issue
        
        # Build complete list: start with ALL findings, enhance with LLM explanations where available
        all_enhanced_issues = []
        seen_rule_ids = set()
        
        # Process ALL findings: add LLM enhancements where available, otherwise use raw finding data
        for finding in findings_dict:
            rule_id = finding.get("rule_id", "")
            if rule_id in seen_rule_ids:
                continue
            seen_rule_ids.add(rule_id)
            
            finding_title = finding.get("title", "").lower()
            # Check if LLM provided explanation for this finding
            llm_issue = None
            for llm_title, llm_data in llm_issues_map.items():
                if finding_title in llm_title or llm_title in finding_title:
                    llm_issue = llm_data
                    break
            
            # Build enhanced issue: use LLM explanation if available, otherwise use raw finding
            if llm_issue:
                enhanced_issue = llm_issue.copy()
                # Ensure severity matches the actual finding (rule engine is source of truth)
                enhanced_issue["severity"] = finding.get("severity", llm_issue.get("severity", "low"))
            else:
                # No LLM explanation, create from raw finding
                enhanced_issue = {
                    "title": finding.get("title", ""),
                    "severity": finding.get("severity", "low"),
                    "why_it_matters": finding.get("rationale", "This may indicate increased contractual risk."),
                    "negotiation_consideration": "Commonly negotiated; consider clarifying scope, caps, and mutuality.",
                }
            
            # Always add clause number and keywords from the actual finding
            if finding.get("clause_number"):
                enhanced_issue["clause_number"] = finding.get("clause_number")
            if finding.get("matched_keywords"):
                enhanced_issue["matched_keywords"] = finding.get("matched_keywords")
            
            all_enhanced_issues.append(enhanced_issue)
        
        # Sort by severity (high first) to match user expectation
        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_enhanced_issues.sort(key=lambda x: (severity_order.get(x.get("severity", "low"), 9), x.get("title", "")))

        # Build rule-based missing sections recommendations
        # Combine deterministic recommendations with LLM suggestions (deterministic takes priority)
        rule_based_sections = rule_engine.build_missing_sections(findings)
        llm_sections = llm_result.get("possible_missing_sections", [])
        # Merge: rule-based first, then unique LLM suggestions (avoid duplicates)
        all_missing_sections = rule_based_sections.copy()
        for llm_section in llm_sections:
            # Simple deduplication: check if similar text already exists
            if not any(llm_section.lower() in existing.lower() or existing.lower() in llm_section.lower() 
                      for existing in all_missing_sections):
                all_missing_sections.append(llm_section)
        # Limit to 6 total
        all_missing_sections = all_missing_sections[:6]

        # Render results
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "filename": entry.get("filename", "document"),
                "overall_risk": llm_result.get("overall_risk", overall_risk),
                "summary_bullets": llm_result.get("summary_bullets", []),
                "top_issues": all_enhanced_issues,  # Show ALL findings, not just LLM-selected ones
                "possible_missing_sections": all_missing_sections,
                "disclaimer": llm_result.get("disclaimer", "This is automated risk triage, not legal advice."),
                "findings_count": len(findings_dict),
                "rule_counts": rule_counts,
                "rule_engine_version": analysis.get("version", "1.0.3"),
            },
        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")
