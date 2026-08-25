CANDIDATE 4 — PHASE 11: REPEATABILITY RESULTS

48 cases (4 per adapter × 12 adapters) × 5 real-provider executions = 240
total executions. Raw results: `repeatability_results.json`.

## Result

**UNSAFE_CLEAN_STATE_VARIANCE: 2** (of 48 cases tested; 46/48 fully stable).

1. `iv-ip_ownership-0220` ("Title to the deliverables shall transfer to
   Recipient upon Recipient's receipt of Provider's final invoice...") —
   4/5 runs `NOT_APPLICABLE`, 1/5 runs `REQUIRES_REVIEW`. **Verified this
   is a PRE-EXISTING defect, not introduced by this mission's code
   changes**: re-run 5x against the pre-Candidate-4 code (via `git
   stash`) reproduces the identical instability (4× `NOT_APPLICABLE`,
   1× `REQUIRES_REVIEW`). Root cause: no deterministic anchor matches this
   specific phrasing at all (`_ANCHOR_RE` requires "intellectual property"/
   "work product"/"work made for hire"/etc., none of which appear in
   "Title... shall transfer..."), so the ENTIRE decision depends on
   whether the real OpenAI call admits a candidate for this text on a
   given run — a genuine AI-admission non-determinism, not a code defect
   this mission's deterministic-side fix touches (my ip_ownership fix
   only changes behavior once a deterministic anchor IS present and
   operative; here there is none). This is closely related to, but
   distinct from, the deferred `ip_ownership-080` defect (which is about
   an ALREADY-admitted candidate's qualifier composing non-deterministically,
   not about admission itself varying) — reported here as its own,
   separate, genuinely new finding per this mission's explicit instruction
   to report any newly-discovered instance rather than folding it into the
   existing deferred-risk entry.

2. `iv-termination-0433` — 4/5 runs `ACCEPT`, 1/5 runs `REQUIRES_REVIEW`.
   `termination_policy_engine.py` was NOT modified by this mission (see
   `git diff d2820362 HEAD -- termination_policy_engine.py`, empty), so
   this instability is necessarily pre-existing and independent of any
   Candidate 4 change — the same class of real-provider admission
   non-determinism as case 1 above, in a different adapter.

## Assessment

Per this mission's explicit Phase 11 requirement, `UNSAFE CLEAN-STATE
VARIANCE = 0` is REQUIRED. The actual count is **2**, not 0. Both
instances are confirmed pre-existing (not introduced by this mission's
adapter fixes) and both stem from the same underlying mechanism: the real
OpenAI provider's candidate-admission step is not fully deterministic for
certain boundary-line phrasings, and when NO deterministic anchor exists
at all, the adapter's final decision depends entirely on that one
non-deterministic step. This is reported honestly as a hard-gate-adjacent
failure of this mission's own Phase 11 requirement — it is NOT waived or
explained away, even though it predates this mission's changes. See the
final verdict for its effect on `READY TO FREEZE CANDIDATE 4`.
