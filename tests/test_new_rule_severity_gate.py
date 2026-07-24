"""The gate that answers "will a new rule be properly assigned severity":
tests/test_new_rule_severity_gate.py::test_live_ruleset_has_no_unscored_or_mismatched_new_rules
is what actually enforces it. Add a rule to rules_engine.py without a
matching, consistent entry in severity_factor_data.py, and this test
fails the build with a message telling you exactly what's missing or
wrong -- that is the whole mechanism; there is no automatic severity
assignment beyond it, because scoring a clause's 11 factors is real
analytical work a human has to do and justify in text, the same way the
existing 117 rules were scored.

The other tests here don't test the current ruleset (which trivially
passes today, since every current rule is in the legacy-exempt set) --
they test the GATE LOGIC ITSELF against synthetic data, proving it
actually catches the failure modes it claims to catch.
"""

from dataclasses import dataclass

from rules_engine import RuleEngine, Severity
from severity_factor_data import (
    FACTOR_VECTORS_BY_RULE_ID,
    KNOWN_LEGACY_RULE_IDS,
    find_new_rule_severity_problems,
)
from severity_scoring import FactorVector, compute_severity


@dataclass
class _FakeRule:
    """Minimal duck-typed stand-in for rules_engine.Rule -- only rule_id
    and severity matter to the gate, confirmed by test_gate_is_duck_typed
    below."""
    rule_id: str
    severity: Severity


def test_gate_is_duck_typed_not_dependent_on_real_rule_class():
    fake = _FakeRule(rule_id="H_INDEM_01", severity=Severity.HIGH)  # a legacy id -> exempt regardless of severity value
    assert find_new_rule_severity_problems([fake]) == []


def test_new_rule_with_no_factor_vector_is_flagged():
    fake = _FakeRule(rule_id="X_BRAND_NEW_RULE_01", severity=Severity.HIGH)
    problems = find_new_rule_severity_problems([fake], factor_vectors={})
    assert len(problems) == 1
    assert "no factor vector" in problems[0]
    assert "X_BRAND_NEW_RULE_01" in problems[0]


def test_new_rule_with_matching_severity_passes():
    vector = FactorVector.from_levels(PE=3)  # -> CRITICAL via ceiling, deterministic
    fake = _FakeRule(rule_id="X_BRAND_NEW_RULE_01", severity=Severity.CRITICAL)
    problems = find_new_rule_severity_problems(
        [fake], factor_vectors={"X_BRAND_NEW_RULE_01": vector}
    )
    assert problems == []


def test_new_rule_with_mismatched_severity_is_flagged_with_the_correct_answer():
    vector = FactorVector.from_levels(PE=3)  # computes CRITICAL
    fake = _FakeRule(rule_id="X_BRAND_NEW_RULE_01", severity=Severity.LOW)  # wrong, hand-typed guess
    problems = find_new_rule_severity_problems(
        [fake], factor_vectors={"X_BRAND_NEW_RULE_01": vector}
    )
    assert len(problems) == 1
    assert "severity='low'" in problems[0]
    assert "computed severity='critical'" in problems[0]
    assert "Severity.CRITICAL" in problems[0]  # tells the contributor exactly what to write


def test_legacy_rules_are_exempt_even_with_a_wrong_severity():
    # This is deliberate, not a loophole: 67/117 legacy rules currently
    # disagree with the framework (see severity_migration_report_full_117.md);
    # fixing that is the separate, explicit Phase 5 cutover decision, not
    # something this gate should force by breaking the build today.
    fake = _FakeRule(rule_id="H_ASYMMETRIC_LIABILITY_01", severity=Severity.LOW)  # deliberately wrong
    assert find_new_rule_severity_problems([fake]) == []


def test_multiple_new_rule_problems_are_all_reported_not_just_the_first():
    fakes = [
        _FakeRule(rule_id="X_NEW_A", severity=Severity.HIGH),
        _FakeRule(rule_id="X_NEW_B", severity=Severity.LOW),
    ]
    vectors = {"X_NEW_B": FactorVector.from_levels(RW=3)}  # computes CRITICAL, not LOW
    problems = find_new_rule_severity_problems(fakes, factor_vectors=vectors)
    assert len(problems) == 2
    assert any("X_NEW_A" in p and "no factor vector" in p for p in problems)
    assert any("X_NEW_B" in p and "computed severity='critical'" in p for p in problems)


def test_known_legacy_rule_ids_is_frozen_at_117():
    # A safety net on the exemption list itself -- if this ever changes it
    # should be a deliberate, reviewed edit (e.g. Phase 5 cutover shrinking
    # it), never an accidental side effect of some other change.
    assert len(KNOWN_LEGACY_RULE_IDS) == 117


def test_gate_uses_the_v1_1_default_relative_mode():
    # The gate must compute against the SAME default a real caller of
    # compute_severity() gets -- verified by not passing mode= explicitly
    # inside find_new_rule_severity_problems and cross-checking here that
    # the module-level default really is "relative" (a regression guard
    # against find_new_rule_severity_problems silently drifting to
    # mode="absolute" some day without anyone noticing).
    vector = FactorVector.from_levels(UD=3, FB=2)  # relative: HIGH; absolute: LOW (WAS=8 < 18)
    assert compute_severity(vector).tier == Severity.HIGH  # default mode
    fake = _FakeRule(rule_id="X_NEW_RELATIVE_CHECK", severity=Severity.HIGH)
    problems = find_new_rule_severity_problems([fake], factor_vectors={"X_NEW_RELATIVE_CHECK": vector})
    assert problems == []


# --- The actual production gate ---

def test_live_ruleset_has_no_unscored_or_mismatched_new_rules():
    """THE enforcement test. Passes today because every one of the 117
    live rules is in KNOWN_LEGACY_RULE_IDS. The moment a rule_id is added
    to rules_engine.py that ISN'T in that frozenset, this test starts
    checking it for real: it must have a factor vector in
    severity_factor_data.py, and that vector's computed severity
    (mode="relative") must match what's hand-set on the Rule."""
    live_rules = RuleEngine().rules
    problems = find_new_rule_severity_problems(live_rules)
    assert problems == [], "\n" + "\n".join(problems)


def test_every_legacy_rule_id_still_exists_in_the_live_engine():
    # Catches the inverse mistake: silently deleting or renaming a rule_id
    # without updating KNOWN_LEGACY_RULE_IDS (which would make the gate
    # blind to it rather than erroring loudly).
    live_ids = {r.rule_id for r in RuleEngine().rules}
    missing = KNOWN_LEGACY_RULE_IDS - live_ids
    assert not missing, f"legacy rule_id(s) no longer exist in rules_engine.py: {missing}"
