# Residual Risk Register (Candidate 3 remediation)

Honest accounting of what this remediation does NOT close, discovered during the fix itself (not retroactively minimized).

## 1. `is_operative_context`-family filtering gaps remain for 7 adapters (unchanged scope)

Per `artifacts/candidate2_remediation/CROSS_ADAPTER_SWEEP.md` (Candidate 2) and reconfirmed in this mission's burned-corpus replay: liability's own descriptive/hypothetical/negotiation/quoted-family false-positives (e.g. `limitation_of_liability-001` through `004`) are **pre-existing failures unrelated to Root Causes 1–3** — they existed identically before and after this remediation (confirmed via direct diff of the original Candidate 3 real-AI run vs. this remediation's burned-corpus replay). Liability, indemnification, and payment_terms already call `is_operative_context()`; the other 9 adapters remain only partially covered. This is out of THIS mission's explicit 3-root-cause scope and is recorded here as a distinct, separate defect class requiring its own future mission.

## 2. Liability's admitted-AI-candidate qualifiers are not merged when deterministic anchors already exist

Documented inline in `liability_policy_engine.py` (Candidate 3 remediation comment): when `accepted_anchors` is already non-empty, an ADDITIONALLY admitted semantic candidate's `condition`/`exception` are not merged onto any provision, because the qualifier-composition loop matches strictly by shared anchor offset. This is a narrower scope than the other 11 adapters' "always add AI's qualifiers regardless of which channel found the anchor" behavior. Liability does not have Root Cause 1's defect (an unparseable admitted candidate already routes to `MUST_REDLINE` via the "no numeric cap stated" branch), so this gap is about a potential missed CONDITION/EXCEPTION corroboration, not a primary-fact safety violation — but it is a real, acknowledged asymmetry.

## 3. `established_dimension_count`-style checks are per-adapter heuristics, not a single canonical rule

The `PRESENT_BUT_UNRESOLVED` fix was implemented per-adapter (insurance, payment_terms, ip_ownership, data_security, warranties, sla), each with its own list of "what counts as established." These lists were hand-derived from each adapter's own Facts dataclass and cross-checked against that adapter's existing test suite, but they are not automatically guaranteed to be exhaustive — a future Facts field added to one of these adapters without also being added to its corresponding "any established" check could silently reintroduce a narrower version of Root Cause 1 for that specific field. This is a maintainability risk, not a currently-known failure.

## 4. Provider-variance design accepts residual (safe) variance, not zero variance

Per `PROVIDER_VARIANCE_DESIGN.md`: the chosen design does not add multi-sampling, so a genuinely-present, unusually-phrased clause can still be found on one production review and missed on another (routing to `CONFIRMED_ABSENT` when missed, `PRESENT_BUT_UNRESOLVED`/`REQUIRES_REVIEW` when found). This is an accepted, documented recall limitation, explicitly distinguished from the FORBIDDEN clean-state variance this mission's hard gates target — but it means two reviews of the identical document can still produce two different (both individually safe) outcomes. Not fixed in this mission; would require either a corroboration/multi-sample design (explicitly weighed and rejected as disproportionate for a per-review cost increase) or a stronger single-call model/prompt.

## 5. Cross-adapter interaction rules only cover 4 of the 12 adapters pairwise

Confirmed directly in Section 11's interaction proof: `interaction_rules.LAUNCH_CATALOG` only pairs `(indemnification, limitation_of_liability)`, `(insurance, limitation_of_liability)`, `(payment_terms, sla)`, `(payment_terms, termination)`. The mission's requested `confidentiality x data_security` pairing has no rule at all. This is pre-existing scope, not something this remediation was asked to expand, but is recorded here as a gap in interaction coverage more broadly.

## 6. Real-provider repeatability testing in this mission is scoped, not exhaustive

Given the real, non-trivial cost and latency of real OpenAI calls (each adapter's discovery+verification round trip takes 1–5 real seconds), this mission's repeatability testing targets a meaningful but bounded sample rather than exhaustively re-testing every one of the 240 burned-corpus cases 5 times each (which would be 1,200 additional real calls). See `REAL_PROVIDER_REPEATABILITY.md` for the exact sample and result.
