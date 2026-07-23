"""Permanent regression suite for the v1.0 severity framework
(docs/rules_engine/severity_architecture.md §5, §9.6, §12).

This is the golden set: every clause below is a hand-scored example from
the architecture doc's 40-clause stress test, with its documented tier
verified here so that no future change to severity_scoring.py (whether an
intentional v1.1 refinement or an accidental regression) can silently alter
what these clauses score without a visible, reviewed test failure.

Per architecture doc §7 (Task 7): 40 clauses is the *seed* corpus, not the
target size. As rules are migrated (Phase 2/3, §12) and new rules are
authored (§10), every rule's blind-re-scored, attorney-reviewed factor
vector should be added here too -- recommended target size is 150-200
entries once the full 117-rule (soon 500+) migration completes, enough to
give the monotonicity validator (severity_scoring.validate_monotonicity)
real cross-rule coverage within every clause_category. Growing this corpus
is real legal-review work (§10's blind re-score gate applies to every
addition) and is not something to backfill by guessing -- this file's
CORPUS list is intentionally the exact 40 from the architecture doc, no
more, so nothing here is asserted without a documented justification.

Do NOT add entries to CORPUS without also adding the corresponding row (or
a documented correction to an existing row, as with #29 -- see the
architecture doc's erratum note) to severity_architecture.md §5. The doc
and this file must never drift apart; that drift is exactly what row #29
demonstrated happening once, on the very first implementation pass.
"""

from dataclasses import dataclass
from typing import Dict

import pytest

from rules_engine import Severity
from severity_scoring import FactorVector, compute_severity


@dataclass(frozen=True)
class CorpusEntry:
    id: int
    agreement_type: str
    clause: str
    levels: Dict[str, int]
    expected_tier: Severity
    expected_method: str  # "ceiling" | "band"
    expected_ceiling_rule: str = None


CORPUS = [
    CorpusEntry(1, "NDA", "Perpetual confidentiality, mutual, standard exceptions",
                dict(DUR=2), Severity.LOW, "band"),
    CorpusEntry(2, "NDA", "Confidential-info definition lacks public/independent-development carve-out",
                dict(REV=1), Severity.LOW, "band"),
    CorpusEntry(3, "SaaS", "Vendor liability 'shall not be limited'",
                dict(FB=3, REV=1), Severity.HIGH, "ceiling", "FB == 3"),
    CorpusEntry(4, "SaaS", "Liability capped at 12mo fees, standard carve-outs",
                dict(REV=1), Severity.LOW, "band"),
    CorpusEntry(5, "MSA", "Vendor-only termination for convenience, 30-day notice",
                dict(UD=3, REV=1), Severity.LOW, "band"),
    CorpusEntry(6, "MSA", "Vendor-only termination for convenience, immediate, sole discretion",
                dict(UD=3, REV=1, OC=2), Severity.HIGH, "ceiling", "UD == 3 and (OC == 2 or FB >= 2)"),
    CorpusEntry(7, "MSA", "Mutual termination for convenience, 30-day notice",
                dict(REV=1), Severity.LOW, "band"),
    CorpusEntry(8, "Loan", "Unlimited personal guaranty, 'any and all obligations'",
                dict(PE=3, REV=1), Severity.CRITICAL, "ceiling", "PE == 3"),
    CorpusEntry(9, "Loan", "Limited personal guaranty, capped at $50,000",
                dict(PE=1, REV=1), Severity.LOW, "band"),
    CorpusEntry(10, "Loan", "Confession of judgment / cognovit",
                dict(RW=3, REV=3), Severity.CRITICAL, "ceiling", "RW == 3"),
    CorpusEntry(11, "Loan", "Mandatory arbitration, neutral administrator, no other waivers",
                dict(RW=2, REV=1), Severity.LOW, "band"),
    CorpusEntry(12, "Loan", "Jury-trial waiver only",
                dict(RW=1, REV=1), Severity.LOW, "band"),
    CorpusEntry(13, "Loan", "Arbitration + jury waiver + class-action waiver, stacked",
                dict(RW=3, REV=2, SC=2), Severity.CRITICAL, "ceiling", "RW == 3"),
    CorpusEntry(14, "Employment", "Broad invention assignment, no own-time carve-out",
                dict(AT=3, REV=3), Severity.HIGH, "ceiling", "AT == 3 and REV == 3"),
    CorpusEntry(15, "Employment", "Invention assignment with explicit own-time carve-out",
                dict(AT=1, REV=1), Severity.LOW, "band"),
    CorpusEntry(16, "Employment", "Standard mutual at-will disclaimer",
                dict(), Severity.LOW, "band"),
    CorpusEntry(17, "Employment", "Non-compete, 2-year radius, no stated consideration",
                dict(RS=1, REV=1, DUR=1), Severity.LOW, "band"),
    CorpusEntry(18, "Employment", "Severance release, broad, no EEOC/whistleblower carve-out",
                dict(RW=2, RS=1, REV=2), Severity.LOW, "band"),
    CorpusEntry(19, "Lease", "Personal guaranty of all lease obligations, uncapped, full term",
                dict(PE=3, REV=1), Severity.CRITICAL, "ceiling", "PE == 3"),
    CorpusEntry(20, "Lease", "CAM charges, landlord sole discretion, no cap anywhere",
                dict(FB=3, UD=2, REV=1), Severity.HIGH, "ceiling", "FB == 3"),
    CorpusEntry(21, "Lease", "Rent escalation capped at 3%/year",
                dict(), Severity.LOW, "band"),
    CorpusEntry(22, "Construction", "Pay-if-paid",
                dict(FB=3, REV=2), Severity.HIGH, "ceiling", "FB == 3"),
    CorpusEntry(23, "Construction", "Lien waiver required before payment received",
                dict(RW=1, FB=2, REV=2), Severity.LOW, "band"),
    CorpusEntry(24, "Construction", "Retainage withheld, no release trigger",
                dict(FB=2, REV=1, DUR=2), Severity.LOW, "band"),
    CorpusEntry(25, "Procurement", "MFN clause",
                dict(), Severity.LOW, "band"),
    CorpusEntry(26, "Procurement", "Unlimited customer audit rights, no notice",
                dict(UD=2, REV=1, OC=2), Severity.LOW, "band"),
    CorpusEntry(27, "Partnership", "Capital call default -> uncapped dilution penalty",
                dict(AT=3, UD=3, REV=3), Severity.HIGH, "ceiling", "AT == 3 and REV == 3"),
    CorpusEntry(28, "Partnership", "50/50 ownership, no deadlock mechanism",
                dict(REV=1, DUR=2), Severity.LOW, "band"),
    CorpusEntry(29, "M&A", "Earnout metrics nominally formula-based, final calculation left to buyer's own auditors",
                dict(FB=2, UD=3, REV=2), Severity.HIGH, "ceiling", "UD == 3 and (OC == 2 or FB >= 2)"),
    CorpusEntry(30, "AI", "Model training on customer data, no opt-out, 'all data'",
                dict(RS=3, AT=3, UD=2, REV=3, SC=3), Severity.HIGH, "ceiling", "AT == 3 and REV == 3"),
    CorpusEntry(31, "Privacy", "Unlimited data retention, no deletion right, regime not named",
                dict(RS=2, REV=2, SC=2, DUR=2), Severity.LOW, "band"),
    CorpusEntry(32, "Privacy", "Same, but clause explicitly names GDPR",
                dict(RS=3, REV=2, SC=2, DUR=2), Severity.LOW, "band"),
    CorpusEntry(33, "Healthcare", "PHI handling, no BAA execution requirement",
                dict(RS=3, REV=2, SC=2), Severity.LOW, "band"),
    CorpusEntry(34, "Government", "FCA certification required, clause itself is routine/ambiguous drafting",
                dict(CR=1, RS=3, REV=2), Severity.LOW, "band"),
    CorpusEntry(35, "Government", "Mandatory flow-down clauses omitted (absence-type)",
                dict(RS=2, REV=1), Severity.LOW, "band"),
    CorpusEntry(36, "Consumer", "Auto-renewal, 60-day notice, clearly disclosed",
                dict(), Severity.LOW, "band"),
    CorpusEntry(37, "Consumer", "Auto-renewal, cancel only via certified mail in a 5-day annual window",
                dict(UD=2, REV=1, DUR=1), Severity.LOW, "band"),
    CorpusEntry(38, "Boilerplate", "Governing law / exclusive jurisdiction",
                dict(), Severity.LOW, "band"),
    CorpusEntry(39, "Boilerplate", "Counterparts / e-signature",
                dict(), Severity.LOW, "band"),
    CorpusEntry(40, "MSA", "Assignment restricted on change of control, no M&A carve-out",
                dict(UD=2, REV=1), Severity.LOW, "band"),

    # Entries 41-42 added during implementation, not part of the architecture
    # doc's original 40-clause hand-scored set: the first implementation pass
    # found that none of the 40 exercised ceiling rules "CR == 2" or
    # "FB == 3 and PE == 2", leaving two of the eight ceiling rules with zero
    # regression coverage. Per architecture doc §14 ("growing this corpus"),
    # closing a coverage gap in the golden set is corpus growth, not a
    # framework change -- these do not alter §2's factor definitions, §6's
    # ceiling rules, or §6.3's thresholds, they only add test evidence.
    CorpusEntry(41, "Government", "Contract requires backdating invoices to obtain payment (direct exposure to fraud/false-claims statutes)",
                dict(CR=2, RS=3, REV=2), Severity.CRITICAL, "ceiling", "CR == 2"),
    CorpusEntry(42, "Lease", "Tenant entity's total liability is unlimited; principal separately guarantees Base Rent only, capped to that amount",
                dict(PE=2, FB=3, REV=1), Severity.CRITICAL, "ceiling", "FB == 3 and PE == 2"),
    # #43 closes a second coverage gap the first pass at #41/#42 missed on its
    # own first run: row #30 (AI training) has RS=3 and SC=3, but its AT=3/
    # REV=3 combination fires ceiling rule 6 first (rules are checked in
    # order, first match wins -- architecture doc §6.1), so "RS == 3 and
    # SC == 3" (rule 7) was still never the *recorded* ceiling anywhere in
    # the corpus. This entry has RS=3/SC=3 with AT and REV deliberately kept
    # below 3 so rule 7 is the one that actually fires.
    CorpusEntry(43, "Privacy", "Broad third-party data sharing ('any partner'), GDPR Data Controller obligations named, no DPA required",
                dict(RS=3, SC=3, REV=1), Severity.HIGH, "ceiling", "RS == 3 and SC == 3"),
]

assert len(CORPUS) == 43, "corpus size drifted -- update this assertion and the architecture doc together"
assert len({e.id for e in CORPUS}) == len(CORPUS), "duplicate corpus id"


def _vector(levels: Dict[str, int]) -> FactorVector:
    return FactorVector.from_levels(**{k: v for k, v in levels.items()})


@pytest.mark.parametrize("entry", CORPUS, ids=lambda e: f"{e.id:02d}_{e.agreement_type}")
def test_corpus_entry_matches_documented_severity(entry: CorpusEntry):
    # This corpus's expected_tier values are the v1.0 absolute-threshold
    # tiers documented in architecture doc §5 -- pinned explicitly since
    # v1.1 changed compute_severity's default mode to "relative". See
    # test_corpus_relative_mode_is_deterministic below for the same 43
    # vectors under the v1.1 default.
    derivation = compute_severity(_vector(entry.levels), mode="absolute")
    assert derivation.tier == entry.expected_tier, (
        f"#{entry.id} ({entry.agreement_type}: {entry.clause}) expected "
        f"{entry.expected_tier.value}, got {derivation.tier.value} (WAS={derivation.was})"
    )
    assert derivation.method == entry.expected_method
    if entry.expected_ceiling_rule:
        assert derivation.ceiling_rule == entry.expected_ceiling_rule


def test_corpus_covers_every_agreement_type_named_in_the_architecture_doc():
    required = {
        "NDA", "SaaS", "MSA", "Employment", "Loan", "Lease", "Construction",
        "Procurement", "Partnership", "M&A", "AI", "Privacy", "Healthcare",
        "Government",
    }
    present = {e.agreement_type for e in CORPUS}
    missing = required - present
    assert not missing, f"corpus is missing coverage for: {missing}"


def test_corpus_covers_every_severity_tier():
    tiers_present = {e.expected_tier for e in CORPUS}
    assert tiers_present == {Severity.CRITICAL, Severity.HIGH, Severity.LOW}, (
        "corpus should exercise every reachable tier at least once; MEDIUM is "
        "legitimately absent from the hand-picked 40 (several boundary cases "
        "landed just under 18) -- see architecture doc §5.1's boundary-case "
        "discussion, and treat adding an explicit MEDIUM example as a Task-7 "
        "corpus-growth item, not a bug in this test."
    )


def test_corpus_exercises_every_ceiling_rule_at_least_once():
    """Each of the 8 ceiling rules in severity_scoring._ceiling_rules() should
    fire on at least one corpus entry -- an untested ceiling rule is exactly
    the kind of gap architecture doc §9.6 (golden-set regression) exists to
    prevent."""
    fired_rules = set()
    for entry in CORPUS:
        d = compute_severity(_vector(entry.levels), mode="absolute")
        if d.method == "ceiling":
            fired_rules.add(d.ceiling_rule)
    expected = {
        "CR == 2",
        "PE == 3",
        "RW == 3",
        "FB == 3 and PE == 2",
        "FB == 3",
        "AT == 3 and REV == 3",
        "RS == 3 and SC == 3",
        "UD == 3 and (OC == 2 or FB >= 2)",
    }
    missing = expected - fired_rules
    assert not missing, f"ceiling rule(s) never exercised by the corpus: {missing}"


# Expected tier under the v1.1 DEFAULT (relative) mode for every corpus
# entry -- computed once when v1.1 was adopted and hardcoded here so this
# corpus is a genuine regression guard for the current default, not just
# the "absolute" compatibility mode tested above. Ceiling-fired entries
# are identical to expected_tier (ceilings are mode-independent) and are
# not re-listed; ids not present here are exactly the ceiling-fired ones.
EXPECTED_RELATIVE_TIER = {
    1: Severity.HIGH, 2: Severity.LOW, 4: Severity.LOW, 5: Severity.HIGH,
    7: Severity.LOW, 9: Severity.LOW, 11: Severity.MEDIUM, 12: Severity.LOW,
    15: Severity.LOW, 16: Severity.LOW, 17: Severity.MEDIUM, 18: Severity.MEDIUM,
    21: Severity.LOW, 23: Severity.MEDIUM, 24: Severity.MEDIUM, 25: Severity.LOW,
    26: Severity.MEDIUM, 28: Severity.MEDIUM, 31: Severity.HIGH, 32: Severity.HIGH,
    33: Severity.HIGH, 34: Severity.HIGH, 35: Severity.MEDIUM, 36: Severity.LOW,
    37: Severity.MEDIUM, 38: Severity.LOW, 39: Severity.LOW, 40: Severity.MEDIUM,
}


@pytest.mark.parametrize("entry", [e for e in CORPUS if e.id in EXPECTED_RELATIVE_TIER],
                          ids=lambda e: f"{e.id:02d}_{e.agreement_type}")
def test_corpus_relative_mode_matches_recorded_v1_1_tier(entry: CorpusEntry):
    """Locks in the v1.1 default (relative) mode's output for every
    non-ceiling corpus entry, the same golden-set discipline
    test_corpus_entry_matches_documented_severity applies to absolute
    mode. A change here means either an intentional, governed threshold
    adjustment (update EXPECTED_RELATIVE_TIER deliberately, per
    architecture doc §13) or an unintended regression -- never a change
    to accept silently."""
    derivation = compute_severity(_vector(entry.levels), mode="relative")
    assert derivation.method == "band", f"#{entry.id} unexpectedly ceiling-fired under relative mode"
    assert derivation.tier == EXPECTED_RELATIVE_TIER[entry.id], (
        f"#{entry.id} ({entry.agreement_type}: {entry.clause}) expected "
        f"{EXPECTED_RELATIVE_TIER[entry.id].value} under v1.1 relative mode, "
        f"got {derivation.tier.value} (WAS={derivation.was}, pmax={derivation.practical_max})"
    )


def test_ceiling_fired_entries_are_identical_across_both_modes():
    """Ceiling rules must never depend on band mode -- every corpus entry
    NOT in EXPECTED_RELATIVE_TIER above is exactly the ceiling-fired set,
    and both modes must agree on tier for every one of them."""
    ceiling_ids = {e.id for e in CORPUS} - set(EXPECTED_RELATIVE_TIER)
    for entry in CORPUS:
        if entry.id not in ceiling_ids:
            continue
        d_abs = compute_severity(_vector(entry.levels), mode="absolute")
        d_rel = compute_severity(_vector(entry.levels), mode="relative")
        assert d_abs.method == d_rel.method == "ceiling", f"#{entry.id} expected to be ceiling-fired in both modes"
        assert d_abs.tier == d_rel.tier == entry.expected_tier
