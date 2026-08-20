# Step 4A.10.2 Phase 5 — Symmetry Architecture Audit

## A-D. What is a snapshot, what's compared, what's ignored

`_snapshot_indemnity_attribution(local: str) -> Dict[str, Any]` (indemnification_policy_engine.py)
returns exactly 6 keys: `monetary`, `scope`, `defense_control`, `triggers`,
`broad_beneficiary`, `causation_standard`. **`_compare_indemnity_
attribution` can only ever compare these 6 fields — there is no
representation at all for temporal scope/survival or for a cross-
referenced schedule/exhibit label.** This is the real, structural root
cause of the 2 remaining false-symmetry dimensions: it is not that the
comparison mishandles these dimensions, it's that the snapshot never
captures them in the first place — the Step 4A.10.1 "differentiating-
qualifier" safety net was a lexical stopgap around this gap, not a fix to
it (and, per its own design, only fires when the compare_fn found nothing
AND a generic cue word happened to appear — an unreliable proxy for these
two dimensions specifically, as the regression found).

## E-G. UNKNOWN/missing-field handling

Every existing comparison line in `_compare_indemnity_attribution` is
gated `if base["X"] ... and snap["X"] ...` (both sides non-empty/non-
default) before comparing — i.e., **a field UNKNOWN on either side is
correctly never treated as "equal," it's treated as "not compared,"
which correctly avoids asserting false equivalence.** The danger is
narrower than "UNKNOWN treated as equivalent": it's that when NEITHER
side's snapshot has a field AT ALL for a given dimension (because no such
key exists), the aggregate `reasons` list can be empty even though a real
difference exists in the text — indistinguishable, from the caller's
point of view, from "checked and found equal." This is exactly the
Step 4A.10.1 root-cause finding restated at the representation level.

## H-K.

H. A reciprocal opener does NOT override a later exception in this
   architecture — `_detect_reciprocal_asymmetry` runs unconditionally
   whenever a mutual/reciprocal match fires, checking attribution,
   party-specific-exception, procedural-differentiation, and (Step
   4A.10.1) generic-qualifier signals in sequence. No override risk found.
I. Category normalization (`_TRIGGER_KEYWORD_RE`, 7 fixed keywords) CAN
   erase meaningful distinctions when phrasing falls outside the 7
   keywords (Step 4A.10.1 already found and addressed this generally via
   the qualifier safety net for cases where SOME keyword appears).
J. No evidence found of a one-party proviso being promoted to
   document-level scope inappropriately.
K. **Confirmed direct**: cross-referenced differences (a schedule/exhibit
   label attached to one named role) disappear entirely during snapshot
   construction — `_ROLE_ATTRIBUTION_RE` requires an "obligation(s)" noun
   phrase or (after Step 4A.10.1) an "is liable/responsible for" verb
   phrase; "Schedule 3 for Vendor... Schedule 5 for Client" uses neither
   shape, so `detect_role_attributed_asymmetry` never even reaches 2
   attributions (0 found) — the comparison function is never invoked at
   all for this case, confirmed directly this session.

## Conclusion — the fix per Phase 8's own rules

Add TWO genuine new comparison dimensions to the snapshot/compare
architecture (not a qualifier-word safety net, not a phrase blacklist):
1. **Survival/temporal** — a normalized classifier
   (`_classify_survival`) added as a new snapshot key, compared the same
   way `causation_standard` already is.
2. **Schedule/exhibit cross-reference** — a dedicated structural check
   (a named role bound to an external Schedule/Exhibit/Appendix/Annex
   label) added to `_detect_reciprocal_asymmetry` alongside its existing
   party-specific-exception and procedural-differentiation checks; two
   DIFFERENT labels for two DIFFERENT named roles is treated as
   unresolved/asymmetric on the principled ground that the clause's own
   text cannot verify what a cross-referenced document contains — the
   engine cannot know the two schedules are equivalent, so it must not
   assume they are.
