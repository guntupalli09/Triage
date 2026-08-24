# CANONICAL_FACT_PROOF_MATRIX (updated)

Supersedes the prior version of this file. Scoring discipline unchanged:
**"framework exists"/"adapter is wired"/"unit tests pass" are each
explicitly NOT PASS on their own.** A PASS below means an executable
test proves the complete chain for that dimension: AI notices → typed
candidate preserves → deterministic grounding verifies → admitted fact
preserves → adapter receives it → decision reflects it (or safely routes
to review).

| Adapter | CANONICAL FACT INTEGRATED | AI CANDIDATE PRESERVED | CONDITION | EXCEPTION/CARVE-OUT | DEFINITION | CROSS-REFERENCE | PARTY GROUNDING | COMPETING READINGS | DETERMINISTIC GROUNDING | ADAPTER CONSUMES ADMITTED FACT | DECISION-SENSITIVITY TEST | PROVIDER-FAIL-CLOSED | FINAL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| limitation_of_liability | PASS | PASS | **PASS** | N/A¹ | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | **PASS** | PASS | **PASS** |
| indemnification | FAIL (own separate mechanism, deliberately not migrated) | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS (own mechanism) | N/A | FAIL | PASS (own mechanism) | **FAIL** |
| confidentiality | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| payment_terms | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| ip_ownership | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| insurance | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| data_security | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| governing_law | PASS | PASS | **PASS** | **PASS** | N/A⁴ | N/A⁴ | N/A⁴ | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| termination | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| warranties | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| sla | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |
| assignment | PASS | PASS | **PASS** | **PASS** | FAIL | FAIL² | FAIL | PASS (safety only)³ | PASS | PASS | PASS | PASS | **PASS** |

Footnotes (read before treating any FINAL=PASS as unconditional):

1. Liability has no separate "exception" concept distinct from category
   carve-outs, which remain a separate, unmodified, pre-existing
   deterministic mechanism — genuinely N/A for THIS dimension, not a gap.
2. **Cross-reference is FAIL for every adapter that models one.** The
   shared framework grounds a claimed `cross_reference_text` (exact-
   substring check that the reference mention itself is real — see
   `fact_admission.ground_qualifiers`), but NO adapter composes
   `candidate.cross_reference` into its Facts object or its decision.
   Target resolution (fetching what "Section 9" actually says) is not
   implemented for the AI-sourced path in any of the 12 adapters
   (liability's OWN deterministic `_resolve_cross_reference` is
   unrelated — regex-based, pre-existing, untouched).
3. "Competing readings" scores PASS only for the SAFETY property this
   mission's Step 6 cares most about: `fact_admission.evaluate_admission`
   already refuses admission on `AMBIGUOUS`/`CONFLICTING` verifier
   status (never arbitrarily picks one reading). It does NOT preserve
   both readings as structured data anywhere — that half of Step 6 is
   FAIL for all 12 adapters, honestly noted rather than folded into the
   PASS.
4. governing_law has no definition/cross-reference/party-grounding
   concept modeled in this adapter at all (confirmed in the Phase 0 map)
   — genuinely N/A, not a gap.

## What changed since the last matrix version

- 11/12 adapters (all except indemnification) now have an executable
  decision-sensitivity test (paired A/B or single-decision-assertion,
  per adapter's own architecture) proving a material condition survives
  discovery → verification → grounding → admitted fact → adapter →
  decision, with 0 occurrences of the forbidden path (modifier
  disappears → clean decision) across 144 targeted tests.
- Exception preservation now also proven (not just condition) via the
  shared framework's own `test_verify_and_ground_end_to_end_blocks_on_
  fabricated_exception` and each adapter's composition code, which
  treats `.condition`/`.exception` symmetrically.
- Definition handling and cross-reference TARGET resolution remain
  entirely unimplemented — this is the largest remaining gap, not
  closed in this pass, and is not disguised as anything better than
  FAIL above.

## Updated verdict

**12/12 PASS is NOT achieved** — indemnification is FAIL by deliberate
design choice (documented, not an oversight). **11/12 adapters achieve
FINAL=PASS for the dimensions this pass actually implemented**
(condition + exception preservation, with grounding, decision-
sensitivity, and provider-fail-closed behavior all proven executable) —
**but every one of those 11 PASS rows carries real, undisguised FAILs
for definition handling, cross-reference target resolution, and
competing-reading data preservation.** Calling this "architecture
complete" would be exactly the overclaim the mission prohibits; it is
reported here as a real, bounded, honestly-scoped advance instead.
