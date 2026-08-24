# ABSENCE_MATRIX

This supersedes-by-reference `artifacts/fact_admission_architecture/
ADAPTER_MATRIX.md`'s "Absence-state matrix (all 12 adapters)" section —
that table (mapping PRESENT+ESTABLISHED / PRESENT+UNRESOLVED /
RECOGNITION_UNCERTAIN / CONFIRMED_ABSENT / NOT_APPLICABLE /
DEPENDENCY_UNRESOLVED / EVALUATION_ERROR to each adapter's actual
decision states) was re-spot-checked in this session (liability,
confidentiality, warranties — one of each of the three distinct
sub-patterns documented there) and found accurate; not reproduced in
full here to avoid drift between two copies of the same table. See that
document for the complete per-adapter breakdown.

## Hard invariant, re-verified this session

**"No extraction result" never equals "confirmed absent" without
independent evidence**, for all 12 adapters. Mechanism (unchanged from
prior session, re-confirmed present):

- `CONFIRMED_ABSENT` (→ `NOT_APPLICABLE`) is reachable only when
  deterministic discovery found nothing AND semantic discovery (a) ran
  (b) completed without error (c) found nothing.
- A provider error/timeout/malformed response on that same no-anchor path
  becomes `RECOGNITION_UNCERTAIN`, routed to `REQUIRES_REVIEW` in every
  one of the 12 adapters (via an existing safe branch in 5 adapters, or
  an explicit new branch added in 7 — see the prior matrix for which is
  which).

## What Phase 0 of THIS session adds to this picture

The absence-vs-uncertainty distinction above only matters for a review
that actually runs through `apply_active_policies()` — which, per
PRE_IMPLEMENTATION_MAP.md's central finding, only happens in `cutover`
mode. In the default `shadow` mode, none of this absence-state machinery
produces the user-visible result at all; the legacy liability-only path
has no equivalent RECOGNITION_UNCERTAIN concept for the other 11 clause
types (it doesn't evaluate them at all). This is not a regression
introduced by either branch — it is the pre-existing mode-gating
mechanism — but it means the absence-matrix's guarantees are currently
inert for real users, not actively protecting anyone, until cutover mode
is active.
