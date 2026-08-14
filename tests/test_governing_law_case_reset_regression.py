"""
Regression tests for the governing_law_policy_engine jurisdiction/venue
case-sensitivity bug (Stage A.2 of the pre-#11 hardening pass).

_JURISDICTION_RE and _VENUE_RE both compile with re.I (needed for the
surrounding "governed by"/"the State of"/"venue shall be" phrasing to
match regardless of case) but, before this fix, their captured
jurisdiction/venue name used a bare [A-Z] with no (?-i:...) case-reset --
so re.IGNORECASE silently let [A-Z] match lowercase letters too, defeating
the "must look like a capitalized proper-noun jurisdiction name" gate the
pattern relies on. Every other adapter's party-name capture in this
codebase already carries this reset; this file's jurisdiction/venue
capture had not.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import governing_law_policy_engine as g


def test_capitalized_jurisdiction_still_matches():
    text = "This Agreement shall be governed by the laws of the State of New York, without regard to conflicts of law principles."
    m = g._JURISDICTION_RE.search(text)
    assert m is not None
    assert m.group(1) == "New York"


def test_lowercase_jurisdiction_in_ordinary_prose_is_not_accepted_solely_by_case_insensitive_matching():
    text = "This Agreement shall be governed by the laws of the state of new york, without regard to conflicts of law principles."
    m = g._JURISDICTION_RE.search(text)
    assert m is None, (
        f"lowercase 'new york' should not be captured as a jurisdiction name via the "
        f"case-insensitive compile flag alone; got {m.group(1)!r}" if m else ""
    )


def test_lowercase_jurisdiction_clause_is_found_but_jurisdiction_unresolved():
    """The anchor still matches (clause is present), but with no reliably
    capitalized jurisdiction name, jurisdiction extraction correctly comes
    back None rather than confidently capturing the lowercase text --
    this is what routes the adapter to REQUIRES_REVIEW instead of
    silently accepting a low-confidence extraction."""
    text = "This Agreement shall be governed by the laws of the state of new york, without regard to conflicts of law principles."
    facts = g.extract_governing_law_facts(text)
    assert facts.clause_found is True
    assert facts.jurisdiction is None


def test_capitalized_venue_still_matches():
    text = "The parties submit to the exclusive jurisdiction of the state and federal courts located in Delaware, without further recourse."
    m = g._VENUE_RE.search(text)
    assert m is not None
    assert m.group(1) == "Delaware"


def test_lowercase_venue_in_ordinary_prose_is_not_accepted_solely_by_case_insensitive_matching():
    text = "the parties submit to the exclusive jurisdiction of the courts located in delaware, without further recourse."
    m = g._VENUE_RE.search(text)
    assert m is None, (
        f"lowercase 'delaware' should not be captured as a venue via the case-insensitive "
        f"compile flag alone; got {m.group(1)!r}" if m else ""
    )


def test_other_supported_jurisdictions_still_resolve_correctly():
    """A representative sample of jurisdictions already covered by the
    existing benchmark corpus, confirming the fix did not narrow
    legitimate capitalized matches."""
    cases = [
        ("This Agreement shall be governed by the laws of the State of California, without regard to conflicts of law principles.", "California"),
        ("This Agreement shall be governed by the laws of the Commonwealth of Massachusetts, without regard to conflicts of law principles.", "Massachusetts"),
        ("This Agreement shall be governed by the laws of Delaware, without regard to conflicts of law principles.", "Delaware"),
        ("This Agreement shall be governed by the laws of the State of Texas, without regard to conflicts of law principles.", "Texas"),
    ]
    for text, expected in cases:
        m = g._JURISDICTION_RE.search(text)
        assert m is not None, f"expected a match for: {text!r}"
        assert m.group(1) == expected, f"expected {expected!r}, got {m.group(1)!r} for: {text!r}"


def test_governing_law_benchmark_corpus_golden_outputs_unchanged():
    """The fix must not change any existing benchmark case's expected
    outcome -- the corpus never relied on the buggy case-insensitive
    behavior in the first place."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from benchmarks.run_governing_law_benchmark import run, summarize
    data = run()
    summary = summarize(data)
    assert summary["false_safe_count"] == 0
    assert summary["false_escalation_count"] == 0
    mismatches = [r for r in data["rows"] if not r["state_correct"]]
    assert mismatches == [], f"golden-output drift on: {[r['id'] for r in mismatches]}"
