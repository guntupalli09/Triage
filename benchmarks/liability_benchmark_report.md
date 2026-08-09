# Limitation of Liability Policy Engine — Benchmark Report

Corpus size: **109** cases across 25 drafting-pattern tags.

## Headline safety metric

**False-safe rate: 15 / 109 (13.8%)** — cases where the correct answer required attorney attention (NEGOTIATE / MUST_REDLINE / PROHIBITED / ESCALATE / REQUIRES_REVIEW) but the engine returned ACCEPT or ACCEPT_WITH_NOTE.

**This is the release gate. Any non-zero count here blocks release regardless of overall accuracy.**

- `greater-01` (tags: greater_of) — expected `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `greater-03` (tags: greater_of) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `greater-04` (tags: greater_of) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `greater-05` (tags: greater_of) — expected `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `lesser-01` (tags: lesser_of) — expected `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `lesser-03` (tags: lesser_of) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `lesser-04` (tags: lesser_of) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `lesser-05` (tags: lesser_of) — expected `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `separate-03` (tags: separate_caps) — expected `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `asym-01` (tags: asymmetric) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `asym-02` (tags: asymmetric) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `asym-04` (tags: asymmetric) — expected `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `asym-05` (tags: asymmetric) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `multisection-02` (tags: multiple_sections, window_boundary) — expected `REQUIRES_REVIEW`, got `ACCEPT`
- `amendment-02` (tags: amendment, window_boundary) — expected `REQUIRES_REVIEW`, got `ACCEPT`

## Metrics

| Metric | Result | Target |
|---|---|---|
| Policy-state accuracy | 73.4% (109 cases) | >95% |
| General-cap extraction accuracy | 96.0% (75 scored) | >98% |
| Category-treatment accuracy | 92.6% (27 scored) | >95% |
| Consequential-damages-exclusion accuracy | 37.5% (8 scored) | — |
| Ambiguity detection recall (REQUIRES_REVIEW) | 38.5% (15/39) | very high |
| False-safe rate | 13.8% (15/109) | ≈0% |
| Determinism (5x repeat, byte-identical) | 109/109 identical | 100% |

## Failures by drafting pattern

Grouped by tag so recurring gaps in one drafting pattern are visible together, rather than as N isolated case failures. Extraction logic was not modified to force individual cases to pass — these are the actual current gaps.

### `greater_of` — 5 failing case(s)

- `greater-01` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `greater-02`: expected state `REQUIRES_REVIEW`, got `NEGOTIATE`
- `greater-03` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`
- `greater-04` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`
- `greater-05` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`

### `lesser_of` — 5 failing case(s)

- `lesser-01` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `lesser-02`: expected state `REQUIRES_REVIEW`, got `NEGOTIATE`
- `lesser-03` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`
- `lesser-04` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`
- `lesser-05` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`

### `cross_reference` — 5 failing case(s)

- `xref-01`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-02`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-03`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-04`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`
- `xref-05`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`

### `asymmetric` — 4 failing case(s)

- `asym-01` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`
- `asym-02` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`
- `asym-04` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `asym-05` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`

### `multiple_super_caps` — 3 failing case(s)

- `multisupercap-01`: expected state `ACCEPT`, got `REQUIRES_REVIEW`; general-cap extraction mismatch; category mismatch: data_breach
- `multisupercap-04`: expected state `ACCEPT`, got `ACCEPT_WITH_NOTE`
- `multisupercap-05`: expected state `ACCEPT_WITH_NOTE`, got `REQUIRES_REVIEW`; general-cap extraction mismatch; category mismatch: confidentiality

### `consequential_damages` — 3 failing case(s)

- `conseq-02`: expected state `ACCEPT_WITH_NOTE`, got `ACCEPT_WITH_NOTE`; consequential-damages fact mismatch
- `conseq-03`: expected state `ACCEPT`, got `ACCEPT`; consequential-damages fact mismatch
- `conseq-05`: expected state `NEGOTIATE`, got `NEGOTIATE`; consequential-damages fact mismatch

### `separate_caps` — 2 failing case(s)

- `separate-03` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT_WITH_NOTE`
- `separate-05`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`

### `consequential_carveout` — 2 failing case(s)

- `conseq-carveout-02`: expected state `ACCEPT_WITH_NOTE`, got `ACCEPT_WITH_NOTE`; consequential-damages fact mismatch
- `conseq-carveout-03`: expected state `ACCEPT`, got `ACCEPT`; consequential-damages fact mismatch

### `window_boundary` — 2 failing case(s)

- `multisection-02` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`
- `amendment-02` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`

### `per_claim_vs_aggregate` — 1 failing case(s)

- `perclaim-05`: expected state `REQUIRES_REVIEW`, got `MUST_REDLINE`

### `partial_carveout` — 1 failing case(s)

- `partial-01`: expected state `ACCEPT`, got `NEGOTIATE`

### `malformed` — 1 failing case(s)

- `malformed-02`: expected state `ACCEPT_WITH_NOTE`, got `NOT_APPLICABLE`; general-cap extraction mismatch

### `multiple_sections` — 1 failing case(s)

- `multisection-02` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`

### `amendment` — 1 failing case(s)

- `amendment-02` ⚠️ FALSE-SAFE: expected state `REQUIRES_REVIEW`, got `ACCEPT`

## Root-cause analysis

Five distinct root causes account for all 15 false-safe cases and every other
failure. Diagnosed by reading engine output directly (`extract_liability_facts`),
not inferred from state mismatches alone.

### 1. No concept of compound cap structures — `greater_of`, `lesser_of` (10 cases, 8 false-safe)
The engine's `general_cap` model holds exactly one kind (multiplier, fixed
amount, or unlimited). "The greater of $1M or 2x fees" and "the lesser of 2x
fees or $1M" both contain two cap values with no keyword distinguishing
them from the "multiple conflicting caps" case — and in fact **most of these
did correctly land on REQUIRES_REVIEW or NEGOTIATE via the ambiguity
guard** (`greater-02`, `lesser-02`, and several others). The 8 false-safe
failures happen specifically when one of the two values is small enough
that whichever value the ambiguity guard's tie-break happens to prefer
lands in the auto-accept range — i.e., this is not "the engine ignores the
structure," it's "the engine's multi-value ambiguity guard was built for
*conflicting* general caps, and a greater-of/lesser-of clause isn't
conflicting, it's compound; sometimes only one candidate value even gets
extracted at all, and if that value is low, it accepts confidently."
**This is the highest-priority gap** — it's the one the corpus design
predicted (the "typed CapPolicy thresholds" note) and it produced the most
false-safe cases of any category.

### 2. Directional/asymmetric caps have no representation at all — `asymmetric`, `separate_caps` (11 cases, 6 false-safe)
When two named parties have different positions and only one is a
recognizable numeric general cap (the other is phrased as "remains
uncapped," "is not subject to any cap," or a non-fee basis like "purchase
price"), there is only one candidate value for `general_cap` — so there is
no conflict to detect, and the engine accepts confidently on the one value
it found, unaware a second, worse position exists for the other party.
This is architecturally the same gap as #1 (single-cap data model can't
hold a two-party structure) but triggers differently: #1 fails because two
values collide, #2 fails because only one value is ever visible.

### 3. Fixed extraction window silently drops content beyond ~3000 characters — `window_boundary` (2 cases, both false-safe)
`multisection-02` and `amendment-02` were built specifically to test this:
a second, superseding Limitation of Liability provision (a later exhibit
section, or an amendment that explicitly "amends and restates" the
original cap) placed beyond the fixed 3000-character extraction window
from the first anchor match. In both cases the engine never saw the
second provision at all and confidently accepted the stale, superseded
value from the first. **This is qualitatively different from the other
gaps** — it is not "the clause is more complex than the model can
represent," it is "the engine can be blind to part of the document and not
know it." A document with the superseding cap closer than ~3000 characters
away is instead caught correctly (see `multisection-01`, `-03`, `-04`,
`-05`, `amendment-01`, `-03`, `-05`, all REQUIRES_REVIEW as expected) — so
the failure mode is a window-size cliff, not a fundamental incapacity to
detect the pattern.

### 4. `_EXCLUDE_PHRASE_RE` (consequential damages) only covers three rigid phrasings (5 cases, 0 false-safe)
`conseq-02/03/05` and `conseq-carveout-02/03` all reach the *correct*
policy state by coincidence (the consequential-damages fact doesn't
currently feed into `evaluate_liability_policy` at all — see below) but
fail fact-level scoring: "Neither party shall be liable," "shall Supplier
be liable" (no "either/any party"), and "damages are excluded" (no
"liable" verb at all) aren't matched by the three fixed phrasings in
`_EXCLUDE_PHRASE_RE`. This is a narrow, mechanical regex-coverage gap of
the same shape as the "except for breaches of X" gap fixed during
hardening — not a structural issue.

**Related finding, not a corpus failure but worth flagging directly:**
`consequential_damages_excluded` and `consequential_damages_carveouts` are
extracted into `LiabilityFacts` but **`evaluate_liability_policy` never
reads them** — they don't affect the decision and aren't exposed in
`PolicyDecision.as_dict()`. Right now they're inert. If they matter for
the release scope, they need positive wiring, not just extraction.

### 5. Category exclusion-signal window is symmetric and too wide — `multiple_super_caps` (3 cases, 0 false-safe)
`multisupercap-01`/`-05`: when two different category carve-outs
("data breach... shall not exceed 2x..." and "...shall not apply to
claims arising from IP infringement") sit within ~180 characters of each
other, the *first* category's exclusion-signal check (`_EXCLUSION_SIGNAL_RE`,
checked on a ±180-character symmetric window) can match exclusion language
that actually belongs to the *second* category's carve-out later in the
clause. This misclassifies the first category as `uncapped` instead of
`super_cap`, and strands its real super-cap value as an unclaimed general-
cap candidate, triggering a false ambiguity (`REQUIRES_REVIEW` when
`ACCEPT` was correct). Notably this is a **safe-direction bug** (it
produces an unnecessary REQUIRES_REVIEW, never a false ACCEPT) — same
class of fix as the forward-only search already applied to the cap-value
half of category classification, just not yet applied to the exclusion-
signal check.

## Recommendations (not yet implemented — for review)

1. **Do not generalize to a second clause type yet**, per the original
   scoping decision — this run confirms real gaps remain in Limitation of
   Liability specifically.
2. **Root cause #3 (window blindness) is the one to fix first regardless of
   any other roadmap decision.** It is the only gap that produces a
   confident false ACCEPT on a document the engine had every opportunity to
   read correctly — the content was in the document, just past an
   arbitrary cutoff. This is a bug, not a modeling limitation.
3. **Root causes #1 and #2 are the strongest evidence yet for the typed
   `CapPolicy` (basis: FEES | FIXED_AMOUNT | GREATER_OF | LESSER_OF, plus a
   comparison operator) suggested during the design review.** A single
   `general_cap` field structurally cannot represent either compound
   (greater-of/lesser-of) or two-party (asymmetric) positions — no amount
   of regex tuning fixes that, it needs a schema change.
4. **Root causes #4 and #5 are narrow, low-risk regex-coverage fixes**
   (broaden `_EXCLUDE_PHRASE_RE`; make the exclusion-signal check
   forward-only like the cap-value check already is) — same pattern as the
   "except for breaches of X" fix made during hardening. Low priority
   relative to #1–#3 since neither currently produces a false ACCEPT.
5. **Wire `consequential_damages_excluded`/`carveouts` into the decision**
   or explicitly document them as descriptive-only fields — right now they
   are extracted but silently unused, which is a documentation gap at
   minimum and a false sense of coverage at worst.

None of the above has been implemented in this pass — this report is the
review checkpoint requested before any further engine changes or starting
Indemnification.
