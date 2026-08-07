# Privacy

This document describes what data TriageCounsel collects, how it's stored,
who can see it, and how it's deleted — as implemented in this codebase
today. It supersedes `docs/compliance/data_privacy.md`, which described an
earlier, no-longer-current architecture (see the notice at the top of that
file).

This is a technical description of the implementation, not a legal privacy
policy. Consult qualified counsel before publishing a customer-facing
privacy policy or making compliance claims (GDPR/CCPA/etc.) based on this
document.

## What We Collect

| Data | Collected? | Where |
|---|---|---|
| Contract text (extracted from uploads) | Yes | `contracts.contract_text` (encrypted at rest, AES-256-GCM) |
| Playbook template text | Yes | `playbooks.template_text` (encrypted at rest) |
| Deterministic findings, risk scores, AI explanations | Yes | JSON columns on `contracts` (encrypted at rest, AES-256-GCM; `rule_counts_json` deliberately stays plain as it contains no contract text) |
| Account info (email, name, company) | Yes | `users` table |
| Password | Yes, hashed only (PBKDF2-HMAC-SHA256) — never stored or logged in plaintext | `users.password_hash` |
| IP address, user agent, referrer, UTM/acquisition data | Yes | `analytics_models.py` tables (`UserSession`, `UserEvent`, `UserAcquisition`) |
| Payment details | No — handled entirely by Stripe; only a Stripe customer/subscription ID is stored | `users.stripe_customer_id` |
| Original uploaded file (PDF/DOCX bytes) | No — only the extracted text is stored; the original file bytes are never written to disk or persisted | n/a |

## Where Contracts Are Stored

- **Database only** (PostgreSQL in production, SQLite in development) —
  no object storage (S3/GCS/etc.), no filesystem persistence of uploaded
  files.
- `contract_text` and `template_text` are **encrypted at rest** with
  AES-256-GCM (`encryption.py`) — the raw column value is never plaintext
  for any row written after encryption was enabled. See `SECURITY.md` for
  the encryption architecture.
- Other analysis fields (findings, AI explanations, risk scores, review
  decisions) are also stored as JSON and are **encrypted at rest** the
  same way — these fields can contain short verbatim excerpts of contract
  text, so they're covered by the same AES-256-GCM encryption
  (`EncryptedJSON` in `encryption.py`). `rule_counts_json` is deliberately
  left unencrypted since it contains only aggregate counts, never contract
  text.

## What Is Sent to OpenAI

The LLM (OpenAI, model configurable via `OPENAI_MODEL`) **never receives
full contract text** — this is enforced in code, not just policy: a
runtime guard in `evaluator.py` raises an error if full contract text is
ever passed to it. Only these are sent:

- The rule engine's pre-computed `overall_risk` label
- Per-finding metadata: rule name, title, severity, rationale (all fixed
  strings from the rule definitions, not derived from contract text)
- Short, rule-matched excerpts of contract text (capped at 300 characters,
  delimiter-isolated, and screened for prompt-injection patterns before
  being sent — see `LLM_BOUNDARY.md` and `prompt_security.py`)

OpenAI's own data retention/training policies apply to what is sent (not
something this codebase controls or can attest to — refer to OpenAI's API
terms directly).

## Who Can Access Your Contracts

- **You**, via your account — every contract/playbook query in the
  application is scoped to the requesting user's `user_id`; another
  customer's account cannot reach your data through the application.
- **Anyone with a share link you create**, for as long as that link is
  active. Share links support an optional password, an optional
  expiration date, an optional maximum view count, and can be revoked at
  any time — every access attempt is audit-logged (see `SECURITY.md`).
- **Admins**, via the role-based admin dashboard (`rbac.py`) — currently
  scoped to aggregate usage analytics, not individual contract content, in
  the routes reviewed. An admin with direct database access could still
  read encrypted contract text if they also had the encryption key(s) —
  key custody is an operational/infrastructure control outside this
  codebase.

## Deletion

- **Per-contract deletion**: `POST /contract/{id}/delete` (available from
  the history page) permanently deletes the contract row — text, findings,
  every derived analysis field, and its share link. This is a hard SQL
  `DELETE`, not a soft-delete flag.
- **Account deletion**: `POST /settings/delete-account` deletes all of a
  user's contracts and playbooks, then the user account itself.
- **Automatic retention** (opt-in, off by default): operators can set
  `CONTRACT_RETENTION_DAYS` to automatically and permanently delete
  contracts past that age — see `docs/security/data_retention_infra.md`
  for how cleanup is actually scheduled.
- All deletions are audit-logged (`audit_logs` table) — the audit record
  itself persists (recording that a deletion happened, by whom, and when)
  even though the underlying contract data does not.
- **Not covered by application-level deletion**: database backups (if
  the deploying organization runs them — this application does not
  implement backups; see `SOC2_ROADMAP.md`), and any data already sent
  to OpenAI/Stripe/Google as part of normal operation (subject to those
  providers' own retention policies).

## Data We Do Not Collect

- Payment card numbers (Stripe-hosted checkout; only a customer/
  subscription ID is stored)
- The original uploaded file bytes (only extracted text is persisted)

## Compliance Notes

- **GDPR / CCPA**: account deletion and per-contract deletion provide a
  technical basis for data-subject deletion requests, but this codebase
  does not implement a formal DSAR (data subject access request) workflow,
  consent-tracking, or a "do not sell" mechanism. See `SOC2_ROADMAP.md`.
- **HIPAA**: not applicable — this system is not designed to process
  health information and should not be used to do so.
- **PCI DSS**: out of scope for this application — no cardholder data is
  handled; Stripe's hosted flow keeps card data out of this system
  entirely.
