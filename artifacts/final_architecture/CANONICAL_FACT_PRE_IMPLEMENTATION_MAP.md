# CANONICAL_FACT_PRE_IMPLEMENTATION_MAP

Re-verified directly against current code on `claude/final-trust-architecture-cutover`
(commit `346c509`), not assumed from prior artifacts.

## The exact gap, confirmed precisely

`fact_admission.py`'s `CandidateMaterialFact` dataclass (lines 172-179)
already declares `condition`, `proviso`, `exception`, `exclusion`,
`limitation`, `cross_reference`, `schedule_dependency`,
`competing_interpretation` fields. **No code path ever writes to them.**

Confirmed by reading `verify_candidate_proposition()`
(`fact_admission.py:435-474`) end to end: its JSON schema instructs the
model to *consider* conditions/provisos/exceptions/cross-references when
deciding the `status` verdict (e.g. "there is a material condition,
proviso, exception, exclusion, or limitation" is listed as a reason to
NOT conclude ESTABLISHED), but the response schema itself only has three
fields: `status`, `evidence_quote`, `reasoning`. If the model notices a
material condition and correctly downgrades its verdict to
`INSUFFICIENT_CONTEXT`/`AMBIGUOUS`/etc., that is the ONLY trace of the
condition that survives — its actual content (what the condition says,
where it is, whether it can be grounded) is discarded. `verify_and_ground()`
(`fact_admission.py:570+`) never assigns anything to
`candidate.condition`/`.exception`/etc. This is the exact defect this
mission exists to close.

## Per-adapter status

| Adapter | Current discovery | Current AI/semantic path | Current candidate schema | Current grounding | Current evaluator input | Qualifiers preserved? | Conditions preserved? | Exceptions preserved? | Definitions preserved? | Cross-refs preserved? | Party roles preserved? | Competing readings preserved? | Gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| liability | regex anchors + `fact_admission` (off by default) | verify_candidate_proposition, status only | `CandidateMaterialFact` (unused fields) | exact-substring on evidence_quote only | `LiabilityFacts` — already has its OWN deterministic `condition: Optional[ConditionEvidence]` (policy_engine_core), populated by regex, NOT by the AI path | Partial — deterministic path only | Partial — deterministic `ConditionEvidence` only, not AI-sourced | No | No | No | No (role resolution is deterministic-only) | No | AI never contributes qualifier data; only deterministic regex does |
| indemnification | own separate mechanism (semantic_discovery_real.py) + deterministic structural verification | discovery only, no adversarial qualifier extraction | `DiscoveryCandidate` (span only, no qualifier fields at all) | exact-substring on quote | `IndemnificationFacts` — deterministic `ConditionEvidence`-style detection exists (per module docstring) | No — AI path is span-only by design | No | No | No | No | Deterministic only | No | Architecturally furthest from the target — AI layer has no qualifier vocabulary at all, by original design |
| confidentiality | regex (`_EXCLUSION_RE` dict of 4 topics) + `fact_admission` (off) | status only | `CandidateMaterialFact` (unused fields) | exact-substring only | `ConfidentialityFacts.exclusions_present: Dict[str,bool]` — deterministic only | No | N/A (no condition concept modeled) | Partial — deterministic only, 4 fixed exclusion topics | No | No | Deterministic only | No | AI never contributes; adapter's own exclusion vocabulary is a fixed enum, not free-text |
| payment_terms | regex + concept-engagement res + `fact_admission` (off) | status only | `CandidateMaterialFact` (unused fields) | exact-substring only | `PaymentFacts.condition: Optional[ConditionEvidence]` — deterministic only | Partial | Partial — deterministic only | No | No | No | Deterministic only | No | Same pattern as liability |
| ip_ownership | regex + `fact_admission` (off) | status only | unused fields | exact-substring only | `IPFacts` — no condition/exception dataclass field at all | No | No | No | No | No | Deterministic only | No | No qualifier concept modeled at all today |
| insurance | regex + `fact_admission` (off) | status only | unused fields | exact-substring only | `InsuranceFacts` — no condition/exception field | No | No | No | No | No | Deterministic only | No | Same |
| data_security | regex + `fact_admission` (off) | status only | unused fields | exact-substring only | `DataSecurityFacts` — no condition/exception field (has `dpa_cross_reference: bool` flag only, no resolved text) | No | No | No | No | Boolean flag only, no resolution | Deterministic only | No | Cross-reference is a bare boolean, not resolved text |
| governing_law | regex + `fact_admission` (off) | status only | unused fields | exact-substring only | `GoverningLawFacts` — no qualifier concept | No | No | No | No | No | N/A (no directionality) | No | Simplest adapter; no qualifier concept applies materially except forum/venue nuance, unmodeled |
| termination | regex (whole-document) + `fact_admission` (off) | status only | unused fields | exact-substring only | `TerminationFacts` — has `TerminationFee`/`SurvivalTreatment` structured sub-objects (deterministic), no generic condition field | Partial | No generic concept; cure-period IS captured deterministically | No | No | No | Deterministic only | No | Has adapter-specific structured qualifiers already deterministic, not AI-fed |
| warranties | regex (local-window-gated) + `fact_admission` (off) | status only | unused fields | exact-substring only | `WarrantiesFacts.disclaimer_carveout_present: Optional[bool]` — boolean flag, no resolved text | No | No | Boolean flag only | No | No | Deterministic only | No | Carveout presence is boolean, not structured/resolved |
| sla | regex + `fact_admission` (off) | status only | unused fields | exact-substring only | `SLAFacts` — has 4 named exclusion booleans (scheduled/emergency maintenance, customer-caused, force majeure) | Partial (fixed enum) | No | Partial — fixed 4-category boolean set | No | No | N/A | No | Fixed exclusion taxonomy, not free-text AI-identified qualifiers |
| assignment | regex (whole-document) + `fact_admission` (off) | status only | unused fields | exact-substring only | `AssignmentRestriction.exceptions_present: Dict[str,bool]` — deterministic only | No | No | Partial — deterministic only | No | No | Deterministic only | No | Same shape as confidentiality |

## Conclusion

**0/12 adapters today have the AI contextual layer contributing ANY
qualifier/condition/exception/definition/cross-reference/competing-reading
data to an admitted fact.** Every adapter that models a qualifier concept
at all does so entirely deterministically (regex-only), which is
correct and unchanged — the gap is specifically that the mission's Phase
2-4 requirement (AI identifies qualifiers, deterministic grounding proves
them, admitted fact preserves them) has no implementation anywhere yet.
This confirms and sharpens the residual risk already flagged in the
prior branch's `RESIDUAL_RISK_REGISTER.md` item 3.

## Scope decision for this pass

Given the size of full 12-adapter qualifier-grounding implementation with
adversarial proof per adapter (Phase 6/7/8/9/10/11 each require this per
adapter), this pass builds and proves the complete chain for **one
reference adapter (liability)**, chosen because it already has the most
mature deterministic qualifier machinery
(`policy_engine_core.ConditionEvidence`) to integrate the new AI-sourced
qualifier data against, and because it is the mission's own
architecture's proven reference adapter from the prior two phases. The
remaining 11 adapters are NOT claimed complete — see
CANONICAL_FACT_PROOF_MATRIX.md for the conservative, per-adapter PASS/FAIL
accounting the mission's Phase 11 requires.
