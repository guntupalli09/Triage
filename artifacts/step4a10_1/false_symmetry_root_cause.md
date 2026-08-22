# Step 4A.10.1 Phase 8 — False-Symmetry Root Cause

## PRE-fix result

54/72 (75%) of the locked benchmark's asymmetric cases are `FS` (dangerous
false symmetry) — spanning 8 of 12 required dimensions entirely: claim
category, monetary treatment, exception/proviso, conditional
applicability, first/third-party, negligence/fault standard, scope,
cross-reference, temporal/survival. Only causation-standard, defense-
control, and compound-multi-dimension cases were caught (`CA`, 18/72).

## Clustered by mechanism (single root cause, not 8 separate bugs)

`_compare_indemnity_attribution`/`_snapshot_indemnity_attribution`
already correctly finds 2+ role-attributed local windows via
`detect_role_attributed_asymmetry` (confirmed directly:
`_ROLE_ATTRIBUTION_RE` finds both `Vendor's indemnification obligation`
and `Client's obligation` in every failing case). The failure is entirely
downstream, at the SNAPSHOT COMPARISON stage: each dimension is checked
via its OWN narrow, closed-vocabulary classifier (`_classify_monetary`,
`_classify_scope`, `_classify_defense_control`, a 7-keyword `_TRIGGER_
KEYWORD_RE` set, `_classify_causation_standard`) — and `_compare_
indemnity_attribution` only emits a reason when BOTH sides' classifiers
produce a NON-empty, DIFFERING value. When either side's local window
phrasing doesn't hit one of those closed classifiers at all (e.g. "third-
party claims of any kind" hits no `_TRIGGER_KEYWORD_RE` category; "no
right to control the defense" needs the exact `_classify_defense_control`
vocabulary; "conditioned on X first exhausting its remedies" isn't a
recognized monetary/scope/trigger/causation pattern at all), the
comparison silently treats that dimension as "nothing to compare" —
functionally identical to "confirmed equivalent," which is the exact
inversion of the safety property this whole program exists to enforce.

**Root cause (single, general): the system currently presumes symmetry
by DEFAULT whenever its closed set of per-dimension classifiers can't
prove a difference, rather than presuming UNRESOLVED whenever the
document itself shows the drafter explicitly attached separate,
differentiating language to two distinctly-named roles.** This is the
same "closed-vocabulary classifier as the only gate" pattern already
found and fixed for indemnification-EXISTENCE discovery in Step 4A.9
(`_risk_transfer_signal_present`) — here it recurs one layer downstream,
at asymmetry discovery instead of obligation discovery.

## Why this is NOT 8 separate fixes

Every one of the 54 FS cases' role-attributed local windows contains an
explicit differentiating-qualifier word or phrase ("only", "while",
"uncapped"/"capped at", "does not apply", "no right to", "regardless of",
"conditioned on", "extends to", "survives... indefinitely" vs.
"terminates upon", "different... limitations") — a general STRUCTURAL
signal ("this proviso attaches distinguishing language to a specific
named role") that is currently detected nowhere, regardless of which of
the 12 dimensions it falls under. A single general safety net at the
`detect_role_attributed_asymmetry` level, mirroring the existing
discovery-signal-without-verification -> REQUIRES_REVIEW pattern already
used elsewhere in this codebase, addresses all 8 missing dimensions at
once without a per-dimension classifier for each.
