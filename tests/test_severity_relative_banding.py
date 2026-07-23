"""Tests for the v1.1 relative-banding mode
(severity_scoring.compute_severity(mode="relative")), adopted as the
DEFAULT per docs/rules_engine/severity_v1_1_release_notes.md. The v1.0
absolute mode is preserved exactly as a named compatibility mode
(mode="absolute") and must never silently disappear or drift -- these
tests guard both directions: that relative is really the default now,
and that absolute still reproduces v1.0 behavior exactly on request."""

import pytest

from rules_engine import Severity
from severity_scoring import (
    FactorVector,
    SeverityScoringError,
    compute_severity,
)


def zeros(**overrides):
    return FactorVector.from_levels(**overrides)


def test_default_mode_is_relative():
    d = compute_severity(zeros(REV=1))
    assert d.band_mode == "relative"


def test_absolute_mode_available_as_compatibility_mode():
    # Same vector, explicit mode="absolute" -- must reproduce the original
    # v1.0 arithmetic exactly (REV=1 alone: WAS=1, well under the fixed 18
    # threshold -> LOW), proving compatibility mode was preserved, not
    # merely left in place with drifted behavior.
    d = compute_severity(zeros(REV=1), mode="absolute")
    assert d.band_mode == "absolute"
    assert d.band == "LOW (<18)"
    assert d.tier == Severity.LOW


def test_invalid_mode_raises():
    with pytest.raises(SeverityScoringError, match="unknown mode"):
        compute_severity(zeros(REV=1), mode="banana")


def test_ceilings_are_identical_in_both_modes():
    # Ceiling rules must not depend on mode at all -- relative banding only
    # ever touches the non-ceiling (band) path.
    v = zeros(PE=3)
    d_abs = compute_severity(v, mode="absolute")
    d_rel = compute_severity(v, mode="relative")
    assert d_abs.tier == d_rel.tier == Severity.CRITICAL
    assert d_abs.method == d_rel.method == "ceiling"
    assert d_abs.ceiling_rule == d_rel.ceiling_rule == "PE == 3"


def test_relative_band_at_own_max_is_high():
    # A rule that only ever touches REV, scored at REV's own max (3),
    # is 100% of its own practical max -> HIGH under relative banding,
    # even though the absolute WAS (3) is far below the absolute
    # threshold (18) and would be LOW there.
    v = zeros(REV=3)
    d_rel = compute_severity(v, mode="relative")
    d_abs = compute_severity(v, mode="absolute")
    assert d_rel.tier == Severity.HIGH
    assert d_rel.band_mode == "relative"
    assert d_rel.practical_max == 3
    assert d_abs.tier == Severity.LOW


def test_relative_band_at_one_third_of_own_max_is_low():
    # REV=1 against REV's own max of 3 is exactly 33.3%, just under the
    # 35% MEDIUM cutoff -- this is the same boundary case documented in
    # severity_practical_max_experiment.md's "33.3% cluster" finding,
    # now directly visible in the relative-banding output.
    v = zeros(REV=1)
    d_rel = compute_severity(v, mode="relative")
    assert d_rel.tier == Severity.LOW
    assert d_rel.practical_max == 3
    assert d_rel.was == 1


def test_relative_band_at_two_thirds_of_own_max_is_medium():
    v = zeros(FB=2)  # FB max is 3, weight 2 -> WAS=4, practical_max=6, pct=66.7%
    d_rel = compute_severity(v, mode="relative")
    assert d_rel.tier == Severity.MEDIUM
    assert d_rel.practical_max == 6


def test_relative_band_zero_vector_is_low_not_divide_by_zero():
    v = zeros()
    d_rel = compute_severity(v, mode="relative")
    assert d_rel.tier == Severity.LOW
    assert d_rel.practical_max == 0
    assert "practical_max=0" in d_rel.band


def test_relative_mode_never_produces_critical_via_band():
    # The CRITICAL-only-via-ceiling invariant (architecture doc §6.1) must
    # hold identically in relative mode -- relative banding only changes
    # the MEDIUM/HIGH/LOW split among non-ceiling rules.
    from severity_scoring import Factor, FACTOR_MAX_LEVEL
    v = zeros(**{f.value: FACTOR_MAX_LEVEL[f] for f in Factor if f.value not in ("PE", "RW", "CR", "FB")})
    d = compute_severity(v, mode="relative")
    assert d.tier != Severity.CRITICAL
