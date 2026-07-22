# Triage Counsel — Contract Risk Intelligence

A deterministic contract risk triage system designed to surface commonly negotiated risk indicators in standardized agreements such as NDAs, MSAs, and similar contracts.

- Triage Counsel uses a versioned, rule-based engine for risk detection and a constrained LLM layer for contextual explanation only, ensuring reproducible, auditable outputs.

- The system is built for **small and mid-sized law firms** — the core ICP — giving associates and partners rapid, auditable first-pass visibility into contract risk before detailed review. Founders, executives, and in-house legal teams remain supported secondary users.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (see Configuration below)
# Run the application
uvicorn main:app --reload
```

## What This System Does

Analyzes uploaded contract documents using deterministic pattern matching to identify common risk indicators. Detected risks are explained by an LLM layer that provides business-focused context—not legal advice. Produces structured reports with severity classifications, matched excerpts, and suggested negotiation considerations.

**See**: [What This Tool Is NOT](docs/use_cases/what_this_tool_is_not.md) for explicit limitations and non-claims.

## System Architecture

**Neural-Symbolic Architecture with Deterministic Control Plane**:
- **Deterministic Rule Engine**: All risk detection is rule-based (no LLM involvement)
- **LLM Explanation Layer**: Only explains pre-identified findings (never sees contract text)
- **Hard Boundaries**: Architectural guards prevent LLM from inventing risks
- **Safe Failure Modes**: System works even if LLM is unavailable

**See**: [Architecture Documentation](docs/architecture/) for detailed system design.

## Testing

**Test Results**: 268/268 tests passing (100% pass rate), including rule-engine regression tests and the security suite (OAuth verification, CSRF, rate limiting, security headers, production secret validation, secure cookies, Redis fail-closed startup — see `tests/test_security_*.py`, `tests/test_google_oauth.py`, `tests/test_auth_redis_and_cookies.py`).

```bash
# Run all tests
pytest tests/ -v

# Quick summary
pytest tests/ --tb=no -q
```

**See**: [Test Results & Coverage](docs/testing/test_results.md) for detailed test documentation.

## Documentation

Comprehensive documentation is available in the `/docs` directory:

### Core Documentation
- **[Architecture Overview](docs/architecture/architecture_overview.md)**: System design and component interactions
- **[Architecture & Future Roadmap](docs/architecture/FUTURE_ROADMAP.md)**: Enterprise multi-layer architecture and governance framework
- **[Enterprise Upgrade Plan](docs/architecture/ENTERPRISE_UPGRADE_PLAN.md)**: Comprehensive plan to transform Triage Counsel into an industry-leading B2B/B2C platform
- **[Implementation Checklist](docs/architecture/IMPLEMENTATION_CHECKLIST.md)**: Prioritized checklist for enterprise features
- **[Quick Start Guide](docs/architecture/QUICK_START_GUIDE.md)**: Step-by-step guide for implementing Phase 1 features
- **[Neural-Symbolic Design](docs/architecture/neural_symbolic_design.md)**: Deterministic control plane architecture
- **[Data Flow](docs/architecture/data_flow.md)**: How data moves through the system

### Rules Engine
- **[Rules Engine Overview](docs/rules_engine/rules_engine_overview.md)**: How deterministic detection works
- **[Rule Structure](docs/rules_engine/rule_structure.md)**: Rule format and patterns
- **[Rule Categories](docs/rules_engine/rule_categories.md)**: Types of rules and examples
- **[Versioning Strategy](docs/rules_engine/versioning_strategy.md)**: Ruleset versioning and changelog

### LLM Layer
- **[LLM Role & Limits](docs/llm_layer/llm_role_and_limits.md)**: LLM boundaries and safety guarantees
- **[Hallucination Prevention](docs/llm_layer/hallucination_prevention.md)**: How we prevent LLM from inventing risks
- **[Prompt Strategy](docs/llm_layer/prompt_strategy.md)**: LLM prompt design

### Testing & Quality
- **[Testing Strategy](docs/testing/testing_strategy.md)**: Testing philosophy and approach
- **[Test Results](docs/testing/test_results.md)**: Detailed test coverage and results
- **[Regression Policy](docs/testing/regression_policy.md)**: How we prevent breaking changes
- **[Known Limitations](docs/testing/known_limitations.md)**: Current limitations and edge cases

### Safety & Compliance
- **[Auditability](docs/compliance/auditability.md)**: How analyses are auditable
- **[Data Privacy](docs/compliance/data_privacy.md)**: Data handling and privacy
- **[Security Posture](docs/compliance/security_posture.md)**: Security measures
- **[Legal Disclaimer](docs/compliance/legal_disclaimer.md)**: Legal boundaries

### Use Cases
- **[For Founders](docs/use_cases/founders.md)**: How founders can use this tool
- **[For Freelancers](docs/use_cases/freelancers.md)**: Freelancer use cases
- **[Enterprise Review](docs/use_cases/enterprise_review.md)**: Enterprise deployment
- **[What This Tool Is NOT](docs/use_cases/what_this_tool_is_not.md)**: Explicit limitations

### Technical Details
- **[Original Contribution](docs/contribution/original_technical_contribution.md)**: Technical innovation
- **[Why Determinism Matters](docs/contribution/why_determinism_matters.md)**: Design philosophy
- **[Comparison to AI Wrappers](docs/contribution/comparison_to_ai_wrappers.md)**: How this differs

## Configuration

**See**: [Architecture Documentation](docs/architecture/) for detailed configuration options.

## Rule Engine

- **Version**: 4.0.0 (see `rules/version.json`) — 80 rules (24 high, 45 medium, 11 low)
- **Coverage**: Commercial NDAs, MSAs, SaaS agreements, vendor contracts, consumer/creator/marketplace terms, and contract-to-cash correctness (payment/invoice configuration, pricing ambiguity, signature/execution defects, termination-to-billing consequences)
- **Detection**: Regex and proximity-based pattern matching, plus document-level required-section and cross-document consistency checks
- **Anchoring**: All findings include exact text positions (start_index, end_index, exact_snippet) anchored to verbatim source-text slices
- **Suppression**: Deterministic false-positive suppression layer
- **Workflow layer**: signature_readiness (ready_to_send / commercial_review_recommended / legal_review_required / blocked_by_policy), additive to severity
- **Structured extraction**: payment_terms (due_days, currency, billing_frequency, invoice_trigger) for contract-to-cash integrations

**See**: [Rules Engine Documentation](docs/rules_engine/) for detailed rule design, structure, and examples.

## Safety & Legal Defensibility

- **Non-Advisory**: Uses "may indicate" language, never "safe to sign" or "illegal"
- **Auditable**: Every finding includes ruleset version, matched excerpts, and position anchors
- **Reproducible**: Same contract + same version = same output
- **LLM Lockdown**: Hard boundaries prevent LLM from seeing contract text or inventing risks

**See**: [Compliance Documentation](docs/compliance/) for detailed safety and legal defensibility measures.

## Security

**See**: [SOC 2 Readiness Assessment](docs/security/soc2_readiness_assessment.md) for the full control inventory, findings, and roadmap.

### Production environment variables

The app **refuses to start** in production (`DEV_MODE=false`, the default) if any of these are missing or insecure — see `security_config.py`:

| Variable | Requirement | Notes |
|---|---|---|
| `APP_HMAC_SECRET` | ≥32 chars, not a known placeholder | Generate with `openssl rand -hex 32`. Signs anonymous-session tokens. |
| `SESSION_SECRET` | ≥32 chars, not a known placeholder | Generate with `openssl rand -hex 32`. |
| `BASE_URL` | Set, `https://`, not localhost | Used to build absolute redirect/callback/share URLs. |
| `SECURE_COOKIES` | Must be `"true"` | Marks all cookies (session, CSRF, OAuth state/nonce) `Secure`; they are always `HttpOnly` + `SameSite=Lax` regardless. |
| `REDIS_URL` | Required (see below) | Sessions and rate-limit counters use Redis in production — never an in-memory fallback. |

None of these checks apply when `DEV_MODE=true`; local development is never blocked.

### Redis (fail-closed in production)

- **Development** (`DEV_MODE=true`): if `REDIS_URL` is unset or Redis is unreachable, the app logs a warning and falls back to in-memory sessions/rate-limit counters.
- **Production** (`DEV_MODE=false`): startup fails outright if `REDIS_URL` is unset or Redis is unreachable — sessions must never silently degrade to in-memory storage across multiple gunicorn workers. See `auth.init_redis_or_fail()` (uvicorn/ASGI startup) and `database.wait_for_redis()` (gunicorn's `on_starting` hook, `gunicorn.conf.py`).

### CSRF protection

Every browser POST/PUT/PATCH/DELETE route requires a CSRF token — a double-submit cookie (`csrf_token`, minted by `CSRFCookieMiddleware`) that must be echoed back as a hidden form field (`csrf_token`) or an `X-CSRF-Token` header, verified via `Depends(verify_csrf)` (`csrf.py`). The only exemption is `/stripe-webhook`, which authenticates via Stripe's own signature verification instead and is never a browser request.

### Rate limiting

Redis-backed (falls back to in-memory in dev — see above), enforced per-IP and, on identity-bearing endpoints, per-account (email/user id/share token) independently. See `rate_limit.py` for the implementation and each route in `main.py` for its specific limit. Representative limits:

| Endpoint | Per-IP | Per-account |
|---|---|---|
| `POST /login` | 10/min | 5/min, 20/hour |
| `POST /register` | 5/min | 3/min, 10/hour |
| `POST /forgot-password` | 5/min | 3/min, 10/hour |
| `POST /upload`, `/batch-upload` | 30/min, 15/min | — |
| `POST /contract/{id}/share` | 20/min | — |
| `GET /auth/google`, `/auth/google/callback` | 20/min, 30/min | — |
| `POST /subscribe/{plan}` | 10/min | — |

All rate-limit rejections return HTTP 429 with a JSON `detail` message.

### Security headers & CSP

`security_headers.py` adds HSTS (production only), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and a Content-Security-Policy. The CSP allows `'unsafe-inline'` scripts/styles (the app renders inline `<script>`/`<style>` blocks with no nonce plumbing today — tracked as Phase 2) and `https://cdn.jsdelivr.net` (Chart.js on the admin dashboard) / Google Fonts. See the module docstring for the full, current list of exceptions.

### Google Sign-In

`google_oauth.py` verifies ID tokens with Google's official `google-auth` library (`google.oauth2.id_token.verify_oauth2_token`), which checks the RS256 signature against Google's rotating JWKS, issuer, audience, and expiry — the JWT payload is never decoded manually. A nonce is also round-tripped through a short-lived cookie and checked against the token's `nonce` claim, in addition to the existing OAuth `state` check.

### Logging

`log_redaction.py` installs a filter on the root logger that redacts passwords, API keys (OpenAI `sk-...`, Stripe `sk_live_/sk_test_/whsec_...`), OAuth/session tokens, and session/CSRF cookie values from any log line that would otherwise contain them — a defense-in-depth backstop, not a substitute for not logging secrets in the first place.

### Dependency security

- CI (`.github/workflows/security.yml`) runs `pip-audit` (fails on unignored vulnerabilities) and `detect-secrets` (fails on anything not in the committed `.secrets.baseline`) on every push/PR, plus a weekly scheduled run to catch newly disclosed CVEs.
- `.github/workflows/tests.yml` runs the `pytest` suite on every push/PR.
- **Upgrading a pinned dependency**: bump the version in `requirements.txt` (mirror the change in `requirements-prod.txt`/`requirements-docker.txt`), run `pytest -q` and `pip-audit -r requirements.txt --strict`, and do a manual smoke test of login/upload/CSRF/rate-limiting before merging — see the "Dependency security posture" section of the SOC 2 assessment for an example of a version bump that looked safe on paper but broke `TemplateResponse` in testing.
- **Updating `.secrets.baseline`** after a legitimate new match: `detect-secrets scan --baseline .secrets.baseline && detect-secrets audit .secrets.baseline`, then commit the result.

## License

This project is provided as a reference implementation of a deterministic contract risk triage system.

It is intended for evaluation, research, and controlled deployment use cases.  
Users are responsible for reviewing, testing, and validating any modifications prior to production use.


## Support

For technical questions, refer to the documentation in `/docs`. For issues or contributions, please follow standard GitHub workflows.
