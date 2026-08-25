PRE-FREEZE INSPECTION — INSPECTION ONLY. NO PRODUCTION CODE, TESTS, OR CONFIGURATION WAS
MODIFIED. NO NEW CORPUS WAS CREATED OR RUN. NOTHING WAS MERGED OR DEPLOYED.

# Final Pre-Freeze Architecture Verdict — Candidate 3

Methodology: four independent, parallel, read-only adversarial code-tracing passes were
run against current HEAD, plus direct personal verification of the two highest-stakes
claims (`POLICY_ENFORCEMENT_MODE` default/gating, and the `VERIFICATION_ERROR` gap in
`fact_admission.first_unresolved_dependency_note`) via live `python3` reproduction. All
claims below are anchored to file:line citations and, where practical, live code
execution — not to prior mission reports, comments, or docstrings, which were treated as
claims to verify rather than facts to trust. See the four supporting trees
(`FINAL_EXECUTABLE_ARCHITECTURE_TREE.md`, `AUTHORITY_FLOW_TREE.md`,
`FAILURE_FLOW_TREE.md`, `TWELVE_ADAPTER_TREE.md`) and three matrices
(`ADAPTER_ARCHITECTURE_MATRIX.md`, `FAILURE_SAFETY_MATRIX.md`,
`CONFIGURATION_ACTIVATION_MATRIX.md`) in this directory for full detail.

---

CANDIDATE BRANCH: `claude/final-trust-architecture-cutover`
CANDIDATE COMMIT: `7bf099fbda51592099ff627bbcccae3a1530dc18`
WORKING TREE CLEAN: YES (confirmed via `git status --porcelain`, empty output, at inspection start)

EXECUTABLE ARCHITECTURE TRACED: YES

REAL AI CONTEXTUAL DISCOVERY: **FAIL** — true for 11/12 adapters (env-gated,
`fact_admission`-backed, real `gpt-4o-mini` calls), but indemnification's *primary*
discovery channel (`HYBRID_DISCOVERY_ENABLED=True`, unconditional, no env override;
`SEMANTIC_PROVIDER="SIMULATED"`, hardcoded) is an ordinary regex proposer, not a language
model, in any deployment absent a source-code edit. `FACT_ADMISSION_MODE=enforced` has no
effect on this adapter's primary discovery path.

AI AUTHORITY BOUNDARY: **FAIL** — the core admission gate (`fact_admission.evaluate_admission`)
is structurally sound and verified intact: no path lets raw AI output directly create
ACCEPT or NOT_APPLICABLE, and no candidate reaches authority without verbatim,
independently-grounded evidence. However, several confirmed leaks exist ONE LAYER
DOWNSTREAM of the admission gate, at the adapter-composition layer, where a safety
*signal* (not a fact) can be silently discarded before it reaches a decision — see
KNOWN SILENT-CONTEXT-LOSS PATHS below. The boundary between "AI proposes, code decides"
holds; the boundary between "uncertainty is preserved end-to-end" does not, in the
specific cases documented.

CANONICAL FACT ADMISSION: PASS — `evaluate_admission`'s all-gates-must-pass rule is
correct and verified by direct reading and live reproduction. Separately noted (non-
blocking, documentation/schema-hygiene issue, not a live safety hole): `CandidateMaterialFact`
declares ten fields (`candidate_value`, `obligated_party`, `beneficiary_party`, `scope`,
`trigger`, `proviso`, `exclusion`, `limitation`, `schedule_dependency`,
`competing_interpretation`) that are never populated or read anywhere in the repository —
party/role/directionality attribution is in fact handled entirely by separate, adapter-
local deterministic code with no interface to this schema at all. This is schema/
implementation drift that could mislead a future reviewer relying on the dataclass
definition alone, but does not itself create an unsafe decision path.

DETERMINISTIC GROUNDING: PASS — exact-substring evidence/qualifier grounding, deterministic
regex-only definition/cross-reference resolution, and independent per-reading grounding
for competing readings were all verified correct by direct code reading.

PRIMARY FACT CONSUMPTION: 4/12 (confirmed end-to-end with executable proof: liability,
insurance, payment_terms, indemnification-safe-by-construction-for-a-different-scenario)
— the forbidden outcome (an ADMITTED fact silently collapsing to NOT_APPLICABLE/ACCEPT
merely because deterministic regex missed it) was **not found** in any of the 12 adapters
checked, but 8/12 (confidentiality, ip_ownership, data_security, governing_law,
termination, warranties, sla, assignment) were only verified structurally consistent
with the safe pattern, not traced to every evaluate-function branch — reported as UNKNOWN
rather than assumed safe, per this audit's standing instruction.

CONDITION SAFETY: 11/12 (indemnification's reconciliation-channel gate is narrower than
liability's, PARTIAL)
EXCEPTION SAFETY: 11/12 (same caveat)
DEFINITION SAFETY: 11/12 (same caveat)
CROSS-REFERENCE SAFETY: 10/12 (liability's own deterministic cross-reference path UNKNOWN;
indemnification PARTIAL)
COMPETING-READING SAFETY: 12/12 (the shared `evaluate_admission` ≥2-grounded-readings gate
is structurally intact everywhere it is used, including indemnification's reconciliation
channel)
OPERATIVE-CONTEXT SAFETY: 0/12 confirmed — the SHARED primitive (`policy_engine_core.
is_operative_context`/`classify_operative_context`) was live-tested against the mission's
own 10 example sentences and confirmed to classify 4 of them (future/hypothetical framing,
an unquoted illustrative example, a historical-agreement reference, and an explicit
"illustrative only" label) as `OPERATIVE_CONFIRMED` with no hedge whatsoever. Whether any
given adapter's own anchor regex independently prevents each of these four shapes from
reaching a clean decision was not verified per-adapter in this pass, so no adapter is
credited with a confirmed PASS on this dimension — this is reported as a shared-primitive
gap with unknown adapter-level mitigation, not as 12 independent failures.
UNRESOLVED-DEPENDENCY PROPAGATION: 11/12 at the adapter-wiring level (indemnification's
reconciliation `else` branch has no "nothing else established" gate at all) — but ALL
12/12 additionally inherit a deeper, shared-primitive gap: `first_unresolved_dependency_
note`'s uncertain-verification catch-all excludes `VERIFICATION_ERROR` from the states it
checks (confirmed live: `'VERIFICATION_ERROR' in inspect.getsource(first_unresolved_
dependency_note)` → `False`), so a genuine per-candidate provider failure during
verification (not discovery) is invisible to this escalation mechanism for every adapter
that uses it.

PROVIDER FAILURE FAIL-CLOSED: **FAIL** — provider failure during *discovery* fails closed
correctly (RECOGNITION_UNCERTAIN → REQUIRES_REVIEW) for all 12 adapters. Provider failure
during the per-candidate *verify* call (`VERIFICATION_ERROR`) does **not** fail closed at
the adapter-decision layer: it is correctly excluded from `ADMITTED` status, but the
failure itself is not escalated by `first_unresolved_dependency_note`, and can collapse to
`NOT_APPLICABLE` when deterministic regex also finds nothing. This is the single most
severe confirmed finding in this audit — a genuine 🚨 FALSE-CONFIDENCE PATH.

PROVIDER VARIANCE CONTAINMENT: **FAIL** — proven at 0/51 unsafe transitions for the cases
actually covered by the repeatability corpus (`data_security-139`, `ip_ownership-080`,
`ip_ownership-086`, `limitation_of_liability-006`, all independently re-verified in this
audit as correctly closed by their respective fixes). However: (a) indemnification's
structurally analogous, unguarded reconciliation-channel gap was never included in that
corpus and remains open; (b) the "nothing else established" suppression gates (liability
and 6 other adapters) are proven correct only for the exact shape they were built to fix,
not for the broader class of "a genuinely separate, unrelated candidate's uncertainty
discarded because another fact in the same clause type happens to be established."
Containment is real and substantial, but not proven complete across all 12 adapters.

POLICY ADAPTERS EXECUTABLE: 12/12 (code paths exist and run correctly when invoked) — but
with a critical activation caveat: the default `POLICY_ENFORCEMENT_MODE` is `"shadow"`
(unset → `DEFAULT_MODE = "shadow"`, confirmed live), under which **only
`limitation_of_liability` ever executes**; the other 11 adapters and the Interaction
Engine require explicit `POLICY_ENFORCEMENT_MODE=cutover` plus, per clause type, an ACTIVE
`PolicyPosition` on the reviewed playbook.

INTERACTION ENGINE: PASS (mechanism) — the gating logic (`_UNSAFE_PARTICIPANT_STATES`)
structurally cannot produce a clean interaction verdict from an unsafe participant, verified
by direct code reading; genuinely wired into the production route handlers, confirmed at
`main.py:1516-1518` and `main.py:1659`. Coverage caveat (non-blocking, residual risk): only
6/12 adapters (`limitation_of_liability`, `indemnification`, `insurance`, `termination`,
`payment_terms`, `sla`) participate in any launch-catalog rule today; it only runs at all
in cutover mode.

UNIFIED DOCUMENT STATE: PASS (aggregation logic) — `document_aggregation.
aggregate_document_state` is a pure, precedence-ordered function verified incapable of
reporting CLEAN while any REQUIRES_REVIEW/EVALUATION_ERROR/INSUFFICIENT_FACTS/PROHIBITED/
MUST_REDLINE/ESCALATE/NEGOTIATE state exists in its own inputs. The historical bug class
(`overall_risk` computed before policy enforcement) still exists in the underlying data
model (confirmed: `main.py:317-319` computes it before `main.py:1516`'s policy call), but
is mitigated, not eliminated, by this separate, additive aggregation layer — `overall_risk`
itself is never corrected.

UI AUTHORITY CONSISTENCY: **FAIL — 🚨 UI AUTHORITY BLOCKER, confirmed.** The dashboard,
history list, and in-progress single-contract review screen correctly read
`document_aggregation`'s state. The **Full Report & Audit Trail page** (`results.html`,
linked directly off the review screen's own button), its **PDF export**, the
**negotiation package export**, and the **external shared-report link** were all confirmed,
by direct inspection of the exact template-context dictionaries built in `main.py`
(lines 1855-1893, 2128-2137, 2624-2658, 2760-2773 respectively), to pass only the legacy,
pre-policy `overall_risk` value — none of them read `document_state`,
`policy_decisions_json`, or `interaction_decisions_json` at all. A contract can show
`overall_risk == "low"` with no attention badge on the full report, its PDF, its
negotiation package, or a shared link, while the same contract's policy/interaction state
requires review or contains a prohibited clause.

HISTORICAL REPRODUCIBILITY: PARTIAL, non-blocking — AI provider, model, temperature,
prompt/schema version, and the structured canonical-candidate object (evidence quotes,
qualifiers, definition/cross-reference resolutions, competing readings, admission status)
are not persisted; only prose summaries and the final decision state survive per
historical decision. Policy revision (`policy_position_id`, `config_hash`) and interaction
rule version ARE persisted. This degrades future auditability after a model/prompt/policy
change but does not corrupt any decision made under the current, frozen configuration —
correctly classified as non-blocking per the mission's own standard.

BURNED CORPUS EVIDENCE APPLICABLE TO CURRENT SHA: **YES** — independently confirmed via
`git log` on the 8 files the recent remediation touched (`fact_admission.py`,
`liability_policy_engine.py`, `data_security_policy_engine.py`,
`insurance_policy_engine.py`, `sla_policy_engine.py`, `warranties_policy_engine.py`,
`ip_ownership_policy_engine.py`, `payment_terms_policy_engine.py`): none were modified
after the evidence-generating commit (`520fbd0`), and HEAD (`7bf099f`) changed only a
markdown report, no code.

REPEATABILITY EVIDENCE APPLICABLE TO CURRENT SHA: **YES** — same basis; the repeatability
results (`2e0f1be`) predate no relevant code change.

FULL REGRESSION EVIDENCE APPLICABLE TO CURRENT SHA: **YES** — the claimed baseline (1480
passed / 10 failed / 1 skipped / 46 errors) was re-run live during this audit against
current HEAD and reproduced EXACTLY, with the same named failing tests (`test_override_
learning.py`, 9 tests in `test_production_secrets.py` — confirmed environment/dependency-
related, e.g. `ModuleNotFoundError: No module named 'dotenv'`), confirming this evidence is
current, not stale.

---

## KNOWN FALSE-SAFE PATHS
None found. No path was identified where the system reports an actionable/negative
finding it should not, or manufactures a false PROHIBITED/MUST_REDLINE from thin air.

## KNOWN UNVERIFIED→CLEAN PATHS
1. 🚨 **`VERIFICATION_ERROR` invisible to `first_unresolved_dependency_note`** — a provider
   failure specifically on the per-candidate verify call (distinct from a discovery-call
   failure, which IS correctly handled) is not one of the states the escalation catch-all
   checks. If deterministic regex also finds nothing, the result is `NOT_APPLICABLE` — a
   clean "no clause" outcome — despite an unverified, provider-error-shaped candidate
   having existed. (fact_admission.py, confirmed live in this audit)
2. Indemnification's default AI discovery channel produces no genuine model uncertainty to
   propagate in the first place, since it is not a model — this masks rather than resolves
   the "unverified→clean" question for that adapter's primary discovery path.

## KNOWN FALSE-ABSENCE PATHS
None found with confirmed proof. `is_operative_context`'s gaps (future/hypothetical,
unquoted illustrative example, historical reference, "illustrative only" label — all
classified `OPERATIVE_CONFIRMED`) are a **potential** false-presence (not false-absence)
risk whose actual exposure depends on each adapter's own anchor regex, not independently
confirmed per-adapter in this pass.

## KNOWN SILENT-CONTEXT-LOSS PATHS
1. 🚨 The "nothing else established" suppression gates (`liability_policy_engine.py:
   1853-1859` and the structurally identical `_any_established`/`found_anything` gates in
   data_security, insurance, sla, warranties, ip_ownership, payment_terms) discard a
   genuinely uncertain AI candidate's escalation note whenever ANY deterministic fact for
   that clause type is already established — proven correct for the exact redundant-signal
   shape they were built to fix (`limitation_of_liability-006`), but not scoped narrowly
   enough to guarantee a *separate, unrelated* candidate's uncertainty is never discarded
   the same way.
2. 🚨 Indemnification's reconciliation `else` branch (`indemnification_policy_engine.py:
   167-170`) has no equivalent gate at all — fully unguarded silent-context-loss exposure,
   uncaught by the repeatability corpus.
3. Liability's non-anchor-matching admitted candidate drop (`liability_policy_engine.py:
   1798-1806`) — an independently-admitted second condition/exception on a different
   sentence, when a deterministic anchor already exists elsewhere, is silently dropped.
   Documented in-code as a known residual risk, narrower than the other 11 adapters' scope.
4. 🚨 The Full Report/PDF/negotiation-package/shared-link UI surfaces silently lose the
   policy/interaction authoritative state (see UI AUTHORITY CONSISTENCY above) — this is
   context loss at the presentation layer, not the fact/decision layer, but it is a
   customer-facing instance of the same underlying failure mode: material context computed
   correctly, then silently absent where a human reads the outcome.

## KNOWN PROVIDER-VARIANCE→UNSAFE-CLEAN PATHS
1. 🚨 Indemnification's reconciliation channel (structurally identical exposure to the
   fixed and closed `limitation_of_liability-006`, but never itself fixed or tested).
2. The residual, narrower scope of the "nothing else established" gates (item 1 above,
   KNOWN SILENT-CONTEXT-LOSS PATHS) is also, by construction, a provider-variance path:
   if the uncertain candidate's own verification result varies run-to-run, whether it gets
   suppressed depends on whether some OTHER, unrelated fact happened to already be
   established — this is not itself proven to vary in practice for any known case, but the
   mechanism does not structurally prevent it.

## FACT_ADMISSION_MODE CURRENT DEFAULT:
Unset / disabled (empty string, does not equal `"enforced"`)

## FACT_ADMISSION_MODE REQUIRED FOR CUTOVER:
`enforced`

## POLICY_ENFORCEMENT_MODE CURRENT DEFAULT:
`shadow` (`DEFAULT_MODE`, policy_enforcement.py:52) — only `limitation_of_liability` runs;
Interaction Engine never runs

## POLICY_ENFORCEMENT_MODE REQUIRED FOR CUTOVER:
`cutover`

## OTHER REQUIRED PRODUCTION CONFIG:
- Every adapter-specific `<ADAPTER>_SEMANTIC_DISCOVERY_ENABLED` env var set (or rely on
  the `FACT_ADMISSION_MODE=enforced` global fallback) for all 11 mirror adapters.
- `indemnification_policy_engine.SEMANTIC_PROVIDER` requires a **source-code change** to
  `"REAL"` — no environment variable can activate its real-AI discovery path (its
  reconciliation channel is separately, correctly env-gated via
  `INDEMNIFICATION_RECONCILIATION_ENABLED`).
- Every clause type needs an ACTIVE `PolicyPosition` on the playbook under review, for
  full 12-adapter coverage in cutover mode.
- `OPENAI_API_KEY` must be set (no startup-time check enforces this; its absence silently
  degrades every review to maximal manual-review load rather than failing to start).

## ARCHITECTURAL FREEZE BLOCKERS:
1. **`VERIFICATION_ERROR` is invisible to `fact_admission.first_unresolved_dependency_note`**,
   allowing a genuine per-candidate provider failure (not a discovery failure, which IS
   handled) to collapse to a clean `NOT_APPLICABLE` when deterministic regex also misses.
   Confirmed live, applies to all 12 adapters that use this shared function. This is the
   single confirmed 🚨 FALSE-CONFIDENCE PATH in the entire architecture.
2. **The "nothing else established" note-suppression gates** (liability + 6 mirror
   adapters) are broader than the specific flapping case they were built to fix, and can
   in principle discard a genuinely separate, unrelated candidate's uncertainty note.
   Proven correct for the one case tested; not proven safe in general.
3. **Indemnification's reconciliation-channel `else` branch has no equivalent gate at all**,
   exposing it to the exact `limitation_of_liability-006` failure shape. This was never
   closed and never included in the repeatability corpus that measured "0/51."
4. **Indemnification's default/primary AI discovery is not AI** — a hardcoded, non-env-
   configurable simulator. This means the "all 12 adapters use real AI contextual
   discovery" premise this entire remediation program was built on is false for 1 of 12
   adapters, with no configuration-only remedy.
5. **🚨 UI AUTHORITY BLOCKER**: the Full Report/Audit Trail page, its PDF export, the
   negotiation package export, and the external shared-report link can all present a
   clean/low-risk view while the authoritative policy/interaction state requires review or
   is prohibited — confirmed by direct inspection of the exact template-context data built
   for each of these four surfaces.
6. **Default production posture (`POLICY_ENFORCEMENT_MODE` unset → `shadow`) runs only
   1 of 12 adapters and never runs the Interaction Engine.** Not itself a code defect (it
   is an explicit, documented rollback switch), but it means "Candidate 3, frozen" must be
   understood as "Candidate 3 IF AND ONLY IF cutover mode and every semantic-discovery flag
   are explicitly turned on" — the architecture that was audited is not the architecture
   that runs by default today.

## NON-BLOCKING RESIDUAL RISKS:
1. `is_operative_context`'s confirmed gaps for future/hypothetical framing, unquoted
   illustrative examples, historical-agreement references, and explicit "illustrative
   only" labels — real, live-tested, but actual per-adapter exposure not independently
   confirmed (bounded by each adapter's own anchor regex, not verified individually).
2. Cross-reference detection blind spot for the "Section N shall govern..." heading-lead
   pattern (`CROSS_REFERENCE_RE`/`find_delegating_cross_reference` both miss it, live-
   tested) — likely bounded in practice by the same adapter-anchor-regex dependency as #1.
3. `CandidateMaterialFact` schema/implementation drift — ten declared-but-never-used
   fields could mislead a future reviewer, though no live safety hole results since
   party/role/directionality are genuinely handled elsewhere.
4. Liability's documented, narrower "non-anchor-matching admitted candidate dropped"
   residual scope (acknowledged in the adapter's own code comments).
5. Startup fail-closed migration-coverage check only validates `limitation_of_liability`,
   not the other 11 clause types, despite `policy_enforcement.py`'s own (stale) docstring
   claiming six-clause-type coverage.
6. No startup-time `OPENAI_API_KEY` presence check for `FACT_ADMISSION_MODE=enforced`
   deployments.
7. Historical reproducibility gaps (model/prompt/schema version, structured evidence not
   persisted) — degrades future audit capability, does not corrupt current decisions.
8. Interaction Engine coverage is only 6/12 adapters today — not a safety defect (absence
   fails closed to no-interaction-check, never to a false clean interaction), but a real
   functional coverage gap worth closing before broad reliance on cross-policy findings.
9. Zero-retry provider timeout policy (30s, single attempt) — safe (fails closed) but has
   no resilience against a single transient network blip; every such blip forces manual
   review rather than a bounded retry.

## FINAL VERDICT:

**NOT READY TO FREEZE CANDIDATE 3**

Per the mission's own decision rule, freezing requires all eight conditions to hold. Two
are confirmed violated with direct code proof: condition 2 ("no known material path exists:
unverified fact → clean" — violated by the `VERIFICATION_ERROR` gap) and condition 8
("customer-facing authoritative state cannot misleadingly contradict policy/interaction
state" — violated by the four UI surfaces that never read the aggregated state). Condition
5 ("no known material context can silently disappear before authoritative evaluation") is
also violated in the narrower but real senses documented under KNOWN SILENT-CONTEXT-LOSS
PATHS. Condition 6 ("provider uncertainty cannot create unsafe clean-state variance") is
not proven for all 12 adapters — indemnification's reconciliation channel carries the same
structural exposure the repeatability corpus closed for liability, but was never itself
tested or fixed.

The engineering in this candidate is substantial and much of it is genuinely sound: the
core `evaluate_admission` authority boundary is intact and well-defended; deterministic
grounding is rigorous; 11 of 12 adapters' AI-discovery gating and unresolved-dependency
wiring is correct and, for the specific historical regression cases
(`data_security-139`, `ip_ownership-080`, `ip_ownership-086`, `limitation_of_liability-006`),
independently re-verified as fixed in this audit. But "ready to freeze for an independent,
previously-unseen corpus" requires the architecture itself to be free of KNOWN material
gaps first — a corpus cannot discover a defect this audit has already found by reading the
code. The six numbered ARCHITECTURAL FREEZE BLOCKERS above should be closed (or explicitly,
consciously accepted with a documented rationale) before that corpus is built and run.
