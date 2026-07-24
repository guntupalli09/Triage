"""
FULL MIGRATION — Reviewer 1 (Framework Author) Migration.

Every one of the 117 rules in rules_engine.py, scored against Severity
Framework v1.0 (docs/rules_engine/severity_architecture.md) by a single
reviewer (the framework's author). This is Phase 2 of the architecture
doc's migration (§12), NOT Phase 2+3 combined -- it is explicitly a
single-reviewer pass, not the full §10 workflow, which additionally
requires:
  (a) a second contributor blind-re-scoring each vector from only the
      rule's rationale and clause text, and
  (b) a subject-matter/licensed-attorney sign-off.
Neither (a) nor (b) has happened yet. This file's factor vectors are a
real, defensible, individually-justified first pass -- not a rubber stamp
and not analogy-based classification -- but they are one person's
judgment, not independently validated. Treat every row's `legacy_severity`
comparison as a hypothesis for Phase 3 review, not a final answer.

The actual factor-vector data (every _add(...) call) lives in
severity_factor_data.py, not here -- it was extracted into its own
dependency-free module when rules_engine.py needed to read the same data
(to attach factor vectors to Rule objects and gate new rules' severity;
see tests/test_new_rule_severity_gate.py) without creating a circular
import (severity_scoring.py already imports Severity from rules_engine.py,
so rules_engine.py cannot import anything that imports severity_scoring.py
at module level). This file imports that data and combines it with each
rule's live severity/rationale (which does require importing
rules_engine.py) to build the ScoredRule objects the analysis scripts use.

Genuine issues surfaced by doing all 117 (not just an 18-rule sample) are
logged in FINDINGS at the bottom of this file, not silently absorbed.
"""

from rules_engine import RuleEngine, Severity
from severity_scoring import ScoredRule
from severity_factor_data import SCORES_BY_RULE_ID as _SCORES

_engine = RuleEngine()
_LIVE_RULES = {r.rule_id: r for r in _engine.rules}


# ---------------------------------------------------------------------
# Completeness check + ScoredRule construction
# ---------------------------------------------------------------------

_missing = set(_LIVE_RULES) - set(_SCORES)
_extra = set(_SCORES) - set(_LIVE_RULES)
if _missing:
    raise RuntimeError(f"severity_migration_full.py is missing scores for: {sorted(_missing)}")
if _extra:
    raise RuntimeError(f"severity_migration_full.py has scores for unknown rule_ids: {sorted(_extra)}")

FULL_MIGRATION = []
for rule_id, live_rule in _LIVE_RULES.items():
    clause_category, party_role, vector = _SCORES[rule_id]
    FULL_MIGRATION.append(
        ScoredRule(
            rule_id=rule_id,
            clause_category=clause_category,
            affected_party_role=party_role,
            factor_vector=vector,
            legacy_severity=live_rule.severity,
            rationale=live_rule.rationale,
        )
    )

assert len(FULL_MIGRATION) == 185, f"expected 185 scored rules, got {len(FULL_MIGRATION)}"


# ---------------------------------------------------------------------
# FINDINGS -- issues surfaced by scoring all 117, not silently absorbed.
# None of these are framework changes; the frozen v1.0 rubric was applied
# literally throughout. Where a finding suggests the framework itself
# might benefit from a change, it is recorded as a v2 candidate
# observation, not acted on here.
# ---------------------------------------------------------------------
FINDINGS = """
UPDATE (v7.0 rule expansion): FULL_MIGRATION now covers 180 rules, not
117 -- the original 117-rule Reviewer 1 migration plus 63 rules added in
the v7.0 small/midsize-firm coverage expansion (see
docs/rules_engine/README.md and rules/version.json). The 63 new rules
were scored and gated the same way going forward (severity_new_rule_workflow.md,
tests/test_new_rule_severity_gate.py) rather than migrated from a
pre-existing legacy severity, so they do not have a "legacy vs computed"
disagreement to report the way the original 117 do. Everything below this
note describes ONLY the original 117-rule migration and should be read as
a historical record of that specific pass, not as a description of all
180 rules now in FULL_MIGRATION.

UPDATE (Framework v1.1.0): the headline finding below (#0) was recorded
under the v1.0 absolute band mode and directly motivated the v1.1
relative-mode default now shipped in severity_scoring.py. It is kept
verbatim as the calibration record, not because it still describes
current behavior -- under the current default, MEDIUM is reached by 40
of 117 rules, not 0. See docs/rules_engine/severity_v1_1_release_notes.md
for the current state and docs/rules_engine/severity_migration_report_full_117_v1_0_absolute_archive.md
for the absolute-mode snapshot this analysis describes.

0. HEADLINE FINDING -- MEDIUM is structurally unreachable via aggregation
   across the real ruleset. 93 of 117 rules (79%) changed tier; 86 of 117
   (74%) downgraded. Of the 94 rules scored via the WAS band path (no
   ceiling fired), the WAS values range from 0 to 12 -- EVERY ONE landed
   in the LOW band (<18). Not a single band-scored rule reached MEDIUM
   (18-35) or HIGH (36+) through aggregation alone anywhere in the actual
   117-rule set; every HIGH/CRITICAL result in this migration came from a
   named ceiling rule, never from the weighted sum. This is the single
   most important number in this migration and should be read before any
   individual row: it means the v1.0 threshold table (architecture doc
   §6.3, "18/36" as ~35%/70% of a ~52-point theoretical max) was
   calibrated against a hand-picked 40-clause stress test biased toward
   clauses deliberately chosen to be severe, not against the real
   distribution of how actual deployed rules score. Two live hypotheses,
   deliberately left both live rather than picked between (framework is
   frozen; this is exactly what architecture doc §12 Phase 3 exists to
   resolve with real attorney review, not a unilateral engineering call):
     (a) legacy severity is systematically over-escalated (plausible --
         it was assigned by analogy with no downward pressure, so
         "worth mentioning at all" tended to become "at least MEDIUM"),
         and the framework's much lower distribution is closer to correct; OR
     (b) the WAS thresholds (18 for MEDIUM, 36 for HIGH) are set too high
         relative to how real single/double-factor commercial clauses
         actually score under the weighted formula, and Tier C's weight-1
         contribution in particular is too small to ever move a
         REV/SC/OC/DUR-only fact out of LOW regardless of how many of
         those factors are present.
   Recommend this be the FIRST item reviewed in Phase 3, before any
   individual rule's disagreement -- if the threshold table needs
   adjustment, that is a single governed change (architecture doc §9)
   that would resolve dozens of the individual disagreements below at
   once, rather than reviewing 86 rows independently.

1. SYSTEMIC: the v1.0 CRITICAL tier is narrower than legacy's. Legacy's
   v5.0 pass elevated 5 rules to CRITICAL: H_ASYMMETRIC_LIABILITY_01,
   H_LOL_NO_CARVEOUT_01, H_PERSONAL_01, H_DATA_PRIVACY_01, H_AI_TRAINING_01.
   Under the frozen v1.0 ceiling rules, CRITICAL is reachable ONLY via
   PE==3, RW==3, CR==2, or FB==3-and-PE==2 (architecture doc §6.1's hard
   invariant). Of the 5: H_PERSONAL_01 still computes CRITICAL (PE==3).
   The other 4 -- H_ASYMMETRIC_LIABILITY_01, H_LOL_NO_CARVEOUT_01,
   H_DATA_PRIVACY_01, H_AI_TRAINING_01 -- all compute HIGH, not CRITICAL,
   because their underlying facts (uncapped-but-entity-level liability,
   overbroad cap carve-outs, regulatory/breadth exposure, irreversible
   data ingestion) don't touch personal liability, a forum-rights waiver,
   or criminal exposure. This is the single largest, most consistent
   disagreement pattern in the migration and merits explicit governance
   discussion: is legacy's broader CRITICAL concept (severe + irreversible,
   regardless of personal/rights/criminal facts) correct, and the frozen
   ceiling rules too narrow? Or is the frozen design's insistence that
   CRITICAL be reserved for personal/rights/criminal facts specifically
   correct, and legacy over-escalated these 4? Recorded as the top
   candidate for Phase 3 attorney review and/or a v2.0 ceiling-rule
   discussion -- NOT resolved here.

2. INCONSISTENCY FOUND IN LEGACY: H_LEASE_PERSONAL_GUARANTY_01 (legacy
   HIGH) and H_PERSONAL_01 / H_LOAN_GUARANTY_WAIVER_01 (legacy CRITICAL)
   detect the same underlying fact -- an unconditional personal guaranty
   with no cap qualifier -- but were scored two different legacy tiers.
   The v1.0 framework computes CRITICAL for all three uniformly via the
   PE==3 ceiling, which is applied without regard to practice area by
   design. This is exactly the kind of pre-existing legacy inconsistency
   the framework's uniform, rule-independent ceiling logic is supposed to
   surface -- a positive validation of the architecture, not a defect in
   it.

3. DOCUMENTATION INCONSISTENCY FOUND IN THE ARCHITECTURE DOC ITSELF:
   H_LEASE_RELOCATION_01 was cited in the architecture doc's Refinement
   Log #2/#4 narrative as an example that "correctly return[s] HIGH" after
   the UD factor and mutuality-gate fixes. That is inconsistent with the
   doc's own §2 factor rubric, which explicitly names "relocation within
   the same building" as the canonical UD=2 example -- and UD=2 can never
   reach the UD==3-gated ceiling. Scored here as UD=2 (LOW) per the
   literal, frozen rubric text, contradicting the Refinement Log's prose
   claim. Recorded as a documentation defect for correction alongside any
   future v1.x doc maintenance, not resolved by picking whichever answer
   matches the narrative.

4. RECURRING FACTOR-COVERAGE GAPS (rules that don't cleanly map onto any
   of the 11 factors, each scored conservatively and landing LOW as a
   result): H_INDEM_ONEWAY_01 (asymmetry of an obligation, distinct from
   its magnitude), H_PUBLICITY_01 (brand/reputational control),
   H_CONTENT_LICENSE_01 (loss of control over personal identity/likeness
   -- a license, not a title transfer, so AT=0 by definition),
   H_EMPLOY_ATWILL_WAIVER_01 (unintended contract formation),
   M_NONDISPARAGE_01 (speech restriction, not a forum/process right),
   M_INJUNCT_01 (expanded remedy access for the counterparty, not a
   waiver by the restrained party), H_SETTLEMENT_RELEASE_OVERBROAD_01 and
   several substantive-remedy-reduction rules (M_REFUND_01,
   M_WARRANTY_DISCLAIM_01, H_CONSEQUENTIAL_01, H_LOL_NO_CARVEOUT_01) where
   REV alone (weight x1) cannot carry a clause to HIGH and no other factor
   is cleanly implicated. None of these were patched by inflating a
   factor to "make the math work" -- each is flagged inline above with
   its specific reasoning. Worth a dedicated v2-candidates discussion on
   whether a "substantive remedy reduction" factor, distinct from RW's
   narrow forum-rights scope, belongs in a future version.

5. RUBRIC GRANULARITY GAP: M_TERM_NOTICE_01 revealed that OC's definition
   ("0: a specific notice period ... is stated") does not graduate for a
   notice period that is stated but very short (e.g. 5 days) -- it scores
   identically to a fully adequate notice period. A future version might
   want an intermediate OC level for "notice stated but below a
   commercially reasonable minimum," but that reintroduces exactly the
   kind of judgment-call ambiguity the framework was built to eliminate,
   so this is flagged as a genuine tension, not an obvious fix.

6. LIKELY DUPLICATE RULE PAIRS (flagged for the not-yet-implemented
   duplicate-detection validator, architecture doc §9.3):
   M_INSURANCE_01 / M_INSURANCE_MINIMUM_MISSING_01 (near-identical
   rationale and detection); H_DATA_TERMINATION_01 / M_DATA_DELETION_01
   (same underlying fact -- no data return/deletion on termination -- at
   different legacy severities and rule_class).

7. UPGRADE RECOMMENDATIONS (framework computes HIGHER than legacy, not
   just lower -- listed explicitly so the report isn't read as "the
   framework only downgrades"): M_LEASE_CAM_UNCAPPED_01 (MEDIUM->HIGH),
   M_LEASE_ESCALATION_UNCAPPED_01 (MEDIUM->HIGH),
   M_PARTNERSHIP_CAPITAL_CALL_01 (MEDIUM->HIGH),
   M_MA_EARNOUT_DISCRETION_01 (MEDIUM->HIGH), M_WAIVER_DEFENSE_01
   (MEDIUM->HIGH), M_ACCOUNT_SUSPEND_01 (MEDIUM->HIGH),
   H_LEASE_PERSONAL_GUARANTY_01 (HIGH->CRITICAL, see finding #2).

None of the above were "fixed" in this file -- the frozen rubric was
applied as written in every case, and the resulting disagreement was
recorded rather than smoothed over, per the explicit instruction not to
optimize for matching legacy severity.
"""
