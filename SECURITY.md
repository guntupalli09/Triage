# Security

This document describes TriageCounsel's security posture and how to report
a vulnerability. It reflects the implementation as of the security
hardening pass tracked in this repository's git history (see commits
tagged with `security:` prefixes) — every control described below is
backed by code and tests in this repo, not aspirational.

For a deeper architectural threat analysis, see [`THREAT_MODEL.md`](THREAT_MODEL.md).
For data handling specifics, see [`PRIVACY.md`](PRIVACY.md).
For the AI/LLM security boundary specifically, see [`LLM_BOUNDARY.md`](LLM_BOUNDARY.md).
For current SOC 2 readiness, see [`SOC2_ROADMAP.md`](SOC2_ROADMAP.md).

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately
rather than opening a public GitHub issue. Contact the maintainer directly
with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept code/requests if applicable)
- Any suggested remediation

We aim to acknowledge reports within a reasonable timeframe and will keep
you informed as the issue is investigated and resolved. Please give us a
reasonable window to remediate before any public disclosure.

## Implemented Controls

### Authentication & Session Management
- Passwords hashed with PBKDF2-HMAC-SHA256 (100,000 iterations), random
  16-byte salt per password, constant-time verification (`auth.py`).
- Google OAuth (OIDC) sign-in with full RS256 signature verification
  against Google's published JWKS (`google_oauth.py`) — not just claim
  checks.
- Server-side sessions (Redis-backed, in-memory fallback in dev), opaque
  random tokens, `HttpOnly`, `SameSite=Lax` cookies, `Secure` flag on by
  default outside `DEV_MODE`.
- Production startup refuses to run with default/weak
  `SESSION_SECRET`/`APP_HMAC_SECRET` (`main.py`).
- Opt-in TOTP multi-factor authentication (`mfa.py`) — standard 6-digit
  authenticator-app codes (RFC 6238), single-use SHA-256-hashed recovery
  codes (never stored in plaintext), enrollment requires confirming a live
  code before it's enabled, and disabling requires re-entering the account
  password. The MFA secret itself is encrypted at rest
  (`User.mfa_secret`, `EncryptedText`). Not enforced for any account,
  including admin — enabling it is each user's choice.

### Authorization
- Every user-owned resource (contracts, playbooks) is queried scoped by
  both resource ID and `user_id` — cross-tenant access returns 404, not
  a resource-existence leak.
- Admin access is role-based (RBAC — `rbac.py`, `models.py`: `Role`,
  `Permission`, `UserRole`), not a hardcoded email. Managed via
  `manage_roles.py`.
- Failed authorization attempts are audit-logged.

### CSRF Protection
- Synchronizer token via an `HttpOnly` cookie (`csrf.py`), validated on
  every state-changing form POST. The Stripe webhook is the sole,
  deliberate exemption (authenticated by Stripe's own request signature).

### Rate Limiting
- Redis-backed (in-memory fallback), per-route + per-IP fixed-window
  limits on login, registration, password reset, share-link password
  checks, and uploads (`rate_limit.py`).

### Security Headers
- CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy`, `Permissions-Policy`, and HSTS (once `SECURE_COOKIES`
  confirms the deployment is HTTPS) on every response (`security_headers.py`).

### Encryption at Rest
- Contract text and playbook template text are encrypted with AES-256-GCM,
  a fresh random 96-bit nonce per write, versioned envelope for key
  rotation, fail-closed decryption on tampered/malformed ciphertext
  (`encryption.py`). Production startup validates key configuration.
- Retired keys stay decrypt-only; `backfill_encryption.py` re-encrypts any
  legacy plaintext rows on an operator's own schedule.

### Upload Hardening
- Filename sanitization (path traversal stripped regardless of host OS),
  magic-byte/content validation, zip-bomb and PDF-bomb size/ratio guards,
  and a pluggable malware-scanning interface (no-op by default; ClamAV
  supported via `MALWARE_SCANNER=clamd` — see
  `docs/security/upload_hardening_infra.md`) (`upload_security.py`).

### LLM / Prompt Injection
- The LLM never receives full contract text — a code-level guard raises if
  it's ever attempted (`evaluator.py`). Only short, rule-matched excerpts
  reach the prompt, and those are length-capped, delimiter-isolated, and
  scanned for injection patterns before being included
  (`prompt_security.py`). See [`LLM_BOUNDARY.md`](LLM_BOUNDARY.md) for the
  full architectural boundary.

### Data Lifecycle
- Per-contract permanent deletion (`POST /contract/{id}/delete`) and full
  account deletion, both audit-logged.
- Optional, off-by-default automatic retention policy
  (`CONTRACT_RETENTION_DAYS`) with scheduled cleanup via CLI (cron/systemd/
  K8s CronJob) or a bearer-token-protected HTTP endpoint (Vercel Cron) —
  see `docs/security/data_retention_infra.md`.

### Audit Logging
- An append-only `audit_logs` table (`models.py: AuditLog`) records login/
  logout, account creation/deletion, uploads, exports, playbook changes,
  share-link creation/access/revocation, admin access (granted and
  denied), and retention cleanup runs — actor, target, IP, user agent,
  and outcome for each.

### Share Links
- Optional expiry, optional max-view count, explicit revocation
  (non-destructive — re-shareable), and every access attempt (success or
  failure, with reason) is audit-logged.

## Known Limitations

- **Malware scanning is off by default** — requires operator setup of a
  ClamAV daemon. See `docs/security/upload_hardening_infra.md`.
- **No process-level CPU-timeout sandboxing** for document parsing — see
  the same doc's "Process-level sandboxing" section for the residual risk
  and mitigation options.
- **JSON-column fields beyond contract text are not yet encrypted at
  rest** (`findings_json`, `llm_result_json`, etc. can contain short
  contract excerpts). See `SOC2_ROADMAP.md` for the planned follow-up.
- **Admin dashboard has a pre-existing, unrelated SQLite date-grouping
  bug** under real usage data — see `docs/security/known_issues.md`. Not
  a security issue but affects operational reliability.
- **Infrastructure-level controls are documented, not implemented by this
  application**: TLS termination, database/disk encryption, backups,
  network firewalls, and CI/CD security gates are the deploying
  organization's responsibility — see `SOC2_ROADMAP.md` for the specific
  checklist.
