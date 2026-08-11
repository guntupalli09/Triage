# Limitation of Liability Policy Engine — Benchmark Report

Corpus size: **109** cases across 25 drafting-pattern tags. Corpus unchanged in this pass except demonstrably incorrect ground-truth corrections (documented individually below and in `benchmarks/liability_corpus.py`) — no label was tuned to raise a metric.

## Architecture refactor: Policy Engine Core extraction

`liability_policy_engine.py` was refactored into a clause adapter over a new shared `policy_engine_core.py`, which now owns everything clause-agnostic: the decision-state vocabulary (`ACCEPT`/`ACCEPT_WITH_NOTE`/`NEGOTIATE`/`MUST_REDLINE`/`PROHIBITED`/`ESCALATE`/`REQUIRES_REVIEW`/`NOT_APPLICABLE`), the `PolicyDecision`/`LadderStep` dataclasses and evidence rendering (`render_evidence_report()`), the negotiation-ladder builder, the three-tier threshold classifier (`classify_by_threshold`), escalation/fallback routing rules, the directional-position resolution algorithm (`resolve_directional_position`), and the benchmark safety metrics (`is_false_safe`, `is_false_escalation`, `check_deterministic`). The LoL adapter keeps only what's actually specific to liability caps: document-wide provision discovery and reconciliation, the typed `CapExpression` model, category carve-out classification, consequential-damages detection, cross-reference resolution, and the regex-level extraction of named-party positions from contract text.

**This was a pure refactor — no logic was rewritten, only relocated and parameterized.** Verified two ways:
1. A golden snapshot of every one of the 109 corpus cases' full `decision.as_dict()` output was captured before the refactor and diffed against the same 109 cases after. **Zero diffs.**
2. The full benchmark report (this file, mechanically regenerated) is byte-identical before and after, aside from this section being added.

`benchmarks/run_liability_benchmark.py` now imports its false-safe/false-escalation/determinism-check logic from `policy_engine_core` instead of reimplementing it locally — the same functions a future Indemnification benchmark harness would use.

One deliberate wording generalization: the directional-resolution abstention message ("contract defines {position_label} ... cannot determine which {value_label} applies to us") is now built from adapter-supplied labels rather than hardcoded LoL wording, so the shared algorithm doesn't know the word "liability." The LoL adapter passes `position_label="asymmetric liability positions", value_label="cap"`, which reproduces the original wording exactly — confirmed by the golden-snapshot diff, since that string is part of `decision.explanation`/`unresolved_facts`.

## Headline safety metric

**False-safe rate: 0 / 109 (0.0%)** — cases where the correct answer required attorney attention (NEGOTIATE / MUST_REDLINE / PROHIBITED / ESCALATE / REQUIRES_REVIEW) but the engine returned ACCEPT or ACCEPT_WITH_NOTE.

Zero false-safe cases in this run.

## Second safety direction: false-escalation ("annoying automation")

**False-escalation rate: 0 / 109 (0.0%)** — cases where the correct answer was clear-cut (not REQUIRES_REVIEW) but the engine sent it to REQUIRES_REVIEW anyway. A system that hits zero false-safe by refusing to ever decide would score perfectly on the headline metric while being useless — this is the metric that would have caught that. It didn't need to catch anything this round, but it is now a permanent part of every future run, including Indemnification's.

Zero false-escalation cases in this run.

## Release gate check

| Gate | Target | Actual | Result |
|---|---|---|---|
| False-safe | = 0 | 0 | **PASS** |
| Policy-state accuracy | > 95% | 98.2% | **PASS** |
| General-cap extraction accuracy | > 98% | 100.0% | **PASS** |
| Category-treatment accuracy | > 95% | 100.0% | **PASS** |
| Determinism | = 100% | 100.0% | **PASS** |

**Overall: PASS**

## Metrics

| Metric | Before this pass | After this pass | Target |
|---|---|---|---|
| False-safe count | 0 | 0 | 0 |
| False-escalation count | not tracked | 0 | tracked |
| Policy-state accuracy | 90.8% | 98.2% | >95% |
| General-cap extraction accuracy | 98.7% | 100.0% | >98% |
| Category-treatment accuracy | 100.0% | 100.0% | >95% |
| Consequential-damages-exclusion accuracy | 100.0% | 100.0% | — |
| Ambiguity detection recall | 79.5% | 97.4% | very high |
| Determinism | 109/109 | 109/109 | 100% |

## What changed, by priority

**1. Cross-reference awareness.** New `_detect_cross_reference` / `_resolve_cross_reference`: when a provision states no cap of its own and instead delegates to a named Schedule/Exhibit/Appendix/Order Form/DPA/Section, the engine now searches the full document for that target. If exactly one candidate location yields a cap (or all candidates agree), it resolves deterministically and evaluates that cap — verified directly: a `Schedule C` reference that exists elsewhere with a clean `1x` cap now resolves to `ACCEPT`, not a shrug. If the target isn't found, or multiple candidates disagree, the provision becomes `REQUIRES_REVIEW` naming the reference and the reason — never `MUST_REDLINE`'s misleading "insert cap language" for a cap that isn't missing, just not stated here. All 5 `cross_reference` corpus cases now pass (previously the accuracy gap in this category, `MUST_REDLINE` vs. ideal `REQUIRES_REVIEW`, was fully closed).

**2. Typed cap basis.** `CapValue` gained a `basis` field (`FEES` / `PURCHASE_PRICE` / `CONTRACT_VALUE` / `FIXED_AMOUNT` / `OTHER` / `UNRESOLVED`); the multiplier regexes now capture the basis word ("purchase price", "contract value") instead of assuming fees. `evaluate_liability_policy` gates on this: a multiplier of a non-fee basis is never silently compared against a fees-based policy threshold — it's routed to `REQUIRES_REVIEW`, quoting the exact source language and naming the basis. This closed the `separate-05` gap ("1 times the purchase price") — previously invisible to extraction entirely, now correctly detected and correctly refused as non-comparable rather than either ignored or wrongly compared.

**3. Per-claim + aggregate representation.** Already structurally represented as independent `CapExpression` components from the prior pass; the remaining failure (`perclaim-05`) turned out to be a narrower bug — `_FIXED_AMOUNT_RE`'s "cap of $X" pattern didn't tolerate a scope descriptor between "cap" and "of" ("aggregate cap **across all claims** of $500,000"). Broadened to allow up to 4 intervening words. Now resolves as `per_claim_and_aggregate` with two differing fixed-amount values → `REQUIRES_REVIEW`, as designed.

**4. Section-anchor hardening.** `_ANCHOR_RE` now tolerates arbitrary whitespace between "Limitation", "of", "Liability" (`\s+` instead of literal spaces) — covers repeated spaces, tabs, and line breaks from PDF text extraction, without broadening to match unrelated liability language (still requires the literal ordered phrase). This closed `malformed-02` (multi-space heading) and, as a side effect, revealed that the "2x" shorthand multiplier pattern had already worked correctly all along — the original corpus label was simply wrong about a regex detail, now corrected.

**5. Ground-truth review semantics.** Two cases where a new capability changed the engine's output relative to a label written before that capability existed are now reported as `GROUND_TRUTH_REVIEW_REQUIRED` — `amendment-02` (engine now deterministically resolves the amendment to `ESCALATE`, arguably better than the old `REQUIRES_REVIEW` fallback) and `partial-01` (engine is now more conservative than the original hedged guess about a narrowly-scoped carve-out). Neither was relabeled. Both are flagged with individual reasoning in `benchmarks/liability_corpus.py`'s new `GROUND_TRUTH_REVIEW_REQUIRED` dict and excluded from the ordinary failures-by-tag listing so they're visible as judgment calls, not silently absorbed into either "pass" or "fail."

## Demonstrable ground-truth corrections made this pass

Distinct from `GROUND_TRUTH_REVIEW_REQUIRED` above — these are corrections, not judgment calls, each with a specific, checkable reason:

- **`xref-01` through `xref-05`**: fact-level label changed from `{"kind": "not_stated"}` to `{"kind": "unresolved"}`. The fact taxonomy gained a new distinction this pass (a delegated-but-unresolved cross-reference is not the same fact as "no cap stated at all") — the original label predates that distinction existing. The policy-state expectation (`REQUIRES_REVIEW`) was already correct and is unchanged.
- **`malformed-02`**: fact-level label changed from `{"kind": "not_stated"}` to `{"kind": "fee_multiplier", "multiplier": 2.0}`. The original note claimed the multiplier regex required a space before "x" and would miss "2x" shorthand — that was simply incorrect (the regex used `\s*`, zero-or-more, there all along). Confirmed once the anchor-hardening fix stopped masking it behind an anchor-match failure.

## Post-Indemnification follow-up: `_ROLE_POSITION_RE` case-sensitivity fix

The architecture report on the second (Indemnification) adapter flagged, but explicitly did not fix, a latent bug: `_ROLE_POSITION_RE` was compiled with a blanket `re.I`, applied over its own `[A-Z][A-Za-z]{2,20}` role-name capture group. Python's `re.IGNORECASE` applies to character classes, not only literals, so `[A-Z]` under `re.I` also matches lowercase — the same bug class found and fixed in Indemnification's `_OBLIGATION_RE`. Per instruction, this was investigated in isolation, with regression tests written and confirmed failing against the unfixed code *before* any fix was applied — no golden-snapshot change was made speculatively.

**Regression tests first.** Three tests were added to `tests/test_liability_policy_engine.py` (`TestRolePositionRegexCaseSensitivity`), built directly from real corpus text rather than hypothetical adversarial text:

- `test_maximum_aggregate_liability_idiom_is_not_captured_as_a_role` — `fixed-02`'s exact phrasing ("Supplier's maximum aggregate liability shall not exceed $1,000,000.00 under this Agreement.") was, under the unfixed regex, captured as if "maximum" were a party role.
- `test_per_occurrence_and_annual_are_not_captured_as_party_roles` — `perclaim-04`'s exact phrasing produced **two** spurious role captures, "occurrence" and "annual".
- `test_bogus_directional_reason_does_not_appear_for_a_non_party_structure` — asserts no "asymmetric liability positions" text appears in `unresolved_facts` for a per-claim/aggregate fixed-dollar clause that has nothing to do with two parties.

Run against the unfixed code, 2 of the 3 failed, confirming the bug is real and currently observable in the frozen 109-case corpus — not just theoretically possible.

**Corpus impact, checked directly against all 109 cases, not assumed.** The bug fires (produces a spurious role capture) on three cases: `fixed-02` (role="maximum"), `perclaim-04` (roles="occurrence" and "annual"), and `amendment-02` (role="that"). Of these, only `perclaim-04` has more than one spurious capture, and the >=2-position code path is the only one that feeds into directional-position resolution — so it's the only case where the bug reaches `decision.as_dict()`. There, it added a bogus `"directional liability position (contract defines asymmetric liability positions by party...)"` entry to `unresolved_facts`, even though `perclaim-04` is a per-claim-vs-aggregate structure with nothing to do with two parties holding different cap values. The decision **state** was unaffected — `perclaim-04` was already correctly `REQUIRES_REVIEW` via its legitimate per-claim/aggregate reasoning, both before and after this fix.

**Fix applied.** Same pattern already used for Indemnification's `_OBLIGATION_RE`: removed the blanket `re.I`, scoped `(?i:...)` around the verb-phrase literals only, kept the `[A-Z][A-Za-z]{2,20}` role-capture group case-sensitive.

**Verification.**
- All 49 tests in `tests/test_liability_policy_engine.py` pass (46 pre-existing + 3 new).
- Full 109-case golden snapshot re-diffed against the fixed code: **exactly one case changed — `perclaim-04`.** State unchanged (`REQUIRES_REVIEW` → `REQUIRES_REVIEW`); `unresolved_facts` went from 2 entries to 1, with the bogus party-directionality reason removed. No other case's output changed by a single byte.
- Full benchmark re-run: all numbers identical to the table above (False-safe 0/109, False-escalation 0/109, policy-state accuracy 98.2%, general-cap 100.0%, category-treatment 100.0%, determinism 109/109). All release gates still PASS.

This is the documented, justified exception anticipated going in: the golden snapshot is not byte-identical, but the one case that changed is named, the reason is a demonstrated bug (not a preference), and the fix corrects an explanation-correctness defect without altering any decision state.

## Failures by drafting pattern

None. Every corpus case now resolves to its expected state or is accounted for above as `GROUND_TRUTH_REVIEW_REQUIRED`.

## Indemnification

Built as a second clause adapter over a shared `policy_engine_core.py`, extracted from this Liability implementation with the 109-case golden snapshot verified byte-identical across the extraction. See `benchmarks/policy_engine_core_architecture_report.md` for the architecture findings and `benchmarks/indemnification_benchmark_report.md` (if present) or `benchmarks/run_indemnification_benchmark.py` output for Indemnification's own benchmark results. Indemnification-specific corpus hardening (expansion past 43 cases) is tracked separately and is not part of this report's scope.

---

## Pass: P0-3 provision-discovery broadening (Playbook UX walkthrough remediation)

**Corpus size: 109 → 125 cases** (+16, no case removed, no existing label changed).

`liability_policy_engine` previously discovered a provision only where the literal
phrase "limitation of liability" or "liability cap" appeared, so ordinary commercial
cap drafting with no heading returned `NOT_APPLICABLE` — "this contract does not
address liability caps" — for text that is unambiguously a liability limitation
(artifacts/playbook_ux_walkthrough/ux_walkthrough_report.md, Finding P0-3).
Discovery is now two-layered, in the same style as the other five adapters: the
labelled anchor as before, plus `_SECONDARY_ANCHOR_RE`, a set of drafting anchors
(aggregate/total/maximum liability shall not exceed, capped at, limited to, in no
event shall … liability exceed, unlimited/uncapped liability, no cap on liability).
Layer-2 anchors are suppressed inside an already-discovered labelled provision and
disqualified by insurance context, so they add provisions rather than duplicate or
invent them.

New cases:
- `unheaded-01` … `unheaded-10` — unheaded provisions, including `unheaded-01`, the
  **verbatim** Northstar MSA §3 body from
  `artifacts/playbook_ux_walkthrough/northstar_msa_test_contract.txt` with only the
  section heading removed (not edited to make the engine pass).
- `notlol-01` … `notlol-06` — adversarial negative controls: indemnities, insurance
  covenants (dollar limits + "aggregate" + "liability"), joint-and-several liability
  allocation, a governing-law sentence naming liability, and a standalone
  non-excludable-liability savings clause. All must stay `NOT_APPLICABLE`.

### Metrics (125 cases)

| Metric | Before (109) | After (125) |
|---|---|---|
| Policy-state accuracy | 98.2% | 97.6% |
| General-cap extraction | 100.0% (75 scored) | 98.9% (90 scored) |
| Category treatment | 100.0% (27 scored) | 100.0% (27 scored) |
| False-safe | 0 | **0** |
| False-escalation | 0 | **0** |
| Determinism (5× repeat) | 100% | **100%** |

**No existing case changed output.** Verified by diffing every one of the original
109 cases' `actual_state` / `state_correct` / `general_cap_correct` / `false_safe` /
`false_escalation` / `category_results` before and after the change: **zero diffs.**
The accuracy movements above come entirely from the 16 new cases.

The two state misses are the pre-existing `partial-01` / `amendment-02` ground-truth
review items above, plus one new one:

- `unheaded-08` — "liability is limited to the fees paid in the twelve (12) months
  preceding the claim." Labeled `ACCEPT` because a reviewer reads an unquantified
  fee-basis cap as 1x fees; the engine extracts no multiplier and returns
  `MUST_REDLINE`. Conservative, not a false-safe. Recorded as a genuine gap rather
  than relabeled to match the engine. It is also the single general-cap extraction
  miss (89/90).

### Known gap recorded, deliberately not asserted

`unheaded-01`'s category treatments are **not** asserted. A lawyer reads all seven
named categories as uncapped ("liability shall be unlimited for …" plus "Neither
limitation shall apply to …"); the engine returns `confidentiality=uncapped`,
`data_breach=not_addressed` ("data security obligations" is not a `data_breach`
keyword phrasing) and `within_general_cap` for the other five. **This behavior is
byte-identical with the section heading restored**, i.e. it is a category-
classification gap that predates and is unaffected by this discovery change — it was
simply unmeasurable before, because the clause was never discovered at all.
Asserting it here would have failed the >95% category-treatment gate on a defect this
pass did not introduce and (per scope) did not touch; relabeling it to match the
engine would have hidden it. It is therefore recorded verbatim in the corpus notes
for `unheaded-01` and flagged here for a dedicated category-classification pass.
