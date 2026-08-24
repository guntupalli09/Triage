# LEE_QUESTION_MATRIX

Verdicts limited to PROVEN / PARTIALLY PROVEN / DISPROVEN / NOT PROVABLE,
per this continuation phase's instruction. Every question's LIVE PRODUCT
OBSERVATION and SCREENSHOT fields are "NOT AVAILABLE — no live-product
validation was performed this session" (see LIVE_PRODUCT_PROOF_REPORT.md)
and every FROZEN CORPUS RESULT field is "NOT AVAILABLE — no frozen corpus
was executed this session" (see FROZEN_CORPUS_MANIFEST.md /
FROZEN_VALIDATION_REPORT.md). These are not repeated per-row below except
where a question's answer specifically depends on that missing evidence
mattering more or less.

---

### Q1. What stops a confidently wrong extraction from becoming a confidently wrong deterministic ruling?

**VERDICT: NOT PROVABLE** (in this session)

**CODE MECHANISM**: `fact_admission.evaluate_admission()` requires
adversarial-verifier `ESTABLISHED` + independent grounding pass + no
unresolved dependency/conflict before a candidate is admitted; even then,
an admitted candidate only seeds the adapter's own pre-existing
deterministic structuring (e.g. `liability_policy_engine._extract_provision`),
never bypassing it. See AUTHORITY_BOUNDARY.md §3-4.

**TARGETED TEST**: every adapter's `test_verifier_not_established_
descriptive_language_never_admitted` shows a *mocked* NOT_ESTABLISHED
verdict is correctly never admitted, using one naturally-varied
descriptive sentence per adapter (11 distinct constructions, not the same
sentence repeated).

**WHAT THIS PROVES**: the pipeline's mechanical response to a
NOT_ESTABLISHED verdict is correct and structurally cannot be bypassed.

**WHAT THIS DOES NOT PROVE**: that a *real* model, given genuinely novel
descriptive/background language it has never seen in this codebase's
development, would actually classify it NOT_ESTABLISHED rather than
ESTABLISHED. The mission explicitly requires this be shown against an
untouched adversarial family with live-model evidence, which this session
did not obtain (see FROZEN_CORPUS_MANIFEST.md). Marking this PROVEN on
mocked evidence alone would be exactly the overclaim the mission warns
against ("do not claim PROVEN merely because the known example now routes
correctly").

**RESIDUAL RISK**: a real model could be more confirmation-biased or more
easily confused by adversarial phrasing than the mocked tests assume.
This risk is unquantified until a live-model run occurs.

---

### Q2. What counts clauses that aren't there?

**VERDICT: PARTIALLY PROVEN**

**CODE MECHANISM**: `document_aggregation.aggregate_document_state`'s
`DOC_CONFIGURATION_UNRESOLVED` state and each adapter's `NOT_APPLICABLE`
decision state are the only "absent" signals; both require either (a) an
ACTIVE playbook position never having produced a decision at all
(structurally different from a decision existing and saying "absent"), or
(b) `CONFIRMED_ABSENT`, which — as of this session — is reachable in every
one of the 11 newly-integrated adapters only when semantic discovery ran
successfully and also found nothing (see ADAPTER_MATRIX.md's absence
matrix). Indemnification has its own equivalent, pre-existing mechanism.

**TARGETED TEST**: `test_confirmed_absent_when_discovery_runs_and_finds_
nothing` (all 11 adapters) plus `test_provider_unavailable_is_
recognition_uncertain` proving the negative case (provider outage does
NOT count as absent).

**WHAT THIS PROVES**: the code path from "nothing found" to "reported as
absent" now requires a passed, not merely attempted, semantic check, for
every production adapter — not just the two that had this before this
session (indemnification pre-existing, liability from the prior session).

**WHAT THIS DOES NOT PROVE**: that the semantic-discovery step, when
actually enabled and run against a real model on real contracts, achieves
adequate recall — i.e., that it doesn't itself miss genuinely present
clauses and wrongly let them reach CONFIRMED_ABSENT. That is a live-model
recall question, not a code-boundary question, and is unmeasured (see
Q1's residual risk — same underlying gap).

**RESIDUAL RISK**: every flag defaults `False`; in current production
configuration, "what counts clauses that aren't there" is still governed
entirely by each adapter's pre-existing regex vocabulary, exactly as
before this session, until a flag is deliberately enabled.

---

### Q3. What happens when the clause exists but the system fails to recognize it?

**VERDICT: PARTIALLY PROVEN**

**CODE MECHANISM**: `RECOGNITION_UNCERTAIN` (all 12 adapters) is
distinguished from `CONFIRMED_ABSENT`/`NOT_APPLICABLE` and routes to
`REQUIRES_REVIEW` in every adapter — verified per-adapter in the absence
matrix (ADAPTER_MATRIX.md), with two verified sub-patterns: an existing
safe branch absorbing it (4 adapters) or a new explicit branch added this
session (7 adapters, because their existing "nothing structured" path
either could reach ACCEPT under a permissive playbook, or is a deliberate
NOT_APPLICABLE negative control that must not be confused with a genuine
provider failure).

**TARGETED TEST**: `test_recognition_uncertain_routes_to_requires_review*`
for all 11 newly-integrated adapters (indemnification's own pre-existing
suite covers this for that adapter).

**WHAT THIS PROVES**: *when the semantic layer runs and errors*, failure
to recognize is never silently reported as absence, for any of the 12
production adapters.

**WHAT THIS DOES NOT PROVE**: the case the question is really asking about
— a clause that genuinely exists, phrased in a way BOTH the regex AND (if
enabled) the semantic layer fail to recognize, with no error raised (the
semantic layer runs cleanly and simply also misses it). That is a recall
question requiring live-model + real-contract evidence this session
doesn't have, and it is the single most direct manifestation of Finding 8
from the original audit — reduced in surface area (12/12 adapters now
have SOME semantic check where regex fails, vs. 1/12 before), not
eliminated.

**RESIDUAL RISK**: recall of the semantic layer itself, against real
adversarial phrasing, is unmeasured. Prior evidence (Step 4A.9.2, cited
in PRE_IMPLEMENTATION_MAP.md §15a.2) suggests semantic discovery
meaningfully improves recall-into-review but has not been shown to fully
close a recall gap.

---

### Q4. How do you know evidence attached to a decision actually supports the fact?

**VERDICT: PROVEN** (for the fact-admission layer specifically; see
scope note)

**CODE MECHANISM**: `fact_admission.ground_evidence_quote()` performs an
exact substring search of the verifier's cited evidence against the
untouched source document — independent of the verifier's own claim.
`evaluate_admission()` refuses admission on any grounding failure
regardless of the verifier's stated status.

**TARGETED TEST**: `test_verify_and_ground_end_to_end_fabricated_evidence_
not_admitted` (shared framework) and each adapter's `test_hallucinated_
candidate_never_becomes_a_*` — a verifier claiming ESTABLISHED with a
quote that does not appear in the document is caught and blocked in every
case tested (0 exceptions across 11 adapters + the shared module).

**WHAT THIS PROVES**: the specific mechanism this mission asked for
(mechanical, non-AI verification of AI-cited evidence) exists, is applied
uniformly across all 12 adapters, and is unit-tested to actually catch a
fabrication attempt.

**WHAT THIS DOES NOT PROVE**: that evidence attached to a *pre-existing,
regex-only* decision (the vast majority of decisions today, since every
flag defaults off) has ever been mechanically re-verified this way — this
grounding mechanism only applies to the new semantic pathway, not to
regex-sourced facts, which rely on the regex match itself being the
evidence (a pre-existing, unchanged property of this codebase, not newly
introduced or newly audited in this pass).

**RESIDUAL RISK**: none new from this pass; scope is correctly bounded to
what was actually built.

---

### Q5. Can the semantic/LLM layer ever acquire policy authority?

**VERDICT: PROVEN**

**CODE MECHANISM**: `fact_admission.py`'s entire output vocabulary
(`ESTABLISHED`/`NOT_ESTABLISHED`/`AMBIGUOUS`/`INSUFFICIENT_CONTEXT`/
`CONFLICTING`/`DEPENDENCY_UNRESOLVED`/`VERIFICATION_ERROR`/`ADMITTED`/
`NOT_ADMITTED`) contains no `policy_engine_core` decision state; the
`_FORBIDDEN_FIELD_NAMES` guard on `CandidateMaterialFact` plus
`assert_authority_boundary_intact()` structurally prevent the schema from
ever growing an authoritative field (same pattern as the pre-existing
`semantic_discovery.DiscoveryCandidate` guard). Every adapter's semantic
path only ever contributes a span into an unmodified, pre-existing
deterministic structuring function.

**TARGETED TEST**: `test_authority_boundary_intact` (shared module) plus
every adapter's admitted-but-unstructurable test showing the AI's
"opinion" that a candidate is ESTABLISHED still cannot produce a decision
if the deterministic structuring fails.

**WHAT THIS PROVES**: no code path exists, in any of the 12 adapters,
from an AI call's return value directly to `ACCEPT`/`NEGOTIATE`/
`MUST_REDLINE`/`PROHIBITED`/`ESCALATE`.

**WHAT THIS DOES NOT PROVE**: that a *future* code change couldn't
introduce such a path — this is a structural property of the code as
written, verified by inspection and test, not an invariant enforced by a
runtime guard the way the field-name check is. (Recommendation, not
executed in this pass: a repo-wide static check that no `evaluate_*_policy`
function reads a semantic-verification field directly into its `state=`
argument.)

**RESIDUAL RISK**: low but not zero — relies on code review discipline
for future changes, not an automated enforcement mechanism beyond the
dataclass field guard.

---

### Q6. What happens when two individually extracted policy facts need to be considered together?

**VERDICT: PROVEN** (mechanism pre-existing and unmodified; verified, not
assumed)

**CODE MECHANISM**: `interaction_engine_core.py` (not modified this
session) — `_gate_participants()` requires every participating clause
type to have a `PolicyDecision` in a safe state before a cross-clause rule
runs at all; any participant in `REQUIRES_REVIEW` renders the whole
interaction `INSUFFICIENT_FACTS`, never a guess. This session's new
`RECOGNITION_UNCERTAIN`→`REQUIRES_REVIEW` routing in all 12 adapters means
an uncertain fact now correctly starves any interaction rule depending on
it, across all 12 adapters, not just the 2 that had this property before.

**TARGETED TEST**: `tests/test_interaction_engine_core.py` (pre-existing,
re-run this session, passes unchanged).

**WHAT THIS PROVES**: the cross-fact combination mechanism is sound and
now benefits from 12/12 adapters correctly marking uncertainty, not 2/12.

**WHAT THIS DOES NOT PROVE**: end-to-end behavior with the new semantic
paths actually enabled and actually producing `RECOGNITION_UNCERTAIN`
facts feeding into `interaction_engine_core.evaluate()` in a live run —
not exercised together in this session (each was tested in isolation).

**RESIDUAL RISK**: low — the interfaces are the same `PolicyDecision`
objects either way, so integration risk is limited to the code paths
already tested individually, but no combined test exists.

---

### Q7. What happens when two parties look symmetric but differ on one material dimension?

**VERDICT: PROVEN** (pre-existing mechanism, unmodified and unweakened
by this session)

**CODE MECHANISM**: `policy_engine_core.detect_role_attributed_asymmetry`
(used by confidentiality/termination/warranties/assignment/indemnification)
and each adapter's own asymmetry-reason tracking route a detected
per-party divergence to `REQUIRES_REVIEW` with the specific reason named.
Not modified this session — verified still intact via each adapter's
unchanged regression suite (e.g. `tests/test_liability_policy_engine.py`'s
directional-position tests, `tests/test_assignment_conflict_resolution_
regression.py`).

**WHAT THIS PROVES**: this pre-existing safety property was not disturbed
by adding the semantic-discovery layer to 11 adapters — confirmed by
100% of each adapter's pre-existing regression suite passing unchanged.

**WHAT THIS DOES NOT PROVE**: that a semantically-*discovered* candidate
(as opposed to a regex-found one) correctly triggers asymmetry detection
— the semantic layer only ever seeds the SAME window a regex anchor would,
so the mechanism should apply identically, but no test in this session
specifically constructs a semantically-discovered asymmetric pair to
confirm it.

**RESIDUAL RISK**: low, by structural argument, but unconfirmed by a
direct test.

---

### Q8. Can a condition, proviso, schedule, cross-reference, definition, exception, or qualifier be silently stripped from the authoritative fact?

**VERDICT: PARTIALLY PROVEN**

**CODE MECHANISM**: `CandidateMaterialFact` carries dedicated fields for
`condition`/`proviso`/`exception`/`exclusion`/`limitation`/
`cross_reference`/`schedule_dependency`/`competing_interpretation` (per
the mission's own schema requirement, Step 1). However: **none of the 11
newly-integrated adapters currently populate these fields** — the
semantic layer in this pass only ever proposes a *span* (discovery) and a
*yes/no verdict on one proposition* (verification); it does not yet
extract or preserve sub-facts like conditions/provisos onto the
`CandidateMaterialFact` object itself. Those remain the responsibility of
each adapter's own pre-existing deterministic structuring (e.g.
`policy_engine_core.detect_condition_in_span`, unmodified), which DOES
already detect and preserve conditions for regex-found provisions — and,
since an admitted semantic candidate seeds the identical structuring
function, that pre-existing condition-detection logic runs over
semantically-discovered text too.

**TARGETED TEST**: none in this session specifically constructs a
semantically-discovered clause with an embedded condition/proviso to
confirm the pre-existing detector still fires on it.

**WHAT THIS PROVES**: the schema has the fields (Step 1 compliance), and
the pre-existing per-adapter condition detectors are structurally
positioned to run on semantically-discovered text.

**WHAT THIS DOES NOT PROVE**: that this actually happens correctly in
practice — untested, and the `CandidateMaterialFact` fields for these
sub-facts are currently always `None` in every adapter's actual usage
(they are populated by the dataclass definition, not by any adapter's
code this session wrote).

**RESIDUAL RISK**: real. This is the most concrete architectural gap
found while answering this question honestly rather than asserting PROVEN
— worth flagging for a follow-on pass rather than glossing over.

---

### Q9. Can a user see a clean document even though some underlying policy evaluation is unresolved?

**VERDICT: PARTIALLY PROVEN**

**CODE MECHANISM**: `document_aggregation.aggregate_document_state`'s
false-clean invariant (pre-existing, unmodified) — any `REQUIRES_REVIEW`/
`EVALUATION_ERROR` policy decision anywhere routes the whole document to
`DOC_REQUIRES_REVIEW`, never `DOC_CLEAN`. This session extended the
"Needs Attention" badge (already on dashboard/history since commit
`d6f4875`, pre-existing) to the single-contract review page as well
(commit `a8ab2b5`), closing a real gap where that one surface didn't show
it.

**TARGETED TEST**: none for the review-page wiring specifically — verified
only via Jinja2 template parsing and manual review (see
REGRESSION_REPORT.md's honesty note); `document_aggregation.py`'s own
logic has no dedicated `tests/` file (its benchmark lives in
`artifacts/step4b/`, pre-existing, not re-run this session because it
isn't in the `tests/` collection path).

**WHAT THIS PROVES**: the underlying aggregation logic is sound (by prior
Step 4B validation, not re-derived this session) and now reaches all
three user-facing surfaces at the code level.

**WHAT THIS DOES NOT PROVE**: that a real user, on the real deployed
product, actually sees this badge correctly rendered — no live-product
screenshot exists (see LIVE_PRODUCT_PROOF_REPORT.md), and no automated
HTTP-level test exercises the `review_contract` route in this sandbox
(blocked by missing `fastapi`, see REGRESSION_REPORT.md).

**RESIDUAL RISK**: real, specifically for the review-page change (the
newest, least-tested part of this answer) — moderate confidence from
template-parse + code review, not full confidence from an executed test.

---

### Q10. Can today's policy configuration change the meaning of a historical review?

**VERDICT: PROVEN** (pre-existing mechanism, unmodified)

**CODE MECHANISM**: `Contract.policy_revision_metadata_json` (models.py,
pre-existing) pins `policy_position_id`/`revision_activated_at`/
`config_hash` per clause type at review time; `policy_enforcement.
config_hash_for_position()` computes that hash from the position's actual
content, never recomputed from today's playbook state. Not modified this
session.

**TARGETED TEST**: none run this session (pre-existing mechanism, out of
this session's change scope); reproducibility of this specific property
was not re-verified, only confirmed present by code inspection
(PRE_IMPLEMENTATION_MAP.md §9/§15a.6).

**WHAT THIS PROVES**: the mechanism exists and was not touched or
weakened by this session's changes.

**WHAT THIS DOES NOT PROVE**: full historical reproducibility for the NEW
semantic-verification layer specifically — `fact_admission.py`'s
verifications are not currently stamped with a `semantic_verifier_version`
or `verifier_prompt_schema_version` anywhere in `policy_revision_metadata_
json` (a known, previously-identified gap, PRE_IMPLEMENTATION_MAP.md §9,
not closed in this pass). A future prompt change to `fact_admission.py`
would not be distinguishable, in historical data, from today's version —
this is a real, un-closed reproducibility gap for the new layer
specifically, even though the pre-existing mechanism for everything else
is sound.

**RESIDUAL RISK**: real and specific — new semantic-layer decisions lack
version provenance. Low current impact (every flag is off, so no such
decision exists in production data yet) but must be closed before any
flag is enabled for real reviews.

---

### Q11. Where can the system STILL create false confidence?

**VERDICT: NOT PROVABLE** (as an exhaustive claim; specific instances
below ARE identified — this question must never be answered "nowhere,"
and it is not)

Identified, concrete residual false-confidence sources, in order of
materiality:

1. **Live-model recall is unmeasured** (Q1/Q3). If a real model
   systematically fails to flag a class of adversarial phrasing that this
   session's mocked tests happen to cover, false confidence in the
   architecture's actual protection would be higher than the mocked test
   suite suggests.
2. **Condition/proviso/exception preservation on semantically-discovered
   candidates is untested** (Q8) — a real gap where a material
   qualifier could theoretically be lost even though the schema has a
   field for it.
3. **The review-page badge wiring has no automated HTTP-level test** (Q9)
   — confidence in it rests on template-parsing and code review, not
   execution.
4. **No version provenance for semantic-layer decisions** (Q10) — a
   configuration/version-drift risk for future audits, not a present
   false-clean risk (since nothing is live yet).
5. **10 of 12 adapters' semantic path has never been exercised against a
   real model at all** — every test is mocked. The entire "does this
   architecture actually work against real adversarial language" question
   is open for those 10 adapters (liability has none-real-model evidence
   either, only mocked; indemnification alone has real 200-call evidence,
   from before this session).
6. **This session's own claim of "0 new regressions" is bounded by what
   this sandbox could run** — 45 test files requiring `fastapi`/
   `python-docx`/a working `cryptography` build could not be collected at
   all, so any regression specifically reachable only through those paths
   is unverified (REGRESSION_REPORT.md).

This list is the honest answer to "where can this still go wrong" — it is
not exhaustive by construction (an exhaustive list would itself be an
overclaim), but every item above is a specific, actionable gap rather than
a vague disclaimer.
