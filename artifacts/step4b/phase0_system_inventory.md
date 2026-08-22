# Step 4B Phase 0 — Read-Only System Inventory

Traced from actual production code (main.py, policy_enforcement.py,
interaction_engine_core.py, interaction_rules.py, interaction_enforcement.py,
review_queue.py, playbook_authoring.py, models.py), not inferred from
filenames. Where a pre-existing architecture design document already covers
a stage in detail and matches the traced code, it is cited rather than
re-derived from scratch: `docs/architecture/interaction_engine_v1_design.md`
(the Interaction Engine's own design pass, S1–S12) and
`docs/architecture/phase4_cutover.md` (the policy-enforcement mode system).
No production code was modified to produce this document.

## Headline finding before the stage-by-stage detail

**The system already implements a materially large fraction of what Step
4B asks Phase 0–3 to discover from scratch.** A 12-adapter policy
enforcement layer (`policy_enforcement.py`), a 7-rule cross-policy
Interaction Engine V1 with its own pure-function evaluator, gating,
determinism check, and Verify-replay mechanism (`interaction_engine_core.py`,
`interaction_rules.py`, `interaction_enforcement.py`), a review-queue
aggregator that already refuses to conflate PASSED/NOT_APPLICABLE/
EVALUATION_ERROR/exception states (`review_queue.py`), a playbook lifecycle
with revision-pinning and Verify replay (`playbook_authoring.py`, `models.py`),
and segment resolution with a fail-closed "no match = skip, never guess"
rule (`policy_enforcement.resolve_segment_position`) are all live code,
not proposals. A 54-case interaction benchmark (`benchmarks/interaction_corpus.py`,
`benchmarks/run_interaction_benchmark.py`) already passes 100% on its own
scope with all release gates green. This materially changes Step 4B's
starting point: much of Phase 0–5's "map the pipeline, define result
semantics, inventory interactions, build truth tables" work is
already-existing, already-tested code to VERIFY AND EXTEND, not to invent.

Equally important — **the rich 12-adapter/interaction-engine path is NOT
the default production behavior today.** `policy_enforcement.DEFAULT_MODE
= "shadow"`. In shadow mode (the default when `POLICY_ENFORCEMENT_MODE` is
unset), the user-visible result comes from the legacy, liability-only
`apply_liability_policy` path; the 12-adapter/interaction-engine path only
governs the user-visible result in `cutover` mode. Step 4B's system-level
validation must be explicit about which mode it is validating, and the
false-clean/false-escalation gates in Phase 12–13 must state which mode's
behavior they measure — testing "the system" without naming the mode is
ambiguous, since shadow and cutover modes produce materially different
review pipelines from the same contract text.

---

## The 14 pipeline stages

### 1. Document ingestion

- **Entry point**: `main.py`'s upload handler (contract text arrives as
  already-extracted plain text by this point; text-extraction-from-file is
  upstream of the scope traced here).
- **Input**: raw contract text (`str`), optional `playbook_id`, optional
  segment context (`business_unit`, `customer_type`, `deal_value`).
- **Output**: `contract_text` passed to `run_analysis()` and
  `policy_enforcement.apply_policies_for_review()`.
- **Authority level**: non-authoritative (no policy decision made here).
- **Failure mode**: malformed/empty text — not traced in this pass (out of
  Phase 0's scope; flagged for Phase 20 failure-mode testing).
- **Fail-closed behavior**: not yet verified — Phase 20 target.

### 2. Clause/provision segmentation

- There is no single "segmentation" stage shared by both pipelines. The
  **rule engine** (`rules_engine.py`, 5071 lines, legacy pattern-match
  findings) and each of the **12 deterministic adapters**
  (`extract_*_facts(text)`) independently scan the SAME full `contract_text`
  for their own anchors/windows — there is no shared, upstream "split the
  document into provisions" step feeding both. Each adapter owns its own
  provision discovery (e.g. `liability_policy_engine._discover_anchors`,
  `indemnification_policy_engine._OBLIGATION_RE.finditer`).
- **Authority level**: non-authoritative (candidate span discovery only).
- **Fail-closed behavior**: each adapter's own `clause_found: bool` on its
  `*Facts` dataclass is the only "did I find this clause at all" signal;
  absence of a clause is `NOT_APPLICABLE` at the decision layer, never
  inferred as ACCEPT.

### 3. Candidate discovery

- Per-adapter: 11 of the 12 adapters are pure-regex/structural (Step
  4A/4A.11's work this session covered 3 of these in depth). Indemnification
  alone integrates the SIMULATED semantic-discovery layer
  (`semantic_discovery.py`), gated by `HYBRID_DISCOVERY_ENABLED`.
- **Authority level**: semantic layer is explicitly NON-authoritative —
  `_verify_semantic_candidate` (indemnification_policy_engine.py) re-runs
  every semantic candidate through the SAME deterministic structuring
  regexes before it can become an obligation. Confirmed empirically this
  session (semantic→authority=0 across every corpus executed).
- **Fail-closed behavior**: a semantic candidate that fails deterministic
  re-verification is REJECTED, never partially trusted.

### 4. Deterministic verification

- `is_operative_context` (`policy_engine_core.py`) — the shared
  quoted/negated/meta-instructional/descriptive/recital non-operative-text
  filter, used by most adapters (this session's Step 4A.11 work touched
  this extensively).
- `ConditionEvidence` (`policy_engine_core.py`) — shared
  UNCONDITIONAL/ESTABLISHED/NOT_ESTABLISHED/CONFLICTING conditional-
  applicability model, used across indemnification/liability/payment_terms
  (Step 4A.11 Phase 2 built this).
- **Authority level**: authoritative — this IS the boundary between
  "candidate text" and "material fact."
- **Fail-closed behavior**: an unresolved condition or non-operative
  context match causes the calling adapter to skip/decline the candidate,
  never guess.

### 5. Adapter execution (`extract_*_facts` / `evaluate_*_policy`)

- 12 adapters, one shared function-pair contract each, enumerated in
  `docs/architecture/interaction_engine_v1_design.md` §1.5: Liability,
  Indemnification, Termination, Confidentiality, Assignment, Governing Law,
  Data Security, IP Ownership, Insurance, Payment Terms, Warranties, SLA.
  `playbook_authoring._ENGINE_FUNCS` / `_ENGINE_PROTOCOLS` is the actual
  registry (`playbook_authoring.CLAUSE_TYPES = tuple(_ENGINE_PROTOCOLS)`).
- **Input**: `contract_text: str`, a `PolicyRuleLike` object built from an
  ACTIVE `PolicyPosition` (`pa.build_policy_rule_for_enforcement`).
- **Output**: `PolicyDecision` — one shared dataclass shape across all 12
  adapters (`policy_engine_core.py:363`; fields enumerated in the design
  doc §1.1: `state`, `contract_language`, `controlling_provision`,
  `category_treatments`, `escalate_to`, etc.).
- **Authority level**: authoritative — this is THE policy decision layer.
- **Failure mode**: one adapter's extractor/evaluator raising an exception.
- **Fail-closed behavior**: isolated per clause type by
  `policy_enforcement.evaluate_active_policies` — every other adapter's
  evaluation proceeds; the broken one becomes an `EVALUATION_ERROR`
  finding (`_error_finding`), never a fabricated decision, never silently
  dropped from the review.

### 6. Policy result representation

- `PolicyDecision.as_dict()` — one canonical, uniform shape, persisted
  verbatim into `Contract.policy_decisions_json` (`{clause_type:
  decision_dict}`), keyed in `pa.CLAUSE_TYPES`'s fixed order for
  deterministic serialization.
- `Contract.policy_revision_metadata_json` — parallel column pinning
  `{policy_position_id, config_hash, activated_at}` per clause type, the
  substrate for `verify_policy_finding`'s replay mechanism (§17 below).
- **Authority level**: authoritative, persisted.

### 7. Interaction engine

- `interaction_engine_core.evaluate(decisions: Dict[str, PolicyDecision],
  rules: List[InteractionRule]) -> List[InteractionDecision]` — pure
  function, no I/O, no LLM (confirmed by reading the module — imports are
  `hashlib`, `json`, `dataclasses`, `typing`, `policy_engine_core` only).
- `interaction_rules.LAUNCH_CATALOG` — 7 rules, all classified
  `READY_FROM_STRUCTURED_FACTS` per the design doc's own inventory (§3.10),
  spanning Liability×Indemnification (4 rules), Liability×Insurance (1),
  Termination×Payment Terms (1), SLA×Payment Terms (1). See Phase 2 below
  for the full registry extraction.
- **Gating** (`_gate_participants`): a rule's predicate is NEVER called
  unless every one of its `participating_clause_types` has a
  `PolicyDecision` present AND that decision's state is outside
  `{NOT_APPLICABLE, REQUIRES_REVIEW, EVALUATION_ERROR}` — otherwise the
  rule short-circuits to `INSUFFICIENT_FACTS`, matching Step 4B's own
  Phase 3 "Interaction Authority Invariant" verbatim (confirmed already
  implemented, not merely designed).
- **Ceiling enforcement**: a predicate's returned `state` is checked
  against the rule's declared `ceiling_state`; exceeding it raises
  (`ValueError`), a hard code-level guarantee a rule can never escalate
  past what it was registered to produce.
- **Failure mode**: one rule's predicate raising — isolated exactly like
  adapter-level isolation (§5), becomes `EVALUATION_ERROR` for that one
  interaction only, every other rule proceeds.
- **Authority level**: authoritative — but derived ONLY from already-
  authoritative `PolicyDecision`s; never re-reads contract text, never
  calls an extractor a second time (confirmed: `interaction_engine_core.py`
  and `interaction_rules.py` both import nothing from any `*_policy_engine`
  module and take no `contract_text` parameter anywhere in their call
  graphs).
- **Wiring**: `interaction_enforcement.apply_interaction_rules(outcomes,
  findings_dict)`, called from `policy_enforcement.apply_policies_for_review`
  immediately after `apply_active_policies`, **in `cutover` mode only**.

### 8. Severity/prioritization

- `review_queue.TIER_RANK` — an explicit, static table
  (`PROHIBITED/MUST_REDLINE/ESCALATE` → 0, `NEGOTIATE` → 1,
  `REQUIRES_REVIEW/EVALUATION_ERROR` → 2), reused verbatim by interaction
  findings (`interaction_engine_core`'s state vocabulary deliberately
  reuses the same strings — confirmed in that module's own docstring, §35
  above).
- **Authority level**: presentation/ordering only — confirmed by reading
  `build_review_queue`: severity/tier never changes `policy_state` itself,
  never removes a finding, only affects sort order and which of 4 summary
  buckets a count lands in.

### 9. Deduplication

- No explicit, general-purpose deduplication stage was found across
  findings in this pass — `build_review_queue` partitions by
  `finding_type` and `policy_state` but does not merge/drop findings that
  look similar. This is a genuine gap relative to Step 4B's Phase 9
  requirement ("audit all deduplication logic") — **there may be nothing
  to audit yet**, which itself needs to be confirmed against `main.py`'s
  and `rules_engine.py`'s own finding-construction code before Phase 9 can
  proceed (flagged as a continuation-point item, not resolved here).

### 10. Final finding aggregation

- `review_queue.build_review_queue(findings, policy_decisions) ->
  ReviewQueue` — pure function (no DB, no HTTP), unit-tested directly
  (`tests/test_review_queue.py`, confirmed present). Produces
  `policy_exception_indices`, `interaction_exception_indices`,
  `other_finding_indices` (rule-engine findings, order preserved),
  `passed_checks`, `not_applicable_checks`, and a `ReviewQueueSummary`
  with 8 explicit counters — never a single collapsed "clean/not clean"
  boolean at this layer (see Phase 1 below for where document-level status
  is actually decided, if it is).
- **Confirmed non-conflation** (read directly from the module docstring
  and code, not assumed): PASSED_STATES = `(ACCEPT, ACCEPT_WITH_NOTE)` is
  the sole definition of "passed"; a clause type absent from
  `policy_decisions` entirely (never evaluated) produces neither a passed
  row nor a not-applicable row — it is simply invisible to this function,
  which is itself worth flagging (Phase 1: is "never evaluated" visible
  ANYWHERE to the reviewer, or only reconstructable by diffing against
  `pa.CLAUSE_TYPES`? — continuation-point item).

### 11. Explanation generation

- `evaluator.py`'s `LLMEvaluator` — operates ONLY on the legacy
  `rules_engine.py` finding shape (`rule_id`, `rule_name`, `matched_excerpt`,
  `severity`, `rationale`), explicitly hard-gated against ever receiving
  `contract_text` (`evaluate()` raises `ValueError` if a caller passes
  `contract_text` at all). Verified output-maps-to-input-findings check
  (`_verify_output_maps_to_findings`) already exists, logging (not
  blocking) a mismatch.
- **Not yet confirmed**: whether/how this LLM layer's summary interacts
  with `policy_decision`/`interaction_decision` findings (the newer,
  12-adapter/interaction-engine findings) — `_build_prompt` groups by
  `rule_name`, which policy/interaction findings also populate
  (`_finding_from_decision`, `_finding_from_interaction_decision`), so
  they likely DO flow into the same LLM summary today, but this needs
  direct confirmation before Phase 18 (Explanation Fidelity) can be
  scoped — continuation-point item.

### 12. Evidence display

- `PolicyDecision.controlling_provision` / `InteractionDecision.
  participating_provisions` — `{label, excerpt, start_index, end_index}`
  dicts, reused verbatim by `render_evidence_report()` for interactions
  (confirmed: no new evidence storage format, matches design doc §6
  exactly).

### 13. Final review status

- **No single document-level "PASS/FAIL/REVIEW" status field was found**
  in this pass — `Contract` carries `overall_risk` (rule-engine-derived:
  low/medium/high) and the `ReviewQueueSummary` counters, but nothing
  traced so far computes a single authoritative document-level verdict
  combining policy decisions + interaction decisions + rule-engine
  findings into one status. This is the central open question for Step
  4B's Phase 1 (Result-State Model) and Phase 11 (Final Review
  Aggregation) — **flagged, not resolved, in this Phase 0 pass**.

### 14. Persistence/replay behavior

- `Contract.policy_decisions_json`, `.policy_revision_metadata_json`,
  `.interaction_decisions_json` — three parallel, independent JSON
  columns (confirmed: `interaction_decisions_json` is NOT nested inside
  `policy_decisions_json`, matching design doc §11's explicit
  requirement).
- `policy_enforcement.verify_policy_finding` — single-decision replay
  against the EXACT pinned revision (by `policy_position_id`, not "today's
  ACTIVE"), confirmed read directly from source.
- Interaction-level `verify_interaction_finding` — referenced in the
  design doc §7.2 as the natural one-layer-up extension of
  `verify_policy_finding`; **existence in current code not yet confirmed
  in this pass** (interaction_enforcement.py's first 80 lines were read;
  the rest was not) — continuation-point item for Phase 17.
- `PolicyPosition` revision-not-mutation invariant (`models.py`,
  `POLICY_POSITION_STATUSES = (DRAFT, NEEDS_REVIEW, APPROVED, ACTIVE,
  ARCHIVED)`) — editing an ACTIVE position creates a new DRAFT row rather
  than mutating the ACTIVE one in place (confirmed via `models.py`
  comment: "'edit an ACTIVE position' creates a second row (status=DRAFT...").

---

## Mode system (critical context for every subsequent Step 4B phase)

`policy_enforcement.get_enforcement_mode()` reads `POLICY_ENFORCEMENT_MODE`
fresh on every call (no caching), defaulting to `DEFAULT_MODE = "shadow"`.

| Mode | User-visible policy result | Interaction Engine active? | 12-adapter results visible? |
|---|---|---|---|
| `legacy` | Legacy liability-only `PolicyRule` path | No | No |
| `shadow` (**default**) | Same as legacy (12-adapter path runs silently for comparison, logged to `AuditLog`, never shown) | No | No |
| `cutover` | Full 12-adapter `PolicyPosition` path | **Yes** | Yes |

`verify_migration_coverage_or_fail_closed` must pass before cutover mode is
allowed to start (raises `MigrationCoverageError`, a fatal, non-swallowed
exception) — confirmed fail-closed by design.

**Step 4B scoping decision needed**: all Step 4B system-level testing
(Phases 8, 12, 13, 21, 27+) must explicitly state it validates `cutover`
mode — that is the only mode in which "multiple validated policy decisions
operate together," which is Step 4B's own stated purpose. This inventory
does not decide whether shadow-mode's user-visible (legacy-only) behavior
is also in Step 4B's scope; that is a Phase 1 scoping question, not a
Phase 0 one.

---

## Open items carried into Phase 1+ (not resolved in this read-only pass)

1. No single document-level final-status field found — central Phase 1
   question.
2. No general-purpose finding deduplication logic found yet — Phase 9
   needs to confirm whether one exists elsewhere (main.py/rules_engine.py)
   before it can be audited, or confirm there is genuinely none yet.
3. Explanation layer (`evaluator.py`)'s interaction with
   policy_decision/interaction_decision findings not yet directly traced
   end-to-end — Phase 18 prerequisite.
4. `verify_interaction_finding`'s existence/completeness not yet confirmed
   — Phase 17 prerequisite.
5. Whether "never evaluated" (a clause type with no ACTIVE policy at all)
   is visible anywhere to the reviewer, or only absence-by-omission —
   relevant to Step 4B's explicit "do not collapse NOT_APPLICABLE and
   COULD NOT ESTABLISH APPLICABILITY" requirement.
6. Playbook segment testing (Phase 16) has real code to test against
   (`resolve_segment_position`, confirmed fail-closed on no-match) but no
   dedicated adversarial benchmark was found in this pass — needs a
   targeted search before Phase 16 can proceed.
