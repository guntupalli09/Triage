"""Tests for docx_export.py's redlined-document generation.

python-docx's paragraph.text/paragraph.runs deliberately don't see inside
w:ins/w:del wrappers (it wasn't built with revision tracking in mind), so
these tests read the raw OOXML directly via lxml/docx's own element tree —
the same thing a real consumer (Word, or any other OOXML-aware tool) reads.

Decisions are keyed by finding_key ("{rule_id}#{index in the findings
list}"), not bare rule_id — see review_workflow.py's module docstring for
why: the same rule can fire more than once in one real document.
"""

import io
import zipfile

import pytest
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from docx_export import build_redlined_docx
from review_workflow import finding_key as fk


def _finding(rule_id, start, end, exact_snippet, redline_text=None, title=None, rationale="why it matters"):
    return {
        "rule_id": rule_id,
        "title": title or rule_id,
        "rationale": rationale,
        "start_index": start,
        "end_index": end,
        "exact_snippet": exact_snippet,
        "redline": {"suggested_redline": redline_text, "issue": rule_id, "legal_rationale": rationale} if redline_text else None,
    }


def _open(docx_bytes):
    return Document(io.BytesIO(docx_bytes))


def _all_text(doc, tag):
    """Concatenates the text of every element with this qualified tag
    (e.g. 'w:t' or 'w:delText') anywhere in the document body."""
    out = []
    for p in doc.paragraphs:
        for el in p._p.iter(qn(tag)):
            out.append(el.text or "")
    return "".join(out)


def _elements(doc, tag):
    out = []
    for p in doc.paragraphs:
        out.extend(p._p.iter(qn(tag)))
    return out


def _part_xml(docx_bytes, part_name):
    zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
    return zf.read(part_name).decode("utf-8")


def _part_exists(docx_bytes, part_name):
    zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
    return part_name in zf.namelist()


class TestTrackedInsertDelete:
    def test_accepted_redline_is_a_real_ins_and_del(self):
        text = "The Vendor shall have unlimited liability under this Agreement."
        findings = [_finding("H_LOL_01", 11, 32, "shall have unlimited", "shall cap aggregate")]
        decisions = {fk(0, "H_LOL_01"): {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions, author="Jane Attorney")
        assert skipped == []
        doc = _open(docx_bytes)
        assert "shall cap aggregate" in _all_text(doc, "w:t")
        assert "shall have unlimited" in _all_text(doc, "w:delText")
        # and NOT as plain visible w:t (it must be a real deletion, not just struck-through display text)
        assert "shall have unlimited" not in _all_text(doc, "w:t")

    def test_ins_and_del_elements_present(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)
        assert len(_elements(doc, "w:ins")) >= 1
        assert len(_elements(doc, "w:del")) >= 1

    def test_track_changes_author_is_the_reviewing_attorney(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions, author="Jane Attorney")
        doc = _open(docx_bytes)
        ins_els = _elements(doc, "w:ins")
        del_els = _elements(doc, "w:del")
        assert all(el.get(qn("w:author")) == "Jane Attorney" for el in ins_els)
        assert all(el.get(qn("w:author")) == "Jane Attorney" for el in del_els)

    def test_falls_back_to_a_generic_author_if_none_given(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)
        assert _elements(doc, "w:ins")[0].get(qn("w:author"))

    def test_ins_del_ids_are_unique(self):
        text = "AAAA BBBB CCCC DDDD"
        findings = [_finding("R1", 0, 4, "AAAA", "first-new"), _finding("R2", 10, 14, "CCCC", "second-new")]
        decisions = {fk(0, "R1"): {"action": "accepted"}, fk(1, "R2"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)
        ids = [el.get(qn("w:id")) for el in _elements(doc, "w:ins") + _elements(doc, "w:del")]
        assert len(ids) == len(set(ids)), "revision ids must be unique or Word can't tell them apart"


class TestDuplicateRuleId:
    """The same rule can fire more than once in one real document — deciding
    on one occurrence must never affect another occurrence of the same
    rule_id. This is a real bug found live against a real contract, not a
    hypothetical."""

    def test_accepting_one_occurrence_does_not_apply_to_another(self):
        text = "AAAA BBBB CCCC DDDD"
        findings = [
            _finding("H_ATTFEE_01", 0, 4, "AAAA", "first-redline"),
            _finding("H_ATTFEE_01", 10, 14, "CCCC", "second-redline"),
        ]
        # only accept the FIRST occurrence
        decisions = {fk(0, "H_ATTFEE_01"): {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == []
        doc = _open(docx_bytes)
        assert "first-redline" in _all_text(doc, "w:t")
        assert "second-redline" not in _all_text(doc, "w:t")
        # the second occurrence's original text must be untouched, not deleted
        assert "CCCC" in _all_text(doc, "w:t")
        assert "CCCC" not in _all_text(doc, "w:delText")

    def test_rejecting_one_occurrence_does_not_reject_another(self):
        text = "AAAA BBBB CCCC DDDD"
        findings = [
            _finding("H_ATTFEE_01", 0, 4, "AAAA", "first-redline"),
            _finding("H_ATTFEE_01", 10, 14, "CCCC", "second-redline"),
        ]
        decisions = {
            fk(0, "H_ATTFEE_01"): {"action": "accepted"},
            fk(1, "H_ATTFEE_01"): {"action": "rejected", "reason": "already mutual"},
        }
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == []
        doc = _open(docx_bytes)
        assert "first-redline" in _all_text(doc, "w:t")  # accepted one applied
        assert "second-redline" not in _all_text(doc, "w:t")  # rejected one NOT applied
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert comments_xml.count("<w:comment ") == 2  # one rationale comment + one reject-note comment
        assert "already mutual" in comments_xml


class TestEditedRedlines:
    def test_edited_text_used_instead_of_original_redline(self):
        text = "Some clause here that needs work."
        findings = [_finding("R1", 5, 11, "clause", "engine's suggestion")]
        decisions = {fk(0, "R1"): {"action": "edited", "edited_text": "attorney's custom wording"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)
        assert "attorney's custom wording" in _all_text(doc, "w:t")
        assert "engine's suggestion" not in _all_text(doc, "w:t")

    def test_edit_is_noted_in_the_comment_not_the_document_body(self):
        text = "Some clause here."
        findings = [_finding("R1", 5, 11, "clause", "engine text", rationale="original rationale")]
        decisions = {fk(0, "R1"): {"action": "edited", "edited_text": "new text"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        # the body should read like a normal human edit — no visible "[edited]" tag
        assert "[edited by reviewer]" not in _all_text(_open(docx_bytes), "w:t")
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert "edited by the reviewer" in comments_xml


class TestComments:
    def test_comment_part_exists_when_there_are_accepted_redlines(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised", rationale="uncapped exposure")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        assert _part_exists(docx_bytes, "word/comments.xml")

    def test_comment_part_absent_when_nothing_applied(self):
        docx_bytes, _ = build_redlined_docx("test.docx", "plain text, no findings", [], {})
        assert not _part_exists(docx_bytes, "word/comments.xml")

    def test_comment_cites_the_rule_id_and_rationale(self):
        text = "Original clause text here."
        findings = [_finding("H_LOL_01", 0, 8, "Original", "Revised", rationale="uncapped exposure is risky")]
        decisions = {fk(0, "H_LOL_01"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert "H_LOL_01" in comments_xml
        assert "uncapped exposure is risky" in comments_xml

    def test_comment_authored_by_the_engine_not_the_attorney(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions, author="Jane Attorney")
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert 'w:author="TriageCounsel Deterministic Engine"' in comments_xml
        assert 'w:author="Jane Attorney"' not in comments_xml  # the edit is Jane's; the rationale note is the engine's

    def test_content_types_and_relationship_are_registered(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        content_types = _part_xml(docx_bytes, "[Content_Types].xml")
        rels = _part_xml(docx_bytes, "word/_rels/document.xml.rels")
        assert "comments+xml" in content_types
        assert "relationships/comments" in rels

    def test_comment_reference_style_is_registered(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        styles = _part_xml(docx_bytes, "word/styles.xml")
        assert 'w:styleId="CommentReference"' in styles

    def test_one_comment_per_applied_redline(self):
        text = "AAAA BBBB CCCC DDDD"
        findings = [_finding("R1", 0, 4, "AAAA", "first-new"), _finding("R2", 10, 14, "CCCC", "second-new")]
        decisions = {fk(0, "R1"): {"action": "accepted"}, fk(1, "R2"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert comments_xml.count("<w:comment ") == 2


class TestTrackChangesEnabled:
    def test_track_changes_turned_on_when_redlines_applied(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        settings = _part_xml(docx_bytes, "word/settings.xml")
        assert "<w:trackChanges" in settings

    def test_track_changes_turned_on_even_with_no_redlines(self):
        # harmless and still useful — an empty review still benefits from
        # having Track Changes on for whatever happens next
        docx_bytes, _ = build_redlined_docx("test.docx", "plain text", [], {})
        settings = _part_xml(docx_bytes, "word/settings.xml")
        assert "<w:trackChanges" in settings


class TestRejectedFindings:
    def test_rejected_redline_text_is_not_applied(self):
        text = "The Vendor shall have unlimited liability."
        findings = [_finding("R1", 11, 32, "shall have unlimited", "shall cap liability")]
        decisions = {fk(0, "R1"): {"action": "rejected", "reason": "not applicable"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)
        assert "shall cap liability" not in _all_text(doc, "w:t")
        assert "shall have unlimited" in _all_text(doc, "w:t")  # untouched plain text, not a deletion
        assert skipped == []
        # original text is untouched — no deletion was made, even though a comment exists
        assert "shall have unlimited" not in _all_text(doc, "w:delText")

    def test_rejected_finding_gets_a_comment_with_the_reason(self):
        text = "The Vendor shall have unlimited liability under this Agreement."
        findings = [_finding("H_LOL_01", 11, 32, "shall have unlimited", "shall cap liability", title="Unlimited Liability")]
        decisions = {fk(0, "H_LOL_01"): {"action": "rejected", "reason": "deal size too small to matter"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert _part_exists(docx_bytes, "word/comments.xml")
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert "H_LOL_01" in comments_xml
        assert "deal size too small to matter" in comments_xml
        assert "Reviewed and declined" in comments_xml

    def test_rejected_finding_comment_is_authored_by_the_attorney_not_the_engine(self):
        text = "The Vendor shall have unlimited liability."
        findings = [_finding("R1", 11, 32, "shall have unlimited", "shall cap liability")]
        decisions = {fk(0, "R1"): {"action": "rejected", "reason": "not applicable"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions, author="Jane Attorney")
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert 'w:author="Jane Attorney"' in comments_xml
        assert 'w:author="TriageCounsel Deterministic Engine"' not in comments_xml

    def test_rejected_finding_produces_no_ins_or_del(self):
        text = "The Vendor shall have unlimited liability."
        findings = [_finding("R1", 11, 32, "shall have unlimited", "shall cap liability")]
        decisions = {fk(0, "R1"): {"action": "rejected", "reason": "not applicable"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)
        assert _elements(doc, "w:ins") == []
        assert _elements(doc, "w:del") == []

    def test_rejected_and_accepted_findings_both_annotated_in_one_pass(self):
        text = "AAAA BBBB CCCC DDDD"
        findings = [
            _finding("R1", 0, 4, "AAAA", "first-new", title="First"),
            _finding("R2", 10, 14, "CCCC", None, title="Second"),
        ]
        decisions = {fk(0, "R1"): {"action": "accepted"}, fk(1, "R2"): {"action": "rejected", "reason": "no thanks"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == []
        doc = _open(docx_bytes)
        assert "first-new" in _all_text(doc, "w:t")
        assert "CCCC" in _all_text(doc, "w:t")  # rejected span untouched
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert comments_xml.count("<w:comment ") == 2
        assert "no thanks" in comments_xml

    def test_rejected_with_empty_reason_is_not_annotated(self):
        # shouldn't happen given review_workflow's validation, but must not crash or
        # produce a blank comment if it somehow does
        text = "The Vendor shall have unlimited liability."
        findings = [_finding("R1", 11, 32, "shall have unlimited", "shall cap liability")]
        decisions = {fk(0, "R1"): {"action": "rejected", "reason": "  "}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert not _part_exists(docx_bytes, "word/comments.xml")

    def test_rejected_comment_initials_reflect_the_attorney_not_the_engine(self):
        text = "The Vendor shall have unlimited liability."
        findings = [_finding("R1", 11, 32, "shall have unlimited", "shall cap liability")]
        decisions = {fk(0, "R1"): {"action": "rejected", "reason": "not applicable"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions, author="Jane Attorney")
        comments_xml = _part_xml(docx_bytes, "word/comments.xml")
        assert 'w:initials="JA"' in comments_xml

    def test_rejected_finding_overlapping_an_accepted_one_is_skipped(self):
        text = "0123456789ABCDEFGHIJ"
        findings = [
            _finding("R1", 0, 10, text[0:10], "FIRST-REPLACEMENT"),
            _finding("R2", 5, 15, text[5:15], None),
        ]
        decisions = {fk(0, "R1"): {"action": "accepted"}, fk(1, "R2"): {"action": "rejected", "reason": "overlaps"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == ["R2"]


class TestOtherSkippedDecisions:
    def test_flagged_findings_with_no_redline_are_not_applied(self):
        text = "Some indemnification clause text."
        findings = [_finding("R1", 5, 22, "indemnification")]
        decisions = {fk(0, "R1"): {"action": "flagged"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)
        assert "indemnification" in _all_text(doc, "w:t")

    def test_undecided_finding_is_untouched(self):
        text = "Text with a finding nobody decided on yet."
        findings = [_finding("R1", 5, 9, "with", "changed")]
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, {})
        doc = _open(docx_bytes)
        assert "changed" not in _all_text(doc, "w:t")
        assert skipped == []

    def test_missing_position_data_is_skipped_not_crashed(self):
        findings = [{"rule_id": "R1", "start_index": None, "end_index": None, "exact_snippet": "x", "redline": {"suggested_redline": "y"}}]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", "some text", findings, decisions)
        assert docx_bytes


class TestOverlappingSpans:
    def test_overlapping_accepted_findings_the_second_is_skipped_not_corrupted(self):
        text = "0123456789ABCDEFGHIJ"
        findings = [
            _finding("R1", 0, 10, text[0:10], "FIRST-REPLACEMENT"),
            _finding("R2", 5, 15, text[5:15], "SECOND-REPLACEMENT"),
        ]
        decisions = {fk(0, "R1"): {"action": "accepted"}, fk(1, "R2"): {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == ["R2"]
        doc = _open(docx_bytes)
        assert "FIRST-REPLACEMENT" in _all_text(doc, "w:t")
        assert "SECOND-REPLACEMENT" not in _all_text(doc, "w:t")

    def test_non_overlapping_findings_both_applied_in_order(self):
        text = "AAAA BBBB CCCC DDDD"
        findings = [_finding("R1", 0, 4, "AAAA", "first-new"), _finding("R2", 10, 14, "CCCC", "second-new")]
        decisions = {fk(0, "R1"): {"action": "accepted"}, fk(1, "R2"): {"action": "accepted"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert skipped == []
        full_text = _all_text(_open(docx_bytes), "w:t")
        assert "first-new" in full_text and "second-new" in full_text
        assert full_text.index("first-new") < full_text.index("second-new")


class TestDocumentStructure:
    def test_header_note_present(self):
        docx_bytes, _ = build_redlined_docx("test.docx", "text", [], {})
        full_text = _all_text(_open(docx_bytes), "w:t")
        assert "Track Changes" in full_text

    def test_filename_in_title(self):
        docx_bytes, _ = build_redlined_docx("High.docx", "text", [], {})
        assert "High.docx" in _all_text(_open(docx_bytes), "w:t")

    def test_paragraph_breaks_preserved(self):
        text = "First paragraph.\n\nSecond paragraph."
        docx_bytes, _ = build_redlined_docx("test.docx", text, [], {})
        texts = [p.text for p in _open(docx_bytes).paragraphs if p.text.strip()]
        assert any(t == "First paragraph." for t in texts)
        assert any(t == "Second paragraph." for t in texts)

    def test_empty_document_does_not_crash(self):
        docx_bytes, skipped = build_redlined_docx("test.docx", "", [], {})
        assert docx_bytes
        assert skipped == []


class TestPackageIntegrity:
    def test_output_is_a_well_formed_zip(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
        assert zf.testzip() is None  # None means every member's CRC checked out

    def test_every_injected_part_is_well_formed_xml(self):
        text = "Original clause text here."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
        for name in ("[Content_Types].xml", "word/_rels/document.xml.rels", "word/styles.xml",
                     "word/document.xml", "word/settings.xml", "word/comments.xml"):
            etree.fromstring(zf.read(name))  # raises on malformed XML

    def test_document_reopens_cleanly_in_python_docx(self):
        text = "Original clause text here. More text follows."
        findings = [_finding("R1", 0, 8, "Original", "Revised")]
        decisions = {fk(0, "R1"): {"action": "accepted"}}
        docx_bytes, _ = build_redlined_docx("test.docx", text, findings, decisions)
        doc = _open(docx_bytes)  # must not raise
        assert len(doc.paragraphs) > 0


class TestAgainstRealEngineOutput:
    def test_real_finding_positions_round_trip(self, rule_engine):
        text = "In no event shall liability be limited under this Agreement, without limit."
        result = rule_engine.analyze(text)
        findings = [
            {
                "rule_id": f.rule_id, "title": f.title, "rationale": f.rationale,
                "start_index": f.start_index, "end_index": f.end_index,
                "exact_snippet": f.exact_snippet, "redline": None,
            }
            for f in result["findings"]
        ]
        if not findings:
            pytest.skip("no findings on this fixture text")
        decisions = {fk(0, findings[0]["rule_id"]): {"action": "flagged"}}
        docx_bytes, skipped = build_redlined_docx("test.docx", text, findings, decisions)
        assert docx_bytes
