# ADAPTER_MATRIX

## Reconciliation (12/12, resolving the "1/12 vs 10/12" ambiguity)

The previous session's summary conflated two different things under
"integrated." This table separates them:

- **Architecturally protected** = has SOME absence-state-aware,
  fail-closed-on-uncertainty protection today (whether via the new shared
  `fact_admission.py` or indemnification's own pre-existing, separately
  frozen equivalent).
- **Integrated with shared framework** = specifically uses
  `fact_admission.py`'s discover/verify/ground/admit functions.

| # | Adapter | Architecturally protected before this branch | Shared `fact_admission.py` integration | Production enabled | Targeted tests | Regression |
|---|---|---|---|---|---|---|
| 1 | limitation_of_liability | No | **YES** (prior session) | No (`LIABILITY_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 85/85 pass |
| 2 | indemnification | **YES** — own pre-existing `semantic_discovery_real.py` + 4-way `absence_state`, frozen/validated Step 4B | Not migrated (deliberate — see ARCHITECTURE.md) | Partial (`SEMANTIC_PROVIDER` hardcoded `SIMULATED`) | pre-existing suite | pre-existing suite passes |
| 3 | confidentiality | No | **YES** | No (`CONFIDENTIALITY_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 36/36 pass |
| 4 | payment_terms | No | **YES** | No (`PAYMENT_TERMS_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 8/8 pass |
| 5 | ip_ownership | No | **YES** | No (`IP_OWNERSHIP_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 4/4 pass |
| 6 | insurance | No | **YES** | No (`INSURANCE_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 11/11 pass |
| 7 | data_security | No | **YES** | No (`DATA_SECURITY_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 4/4 pass |
| 8 | governing_law | No | **YES** | No (`GOVERNING_LAW_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 25/25 pass |
| 9 | termination | No | **YES** | No (`TERMINATION_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 50/50 pass |
| 10 | warranties | No | **YES** | No (`WARRANTIES_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 4/4 pass |
| 11 | sla | No | **YES** | No (`SLA_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 4/4 pass (test_sla_activation_hook_no_effect_on_existing_adapters.py requires fastapi, environment-blocked in this sandbox — not run) |
| 12 | assignment | No | **YES** | No (`ASSIGNMENT_SEMANTIC_DISCOVERY_ENABLED=False`) | 7 | 26/26 pass |

**Final accounting, all 12/12 closed:**
- **Integrated with the shared `fact_admission.py` framework: 11/12**
  (liability, confidentiality, payment_terms, ip_ownership, insurance,
  data_security, governing_law, termination, warranties, sla, assignment).
- **Architecturally protected but NOT migrated onto the shared framework:
  1/12** (indemnification — its own separate, pre-existing,
  Step-4B-frozen mechanism; left as-is per ARCHITECTURE.md's explicit
  rationale, not an oversight).
- **Architecturally protected overall (either mechanism): 12/12.**
- **Production-enabled (flag defaulting to on, live in the deployed
  product): 0/11 of the newly-integrated adapters** — every
  `*_SEMANTIC_DISCOVERY_ENABLED` flag defaults `False`; indemnification's
  own `SEMANTIC_PROVIDER` is hardcoded `"SIMULATED"`, not calling a real
  model in production either. **No adapter's live production behavior
  differs from before this branch.** Enabling any of them is a deliberate,
  separate deployment decision this implementation pass does not make.
- **Targeted tests added this session: 77** (7 per adapter × 11 adapters)
  **+ 39 for the shared framework itself = 116 new tests total.**
- **Regression**: every adapter's pre-existing test suite re-run after its
  integration and confirmed passing unchanged (see per-row counts above);
  one real bug (a `NameError` in payment_terms from an incomplete
  variable rename) was caught by this exact discipline before commit —
  see that adapter's commit message.

## Absence-state matrix (all 12 adapters)

Per-adapter mapping of the 7 required states to what actually reaches
`evaluate_*_policy` and the `PolicyDecision.state` it produces. "Existing
branch absorbs it" means the RECOGNITION_UNCERTAIN case was not given a
new decision branch because an existing branch already treats the
"structure could not be parsed" case identically and safely (verified
adapter-by-adapter, not assumed).

| Adapter | PRESENT+ESTABLISHED | PRESENT+UNRESOLVED | RECOGNITION_UNCERTAIN | CONFIRMED_ABSENT | NOT_APPLICABLE | DEPENDENCY_UNRESOLVED | EVALUATION_ERROR |
|---|---|---|---|---|---|---|---|
| liability | ACCEPT/NEGOTIATE/etc. per cap terms | REQUIRES_REVIEW (unreconciled/unresolved) | REQUIRES_REVIEW (explicit branch) | NOT_APPLICABLE | NOT_APPLICABLE (same as confirmed-absent — no clause found) | REQUIRES_REVIEW (cross-reference unresolved, pre-existing) | EVALUATION_ERROR (policy_enforcement.py isolation, pre-existing) |
| indemnification | ACCEPT/etc. (PRESENT_AND_VERIFIED) | REQUIRES_REVIEW (PRESENT_BUT_UNRESOLVED) | REQUIRES_REVIEW (own pre-existing 4-way absence_state) | NOT_APPLICABLE (CONFIRMED_ABSENT) | NOT_APPLICABLE | REQUIRES_REVIEW (condition/cross-ref handling, pre-existing) | EVALUATION_ERROR (pre-existing) |
| confidentiality | ACCEPT/etc. | REQUIRES_REVIEW (existing `if not obligations` branch absorbs it) | REQUIRES_REVIEW (same branch, no new code needed) | NOT_APPLICABLE | NOT_APPLICABLE | REQUIRES_REVIEW (resolution_reasons, pre-existing) | EVALUATION_ERROR (pre-existing) |
| payment_terms | ACCEPT/etc. | REQUIRES_REVIEW (unresolved list, pre-existing) | REQUIRES_REVIEW (explicit branch, new) | NOT_APPLICABLE | NOT_APPLICABLE | REQUIRES_REVIEW (chained_delegation/conditional_unverified_precondition, pre-existing) | EVALUATION_ERROR (pre-existing) |
| ip_ownership | ACCEPT/etc. | REQUIRES_REVIEW (conflict categories, pre-existing) | REQUIRES_REVIEW (explicit branch, new — prevents ACCEPT-by-omission) | NOT_APPLICABLE | NOT_APPLICABLE | REQUIRES_REVIEW (sow_cross_reference w/ 0 established dims, pre-existing pattern) | EVALUATION_ERROR (pre-existing) |
| insurance | ACCEPT/etc. | REQUIRES_REVIEW (per-coverage unresolved, pre-existing) | REQUIRES_REVIEW (explicit branch, new — prevents ACCEPT-by-omission) | NOT_APPLICABLE | NOT_APPLICABLE | REQUIRES_REVIEW (schedule_cross_reference, pre-existing) | EVALUATION_ERROR (pre-existing) |
| data_security | ACCEPT/etc. | REQUIRES_REVIEW (role/subprocessor/breach conflicts, pre-existing) | REQUIRES_REVIEW (explicit branch, new — prevents ACCEPT-by-omission) | NOT_APPLICABLE | NOT_APPLICABLE | REQUIRES_REVIEW (dpa_cross_reference w/ 0 established dims, pre-existing) | EVALUATION_ERROR (pre-existing) |
| governing_law | ACCEPT/etc. | REQUIRES_REVIEW (existing `if jurisdiction is None` branch absorbs it) | REQUIRES_REVIEW (same branch, no new code needed) | NOT_APPLICABLE | NOT_APPLICABLE | N/A (no cross-reference concept in this adapter) | EVALUATION_ERROR (pre-existing) |
| termination | ACCEPT/etc. | REQUIRES_REVIEW (existing `if not rights` branch absorbs it) | REQUIRES_REVIEW (same branch, no new code needed) | NOT_APPLICABLE | NOT_APPLICABLE | N/A (no cross-reference concept modeled) | EVALUATION_ERROR (pre-existing) |
| warranties | ACCEPT/etc. | REQUIRES_REVIEW (mutual_asymmetry/duration_conflict, pre-existing) | REQUIRES_REVIEW (explicit branch, new — this adapter's own found_anything gate is deliberately NOT_APPLICABLE, so RECOGNITION_UNCERTAIN needed its own path) | NOT_APPLICABLE | NOT_APPLICABLE (deliberate negative-control: anchor-fired-but-unstructured is also NOT_APPLICABLE, not REQUIRES_REVIEW — see module docstring) | REQUIRES_REVIEW (schedule_cross_reference, pre-existing) | EVALUATION_ERROR (pre-existing) |
| sla | ACCEPT/etc. | REQUIRES_REVIEW (uptime/measurement/credit conflicts, pre-existing) | REQUIRES_REVIEW (explicit branch, new — same reason as warranties) | NOT_APPLICABLE | NOT_APPLICABLE (same deliberate negative-control as warranties) | REQUIRES_REVIEW (schedule_cross_reference, pre-existing) | EVALUATION_ERROR (pre-existing) |
| assignment | ACCEPT/etc. | REQUIRES_REVIEW (existing `if not restrictions and not unrestricted` branch absorbs it) | REQUIRES_REVIEW (same branch, no new code needed) | NOT_APPLICABLE | NOT_APPLICABLE | N/A (no cross-reference concept modeled) | EVALUATION_ERROR (pre-existing) |

**No adapter permits "no extraction result = confirmed absent" without
independent evidence supporting that conclusion.** In every adapter,
CONFIRMED_ABSENT (→ NOT_APPLICABLE) is reachable only when semantic
discovery (a) ran, (b) completed without error, and (c) found nothing —
never merely because the deterministic regex found nothing. Two
architecturally distinct sub-patterns exist, both verified per-adapter
above, not assumed uniform: (1) confidentiality/termination/governing_law/
assignment already had a safe existing branch that RECOGNITION_UNCERTAIN
falls into without new code; (2) liability/payment_terms/ip_ownership/
insurance/data_security/warranties/sla needed (and received) an explicit
new branch, because their existing "nothing structured" path either
resolves to ACCEPT under a permissive playbook (ip_ownership/insurance/
data_security's all-None-facts risk) or is itself a deliberate
NOT_APPLICABLE negative control (warranties/sla) that RECOGNITION_
UNCERTAIN must not be confused with.

DEPENDENCY_UNRESOLVED as its own named state (distinct from the existing
REQUIRES_REVIEW-with-cross-reference-explanation pattern) was not
introduced as a new state value in this pass — every adapter's existing
cross-reference/dependency handling already routes to REQUIRES_REVIEW
with an explanation naming the unresolved dependency, which is the
architecturally correct outcome (never treated as safe); a distinct
`DEPENDENCY_UNRESOLVED` string was judged to add a fourth vocabulary
layer without changing what any consumer does with it (interaction_engine_
core.py and document_aggregation.py both already treat REQUIRES_REVIEW as
unsafe/must-escalate identically to how they would treat a hypothetical
DEPENDENCY_UNRESOLVED). This is a documented design decision, not an
oversight — flagged here for scrutiny rather than silently assumed correct.



Integration status of the shared `fact_admission.py` framework across all
12 production adapters (confirmed list, see PRE_IMPLEMENTATION_MAP.md §1).

| # | Adapter | Fact-admission integration | Existing AI pathway |
|---|---|---|---|
| 1 | limitation_of_liability | **DONE (reference implementation)** — see below | none prior to this change |
| 2 | indemnification | Not migrated — has its own separately frozen, already-validated (Step 4B) semantic-discovery pathway (`semantic_discovery_real.py`) with an equivalent absence-state model. See ARCHITECTURE.md for why this is left as-is. | `semantic_discovery_real.py` (Anthropic, discovery only, deterministic structural verification) |
| 3 | confidentiality | Not yet integrated | none |
| 4 | payment_terms | Not yet integrated | none |
| 5 | ip_ownership | Not yet integrated | none |
| 6 | insurance | Not yet integrated | none |
| 7 | data_security | Not yet integrated | none |
| 8 | governing_law | Not yet integrated | none |
| 9 | termination | Not yet integrated | none |
| 10 | warranties | Not yet integrated | none |
| 11 | sla | Not yet integrated | none |
| 12 | assignment | Not yet integrated | none |

**Only 1 of 12 adapters (liability) has been integrated with the new
shared framework in this pass**, per explicit user direction to prove the
pattern end-to-end on one adapter before rolling out to the rest (see
conversation record — this was a deliberate, confirmed scope decision, not
an oversight). The remaining 10 are scoped below as a roadmap; each is
real design work (Step 8), not mechanical repetition, because each
adapter's material dimensions differ.

## 1. limitation_of_liability — DONE

Material dimensions already handled by `liability_policy_engine.py`'s
existing deterministic structuring (unchanged by this integration): cap
amount/multiplier, cap basis (fees/purchase price/contract value/fixed/
recurring payment), category carve-outs (data breach, IP infringement,
confidentiality, indemnification, fraud, gross negligence, willful
misconduct), consequential-damages exclusion, cross-referenced cap
definitions, multi-provision reconciliation (amendment/consistent-
duplicate/unreconciled), and directional (asymmetric) party positions.

Fact-admission integration adds a third, additive discovery layer for the
one case the deterministic anchors miss entirely: liability language using
neither `_ANCHOR_RE` nor `_SECONDARY_ANCHOR_RE`'s vocabulary. The semantic
layer never touches cap parsing, basis classification, or category
carve-out logic — a semantically-discovered candidate is only ever a
*where to look* signal into the SAME deterministic `_extract_provision()`
every regex anchor already uses (see AUTHORITY_BOUNDARY.md §3). Gated
behind `LIABILITY_SEMANTIC_DISCOVERY_ENABLED` (default `False`).

## 2-12. Roadmap for the remaining adapters (dimensions, not yet built)

Each row lists the material dimensions a semantic verifier's adversarial
proposition set would need to address for that adapter, drawn from each
engine's own `SEMANTIC MODEL` docstring section
(confirmed present at `confidentiality_policy_engine.py:7`,
`payment_terms_policy_engine.py:18`, `ip_ownership_policy_engine.py:17`,
`insurance_policy_engine.py:15`, `data_security_policy_engine.py:13`,
`governing_law_policy_engine.py:14`, `termination_policy_engine.py:12`,
`warranties_policy_engine.py:6`, `sla_policy_engine.py:8`,
`assignment_policy_engine.py:9` — read in full before writing any
verifier prompt, not assumed from the mission brief's examples alone):

- **confidentiality**: who is obligated to protect whose confidential
  information; definition scope; exclusions (public domain, independently
  developed, rightfully received); use restriction; disclosure exceptions
  (legal compulsion, professional advisors); duration (including
  survival past termination); return/destruction obligations.
- **payment_terms**: payment period; disputed-amount handling; offset/
  setoff rights; tax allocation (gross-up vs. inclusive); late fees/
  interest; price-increase conditions; which of several payment-related
  catalog items are independently present vs. absent.
- **ip_ownership**: background IP vs. work product ownership; license
  grants (scope, exclusivity, field of use); residual-rights carve-outs;
  which party owns what given the two genuinely independent questions
  this adapter's own docstring identifies (see file for the exact two).
- **insurance**: required coverage types; minimum limits; additional-
  insured requirements; certificate/evidence-of-insurance obligations;
  schedule/exhibit cross-references for coverage detail.
- **data_security**: security-standard obligations; breach-notification
  triggers and timelines; subprocessor flow-down requirements; data-use/
  transfer restrictions — four largely independent catalog items per the
  engine's own four anchor regexes (`_SUBPROCESSOR_ANCHOR_RE`,
  `_BREACH_ANCHOR_RE`, `_TRANSFER_ANCHOR_RE`, `_SECURITY_ANCHOR_RE`).
- **governing_law**: governing jurisdiction; forum/venue; mandatory vs.
  permissive forum language; conflict-of-laws qualifiers.
- **termination**: termination for convenience vs. for cause; cure
  periods; notice requirements; survival clauses; post-termination
  obligations — independent catalog items per
  `_SURVIVAL_ANCHOR_RE` existing as its own anchor.
- **warranties**: express warranties made; disclaimers (including
  ALL-CAPS conspicuousness conventions); warranty duration; remedies for
  breach; carve-outs/exceptions to disclaimers.
- **sla**: uptime/service-level commitment; measurement methodology;
  exclusions (scheduled maintenance, force majeure); service credits/
  remedies; sole-remedy language — per the engine's own "three independent
  fact families, deliberately never conflated" docstring framing.
- **assignment**: consent requirements; affiliate/change-of-control
  exceptions; assignment-by-operation-of-law treatment; successor-and-
  assigns binding language.

For each, integration should follow the exact 5-step discipline in
ARCHITECTURE.md's "Rollout discipline" section, in the same order liability
was done: absence_state field -> gated real-provider call -> anchor-only
semantic contribution (never bypassing existing structuring) ->
RECOGNITION_UNCERTAIN routes to REQUIRES_REVIEW -> adapter-specific tests
including the descriptive-language regression family.

This is deliberately not attempted in this pass. Each adapter's
`evaluate_*_policy` structuring logic must be read in full before its
semantic verifier propositions can be written correctly — doing all 10 in
one sitting without that reading would repeat the mission's own warned-
against anti-pattern (benchmark-patching without understanding).
