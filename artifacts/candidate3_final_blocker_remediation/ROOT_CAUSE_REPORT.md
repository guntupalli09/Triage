FINAL PRE-FREEZE BLOCKER REMEDIATION — ROOT CAUSE REPORT

Branch: `claude/final-trust-architecture-cutover`
STARTING_COMMIT: `23b897b` (the pre-freeze inspection's own last commit)
FINAL_COMMIT: `bf72d98`

This mission was authorized to remediate exactly five architectural blockers found by the
independent pre-freeze inspection (`artifacts/pre_freeze_architecture/PRE_FREEZE_ARCHITECTURE_VERDICT.md`).
Blocker #6 (POLICY_ENFORCEMENT_MODE defaulting to "shadow") was explicitly out of scope and
was not touched.

## Blocker 1 — VERIFICATION_ERROR could disappear before authoritative evaluation

ROOT CAUSE: `fact_admission.first_unresolved_dependency_note`'s generic uncertain-
verification catch-all checked only 4 of the module's 6 unsafe verification states
(`NOT_ESTABLISHED`, `AMBIGUOUS`, `INSUFFICIENT_CONTEXT`, `CONFLICTING`), silently excluding
`DEPENDENCY_UNRESOLVED` and — critically — `VERIFICATION_ERROR`. A candidate that discovery
successfully proposed (a real, offset-grounded span) but whose per-candidate verify call then
failed on a provider error was therefore invisible to every one of the 12 adapters'
escalation mechanism, and could collapse to `NOT_APPLICABLE` when deterministic regex also
missed. See `VERIFICATION_FAILURE_SAFETY.md` for the full state-space audit and fix.

## Blocker 2 — Note-suppression gates could discard material AI uncertainty too broadly

ROOT CAUSE, discovered in two layers:
1. A **confirmed, severe** bug in liability's own gate: `category_treatments` always
   contains a `treatment="not_addressed", established=True` entry for every category
   nobody mentioned in the text, so `any(t.established for t in ...)` was ALWAYS true for
   any real provision — the gate suppressed the uncertain note regardless of whether the
   cap itself, or anything material, was ever established. Reproduced live against a bare
   "This Section addresses liability matters generally." provision.
2. A **previously-untested** defect shared by liability and indemnification: their gates
   uniformly suppressed ALL of `first_unresolved_dependency_note`'s output, including the
   definition-dependency/cross-reference-dependency/competing-readings mechanisms, which
   are always structurally material regardless of what else was established (the
   deterministic side has no way to independently know about a defined term/cross-
   reference/alternate reading it never scans for). No existing test combined "something
   else established" with "an unresolved definition/cross-reference/competing-reading on a
   different candidate," so this went undetected until this mission's own new tests
   exercised it. See `NOTE_SUPPRESSION_MATERIALITY.md`.

## Blocker 3 — Indemnification lacked equivalent reconciliation/provider-variance protection

ROOT CAUSE, two layers:
1. The reconciliation channel's uncertain-verification `else` branch consumed
   `first_unresolved_dependency_note`'s output completely unguarded — no equivalent to
   liability's materiality gate at all.
2. After adding a first gate (mirroring liability's monetary/scope/condition-established
   check), this mission's OWN repeatability testing found a second-order gap: unlike
   liability, indemnification has no deterministic classifier that can positively confirm
   "this named carve-out category was checked and found absent" — `condition.status ==
   "UNCONDITIONAL"` is ambiguous between "genuinely no exception" and "an exception exists
   in the text but wasn't structured." Monetary/scope being established says nothing about
   whether a same-clause exception was missed. See `INDEMNIFICATION_RECONCILIATION.md`.

## Blocker 4 — Indemnification's discovery provider was hardcoded, not configurable

ROOT CAUSE: `SEMANTIC_PROVIDER = "SIMULATED"` was a bare module-level literal with no
`os.environ` read anywhere in the file, unlike every other adapter's
`<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED` flag (all routed through the shared
`fact_admission.semantic_discovery_enabled` abstraction). Setting `FACT_ADMISSION_MODE=
enforced` activated real OpenAI discovery for 11/12 adapters and had zero effect on this
one; only a source-code edit could switch it. See `PROVIDER_UNIFICATION.md`.

## Blocker 5 — Customer surfaces could present legacy overall_risk as authoritative

ROOT CAUSE: four customer-facing surfaces (Full Report page, PDF export — all three call
sites, negotiation-package cover memo, external share link) never read
`document_aggregation.aggregate_document_state` or the underlying `policy_decisions_json`/
`interaction_decisions_json` at all — only the dashboard, history list, and in-progress
review page had been wired to the aggregated, policy/interaction-aware signal. See
`AUTHORITATIVE_DOCUMENT_STATE.md`.

## A sixth issue found (NOT one of the five authorized blockers, NOT fixed)

This mission's own repeatability re-run (after fixing Blockers 1–4) surfaced a genuinely new,
pre-existing, out-of-scope instance of unsafe clean-state variance: `ip_ownership-080`
flipped `ACCEPT`↔`REQUIRES_REVIEW` across identical real-provider runs (1/52 in the final
run). Root cause: `extract_ip_facts`'s admitted-candidate condition/exception composition
loop (`ip_ownership_policy_engine.py`, ~line 720) composes a grounded AI qualifier onto
`facts.ai_identified_condition`/`facts.ai_identified_exception` whenever the candidate is
`ADMITTED` — and whether the verifier happens to ground a qualifier for colloquial text like
"...shall be owned exclusively by Customer upon full payment" varies run to run. Confirmed
via `git diff` that this code was not touched by any commit in this mission. Per the
mission's explicit instruction not to fix beyond the five authorized blockers without
justification, this was documented, not fixed — see `FINAL_REMEDIATION_VERDICT.md`'s
KNOWN PROVIDER-VARIANCE→UNSAFE-CLEAN PATHS section.
