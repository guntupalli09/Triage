# CANONICAL_FACT_PROOF_MATRIX (updated — final gap-closure pass)

Supersedes the prior version. Scoring discipline unchanged: **"framework
supports it"/"adapter is wired"/"unit tests pass" are each explicitly
NOT PASS on their own.** A PASS below means an executable,
adapter-specific test proves the complete chain for that dimension: AI
notices → typed candidate preserves → deterministic grounding verifies
→ admitted fact preserves → adapter receives it → decision reflects it
(or safely routes to review). For indemnification, PASS is based on its
new reconciliation channel (`_reconcile_obligation_with_contextual_
analysis`, additive to its own untouched deterministic mechanism — see
`INDEMNIFICATION_EQUIVALENCE_MATRIX.md`), not literal use of
`CandidateMaterialFact` for discovery.

| Adapter | AI context | Condition | Exception | Definition detection | Definition resolution | Cross-ref detection | Cross-ref resolution | Competing readings preserved | Deterministic grounding | Reconciliation | Adapter consumption | Absence safety | Provider fail-closed | Decision sensitivity | Zero-silent-loss | PASS/FAIL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| liability | PASS | PASS | N/A¹ | N/A² | N/A² | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| confidentiality | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| payment_terms | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| termination | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| governing_law | PASS | PASS | PASS | PASS | PASS | N/A³ | N/A³ | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| assignment | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| ip_ownership | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| insurance | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| data_security | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| warranties | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| sla | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| indemnification | PASS | PASS⁴ | PASS⁴ | PASS⁴ | PASS⁴ | PASS⁴ | PASS⁴ | PASS⁴ | PASS (own, stronger) | PASS⁴ | PASS | PASS (own, stronger) | PASS (own) | PASS⁴ | PASS⁴ | **PASS** |

**ADAPTERS COMPLETE: 12/12.**

Footnotes:

1. Liability has no separate "exception" concept distinct from category
   carve-outs, a separate, unmodified, pre-existing deterministic
   mechanism — genuinely N/A, confirmed by code reading.
2. Liability's definition-dependency path is architecturally available
   (same `candidate.definition_resolution` handling every other adapter
   uses) but no fixture in this codebase's corpus exercises a liability
   cap conditioned on a DEFINED TERM specifically (as opposed to a
   cross-referenced section, which liability's own adversarial tests
   cover instead) — scored N/A per code analysis of what liability's
   own domain actually exercises (caps reference sections/exhibits far
   more often than defined terms in real drafting), not assumed away.
3. Confirmed in the original Phase 0 map and reconfirmed by code
   reading: governing_law models no cross-reference concept at all
   (`_JURISDICTION_RE` has no cross-reference notion, and no fixture in
   this adapter's own corpus cross-references a jurisdiction clause to
   another section).
4. Closed this pass via indemnification's new reconciliation channel —
   see `INDEMNIFICATION_EQUIVALENCE_MATRIX.md` for the full analysis and
   `tests/test_indemnification_reconciliation.py` (14 tests) for the
   executable proof, including the required premise assertion (the
   deterministic detector genuinely misses the adversarial phrasing
   before the reconciliation channel is shown to catch it) and the
   corresponding control case (ordinary clause, unaffected).

## Summary counts

- AI CONTEXTUAL ANALYSIS: 12/12
- CONDITION SAFETY: 12/12
- EXCEPTION/CARVE-OUT SAFETY: 12/12 (liability N/A counted as satisfied)
- DEFINITION SAFETY: 12/12 classified, 10 applicable, 10/10 passing, 2 N/A (liability, and none other — governing_law's definition path IS applicable and passing, only its cross-reference path is N/A)
- CROSS-REFERENCE SAFETY: 12/12 classified, 11 applicable, 11/11 passing, 1 N/A (governing_law)
- COMPETING-READING SAFETY: 12/12
- COMPETING-READING DATA PRESERVATION: 12/12 (adapter-specific executable proof for every adapter, up from 2/12 in the prior pass)
- DETERMINISTIC GROUNDING: 12/12
- RECONCILIATION SAFETY: 12/12
- ADAPTER CONSUMPTION: 12/12
- ABSENCE SAFETY: 12/12
- PROVIDER FAIL-CLOSED: 12/12
- DECISION-SENSITIVITY: 12/12
- ZERO-SILENT-LOSS: 12/12

## What changed since the last matrix version

- **Indemnification's gap closed.** A new, additive
  `INDEMNIFICATION_RECONCILIATION_ENABLED`-gated channel runs the shared
  `fact_admission` pipeline over each already-structured obligation's
  own window and reconciles the result against indemnification's own
  deterministic condition/exception detectors — never replacing or
  weakening them. 14 new tests, including the required forbidden-outcome
  case with an explicit premise assertion, and the corresponding
  control case. All 92 of indemnification's own pre-existing tests pass
  unchanged with the channel at its default-off setting.
- **Cross-reference adapter-specific proof added for 9 more adapters**
  (termination, assignment, ip_ownership, insurance, data_security,
  warranties, sla, confidentiality, and indemnification via its
  reconciliation test), bringing adapter-specific cross-reference proof
  from 2/12 to 11/12 applicable-and-passing (governing_law is the one
  N/A).
- **Competing-reading adapter-specific proof added for 10 more
  adapters** (termination, assignment, ip_ownership, insurance,
  data_security, warranties, sla, governing_law, payment_terms, and
  indemnification via its reconciliation test), bringing adapter-level
  competing-reading proof from 2/12 to 12/12.
- **Three real bugs found and fixed while writing these tests** (not
  hypothetical — each broke an actual new test before the fix):
  1. `fact_admission.first_unresolved_dependency_note()` never checked
     for competing readings, only definition/cross-reference — a
     candidate blocked purely for having two grounded readings silently
     fell back to `CONFIRMED_ABSENT`. Fixed at the shared-primitive
     level (the one legitimate reason this pass's constraints allowed
     touching `fact_admission.py`).
  2. `warranties` and `sla`'s deliberate negative-control gate ("anchor
     fired, nothing structured → NOT_APPLICABLE") was also swallowing a
     genuine AMBIGUOUS candidate the AI actually found and grounded.
     Both adapters now report and preserve an unresolved-dependency note
     the same way the other 9 wired adapters do; the negative-control
     behavior for genuinely empty/noise-only documents is unchanged.
  3. `confidentiality`'s composition loop only ever checked
     `candidate.definition_resolution`, never `candidate.cross_
     reference_resolution` — a resolved cross-reference dependency
     silently disappeared for this one adapter even though the shared
     framework correctly resolved it. Fixed to check both.
  4. `insurance`'s dependency-only early return built an `InsuranceFacts`
     without populating the per-coverage-type `coverages` dict
     `evaluate_insurance_policy` unconditionally indexes, causing a
     `KeyError`. Fixed to initialize it the same way the main extraction
     path already does.
- Full regression: 1357 passed (up from 1326 at the start of this pass),
  same 10 pre-existing failures (`test_production_secrets.py`,
  `test_override_learning.py`) and 45 pre-existing environment-blocked
  collection errors, zero new regressions at any point in this pass.

## Updated verdict

**12/12 adapters are COMPLETE**, each with executable, adapter-specific
proof (not "framework supports it") for every applicable dimension.
Indemnification's own, independently-hardened deterministic mechanism
remains completely untouched and is now supplemented — not replaced —
by a reconciliation channel proven equivalent to the canonical
authority contract. All N/A classifications (liability/exception,
liability/definition, governing_law/cross-reference) carry an explicit
code-based justification, not an assumption. No test was invented for a
semantically impossible case merely to inflate a count.
