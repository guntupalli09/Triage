# EXECUTABLE ARCHITECTURE TRACE (at FROZEN_COMMIT f94c4c3)

Traced by direct code reading at the frozen commit, not by assumption or
by re-reading prior sessions' claims. Each row states what actually
executes, not what was intended.

## 0. THE SINGLE MOST IMPORTANT FINDING

**With `POLICY_ENFORCEMENT_MODE` unset (production default = `"shadow"`,
`policy_enforcement.py:52`), none of the fact-admission architecture
validated in this initiative determines the customer-visible review
result.**

`apply_policies_for_review()` (`policy_enforcement.py:751`) is "the one
function main.py calls for policy enforcement, regardless of mode."
Its mode branch (`policy_enforcement.py:776-809`):

- `mode == "cutover"` → calls `apply_active_policies()`, which walks all
  12 registered clause types (`playbook_authoring.py:72-87`,
  `_ENGINE_PROTOCOLS`/`CLAUSE_TYPES` — genuinely all 12, despite a stale
  docstring elsewhere claiming "six clause types") via each adapter's
  real `extract_fn`/`evaluate_fn` pair, then feeds the results into
  `interaction_enforcement.apply_interaction_rules()`. **This is the
  ONLY path where this session's (and prior sessions') work is
  authoritative.**
- `mode in ("legacy", "shadow")` → **always** calls
  `apply_liability_policy()` (`policy_enforcement.py:73`, the
  ORIGINAL, single-clause-type, pre-fact-admission legacy path) for the
  actual `policy_decisions` returned to the caller. In `"shadow"` mode
  specifically, `run_shadow_comparison()` ALSO runs the 12-adapter
  engine, but strictly for diagnostic comparison — wrapped in a bare
  `except Exception: pass` (`policy_enforcement.py:801-807`) — and its
  result is discarded, never merged into the returned
  `policy_decisions`.

`is_policy_authoritative()` (`policy_enforcement.py:156-166`) is the
single sanctioned way to ask "does an ACTIVE PolicyPosition actually
govern this review right now" and returns `False` in both `shadow` and
`legacy` mode. The UI-facing `ENFORCEMENT_DISCLOSURE` dict
(`policy_enforcement.py:174-198`) confirms this is a known, deliberate,
disclosed state — not a bug — but it means: **this entire validation
mission is scoped to code that is not yet deciding any real customer's
contract review**, unless and until an operator sets
`POLICY_ENFORCEMENT_MODE=cutover` (a deployment action outside this
codebase and explicitly forbidden to this session).

A second precondition even under `cutover`: `evaluate_active_policies()`
(`policy_enforcement.py:418`) only evaluates a clause type that has an
**ACTIVE** `PolicyPosition` configured for the playbook in use — absence
of one means that clause type is silently skipped for that review
(documented as intentional: "never treated as permissive acceptance").

## 1. Per-boundary trace (the requested chain)

| Transition | Function/module | Deterministic vs probabilistic | Authoritative? | Failure behavior | Can failure produce CLEAN/ACCEPT? | Does the next layer actually consume the output? |
|---|---|---|---|---|---|---|
| Raw contract → extraction | `extract_<clause>_facts()` per adapter (e.g. `liability_policy_engine.extract_liability_facts`) | Deterministic (regex/structural) | Yes — this IS the authoritative fact layer when no AI path fires | Returns `None` (CONFIRMED_ABSENT) only when regex finds nothing AND semantic discovery also ran and found nothing | No — `None` maps to `NOT_APPLICABLE`, not `ACCEPT` | Yes, unconditionally |
| Extraction → normalization | Same functions (window extraction, role-side resolution, category tokenization) | Deterministic | Yes | Ambiguous tokens recorded as `*_conflict=True` / `"unresolved"`, never silently resolved | No — conflict flags route to `REQUIRES_REVIEW` in every adapter's evaluate function | Yes |
| → AI contextual discovery/verification | `fact_admission.discover_candidate_spans` / `verify_candidate_proposition` | Probabilistic | **No** — AI never sets `admission_status` | `VERIFICATION_ERROR` (never `NOT_ESTABLISHED`) on any provider failure (`fact_admission.py`, `verify_candidate_proposition`) | No — `VERIFICATION_ERROR` is one of `_UNSAFE_VERIFICATION_STATES`, blocks admission | Yes, but **only runs at all when `<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED` or `FACT_ADMISSION_MODE=enforced` is set — both unset in production at freeze** (see `FREEZE_MANIFEST.md`) |
| → canonical candidate material facts | `CandidateMaterialFact` (`fact_admission.py`) | N/A (schema) | No (candidate is pre-authority) | `_FORBIDDEN_FIELD_NAMES`/`assert_authority_boundary_intact()` prevents any decision-shaped field from ever existing on this class | N/A | Yes |
| → verbatim grounding | `ground_evidence_quote()` | Deterministic (exact substring) | Yes (gate) | `GroundingResult(passed=False)` on any non-exact match | No — feeds `evaluate_admission`'s hard gate | Yes |
| → condition/exception grounding | `ground_qualifiers()` | Deterministic | Yes (gate) | Same as above, per-qualifier | No | Yes |
| → definition resolution | `resolve_definition()` | Deterministic (regex over source text, never AI content) | Yes (gate) | `NOT_FOUND`/`CONFLICTING` blocks admission (`evaluate_admission`) | No | Yes — proven per-adapter this pass (see `CANONICAL_FACT_PROOF_MATRIX.md`) |
| → cross-reference resolution | `resolve_cross_reference_target()` | Deterministic | Yes (gate) | `NOT_FOUND`/`CONFLICTING`/`MISSING_ATTACHMENT` blocks admission | No | Yes — proven per-adapter this pass |
| → competing-reading preservation | `ground_competing_readings()` | Deterministic (grounds the AI's claimed readings, does not itself interpret) | Yes (gate) | ≥2 grounded readings blocks admission (defense-in-depth check in `evaluate_admission`, independent of `verification.status`) | No | Yes — proven per-adapter this pass |
| → admission/reconciliation | `evaluate_admission()` / `verify_and_ground()`; indemnification's `_reconcile_obligation_with_contextual_analysis()` | Deterministic | Yes — the ONE function permitted to set `admission_status` | `NOT_ADMITTED` on any gate failure | No | Yes |
| → deterministic authoritative facts | Each adapter's `*Facts` dataclass, composed from admitted candidates only | Deterministic | Yes | Unresolved/unreconciled material forces a dedicated field that every adapter's evaluate function checks | No | Yes |
| → adapter policy evaluation | `evaluate_<clause>_policy()` per adapter | Deterministic | Yes | See per-adapter matrix below | No (by design; this is the layer the whole initiative protects) | Yes, when called |
| → interaction engine | `interaction_enforcement.apply_interaction_rules()` | Deterministic | Yes, but **only reached in `cutover` mode** (`policy_enforcement.py:792-793`) | Not exercised in `shadow`/`legacy` | N/A (not reached) | **Only in cutover — not reached in shadow/legacy, the production default** |
| → unified document state | `Contract.policy_decisions_json` / `policy_revision_metadata_json` | N/A (persistence) | Reflects whichever branch above executed | — | — | Yes |
| → persisted review | Same `Contract` row, via `main.py`'s call into `apply_policies_for_review` | — | — | — | — | Yes |
| → UI surfaces | `ENFORCEMENT_DISCLOSURE` gates whether the UI claims the policy is "governing" vs "checking only" | — | — | — | — | Yes, per `is_policy_authoritative()` |

## 2. IMPLEMENTED vs WIRED vs UNIT-TESTED vs CORPUS-PROVEN vs LIVE-PROVEN

Using the mission's own required distinction, for the fact-admission
layer specifically (definition/cross-reference/competing-reading/
reconciliation, i.e. everything built across the last several
sessions):

- **IMPLEMENTED**: Yes, all 12 adapters, at `FROZEN_COMMIT`.
- **WIRED**: Yes, into `evaluate_active_policies()`'s dispatch table
  (`playbook_authoring.py:72-87`) and each adapter's own
  `_run_semantic_discovery`/reconciliation call sites — confirmed by
  direct code reading, not assumed.
- **UNIT-TESTED**: Yes, extensively (mocked provider responses) — see
  every prior session's test additions; 1357 passing tests at
  `FROZEN_COMMIT` per the regression baseline.
- **CORPUS-PROVEN**: Partial, this session — see
  `FINAL_VALIDATION_REPORT.md`. The deterministic backbone (extraction,
  absence handling, party resolution, policy evaluation) is exercised
  against a fresh, independent corpus. The AI-contextual-discovery
  dimension specifically is **NOT** corpus-proven this session — no
  `ANTHROPIC_API_KEY` is available in this environment (confirmed in
  `FREEZE_MANIFEST.md`), and this mission's own rules forbid fabricating
  provider calls or substituting mocks and calling it corpus-proven.
- **LIVE-PROVEN**: No. Not attempted, per this mission's explicit scope
  (`triagecounsel.com` validation is a separate, later mission), and
  moot regardless given Finding 0 above — the architecture is not
  authoritative in production today under its own default configuration.

## 3. Minor documentation staleness noted (not a functional defect)

`policy_enforcement.py:562`'s docstring for `apply_active_policies`
says "generalized to all six clause types" — the actual dispatch table
(`playbook_authoring.CLAUSE_TYPES`) has all 12. Recorded here for
completeness; does not affect the FROZEN_COMMIT's behavior, so it is
not scored as a safety-gate failure and, per this mission's
immutability rule, was NOT corrected in this session.
