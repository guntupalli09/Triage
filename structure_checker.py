"""
Defined-Terms & Cross-Reference Integrity Checker.

Product roadmap Feature 2 (see the TriageCounsel product memo, Rev. 2): the
classic first-pass drafting-QA an associate runs before touching substance —
undefined terms, unused definitions, duplicate definitions, and references
to sections/exhibits/schedules that don't actually exist in the document.

Fully structural pattern-matching over defined-term and cross-reference
CONVENTIONS, in the same regex idiom rules_engine.py already uses. This adds
no new legal-risk detection — it is a document-hygiene pass, independent of
severity/overall_risk.

Known limitation, stated honestly rather than silently: this is regex-based
pattern matching over common drafting conventions ("X" means..., (the "X"),
Section 4.2, Exhibit A), not a document parser. A contract that defines
terms with unconventional phrasing, or whose extraction mangled quote
characters, will under- or over-report. Flags here are a worklist for a
human reviewer, not a certified defect list — the same posture
rules_engine.py's REQUIRED_SECTION rules take toward absence claims.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Set, Tuple

# --- Defined-terms patterns ---------------------------------------------

# "Confidential Information" means/shall mean/refers to ... — the actual
# definitional clause, not just a later reference to the term.
_DEFINITION_CLAUSE_RE = re.compile(
    r'"([A-Z][A-Za-z0-9 ,&\'/\-]{1,60}?)"\s+'
    r'(?:shall mean|shall have the meaning|means|refers to|shall refer to)',
)

# Foo Corp ("Company"), (the "Agreement"), (collectively, the "Parties"),
# (in such capacity, "Administrative Agent"), (as defined below, "Term") —
# short-form naming, not a definitional clause on its own; a term named this
# way is "defined" for cross-reference purposes but duplicate short-form
# naming (e.g. once per party) is normal and not flagged as a duplicate.
#
# Deliberately permissive about what precedes the quoted term (any lead-in
# text, not an enumerated list of phrases) — verified against a real credit
# agreement whose dominant convention, "(in such capacity, \"X\")", isn't
# any of the handful of lead-ins an earlier, narrower version of this
# pattern enumerated, which produced a wave of false "used but undefined"
# flags for terms that were, in fact, properly named. The quoted term must
# still be the last thing before the closing paren, which keeps this from
# matching an unrelated quote that merely happens to fall inside some other
# parenthetical.
_SHORT_FORM_NAME_RE = re.compile(
    r'\([^()]{0,60}?"([A-Z][A-Za-z0-9 ,&\'/\-]{1,60}?)"\s*\)',
)

# Any quoted, capitalized phrase anywhere in the document — used to detect
# terms that are USED like defined terms (repeatedly, in quotes) but never
# actually defined by either pattern above.
_QUOTED_CAPITALIZED_RE = re.compile(r'"([A-Z][A-Za-z0-9 ,&\'/\-]{1,60}?)"')

# --- Cross-reference patterns --------------------------------------------

# Section/Clause/Article X(.Y) — one namespace (numbered provisions).
_SECTION_REF_RE = re.compile(
    r'\b(?:Section|Clause|Article|Paragraph)s?\s+(\d+(?:\.\d+)*)', re.IGNORECASE,
)
# A HEADING declaration for a section number: the keyword starts the line —
# covers both a bare numbered heading ("4.2. Confidentiality") and, just as
# commonly in real contracts, "Section 4.2" itself as the heading text
# (either inline — "Section 1.01 Certain Defined Terms" — or as its own
# line in a table of contents). Requiring the keyword/number to START the
# line (not appear mid-sentence) is what distinguishes a heading/ToC entry
# from an ordinary prose cross-reference like "...as described in Section
# 4.2 below" — verified against real fixture contracts (credit agreements,
# PSAs) where "Section N.N" as the heading itself, not a bare number, is
# the dominant convention. Trade-off, stated honestly: a document that
# opens a paragraph with "Section 4.2 governs..." would misclassify that
# sentence as a heading — the safe failure direction (under-reporting, not
# a false "broken reference" flag), consistent with how REQUIRED_SECTION
# rules in rules_engine.py already treat absence claims.
_SECTION_HEADING_RE = re.compile(
    r'^\s*(?:'
    r'(?:Section|Clause|Article|Paragraph)s?\s+(\d+(?:\.\d+)*)\b'   # "Section 4.2" / "Section 4" as heading text
    r'|(\d+(?:\.\d+)*)\.\s+[A-Z]'                                   # bare "1. Title" / "4.2. Title"
    r')', re.IGNORECASE | re.MULTILINE,
)

# Exhibit/Schedule/Appendix/Annex X — a separate namespace (attachments).
# The keyword is matched case-insensitively via a *scoped* inline flag
# (?i:...) so it doesn't also loosen the target group below — a plain
# re.IGNORECASE on the whole pattern would make [A-Z0-9]+ match lowercase
# too, turning "the Schedule for payments" into a false "Schedule for"
# reference (verified: this was a real false positive before the fix).
_ATTACHMENT_REF_RE = re.compile(
    r'\b((?i:Exhibit|Schedule|Appendix|Annex))\s+([A-Z0-9]+)\b',
)
_ATTACHMENT_HEADING_RE = re.compile(
    r'^\s*(?i:EXHIBIT|SCHEDULE|APPENDIX|ANNEX)\s+([A-Z0-9]+)\b', re.MULTILINE,
)

# Common English words that can appear capitalized in a title ("SCHEDULE OF
# INSUREDS") and would otherwise be misread as the attachment's identifier.
# Deliberately excludes single letters ("A", "B") — those are themselves
# completely standard exhibit/schedule identifiers ("Exhibit A"), not
# stopwords, and must never be filtered here.
_STOPWORD_TARGETS = frozenset({"OF", "THE", "FOR", "AND", "TO", "IN"})

# References to an external statute, not this document's own numbering —
# "Section 1445 of the Code", "Section 4975(a)(1)(B)", IRC/ERISA/securities-
# law citations common in credit agreements, loan docs, and PSAs. These are
# NOT internal cross-references and must never be checked against this
# document's own headings.
_STATUTE_PROXIMITY_RE = re.compile(
    r'of\s+(?:the\s+)?(?:Internal Revenue\s+)?Code\b|of\s+ERISA\b|of\s+the\s+Securities\s+(?:Act|Exchange\s+Act)\b|'
    r'U\.?S\.?C\.?\b',
    re.IGNORECASE,
)

# References to a section of a DIFFERENT, separately named document —
# "Section 8.08 of the Credit Agreement" inside a Guaranty that itself
# doesn't define Section 8.08 (the Credit Agreement does), or "Section 9.5
# of the General Conditions" in a construction contract that incorporates a
# separate AIA General Conditions document by reference. Verified against
# real fixtures (a guaranty referencing its credit agreement; an AIA A111
# construction contract referencing AIA A201 General Conditions throughout)
# where this was the dominant source of false "broken" flags.
#
# Matches "of the <Capitalized Phrase>" generally — a real external
# document name almost always carries a distinguishing capitalized modifier
# ("Credit Agreement", "General Conditions", "Contract Documents"). The
# negative lookahead specifically excludes bare "of the Agreement", which
# self-references this document (a contract calling itself "the
# Agreement") and should still be checked against its own headings. This is
# a genuine judgment call, not a certainty: a document that uses a
# capitalized nickname for ITSELF (e.g. "the Guaranty" self-referring
# inside a guaranty agreement) will also be excluded here, meaning a real
# same-document broken reference phrased that way could be missed — an
# under-report, the same safe-failure direction this module takes
# throughout (see the module docstring and REQUIRED_SECTION rules in
# rules_engine.py for the same posture toward absence claims).
_EXTERNAL_DOCUMENT_PROXIMITY_RE = re.compile(
    r'\bof\s+the\s+(?!Agreement\b)[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*){0,3}\b',
)


def _norm(term: str) -> str:
    return re.sub(r'\s+', ' ', term).strip()


def _looks_like_external_reference(text: str, match_end: int) -> bool:
    """True if the ~60 characters right after a "Section N" match read like
    a reference to an external statute (IRC/ERISA/securities-law) or to a
    different, separately named agreement — either way, not an internal
    cross-reference this document's own headings should be checked against."""
    tail = text[match_end:match_end + 60]
    return bool(_STATUTE_PROXIMITY_RE.search(tail) or _EXTERNAL_DOCUMENT_PROXIMITY_RE.search(tail))


@dataclass(frozen=True)
class DefinedTermIssue:
    term: str
    issue: str  # "unused" | "duplicate_definition" | "used_but_undefined"
    detail: str


@dataclass(frozen=True)
class CrossReferenceIssue:
    reference_text: str  # e.g. "Section 7.4", "Exhibit C"
    reference_type: str  # "section" | "attachment"


@dataclass(frozen=True)
class StructureReport:
    defined_term_count: int
    unused_terms: List[DefinedTermIssue]
    duplicate_definitions: List[DefinedTermIssue]
    used_but_undefined: List[DefinedTermIssue]
    broken_cross_references: List[CrossReferenceIssue]
    methodology_note: str = (
        "Regex-based pattern matching over common drafting conventions (\"X\" means..., "
        "(the \"X\"), Section 4.2, Exhibit A) — not a document parser. Unconventional "
        "phrasing or mangled quote characters from text extraction can cause under- or "
        "over-reporting. Treat this as a worklist for a human reviewer, not a certified "
        "defect list."
    )

    @property
    def total_issue_count(self) -> int:
        return (
            len(self.unused_terms)
            + len(self.duplicate_definitions)
            + len(self.used_but_undefined)
            + len(self.broken_cross_references)
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "defined_term_count": self.defined_term_count,
            "unused_terms": [{"term": i.term, "detail": i.detail} for i in self.unused_terms],
            "duplicate_definitions": [{"term": i.term, "detail": i.detail} for i in self.duplicate_definitions],
            "used_but_undefined": [{"term": i.term, "detail": i.detail} for i in self.used_but_undefined],
            "broken_cross_references": [
                {"reference_text": i.reference_text, "reference_type": i.reference_type}
                for i in self.broken_cross_references
            ],
            "total_issue_count": self.total_issue_count,
            "methodology_note": self.methodology_note,
        }


def _find_defined_terms(text: str) -> Tuple[Set[str], List[Tuple[str, int]], Set[str]]:
    """Returns (all_defined_terms, definition_clause_occurrences, short_form_terms).

    definition_clause_occurrences is every ("X" means...) match with its
    position — used for duplicate-definition detection. short_form_terms are
    terms only ever named via (the "X") parenthetical, which legitimately
    can appear more than once (e.g. once per party) without being a
    duplicate definition.
    """
    clause_matches = [(_norm(m.group(1)), m.start()) for m in _DEFINITION_CLAUSE_RE.finditer(text)]
    short_form_terms = {_norm(m.group(1)) for m in _SHORT_FORM_NAME_RE.finditer(text)}
    all_defined = {t for t, _ in clause_matches} | short_form_terms
    return all_defined, clause_matches, short_form_terms


def _count_usages(text: str, term: str) -> int:
    """Total occurrences of `term` as a standalone phrase anywhere in the
    document (both quoted and bare), including its own defining occurrence."""
    pattern = r'\b' + re.escape(term) + r'\b'
    return len(re.findall(pattern, text))


def _check_defined_terms(text: str) -> Tuple[List[DefinedTermIssue], List[DefinedTermIssue], List[DefinedTermIssue]]:
    all_defined, clause_matches, short_form_terms = _find_defined_terms(text)

    # Duplicate definitions: the same term given a full "means/shall mean"
    # definitional clause more than once. Short-form naming (the "X") is
    # deliberately excluded — that can legitimately repeat.
    seen_clause_terms: Dict[str, int] = {}
    duplicates: List[DefinedTermIssue] = []
    flagged_dupes: Set[str] = set()
    for term, _pos in clause_matches:
        seen_clause_terms[term] = seen_clause_terms.get(term, 0) + 1
        if seen_clause_terms[term] == 2 and term not in flagged_dupes:
            duplicates.append(DefinedTermIssue(
                term=term, issue="duplicate_definition",
                detail=f'"{term}" is given a full definitional clause more than once.',
            ))
            flagged_dupes.add(term)

    # Unused: defined but appears nowhere else in the document beyond its
    # own definition (usage count <= 1 defining occurrence... allow up to 1
    # extra for the short-form naming pattern itself, which co-occurs with
    # the clause at the same position range in some drafting styles).
    unused: List[DefinedTermIssue] = []
    for term in sorted(all_defined):
        count = _count_usages(text, term)
        if count <= 1:
            unused.append(DefinedTermIssue(
                term=term, issue="unused",
                detail=f'"{term}" is defined but never used elsewhere in the document.',
            ))

    # Used but undefined: a quoted, capitalized phrase referenced 2+ times
    # (i.e. formatted and repeated like a defined term) that never received
    # a definitional clause or short-form naming.
    quoted_counts: Dict[str, int] = {}
    for m in _QUOTED_CAPITALIZED_RE.finditer(text):
        term = _norm(m.group(1))
        quoted_counts[term] = quoted_counts.get(term, 0) + 1
    used_but_undefined: List[DefinedTermIssue] = []
    for term, count in sorted(quoted_counts.items()):
        if term in all_defined:
            continue
        if count >= 2:
            used_but_undefined.append(DefinedTermIssue(
                term=term, issue="used_but_undefined",
                detail=f'"{term}" is quoted like a defined term and referenced {count} times, '
                       f'but no definitional clause was found for it.',
            ))

    return unused, duplicates, used_but_undefined


# If a large share of a document's own distinct cross-references come back
# "broken," that is itself evidence this checker's heading-detection
# doesn't fit this document's drafting convention — not that a
# professionally drafted contract genuinely has dozens of dangling
# references. Verified against real fixtures (AIA construction contracts,
# license agreements with idiosyncratic numbering) where an unmodeled
# convention, not real gaps, was driving high counts. Below this
# confidence gate, all references of that type are suppressed for the
# document rather than reported — the same under-report-over-over-report
# posture the rest of this module takes.
_MIN_REFERENCES_FOR_CONFIDENCE = 8
_MAX_BROKEN_FRACTION = 0.4


def _resolve_references(
    ref_matches: List[Tuple[str, str]],  # (display_text, target_key)
    known_targets: Set[str],
) -> List[CrossReferenceIssue]:
    seen: Set[str] = set()
    total_checked: Set[str] = set()
    broken_targets: List[str] = []
    display_by_target: Dict[str, str] = {}

    for display_text, target in ref_matches:
        total_checked.add(target)
        display_by_target.setdefault(target, display_text)
        if target not in known_targets and target not in seen:
            broken_targets.append(target)
            seen.add(target)

    if len(total_checked) < _MIN_REFERENCES_FOR_CONFIDENCE:
        return [
            CrossReferenceIssue(reference_text=display_by_target[t], reference_type="")
            for t in broken_targets
        ]
    if broken_targets and len(broken_targets) / len(total_checked) > _MAX_BROKEN_FRACTION:
        return []  # low confidence — see module docstring / gate rationale above
    return [
        CrossReferenceIssue(reference_text=display_by_target[t], reference_type="")
        for t in broken_targets
    ]


def _check_cross_references(text: str) -> List[CrossReferenceIssue]:
    known_sections = {
        (m.group(1) or m.group(2)) for m in _SECTION_HEADING_RE.finditer(text)
    }
    known_attachments = {
        _norm(m.group(1)).upper() for m in _ATTACHMENT_HEADING_RE.finditer(text)
    } - _STOPWORD_TARGETS

    # Note: no separate "skip entirely if zero known headings" gate — that
    # case (most often a PDF/DOCX extraction that collapsed all line
    # breaks; see rules_engine.normalize_contract_text's own similar
    # honesty about extraction artifacts) is already covered by
    # _resolve_references' confidence-fraction gate below: zero known
    # headings makes every checked reference "broken," which trips the
    # >40%-broken gate once there are enough references to be a
    # statistically meaningful sample. A document with only a handful of
    # references and no detected headings still gets them checked (and
    # flagged if genuinely unresolved) — small samples pass through.
    section_refs: List[Tuple[str, str]] = []
    for m in _SECTION_REF_RE.finditer(text):
        target = m.group(1)
        if _looks_like_external_reference(text, m.end()):
            continue
        # Bare (non-decimal) 3+ digit numbers are essentially always an
        # external statute citation (IRC/ERISA section numbers commonly run
        # into the thousands) rather than this document's own numbering,
        # even without a nearby "of the Code" cue.
        if "." not in target and len(target) >= 3:
            continue
        section_refs.append((f"Section {target}", target))

    attachment_refs: List[Tuple[str, str]] = []
    for m in _ATTACHMENT_REF_RE.finditer(text):
        kind, target = m.group(1), _norm(m.group(2)).upper()
        if target in _STOPWORD_TARGETS:
            continue
        attachment_refs.append((f"{kind.capitalize()} {target}", target))

    broken: List[CrossReferenceIssue] = []
    for issue in _resolve_references(section_refs, known_sections):
        broken.append(CrossReferenceIssue(reference_text=issue.reference_text, reference_type="section"))
    for issue in _resolve_references(attachment_refs, known_attachments):
        broken.append(CrossReferenceIssue(reference_text=issue.reference_text, reference_type="attachment"))

    return broken


def analyze_structure(text: str) -> StructureReport:
    """Pure function: normalized contract text -> StructureReport.

    Callers should pass already-normalized text (see
    rules_engine.normalize_contract_text) so quote/dash handling stays
    consistent with the rest of the pipeline. This module does not import
    rules_engine itself, to avoid a circular import — rules_engine.py
    imports and calls this module, not the other way around.
    """
    unused, duplicates, used_but_undefined = _check_defined_terms(text)
    broken_refs = _check_cross_references(text)
    all_defined, _, _ = _find_defined_terms(text)

    return StructureReport(
        defined_term_count=len(all_defined),
        unused_terms=unused,
        duplicate_definitions=duplicates,
        used_but_undefined=used_but_undefined,
        broken_cross_references=broken_refs,
    )
