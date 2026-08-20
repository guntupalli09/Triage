# Step 4A.10.3 — Corpus Construction Defect (found via execution, fixed before re-lock)

The first version of `step4a10_3_fresh_independent_corpus.json` (locked at
commit `7846782`) used "shall make good [claim]" as its base reciprocal
opener verb throughout, in an effort to use fresh vocabulary end to end.
This defeated `_MUTUAL_RECIPROCAL_RE` and `_OBLIGATION_RE` entirely (both
require "indemnify" specifically as the operative verb) — every one of
the 182 cases returned `facts=None` (not even a discovered-but-unresolved
state), so all 182 landed on `CR` for a reason having nothing to do with
the symmetry mechanism under test (a pure discovery-layer miss, already
the known, separately-tracked "verifier lacks structural pattern"
bottleneck from Step 4A.10).

This is a corpus-construction defect discovered via execution (the
Step 4A.8 precedent for this kind of correction: mechanical, not an
after-the-fact relabeling of what "should" have happened). Fix: the base
reciprocal opener verb was changed back to "shall indemnify" throughout
(matching every prior corpus in this program), while keeping fresh,
independently-chosen vocabulary in the DIFFERENTIATING clauses — which is
where the symmetry mechanism is actually being tested — unchanged. No
case's LABEL, dimension, or intended asymmetry content was altered, only
the base verb. Relocked before re-execution; the original (broken) lock
commit `7846782` and this note remain in git history for transparency —
nothing was silently redone.
