# Severity Framework v1.1.0 — Release Notes

**Status: ADOPTED.** `compute_severity()`'s default is `mode="relative"`
as of this release. `mode="absolute"` (the original v1.0 behavior) is
preserved exactly and available as a permanent, named compatibility
mode — not deprecated, not scheduled for removal, just no longer the
default a caller gets without asking.

This supersedes `severity_threshold_v1_1_candidate.md` (kept, marked
superseded, for its detailed rationale and the evidence that led here).

## What changed

One thing: how a **non-ceiling** (band-scored) rule's WAS gets mapped to
a tier.

- **v1.0 (`mode="absolute"`, now compatibility-only):** WAS compared
  against a fixed global cutoff — MEDIUM at 18, HIGH at 36 — the same
  number for every rule regardless of clause type.
- **v1.1 (`mode="relative"`, now default):** WAS compared against that
  rule's own `practical_max` (the WAS it would score if every factor it
  already touches were set to that factor's own ceiling), using the same
  35%/70% cut points the original 18/36 thresholds were derived from.

**Unchanged, in both modes:** all 11 factor definitions, all 8 ceiling
rules, all tier weights, the CRITICAL-only-via-ceiling invariant. This
was a threshold-mechanism change, not a re-derivation of the frozen
architecture doc's factors or ceilings.

## Why

The family-clustering experiment
(`severity_family_clustering_experiment.md`) found the v1.0 absolute
threshold produced comparable behavior for only 2 of 18 observed
practice-area families — 16 were either fully saturated (everything
already above the cutoff) or fully locked out (nothing could ever cross
it, regardless of clause severity), because a clause type's achievable
WAS range is set mostly by how many of the 11 factors it structurally
touches, not by drafting severity. Five alternative explanations for
that pattern were tested and four were falsified or found insufficient
(`severity_family_conclusion_stress_test.md`,
`severity_authoring_bias_and_confidence.md`) before this was accepted as
a real architectural problem rather than an artifact of clustering,
authorship, or coverage gaps.

## Evidence (full detail in `severity_threshold_v1_1_candidate.md`)

Across all 117 migrated rules:

| | v1.0 absolute | v1.1 relative |
|---|---|---|
| LOW | 94 | 49 |
| MEDIUM | 0 | 40 |
| HIGH | 19 | 24 |
| CRITICAL | 4 | 4 |
| Families with genuine internal differentiation | 2 of 18 | 16 of 18 |
| Legacy-severity agreement | 24/117 | 50/117 |

Two families (Administrative, Insurance) remain entirely LOW under
relative banding — checked, not assumed away: both trace to rules scored
at exactly 33.3% of their own factor ceiling (the same reviewer-scoring
pattern documented earlier), now isolated to 2 families instead of
diffused across 16. Not claimed as fully solved; see the candidate doc.

## What did not change as part of this release

- **The single-reviewer status of the underlying migration.** Every
  factor vector this release's numbers are computed from is still the
  Reviewer 1 (Framework Author) pass. The blind re-score gate (Priority 7
  in `severity_authoring_bias_and_confidence.md`) has not happened. This
  release changes how existing vectors get mapped to a tier; it does not
  re-score any vector or substitute for independent review.
- **The `rules_engine.py` live `Rule.severity` field.** This entire
  framework — v1.0 and v1.1 alike — still runs in parallel to the
  production detection engine. Nothing here is wired into
  `signature_readiness`, `overall_risk`, or any user-facing severity
  label yet. That is the Phase G/H work described in
  `severity_implementation.md` §1, still not started.
- **`practical_max`'s known limitation.** A factor's own top level can
  describe a more catastrophic fact than some clause types could ever
  actually exhibit (REV=3 means judgment-level irreversibility; not every
  clause touching REV could become that). Relative banding improves
  cross-family comparability; it does not claim every rule's
  `practical_max` is a perfectly realistic ceiling for its clause type.

## Artifacts

- `severity_scoring.py` — `FRAMEWORK_VERSION = "1.1.0"`,
  `compute_severity(vector, mode="relative")` as default
- `tests/test_severity_relative_banding.py`,
  `tests/test_severity_scoring.py`, `tests/test_severity_regression_corpus.py`
  — updated/extended for both modes (391 tests passing total)
- `docs/rules_engine/severity_migration_report_full_117.md` — regenerated
  under the new default
- `docs/rules_engine/severity_migration_report_full_117_v1_0_absolute_archive.md`
  — the pre-v1.1 snapshot, preserved as the calibration record
- `scripts/practical_max_experiment.py` — explicitly pinned to
  `mode="absolute"`, since it is a historical diagnostic of that specific
  mode's flaw and would misrepresent its own findings if left to follow
  the new default silently

## Version note

`severity_scoring.FRAMEWORK_VERSION` (this document) and
`rules_engine.RULE_ENGINE_VERSION` / `rules/version.json` (the detection
rule catalog, currently 6.0.0) are two separate, independently-versioned
axes — one tracks the severity-scoring framework, the other tracks the
detection ruleset. This release touches only the former.
