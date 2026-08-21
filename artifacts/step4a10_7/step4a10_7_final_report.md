# Step 4A.10.7 — Reciprocal-Opener Discovery Generalization: Final Report

## Executive verdict

**FAILED. FS = 4/124 on the authoritative frozen corpus — a real,
dangerous safety regression. The 4A.10.x sequence does NOT stop here
and Step 4A.11 is NOT authorized.** The regression is fully root-caused
to a genuine, pre-existing defect in the symmetry comparator
(`_equal_treatment_cue_present`'s "both" handling), exposed — not
created — by this step's discovery widening. This is new evidence the
comparator is defective, which the user's own stated rule treats as
license to fix it; that fix is intentionally NOT made in this report
(would violate the run-once commitment for this corpus) and is
scoped as the required next step instead.

## What this step did (recap)

Narrowly generalized `_MUTUAL_RECIPROCAL_RE` (the discovery-layer gate
for the reciprocal-obligation extraction path) to recognize
"either/both/every party" (not just "each party"), "one another" (not
just "each other"), and a nominalized "party's indemnification duty ...
binds/applies to/governs" shape. The symmetry comparator itself
(`_detect_reciprocal_asymmetry` and everything it calls) was not
touched — confirmed by identical `policy_engine_core.py` and
`indemnification_policy_engine.py` hashes at the point the comparator
logic lives, aside from the discovery regex change itself.

## Root cause of FS=4

All four false-symmetric cases share the exact same shape: an opener
using **"Both parties shall indemnify the other..."** — a phrasing this
step newly made discoverable — followed by a real, stated asymmetry
(geographic scope: "covers claims worldwide" vs. "confined to domestic
claims only").

```
_equal_treatment_cue_present(window, roles) is called on the FULL
window, which includes the opener sentence itself. The WEAK cue regex
matches bare "\bboth\b" anywhere in the window. Its guard requires
either a nearby role name (not the issue here) OR a nearby "party"/
"parties" word — and "Both parties" IS exactly that: the reciprocal
QUANTIFIER itself, sitting directly next to "party," at the very start
of the window. The cue mechanism was built to recognize a DRAFTER'S
STATEMENT that two named roles are treated the same ("applicable to
both Contractor and Owner," "governs both Vendor and Client
identically") — it was never designed to see the word "both" used as
the reciprocal opener's own OPENING QUANTIFIER, because before this
step, "both parties ... shall indemnify ..." was never even discovered
as an obligation at all. This step's discovery widening is what first
exposes this latent comparator defect to real input.
```

Confirmed directly:
```python
>>> _equal_treatment_cue_present(
...   "Both parties shall indemnify the other for claims arising under "
...   "this Agreement; Content Licensor's duty covers claims worldwide, "
...   "whereas Distribution Partner's duty is confined to domestic "
...   "claims only.",
...   ["Content Licensor", "Distribution Partner"])
True   # WRONG — the clause states a real, explicit asymmetry
```
`role_texts_structurally_equivalent` correctly found the two spans
NOT equivalent (as it should — the content genuinely differs); the
equal-treatment cue escape hatch incorrectly stood the structural
fail-closed check down anyway, because it fired on the opener's own
grammar rather than on any actual statement about the two NAMED roles.

## Why this was not patched in this report

The user's explicit rule: **"do not touch the symmetry comparator
unless 4A.10.7 produces new evidence that it is defective."** This
frozen run is precisely that evidence — but the user's separate,
equally explicit methodological constraint for this whole 4A.10.x
sequence is to freeze code, lock a corpus, run it exactly once, and
accept whatever comes out with no further code changes in response to
that specific run's results. Patching now, in this report, to make
THIS corpus's numbers look better would repeat the exact process
violation already disclosed and corrected once in Step 4A.10.5
(`artifacts/step4a10_5/process_violation_note.md`). The frozen result
stands as reported: **FAILED**.

## Everything else, for completeness

- FA = 5/56, all from a single defense-control template using
  "steers negotiations on any claim" — "negotiations" is outside
  `_RESPONSE_PROCESS_NOUN_RE`'s stem list. This is a corpus-authoring
  imperfection on my part (a template picked for "regression
  confirmation" without checking it against the known stem list before
  locking), not a new code defect — the defense-control mechanism was
  untouched this step and continues to have the same known, disclosed,
  finite (if wide) stem coverage documented in the Step 4A.10.6 report.
- All 12 dimension families minus the monetary_treatment family (which
  contains the FS cases, mislabeled in the corpus generator — the
  second `opener_asym` template is actually a geographic-scope
  asymmetry, not monetary; a corpus-authoring labeling error, noted for
  the record but irrelevant to the FS finding itself, which is about
  the text content, not its label) scored CA cleanly.
- The `genuinely_symmetric_opener` family (28 cases, this step's own
  primary discovery target) — need not be separately reported as clean
  since the FS cases came from the ASYMMETRIC `opener_asymmetric`
  family, not this one; the discovery generalization's RECALL
  contribution is real (see dev-replay evidence in
  `artifacts/step4a10_7/design.md`: 100% symmetric recall on two prior
  corpora) even though this specific frozen run failed its safety gate.
- Production hashes unchanged pre/post execution; determinism confirmed
  (byte-identical re-run); full regression (pytest, historical
  benchmarks, S4) remained clean throughout — this is a narrowly
  isolated defect, not a broad regression.

## Hard gates — honest evaluation

| Gate | Target | Result | Met? |
|---|---|---|---|
| FS | 0 | **4/124** | **NO — FAILED** |
| Symmetric recall | ≥95% | 47/56 = 83.9% (also not met, though secondary given the FS failure) | NO |
| FA | 0 (implied by "preserving FS=0, FA=0") | 5/56 | NO |
| S3/S4 false symmetry | 0 | 4 (all S4) | **NO** |
| UNVERIFIED-clean-symmetry | 0 | 0 (checked directly) | YES |
| Authoritative determinism | 100% | byte-identical re-run | YES |

**This step does not clear its own bar.** Per the user's explicit
instruction, the 4A.10.x sequence does NOT stop, and Step 4A.11 is
**NOT authorized**.

## Required next step (not undertaken here)

A narrowly-scoped **Step 4A.10.8 — Equal-Treatment Cue Opener
Exclusion** should fix `_equal_treatment_cue_present`'s weak-cue check
so it never fires on the reciprocal opener's OWN quantifier word
("each"/"either"/"both"/"every" immediately followed by "party"/
"parties" at the start of the mutual-opener match itself) — the cue
should only recognize "both"/"the same"/etc. when used to describe
something about the two NAMED roles' treatment, not the opener's own
grammar. This is a comparator fix, licensed by this report's own
frozen evidence per the user's stated rule, and should be followed by
yet another genuinely fresh, never-seen frozen corpus, built and locked
before any code changes, run exactly once, accepting whatever results.
