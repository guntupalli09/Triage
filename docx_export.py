"""
Redlined .docx generation for the review workflow's "Generate Negotiation
Package" export.

Deliberately NOT native Word Track Changes (w:ins/w:del XML). That would be
the more authentic version, but it's fiddly low-level OOXML surgery that
can't be validated here without Word itself open to confirm the output
isn't silently corrupt — a bug there produces a file that's worse than not
having the feature. Instead: every accepted/edited redline is applied
directly into the document text as a clearly marked deletion (strikethrough)
+ insertion (underlined), with a header note telling the reader to turn on
Word's own Track Changes if they want native accept/reject controls over
further edits. Real, inspectable, safe.

Only decisions with action in ("accepted", "edited") mutate the document —
rejected/flagged/dismissed findings belong in the cover memo
(review_workflow.build_cover_memo_text), not in the redlined document body.
"""

import io
from typing import Any, Dict, List, Tuple

from docx import Document
from docx.shared import Pt, RGBColor

DEL_COLOR = RGBColor(0x8E, 0x24, 0x1B)
INS_COLOR = RGBColor(0x23, 0x5C, 0x3D)
NOTE_COLOR = RGBColor(0x5C, 0x64, 0x72)


def _flush_text(doc: Document, para, text_chunk: str):
    """Appends text_chunk to para, starting new paragraphs on blank lines and
    line breaks on single newlines, returning the paragraph that should
    receive whatever comes next."""
    if not text_chunk:
        return para
    for i, block in enumerate(text_chunk.split("\n\n")):
        if i > 0:
            para = doc.add_paragraph()
        lines = block.split("\n")
        for j, line in enumerate(lines):
            if j > 0:
                para.add_run().add_break()
            if line:
                para.add_run(line)
    return para


def build_redlined_docx(
    filename: str,
    contract_text: str,
    findings: List[Dict[str, Any]],
    decisions: Dict[str, Dict[str, Any]],
) -> Tuple[bytes, List[str]]:
    """Returns (docx_bytes, skipped_rule_ids). skipped_rule_ids are
    accepted/edited findings that couldn't be applied — either their
    character span is missing/invalid, or it overlaps a higher-priority
    (earlier, lower start_index) applied redline. Overlaps are rare (two
    rules anchoring to genuinely overlapping text) but real — silently
    corrupting the document by applying both would be worse than skipping
    one and reporting it."""
    decisions = decisions or {}
    applicable = []
    for f in findings:
        d = decisions.get(f["rule_id"])
        if not d or d.get("action") not in ("accepted", "edited"):
            continue
        start, end = f.get("start_index"), f.get("end_index")
        if start is None or end is None or start >= end or end > len(contract_text):
            continue
        if d["action"] == "edited":
            new_text = (d.get("edited_text") or "").strip()
        else:
            redline = f.get("redline") or {}
            new_text = redline.get("suggested_redline", "")
        if not new_text:
            continue
        applicable.append({
            "rule_id": f["rule_id"], "start": start, "end": end,
            "original": contract_text[start:end], "new_text": new_text,
            "edited": d["action"] == "edited",
        })

    applicable.sort(key=lambda a: a["start"])
    applied, skipped = [], []
    cursor_end = -1
    for a in applicable:
        if a["start"] < cursor_end:
            skipped.append(a["rule_id"])
            continue
        applied.append(a)
        cursor_end = a["end"]

    doc = Document()
    title = doc.add_heading(f"Redlined Draft — {filename}", level=1)
    note = doc.add_paragraph()
    note_run = note.add_run(
        "AI-suggested redlines are marked below: strikethrough = removed language, "
        "underlined = inserted language. These are applied directly in the text, not as "
        "native Word Track Changes — turn on Review → Track Changes if you want Word's "
        "own accept/reject controls over any further edits you make."
    )
    note_run.italic = True
    note_run.font.size = Pt(9)
    note_run.font.color.rgb = NOTE_COLOR
    doc.add_paragraph()

    para = doc.add_paragraph()
    cursor = 0
    for a in applied:
        para = _flush_text(doc, para, contract_text[cursor:a["start"]])
        del_run = para.add_run(a["original"])
        del_run.font.strike = True
        del_run.font.color.rgb = DEL_COLOR
        ins_run = para.add_run(" " + a["new_text"])
        ins_run.font.underline = True
        ins_run.font.color.rgb = INS_COLOR
        if a["edited"]:
            tag_run = para.add_run(" [edited by reviewer]")
            tag_run.italic = True
            tag_run.font.size = Pt(8)
            tag_run.font.color.rgb = NOTE_COLOR
        cursor = a["end"]
    _flush_text(doc, para, contract_text[cursor:])

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue(), skipped
