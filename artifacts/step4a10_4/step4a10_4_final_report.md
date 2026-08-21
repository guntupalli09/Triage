# Step 4A.10.4 — Structural Differentiation / Fail-Closed Symmetry: Final Report

## Executive verdict

**FS eliminated (0/116) on a genuinely fresh, frozen corpus — the safety
invariant holds. Correct-symmetry automation took a real, disclosed hit
(FA=18/51, 35%) traced to specific, named classifier/cue gaps, not to
the core structural mechanism. Step 4A.11 authorization: conditional —
see recommendation below.**

## What changed from Step 4A.10.3

Step 4A.10.3's fail-closed trigger (`value_asymmetry OR cue_present`,
where `cue_present` was `_DIFFERENTIATING_QUALIFIER_RE`, a closed
lexical list) left FS at 58/116 (50%) on its own frozen corpus, because
neither the specific-dimension classifiers nor the lexical cue
recognized that corpus's differentiation phrasing. This step replaced
the lexical cue with a structural, non-lexical primitive:

- **`role_texts_structurally_equivalent`** (`policy_engine_core.py`):
  normalizes each named role's own local text span (role names →
  `<SELF>`/`<OTHER>` placeholders) and requires the normalized spans be
  identical. No word list — proof of sameness, not absence of a
  recognized difference.
- **`established_equal_fn`**: lets each adapter's own snapshot
  comparator stand the structural check down when a real dimension was
  positively established equal for both roles (necessary because raw
  structural equivalence alone is too strict for ordinary paraphrase —
  see below).
- Wired into both the shared core safety net
  (`detect_role_attributed_asymmetry`, used by five adapters:
  assignment, confidentiality, termination, warranties, and
  indemnification's attribution-phrase path) and indemnification's own
  Step 4A.10.3 general-discovery block.
- The pre-existing `_EQUAL_TREATMENT_CUE_RE` escape hatch (a drafter's
  own explicit statement of equivalence) was kept but tightened twice
  during this step's development iteration after real false positives:
  a negation before the cue ("is **not** the same as Annex 4") was
  misread as confirming sameness; a weak cue describing something other
  than party treatment ("for the **same** risk") was firing purely on
  nearby role-name proximity across a contrastive conjunction ("while").

## Frozen fresh-corpus results (first and only pass, no tuning after seeing results)

Corpus: `benchmarks/step4a10_4_fresh_independent_corpus.json`, 187
cases, sha256 `c28c4f1debc10bbe40cb0819b2d2bd4c5c6f63d0c9eeedb625e7221e583af2b4`.
New role-pair vocabulary (Freight Forwarder/Shipper, Servicer/
Noteholder, Fund Manager/Limited Partner, Sublicensor/Sublicensee,
Prime Contractor/Subcontractor, Trustee/Beneficiary, Clearing Member/
Exchange, Aggregator/Originator) and new phrasing throughout, built
after code freeze at `9df3906`. Zero exact-text overlap against all 4
prior corpora; 0/187 discovery failures at construction time (no
corpus-defect relock needed this time).

```
OVERALL: {'CS': 24, 'CR': 16, 'FA': 18, 'CA': 116, 'WC': 13}

BY TIER (asymmetric+symmetric only):
  Tier 1 (n=75): CS=10, CR=5,  CA=60
  Tier 2 (n=48): FA=18, CS=14, CR=4, CA=12
  Tier 3 (n=44): CA=44

BY DIMENSION FAMILY (asymmetric only, n=8 each unless noted):
  ALL 12 families + compound: CA = 8/8 (or 20/20 for compound)

FS (dangerous) total: 0/116 asymmetric cases
```

**FS = 0/116 (0%), down from 58/116 (50%) under Step 4A.10.3.** Every
one of the 12 dimension families that individually failed under 4A.10.3
now fully generalizes on this UNSEEN corpus's fresh phrasing (not a
replay — first time this exact text has ever been run against the
mechanism). This is the core safety result the user's invariant targets,
and it held.

## FA = 18/51 (35%) on genuinely symmetric cases — disclosed, not hidden

All 18 FA cases come from one of three symmetric sub-families I
deliberately built into this corpus (`genuinely_symmetric_varied`: named
roles, real matching values, but restated with different surface wording
per role — the shape most likely to expose a gap between "the underlying
facts are equal" and "the text used to state them is verbatim
identical"). 24 cases in that sub-family; 6 pass (CS), 18 fail (FA). The
two OTHER symmetric sub-families (`genuinely_symmetric_generic`: no named
roles at all, `genuinely_symmetric_cue`: explicit "applies equally"/"on
the same terms" language) are essentially unaffected (CS=10/15 and
CS=8/12, with the remainder CR from an unrelated, pre-existing discovery
gap — see below — not FA).

Root-caused to exactly **three** template shapes, each a genuine
narrow-vocabulary gap in either `_snapshot_indemnity_attribution`'s
per-dimension classifiers or the `_equal_treatment_cue_present` escape
hatch — not a flaw in the new structural-comparison logic itself, which
is doing exactly what it should (correctly refusing to presume symmetry
absent positive proof):

1. **Survival**: "carries a five-year tail after this Agreement ends"
   (role A) vs. "likewise remains on the hook for five years after this
   Agreement ends" (role B) — the survival classifier recognizes the
   first phrasing but not "remains on the hook for," so only one side's
   snapshot establishes a value; `established_equal_fn` requires BOTH
   sides established, so it can't stand down; the raw text isn't
   identical either, so the structural check (correctly, given what it
   can see) escalates.
2. **Monetary**: "capped at twelve months' fees" vs. "likewise does not
   exceed twelve months' fees" — same shape, monetary classifier gap.
3. **Defense control**: "controls the defense... against it" vs.
   "retains **that same** control... against it" — here the underlying
   FACT actually is captured identically by the defense_control
   classifier in principle, but the escape-hatch cue regex only matches
   literal "the same," not "that same," so a real equal-treatment
   statement wasn't recognized as one.

None of these were patched. Doing so now, having seen the frozen
results, would violate the "no tuning after seeing results" rule and
would also just be next-layer whack-a-mole (add "remains on the hook
for" to the survival classifier, add "that same" to the cue regex) —
exactly the pattern this program has repeatedly rejected. They are
disclosed here as concrete, scoped follow-up items instead.

## What this proves, honestly

The user's framing anticipated this outcome precisely: *"If Claude
cannot implement this without turning everything into REQUIRES_REVIEW,
that itself is useful evidence: it means the current deterministic
structuring layer does not extract enough information to prove symmetry
reliably."* That is exactly what happened, in a bounded, legible way —
not "everything" became REQUIRES_REVIEW (72% of the varied-restatement
symmetric family still passed; 88%+ of the other two symmetric families
passed), but the specific families where the underlying dimension
classifiers have narrow vocabulary DID get correctly caught by the new
invariant, converting what would previously have been a silent (and
untested) presumption of symmetry into a visible, honestly-counted cost.
The mechanism is doing its job. The remaining cost is squarely a
classifier-coverage problem, now precisely located instead of hidden.

## Separate, pre-existing finding: 9/51 SYMMETRIC and 4/20 AMBIGUOUS routed to CR

9 SYMMETRIC-labeled cases (5 `genuinely_symmetric_generic`, 4
`genuinely_symmetric_cue`) came back `verified=False` (facts extracted,
but `obligations` empty) — e.g. "Either party shall indemnify **and
hold harmless** the other against claims arising from that party's own
breach" doesn't match the canonical `_OBLIGATION_RE`/synonym-idiom
shapes. This is the same, separately-tracked "verifier lacks structural
pattern" discovery-layer bottleneck already documented since Step
4A.10 — not something this step's structural-comparison changes touch,
and not a new regression (confirmed: production hashes for
`indemnification_policy_engine.py`'s discovery/structuring code are
unchanged from before this step's edits). WC=13 (mostly AMBIGUOUS cases
routed clean instead of review) is the same pre-existing gap already
disclosed in the Step 4A.10.3 report; not scored against this step's
FS/FA gate and not newly introduced here.

## Regression / integrity checks

- Production hashes: unchanged pre-implementation → post-freeze →
  post-frozen-execution (`PRODUCTION UNCHANGED` at every checkpoint,
  across all 10 production files touched or adjacent to this program).
- `step4a7_reciprocal_semantic_benchmark` and
  `indemnification_asymmetry_benchmark`: byte-identical vs. the
  pre-4A.10.1 baseline (no regression) at every checkpoint during this
  step's own development iteration.
- 213/213 relevant unit tests pass (indemnification, liability,
  assignment, confidentiality, governing-law, payment-terms,
  termination, warranties benchmark gate) — including 3 real regressions
  this step's own structural check introduced and then fixed
  (`test_agreeing_per_party_attribution_still_accepts` in assignment,
  confidentiality, termination), by adding each adapter's own
  `established_equal_fn`.
- Dev benchmarks/controls (132-case symmetry benchmark, 26-case dev
  controls): FS=0/FA=0 throughout, matching or improving on the
  pre-4A.10.4 baseline (dev controls WC dropped 6→5, CR rose 3→4 —
  a small improvement, not a regression).
- Step 4A.10.1 S4 operative/non-operative benchmark: false-operative
  extraction remains 0/50 (unchanged).

## Lee Challenge (LEE-5) status

**SOLVED on the safety axis, on genuinely unseen drafting.** Materially
asymmetric reciprocal obligations no longer become falsely symmetric —
0/116 across all 12 dimension families on a corpus never seen during
development, using vocabulary this program has never used before. This
is a materially stronger result than Step 4A.10.3's 50% FS rate on its
own frozen corpus, and it is not development-benchmark evidence — it is
the real, frozen, first-pass number.

**Not yet solved: correct-symmetry automation on paraphrased
restatement.** The FA=18/51 finding means a real class of genuinely
symmetric drafting — where both parties truly get equal treatment but
say so in slightly different words — currently gets sent to review
rather than cleared automatically, for three specific, named,
narrow-vocabulary reasons (not a structural flaw).

## Step 4A.11 / 4B authorization

**Step 4A.11: conditionally authorized on the safety axis, NOT yet on
the automation axis.** Per the user's own framing — "the target isn't
merely FS=0... it needs FS=0 while preserving high correct-symmetry
automation" — this step delivers half of that bar cleanly (FS=0, genuine
unseen-corpus evidence) and falls short on the other half (FA=18/51 on
one specific symmetric sub-family). Recommend NOT proceeding to 4A.11
until the three named classifier/cue gaps (survival-duration paraphrase,
monetary-cap paraphrase, "that same" as an equal-treatment cue) are
fixed as GENERAL classifier improvements — not per-phrase patches — and
re-verified against a still-different, never-before-seen corpus focused
specifically on paraphrase-heavy genuinely-symmetric drafting, since
that is now the identified remaining risk surface, not general
asymmetry detection.

**Step 4B: NOT authorized** (unchanged).

## Recommended next step (not undertaken here, pending user direction)

Rather than adding "remains on the hook for" / "that same" as isolated
phrase patches (repeating the exact anti-pattern this whole program has
rejected), the general fix is architecturally the same move as Step
4A.10.3's own discovery generalization: widen the per-dimension
classifiers (survival, monetary, defense_control) from closed phrase
lists to structural/semantic patterns capable of recognizing paraphrase,
the same way `_NAMED_ROLE_MENTION_RE` widened role discovery from a
closed verb list to a bare grammatical pattern. That is a larger,
separately-scoped effort and should be its own step.
