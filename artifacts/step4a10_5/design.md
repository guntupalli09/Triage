# Step 4A.10.5 — Structural Value Generalization: Design

## Mandate

Step 4A.10.4 eliminated false symmetry (FS=0/116) on a genuinely fresh
corpus by requiring positive structural proof of sameness before
declaring symmetry. But its own frozen corpus exposed a real cost:
FA=18/51 (35%) on genuinely symmetric drafting restated in different
words per role, because three specific dimension classifiers
(survival, monetary) and the equal-treatment escape hatch had narrow,
closed-phrase vocabulary that didn't recognize legitimate paraphrase
("remains on the hook for five years" vs. the only-recognized
"survives ... for a period of five years"; "does not exceed twelve
months' fees" vs. the only-recognized "$X capped at"; "that same
control" vs. the only-recognized "the same").

The user's framing: reduce false asymmetry by replacing closed lexical
recognition with STRUCTURAL/normalized value establishment wherever
feasible, while preserving the Step 4A.10.4 burden of proof intact —
symmetry may be declared only when material dimensions are positively
established as equivalent. This is explicitly NOT a request to loosen
the invariant; it's a request to make the classifiers that FEED the
invariant less narrow, the same generalization move already applied to
role-attribution discovery in Step 4A.10.3.

## Changes

1. **`WORD_NUMBERS`** (`policy_engine_core.py`) extended past ten
   (eleven..twenty, thirty, forty, sixty, ninety). This is a genuinely
   closed, finite set (English number words) — extending it is not the
   phrase-list anti-pattern this program otherwise rejects; it's
   filling a real gap ("twelve months' fees" previously couldn't parse
   "twelve" at all).

2. **`_MONETARY_DURATION_FEES_RE`** (new): recognizes a cap stated as a
   DURATION of fees ("twelve months' fees," "two years' fees") as its
   own value shape, verb-agnostic — the value is the (quantity, unit)
   phrase itself, not whichever governing verb introduces it ("capped
   at"/"tops out at"/"does not exceed"/...). New `MonetaryTreatment`
   kind `"duration_fees"` with a `duration_months` field normalized
   onto a shared scale, same normalization strategy `_classify_survival`
   already uses for its own (magnitude, unit) tuple.

3. **`_SURVIVAL_DURATION_NUMBER_RE` + `_SURVIVAL_CONTINUATION_CUE_RE`**
   (new): generalizes `_classify_survival` past its one rigid phrase
   ("survives ... for a period of N years") by separating the
   NUMBER+UNIT (which can appear as "five-year" or "five years" after
   any governing verb) from CONTEXT confirming it describes
   survival/continuation (tail, survive(s), "on the hook," "remains
   liable," continues, extends, "after this Agreement ends," "post-
   termination") rather than some unrelated duration elsewhere in the
   clause. Both must be present — this is not a bare number-anywhere
   match.

4. **`_EQUAL_TREATMENT_WEAK_CUE_RE`** widened to accept "that same"/
   "this same" alongside "the same" — a demonstrative pronoun referring
   back to a value just stated for the OTHER role is the same
   equal-treatment assertion, just a different (equally common)
   determiner.

None of these changes touch `role_texts_structurally_equivalent` or the
`established_equal_fn` gating logic itself — Step 4A.10.4's burden of
proof is untouched. They only make it EASIER for a classifier to
positively establish a real value, so more genuinely-equal cases clear
the bar the fail-closed check already enforces; they cannot make it
easier for a genuinely different case to slip through, since a wrong
extracted value still fails `_any_dimension_established_equal`'s
equality check and falls through to the (unchanged) structural
fail-closed comparison.

## Development iteration (dev-replay only, NOT final validation)

Replaying the already-seen Step 4A.10.4 frozen corpus (187 cases) as
development evidence: FA dropped from 18/51 (35%) to 0/51 (0%),
CS rose from 24/51 (47%) to 42/51 (82%). The remaining 9 CR cases
(all SYMMETRIC-labeled) are a SEPARATE, pre-existing, already-documented
discovery-layer gap (non-canonical mutual-opener phrasing like "Either
party shall indemnify and hold harmless the other," which doesn't match
either the dedicated reciprocal-opener regex or `_OBLIGATION_RE`'s
generic two-role capture) — unrelated to this step's target
(paraphrase-sensitive VALUE classifiers) and not touched here. FS
remained 0/116. Zero regression on any historical benchmark, unit test,
or dev control.
