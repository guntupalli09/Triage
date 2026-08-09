# Limitation of Liability Policy Engine — Benchmark Report

Corpus size: **109** cases across 25 drafting-pattern tags. Corpus unchanged in this pass except demonstrably incorrect ground-truth corrections (documented individually below and in `benchmarks/liability_corpus.py`) — no label was tuned to raise a metric.

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

## Failures by drafting pattern

None. Every corpus case now resolves to its expected state or is accounted for above as `GROUND_TRUTH_REVIEW_REQUIRED`.

## Indemnification

Not started. Per the review checkpoint, this report is for review before any further clause-type work begins. The user's proposed architecture — a shared Policy Engine Core (structured facts → policy evaluator → decision engine → evidence/redline/audit) with clause-specific adapters, rather than a duplicated `indemnification_policy_engine.py` — has not yet been attempted or validated against this codebase; that remains an open design question for when Indemnification work is authorized.
