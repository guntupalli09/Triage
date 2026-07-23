# Adding a new rule: the actual, current workflow

This is the concrete, up-to-date version of `severity_implementation.md`
§8's contributor workflow — that section describes the full aspirational
process (including the blind re-score gate and attorney sign-off, still
not built). This document describes what's **actually enforced by code
today**: `tests/test_new_rule_severity_gate.py` and
`severity_factor_data.py`.

## What's enforced, and what isn't

**Enforced (the build fails if you skip it):** a new rule's severity in
`rules_engine.py` must match what `compute_severity()` computes from a
factor vector you provide in `severity_factor_data.py`. You cannot add a
rule with a hand-picked severity and no scoring behind it.

**Not enforced, and can't be automated:** the factor scoring itself.
Reading the clause, deciding which of the 11 factors it touches, and
writing a real justification for each non-zero one is analytical work —
the same work every one of the 117 existing rules required. The gate
checks that your severity *matches your scoring*, not that your scoring
is *correct*. That's what the still-pending blind re-score gate and
attorney sign-off are for (see `severity_authoring_bias_and_confidence.md`,
Priority 7) — this workflow doesn't replace that, it just stops an
un-scored or inconsistent rule from shipping silently in the meantime.

## Steps

1. **Write the detection rule** in `rules_engine.py` as usual (pattern/
   anchors/nearby, rule_id, title, rationale). Pick a `severity=` value —
   your best guess is fine, you'll find out immediately if it's wrong.

2. **Score the 11 factors** against `severity_architecture.md` §2's
   definitions, reading only the clause language and doctrine — not by
   analogy to a similar-looking existing rule (see
   `severity_migration_full.py`'s module docstring for why that
   distinction matters). Add an entry to `severity_factor_data.py`:

   ```python
   _add("YOUR_NEW_RULE_ID", "ClauseCategoryName", "AffectedPartyRole", _vec(
       FB=(2, "Why this factor is at this level, citing the clause language."),
       REV=(1, "..."),
       # only non-zero factors need a real justification; the rest
       # default to a boilerplate "not implicated" via _vec()
   ))
   ```

   `ClauseCategoryName` should match an existing category if the clause
   type is a real match (feeds the cross-rule monotonicity check,
   `severity_scoring.validate_monotonicity`) — check
   `scripts/rule_family_clustering_experiment.py`'s `_family_of` or grep
   existing `_add(...)` calls for the closest fit before inventing a new
   one.

3. **Run the gate:**
   ```
   python3 -m pytest tests/test_new_rule_severity_gate.py -q
   ```
   If your rule isn't in `severity_factor_data.py` yet, or your vector's
   computed severity doesn't match what you wrote in `rules_engine.py`,
   this fails with the exact rule_id and the exact severity you should
   use instead — e.g. `hand-set severity='high' does not match
   framework-computed severity='critical' ... Set severity=Severity.CRITICAL`.
   Fix the mismatch (usually: update `rules_engine.py`'s `severity=` to
   match what the framework says — that's the point).

4. **Run the full suite** (`python3 -m pytest tests/ -q`) to confirm
   nothing else broke, and add detection-pattern tests (positive/
   negative/messy-formatting) the same way every other rule does.

5. **Optionally add a corpus entry** to
   `tests/test_severity_regression_corpus.py` if the clause type is
   distinctive enough to be worth a permanent regression example — not
   required by the gate, but keeps the golden set growing per
   `severity_implementation.md` §7's target of 150–200 entries.

## Why the gate exempts the 117 existing rules

`severity_factor_data.KNOWN_LEGACY_RULE_IDS` is a frozen list of the 117
rule_ids scored in the Reviewer 1 migration. 67 of those currently have a
hand-set `severity` in `rules_engine.py` that disagrees with what the
framework computes (see `severity_migration_report_full_117.md`) —
that's the known, tracked, single-reviewer-pass result, not a bug in the
gate. Reconciling those 67 is the separate, deliberate Phase 5 cutover
decision (`severity_implementation.md` §12), not something a new-rule
gate should force by breaking the build today for 67 rules nobody just
touched. Every rule_id **not** in that frozenset — i.e. anything added
from here forward — gets the full check with no exemption.
