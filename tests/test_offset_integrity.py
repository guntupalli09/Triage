"""
Regression tests for evidence offset reliability.

The engine used to chunk text by collapsing whitespace before computing
match offsets, then reported those offsets as positions in the original
(un-collapsed) text. Whenever a chunk contained blank lines, repeated
spaces, or multi-line wrapping, start_index/end_index would drift from
the actual source text.

These tests assert the invariant that must always hold:
    text[finding.start_index:finding.end_index] == finding.exact_snippet
"""

import pytest
from rules_engine import RuleEngine, _chunk_text


@pytest.fixture
def engine():
    return RuleEngine()


def assert_offsets_match_source(text, findings):
    for f in findings:
        assert text[f.start_index:f.end_index] == f.exact_snippet, (
            f"Offset drift for {f.rule_id}: "
            f"text[{f.start_index}:{f.end_index}] = "
            f"{text[f.start_index:f.end_index]!r} != {f.exact_snippet!r}"
        )


class TestChunkTextPreservesOffsets:
    def test_chunks_are_verbatim_substrings(self):
        raw = "First section line one.\n  extra   spaces\n\nSecond section\n\twith a tab\n\n\nThird section"
        for start, chunk in _chunk_text(raw):
            assert raw[start:start + len(chunk)] == chunk

    def test_no_whitespace_collapsing(self):
        raw = "Alpha   beta\ngamma\n\nDelta"
        _, first_chunk = _chunk_text(raw)[0]
        # internal whitespace must be preserved verbatim, not collapsed to single spaces
        assert first_chunk == "Alpha   beta\ngamma"

    def test_fallback_no_blank_lines_still_verbatim(self):
        raw = "one two   three\nfour" * 50  # long, no blank lines -> fixed-size fallback
        for start, chunk in _chunk_text(raw):
            assert raw[start:start + len(chunk)] == chunk


class TestFindingOffsetsMatchOriginalDocument:
    def test_offsets_survive_blank_lines_and_repeated_whitespace(self, engine):
        text = (
            "1. Introduction\n\n\n"
            "This section is just padding   with   irregular   spacing.\n\n"
            "2. Indemnification\n\n"
            "The   Contractor    shall   indemnify   and   hold  harmless   the Client "
            "without   limit   for any and all claims arising hereunder.\n\n"
            "3. Miscellaneous\n\n"
            "Governing law is the State of Delaware."
        )
        result = engine.analyze(text)
        findings = result["findings"]
        assert len(findings) > 0
        assert_offsets_match_source(text, findings)

    def test_offsets_survive_crlf_line_endings(self, engine):
        text = (
            "Section A\r\n\r\n"
            "The parties agree to non-compete restrictions limiting competitor activity.\r\n\r\n"
            "Section B\r\n\r\n"
            "Attorneys' fees shall be borne solely by the losing party.\r\n"
        )
        result = engine.analyze(text)
        findings = result["findings"]
        assert len(findings) > 0
        # text is normalized (\r\n -> \n) once inside analyze(); re-derive it the same way
        # to validate offsets against what the engine actually indexed.
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        assert_offsets_match_source(normalized, findings)

    def test_offsets_survive_multiline_wrapped_clause(self, engine):
        text = (
            "Confidentiality\n\n"
            "Each party's confidentiality obligations hereunder\n"
            "shall survive termination of this Agreement\n"
            "in perpetuity and shall have no expiration date whatsoever.\n\n"
            "Termination\n\n"
            "Either party may terminate this Agreement for convenience at any time\n"
            "upon 30 days written notice at its sole discretion."
        )
        result = engine.analyze(text)
        findings = result["findings"]
        assert len(findings) > 0
        assert_offsets_match_source(text, findings)
