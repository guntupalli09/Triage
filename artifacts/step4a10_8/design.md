# Step 4A.10.8 — Equal-Treatment Cue Structural Exclusion: Design

## Architectural rule (per the user's mandate)

An equal-treatment cue can override fail-closed comparison only when it
independently asserts equivalence of the relevant obligations or
material dimension. A reciprocal quantifier used to CREATE two
obligations (each/either/both/every, "one another"/"each other," the
nominalized "duty ... binds/applies to/governs" shape) is structural
scaffolding, not evidence that those obligations' TERMS are equivalent.

## Implementation (stronger than special-casing "both")

`_equal_treatment_cue_present` now masks out every match of
`_MUTUAL_RECIPROCAL_RE` from the text BEFORE scanning for cue words
(replacing the matched span with spaces, preserving character offsets
so all downstream negation/proximity logic still operates on real
positions). This is structural, not lexical: it doesn't special-case
"both" or enumerate quantifier words in the cue-exclusion logic —
whatever `_MUTUAL_RECIPROCAL_RE` recognizes as an opener (currently
each/either/both/every + verb-phrase, "the parties ... indemnify each
other/one another", the nominalized duty-binds shape, and "mutual
indemnification") is automatically excluded from cue consideration, and
stays correct if that regex is ever widened again. Only text describing
the two NAMED roles' actual obligations can trigger a cue.

## A related, real bug found and fixed during this step's own iteration

`_GENERIC_ROLE_WORDS` was missing "every" — added to the reciprocal-
opener quantifier set in Step 4A.10.7 but never added to the
generic-role stoplist the general role-discovery block
(`_NAMED_ROLE_MENTION_RE`) checks against. This meant "Every party
shall indemnify the other..." was treating the capitalized word "Every"
itself as a bogus third named role, corrupting the >=2-distinct-roles
comparison for every case using that quantifier. Found via this step's
own adversarial dev suite (11/16 initial failures were "Every party"
cases); fixed by adding "every" to `_GENERIC_ROLE_WORDS`.

## Development/adversarial iteration (explicitly non-authoritative)

Per the user's non-negotiable methodological constraint, no
authoritative corpus was built until this was exhausted:

1. **`scripts/step4a10_8_dev_adversarial_controls.py`** (new): every
   reciprocal-opener SHAPE this program recognizes (each/either/both/
   every/"one another"/"mutually...each other") crossed with a
   downstream difference in EACH of: scope (first/third-party), 
   survival, monetary cap, causation, defense control, claim category
   (trigger-keyword), proviso, and cross-reference — both the
   genuinely-asymmetric and genuinely-symmetric mirror-image version of
   each (96 cases total). All 96/96 pass after the two fixes above.
   Two of the initial 16 failures (before the "every" fix, persisting
   after it) were traced to test-construction issues (my own template
   used untracked dimensions — geographic scope and free-text claim
   category, neither an actual snapshot field — combined with a
   trailing-connector paraphrase artifact; this is the SAME pre-
   existing, already-disclosed "untracked dimension" limitation found
   in the Step 4A.10.5/4A.10.6 reports, not a new defect). Rewrote
   those two templates to use the dimensions actually tracked by the
   snapshot model (first/third-party scope, trigger-keyword claim
   category) — 96/96 pass cleanly.
2. Step 4A.10.6's own 11-case adversarial suite
   (`step4a10_6_dev_adversarial_controls.py`) still passes 11/11,
   confirming the defense-control mechanism is undisturbed.
3. Dev-replay of all 5 previously-built, now-non-authoritative frozen
   corpora (4A.10.4, the burned 4A.10.5, 4A.10.5b, 4A.10.6, 4A.10.7):
   **FS=0 across all five**, including 4A.10.7's own corpus (the one
   whose authoritative run found FS=4) — now 0/124.

## The "steers negotiations on" finding (per the user's correction)

Step 4A.10.7's report characterized this defense-control paraphrase gap
as a "corpus-authoring imperfection." Per the user's correction: a
human reader would reasonably understand "steers negotiations on any
claim" as a defense/control-allocation statement, so the classifier's
failure to normalize it is real evidence of a vocabulary/generalization
boundary in `_RESPONSE_PROCESS_NOUN_RE`'s stem list — not something to
discount just because it hurt an FA count. It remains unfixed here
(out of this step's scope, which targets the equal-treatment cue, not
the defense-control stem list) but is retained as disclosed, standing
evidence of a real, low-priority boundary, not deleted from the record.
