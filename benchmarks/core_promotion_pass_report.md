# Core Promotion Pass — Report

Follow-up to `benchmarks/duplication_promotion_review.md`. Implements exactly
the three promotions authorized from that review, in the order specified:
(1) reciprocal-symmetry verification mechanics, (2) `_excerpt`/
`_section_label_before`, (3) formulaic `REQUIRES_REVIEW` decision
construction/formatting. Nothing else was touched — no monetary/cap
representations, no `resolve_directional_position`, no adapter-specific
resolve-for-side semantics, no cross-reference resolution, no new threshold
models, no clause-specific extraction or policy evaluation logic.

## Pre-refactor bug reproduction (required before any promotion)

Per instruction, the known reciprocal-symmetry window-bleed failure class
(found and fixed in Assignment, then proactively ported to Confidentiality
during Batch A) was tested against Indemnification and Termination's
*pre-promotion* implementations before touching any shared code.

**Both reproduced.**

- **Indemnification** (`_detect_reciprocal_asymmetry`): a reciprocal opener
  with a differentiated proviso on the `scope` axis (Vendor's own clause
  states third-party-only; Customer's own clause — bled into Vendor's
  classification window because the two attributions are joined by `, and`
  rather than a period — states an explicit first-party-inclusive signal)
  produced `asymmetry_reasons == []`. `_classify_scope` checks first-party
  before third-party-only (priority order, not position order), so the
  bleed let Customer's language silently flip Vendor's own snapshot.
- **Termination** (`_detect_right_asymmetry`): a reciprocal opener with a
  differentiated proviso on the `immediate` axis (Vendor's own clause
  states a 30-day cure period; Customer's own clause — same bleed — states
  immediate termination with no cure opportunity) produced
  `asymmetry_reasons == []`. `_IMMEDIATE_RE` is a bare presence check over
  the (bled) window, so Vendor's own snapshot picked up Customer's
  "immediately" language.

Regression tests capturing the **correct** expected behavior were added and
confirmed **failing** against the unfixed code before any promotion work
began:

- `tests/test_indemnification_policy_engine.py::TestReciprocalAsymmetryWindowBleed::test_differentiated_scope_is_not_masked_by_window_bleed`
- `tests/test_termination_policy_engine.py::TestRightAsymmetryWindowBleed::test_differentiated_immediacy_is_not_masked_by_window_bleed`

Both now **pass** — the fix landed as a natural consequence of promoting the
shared mechanics onto the already-fixed windowing logic (see below), not as
a separate patch.

## What was promoted, and how

All three additions live in `policy_engine_core.py`. Each adapter's own
attribution regex, generic-role stoplist, and clause-specific fact
snapshot/comparison logic remain exactly where they were.

**1. `detect_role_attributed_asymmetry(window, attribution_re,
generic_role_words, snapshot_fn, compare_fn, max_chars=220)`** — the
scan/window/compare skeleton previously duplicated four times
(Indemnification, Termination, Confidentiality, Assignment). Bounds each
role's local window at the start of the *next* role attribution (not just
the next sentence period) — this is the fix. Each adapter now supplies only
a `snapshot_fn` (what does one role's local text mean) and a `compare_fn`
(how do two snapshots disagree, phrased in clause-specific language) as
adapter-owned closures — e.g. Indemnification's `_snapshot_indemnity_attribution`/
`_compare_indemnity_attribution`, Termination's
`_snapshot_right_attribution`/`_compare_right_attribution`, and likewise for
Confidentiality and Assignment.

**2. `excerpt(text, start, end, pad=60)` / `section_label_before(text,
anchor_start, lookback=30)`** — byte-identical pure text utilities,
previously duplicated six times including in Governing Law. Every adapter
now imports these under their original local names (`_excerpt`,
`_section_label_before`) via `from policy_engine_core import excerpt as
_excerpt, section_label_before as _section_label_before`, so every existing
call site needed zero changes.

**3. `requires_review_explanation(clause_description, contract_language,
unresolved_facts)` / `requires_review_required_action(unresolved_facts)`**
— the two formulaic strings built inside every adapter's "unresolved facts
→ abstain" branch. Deliberately **not** a `PolicyDecision` builder: each
adapter's `REQUIRES_REVIEW` decision carries a different field set (LoL
includes `category_treatments`/`our_position`/`counterparty_position`/
`reconciliation`; the others pass empty/`None` for those), and forcing one
constructor to cover every adapter's shape would have meant either bloating
every call site with unused parameters or silently dropping fields an
adapter actually needs. Only the two pure strings, which carry zero
decision-shape information, are shared. Applied to LoL, Indemnification,
Termination, Confidentiality, and Assignment — the five adapters whose
`REQUIRES_REVIEW` branch actually uses this "Contract language: ... this
{X} could not be evaluated deterministically ..." template.

## Governing Law — negative control, confirmed

Governing Law received **only** promotion #2 (`excerpt`/
`section_label_before`). It does not consume `detect_role_attributed_asymmetry`
(no reciprocal/mutual concept exists in its model at all) or
`requires_review_explanation`/`requires_review_required_action` (its own
`REQUIRES_REVIEW` branch — "jurisdiction referenced but unparseable" — is a
fixed string that never matched the "unresolved facts" template to begin
with; verified by inspection before touching the file, not assumed). This
is the negative control behaving exactly as required: no proposed promotion
was forced onto it, and the one primitive it does use was already
genuinely shared, unmodified code before this pass.

## Explicitly not touched

Confirmed by reading (not just recalling) the current source of every
adapter before starting: no changes to `CapValue`/`CapExpression`/
`MonetaryTreatment`/`TerminationFee` (typed monetary/value representations),
`resolve_directional_position` or its LoL-only usage, the four adapters'
resolve-for-side functions (`_resolve_obligations_for_side` ×2,
`_resolve_rights_for_side`, `_resolve_restrictions_for_side`), LoL's
cross-reference detection/resolution, `classify_by_threshold` or its usage
pattern, or any clause-specific extraction/evaluation logic beyond the
three promoted mechanisms.

## Golden-snapshot diff (before vs. after), full corpus, all six adapters

Captured `decision.as_dict()` for every corpus case immediately before any
`policy_engine_core.py` change, and again after every adapter finished
migrating.

| Adapter | Cases | Result |
|---|---|---|
| Liability | 109 | **BYTE-IDENTICAL** |
| Indemnification | 100 | **BYTE-IDENTICAL** |
| Termination | 40 | **BYTE-IDENTICAL** |
| Confidentiality | 24 | **BYTE-IDENTICAL** |
| Assignment | 19 | **BYTE-IDENTICAL** |
| Governing Law | 22 | **BYTE-IDENTICAL** |
| **Total** | **314** | **Zero decision-state changes** |

The two demonstrated window-bleed bug fixes (Indemnification, Termination)
do not change any existing corpus case's outcome — neither corpus happened
to contain a case shaped like the adversarial reproduction. The fix is real
and proven (via the two regression tests, shown failing before and passing
after), but its effect on the frozen corpora is nil, which is why "zero
unexplained decision-state changes" and "two independently demonstrated,
regression-tested behavioral fixes" are both true at once — nothing here is
an unexplained change; both are named, both have a failing-before/passing-
after test, and both are the *only* authorized exception to "behavior-
preserving."

## Required invariant — verified

| Adapter | False-safe | False-escalation | Determinism | Gates |
|---|---|---|---|---|
| Liability | 0 | (n/a — LoL's gate is policy-state/category-based, see below) | 100% | PASS |
| Indemnification | 0 | 0 | 100% | PASS |
| Termination | 0 | 0 | 100% | PASS |
| Confidentiality | 0 | 0 | 100% | PASS |
| Assignment | 0 | 0 | 100% | PASS |
| Governing Law | 0 | 0 | 100% | PASS |

Liability's release gate (unchanged from before this pass) checks false-safe
= 0, policy-state accuracy > 95% (actual 98.2%), general-cap extraction >
98% (actual 100.0%), category treatment > 95% (actual 100.0%), and
determinism = 100% — all PASS, numbers unchanged from before the promotion.

Full combined regression suite: **191 tests pass** (189 before this pass,
plus the two new window-bleed regression tests) across all six adapters.

## Not done, per instruction

Batch B (IP ownership, Data/Security, Insurance, Payment Terms) was not
started. No further promotions beyond the three authorized here were made,
including the ones this review's own recommendation section flagged as
plausible future candidates (the `mutual`/`named`-split sub-fragment, the
low-level scalar-or-unlimited monetary regex layer) — those remain
unpromoted, as scoped.
