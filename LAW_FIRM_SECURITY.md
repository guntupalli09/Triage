# Security FAQ for Law Firms

Plain-language answers for evaluating TriageCounsel as an enterprise
customer, grounded in what this codebase actually implements (see
`SECURITY.md`, `PRIVACY.md`, `THREAT_MODEL.md` for the detail behind each
answer). Where something isn't yet implemented, this document says so
explicitly rather than implying otherwise.

## Is my data private?

Your contract text is stored in our database, encrypted at rest
(AES-256-GCM), and scoped to your account — every query the application
makes is filtered to your account, so other customers cannot reach your
contracts through the application. We do not sell your data or share it
with third parties beyond what's needed to run the service (OpenAI for AI
explanations, Stripe for billing — see below for exactly what each
receives).

## Can OpenAI train on my contracts?

We never send OpenAI your contract text. This is enforced in code: the
function that talks to OpenAI has a hard guard that raises an error if
full contract text is ever passed to it. Only short, already-detected rule
matches (a few hundred characters at most, per finding) and their
titles/severities are sent — never the document itself.

Whether OpenAI uses API traffic for model training is governed by OpenAI's
own API terms, not by our code. As of this writing, OpenAI's standard API
terms state that API inputs/outputs are not used to train their models by
default — but this is OpenAI's policy, not something we can independently
verify or guarantee from our side. Review OpenAI's current API data usage
policy directly for your own diligence.

## Who can access my contracts?

- You, through your account.
- Anyone you explicitly share a link with — share links can be
  password-protected, set to expire, capped at a maximum number of views,
  and revoked at any time. Every access attempt to a shared link is
  logged.
- A small number of admin accounts, explicitly granted that role (not a
  hardcoded username/password), for viewing aggregate usage analytics —
  not, in the routes we've reviewed, individual contract content.

## How are contracts protected?

- **Encrypted at rest**: contract text is encrypted with AES-256-GCM
  before it touches the database.
- **Access-controlled**: every contract query is scoped to your account.
- **CSRF-protected**: actions like uploading, sharing, or deleting a
  contract require a token tied to your browser session, so a malicious
  website can't trigger them on your behalf.
- **Rate-limited**: login, password reset, and share-link password
  attempts are throttled to slow down automated attacks.
- **Audit-logged**: uploads, exports, deletions, shares, and admin access
  are recorded with who, what, and when.

We do **not** currently offer multi-factor authentication (MFA) for any
account, including admin. This is a known gap — see `SOC2_ROADMAP.md`.

## Can I delete my contracts?

Yes, two ways:
- **Per-contract**: permanently delete a single contract (text, findings,
  and its share link) from your history page at any time.
- **Full account**: deleting your account permanently deletes all your
  contracts and playbooks in the same operation.

Both are hard deletions (not a "hidden" flag) and are logged in our audit
trail — the record that a deletion happened persists even though the
contract content does not.

## How is AI used?

AI is used only to write plain-English explanations of risks our
deterministic rule engine has already found. It never scans your contract
directly, never decides what counts as a risk, and never overrides the
computed risk level — that's enforced in code, not just instructed by
prompt. See `LLM_BOUNDARY.md` for the full technical detail.

## Does AI make legal decisions?

No. The AI is instructed to never declare something legal, enforceable,
or "safe to sign" — only the deterministic rule engine determines findings
and risk level, and that determination is never influenced by the AI. We
should be transparent that the "never use these phrases" instruction is
enforced by prompting the model, not by scanning its output afterward and
rejecting non-compliant responses — this is a known limitation, tracked in
`LLM_BOUNDARY.md`.

## What happens if AI fails or is unavailable?

Your report is still generated. If the AI service is unreachable, times
out, or isn't configured, the system falls back to a rules-only summary
built directly from the deterministic findings — no fabricated analysis,
no degraded findings.

## Is every finding explainable?

Every finding includes the specific rule that triggered it, the matched
contract excerpt, and a rationale — persisted exactly as computed at
analysis time, along with the rule-engine version used, so it stays
consistent even if the ruleset is later updated. Every AI-generated
explanation is checked against the deterministic findings it was given;
currently this check logs a warning if something doesn't map back cleanly
rather than blocking it outright — see `LLM_BOUNDARY.md`'s "Known
Limitations."

## Can the platform be audited?

We maintain an append-only audit log covering logins, uploads, exports,
deletions, playbook changes, share-link activity, and admin access
(granted and denied) — actor, target, IP address, and outcome for each. We
do not yet have a completed SOC 2 attestation; see `SOC2_ROADMAP.md` for
our current control posture and what's still outstanding before we'd
pursue one.

## What about infrastructure — TLS, backups, encryption at the disk level?

These are deployment-specific, not something the application code itself
guarantees:
- **TLS/HTTPS**: the application sends security headers assuming HTTPS
  (including HSTS once configured for a secure deployment), but actual TLS
  termination is the responsibility of whatever reverse proxy or hosting
  platform fronts the deployment.
- **Backups**: not implemented by this application. Whether backups exist,
  how they're encrypted, and how often they're tested depends entirely on
  how a given instance is operated.
- **Disk/database-level encryption**: separate from the AES-256-GCM
  encryption this application applies specifically to contract text —
  whether the underlying database volume is also encrypted depends on the
  hosting provider's configuration.

Ask your deployment operator (or us, if we're hosting your instance) about
these specifically — they're not universal facts about "TriageCounsel,"
they depend on how a given instance is deployed. See `SOC2_ROADMAP.md` for
the infrastructure checklist.
