"""Tests for docx_export.py's redlined-document generation."""

import io

import pytest
from docx import Document

from docx_export import build_redlined_docx


def _finding(rule_id, start, end, exact_snippet, redline_text=None):
    return {
        "rule_id": rule_id,
        "start_index": start,
        "end_index": end,
        "exact_snippet": exact_snippet,
        "redline": {"suggested_redline": redline_text} if redline_text else None,
    }


class TestBasicApplication:
    def test_accepted_redline_appears_in_document(self):
        text = "The Vendor shall have unlimited liability under this Agreement."
        findings = [_finding("H_LOL_01", 12, 32, "shall have unlimited", "shall cap aggregate")]
        decisions = {"H_LOL_01": {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == []
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "shall cap aggregate" in full_text
        assert "shall have unlimited" in full_text  # struck-through original still visible

    def test_original_text_is_struck_through(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {"R1": {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = Document(io.BytesIO(docx_bytes))
        struck_runs = [r for p in doc.paragraphs for r in p.runs if r.font.strike]
        assert any(r.text == "Original" for r in struck_runs)

    def test_inserted_text_is_underlined(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {"R1": {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = Document(io.BytesIO(docx_bytes))
        underlined_runs = [r for p in doc.paragraphs for r in p.runs if r.font.underline]
        assert any("Revised" in r.text for r in underlined_runs)


class TestEditedRedlines:
    def test_edited_text_used_instead_of_original_redline(self):
        text = "Some clause here that needs work."
        findings = [_finding("R1", 5, 11, "clause", "engine's suggestion")]
        decisions = {"R1": {"action": "edited", "edited_text": "attorney's custom wording"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "attorney's custom wording" in full_text
        assert "engine's suggestion" not in full_text

    def test_edited_redline_is_tagged(self):
        text = "Some clause here."
        findings = [_finding("R1", 5, 11, "clause")]
        decisions = {"R1": {"action": "edited", "edited_text": "new text"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "[edited by reviewer]" in full_text


class TestSkippedDecisions:
    def test_rejected_findings_are_not_applied(self):
        text = "The Vendor shall have unlimited liability."
        findings = [_finding("R1", 12, 32, "shall have unlimited", "shall cap liability")]
        decisions = {"R1": {"action": "rejected", "reason": "not applicable"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "shall cap liability" not in full_text
        assert "shall have unlimited" in full_text  # untouched, no strikethrough markers expected
        assert skipped == []  # rejected isn't "skipped", it's just never applicable

    def test_flagged_findings_with_no_redline_are_not_applied(self):
        text = "Some indemnification clause text."
        findings = [_finding("R1", 5, 22, "indemnification")]
        decisions = {"R1": {"action": "flagged"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        doc = Document(io.BytesIO(docx_bytes))
        assert "indemnification" in "\n".join(p.text for p in doc.paragraphs)

    def test_undecided_finding_is_untouched(self):
        text = "Text with a finding nobody decided on yet."
        findings = [_finding("R1", 5, 9, "with", "changed")]
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, {})
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "changed" not in full_text
        assert skipped == []

    def test_missing_position_data_is_skipped_not_crashed(self):
        findings = [{"rule_id": "R1", "start_index": None, "end_index": None, "exact_snippet": "x", "redline": {"suggested_redline": "y"}}]
        decisions = {"R1": {"action": "accepted"}}
        # must not raise
        docx_bytes, skipped = build_redlined_docx("test.docx", "some text", findings, decisions)
        assert docx_bytes


class TestOverlappingSpans:
    def test_overlapping_accepted_findings_the_second_is_skipped_not_corrupted(self):
        text = "0123456789ABCDEFGHIJ"
        findings = [
            _finding("R1", 0, 10, text[0:10], "FIRST-REPLACEMENT"),
            _finding("R2", 5, 15, text[5:15], "SECOND-REPLACEMENT"),  # overlaps R1's span
        ]
        decisions = {"R1": {"action": "accepted"}, "R2": {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == ["R2"]
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "FIRST-REPLACEMENT" in full_text
        assert "SECOND-REPLACEMENT" not in full_text

    def test_non_overlapping_findings_both_applied_in_order(self):
        text = "AAAA BBBB CCCC DDDD"
        findings = [
            _finding("R1", 0, 4, "AAAA", "first-new"),
            _finding("R2", 10, 14, "CCCC", "second-new"),
        ]
        decisions = {"R1": {"action": "accepted"}, "R2": {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == []
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "first-new" in full_text
        assert "second-new" in full_text
        assert full_text.index("first-new") < full_text.index("second-new")


class TestDocumentStructure:
    def test_header_note_present(self):
        docx_bytes, _ = build_redlined_docx("test.docx", "text", [], {})
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "not native Word Track Changes" in full_text or "Track Changes" in full_text

    def test_filename_in_title(self):
        docx_bytes, _ = build_redlined_docx("High.docx", "text", [], {})
        doc = Document(io.BytesIO(docx_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "High.docx" in full_text

    def test_paragraph_breaks_preserved(self):
        text = "First paragraph.\n\nSecond paragraph."
        docx_bytes, _ = build_redlined_docx("test.docx", text, [], {})
        doc = Document(io.BytesIO(docx_bytes))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        assert any("First paragraph." == t for t in texts)
        assert any("Second paragraph." == t for t in texts)

    def test_empty_document_does_not_crash(self):
        docx_bytes, skipped = build_redlined_docx("test.docx", "", [], {})
        assert docx_bytes
        assert skipped == []


class TestAgainstRealEngineOutput:
    def test_real_finding_positions_round_trip(self, rule_engine):
        text = "In no event shall liability be limited under this Agreement, without limit."
        result = rule_engine.analyze(text)
        findings = [
            {
                "rule_id": f.rule_id, "start_index": f.start_index, "end_index": f.end_index,
                "exact_snippet": f.exact_snippet, "redline": None,
            }
            for f in result["findings"]
        ]
        if not findings:
            pytest.skip("no findings on this fixture text")
        rid = findings[0]["rule_id"]
        decisions = {rid: {"action": "flagged"}}
        # should not crash even with real engine-derived positions and a no-redline decision
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert docx_bytes
