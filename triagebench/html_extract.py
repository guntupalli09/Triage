"""
Two independent HTML→text extractors for SEC EDGAR exhibit filings.

The corpus files are SGML-wrapped HTML (`<DOCUMENT>...<TEXT><html>...`).
TriageCounsel's own `extract_text_from_file` (main.py) only handles
.txt/.pdf/.docx — it has never had to parse this corpus's SEC HTML — so this
module is TriageBench's own upload-stage adapter, deliberately kept separate
from and simpler than the application's extractor.

Two implementations exist on purpose, not for redundancy but because the
benchmark's "independent parsing" validation goal requires a second,
differently-built parser to cross-check the primary one: if a formatting
quirk in one SEC filing produces wildly different text between a proper
event-driven parser (`extract_primary`) and a dumb regex tag-stripper
(`extract_reference`), that is a signal the primary extractor is silently
mis-parsing that document, not evidence the document is unusual.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import List

BLOCK_TAGS = {
    "p", "div", "br", "tr", "table", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "ul", "ol", "hr", "section", "article",
}
SKIP_TAGS = {"script", "style", "head", "title"}


class _BlockAwareHTMLExtractor(HTMLParser):
    """Turns block-level tags into line breaks so clause boundaries in the
    rendered text roughly match clause boundaries in the source document —
    the rule engine's chunker (`_chunk_text` in rules_engine.py) depends on
    real newlines to find them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0 and data:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _collapse_whitespace(text: str) -> str:
    # Collapse runs of spaces/tabs but preserve paragraph breaks (multiple
    # newlines are what the rule engine's chunker treats as clause
    # boundaries — collapsing them to a single newline would merge clauses).
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_sgml_wrapper(raw: str) -> str:
    """Drop the `<DOCUMENT>/<TYPE>/<SEQUENCE>/...` SGML header EDGAR wraps
    each exhibit file in, keeping only the `<TEXT>...</TEXT>` (or the whole
    thing, if this file isn't wrapped) — the HTML itself starts inside it."""
    m = re.search(r"<TEXT>(.*?)</TEXT>", raw, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else raw


def extract_primary(raw_bytes: bytes) -> str:
    """Event-driven HTML parser (stdlib html.parser) — the extractor whose
    output actually feeds the rule engine in the benchmark pipeline."""
    text = raw_bytes.decode("utf-8", errors="replace")
    text = _strip_sgml_wrapper(text)
    parser = _BlockAwareHTMLExtractor()
    parser.feed(text)
    parser.close()
    return _collapse_whitespace(parser.get_text())


_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_BREAK_RE = re.compile(
    r"</(p|div|tr|table|h[1-6]|li|br|section|article)\b[^>]*>", re.IGNORECASE
)


def extract_reference(raw_bytes: bytes) -> str:
    """Dumb, independent second parser: turn known block-closing tags into
    newlines, then regex-strip every remaining tag. No shared code path with
    extract_primary — used only as a cross-check, never as the text that
    feeds analysis."""
    text = raw_bytes.decode("utf-8", errors="replace")
    text = _strip_sgml_wrapper(text)
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", text)
    text = _BLOCK_BREAK_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = unescape(text)
    return _collapse_whitespace(text)


@dataclass
class IndependentParseCheck:
    primary_words: int
    reference_words: int
    word_count_delta_pct: float
    agree: bool


def cross_check(primary_text: str, reference_text: str, tolerance_pct: float = 8.0) -> IndependentParseCheck:
    """Word-count agreement between the two independent extractors. A large
    divergence means one of them is mishandling this document's markup —
    exactly the failure mode 'independent parsing' validation exists to
    catch, since neither extractor can mark its own homework."""
    pw = len(primary_text.split())
    rw = len(reference_text.split())
    denom = max(pw, rw, 1)
    delta_pct = abs(pw - rw) / denom * 100.0
    return IndependentParseCheck(
        primary_words=pw,
        reference_words=rw,
        word_count_delta_pct=round(delta_pct, 3),
        agree=delta_pct <= tolerance_pct,
    )
