# Step 4A.10.4 — Structural Differentiation / Fail-Closed Symmetry: Design

## User's mandate

Step 4A.10.3's own fail-closed trigger (`value_asymmetry OR cue_present`,
where `cue_present` meant `_DIFFERENTIATING_QUALIFIER_RE`) was itself a
closed lexical vocabulary — the same anti-pattern the step set out to
eliminate at the discovery layer, recurring one layer deeper. Six
dimension families (defense control, monetary treatment, first/third-
party, geographic scope, cross-reference/schedule, temporal/survival)
stayed falsely symmetric on the Step 4A.10.3 frozen corpus (58/116, 50%)
because neither the specific-dimension classifiers NOR the lexical cue
recognized this fresh corpus's differentiation phrasing.

The mandated invariant: **a reciprocal structure may be declared
symmetric only if two independently constructed obligation snapshots
exist and every policy-material dimension required for comparison is
established equivalent or explicitly irrelevant. Absence of a difference
cue is not evidence of symmetry.** Burden of proof inverts from "detect a
difference" to "prove sameness."

## Implementation

1. **`role_texts_structurally_equivalent`** (new, `policy_engine_core.py`):
   normalizes each named role's own local text span by substituting role
   names with generic `<SELF>`/`<OTHER>` placeholders, then requires the
   normalized spans be byte-identical. This is non-lexical — it doesn't
   look for any specific word, only for whether the drafter used the
   exact same mirrored language for each role. Two independent call
   sites now use this as the safety-net trigger, replacing
   `_DIFFERENTIATING_QUALIFIER_RE`:
   - the shared core `detect_role_attributed_asymmetry` (used by
     assignment/confidentiality/termination/warranties/indemnification's
     attribution-phrase-based path)
   - indemnification's own `_NAMED_ROLE_MENTION_RE`-based general
     discovery block (Step 4A.10.3's contribution)

2. **`_any_dimension_established_equal`** (indemnification) and its
   per-adapter equivalents (`_any_restriction_dimension_established_equal`,
   `_any_confidentiality_dimension_established_equal`,
   `_any_right_dimension_established_equal`,
   `_any_warranty_dimension_established_equal`, wired via the new
   `established_equal_fn` parameter on the shared core function): real,
   POSITIVELY established agreement on at least one dimension (e.g. both
   roles' spans state the same duration, even worded slightly
   differently around a window-slicing boundary) stands down the
   structural check — this is genuine positive proof, not a lexical
   permission slip, and is necessary because raw-text structural
   equivalence alone is too strict (it would flag "Licensee's obligation
   survives for 3 years" vs. "Licensor's obligation survives for 3 years
   as well" purely for ending in "and" vs. "as well", even though the
   survival dimension was actually extracted and matched for both).
   Always-established boolean fields (`broad_beneficiary`, `immediate`)
   are excluded from this check since False==False would trivially
   satisfy it for every clause and defeat its purpose.

3. **`_equal_treatment_cue_present`** (indemnification): retained as an
   explicit escape hatch for a drafter's own stated equivalence ("applies
   equally", "on the same terms", "both X and Y", "X and Y alike"), but
   tightened during this step's own development iteration after two real
   false positives were found:
   - a negation immediately before the cue ("is NOT the same as Annex 4")
     was matching "the same" and reading a stated DIFFERENCE as a
     confirmation of sameness — fixed via `_EQUAL_TREATMENT_NEGATION_RE`.
   - a weak cue word ("the same", "both", "alike", "identical") used to
     describe something OTHER than party-to-party treatment ("carries its
     own cyber cover for the same risk") was firing purely because a role
     name happened to appear nearby in the sentence — fixed by requiring
     either "party"/"parties" nearby, or a nearby role name NOT separated
     from the cue by a contrastive conjunction ("while", "but",
     "whereas", ...), which signals the sentence is drawing a contrast,
     not stating equivalence.

## Result: this step's own development iteration (dev-replay only, NOT final validation)

Replaying the already-seen Step 4A.10.3 frozen corpus (182 cases) as
development evidence: all 12 dimension families now generalize fully
(FS 0/8 each, was 6/12 families at 8/8 FS under 4A.10.3), FS overall
0/116 (was 58/116), zero regression on symmetric recall (CS=16/40,
unchanged) or any historical benchmark/unit test. This is NOT the real
validation — see the genuinely fresh Step 4A.10.4 corpus and its frozen
single-pass execution for that.
