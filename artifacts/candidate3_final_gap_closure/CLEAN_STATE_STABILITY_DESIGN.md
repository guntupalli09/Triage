# Clean-State Stability Design (Root Cause C)

## Fix implemented

1. `ip_ownership_policy_engine._OWNERSHIP_PASSIVE_RE` broadened: `shall\s+be\s+(?:solely\s+)?owned\s+(?:solely\s+|exclusively\s+)?by` — the adverb now correctly sits between "owned" and "by" (previously the fix attempt mistakenly placed it BEFORE "owned", which never matched the actual phrasing at all — see commit history for the corrected version).
2. `ip_ownership_policy_engine._nearest_category` changed from a single raw-nearest-distance search to a two-pass search: pass 1 excludes any category keyword sitting inside a subordinate qualifier span (`_SUBORDINATE_QUALIFIER_SPAN_RE`: `including|except(ing)?|other than|excluding` up to the next comma/semicolon/period); pass 2 (only if pass 1 finds nothing) falls back to the original raw-nearest-distance search unchanged. This directly fixes the category-misattribution regression the first fix attempt caused, without weakening the heuristic for cases where a subordinate-qualifier keyword legitimately IS the only category mention available.

## Why this generalizes rather than patches one fixture

The subordinate-qualifier exclusion is a structural, not phrase-specific, fix: ANY clause of the shape `"<subject category>, including/except/other than <different category>, shall be owned by <party>"` is now handled correctly, regardless of which two categories are named or which party is named. Verified with a freshly-worded variant (`test_subordinate_qualifier_does_not_hijack_category_attribution`, using "Deliverables"/"background technology" — neither phrase appears in the burned corpus or in `benchmarks/ip_ownership_corpus.py`) as well as the original `conflict-02` benchmark case, both passing.

## Clean-state stability beyond `ip_ownership-080`

This mission's Section 0 re-verification (`ROOT_CAUSE_MAP.md`) found no OTHER confirmed clean-state provider-variance case in the current burned-corpus or repeatability data beyond `ip_ownership-080` — `ip_ownership-099`, `warranties-199`, and `sla-219` all toggle only between two SAFE states (`REQUIRES_REVIEW`/`NOT_APPLICABLE`), which the Candidate 3 remediation mission's Section 15 explicitly carved out as acceptable (never touches a clean state). No new instances of this class were discovered while implementing or testing Root Causes A/B, and no adapter besides `ip_ownership` was found to share the specific "regex word-order gap on the one field a `PRESENT_BUT_UNRESOLVED`-suppressing check also inspects" shape — but this claim is scoped to what this mission's fresh adversarial tests and the (pending) real-provider repeatability run below actually exercised, not a blanket guarantee that no other adapter has an analogous latent gap.

See `PROVIDER_VARIANCE_ROOT_CAUSE.md` for the full run-by-run trace and the considered-and-rejected blanket "deterministic completeness invariant."
