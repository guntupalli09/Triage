# v1.1 candidate: relative band mode

**Status: SUPERSEDED — ADOPTED.** This proposal was accepted;
`mode="relative"` is now the default as of Framework v1.1.0. See
`docs/rules_engine/severity_v1_1_release_notes.md` for the authoritative
release summary. This document is kept as-is for its detailed rationale,
evidence, and results table, which the release notes summarize but don't
replace — the "not yet the default" framing below is historical, dating
to when this was still a proposal.

---

Original status line (historical): **implemented, tested, NOT the
default.** Available via `compute_severity(vector, mode="relative")`;
the default at the time was `mode="absolute"` (the frozen v1.0 threshold
table). This document was the proposal and evidence for adopting
`relative` as the new default — adoption went through the sign-off
`severity_architecture.md` §13 specifies for any threshold change (the
user directing this session, in lieu of a separate attorney/governance
body which does not yet exist for this project).

## What changed, and what didn't

**Unchanged:** all 8 ceiling rules, all 11 factor definitions, all tier
weights. The CRITICAL-only-via-ceiling invariant (architecture doc §6.1)
holds identically in both modes — verified by
`test_relative_mode_never_produces_critical_via_band` in
`tests/test_severity_relative_banding.py`.

**Changed:** how a non-ceiling (band-scored) rule's WAS is compared
against a cutoff. Absolute mode (`_band`) compares WAS to a fixed global
number (18/36) regardless of which factors that rule's clause type can
even touch. Relative mode (`_relative_band`) compares WAS to that same
rule's own `practical_max` — the WAS the rule would score if every
factor it already touches were set to that factor's own ceiling — using
the *same* 35%/70% cut points the original 18/36 thresholds were derived
from (architecture doc §6.3), just applied against a per-rule denominator
instead of one global one. `practical_max` itself is the exact method
from `scripts/practical_max_experiment.py`, promoted into
`severity_scoring.py` because relative banding needs it at scoring time,
not just for after-the-fact analysis.

This directly targets the family-clustering experiment's finding: no
single global threshold produced comparable behavior across families
because a clause type's achievable WAS range is mostly determined by how
many of the 11 factors it structurally touches, not by drafting
severity. Relative banding removes the shared denominator that made that
comparison unfair in the first place.

## Results across all 117 migrated rules

Reproducible via `scripts/relative_banding_comparison.py`.

| | Absolute (current default) | Relative (candidate) |
|---|---|---|
| LOW | 94 | 49 |
| MEDIUM | 0 | 40 |
| HIGH | 19 | 24 |
| CRITICAL | 4 | 4 |

- 45 of 117 rules change tier between modes.
- Legacy-severity agreement: 24/117 under absolute, **50/117** under
  relative — roughly doubled. (Not the target metric on its own, since
  legacy has its own documented over-escalation issues, but a useful
  cross-check that relative banding isn't just moving numbers around
  arbitrarily.)
- MEDIUM goes from completely unreachable via aggregation (the original
  headline finding) to 40 rules — the band mechanism now does real work.

Family-level distribution under relative banding (all 18 families,
n shown for reference — see
`severity_authoring_bias_and_confidence.md` for per-family confidence):

| Family | n | LOW | MED | HIGH | CRIT |
|---|---|---|---|---|---|
| Other/Commercial Terms | 16 | 10 | 4 | 2 | 0 |
| Data/Privacy | 13 | 2 | 8 | 3 | 0 |
| Administrative | 13 | 13 | 0 | 0 | 0 |
| Financial | 11 | 8 | 2 | 1 | 0 |
| Rights Waiver/Remedy | 8 | 4 | 3 | 1 | 0 |
| Indemnification/Liability Cap | 7 | 2 | 2 | 3 | 0 |
| Unilateral Discretion/Termination | 7 | 0 | 3 | 4 | 0 |
| Lease | 6 | 1 | 2 | 2 | 1 |
| Employment | 5 | 0 | 4 | 1 | 0 |
| Restrictive Covenant | 5 | 2 | 3 | 0 | 0 |
| Loan | 5 | 2 | 1 | 0 | 2 |
| IP/Ownership | 4 | 1 | 1 | 2 | 0 |
| M&A/Partnership | 4 | 0 | 2 | 2 | 0 |
| Regulatory Compliance | 3 | 0 | 3 | 0 | 0 |
| Construction | 3 | 0 | 2 | 1 | 0 |
| Insurance | 2 | 2 | 0 | 0 | 0 |
| Franchise | 2 | 1 | 0 | 1 | 0 |
| Settlement | 2 | 1 | 0 | 1 | 0 |
| Personal Liability | 1 | 0 | 0 | 0 | 1 |

**16 of 18 families now show genuine internal differentiation** — a
qualitative improvement over the absolute mode, where 16 of 18 were
either fully saturated or fully locked out with no real distinction
possible within them.

## What relative banding does NOT fix

**Two families remain entirely LOW: Administrative and Insurance.** This
was checked, not assumed — both cases trace to the exact same root
cause identified in the earlier practical-max experiment: the rules in
question were scored `REV=1` (Administrative) or `FB=1, REV=1`
(Insurance), which is exactly 33.3% of those factors' own ceiling — just
under the 35% MEDIUM cutoff. This is the same reviewer-scoring pattern
already documented (the "33.3% cluster" in
`severity_practical_max_experiment.md`), now cleanly isolated to two
specific families instead of diffused across the whole corpus. It is not
a new failure of relative banding — it's the same known, partially
reviewer-attributable, partially clause-type-intrinsic pattern, now
visible in only 2 families instead of 16.

**The known limitation carried over from the practical-max experiment
still applies**: `practical_max` uses each factor's own absolute ceiling
level, which can describe a qualitatively different, more catastrophic
fact than a given clause type could ever actually exhibit (REV=3 means
judgment-level irreversibility; some clause types touching REV can't
become that regardless of drafting). Relative banding is a genuine
improvement in cross-family comparability, not a claim that every rule's
`practical_max` is a perfectly realistic ceiling for its clause type.

**This is still a single-reviewer result.** All 45 tier changes trace
back to the same 117-rule, single-author migration discussed throughout
this document set. The blind re-score gate (Priority 7,
`severity_authoring_bias_and_confidence.md`) has not happened and would
likely shift some of these numbers, particularly the Administrative/
Insurance boundary cases sitting at exactly 33.3%.

## Recommendation (adopted)

Relative banding is a substantial, tested, working fix to the specific
architectural problem the family-clustering experiments found — not a
patch that hides the symptom. **This recommendation was accepted**: it
went through architecture doc §13's process (full golden set re-run,
explicit sign-off from the user directing this session) and is now the
Framework v1.1.0 default — see `severity_v1_1_release_notes.md`. Making
it the default feeding the eventual Phase 5 cutover
(`severity_implementation.md` §12, still separate — that phase wires
severity into `rules_engine.py`'s live `Rule.severity` field, which this
release does not touch) remains a distinct, not-yet-made decision.
