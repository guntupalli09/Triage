"""
Independent validation of the downloaded Negotiation Package ZIP and the
redlined .docx inside it — using three parsers that share no code with each
other or with docx_export.py, so a bug that survives one is unlikely to
survive all three:

  1. Raw zip + stdlib xml.etree — structural/XML well-formedness, and exact
     counts of w:ins/w:del/comment elements.
  2. python-docx — the same library reads what the app writes; a document
     it cannot open is not a usable Word document, no matter how well-formed
     its raw XML is.
  3. mammoth — a completely separate, third-party OOXML→HTML converter with
     its own parser; used here for its warning/error surface, not its HTML
     output. A mammoth warning (e.g. an unrecognized style, a malformed
     relationship) that structlint/python-docx don't catch is exactly the
     kind of divergence "every validator should agree" exists to catch.

This module never touches docx_export.py. It only sees the bytes a real
`GET /contract/{id}/review/package` HTTP response actually returned.
"""
from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

REQUIRED_ZIP_ENTRIES = {"[Content_Types].xml", "word/document.xml", "word/_rels/document.xml.rels"}
REQUIRED_XML_PARTS = ("word/document.xml", "word/settings.xml", "word/styles.xml", "[Content_Types].xml")


@dataclass
class DocxValidationResult:
    ok: bool
    zip_valid: bool = False
    zip_entries: List[str] = field(default_factory=list)
    missing_required_entries: List[str] = field(default_factory=list)
    xml_well_formed: Dict[str, bool] = field(default_factory=dict)
    ins_count: int = 0
    del_count: int = 0
    comment_reference_count: int = 0
    comments_defined_count: int = 0
    python_docx_ok: bool = False
    python_docx_error: str = ""
    python_docx_paragraph_count: int = 0
    mammoth_ok: bool = False
    mammoth_error: str = ""
    mammoth_warnings: List[str] = field(default_factory=list)
    all_validators_agree: bool = False
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        return d


def validate_package_zip(zip_bytes: bytes) -> Dict[str, Any]:
    """Validates the outer Negotiation Package .zip: is it a real zip, does
    it contain exactly the three deliverables the app promises
    (Redlined_*.docx, Cover_Memo.txt, Audit_Trail.txt)."""
    result: Dict[str, Any] = {"ok": False, "entries": [], "has_docx": False, "has_memo": False, "has_audit": False, "errors": []}
    if not zipfile.is_zipfile(io.BytesIO(zip_bytes)):
        result["errors"].append("not a valid zip container")
        return result
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    result["entries"] = names
    result["has_docx"] = any(n.startswith("Redlined_") and n.endswith(".docx") for n in names)
    result["has_memo"] = "Cover_Memo.txt" in names
    result["has_audit"] = "Audit_Trail.txt" in names
    bad_crc = zf.testzip()
    if bad_crc:
        result["errors"].append(f"corrupt member: {bad_crc}")
    result["ok"] = result["has_docx"] and result["has_memo"] and result["has_audit"] and not bad_crc
    return result


def validate_docx(docx_bytes: bytes, expected_redline_count: int) -> DocxValidationResult:
    r = DocxValidationResult(ok=False)

    # --- Validator 1: raw zip + stdlib XML ---
    if not zipfile.is_zipfile(io.BytesIO(docx_bytes)):
        r.errors.append("docx is not a valid zip container")
        return r
    r.zip_valid = True
    zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
    names = set(zf.namelist())
    r.zip_entries = sorted(names)
    r.missing_required_entries = sorted(REQUIRED_ZIP_ENTRIES - names)
    if r.missing_required_entries:
        r.errors.append(f"missing required parts: {r.missing_required_entries}")

    for part in REQUIRED_XML_PARTS:
        if part not in names:
            continue
        try:
            ET.fromstring(zf.read(part))
            r.xml_well_formed[part] = True
        except ET.ParseError as exc:
            r.xml_well_formed[part] = False
            r.errors.append(f"{part} malformed: {exc}")

    has_comments = "word/comments.xml" in names
    if has_comments:
        try:
            comments_root = ET.fromstring(zf.read("word/comments.xml"))
            r.xml_well_formed["word/comments.xml"] = True
            r.comments_defined_count = len(comments_root.findall(f"{W_NS}comment"))
        except ET.ParseError as exc:
            r.xml_well_formed["word/comments.xml"] = False
            r.errors.append(f"word/comments.xml malformed: {exc}")

    if "word/document.xml" in names and r.xml_well_formed.get("word/document.xml"):
        doc_root = ET.fromstring(zf.read("word/document.xml"))
        r.ins_count = len(doc_root.findall(f".//{W_NS}ins"))
        r.del_count = len(doc_root.findall(f".//{W_NS}del"))
        r.comment_reference_count = len(doc_root.findall(f".//{W_NS}commentReference"))
        if r.ins_count != expected_redline_count:
            r.errors.append(
                f"w:ins count ({r.ins_count}) != expected accepted/edited redline count ({expected_redline_count})"
            )
        if r.comment_reference_count != r.comments_defined_count:
            r.errors.append(
                f"commentReference count ({r.comment_reference_count}) != comments defined ({r.comments_defined_count})"
            )

    # --- Validator 2: python-docx round-trip ---
    try:
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        r.python_docx_ok = True
        r.python_docx_paragraph_count = len(doc.paragraphs)
    except Exception as exc:  # noqa: BLE001
        r.python_docx_error = f"{type(exc).__name__}: {exc}"
        r.errors.append(f"python-docx could not open the document: {r.python_docx_error}")

    # --- Validator 3: mammoth (independent third-party OOXML parser) ---
    try:
        import mammoth
        result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
        r.mammoth_ok = True
        r.mammoth_warnings = [str(m) for m in result.messages]
        if result.messages:
            r.errors.append(f"mammoth reported {len(result.messages)} warning(s): {r.mammoth_warnings[:5]}")
    except Exception as exc:  # noqa: BLE001
        r.mammoth_error = f"{type(exc).__name__}: {exc}"
        r.errors.append(f"mammoth could not open the document: {r.mammoth_error}")

    r.all_validators_agree = (
        r.zip_valid
        and not r.missing_required_entries
        and all(r.xml_well_formed.values())
        and r.python_docx_ok
        and r.mammoth_ok
        and not r.mammoth_warnings
        and r.ins_count == expected_redline_count
        and r.comment_reference_count == r.comments_defined_count
    )
    r.ok = r.all_validators_agree
    return r
