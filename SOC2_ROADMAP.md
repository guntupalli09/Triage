# SOC 2 Roadmap

Current control posture and the remaining path to SOC 2 readiness. This
supersedes the assessment date on `docs/security/soc2_readiness_assessment.md`
(2026-07-22, pre-hardening) — that file is kept as a historical record of
the starting point; this document reflects the state after the P1–P9
security hardening pass tracked in this repository's git history, plus
two subsequent fixes (JSON-analysis-column encryption at rest, and TOTP
multi-factor authentication) closing gaps this document itself had
flagged as open.

**This is not a certification and does not substitute for an independent
audit.** It's an honest internal accounting of what's implemented, based
on reading the code, to help scope what an actual SOC 2 engagement would
still need to cover.

## Summary of What Changed

The prior assessment scored overall readiness at 38/100 and listed ten
blockers. Of those:

| Prior blocker | Status |
|---|---|
| No CSRF protection | ✅ Fixed — synchronizer token on all 21 state-changing routes |
| No rate limiting | ✅ Fixed — login/register/reset/share/upload |
| Sensitive contract content stored in plaintext | ✅ Fixed — AES-256-GCM encryption at rest for contract/template text |
| Google ID tokens decoded without signature verification | ✅ Fixed — full JWKS/RS256 verification |
| No security headers / TLS enforcement in app config | ✅ Fixed — CSP/HSTS/X-Frame-Options/etc. middleware |
| Default dev secrets could reach production | ✅ Fixed — production startup refuses to run with them |
| No MFA | ✅ Fixed — opt-in TOTP with recovery codes (`mfa.py`) |
| No audit-log immutability / admin action logging | ✅ Largely fixed — append-only `audit_logs` table covering auth, uploads, exports, deletes, shares, playbook changes, admin access |
| No backup/restore, DR evidence | ❌ Still open — infrastructure, not application code |
| No auditable CI/CD, dependency/secret scanning | ❌ Still open |

## Current Control Status

| Area | Status | Evidence |
|---|---:|---|
| Authentication | 🟢 Implemented | PBKDF2-HMAC-SHA256, verified Google OIDC, rate-limited |
| Authorization | 🟢 Implemented | Per-user_id scoping everywhere; RBAC for admin (not hardcoded) |
| Session management | 🟡 Mostly implemented | Redis-backed, HttpOnly/Secure/SameSite; in-memory fallback if Redis is down is a known resilience gap |
| CSRF | 🟢 Implemented | All 21 state-changing routes |
| Rate limiting | 🟢 Implemented | Auth, reset, share, upload |
| Security headers | 🟢 Implemented | CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| Encryption in transit | 🟡 Partially — app-level | Headers assume HTTPS; actual TLS termination is infra |
| Encryption at rest | 🟢 Implemented | `contract_text`/`template_text` and all JSON analysis columns that can embed contract excerpts (findings, AI output, review decisions, etc.) are AES-256-GCM encrypted with key rotation support; `rule_counts_json` deliberately stays plain (no contract text in it) |
| Upload validation | 🟢 Implemented | Magic bytes, zip/PDF bomb guards, filename sanitization |
| Malware scanning | 🟡 Interface implemented, off by default | Requires operator ClamAV setup |
| Audit logging | 🟢 Implemented | Append-only, covers the major event categories |
| RBAC | 🟢 Implemented | Roles/permissions/assignments, no hardcoded admin |
| Data retention | 🟡 Implemented, opt-in | Off by default; requires operator scheduling (cron/CronJob/HTTP) |
| Secrets management | 🟡 Partially | Production-required strength checks; no rotation automation or secret-scanning in CI |
| MFA | 🟢 Implemented, opt-in | TOTP + recovery codes (`mfa.py`); not enforced for any account |
| Backups / DR | ❌ Not implemented | Application code has no backup mechanism — infrastructure responsibility |
| CI/CD security gates | ❌ Not implemented | No `.github/workflows`, no dependency/secret/SAST scanning found in repo |
| Vulnerability management | ❌ Not implemented | No Dependabot/pip-audit configured |
| Vendor risk documentation | ❌ Not implemented | No DPA templates, subprocessor list |

## Remaining Blockers (Ranked)

1. **MFA is opt-in, not enforced.** TOTP + recovery codes are implemented
   (`mfa.py`) and available to every account, but nothing requires an
   admin (or any user) to actually turn it on. SOC 2 auditors commonly
   expect MFA to be *required* for privileged access specifically —
   enforcing that is a policy decision (would need e.g. "admin role
   requires MFA before the grant takes effect"), not implemented here
   since it changes account-management behavior beyond making the
   capability available.
2. **No backups/DR evidence.** Purely an infrastructure gap — this
   application has no backup mechanism of its own; whoever operates a
   deployment needs to add managed database backups, test restores, and
   define RPO/RTO.
3. **No CI/CD security gates** — no automated tests-on-PR, dependency
   scanning, secret scanning, or SAST configured in this repository.
4. **No vulnerability/dependency scanning** — `requirements*.txt` pin most
   versions but nothing automatically flags known CVEs in them.
5. **No vendor risk / DPA documentation** — Stripe, OpenAI, Google, and
   the hosting provider are all subprocessors without a documented review
   or data processing agreement template in this repo.
6. **Session resilience**: in-memory session fallback if Redis is
   unreachable in production should fail closed (reject the request) or
   at minimum alert loudly, rather than silently degrading.
7. **Admin dashboard reliability bug** (unrelated to security, but affects
   operational trust) — see `docs/security/known_issues.md`.

## What an Actual SOC 2 Engagement Would Still Need

Beyond the code-level items above, a real SOC 2 Type I/II process
requires organizational evidence this repository cannot provide by
itself:

- Documented security policies (access control, change management,
  incident response, vulnerability management, vendor management,
  acceptable use, data retention, backup/DR, risk assessment)
- Evidence of access reviews, least-privilege IAM configuration in
  whatever cloud/hosting environment is used
- Incident response runbooks and a tested tabletop exercise
- Independent penetration testing
- Change-management evidence (branch protection, required review,
  deployment approvals)
- For Type II specifically: sustained observation of these controls
  operating correctly over an audit period (typically 3-12 months)

## Estimated Effort

The application-code portion of the remaining gaps (CI/CD scanning setup,
enforcing MFA for privileged roles specifically) is now small — most of
what was originally scoped here (MFA capability, JSON-field encryption)
is done. The infrastructure and organizational-process portions
(backups, IAM, policies, incident response, penetration testing, and the
observation period itself) are the larger, longer-lead-time piece and are
not primarily a coding effort.
