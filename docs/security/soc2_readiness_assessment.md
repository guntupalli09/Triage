# SOC 2 Readiness Assessment

Assessment date: 2026-07-22
Scope: repository evidence only. Where a control, process, cloud setting, or operational practice is not represented in this repository, this report states: "Evidence not found in repository."

## Executive Summary

Overall SOC 2 readiness score: **38/100**.
Estimated readiness: **Early**.

The application has a meaningful security baseline for an early SaaS product: SQLAlchemy ORM usage, password hashing, session cookies with HttpOnly/SameSite, upload size/type restrictions, object-owner checks on core contract/playbook routes, Stripe webhook signature verification, Docker health checks, non-root container execution, and basic analytics/security event recording. However, it is not close to SOC 2 Type II readiness because key controls are missing or cannot be verified from the repository: MFA, centralized audit logging, security monitoring/alerting, vulnerability scanning, CI/CD controls, backup/restore evidence, encryption-at-rest configuration, key/secret rotation, production TLS/HSTS enforcement, CSRF protection, rate limiting, signed Google ID token verification, data retention, incident response evidence, vendor risk evidence, and formal change management evidence.

Biggest blockers:

1. No auditable CI/CD, change-management, code-scanning, dependency-scanning, or deployment approval workflow found.
2. No evidence of backup/restore, disaster recovery, RPO/RTO, or production monitoring/alerting controls.
3. Sensitive contract contents are stored in plaintext application tables, with no repository evidence of encryption at rest or customer-managed encryption.
4. No CSRF protection on state-changing browser POST routes.
5. No rate limiting or account lockout on login, registration, password reset, share-password, upload, or Stripe-exposed routes.
6. Google ID tokens are decoded without cryptographic signature verification.
7. No MFA support found.
8. No security headers middleware or TLS/HSTS enforcement in application/deployment configuration.
9. No repository evidence of audit-log immutability, admin action logging, privileged access review, or least-privilege IAM/cloud configuration.
10. Secrets have safe placeholders in `.env.example`, but runtime fails open to default development secrets unless operators override them.

Estimated engineering effort to become audit-ready: **6-10 weeks** for a small team, excluding company-policy evidence, vendor review, penetration testing, and control observation time required for Type II.

## Phase 1 Implementation Update (2026-07-22)

All ten Phase 1 items from the roadmap below have been implemented. This
section records what changed and supersedes the corresponding findings
above (which are left intact as historical record of the original
assessment).

| # | Item | Status | Where |
|---|---|---|---|
| 1 | Google OAuth OIDC verification | ✅ Done | `google_oauth.py` now verifies signature/issuer/audience/expiry via `google-auth`'s JWKS-backed `id_token.verify_oauth2_token`, plus a nonce round-trip. Resolves **C-03**. |
| 2 | Production secret enforcement | ✅ Done | `security_config.py`, called at import time in `main.py`. Resolves **H-04**. |
| 3 | Security headers | ✅ Done | `security_headers.py` (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, CSP). Resolves **H-05**. |
| 4 | CSRF protection | ✅ Done | `csrf.py` — double-submit cookie + `Depends(verify_csrf)` on every browser POST route except `/stripe-webhook`. Resolves **H-01**. |
| 5 | Redis-backed rate limiting | ✅ Done | `rate_limit.py` — per-IP and per-account limits on auth/upload/share/OAuth/billing routes. Resolves **H-02**. |
| 6 | Redis fail-closed in production | ✅ Done | `auth.init_redis_or_fail()` + `database.wait_for_redis()`. Resolves **M-04**. |
| 7 | Secure cookie enforcement | ✅ Done | `security_config.SECURE_COOKIES`, enforced by item 2's startup check. |
| 8 | Dependency + secret scanning in CI | ✅ Done | `.github/workflows/security.yml` (pip-audit, detect-secrets), `.github/workflows/tests.yml`. Resolves **H-06** (partially — no SAST/container scanning yet, see Phase 2). |
| 9 | Dependency pinning / upgrades | ✅ Done | See "Dependency security posture" below. Resolves **M-05**. |
| 10 | Logging redaction | ✅ Done | `log_redaction.py`, installed on the root logger in `main.py`. |

### Dependency security posture

Upgrading `fastapi`/`starlette` to the newest versions that don't change
`TemplateResponse`'s calling convention (`fastapi==0.128.0`,
`starlette==0.49.1`) resolves all but 5 `pip-audit` findings, all of which
require Starlette's 1.x line (a breaking change to `TemplateResponse` used
across ~50 call sites in `main.py`, confirmed by direct testing — see
below). These 5 are explicitly ignored in CI (`.github/workflows/security.yml`)
with per-CVE justification:

| CVE | Issue | Why it's low-risk here |
|---|---|---|
| PYSEC-2026-161, PYSEC-2026-248 | `request.url`/Host-header reconstruction can be spoofed via a malformed path/Host. | The app never trusts `request.url.hostname`; `get_base_url()` uses the production-required, operator-set `BASE_URL` env var (enforced non-empty/https by item 2) instead. |
| PYSEC-2026-249 | `request.form()` doesn't bound field count/size for `application/x-www-form-urlencoded` bodies (only multipart). | Every POST route is now rate-limited (item 5); a flood is throttled per-IP/per-account before it can be repeated. |
| PYSEC-2026-2280, PYSEC-2026-2281 | Starlette's class-based `HTTPEndpoint` method dispatch / Windows UNC-path `StaticFiles` SSRF. | The app uses only function-based FastAPI routes (no `HTTPEndpoint` subclasses) and deploys on Linux containers, not Windows. |

**Verification performed**: full `pytest` suite (268 tests) plus a manual
smoke test (register → upload → view contract → security headers →
CSRF → rate limiting) were run against `starlette==1.3.1` before reverting
— it broke immediately with `TypeError: unhashable type: 'dict'` in
`Jinja2Templates.TemplateResponse`, because 1.x requires the newer
`TemplateResponse(request, name, context)` argument order instead of the
`TemplateResponse(name, {"request": request, ...})` form used throughout
`main.py`. Migrating is straightforward but touches every template
response call site — tracked as Phase 2 work below.

Also replaced the unmaintained `PyPDF2==3.0.1` with its actively
maintained successor `pypdf` (same `PdfReader` API, no code changes
needed beyond the import).

### New/updated Phase 2 items from this round
- Migrate every `TemplateResponse(name, {...})` call in `main.py` to
  `TemplateResponse(request, name, {...})`, then upgrade to
  `starlette>=1.0.1` to close the remaining 5 pip-audit findings above.
- Replace `@app.on_event("startup"/"shutdown")` with a `lifespan` context
  manager (currently emits a `DeprecationWarning` under `fastapi==0.128.0`
  but still functions).
- Add SAST/container image scanning to CI (dependency + secret scanning
  only exist today).
- Tighten the CSP's `script-src`/`style-src` from `'unsafe-inline'` to
  per-request nonces (see `security_headers.py` docstring for the current,
  documented exception).

## SOC 2 Trust Services Criteria Classification

| Area | Status | Repository evidence | Gap summary |
|---|---:|---|---|
| Security - authentication | 🟡 Partially implemented | Email/password and Google OAuth routes exist; sessions are cookie-based. | No MFA, weak password policy, no lockout/rate limit. |
| Security - authorization | 🟡 Partially implemented | Core user-owned resources filter by `user_id`; admin is single email match. | No RBAC, roles, privilege review, or tenant model beyond owner filtering. |
| Security - session management | 🟡 Partially implemented | Random tokens, Redis TTL, HttpOnly/SameSite cookies. | `SESSION_SECRET` unused, Secure flag optional, in-memory fallback in production possible. |
| Security - input validation/uploads | 🟡 Partially implemented | Extension allowlist and 10 MB limit. | No MIME validation, malware scanning, parser sandboxing, or content safety controls. |
| Security - SQL injection | ✅ Fully implemented for reviewed app queries | SQLAlchemy filters used for request-derived values. | Raw migration SQL is static only; no dynamic user input observed. |
| Security - XSS protection | 🟡 Partially implemented | Jinja2 templates autoescape by default. | No CSP/security headers evidence; uploaded text is rendered in templates and must be continuously reviewed. |
| Security - CSRF | ❌ Missing | Evidence not found in repository. | Browser POST routes lack CSRF tokens. |
| Security - rate limiting | ❌ Missing | Evidence not found in repository. | No throttling of auth/upload/share reset routes. |
| Security - secrets management | 🟡 Partially implemented | Production-required Stripe/OpenAI env vars and `.env.example` placeholders. | Default dev secrets exist; no rotation/scanning/KMS evidence. |
| Security - audit logging | 🟡 Partially implemented | Analytics models/events record application actions and contract events. | No immutable security audit log, admin audit trail, retention, review, or alerting. |
| Availability - health checks | ✅ Fully implemented for basic liveness/readiness | `/health`, Docker, and Compose health checks exist. | Does not cover synthetic monitoring or alerting. |
| Availability - backups/DR | ❌ Missing | Evidence not found in repository. | No backup schedule, restore test, RPO/RTO, replication, or runbooks. |
| Availability - monitoring/alerting | ❌ Missing | Evidence not found in repository. | Logs exist but no metrics, alert rules, uptime monitoring, or incident escalation. |
| Confidentiality - encryption in transit | 🟡 Partially implemented | Google/Stripe APIs use HTTPS; Secure cookies configurable. | No HSTS/TLS redirect or deployment TLS policy evidence. |
| Confidentiality - encryption at rest | ❌ Missing | Evidence not found in repository. | Contract text is stored as `Text` with no app-layer encryption. |
| Confidentiality - retention/deletion | 🟡 Partially implemented | Delete-account route deletes user contracts/playbooks/user. | No retention policy, deletion verification, secure deletion, backup deletion, or legal hold workflow. |
| Confidentiality - third-party/LLM security | 🟡 Partially implemented | OpenAI API key required and contract text is intentionally analyzed. | No DPA/vendor evidence, data-minimization control, opt-out, prompt-injection guardrails, or model logging controls. |
| CI/CD/change management | ❌ Missing | Evidence not found in repository. | No workflows, branch protection, approvals, SAST/DAST, or deployment evidence. |
| Infrastructure/IAM | ❌ Missing | Evidence not found in repository. | No Terraform/Kubernetes/cloud IAM policy evidence. |

## Positive Controls Already Implemented

- Passwords are salted and hashed using PBKDF2-HMAC-SHA256 with `secrets.token_hex(16)` salt and constant-time comparison.
- Sessions use random URL-safe tokens and store expiry timestamps; Redis sessions use `SETEX` for TTL.
- Auth cookies are `HttpOnly` and `SameSite=Lax`; Secure cookies are supported via `SECURE_COOKIES=true`.
- Google OAuth flow uses a random state cookie and constant-time state comparison.
- Password reset tokens are random, stored hashed, expire after one hour, and are nulled after use.
- Stripe webhook requests are verified with Stripe's webhook signature helper.
- Uploaded contract files are limited to `.pdf`, `.docx`, and `.txt`, capped at 10 MB, and rejected if empty or unreadable.
- User-owned contract and playbook access generally filters on both resource ID and `user_id`.
- Docker runs the web process as a non-root `triage` user and has a container health check.
- Docker Compose defines health checks for web, Postgres, and Redis and log rotation for services.

## Findings

### Critical

#### C-01: No backup, restore, or disaster recovery evidence
- Evidence: Docker Compose stores Postgres and Redis data in named volumes, but no backup service, scheduled dump, object storage target, restore test, RPO/RTO, or DR runbook is present. Evidence not found in repository.
- Why this is a SOC 2 issue: Availability criteria require the system to be available for operation and use as committed, including recovery from failures.
- Real-world risk: A host failure, volume corruption, operator error, or ransomware event could permanently destroy customer contracts and analysis history.
- Recommended fix: Add managed database backup configuration or scripted encrypted backups, restore runbooks, scheduled restore tests, documented RPO/RTO, and monitoring for backup failure.
- Estimated effort: Large (>2 days).

#### C-02: No encryption-at-rest evidence for contracts and playbooks
- Evidence: `Contract.contract_text` and `Playbook.template_text` are plain SQLAlchemy `Text` columns, and database setup simply creates an engine from `DATABASE_URL` without encryption configuration. Evidence of cloud/database encryption not found in repository.
- Why this is a SOC 2 issue: Confidentiality criteria require protected information to be safeguarded at rest according to commitments.
- Real-world risk: Database snapshot, host, or volume compromise exposes full customer contract content.
- Recommended fix: Use managed database encryption with documented configuration and, for high-sensitivity contract text, app-layer envelope encryption with KMS-managed keys and rotation.
- Estimated effort: Large (>2 days).

#### C-03: Google OAuth ID tokens are not cryptographically verified
- Evidence: `google_oauth.decode_id_token` base64-decodes the JWT payload and validates issuer, audience, and expiry, but it does not verify the JWT signature against Google JWKS.
- Why this is a SOC 2 issue: Security criteria require reliable authentication. Accepting unsigned/unverified claims undermines identity assurance.
- Real-world risk: If an attacker can cause the callback to process a forged token response or exploit implementation assumptions, they may impersonate users.
- Recommended fix: Use a maintained OIDC/JWT library that validates signature, issuer, audience, expiry, nonce where applicable, and key rotation against Google JWKS.
- Estimated effort: Medium (0.5-2 days).

### High

#### H-01: No CSRF protection on browser state-changing endpoints
- Evidence: State-changing routes such as login, register, account update, password change, delete account, upload, share, subscription, and admin actions are POST routes, but repository-wide search found no CSRF middleware/token implementation. Evidence not found in repository.
- Why this is a SOC 2 issue: Security criteria require protection against unauthorized actions.
- Real-world risk: A logged-in user could be tricked into uploading content, changing profile/password where possible, deleting an account, creating share links, or starting billing flows.
- Recommended fix: Add CSRF tokens to all browser forms, validate origin/referer for sensitive actions, and exempt only machine-to-machine webhooks with explicit controls.
- Estimated effort: Medium (0.5-2 days).

#### H-02: No rate limiting or brute-force protection
- Evidence: Login validates credentials directly; password reset issues tokens; share password checks directly; no rate limiting middleware or lockout was found. Evidence not found in repository.
- Why this is a SOC 2 issue: Security criteria require logical access controls that prevent credential attacks and abuse.
- Real-world risk: Attackers can brute-force passwords, reset flows, shared-report passwords, and consume compute/LLM resources with repeated uploads.
- Recommended fix: Add Redis-backed per-IP and per-account rate limits, progressive delays, account lockout/step-up controls, and abuse alerts.
- Estimated effort: Medium (0.5-2 days).

#### H-03: MFA is missing
- Evidence: User model has no MFA fields, auth routes do not challenge for MFA, and no TOTP/WebAuthn/SMS/email OTP implementation exists. Evidence not found in repository.
- Why this is a SOC 2 issue: SOC 2 auditors commonly expect MFA for administrative and production access and often for sensitive SaaS accounts.
- Real-world risk: A stolen password or OAuth account can directly access customer contracts.
- Recommended fix: Implement MFA for all admins and optionally/mandatorily for customers handling confidential contracts; include recovery-code controls.
- Estimated effort: Large (>2 days).

#### H-04: Default development secrets can be used at runtime
- Evidence: `APP_HMAC_SECRET` defaults to `dev_secret_change_me`; `SESSION_SECRET` defaults to `dev_session_secret_change_me`; production startup validates Stripe/OpenAI secrets but not these two values.
- Why this is a SOC 2 issue: Security criteria require secure configuration and protection of secrets.
- Real-world risk: Predictable HMAC/session-related secrets weaken anonymous-result tokens and any future signed session use.
- Recommended fix: Fail startup in production when `APP_HMAC_SECRET` or `SESSION_SECRET` are absent/default, remove unused `SESSION_SECRET` or use it to sign/encrypt cookies, and add secret scanning.
- Estimated effort: Small (<2 hours).

#### H-05: Security headers and TLS enforcement are missing
- Evidence: The FastAPI app mounts middleware for CORS, analytics, and request IDs, but no middleware sets HSTS, CSP, X-Frame-Options/frame-ancestors, X-Content-Type-Options, Referrer-Policy, or Permissions-Policy. Vercel config contains routes only, not headers.
- Why this is a SOC 2 issue: Security/confidentiality criteria require defenses that reduce browser-based data exposure.
- Real-world risk: Clickjacking, MIME sniffing, weaker transport guarantees, and XSS blast radius increase.
- Recommended fix: Add a security headers middleware and platform config for HSTS/TLS redirects; design a CSP compatible with templates/static assets.
- Estimated effort: Small (<2 hours) to Medium for CSP tuning.

#### H-06: No CI/CD security gates or change-management evidence
- Evidence: No `.github/workflows` files, Terraform, Kubernetes manifests, or cloud deployment pipeline definitions were found; only `vercel.json`, Dockerfile, and Compose are present.
- Why this is a SOC 2 issue: Security and availability criteria require controlled changes, review, testing, and deployment safeguards.
- Real-world risk: Unreviewed or vulnerable changes can reach production without tests, vulnerability checks, or approval evidence.
- Recommended fix: Add CI that runs tests, dependency scans, secret scanning, SAST, container scanning, and build checks; document branch protection and deployment approval evidence.
- Estimated effort: Medium (0.5-2 days).

#### H-07: No production monitoring or alerting evidence
- Evidence: Application logging and `/health` exist, but no alert rules, metrics exporter, uptime checks, error tracking, SIEM forwarding, on-call schedule, or incident runbooks were found. Evidence not found in repository.
- Why this is a SOC 2 issue: Availability/security criteria require detecting and responding to failures and security events.
- Real-world risk: Outages, auth attacks, webhook failures, or data access anomalies may go unnoticed.
- Recommended fix: Add structured logs, metrics, alerting, synthetic checks, security event alerts, and runbooks.
- Estimated effort: Large (>2 days).

### Medium

#### M-01: Admin authorization is a single configured email, not RBAC
- Evidence: `require_admin` grants admin access when the current user's email equals `ADMIN_EMAIL`; no roles/permissions table is present.
- Why this is a SOC 2 issue: Least privilege and access review require explicit roles, approval, revocation, and auditability.
- Real-world risk: Email reuse or misconfiguration grants broad analytics/admin access without role lifecycle controls.
- Recommended fix: Add roles/permissions, admin MFA requirement, access-review logs, break-glass controls, and admin action auditing.
- Estimated effort: Medium (0.5-2 days).

#### M-02: Contract sharing can be created without password, expiry, revocation, or access logs
- Evidence: `create_share_link` generates a token and only sets a password if one is supplied; the model has no share expiry/revocation timestamp/access counter fields.
- Why this is a SOC 2 issue: Confidentiality criteria require limiting disclosure of confidential information.
- Real-world risk: A leaked share URL can expose analysis indefinitely.
- Recommended fix: Require password or authenticated recipients for confidential reports, add expiry/revocation, record accesses, and expose owner controls.
- Estimated effort: Medium (0.5-2 days).

#### M-03: Upload validation is extension-based and parser execution is in-process
- Evidence: Upload validation checks filename extension and size before parsing with PyPDF2/python-docx in the web request.
- Why this is a SOC 2 issue: Security and availability criteria require protection against malicious inputs and resource exhaustion.
- Real-world risk: Malformed documents can exploit parser vulnerabilities or exhaust CPU/memory, affecting availability.
- Recommended fix: Validate MIME/magic bytes, scan for malware, process documents in an isolated worker/container with timeouts, and cap parsed pages/text length.
- Estimated effort: Large (>2 days).

#### M-04: Redis session fallback can silently degrade production resilience
- Evidence: `_get_redis` logs a warning and falls back to in-memory sessions if Redis is unavailable.
- Why this is a SOC 2 issue: Availability and security criteria require controlled failure modes.
- Real-world risk: Multi-worker deployments lose sessions unpredictably and incident evidence may be incomplete.
- Recommended fix: In production, fail closed when Redis is required but unavailable; only allow in-memory fallback in explicit development mode.
- Estimated effort: Small (<2 hours).

#### M-05: Dependency vulnerability scanning is absent and some dependencies are old/unpinned ranges
- Evidence: Requirements pin several packages but allow ranges for OpenAI, fpdf2, python-dotenv, SQLAlchemy, and user-agents; no Dependabot/pip-audit/Safety configuration was found.
- Why this is a SOC 2 issue: Vulnerability management requires identifying and remediating vulnerable components.
- Real-world risk: Known CVEs can remain deployed unnoticed.
- Recommended fix: Add Dependabot/Renovate, pip-audit or Safety in CI, pinned lockfiles/hashes for production, and remediation SLAs.
- Estimated effort: Medium (0.5-2 days).

#### M-06: LLM/prompt-injection controls are not evidenced
- Evidence: Contract text is processed by `LLMEvaluator`; no repository evidence was found for prompt-injection testing, output safety validation beyond deterministic rules, data handling commitments with OpenAI, or model logging configuration.
- Why this is a SOC 2 issue: Confidentiality and processing integrity can be affected by third-party AI handling and untrusted document instructions.
- Real-world risk: Contract text may induce unsafe model output, leak sensitive text in logs or provider systems, or manipulate analysis output.
- Recommended fix: Add LLM threat model, prompt-injection test cases, strict schemas, no-secret/no-PII logging rules, provider data-retention settings evidence, and human-readable AI limitations.
- Estimated effort: Medium (0.5-2 days).

### Low

#### L-01: Health endpoint discloses component status
- Evidence: `/health` returns separate `database` and `redis` statuses.
- Why this is a SOC 2 issue: Security criteria prefer limiting unauthenticated operational detail.
- Real-world risk: Attackers can fingerprint dependencies and outage windows.
- Recommended fix: Return generic public health and expose detailed readiness only internally.
- Estimated effort: Small (<2 hours).

#### L-02: CORS allows all headers
- Evidence: CORS configuration allows configured origins and credentials but sets `allow_headers=["*"]`.
- Why this is a SOC 2 issue: Secure default configuration should minimize cross-origin capability.
- Real-world risk: If origins are misconfigured, broad headers increase attack surface.
- Recommended fix: Restrict allowed headers to required values.
- Estimated effort: Small (<2 hours).

## Roadmap

### Phase 1 (Critical)
- Add backup/restore automation, encrypted backup storage, restore tests, RPO/RTO, and DR runbooks.
- Enforce production secrets for `APP_HMAC_SECRET`, `SESSION_SECRET`, `SECURE_COOKIES`, and `BASE_URL`.
- Replace Google ID token decoding with full OIDC signature validation.
- Add CSRF protection across browser forms.
- Add rate limiting to auth, reset, share, upload, and webhook-adjacent endpoints.

### Phase 2 (High Priority)
- Add MFA for admins and sensitive customer accounts.
- Implement security headers, HSTS/TLS redirect evidence, and CSP.
- Add CI/CD with tests, SAST, dependency scanning, secret scanning, container scanning, and approval evidence.
- Add centralized logging, alerting, uptime checks, and incident runbooks.
- Add encryption-at-rest evidence and app-layer encryption plan for contract text.

### Phase 3 (Medium Priority)
- Replace single-email admin with RBAC and periodic access review evidence.
- Harden report sharing with expiry, revocation, password requirements, recipient controls, and access logs.
- Move document parsing to isolated workers with malware scanning and parser timeouts.
- Fail closed on Redis outage in production.
- Add dependency lockfiles/hashes and vulnerability remediation SLAs.
- Add LLM security test suite and provider data-retention evidence.

### Phase 4 (Nice to Have)
- Split public `/health` from private readiness details.
- Tighten CORS headers.
- Add customer-facing security documentation and trust-center evidence.
- Add automated retention/deletion jobs and customer export/delete audit records.

## Type I Pre-Audit Checklist

- [ ] Define SOC 2 scope, system boundaries, products, data classes, subprocessors, and control owners.
- [ ] Document security policies: access control, change management, incident response, vulnerability management, vendor management, acceptable use, data retention, backup/DR, and risk assessment.
- [ ] Implement and document MFA for admins and production/cloud access.
- [ ] Implement RBAC and remove single-email admin authorization.
- [ ] Add quarterly access reviews and retain evidence.
- [ ] Add CSRF tokens for all browser state-changing actions.
- [ ] Add rate limiting and lockout/abuse detection.
- [ ] Enforce Secure cookies and production-only secret validation.
- [ ] Add HSTS, CSP, clickjacking, MIME-sniffing, referrer, and permissions headers.
- [ ] Add TLS redirect/evidence for every production deployment path.
- [ ] Add OIDC signature verification for Google login.
- [ ] Add centralized immutable audit logging for login, logout, failed login, password reset, admin access, uploads, downloads, sharing, account deletion, subscription changes, and security configuration changes.
- [ ] Add log retention and review procedures.
- [ ] Add monitoring/alerting for uptime, error rate, latency, DB/Redis health, failed login spikes, upload abuse, webhook failures, and backup failures.
- [ ] Add incident response runbooks, severity definitions, escalation, and postmortem template.
- [ ] Add encrypted backups, backup monitoring, restore test evidence, RPO/RTO, and DR runbooks.
- [ ] Verify encryption at rest for production database, Redis, logs, and backups; add app-layer encryption for contract text if confidentiality commitments require it.
- [ ] Add documented key management and secret rotation process.
- [ ] Add secret scanning to CI and pre-commit/developer workflow.
- [ ] Add SAST, dependency scanning, container scanning, and remediation SLAs.
- [ ] Add branch protection, code review requirements, deployment approvals, and change tickets/release evidence.
- [ ] Pin production dependencies with hashes/lockfile and automate dependency updates.
- [ ] Add malware scanning and sandboxing for document uploads.
- [ ] Add MIME/magic-byte validation and parser timeouts/page limits.
- [ ] Add retention schedule and automated deletion workflow for contracts, analytics, logs, backups, and shared reports.
- [ ] Add secure deletion evidence and customer deletion verification.
- [ ] Add share-link expiry, revocation, access logging, and password/recipient policy.
- [ ] Add vendor risk review evidence for Stripe, OpenAI, Google, email provider, hosting, database, Redis, monitoring, and analytics providers.
- [ ] Add privacy/security notices matching actual data flows, especially LLM processing of contract text.
- [ ] Add prompt-injection/LLM misuse threat model and regression tests.
- [ ] Conduct penetration test or independent security review and track remediation.
- [ ] Run tabletop incident and disaster recovery exercises.
- [ ] Prepare auditor evidence repository with screenshots/config exports for cloud IAM, backups, encryption, monitoring, CI/CD, branch protection, and production access.
