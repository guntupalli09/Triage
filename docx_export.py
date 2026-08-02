"""
Redlined .docx generation for the review workflow's "Generate Negotiation
Package" export — native Word Track Changes (w:ins / w:del), with a Word
comment on every accepted/edited redline explaining the deterministic rule
behind it.

python-docx has no public API for track changes or comments — both are
built here via direct OOXML element construction (docx.oxml.OxmlElement)
and, for comments specifically, direct manipulation of the saved .docx as a
zip package (python-docx can't add a new document part like word/comments.xml
on its own). This can't be validated against real Microsoft Word in this
environment; it has been checked for well-formedness, round-tripped through
python-docx's own parser, and independently validated with mammoth (a
separate, unrelated OOXML parser) confirming zero warnings/errors and
correct interpretation of the insertions, deletions, and comment
relationships. That is strong evidence, not a substitute for opening it in
Word.

Track-changes authorship is the *reviewing attorney* (an accepted/edited
redline becomes their edit the moment they accept it — the same way
accepting a Grammarly or Word Copilot suggestion attributes the resulting
change to the human, not the tool). The explanatory comment is authored as
"TriageCounsel Deterministic Engine" — the system's reasoning stays fully
visible and attributable, it just doesn't masquerade as the edit itself.

Only decisions with action in ("accepted", "edited") mutate the document —
rejected/flagged/dismissed findings belong in the cover memo
(review_workflow.build_cover_memo_text), not in the redlined document body.
"""

import io
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

COMMENTS_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
COMMENTS_RELATIONSHIP_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
ENGINE_AUTHOR = "TriageCounsel Deterministic Engine"


def _xml_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;").replace("'", "&apos;")
    )


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text_run(text: str, delete: bool = False):
    r = OxmlElement("w:r")
    t = OxmlElement("w:delText" if delete else "w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def _ins_element(author: str, date_iso: str, rev_id: int, text: str):
    el = OxmlElement("w:ins")
    el.set(qn("w:id"), str(rev_id))
    el.set(qn("w:author"), author)
    el.set(qn("w:date"), date_iso)
    el.append(_text_run(text))
    return el


def _del_element(author: str, date_iso: str, rev_id: int, text: str):
    el = OxmlElement("w:del")
    el.set(qn("w:id"), str(rev_id))
    el.set(qn("w:author"), author)
    el.set(qn("w:date"), date_iso)
    el.append(_text_run(text, delete=True))
    return el


def _comment_range_start(comment_id: int):
    el = OxmlElement("w:commentRangeStart")
    el.set(qn("w:id"), str(comment_id))
    return el


def _comment_range_end_with_reference(comment_id: int):
    """w:commentRangeEnd plus the w:r/w:commentReference run that renders
    the clickable comment marker — always emitted together since a range
    end with no reference run is a comment nobody can open."""
    end = OxmlElement("w:commentRangeEnd")
    end.set(qn("w:id"), str(comment_id))
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rstyle = OxmlElement("w:rStyle")
    rstyle.set(qn("w:val"), "CommentReference")
    rpr.append(rstyle)
    run.append(rpr)
    ref = OxmlElement("w:commentReference")
    ref.set(qn("w:id"), str(comment_id))
    run.append(ref)
    return end, run


def _flush_text(doc: Document, para, text_chunk: str):
    """Appends text_chunk to para as plain (untracked) runs, starting new
    paragraphs on blank lines and line breaks on single newlines."""
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


def _inject_comments_part(docx_bytes: bytes, comments: List[Dict[str, str]]) -> bytes:
    """Adds word/comments.xml + the CommentReference character style +
    the Content_Types override + the document relationship — everything
    python-docx doesn't know how to do, done by treating the saved .docx
    as the zip package it actually is."""
    if not comments:
        return docx_bytes

    comment_items = "".join(
        f'<w:comment w:id="{c["id"]}" w:author="{_xml_escape(c["author"])}" '
        f'w:initials="{_xml_escape(c.get("initials", "TC"))}" w:date="{c["date"]}">'
        f'<w:p><w:r><w:t xml:space="preserve">{_xml_escape(c["text"])}</w:t></w:r></w:p></w:comment>'
        for c in comments
    )
    comments_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"{comment_items}</w:comments>"
    )

    zin = zipfile.ZipFile(io.BytesIO(docx_bytes), "r")
    content_types = zin.read("[Content_Types].xml").decode("utf-8")
    rels = zin.read("word/_rels/document.xml.rels").decode("utf-8")
    styles = zin.read("word/styles.xml").decode("utf-8")

    if "/word/comments.xml" not in content_types:
        content_types = content_types.replace(
            "</Types>",
            f'<Override PartName="/word/comments.xml" ContentType="{COMMENTS_CONTENT_TYPE}"/></Types>',
        )
    if COMMENTS_RELATIONSHIP_TYPE not in rels:
        rels = rels.replace(
            "</Relationships>",
            f'<Relationship Id="rIdTriageComments" Type="{COMMENTS_RELATIONSHIP_TYPE}" Target="comments.xml"/></Relationships>',
        )
    if 'w:styleId="CommentReference"' not in styles:
        comment_ref_style = (
            '<w:style w:type="character" w:styleId="CommentReference">'
            '<w:name w:val="annotation reference"/><w:basedOn w:val="DefaultParagraphFont"/>'
            '<w:uiPriority w:val="99"/><w:semiHidden/><w:unhideWhenUsed/>'
            '<w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:style>'
        )
        styles = styles.replace("</w:styles>", comment_ref_style + "</w:styles>")

    buf_out = io.BytesIO()
    with zipfile.ZipFile(buf_out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "[Content_Types].xml":
                zout.writestr(item, content_types)
            elif item.filename == "word/_rels/document.xml.rels":
                zout.writestr(item, rels)
            elif item.filename == "word/styles.xml":
                zout.writestr(item, styles)
            else:
                zout.writestr(item, zin.read(item.filename))
        zout.writestr("word/comments.xml", comments_xml)
    return buf_out.getvalue()


def _enable_track_changes(docx_bytes: bytes) -> bytes:
    """Turns Track Changes on in the saved document's settings, so further
    edits either side makes while negotiating also get tracked automatically
    — matches how a redline is normally exchanged between firms."""
    zin = zipfile.ZipFile(io.BytesIO(docx_bytes), "r")
    settings = zin.read("word/settings.xml").decode("utf-8")
    if "<w:trackChanges" not in settings:
        idx = settings.index("<w:settings")
        close = settings.index(">", idx) + 1
        settings = settings[:close] + "<w:trackChanges/>" + settings[close:]

    buf_out = io.BytesIO()
    with zipfile.ZipFile(buf_out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "word/settings.xml":
                zout.writestr(item, settings)
            else:
                zout.writestr(item, zin.read(item.filename))
    return buf_out.getvalue()


def build_redlined_docx(
    filename: str,
    contract_text: str,
    findings: List[Dict[str, Any]],
    decisions: Dict[str, Dict[str, Any]],
    author: Optional[str] = None,
) -> Tuple[bytes, List[str]]:
    """Returns (docx_bytes, skipped_rule_ids). author is the reviewing
    attorney's name/email — becomes the Track Changes author of record for
    every accepted/edited redline, exactly as Word attributes any other
    edit to whoever is signed in. Falls back to a generic label only if the
    caller genuinely has nothing better (should not happen for an
    authenticated review session)."""
    author = author or "TriageCounsel Reviewer"
    decisions = decisions or {}
    date_iso = _iso_now()

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
            "issue": (f.get("redline") or {}).get("issue", f.get("title", f["rule_id"])),
            "rationale": (f.get("redline") or {}).get("legal_rationale") or f.get("rationale", ""),
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
    doc.add_heading(f"Redlined Draft — {filename}", level=1)
    note = doc.add_paragraph()
    note_run = note.add_run(
        "This redline uses native Word Track Changes. Each suggested edit carries a comment "
        "explaining the deterministic rule behind it — accept, reject, or edit them exactly as "
        "you would any other tracked change."
    )
    note_run.italic = True
    doc.add_paragraph()

    comments_meta: List[Dict[str, str]] = []
    para = doc.add_paragraph()
    cursor = 0
    rev_id = 1
    comment_id = 0
    for a in applied:
        para = _flush_text(doc, para, contract_text[cursor:a["start"]])
        para._p.append(_del_element(author, date_iso, rev_id, a["original"]))
        rev_id += 1

        para._p.append(_comment_range_start(comment_id))
        para._p.append(_ins_element(author, date_iso, rev_id, a["new_text"]))
        rev_id += 1
        end_el, ref_run = _comment_range_end_with_reference(comment_id)
        para._p.append(end_el)
        para._p.append(ref_run)

        comment_text = f"Rule {a['rule_id']} — {a['issue']}. {a['rationale']}".strip()
        if a["edited"]:
            comment_text += " (Suggested redline was edited by the reviewer before acceptance.)"
        comments_meta.append({"id": str(comment_id), "author": ENGINE_AUTHOR, "date": date_iso, "text": comment_text})
        comment_id += 1

        cursor = a["end"]
    _flush_text(doc, para, contract_text[cursor:])

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()
    docx_bytes = _inject_comments_part(docx_bytes, comments_meta)
    docx_bytes = _enable_track_changes(docx_bytes)
    return docx_bytes, skipped
