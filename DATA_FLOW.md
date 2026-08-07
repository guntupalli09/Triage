# Data Flow

How a contract moves through TriageCounsel, from upload to storage to
(optional) AI explanation to export/deletion. See `SECURITY.md` for the
controls referenced at each step and `LLM_BOUNDARY.md` for the AI-specific
detail.

## 1. Upload

```
Browser --(multipart POST, CSRF-protected, rate-limited)--> /upload
    │
    ▼
file_bytes = await file.read()               # in memory only, never written to disk
    │
    ▼
upload_security.sanitize_filename()           # strip path traversal, control chars
    │
    ▼
extract_text_from_file(file_bytes, filename)
    ├── upload_security.validate_magic_bytes()      # content must match claimed extension
    ├── upload_security.scan_for_malware()           # no-op by default; ClamAV if configured
    ├── (.docx) upload_security.validate_docx_zip_safety()   # zip-bomb guard
    ├── (.pdf)  upload_security.validate_pdf_page_count()    # PDF-bomb guard
    └── returns extracted plaintext, capped at ~20MB
    │
    ▼
contract_text (Python string, in memory)
```

The original file bytes are discarded after extraction — never persisted
to disk or object storage.

## 2. Deterministic Analysis

```
contract_text
    │
    ▼
rules_engine.analyze(contract_text)
    │
    ├── findings (rule_id, matched_excerpt, severity, rationale, ...)
    ├── overall_risk (low/medium/high)
    ├── risk_dashboard, structure_report, clause_quality, metadata, risk_balance
    └── (all deterministic — no LLM call yet)
```

This step never leaves the process. No network call, no third party.

## 3. AI Explanation (optional, bounded)

```
findings (metadata only — rule_name, title, severity, rationale, matched_excerpt)
    │
    ▼
evaluator.LLMEvaluator.evaluate(findings, overall_risk)
    │  [HARD GUARD: raises if contract_text is ever passed here]
    │
    ▼
evaluator._build_prompt()
    ├── prompt_security.sanitize_excerpt_for_prompt() per excerpt
    │     (truncate → 300 chars, injection-pattern check → withhold if matched)
    └── prompt_security.wrap_excerpt() — delimiter isolation
    │
    ▼
OpenAI API (HTTPS)  ── receives: overall_risk label + bounded excerpts + rule metadata
    │                  NEVER receives: full contract_text
    ▼
LLM JSON response (summary_bullets, top_issues, possible_missing_sections)
    │
    ▼
result["overall_risk"] = overall_risk   # code overwrites whatever the model returned
    │
    ▼
_verify_output_maps_to_findings()   # logs a warning if an issue doesn't trace to a real finding
```

If `OPENAI_API_KEY` is unset, or the API call fails, this step is skipped
entirely and `create_fallback_response()` produces a rules-only summary
with no fabricated analysis — the deterministic findings are unaffected
either way.

## 4. Persistence

```
Contract(
    contract_text=...,          # → encryption.EncryptedText → AES-256-GCM envelope in DB
    findings_json=...,          # plaintext JSON (not yet encrypted — see SOC2_ROADMAP.md)
    llm_result_json=...,        # plaintext JSON
    risk_dashboard_json=...,    # plaintext JSON
    ...
)
    │
    ▼
PostgreSQL (prod) / SQLite (dev)
```

`contract_text` and (for playbooks) `template_text` are the only two
fields with application-level encryption at rest today.

## 5. Read Paths (review page, PDF export, negotiation package, share links)

```
DB row
    │
    ▼
encryption.EncryptedText.process_result_value()   # transparent decrypt on load
    │
    ▼
contract.contract_text (plain string, in memory for this request only)
    │
    ├──> /contract/{id}/review          (owner only, user_id-scoped query)
    ├──> /contract/{id}/pdf              (owner only; audit-logged as contract_exported)
    ├──> /contract/{id}/review/package   (owner only; audit-logged as contract_exported)
    └──> /shared/{token}                 (no auth — gated by expiry/revocation/max-views/
                                           optional password; every attempt audit-logged)
```

Every read is scoped to the requesting identity (owner's `user_id`, or a
valid, non-expired, non-revoked share token) — see `THREAT_MODEL.md` T1
and T7.

## 6. Deletion

```
POST /contract/{id}/delete                    (owner-initiated, CSRF-protected)
    OR
retention.run_cleanup()                        (automatic, if CONTRACT_RETENTION_DAYS set)
    │
    ▼
db.delete(contract)   # hard DELETE — not a soft-delete flag
    │
    ├──> cascades to ContractEvent rows (ondelete=CASCADE)
    ├──> share link (share_token etc.) deleted with the row
    └──> audit_log.record_event("contract_deleted" or "contract_auto_deleted")
```

The audit record of the deletion persists even though the contract data
itself does not.

## Cross-Cutting: Every Request

Regardless of which path above a request takes, it passes through (in
this order, see `main.py`'s `app.add_middleware()` calls):

```
CORSMiddleware → AnalyticsMiddleware → RequestIDMiddleware →
SecurityHeadersMiddleware → CSRFCookieMiddleware → route handler
    │                                                    │
    │                                          Depends(rate_limit(...))  (where applied)
    │                                          Depends(csrf_protect)     (state-changing routes)
    │                                          require_user() / require_admin()  (auth)
    ▼
Response, with security headers attached on the way back out
```
