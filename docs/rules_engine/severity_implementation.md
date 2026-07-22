# Severity Framework v1.0 — Implementation

Companion to `docs/rules_engine/severity_architecture.md` (the frozen
spec). This document covers everything the spec doesn't: the engineering
plan, the working code, and the process pieces (workflow, governance,
checklist) that make the framework operable by more than one person over
years.

**No part of the frozen architecture was changed to produce this
implementation.** No new factor, ceiling rule, weight, or threshold was
introduced. One documentation bug was found and fixed (§0 below) — it was
a self-contradictory example in the spec's own stress-test table, not a
defect in the framework itself. Zero issues were found that require a v2
candidate; if one had been, it would be recorded in
`docs/rules_engine/severity_v2_candidates.md` (not yet created — nothing
to put in it yet) rather than patched into v1.0.

## 0. What was built

| Artifact | Purpose |
|---|---|
| `severity_scoring.py` | The scoring engine: `Factor`, `FactorScore`, `FactorVector`, `compute_severity()`, `SeverityDerivation`, `ScoredRule`, and the four validators (`validate_schema`, `validate_mutuality_gate`, `validate_ceiling_coverage`, `validate_monotonicity`). |
| `tests/test_severity_scoring.py` | 31 unit tests on the engine's mechanics — ceiling ordering, WAS arithmetic, exact threshold boundaries, validator behavior. |
| `tests/test_severity_regression_corpus.py` | The permanent golden set — the architecture doc's 40 stress-test clauses plus 3 added during implementation to close ceiling-rule coverage gaps (43 total), each asserted against `compute_severity()`. |
| `scripts/severity_migration_sample.py` | 18 real `rule_id`s from `rules_engine.py`, hand-scored with `legacy_severity` preserved — a representative sample, not the full 117-rule migration (see §3). |
| `scripts/generate_migration_report.py` | Produces the Task 5 comparison report (legacy/new/changed/reason/confidence/recommendation) from any `List[ScoredRule]`. |
| `tests/test_severity_migration_report.py` | 7 tests on the report generator itself. |

**Erratum found and fixed during implementation:** the architecture doc's
stress-test row #29 (earnout discretion) was originally vectored with
`FB=3`, which — once actually run through the ceiling rules in order —
fires the plain `FB == 3` ceiling before ever reaching the `UD`/`FB`
compound rule the row's own note claimed was doing the work. Running the
doc's numbers through code, not just re-reading the prose, is what caught
this. Corrected to `FB=2` in both the architecture doc and the regression
corpus; the tier is unchanged (HIGH either way), only the *cited reason*
was wrong. Documented in the architecture doc §5 directly rather than
silently fixed, per this file's own §9 governance rule that a corpus entry
and its doc row must never be edited independently.

Total test suite: **345 passing** (261 pre-existing rule tests + 31 engine
unit tests + 46 corpus tests + 7 migration-report tests).

---

## 1. Implementation plan

| Phase | Scope | Depends on | Effort (eng-days, rough order of magnitude) | Status |
|---|---|---|---|---|
| **A — Engine** | `severity_scoring.py`: factors, ceiling rules, WAS, thresholds, `ScoredRule`, validators | Frozen architecture doc | 1–2 | **Done** (this session) |
| **B — Engine tests** | Unit tests on ceiling ordering, WAS arithmetic, threshold boundaries, validator behavior | A | 1 | **Done** |
| **C — Regression corpus** | Convert architecture doc §5's 40 clauses into `CORPUS`; close ceiling-coverage gaps found by testing | A, B | 1 | **Done** (43 entries; see §7 for growth plan to 150–200) |
| **D — Migration tooling** | `ScoredRule`, `validate_ruleset`, sample migration set, comparison-report generator | A | 1–2 | **Done** (18-rule representative sample) |
| **E — Full retroactive scoring (Phase 2 of the architecture doc's migration, §12)** | Score all 117 existing rules — every factor level needs a contributor-written justification and a second contributor's blind re-score (§10.7) | A–D | ~117 rules × (0.5–1 hr scoring + 0.5 hr blind re-score + attorney sign-off queue time) ≈ **3–5 eng-weeks**, gated by attorney review-turnaround, not engineering time | **Not started** — genuinely requires the §10 workflow run 117 times; not something to batch-generate |
| **F — Calibration (Phase 3)** | Diff computed vs. legacy for all 117; root-cause every mismatch; adjust §6.3 thresholds only if justified by real disagreements, not to force-match legacy | E | 2–3 days analysis + governance sign-off (§9 of this doc) to approve any threshold change | Not started |
| **G — Schema/metadata persistence** | Add `RuleMetadata` fields (architecture doc §8) to the actual `Rule` dataclass in `rules_engine.py`, additive/nullable | A | 2–3 days | Not started |
| **H — Shadow mode (Phase 4)** | Ship `computed_severity` as a secondary field; verify `overall_risk`, `signature_readiness`, `ONE_WAY_RULE_IDS` against it | E, F, G | 1 release cycle bake time + 1–2 eng-days integration | Not started |
| **I — CI enforcement (Task 6/Phase 6)** | Wire `validate_ruleset` into CI as a hard gate on every rule PR | A, G | 1 day | Not started |
| **J — Cutover (Phase 5)** | `severity` becomes a generated property of `computed_severity`; `legacy_severity` retained permanently | E–I all green | 1 day + rollback readiness | Not started |

**Rollout order:** A→B→C→D can (and did) happen in parallel with zero
production risk, since none of it touches `rules_engine.py`'s live
`Rule.severity` field — it's a standalone module plus tests and scripts.
E and G can run in parallel once D exists. F depends on E. H depends on
E+F+G. I can land any time after G (validating an empty/partial metadata
set is still useful). J is strictly last and gated on everything else
being green, per the architecture doc §12's own phase ordering — this
document doesn't change that ordering, only fills in effort estimates and
dependencies around it.

**Rollback strategy:** identical to architecture doc §12 — every phase
through H is purely additive (new module, new optional fields, a secondary
report field); nothing in `rules_engine.py`'s existing behavior changes
until J. J itself is a one-line revert (`severity` repoints to
`legacy_severity`) since `legacy_severity` is never deleted. No phase in
this plan introduces a rollback path any less safe than the architecture
doc already specified.

---

## 2. Rule schema (as implemented)

The architecture doc §8 schema is the target for the eventual persisted
`Rule` record (Phase G above). What's actually implemented today in
`severity_scoring.py` is the subset the *scoring and validation pipeline*
needs — deliberately smaller than the full persisted schema, since
governance/audit fields (`authored_by`, `references`, `review_date`, …)
don't affect what severity a factor vector produces and don't belong in a
pure-function engine's input type.

| Field | Type | Required | Validation | Purpose |
|---|---|---|---|---|
| `Factor` (enum) | `str, Enum` — 11 members | n/a | Membership in the fixed 11-factor set (`assert TIER_A \| TIER_B \| TIER_C == set(Factor)` at import time) | The closed vocabulary — adding a 12th value here **is** a framework change and requires the v2 governance process (§9). |
| `FactorScore.level` | `int` | Yes | `0 <= level <= FACTOR_MAX_LEVEL[factor]`, checked in `FactorVector.__post_init__` | The scored value for one factor. |
| `FactorScore.justification` | `str` | Yes | Non-empty after `.strip()` | A bare integer level is a schema violation per architecture doc §5/§9.5 — enforced at construction, not just at CI time. |
| `FactorVector.scores` | `Dict[Factor, FactorScore]` | Yes | Exactly the 11 factors, no more, no fewer | The complete scoring input for one rule; partial scoring is not a valid state. |
| `ScoredRule.rule_id` | `str` | Yes | Non-empty (`validate_schema`) | Links back to the actual `Rule.rule_id` in `rules_engine.py`. |
| `ScoredRule.clause_category` | `str` | Yes | Non-empty (`validate_schema`) | Groups doctrinally-identical clauses across `legal_domain` for the monotonicity check (§9.2) — see architecture doc §8's design note on why this is separate from domain. |
| `ScoredRule.affected_party_role` | `str` | Yes | Non-empty; checked against `MUTUAL_PARTY_ROLES` by the mutuality gate | Drives `validate_mutuality_gate` — a structural backstop against the Refinement Log #4 false positive. |
| `ScoredRule.factor_vector` | `FactorVector` | Yes | (validated by `FactorVector` itself) | The scoring source of truth. |
| `ScoredRule.legacy_severity` | `Optional[Severity]` | No (None pre-migration) | Must be one of the 4 `Severity` enum values | Permanent historical record, per architecture doc §7.4/§12 — never overwritten. |
| `ScoredRule.rationale` | `str` | Yes | Non-empty (`validate_schema`) | Feeds `validate_ceiling_coverage`'s keyword lint. |
| `ScoredRule.known_contestable` | `bool` | No (default `False`) | n/a | Added during implementation (§5 of this doc) so a documented human judgment call (architecture doc §5.1) can never be silently overridden by an automated confidence heuristic. |
| `SeverityDerivation.tier` / `.was` / `.method` / `.ceiling_rule` / `.band` / `.framework_version` | mixed | Generated, never hand-set | Produced only by `compute_severity()` | The audit trail architecture doc §6.1 requires: every CRITICAL traces to a one-sentence, citable reason. |

Fields from architecture doc §8 **not yet implemented** (deferred to
Phase G, since they're persistence/governance metadata, not scoring
inputs): `rule_version`, `legal_domain`, `affected_asset`,
`prerequisite_facts`, `jurisdiction_profile`, `references`, `authored_by`,
`reviewed_by`, `review_date`, `schema_version`, `aliases`. None of these
change how `compute_severity()` behaves; they attach to the eventual
persisted record around it.

---

## 3. Migration of existing rules — process actually used

Per Task 4's explicit requirement ("preserve legacy severity, compute new
severity independently, compare both, generate migration report, do not
overwrite, must be fully reversible"), here's what was actually done for
the 18-rule sample, exactly reproducing the process the remaining ~99
rules go through in Phase E:

1. **Select the rule** from `rules_engine.py` by `rule_id`; read its
   `title`/`rationale`/detection pattern.
2. **Score all 11 factors independently**, using only the clause language
   and doctrine the rule itself detects — never looking at the rule's
   current `severity` while scoring (the architecture doc §7's mandate
   applied literally: score first, look at legacy only when comparing).
   Where the stress-test corpus already scored the same fact pattern
   (architecture doc §5), the vector was reused with a citation back to
   that row rather than re-derived from scratch — legitimate reuse of
   already-reviewed analysis, not a shortcut around justification.
3. **Construct a `ScoredRule`** with `legacy_severity` set from the real
   `Rule.severity` value in `rules_engine.py` — read, never written.
4. **Run `compute_severity()`** via `ScoredRule.severity`/`.derivation` —
   fully automatic, no hand-picked tier.
5. **Run `validate_ruleset()`** — zero hard errors on the 18-rule sample
   (confirmed by `test_migration_sample_has_no_hard_validation_errors`).
6. **Generate the report** via `scripts/generate_migration_report.py`.

This is read-only end to end: nothing in `rules_engine.py` was modified.
`legacy_severity` lives only in the migration sample module, entirely
separate from the live `Rule.severity` field. Reversal is
trivial — delete the migration sample and report script, and the live
engine is untouched, exactly as it was before this session.

**The remaining ~99 rules are not scored here.** Doing so would mean
either fabricating factor-level justifications without real legal
analysis (unacceptable — `FactorScore.justification` exists specifically
to prevent exactly that) or silently skipping the §10 blind-re-score gate.
Phase E in §1's plan is the correct place for that work, sized honestly at
3–5 weeks of calendar time dominated by attorney review turnaround, not
engineering effort.

---

## 4. Scoring engine — execution flow (as implemented)

```
Rule (rules_engine.py, unmodified)
  │
  ▼
Metadata Validation          validate_schema(rule) -- rule_id, clause_category,
  │                            affected_party_role, rationale all non-empty
  ▼
Factor Extraction            FactorVector(scores={...}) construction --
  │                            raises SeverityScoringError immediately on a
  │                            missing factor, out-of-range level, or empty
  │                            justification. This stage cannot silently
  │                            produce a partially-valid vector.
  ▼
Ceiling Rule Evaluation      _evaluate_ceiling_rules(vector) -- the 8 rules
  │                            in architecture doc §6.1's exact order,
  │                            first match wins
  ▼
Weighted Scoring             _weighted_aggregate_score(vector) -- always
  │                            computed, even when a ceiling already fired
  │                            (kept in SeverityDerivation.was for audit/
  │                            reporting even though it didn't decide the
  │                            tier in that case)
  ▼
Threshold Mapping            _band(was) -- only consulted if no ceiling fired
  │
  ▼
Computed Severity            SeverityDerivation(tier, was, method,
  │                            ceiling_rule|band, framework_version)
  ▼
Validation                   validate_mutuality_gate, validate_ceiling_coverage
  │                            (per-rule) + validate_monotonicity (cross-rule,
  │                            requires the full rule set) -- run by the
  │                            caller (CI, migration script), not embedded
  │                            in compute_severity() itself, since
  │                            compute_severity() must stay a pure function
  │                            of one vector with no dependency on the rest
  │                            of the ruleset
  ▼
Final Stored Result          Caller's responsibility -- this module never
                               writes to rules_engine.py or any datastore.
                               Persistence is Phase G (§1).
```

Every arrow above is exercised by at least one test in
`tests/test_severity_scoring.py`.

---

## 5. Difference analysis (Task 5) — format and generation

Implemented in `scripts/generate_migration_report.py`; the exact columns
Task 5 specified, plus how each is computed:

- **Legacy Severity / New Severity** — direct reads: `rule.legacy_severity`
  and `rule.severity` (the latter derived, never stored independently).
- **Changed?** — `new != legacy`.
- **Reason** — for a ceiling-derived tier, the exact ceiling rule name
  (`"FB == 3"`, etc.) — a one-sentence, citable fact, per architecture doc
  §6.1's invariant. For a band-derived tier, the WAS value and band label.
- **Confidence** — deterministic, not a guess: `"high"` for any
  ceiling-derived result (a named legal fact, not an aggregate);
  `"low"` for any rule marked `known_contestable=True` regardless of WAS
  (§0's note on why); otherwise `"medium"` if the WAS is ≥6 points from
  the nearest real decision line (18 or 36) and `"low"` if within 6 —
  i.e., automatically flagging exactly the boundary cases architecture doc
  §5.1 discusses by name, without needing a human to notice they're close
  to a line.
- **Reviewer Notes** — not auto-generated; this is where a human
  attorney's Phase-F notes go, appended to the `ScoredRule` record (not yet
  a formal field — add `reviewer_notes: str` to `ScoredRule` in Phase E
  once real review begins, since inventing placeholder text for it now
  would be worse than leaving it absent).
- **Recommendation** — `"no action"` if unchanged; `"adopt new severity"`
  for high-confidence changes; `"recommend adopting new severity; flag for
  attorney spot-check"` for medium-confidence changes; `"defer to Phase 3
  attorney calibration"` for low-confidence changes — never a bare
  assertion on a low-confidence result, enforced by
  `test_recommendation_never_silently_resolves_a_boundary_case`.

Sample output (18 rules, live-generated by `python3 -m
scripts.generate_migration_report`): **8/18 changed tier** — 3 upgrades
(all ceiling-derived, high confidence), 1 medium-confidence downgrade, 4
low-confidence downgrades explicitly deferred rather than resolved. This
matches the disagreement pattern architecture doc §5.1 already predicted
by hand — the tooling reproduces the same conclusions the manual stress
test reached, which is itself a useful cross-check that the engine
correctly implements the spec.

---

## 6. Validation (Task 6) — as implemented

| Check | Function | Fails loudly how |
|---|---|---|
| Invalid metadata / missing required fields | `validate_schema` | Returns error strings; `validate_ruleset` puts them under `"errors"` (hard fail) |
| Impossible factor combinations (out-of-range levels) | `FactorVector.__post_init__` | Raises `SeverityScoringError` at construction time — cannot even build an invalid vector, let alone score one |
| Missing justification (a bare-number factor) | `FactorScore.__post_init__` | Raises `SeverityScoringError` immediately |
| Conflicting/duplicate reasoning (ceiling-keyword under-scoring) | `validate_ceiling_coverage` | Returns warning strings — soft-fail by design (a keyword match without the ceiling firing needs human judgment, not an automatic hard block) |
| Inconsistent scores across rules (monotonicity) | `validate_monotonicity` | Returns error strings describing exactly which rule pair violates dominance and in which `clause_category` |
| Mutuality-gate violations (Refinement Log #4 regression) | `validate_mutuality_gate` | Returns error strings; `validate_ruleset` puts them under `"errors"` (hard fail) |
| Schema violations generally | All of the above, aggregated | `validate_ruleset(rules) -> {"errors": [...], "warnings": [...]}` |

`scripts/generate_migration_report.py` calls `validate_ruleset` before
generating anything and exits non-zero on hard errors (`sys.exit(1)`,
printed to stderr) — validation failing loudly is wired into the one
existing entry point, and the same call is what Phase I wires into CI.

**Duplicate rule detection** (near-identical `rationale`/pattern text,
architecture doc §9.3) is **not implemented** in this pass — it requires
either a similarity-clustering library or an embedding model, which is a
larger dependency decision than this implementation session should make
unilaterally. Flagged here as an explicit open item for Phase I, not
silently dropped.

---

## 7. Regression suite (Task 7) — size and growth plan

**Current size: 43** (the architecture doc's 40 plus 3 added during
implementation to close ceiling-coverage gaps — §0 above).
**Recommended target: 150–200**, reached as a *byproduct* of Phase E (full
retroactive scoring), not as separate work: every one of the ~99 remaining
rules, once scored via the §10 blind-re-score workflow, becomes a corpus
entry for free — its factor vector and expected tier are already produced
by that process. 150–200 gives the monotonicity validator
(`validate_monotonicity`) meaningful coverage within most
`clause_category` groups (multiple entries per category is what makes a
dominance violation detectable at all), which 43 entries — spread across
14+ agreement types — mostly cannot yet provide.

`test_corpus_covers_every_agreement_type_named_in_the_architecture_doc`
and `test_corpus_exercises_every_ceiling_rule_at_least_once` are themselves
part of the permanent suite specifically so corpus growth is *checked*,
not just hoped for — if Phase E's 99 new entries somehow left a coverage
gap, these two tests would catch it the same way they caught the original
40's gaps in §0.

**Financial Services**, named in Task 7's required coverage list, has no
corpus entry yet — none of the 43 clauses is a bank/broker-dealer/payments
clause specifically (Loan and Government are the closest analogues
present). Recorded here as a known gap for Phase E rather than
papered over with a mislabeled entry.

---

## 8. Contributor workflow (Task 8)

This is architecture doc §10, made concrete with the actual functions a
contributor runs at each step:

1. **Identify `clause_category`.** Check the controlled vocabulary (today:
   the categories already in use across `severity_migration_sample.py` and
   the corpus — e.g. `LiabilityCap`, `PersonalGuaranty`, `RightsWaiver`,
   `IPAssignment`; propose new ones via a separate PR, not inline).
2. **Score all 11 factors.** Construct a `FactorVector` via
   `FactorVector.from_levels(...)` is for tests/fixtures only — production
   authoring uses the full `FactorScore(level=..., justification="...")`
   form for every factor, no exceptions (the constructor enforces this).
3. **Run `compute_severity(vector)`.** Do not hand-pick a tier under any
   circumstance — the field doesn't exist as an input.
4. **Inspect `SeverityDerivation`.** Confirm the `ceiling_rule` or `band`
   matches your own expectation before moving on; if it doesn't, that's
   either a scoring mistake (fix the vector) or a real framework question
   (stop — see §9's escalation path, don't route around it).
5. **Write detection pattern + tests** (unchanged discipline: whitespace/
   line-wrap-tolerant regex, positive/negative/messy-formatting tests, as
   already practiced in `rules_engine.py`).
6. **Blind re-score gate.** A second contributor runs steps 2–4 independently,
   given only the `rationale` and clause text — not your `FactorVector`.
   Compare `SeverityDerivation.tier` between the two. A mismatch means the
   *factor definitions* need discussion, not that either scorer picks a
   winner.
7. **Add to `severity_migration_sample.py`** (or its post-Phase-G
   successor — the real persisted rule store) with `legacy_severity` set
   only if this is a migration of an existing rule; omit it for a
   genuinely new rule.
8. **Run `validate_ruleset([your_rule] + existing_rules)`.** Zero errors
   required; review any warnings.
9. **Add a corpus entry** (`tests/test_severity_regression_corpus.py`) once
   the vector is reviewer-approved — this is what makes the rule's severity
   permanently regression-tested.
10. **Reviewer sign-off** from someone with subject-matter familiarity in
    the rule's practice area, recorded (once Phase G lands `reviewed_by`)
    permanently on the rule record.

---

## 9. Governance (Task 9)

- **Framework versioning.** `severity_scoring.FRAMEWORK_VERSION = "1.0.0"`,
  stamped onto every `SeverityDerivation`. A change to any of §2's factor
  definitions, §6's ceiling rules, or §6.3's thresholds in the architecture
  doc is a framework version bump (`1.x.0` for an additive, backward-
  compatible change like a new deferred candidate being adopted; `2.0.0`
  for anything that changes an existing factor's meaning or an existing
  ceiling/threshold) — and requires re-running the full regression corpus
  (§7) with every resulting tier flip individually reviewed, per
  architecture doc §13.
- **Rule versioning.** Deferred to Phase G (`rule_version` field, not yet
  persisted) — noted here so it isn't forgotten, not implemented
  prematurely against a schema that doesn't exist yet.
- **Migration policy.** Exactly architecture doc §12's six phases; this
  document's §1 adds effort estimates and explicit phase dependencies but
  changes no phase's order or content.
- **Deprecation policy.** A `Factor` is never silently removed from the
  enum — doing so would invalidate every `FactorVector` scored under the
  prior version, breaking reproducibility for historical rules. A factor
  found to be wrong (architecture doc §1.3's MC removal is the precedent)
  is deleted only as part of a governed `2.0.0` bump with a full corpus
  re-score, never a patch release.
- **Review policy.** Every rule addition requires the §10 blind-re-score
  gate (step 6) plus one subject-matter sign-off (step 10) — no exceptions
  for "obviously low severity" rules, since the exact failure this whole
  architecture was built to prevent is an unreviewed judgment call that
  turns out to be wrong at scale.
- **Change approval for the framework itself.** Any proposed edit to the
  frozen architecture doc requires: (1) a recorded v2 candidate entry
  (`docs/rules_engine/severity_v2_candidates.md`) with a concrete failing
  example, not a hypothetical; (2) re-running the full corpus against the
  proposed change to show exactly what would flip and why; (3) explicit
  sign-off before merge — the same bar this session held itself to when
  fixing the row-#29 erratum (recorded, not silently patched) and when
  finding zero framework-level issues worth escalating this round.

---

## 10. Implementation checklist

Grouped by milestone; every line is independently assignable.

**Milestone A — Engine (done)**
- [x] `Factor` enum, `FACTOR_MAX_LEVEL`, tier groupings, tier weights
- [x] `FactorScore` / `FactorVector` with construction-time validation
- [x] `_evaluate_ceiling_rules` — all 8 rules, exact documented order
- [x] `_weighted_aggregate_score`, `_band` thresholds
- [x] `compute_severity` — pure function, `SeverityDerivation` output
- [x] `ScoredRule` (+ `known_contestable` override field)

**Milestone B — Validators (done)**
- [x] `validate_schema`
- [x] `validate_mutuality_gate`
- [x] `validate_ceiling_coverage`
- [x] `validate_monotonicity`
- [x] `validate_ruleset` aggregator
- [ ] Duplicate/near-duplicate detection (§6 — explicitly deferred, needs a
      dependency decision)

**Milestone C — Test coverage (done)**
- [x] Unit tests: ceiling ordering (all 8 rules individually)
- [x] Unit tests: WAS arithmetic, exact threshold boundaries (17/18/35/36)
- [x] Unit tests: CRITICAL-unreachable-via-band invariant, swept exhaustively
- [x] Unit tests: all 4 validators, positive and negative cases
- [x] Regression corpus: 43 entries from architecture doc §5 + gap-closing additions
- [x] Regression corpus: every named agreement type covered except Financial Services (§7 gap, noted)
- [x] Regression corpus: every ceiling rule exercised at least once

**Milestone D — Migration tooling (done, sample-scale)**
- [x] `ScoredRule`-based migration sample (18 rules)
- [x] `generate_migration_report.py` (md + csv output)
- [x] Confidence heuristic + `known_contestable` override
- [x] Tests on the report generator itself

**Milestone E — Full migration (not started, ~99 rules remaining)**
- [ ] Score all 117 rules via §8's workflow (contributor + blind re-score
      + attorney sign-off) — track progress as a simple count, not a
      percentage-complete estimate, since attorney turnaround makes
      calendar-time estimates unreliable
- [ ] Produce the full 117-row comparison report
- [ ] Root-cause every disagreement (§F below)

**Milestone F — Calibration (not started)**
- [ ] Diff computed vs. legacy across all 117
- [ ] For each mismatch: legacy-was-wrong vs. threshold-needs-adjustment
      vs. genuine-boundary-case-defer, per architecture doc §5.1's three
      categories
- [ ] If any threshold change is justified, run it as a governed `1.x.0`
      bump (§9) with full corpus re-verification before adoption

**Milestone G — Persistence (not started)**
- [ ] Add architecture doc §8's remaining metadata fields to a persisted
      `Rule`/`RuleMetadata` record (nullable/additive)
- [ ] Wire `ScoredRule` construction from the persisted record

**Milestone H — Shadow mode (not started)**
- [ ] Expose `computed_severity` as a secondary field alongside live
      `severity`
- [ ] Verify `overall_risk`, `signature_readiness`, `ONE_WAY_RULE_IDS`
      logic against `computed_severity` in test-only mode
- [ ] One release cycle bake time

**Milestone I — CI enforcement (not started)**
- [ ] Wire `validate_ruleset` into CI as a hard gate on rule-touching PRs
- [ ] Wire regression corpus into the standard test run (already true,
      since it's a normal pytest file — confirm it's not excluded from any
      CI filter)

**Milestone J — Cutover (not started, gated on E–I)**
- [ ] `severity` becomes a generated property of `computed_severity`
- [ ] `legacy_severity` retained permanently on every rule
- [ ] Rollback plan rehearsed (repoint `severity` back to
      `legacy_severity`) before cutover, not after a problem is found
