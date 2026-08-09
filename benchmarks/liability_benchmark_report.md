# Limitation of Liability Policy Engine — Benchmark Report

Corpus size: **109** cases across 25 drafting-pattern tags.

## Headline safety metric

**False-safe rate: 0 / 109 (0.0%)** — cases where the correct answer required attorney attention (NEGOTIATE / MUST_REDLINE / PROHIBITED / ESCALATE / REQUIRES_REVIEW) but the engine returned ACCEPT or ACCEPT_WITH_NOTE.

Zero false-safe cases in this run.

## Metrics

| Metric | Result | Target |
|---|---|---|
| Policy-state accuracy | 90.8% (109 cases) | >95% |
| General-cap extraction accuracy | 98.7% (75 scored) | >98% |
| Category-treatment accuracy | 100.0% (27 scored) | >95% |
| Consequential-damages-exclusion accuracy | 100.0% (8 scored) | — |
| Ambiguity detection recall (REQUIRES_REVIEW) | 79.5% (31/39) | very high |
| False-safe rate | 0.0% (0/109) | ≈0% |
| Determinism (5x repeat, byte-identical) | 109/109 identical | 100% |

## Failures by drafting pattern

Grouped by tag so recurring gaps in one drafting pattern are visible together, rather than as N isolated case failures. Extraction logic was not modified to force individual cases to pass — these are the actual current gaps.

### `cross_reference` — 5 failing case(s)

- `xref-01`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-02`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-03`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-04`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-05`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`

### `separate_caps` — 1 failing case(s)

- `separate-05`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`

### `per_claim_vs_aggregate` — 1 failing case(s)

- `perclaim-05`: expected state `REQUIRES_REVIEW`, got `ESCALATE`

### `partial_carveout` — 1 failing case(s)

- `partial-01`: expected state `ACCEPT`, got `NEGOTIATE`

### `malformed` — 1 failing case(s)

- `malformed-02`: expected state `ACCEPT_WITH_NOTE`, got `NOT_APPLICABLE`; general-cap extraction mismatch

### `amendment` — 1 failing case(s)

- `amendment-02`: expected state `REQUIRES_REVIEW`, got `ESCALATE`

### `window_boundary` — 1 failing case(s)

- `amendment-02`: expected state `REQUIRES_REVIEW`, got `ESCALATE`

## Remediation pass — before/after

|  | Before | After |
|---|---|---|
| False-safe count | **15** | **0** |
| Policy-state accuracy | 73.4% | 90.8% |
| General-cap extraction accuracy | 96.0% | 98.7% |
| Category-treatment accuracy | 92.6% | 100.0% |
| Consequential-damages accuracy | not consumed by evaluator at all | 100.0%, and now a real policy input |
| Ambiguity detection recall | 38.5% | 79.5% |
| Determinism | 109/109 | 109/109 |

**Release gate: PASS.** Zero false-safe cases. The corpus was rerun unchanged except one demonstrably incorrect ground-truth label (`multisupercap-04`: 1.5x is above the 1.0x preferred threshold under `DEFAULT_POLICY`, so `ACCEPT_WITH_NOTE` is arithmetically correct, not `ACCEPT` — a labeling arithmetic error, not an engine gap) and two labels corrected in the prior review pass (malformed clauses whose heading itself is destroyed). No label was adjusted to make a case pass; each correction is noted individually with its rationale.

## What changed, by priority

**Priority 1 — document-wide provision discovery.** `extract_liability_facts` now finds every `_ANCHOR_RE` match across the full document, not just the first, and builds a `Provision` per anchor (deduping anchors within 300 characters as the same clause mentioning itself twice). Multiple provisions are reconciled deterministically: an explicit amendment/restatement signal (`hereby amended`, `amended and restated`, `supersedes`, ...) makes the superseding provision controlling; provisions that agree are treated as consistent duplicates; anything else is `REQUIRES_REVIEW` listing every candidate provision and its value, never a silent first-pick. This directly fixed both `window_boundary` false-safes (`multisection-02`, and `amendment-02`'s *false-safe* component specifically — see below). Verified with a dedicated regression test using a >3000-character document where the superseding cap sits well past the old fixed window.

**Priority 2 — typed `CapExpression`.** Replaced the flat `CapValue` general-cap field with `CapExpression`, representing `simple`, `greater_of`, `lesser_of`, and `per_claim_and_aggregate` structures explicitly. `effective_cap()` resolves a structure to one comparable value only when that's deterministically possible (e.g. greater-of two multipliers reduces via `max()`) and returns a specific unresolved reason otherwise (e.g. "cannot resolve a greater of structure mixing a fee multiplier and a fixed dollar amount without the actual annual fee value"). This is what took `greater_of`/`lesser_of` from 8 false-safes to 0.

**Priority 3 — directional/asymmetric positions.** `PartyPosition` tracks each named role's cap independently; `_resolve_directional_position` maps "ours" from `policy.contract_side`. A `mutual`-configured policy facing a contract with unequal party-specific caps returns `REQUIRES_REVIEW` rather than guessing; a `buy_side`/`sell_side` policy resolves to *our* position specifically (verified: evaluating a sell-side policy against a contract where the Vendor's stated cap is worse than the Customer's correctly drives the decision off the Vendor figure, not the easier-to-parse Customer one). Unrecognized/unmappable role names never fall back to evaluating whichever side happened to parse — they return `REQUIRES_REVIEW` naming the roles that couldn't be mapped.

**Priority 4 — safe-direction defects, regression-tested first.** Two real bugs were found and fixed, both diagnosed by reading engine output directly before changing anything:
- `_EXCLUDE_PHRASE_RE` (consequential-damages exclusion detection) missed "neither party shall be liable," "shall Supplier be liable" (no "either/any party" wording), and "damages are excluded" — broadened to a more general `in no event shall (?:\w+\s+){0,3}be liable` plus explicit "excluded" phrasing.
- The category exclusion-signal check (used for carve-out detection like "except for breaches of fraud") was replaced entirely: instead of local-window proximity checks (which both under- and over-attributed carve-outs to the wrong category — see `multisupercap-01/-03/-05` in the original report), it now computes one forward-coverage span per exclusion signal across the whole provision, crediting every category named within that span up to the next sentence/clause boundary. This correctly credits a coordinated list ("...shall not apply to fraud or gross negligence.") to *both* categories while still stopping at a new independent clause ("...misconduct, **and** liability for confidentiality breaches **shall not exceed** 4x...") so an unrelated category's own cap doesn't get swept in.

**Priority 5 — consequential damages as real policy inputs.** `PolicyRule` gained `require_consequential_damages_exclusion` and `required_consequential_carveouts_json`. `evaluate_liability_policy` now folds these into the same unresolved-facts gate as everything else (ambiguous language → `REQUIRES_REVIEW`) and the same missing-protection downgrade as category exceptions (required but absent → `NEGOTIATE`). Previously these facts were extracted and silently unused — the exact "false sense of coverage" the review flagged.

**Provenance.** Every `PolicyDecision` now carries `controlling_provision` (section label, excerpt, offsets), and `our_position`/`counterparty_position` when directional resolution engaged. `PolicyDecision.render_evidence_report()` produces the section-labeled, evidence-quoting block requested in the review, wired into the review UI's finding popover (source line, our/counterparty position chips) and the "Apply approved redline" flow unchanged.

## Remaining gaps (all non-catastrophic — none is a false ACCEPT)

- **`cross_reference` (5 cases).** A clause that states no number and instead points to a schedule/exhibit for the actual cap resolves to `MUST_REDLINE` ("insert cap language"), which is a safe but slightly misleading instruction — the ideal is `REQUIRES_REVIEW` ("verify the referenced schedule"). Out of scope for this pass: resolving a cross-reference would mean reading and correlating a different section of the document by name, not just failing safe on the current one.
- **`separate_caps` (`separate-05`, 1 case).** Uses "purchase price" instead of "fees" as the basis word — the extractor's cap-value patterns are fee-scoped by design; a non-fee basis is a distinct, documented gap, not a directional-resolution failure.
- **`per_claim_vs_aggregate` (`perclaim-05`, 1 case).** "Each claim is subject to a cap of $100,000, subject to an aggregate cap... of $500,000" — both values are fixed amounts, so the fallback ambiguity path (which only compares fee multipliers or flags mixed kinds) sends this to `ESCALATE` rather than the more precise `REQUIRES_REVIEW` for an unrepresented per-claim/aggregate split. Still safe, still routes to a human.
- **`partial_carveout` (`partial-01`, 1 case).** A carve-out scoped narrowly ("gross negligence *in performing data security obligations*") no longer gets credited as satisfying a *separate* `data_breach` requirement — this is the engine now being **more conservative** than the original hedged ground-truth guess, not a regression; the note on this case when it was written already flagged uncertainty about whether it should count.
- **`malformed-02` (1 case).** Excess whitespace between words in "Limitation   of   Liability" breaks the literal-space anchor regex; a genuine, narrow, documented robustness gap, not attempted in this pass.
- **`amendment-02` (1 case, listed under both `amendment` and `window_boundary`).** This is the corpus's headline stress test, and it no longer fails unsafely — but its exact recorded state (`REQUIRES_REVIEW`, chosen when the label was written before this capability existed) no longer matches what the engine now does: it deterministically reconciles the amendment (explicit "hereby amended and restated" language) and resolves to `ESCALATE` on the amendment's 6x figure. Per the instruction not to tune labels to improve metrics, this label was left unchanged rather than "corrected" to match a capability that didn't exist when it was written — but a deterministic, evidence-backed `ESCALATE` is arguably the *better* answer, not a worse one, and is explicitly one of the two acceptable reconciliation outcomes (deterministic resolution or `REQUIRES_REVIEW`) called for in Priority 1.

## Indemnification

Not started. Per the review checkpoint, this report is for review before any further clause-type work begins.
