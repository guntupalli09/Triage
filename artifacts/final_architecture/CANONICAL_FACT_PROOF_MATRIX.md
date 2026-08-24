# CANONICAL_FACT_PROOF_MATRIX (updated — final-architecture-completion pass)

Supersedes the prior version of this file. Scoring discipline unchanged:
**"framework exists"/"adapter is wired"/"unit tests pass" are each
explicitly NOT PASS on their own.** A PASS below means an executable
test proves the complete chain for that dimension: AI notices → typed
candidate preserves → deterministic grounding verifies → admitted fact
preserves → adapter receives it → decision reflects it (or safely routes
to review).

This pass's mandate was four specific blockers: (1) definition
resolution, (2) cross-reference TARGET resolution, (3) competing-reading
DATA preservation, (4) indemnification migration. Each is scored
separately below, honestly, rather than folded into a single "final"
column that could hide a partial result.

## Shared-framework primitives (fact_admission.py) — all four blockers

| Dimension | Status | Evidence |
|---|---|---|
| `resolve_definition()` | **PASS** | `resolve_definition()` deterministically locates the actual `"Term" means/refers to...` clause via regex, independent of any AI claim about content; RESOLVED/NOT_FOUND/CONFLICTING all covered — `tests/test_fact_admission.py::test_resolve_definition_*` (4 tests) |
| `resolve_cross_reference_target()` | **PASS** | Resolves a Section/Clause/Article/Paragraph or Exhibit/Schedule/Appendix/Annex label to its own heading's text; RESOLVED/NOT_FOUND/CONFLICTING/MISSING_ATTACHMENT all covered — `test_resolve_cross_reference_target_*` (5 tests) |
| `ground_competing_readings()` | **PASS** | Grounds each of the verifier's up-to-two competing readings independently; preserves both as `CompetingReading` data regardless of grounding outcome — `test_ground_competing_readings_*` (2 tests) |
| `evaluate_admission()` zero-silent-loss gates | **PASS** | An unresolved definition, unresolved cross-reference, or ≥2 independently-grounded competing readings each independently block admission — never silently drop the dependency and admit the base proposition — `test_evaluate_admission_blocks_on_unresolved_definition_dependency`, `..._cross_reference`, `..._two_grounded_competing_readings`, plus the "only one reading grounded → not blocked" negative control |
| `verify_and_ground()` end-to-end wiring | **PASS** | Full AI→candidate→resolver→admitted-fact chain proven for: definition resolves (`test_verify_and_ground_end_to_end_resolves_definition_dependency`), definition unresolvable (`..._blocks_on_unresolvable_definition`), cross-reference resolves (`..._resolves_cross_reference_target`), cross-reference to missing attachment (`..._blocks_on_missing_attachment`), competing readings preserved as data (`..._preserves_competing_readings_as_data`) |
| Zero-silent-loss invariant, directly tested | **PASS** | `test_zero_silent_loss_invariant_definition_dependency_never_disappears` asserts the exact two-state disjunction from Step H (survives to admitted fact XOR admission blocked — no third state) |

`tests/test_fact_admission.py`: 70/70 passing (55 pre-existing + 15 new
this pass). Zero regressions in the shared module.

**The shared primitives are complete and proven at the framework level.**
What follows is honest per-adapter integration status — the mission's own
scoring discipline explicitly forbids treating "the framework exists" as
equivalent to "12/12 adapters use it."

## Per-adapter integration status

| Adapter | Definition dependency detection | Definition target grounding | Cross-reference detection | Cross-reference target grounding | Competing readings preserved | Zero-silent-loss (this adapter) |
|---|---|---|---|---|---|---|
| confidentiality | **PASS** | **PASS** | N/A¹ | N/A¹ | inherited (framework-level only) | **PASS** |
| limitation_of_liability | N/A² | N/A² | **PASS** | **PASS** | inherited (framework-level only) | **PASS** |
| indemnification | FAIL (own separate mechanism, not migrated — see below) | FAIL | FAIL | FAIL | FAIL | FAIL (own mechanism has its own, different, unmigrated safeguards) |
| payment_terms | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |
| ip_ownership | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |
| insurance | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |
| data_security | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |
| governing_law | N/A³ | N/A³ | N/A³ | N/A³ | inherited (framework-level only) | not applicable to this dimension |
| termination | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |
| warranties | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |
| sla | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |
| assignment | not wired | not wired | not wired | not wired | inherited (framework-level only) | not applicable to this dimension |

**ADAPTERS WITH DEFINITION HANDLING PROVEN END-TO-END: 1/12** (confidentiality)
**ADAPTERS WITH CROSS-REFERENCE TARGET RESOLUTION PROVEN END-TO-END: 1/12** (liability)
**ADAPTERS USING COMPLETE CANONICAL FACTS (all required dimensions, including definition/cross-reference/competing-reading where materially applicable): 0/12**

Footnotes:

1. Confidentiality has no cross-reference concept materially distinct
   from the definition-dependency case it already models (its own
   obligations don't cross-reference other sections in the fixtures/
   corpus this codebase exercises) — not proven either way this pass,
   scored N/A rather than a silent gap, but this N/A has NOT been
   independently verified by code analysis the way governing_law's was
   in the prior pass; treat as "not yet examined," not "confirmed
   irrelevant."
2. Liability's definition-dependency path is architecturally identical
   to its cross-reference path (both flow through the same `candidate.
   definition_resolution`/`candidate.cross_reference_resolution` handling
   added this pass — see the composition loop in `extract_liability_
   facts`), but no adversarial test exercises a definition (as opposed to
   cross-reference) dependency for this adapter — scored N/A only in the
   sense "not this pass's proof target," not "structurally impossible."
3. Confirmed in the original Phase 0 map: governing_law models no
   definition/cross-reference concept at all.

## Blocker 4 — indemnification migration: NOT DONE, reported honestly

`indemnification_policy_engine.py` runs its own pre-existing, heavily
adversarially-hardened discovery/verification pipeline
(`_run_semantic_discovery` → `semantic_discovery.py`/
`semantic_discovery_real.py`, `_verify_role_capture`'s multi-word role-
name budget/boundary logic, `_STRUCTURAL_RISK_TRANSFER_PATTERNS`'
doubled verbatim structural re-verification, its own `_detect_obligation_
condition`) that is architecturally independent of `fact_admission.py`
and was NOT built on the CandidateMaterialFact/VerificationResult schema
at any point.

This pass did **not** attempt the migration. Rationale, stated plainly
rather than hidden behind a partial attempt: migrating a ~3,000-line,
extensively corpus-hardened module (with its own condition detection,
role-name attribution, structural risk-transfer re-verification, and
"doubled verbatim verification" safeguards refined over many prior
steps referenced throughout this file's own history) onto a different
schema, inside this single pass, without the adversarial regression
corpus this module was originally validated against being re-run, is a
correctness risk this pass chose not to take. A rushed migration that
silently weakened role-name-boundary correctness or condition detection
would be a strictly worse outcome than leaving indemnification on its
own, already-proven, independent mechanism for one more pass.

**Recommendation for the next pass**, not attempted here: (a) diff
indemnification's own condition/role/structural safeguards against
fact_admission.py's qualifier-grounding/definition/cross-reference gates
line by line to build an explicit preservation checklist, (b) migrate
discovery only (candidate schema + verification), keeping indemnification's
own structural re-verification and role-name logic completely intact as
a post-admission structuring step (mirroring how liability's own
`_extract_provision` structuring already sits downstream of
`fact_admission.verify_and_ground` today), (c) run indemnification's own
existing adversarial/regression suites (not just the shared framework's)
before and after to prove zero regression, before ever touching
`SEMANTIC_PROVIDER`/`HYBRID_DISCOVERY_ENABLED`.

## What changed since the last matrix version

- All four shared-framework primitives for this pass's blockers
  (definition resolution, cross-reference target resolution, competing-
  reading data preservation, and the zero-silent-loss gate tying them
  together) are implemented and proven with 15 new executable tests in
  `tests/test_fact_admission.py`, none previously existing.
- Two adapters (confidentiality for definitions, liability for cross-
  references) were wired end-to-end onto these primitives, each with its
  own adversarial tests proving: the dependency resolves and forces
  review even though the base clause reads clean; the dependency fails
  to resolve (missing definition / missing attachment) and forces review
  rather than falling back to "no clause found."
- Indemnification was NOT migrated — see above.
- The remaining 10 adapters were NOT wired to definition/cross-reference/
  competing-reading handling this pass. Whether each dimension is
  materially applicable to each of those adapters has not been
  determined by code analysis (Section E's requirement) — this is
  reported as unknown/not-yet-examined, not silently assumed N/A.
- Full regression suite: 1312 passed, 10 pre-existing failures
  (unrelated: `test_production_secrets.py`, `test_override_learning.py`),
  45 pre-existing environment-blocked collection errors (missing
  `fastapi`/`python-docx`/working `cryptography` build in this sandbox) —
  identical baseline to every prior pass, zero new failures introduced.

## Updated verdict

**12/12 is NOT achieved on any of the four blockers' adapter-integration
dimensions.** The shared primitives this pass was asked to build are
complete, tested, and proven correct in isolation and through two
reference-adapter integrations (confidentiality/definitions,
liability/cross-references) — this is real, executable progress, not a
"framework exists" claim. But per the mission's own scoring discipline,
this does not entitle a claim of architecture completion:
indemnification remains fully unmigrated by deliberate, reasoned choice,
and 10 of 12 adapters have not been evaluated for whether definition/
cross-reference/competing-reading handling is even materially relevant
to them, let alone wired and tested.
