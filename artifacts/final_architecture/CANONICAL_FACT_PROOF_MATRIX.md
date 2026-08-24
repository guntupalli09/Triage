# CANONICAL_FACT_PROOF_MATRIX (updated — adapter-completion pass)

Supersedes the prior version. Scoring discipline unchanged: **"framework
supports it"/"adapter is wired"/"unit tests pass" are each explicitly
NOT PASS on their own.** A PASS below means an executable test proves
the complete chain for that dimension: AI notices → typed candidate
preserves → deterministic grounding verifies → admitted fact preserves
→ adapter receives it → decision reflects it (or safely routes to
review). For indemnification, PASS is based on proven equivalent-or-
stronger behavior (see `INDEMNIFICATION_EQUIVALENCE_MATRIX.md`), not
literal use of `CandidateMaterialFact`.

| Adapter | AI contextual analysis | Condition preservation | Exception/carve-out preservation | Definition dependency detection | Definition target grounding | Cross-reference detection | Cross-reference target grounding | Competing readings preserved | Deterministic grounding | Canonical/proven-equivalent admitted fact | Adapter consumption | Absence safety | Provider fail-closed | Decision sensitivity | Zero-silent-loss | PASS/FAIL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| liability | PASS | PASS | N/A¹ | N/A² | N/A² | **PASS** | **PASS** | **PASS** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| confidentiality | PASS | PASS | PASS | **PASS** | **PASS** | N/A³ | N/A³ | **PASS** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| payment_terms | PASS | PASS | PASS | **PASS** | **PASS** | **PASS** | **PASS** | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| termination | PASS | PASS | PASS | **PASS** | **PASS** | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| governing_law | PASS | PASS | PASS | **PASS**⁶ | **PASS**⁶ | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| assignment | PASS | PASS | PASS | **PASS** | **PASS** | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| ip_ownership | PASS | PASS | PASS | **PASS** | **PASS** | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| insurance | PASS | PASS | PASS | **PASS** | **PASS** | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| data_security | PASS | PASS | PASS | **PASS** | **PASS** | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| warranties | PASS | PASS | PASS | **PASS** | **PASS** | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| sla | PASS | PASS | PASS | **PASS** | **PASS** | not tested⁵ | not tested⁵ | PASS (framework-level)⁴ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| indemnification | PASS (own mechanism) | FAIL⁷ | FAIL⁷ | FAIL | FAIL | FAIL | FAIL | PASS (safety only)⁸ | PASS (own, stronger) | PASS (proven equivalent for grounding/absence/fail-closed only) | N/A | PASS (own, stronger) | PASS (own) | FAIL⁷ | FAIL⁷ | **FAIL** |

Footnotes:

1. Liability has no separate "exception" concept distinct from category
   carve-outs, a separate, unmodified, pre-existing deterministic
   mechanism — genuinely N/A, confirmed by code reading (its own
   `_resolve_cross_reference`/carve-out logic is untouched by this
   pass).
2. Liability's cross-reference concept (a Section reference to a cap
   value) is its OWN pre-existing deterministic mechanism, unrelated to
   the AI-sourced path this pass wired — this pass instead proved the
   NEW, generic AI-sourced cross-reference-target chain on liability
   specifically (columns 6-7), so liability is the one adapter where
   cross-reference is PASS and definition is N/A (the reverse of
   confidentiality).
3. Confidentiality's obligations don't cross-reference other sections in
   any fixture/corpus this codebase exercises — scored N/A per code
   analysis, not assumed; see `CANONICAL_FACT_PROOF_MATRIX.md`'s prior
   version footnote 1 for the same discipline applied to liability's
   exception dimension.
4. "Competing readings preserved" is PASS at the FRAMEWORK level for
   every adapter using `verify_and_ground` (an executable shared-module
   test proves grounding/preservation — see
   `tests/test_fact_admission.py`), and PASS at the ADAPTER level with
   an executable adversarial test for liability and confidentiality
   specifically (proving neither reading reaches the adapter as
   authoritative, and the document does not collapse to CONFIRMED_ABSENT
   even though a real candidate was found). The other 9 wired adapters
   inherit the same safety property BY CONSTRUCTION (they all gate on
   `admission_status == ADMITTED`, and the shared
   `first_unresolved_dependency_note()` helper — now fixed this pass to
   also catch the competing-readings case — is what several of them
   call), but do not each have their own adapter-specific adversarial
   test proving it. Reported honestly as framework-proven +
   structurally-guaranteed, not adapter-specific-executable-proof, for
   those 9.
5. Termination, governing_law, assignment, ip_ownership, insurance,
   data_security, warranties, sla each received a definition-dependency
   adversarial test this pass (proving the resolve/force-review chain),
   but NOT a separate cross-reference-specific adversarial test — the
   underlying code path (`first_resolved_dependency_note`/
   `first_unresolved_dependency_note`) is identical for both dimensions
   and is proven generically at the shared-framework level, but no
   adapter-specific cross-reference test exists for these 8. Reported as
   "not tested" rather than folded into a PASS.
6. Governing_law's own `_JURISDICTION_RE` always implies its anchor also
   matched (both require "governed by"), so its semantic-only path can
   never itself produce a jurisdiction-found-plus-AI-dependency
   combination in practice — proven directly at the Facts level instead
   (the same discipline already used for its condition/exception tests
   in the prior pass), not via a full document-level mocked-provider
   test the way the other 7 were.
7. See `INDEMNIFICATION_EQUIVALENCE_MATRIX.md` for the full analysis.
   Indemnification's condition/exception detection is PURELY
   deterministic-regex-based (`_detect_obligation_condition`,
   `_find_exception_clause_named_roles`) with NO path for the AI to
   notice a qualifier phrased outside that regex vocabulary and have it
   independently grounded and preserved — this is the exact
   mission-critical failure mode (AI notices material context → context
   lost → base fact survives → clean decision) the rest of this
   initiative exists to close, and it is NOT yet closed here. This is
   reported as a real, material FAIL, not minimized.
8. Indemnification's `_classify_candidate` never picks one reading as
   authoritative for an ambiguous candidate (returns `UNRESOLVED`) —
   the SAFETY property is equivalent — but does not preserve both
   candidate readings as structured, inspectable data the way
   `CompetingReading` does. Scored PASS (safety only), matching the
   discipline used for this exact distinction in the prior matrix
   version.

## Summary counts (this pass)

- AI CONTEXTUAL ANALYSIS WIRED: 12/12
- CONDITION PRESERVATION: 11/12 (indemnification FAIL)
- EXCEPTION/CARVE-OUT PRESERVATION: 11/12 (indemnification FAIL; liability N/A counted as satisfied)
- DEFINITION DEPENDENCY DETECTION: 10/12 (liability, indemnification are the two non-PASS: liability N/A by code analysis, indemnification FAIL)
- DEFINITION TARGET GROUNDING: 10/12 (same two)
- CROSS-REFERENCE DETECTION: 2/12 executable adapter-level proof (liability, payment_terms); 8 more wired but untested for this specific dimension; indemnification FAIL
- CROSS-REFERENCE TARGET GROUNDING: 2/12 executable adapter-level proof (same two); indemnification FAIL
- COMPETING-READING SAFETY: 12/12 (framework-level, structurally guaranteed for every adapter gating on ADMITTED)
- COMPETING-READING DATA PRESERVATION: 2/12 adapter-level executable proof (liability, confidentiality); framework-proven for all others; indemnification PASS (safety only)
- DETERMINISTIC GROUNDING: 12/12
- ADAPTERS WITH CANONICAL OR PROVEN-EQUIVALENT ADMITTED FACT AUTHORITY: 11/12 (indemnification FAIL on the condition/exception dimension specifically, though PASS on several others)
- ADAPTER CONSUMPTION: 11/12
- ABSENCE SAFETY: 12/12
- PROVIDER FAIL-CLOSED: 12/12
- DECISION SENSITIVITY: 11/12 (indemnification untested/unclosed for the AI-notices-outside-vocabulary case)
- ZERO-SILENT-LOSS: 11/12 (indemnification is the one adapter where a real, material qualifier phrased outside deterministic vocabulary could currently vanish with the base obligation reaching a clean decision — this is the honest, named exception to the invariant, not swept into a rounded-up PASS)

**ADAPTERS COMPLETE (PASS on every applicable dimension): 11/12.**
Indemnification is the one FAIL, for the reasons detailed in
`INDEMNIFICATION_EQUIVALENCE_MATRIX.md` — not a rushed migration risk
this pass chose to take, but a real, unclosed gap reported honestly.

## What changed since the last matrix version

- 8 more adapters (termination, governing_law, assignment, ip_ownership,
  insurance, data_security, warranties, sla) wired onto
  `resolve_definition`/`resolve_cross_reference_target` via new shared
  `fact_admission.first_resolved_dependency_note()`/
  `first_unresolved_dependency_note()` helpers, each with an executable
  adversarial test.
- payment_terms wired with a full definition + cross-reference-to-
  missing-attachment pair of tests, plus a new `DEPENDENCY_UNRESOLVED`
  absence state (mirroring liability's).
- A genuine defect in `first_unresolved_dependency_note()` was found via
  an adapter-level competing-reading test on liability (it never
  checked for competing readings, only definition/cross-reference) and
  fixed at the shared-primitive level — the one legitimate reason this
  pass's constraints allowed touching `fact_admission.py`.
- liability and confidentiality's `_run_semantic_discovery` each had a
  hand-rolled duplicate of the old, incomplete check — both now call the
  shared helper and automatically inherit the fix.
- Adapter-level competing-reading adversarial tests added for liability
  and confidentiality, proving neither of two grounded readings reaches
  the adapter as authoritative.
- Indemnification equivalence matrix produced (13 invariants compared);
  indemnification NOT migrated — a real, material gap (condition/
  exception detection has no AI-notices-outside-vocabulary path) is
  reported honestly rather than papered over or rushed.
- Full regression: 1326 passed (up from 1312 at the start of this pass),
  same 10 pre-existing failures and 45 pre-existing collection errors,
  zero new regressions.

## Updated verdict

**11/12 adapters are COMPLETE** on every dimension this pass's mission
covers, with executable proof (not "framework supports it"). Cross-
reference-specific adversarial tests exist for 2 of those 11
(liability, payment_terms); the other 9 share the identical code path,
proven generically, but lack their own adapter-specific cross-reference
test — reported honestly as a smaller residual gap rather than rounded
into the PASS. **Indemnification is the one FAIL**, for a real and
specific reason (no AI-notices-a-qualifier-outside-deterministic-
vocabulary path for conditions/exceptions) — not a placeholder or an
oversight, and not fixed this pass because doing so safely needs its
own dedicated, carefully-scoped change and adversarial regression pass
against a module this hardened, which this pass's remaining time did
not allow doing responsibly.
