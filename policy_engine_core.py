"""
Shared deterministic Policy Engine Core.

Clause-agnostic decision model, abstention semantics, evidence/provenance,
escalation routing, negotiation ladder, directional-position resolution,
and benchmark safety metrics — everything a policy-rule engine needs that
has no idea what a "liability cap" or an "indemnification obligation" is.

A clause adapter (see liability_policy_engine.py for the first one) owns
all clause-specific work: what counts as the relevant provision in a
document, what facts to extract from it, and how to turn those facts into
one of the states defined here. This module never parses contract text and
never imports a clause adapter — the dependency runs one way.

Architecture:

    Contract -> Clause Adapter -> Structured Facts -> [this module]
             -> Decision -> Evidence -> Redline / Escalation / Audit

Extracted from liability_policy_engine.py's first working adapter rather
than designed up front — every piece here already had one real consumer
before being generalized, and the LoL adapter's benchmark results (0
false-safe, 0 false-escalation, 98.2% policy-state accuracy, 100%
determinism on the 109-case corpus) are the regression test for this
refactor: they must be exactly unchanged after extraction.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Hashable, List, Optional, Pattern, Protocol, Tuple

# ---------------------------------------------------------------------------
# Decision states — shared vocabulary across every clause type.
# ---------------------------------------------------------------------------

ACCEPT = "ACCEPT"
ACCEPT_WITH_NOTE = "ACCEPT_WITH_NOTE"
NEGOTIATE = "NEGOTIATE"
MUST_REDLINE = "MUST_REDLINE"
PROHIBITED = "PROHIBITED"
ESCALATE = "ESCALATE"
REQUIRES_REVIEW = "REQUIRES_REVIEW"
NOT_APPLICABLE = "NOT_APPLICABLE"

# Order along the negotiation ladder — REQUIRES_REVIEW and NOT_APPLICABLE
# are deliberately excluded: they mean "no ladder position was reached
# yet," not a point along it.
LADDER_ORDER = [ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, ESCALATE, PROHIBITED]


# Party-role vocabulary: which named roles conventionally sit on which
# side of a commercial contract. Genuinely clause-agnostic — a "Customer"
# is buy-side whether the clause in question is Limitation of Liability or
# Indemnification — so it lives here rather than being duplicated per
# adapter. An adapter maps a role word found in its own clause-specific
# text extraction through this vocabulary to resolve "ours vs. theirs";
# the vocabulary itself has no opinion about what kind of position the
# role holds.
BUY_SIDE_ROLES = {"customer", "client", "licensee", "buyer", "purchaser", "recipient"}
SELL_SIDE_ROLES = {"supplier", "vendor", "contractor", "licensor", "provider", "seller", "company"}

# Step 4A.9 — Step 4A.8 found indemnification's monetary-multiplier
# extraction never received this capability at all: liability supports a
# spelled-out-number-with-optional-parenthetical-numeral drafting
# convention ("one (1) times the fees paid"), which is at least as common
# in real legal drafting as bare digits, but indemnification's own
# multiplier regex only ever matched bare digits — across all 97
# indemnification cases in that corpus, zero produced a verified
# multiplier. Number parsing itself has no adapter-specific semantics (a
# spelled-out "two" means 2 whether the surrounding clause is a liability
# cap or an indemnification cap) — unlike the BASIS noun vocabulary
# (liability has purchase-price/contract-value/order-form-value basis
# words indemnification doesn't), which genuinely does differ per adapter
# and is deliberately kept adapter-local. This dict and the two helpers
# below are the shared, adapter-agnostic number-parsing primitive; each
# adapter still builds its own basis-word regex around it.
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    # Step 4A.10.5 — extended past ten: contract duration/cap language
    # routinely spells out numbers this dict didn't cover ("twelve
    # months' fees," "eighteen months," "thirty days"), and this is a
    # genuinely closed, finite set (English number words), unlike a
    # domain phrase list — extending it is not the anti-pattern this
    # program otherwise rejects.
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "sixty": 60, "ninety": 90,
}


def word_number_alternation() -> str:
    """The regex alternation fragment ('one|two|three|...') for matching a
    spelled-out multiplier number, e.g. inside
    r"\\b(" + word_number_alternation() + r")\\s*(?:\\(\\d+\\))?\\s*times?..."."""
    return "|".join(WORD_NUMBERS)


def parse_multiplier_token(token: str) -> Optional[float]:
    """Converts a matched multiplier token — either a bare digit string
    ("2", "1.5") or a spelled-out word number ("two") — to a float. Returns
    None if the token is neither (should not happen for a token captured by
    a group built from word_number_alternation() or a \\d+(?:\\.\\d+)?
    group, but kept total rather than raising for callers passing arbitrary
    text)."""
    token = token.strip().lower()
    if token in WORD_NUMBERS:
        return float(WORD_NUMBERS[token])
    try:
        return float(token)
    except ValueError:
        return None


def side_for_role(role: str) -> Optional[str]:
    role_key = role.lower()
    if role_key in BUY_SIDE_ROLES:
        return "buy_side"
    if role_key in SELL_SIDE_ROLES:
        return "sell_side"
    return None


# ---------------------------------------------------------------------------
# Document-specific role-side verification (Step 4A, hardened in 4A.1) —
# TriageCounsel counsel-audit Steps 2/2B demonstrated that side_for_role()'s
# generic vocabulary can be silently wrong: a contract is free to define
# "Vendor" as the purchaser, or "Licensee" as the party that grants the
# license, and side_for_role() has no way to know that. This does NOT
# replace side_for_role() — the generic mapping remains the baseline for
# the (overwhelming) majority of contracts that use role words
# conventionally. It adds one narrow check: does the DOCUMENT'S OWN
# definition of this specific role word use language that describes the
# opposite transactional side from the generic mapping? If so, the
# generic mapping cannot be trusted for THIS document — see
# resolve_role_side's docstring for the exact contract.
#
# Two deliberately SEPARATE questions, kept as separate regex passes
# rather than one combined pattern (4A.1 — Step 4A's PA-2 adversarial
# finding showed a narrow definitional-predicate list could silently miss
# a real definition, which is a DISCOVERY failure, not an interpretation
# failure, and conflating the two makes both harder to reason about and
# to test independently):
#
#   A. DISCOVERY — did the document define this role at all, and what is
#      the definition's body text? (_find_role_definition_body)
#   B. INTERPRETATION — does that body text contain deterministic
#      evidence of a transactional side, and does it agree or conflict
#      with the generic mapping? (_classify_directional_evidence)
#
# Still deliberately NOT a general definition-understanding engine: (A)
# recognizes a fixed, small family of explicit definitional predicates,
# and (B) a fixed, small vocabulary of buy-side vs. sell-side verbs
# within a discovered body. A definition using neither vocabulary (e.g.
# "'Vendor' means Acme Corp, a Delaware corporation") is discovered but
# carries no directional signal and is silently ignored — ordinary
# contracts, which almost never state a role's transactional function in
# their defined-terms section at all, are unaffected by this check.
# ---------------------------------------------------------------------------

# Quote characters (straight or curly) around a role/defined-term are
# optional so both "'Vendor' means" and "Vendor means" are recognized.
_ROLE_DEFINITION_QUOTE = r"[‘’'\"]?"
_CROSS_SENTENCE_EXTENSION_CHARS = 400

# A. DISCOVERY — definitional predicates. Each is a deterministic,
# grammatically explicit "this word IS a definition" signal — not an
# attempt to recognize every way a lawyer might introduce a defined term.
# Deliberately EXCLUDED: free-form patterns like "for purposes of this
# Agreement, X is ..." — "is" alone is not a reliable definitional
# predicate (most sentences using "is" are not definitions at all,
# e.g. "for purposes of this Agreement, notice is deemed given when..."),
# and admitting it would trade a discovery miss for a discovery false-
# positive flood, which is the opposite of what 4A.1 is hardening
# against. Ordered longer/more-specific alternatives first purely so the
# match consumes the most descriptive predicate available when several
# would technically fit at the same position (does not change whether a
# definition is found, only how much of it renders in error messages).
_DEFINITION_PREDICATE_FRAGMENT = (
    r"(?:means\s+and\s+includes|shall\s+be\s+construed\s+to\s+mean|shall\s+have\s+the\s+meaning"
    r"|has\s+the\s+meaning|is\s+defined\s+as|shall\s+refer\s+to|shall\s+mean|refers\s+to|means"
    # "will" is the same predicate family as "shall" (both are simply the
    # future/obligatory auxiliary a drafter chose) — not held-out-corpus
    # memorization, the same generalization already applied to "shall".
    r"|will\s+mean|will\s+refer\s+to|will\s+denote|will\s+designate)\b"
)
_DEFINITION_PREDICATE_RE = re.compile(_DEFINITION_PREDICATE_FRAGMENT, re.I)

# Step 4A.5 — a second (or later) definition of the same role is sometimes
# scoped to a particular section rather than stated plainly ("'Grower,'
# solely for purposes of Section 14 (Equipment Financing), means..."),
# putting a qualifier clause between the role name and its predicate that
# the plain anchor (role immediately followed by predicate) does not
# match. This is deliberately bounded to an explicit "for purposes of ..."
# scoping phrase — the same family already recognized as a definitional
# preamble elsewhere — not a generic "any words in between" allowance.
_SCOPED_QUALIFIER_FRAGMENT = r"(?:,?\s*(?:solely\s+)?for\s+purposes\s+of\s+[^,]{0,60},?\s*)?"

# Step 4A.5 — self-referential, externally-conditioned identity: a
# definition can make the role's actual identity depend on an external
# document not present in the text ("means the party identified as such
# in the Order Form"), with a fallback that could resolve to EITHER named
# party ("if the Order Form is silent, means Tenant Operator; if the
# Order Form so specifies, means the party OTHER THAN Tenant Operator").
# "the party other than <name>" is a generic, deterministic drafting
# construction for "whichever party that isn't" — its mere presence in a
# role's own definition means the role's identity is not fixed by the
# text at all, regardless of what directional vocabulary happens to
# appear nearby, and must never be resolved by picking one interpretation.
_PARTY_OTHER_THAN_RE = re.compile(
    r"the\s+party\s+other\s+than\b|whichever\s+party\s+is\s+not\b", re.I,
)


def _role_definition_anchor_re(role: str) -> "re.Pattern[str]":
    return re.compile(
        _ROLE_DEFINITION_QUOTE + re.escape(role) + r",?" + _ROLE_DEFINITION_QUOTE + r",?"
        + r"\s*" + _SCOPED_QUALIFIER_FRAGMENT + r"\s*" + _DEFINITION_PREDICATE_FRAGMENT,
        re.I,
    )


def _find_role_definition_body(role: str, document_text: str) -> Optional[str]:
    """Returns the defining sentence's body text (up to ~300 chars, or a
    structural boundary if found sooner) for the first explicit
    definition of `role` found anywhere in the document, or None if no
    such definitional sentence exists. Searches the WHOLE document, not a
    local window — a defined-terms section is routinely far from the
    operative clause that uses the term.

    This function answers ONLY "was a definition found, and what is its
    body" — it makes no judgment about transactional direction. See
    _classify_directional_evidence for that separate question."""
    anchor_re = _role_definition_anchor_re(role)
    m = anchor_re.search(document_text)
    if not m:
        return None
    return _extract_definition_body_at(role, document_text, m)


def _find_all_role_definition_bodies(role: str, document_text: str) -> List[str]:
    """Like _find_role_definition_body, but returns the body of EVERY
    definitional anchor for `role` found in the document, not just the
    first. Real drafting sometimes defines the same role twice with
    different scope ("'Grower' means X. 'Grower,' solely for purposes of
    Section 14, means Y.") — a caller that only ever looks at the first
    definition would silently miss that the second, differently-scoped
    definition points the opposite transactional direction. Used by
    resolve_role_side to detect that specific conflict; single-body
    callers are unaffected."""
    anchor_re = _role_definition_anchor_re(role)
    bodies = []
    for m in anchor_re.finditer(document_text):
        body = _extract_definition_body_at(role, document_text, m)
        if body:
            bodies.append(body)
    return bodies


def _extract_definition_body_at(role: str, document_text: str, m: "re.Match[str]") -> Optional[str]:
    forward = document_text[m.end():min(len(document_text), m.end() + 300)]
    # Prefer a structural boundary over the fixed 300-char cap: a
    # sentence/clause boundary, or the start of the NEXT role's own
    # definition. Several definitions are routinely joined by "and" into
    # one run-on sentence ("'Licensor' refers to ..., and 'Licensee'
    # refers to ...") with no period between them — without the second
    # boundary this role's captured body would bleed into the next
    # role's definition, corrupting the directional classification with
    # language that describes a different party entirely.
    next_definition = re.search(
        _ROLE_DEFINITION_QUOTE + r"[A-Z]\w*" + _ROLE_DEFINITION_QUOTE + r"\s+" + _DEFINITION_PREDICATE_FRAGMENT,
        forward, re.I,
    )
    sentence_boundary = re.search(r"\.\s|\.$|;", forward)
    cutoffs = [b.start() for b in (next_definition, sentence_boundary) if b is not None]
    body = forward[:min(cutoffs)] if cutoffs else forward

    # Step 4A.3 — Family E hardening: a definition body that is a BARE
    # ALIAS (just a name, no verb at all — e.g. "'Vendor' means Beta
    # Inc.") carries no content to interpret on its own, but real
    # drafting routinely states the alias in one sentence and the actual
    # directional content in the NEXT one ("'Vendor' means Beta Inc.
    # Beta Inc. is the party that purchases..."). When the captured body
    # has no verb-shaped word at all, extend the search one sentence
    # further and, if that next sentence's subject is the SAME alias
    # just established, fold it in — otherwise leave the body as-is
    # (a short alias with an unrelated following sentence is not this
    # pattern, and must not pull in unrelated text).
    if body and cutoffs and not _RELATIONAL_VERB_TOKEN_RE.search(body):
        alias = body.strip().rstrip(".;").strip()
        alias_words = alias.split()
        # Only treat this as a bare-alias name if it looks like a short
        # proper-noun phrase (1-4 capitalized-ish tokens), not an
        # arbitrary truncated clause.
        if 1 <= len(alias_words) <= 4 and re.match(r"^[A-Z]", alias):
            next_start = min(cutoffs) + (2 if forward[min(cutoffs):min(cutoffs) + 1] == "." else 1)
            remainder = forward[next_start:]
            alias_subject_re = re.compile(r"^\s*" + re.escape(alias) + r"\.?\s+(?:is|are|shall\s+be)\b", re.I)
            am = alias_subject_re.match(remainder)
            if am:
                next_boundary = re.search(r"\.\s|\.$|;", remainder[am.end():])
                extra_end = am.end() + (next_boundary.start() if next_boundary else len(remainder) - am.end())
                body = body + ". " + remainder[:extra_end]

    # Step 4A.5 — broader cross-sentence extension: a definitional
    # sentence can be purely descriptive ("means the party responsible
    # for performing the work described in Exhibit B") or a bare alias
    # repeated as the next sentence's own subject ("'Staffing Agency'
    # refers to Beta LLC. Staffing Agency is in the business of
    # supplying..."), with the actual directional evidence appearing in
    # a LATER sentence that mentions the role's own name again (as
    # subject or object). The alias-specific extension above only covers
    # a short 1-4-word alias body with no verb at all; this covers the
    # general case: whenever the body found so far carries no recognized
    # buy/sell evidence, extend forward (bounded) to the next sentence
    # that mentions the role's OWN name again and fold it in. Anchoring
    # to a literal re-mention of the role (not just "the next sentence")
    # is what makes this safe — an unrelated following sentence that
    # never names the role again is left alone.
    if body and _classify_directional_evidence(body) is None:
        tail_start = m.end() + len(body)
        tail = document_text[tail_start:min(len(document_text), tail_start + _CROSS_SENTENCE_EXTENSION_CHARS)]
        role_mention = re.search(_ROLE_DEFINITION_QUOTE + re.escape(role) + _ROLE_DEFINITION_QUOTE, tail, re.I)
        # Step 4A.5 Priority 4 (anti-false-safe correction): a NEW numbered
        # section heading ("9. Limitation of Liability.") between the
        # definitional sentence and the role re-mention means that
        # re-mention is the OPERATIVE clause using the role, not a
        # continuation of its definition — folding it in pulled in the
        # heading text itself as spurious "relational content" and
        # produced unnecessary review on ordinary corporate-identity
        # definitions ("'Vendor' means Acme Corporation, a Delaware
        # corporation.") that have no directional content to find at all.
        # Only extend within the SAME section.
        if role_mention:
            section_heading = re.search(r"\n\s*\n\s*\d+[.)]\s+[A-Z]", tail[:role_mention.start()])
            if section_heading:
                role_mention = None
        if role_mention:
            sentence_end = re.search(r"\.\s|\.$|;", tail[role_mention.end():])
            extra_end = role_mention.end() + (sentence_end.start() if sentence_end else len(tail) - role_mention.end())
            body = body + ". " + tail[:extra_end]
    return body


# B. INTERPRETATION — directional evidence vocabulary. Deliberately a
# SMALL, drafting-pattern-justified list (see benchmarks/liability_corpus.py,
# indemnification_corpus.py, payment_terms_corpus.py and the adversarial
# suites in tests/ for the actual buy/sell verb patterns real contracts in
# this corpus use), not an exhaustive synonym dictionary — an unmatched
# definition body is a legitimate, common, UNKNOWN outcome (see
# resolve_role_side), not a gap to keep patching.
#
# Every stem below is restricted to explicit VERB-INFLECTION suffixes
# (-s/-es/-ing/-ed, or an irregular past tense) rather than a bare `\w*`
# wildcard. This is a structural fix, not example-tuning (found via the
# role-resolution verifier benchmark, not by patching a single failing
# sentence): `\w*` after a verb stem also matches that stem's AGENT NOUN
# — "buy\w*" matches "Buyer", "provid\w*" matches "Provider",
# "purchas\w*" matches "Purchaser", "sell\w*" matches "Seller",
# "suppl\w*" matches "Supplier" — i.e. it matches the ROLE NAME itself
# whenever the defined term or another party in the same sentence happens
# to share a stem with the verb vocabulary, which is common (a sentence
# defining "Reseller" that also mentions "Provider" would otherwise
# register sell-side evidence purely because the word "Provider" appeared
# as someone else's name, not because any verb was used). Restricting to
# verb-inflection suffixes closes this whole class of false positive at
# once, rather than special-casing each specific agent noun.
_DIRECTIONAL_BUY_EVIDENCE_RE = re.compile(
    r"\bpurchas(?:e|es|ing|ed)\b|\bbuy(?:s|ing)?\b|\bbought\b|\bpay(?:s|ing)?\s+for\b"
    r"|\bprocur(?:e|es|ing|ed)\b|\bacquir(?:e|es|ing|ed)\b"
    r"|\breceiv(?:e|es|ing|ed)\s+(?:a|the)\s+license\b"
    r"|\breceiv(?:e|es|ing|ed)\s+(?:the\s+)?services?\s+from\b"
    r"|\bsubscrib(?:e|es|ing|ed)\b|\border(?:s|ing|ed)?\s+(?:the\s+)?(?:goods|services)\b"
    r"|\bobtain(?:s|ing|ed)?\s+(?:the\s+)?services?\s+from\b|\bcustomer\s+of\b"
    r"|\bengag(?:e|es|ing|ed)\b.{0,25}?\bservices?\b"
    r"|\bcommission(?:s|ing|ed)?\b|\bsourc(?:e|es|ing|ed)\s+(?:the\s+)?\w+\s+from\b"
    r"|\bobtain(?:s|ing|ed)?\s+the\s+benefit\s+of\b|\bcompensat(?:e|es|ing|ed)\b"
    r"|\bleas(?:e|es|ing|ed)\b.{0,30}?\bfrom\b",
    re.I,
)
_DIRECTIONAL_SELL_EVIDENCE_RE = re.compile(
    # "licens(e|es|ing|ed) to" is deliberately excluded: "a license to
    # use the Platform" (an infinitive following the noun "license") is
    # the BUYER's side of a license grant, not the grantor's — only
    # "licenses the ..." / "licenses out ..." (the licensor actively
    # licensing something) counts as sell-side signal here; a licensor
    # granting TO someone is separately covered by "grant... license"
    # below. "licenses the X FROM Y" is excluded via a negative lookahead
    # below it — that phrasing is the BUYER receiving a license from a
    # grantor, not the licensor's own conduct, even though it matches
    # "licenses the" on its face.
    r"\bprovid(?:e|es|ing|ed)\b|\bdevelop(?:s|ing|ed)?\b|\b(?:re)?sell(?:s|ing)?\b|\b(?:re)?sold\b"
    r"|\blicens(?:e|es|ing|ed)\s+(?:the|out)\b(?!.{0,30}?\bfrom\b)"
    r"|\bgrant(?:s|ing|ed)?\s+(?:a\s+|the\s+)?license\b|\bsuppl(?:y|ies|ying|ied)\b"
    r"|\bdeliver(?:s|ing|ed)?\b|\bfurnish(?:es|ing|ed)?\b"
    r"|\bdeliver(?:s|ing|ed)?\s+services?\s+to\b|\bcreat(?:e|es|ing|ed)\b|\bmanufactur(?:e|es|ing|ed)\b"
    r"|\brender(?:s|ing|ed)?\b.{0,50}?\bto\b|\bperform(?:s|ing|ed)?\b.{0,35}?\bfor\b"
    r"|\bmak(?:e|es|ing)\b.{0,20}?\bavailable\s+to\b|\bleas(?:e|es|ing|ed)\b.{0,30}?\bto\b",
    re.I,
)


# Step 4A.3 — Failure Family 1 hardening. Step 4A.2's held-out corpus
# demonstrated that when a document redefines a role using a predicate
# OUTSIDE _DEFINITION_PREDICATE_FRAGMENT ("is understood to mean", "for
# purposes hereof, X is...", "will denote", "shall carry the meaning of",
# etc.), _find_role_definition_body finds nothing, and resolve_role_side
# silently falls back to the generic mapping — producing a genuine S4
# false-safe (PAY-A2-02) and several liability/indemnification WCs.
#
# The fix is NOT to add those specific phrases to the interpretable
# predicate list (that only memorizes the held-out corpus and leaves the
# same gap for the next unrecognized phrase). Instead: a SEPARATE,
# broader, purely-detection-only signal answers a narrower question than
# "what does this definition mean" — it answers "does document-specific
# semantic content about this role appear to exist at all". When that
# broader signal fires but the narrow, interpretable pipeline found
# nothing, the caller must not use the generic mapping — it must return
# UNRESOLVED (side=None, reason=...), the same shape as a detected
# CONFLICT, so callers need no new branch.
#
# The broader signal is still bounded and justified, not a general
# language model of "sounds like a definition": it fires only when a
# (possibly quoted) role term is closely followed by one of a wider
# family of copular/definitional verbs, OR when an explicit "for
# purposes hereof / of this Agreement / as used herein" preamble
# precedes a bare copula ("is"/"are"/"shall be") — the preamble is what
# makes a bare copula safe to treat as definitional; a bare "is"
# anywhere in a contract is NOT itself a signal (that would explode into
# matching ordinary sentences having nothing to do with role definition).
_DEFINITIONAL_PREAMBLE_FRAGMENT = r"(?:for\s+purposes\s+(?:hereof|of\s+this\s+agreement)|as\s+used\s+(?:herein|in\s+this\s+agreement))\s*,?\s*"
_BROAD_DEFINITION_VERB_FRAGMENT = (
    r"(?:means?\b|denotes?\b|designates?\b|constitutes?\b"
    r"|will\s+(?:mean|refer\s+to|denote|designate|constitute)\b"
    r"|shall\s+(?:mean|refer\s+to|denote|designate|constitute|be\s+construed|be\s+treated|carry\s+the\s+meaning|have\s+the\s+meaning)\b"
    r"|refers?\s+to\b|is\s+(?:understood|construed|deemed|defined)\b|are\s+(?:understood|construed|deemed|defined)\b"
    r"|has\s+the\s+meaning\b)"
)
_BROAD_DEFINITION_QUOTED_RE_TEMPLATE = _ROLE_DEFINITION_QUOTE + "{role}" + _ROLE_DEFINITION_QUOTE + r"\s+" + _BROAD_DEFINITION_VERB_FRAGMENT
_BROAD_DEFINITION_PREAMBLE_RE_TEMPLATE = (
    _DEFINITIONAL_PREAMBLE_FRAGMENT + _ROLE_DEFINITION_QUOTE + "{role}" + _ROLE_DEFINITION_QUOTE
    + r"\s+(?:is|are|shall\s+be)\b"
)


_REFERENCES_TO_RE_TEMPLATE = (
    r"references?\s+to\s+" + _ROLE_DEFINITION_QUOTE + "{role}" + _ROLE_DEFINITION_QUOTE
    + r"\s+(?:are|is|shall\s+be)\s+references?\s+to\b"
)


def _has_broad_definition_signal(role: str, document_text: str) -> bool:
    """Detection-only (never interpretation): does document-specific
    language ABOUT this specific role's meaning appear to exist,
    independent of whether it uses one of the narrow, confidently-
    interpretable predicates? True does not mean the definition was
    understood — it means generic vocabulary must not be trusted
    silently."""
    escaped = re.escape(role)
    if re.search(_BROAD_DEFINITION_QUOTED_RE_TEMPLATE.format(role=escaped), document_text, re.I):
        return True
    if re.search(_BROAD_DEFINITION_PREAMBLE_RE_TEMPLATE.format(role=escaped), document_text, re.I):
        return True
    if re.search(_REFERENCES_TO_RE_TEMPLATE.format(role=escaped), document_text, re.I):
        return True
    return False


# Failure Family 1, second gap: even when the narrow predicate IS found
# (discovery succeeds), the body can contain a genuine relational verb
# about another party that simply isn't in _DIRECTIONAL_*_EVIDENCE_RE's
# small vocabulary (Step 4A.2's LOL-B2-02: "'Vendor' means Acme Corp,
# the entity that RETAINS Customer's manufacturing capacity..." — "means"
# is recognized, but "retains" is not, and the body plainly relates
# Vendor to a second named party). Rather than expanding the verb
# vocabulary indefinitely (which only ever covers today's known
# examples), detect the STRUCTURAL shape of "this body relates the role
# to another capitalized party via some verb" and treat an unrecognized
# instance of that shape as unresolved rather than silently signal-free.
_RELATIONAL_VERB_STOPWORDS = frozenset({
    "is", "are", "was", "were", "means", "mean", "meaning", "refers", "referring",
    "has", "have", "having", "had", "being", "shall", "will", "hereby",
})
_RELATIONAL_VERB_TOKEN_RE = re.compile(r"\b([a-z]+(?:s|es|ed|ing))\b", re.I)
_SECOND_ROLE_TOKEN_RE = re.compile(r"\b[A-Z][a-z]{2,25}\b")
_BYSTANDER_BOILERPLATE_RE = re.compile(
    r"together\s+with\s+its\s+successors\s+and\s+(?:permitted\s+)?assigns"
    r"|its\s+successors\s+and\s+(?:permitted\s+)?assigns"
    r"|together\s+with\s+its\s+wholly[\s-]owned\s+subsidiaries(?:\s+and\s+any\s+Affiliate[s]?(?:\s+performing\s+services\s+hereunder)?)?"
    r"|the\s+party\s+identified\s+as\s+[‘’'\"]?[A-Z][A-Za-z]{2,25}[‘’'\"]?\s+on\s+the\s+signature\s+page\s+hereto"
    # Jurisdiction-of-formation/incorporation boilerplate: "a Delaware
    # corporation", "formed under the laws of the State of Colorado" —
    # states WHERE the entity was formed, not its transactional role.
    r"|(?:formed|organized|incorporated)\s+(?:under\s+the\s+laws\s+of\s+|in\s+)(?:the\s+State\s+of\s+)?[A-Z][a-z]+"
    r"|qualified\s+to\s+do\s+business\s+in\s+[A-Z][a-z]+"
    r"|and\s+includes\s+its\s+[a-z-]+(?:\s+and\s+[a-z-]+)?\s+acting\s+in\s+their\s+capacity\s+as\s+such"
    r"|a\s+[A-Z][a-z]+\s+(?:corporation|partnership|limited\s+liability\s+company|limited\s+partnership|agricultural\s+cooperative)\b"
    # Step 4A.5 Priority 4: a passive-voice clause ("which was acquired
    # last year by Meridian Financial Holdings", "licensed by the State
    # Insurance Commissioner") attributes the action to whatever follows
    # "by", not to the role whose definition is being scanned — the same
    # bystander principle _is_bystander_verb_match already applies to the
    # buy/sell-vocabulary check, generalized here for the broader
    # unrecognized-relational-content scan too.
    r"|\b[a-z]+(?:ed|en)\s+(?:[a-z]+\s+){0,3}by\s+(?:the\s+)?[A-Z][A-Za-z]{2,25}(?:\s+[A-Z][A-Za-z]{2,25}){0,3}"
    # Regulatory-oversight boilerplate ("subject to solvency regulation
    # by the Commissioner") — a THIRD PARTY (regulator) regulating the
    # role, not the role's own transactional conduct.
    r"|subject\s+to\s+[a-z]+\s+regulation\s+by\s+(?:that\s+|the\s+)?[A-Z][A-Za-z]{2,25}(?:\s+[A-Z][A-Za-z]{2,25}){0,2}"
    # Notice-address boilerplate ("notices to which shall be sent to
    # Vendor's Legal Department at the address in Exhibit B") — states
    # WHERE to send administrative notices, not the role's transactional
    # direction.
    r"|notices?\s+to\s+which\s+shall\s+be\s+sent\s+to\s+[^.]{0,60}"
    # Cross-reference to an external ORDERING/execution document ("the
    # entity identified in the Order Form", "the party described in the
    # Slip") — the document name is not a second party.
    r"|(?:identified|described)\s+in\s+the\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?",
    re.I,
)


def _has_unrecognized_relational_content(definition_body: str, role: str) -> bool:
    """True when the body contains BOTH a verb-shaped word outside the
    small stopword list AND a second capitalized term distinct from
    `role` — i.e. the body plausibly relates this role to another named
    party through some action, even though _classify_directional_evidence
    found no recognized buy/sell vocabulary in it."""
    # Step 4A.5 Priority 4 (FE Family 2 — bystander corporate boilerplate):
    # entity-identity boilerplate ("together with its successors and
    # permitted assigns", "wholly owned subsidiaries and any Affiliate
    # performing services hereunder", "identified as 'X' on the signature
    # page hereto") states corporate FORM/GROUP facts, not the role's own
    # transactional direction — it is never itself evidence the role's
    # generic classification might be wrong. Stripped before the
    # relational-content scan so it can't supply the "second capitalized
    # term" or "verb" that would otherwise trigger unnecessary review;
    # any OTHER relational language in the same body (a genuine buy/sell
    # verb, an unrecognized-but-real relation to another named party) is
    # untouched and still detected normally.
    definition_body = _BYSTANDER_BOILERPLATE_RE.sub(" ", definition_body)
    has_verb = False
    for m in _RELATIONAL_VERB_TOKEN_RE.finditer(definition_body):
        if m.group(1).lower() not in _RELATIONAL_VERB_STOPWORDS:
            has_verb = True
            break
    if not has_verb:
        return False
    role_key = role.lower()
    # Step 4A.5 Priority 4: a definition's own leading entity name
    # ("Ridgeline Materials Group, a general partnership...") is commonly
    # a multi-word legal name containing ordinary capitalized common
    # nouns ("Materials", "Group", "Holdings", "Partners") — these are
    # part of the SAME role's own identity, not a second, different
    # party, and must not by themselves count as relating the role to
    # someone else. Only the leading capitalized run up to the first
    # comma is treated this way (the entity's own stated name); a
    # capitalized term appearing LATER in the body, after a comma, is
    # still eligible to be a genuine second party.
    own_name_run = re.match(
        r"\s*(?:[A-Z][A-Za-z.&]*\s*)+(?:,\s*(?:Inc|LLC|L\.L\.C|Corp|Ltd|L\.P|LLP)\.?\s*)?",
        definition_body,
    )
    own_name_tokens = (
        {t.strip(".,").lower() for t in own_name_run.group(0).split()} if own_name_run else set()
    )
    for m in _SECOND_ROLE_TOKEN_RE.finditer(definition_body):
        token = m.group(0).lower()
        if token != role_key and token not in own_name_tokens and token not in {"the", "and", "this", "that", "which", "who"}:
            return True
    return False


# A -ing verb form immediately preceded by a possessive ("Customer's
# manufacturing capacity", "its purchasing power") is a nominalized/
# adjectival gerund heading a noun phrase, not a verb describing the
# discovered role's own conduct — the possessive's OWNER is the one
# "doing" it grammatically, and here the owner is a bystander (a
# different party's capacity/power/etc.), not the role being classified.
# A plain "-ing" gerund with a direct object and no preceding possessive
# ("the entity purchasing the Deliverables") is unaffected and still
# counts, since that IS the role's own conduct.
_POSSESSIVE_GERUND_GUARD_RE = re.compile(r"(?:'s|s')\s*$|\b(?:its|their|his|her|our|your)\s*$", re.I)
_GERUND_MATCH_CHARS = 25
# A verb match immediately followed by a passive-voice agent phrase
# ("goods manufactured BY Seller") attributes the action to whatever
# follows "by", not to the role whose definition body is being scanned —
# same bystander principle as the possessive-gerund guard above, just for
# passive voice instead of a nominalized gerund.
_PASSIVE_AGENT_GUARD_RE = re.compile(r"^\s*(?:[a-z]+\s+){0,3}by\b", re.I)
_PASSIVE_AGENT_LOOKAHEAD_CHARS = 25


_ADMINISTRATIVE_OBJECT_RE = re.compile(
    r"^\s*(?:the\s+)?(?:data|information|documentation|records?)\b", re.I,
)

# Case-SENSITIVE on purpose: "to end-user subscribers"/"to customers" (a
# lowercase, generic, unnamed class of downstream third parties) is a
# bystander recipient, but "to Client"/"to Customer" (capitalized) is
# almost always THIS document's own defined role name for the actual
# counterparty — filtering that too would silently discard genuine
# sell-side evidence about the real contractual relationship, an
# opposite-direction false-safe this must not create.
_DOWNSTREAM_GENERIC_RECIPIENT_RE = re.compile(
    r"\bto\s+(?:end[\s-]user\s+)?(?:subscribers?|customers?|clients?|consumers?|shippers?|users?)\b",
)
_LOOKAHEAD_OBJECT_CHARS = 30


def _is_bystander_verb_match(definition_body: str, match: "re.Match[str]") -> bool:
    word = match.group(0)
    if re.search(r"ing\b", word, re.I):
        lookbehind = definition_body[max(0, match.start() - _GERUND_MATCH_CHARS):match.start()]
        if _POSSESSIVE_GERUND_GUARD_RE.search(lookbehind):
            return True
    lookahead = definition_body[match.end():match.end() + _PASSIVE_AGENT_LOOKAHEAD_CHARS]
    if _PASSIVE_AGENT_GUARD_RE.search(lookahead):
        return True
    # Step 4A.5 Priority 4 (FE Family 2 — bystander corporate/administrative
    # content): "provided the data ... for account-verification purposes"
    # describes an administrative disclosure, not a commercial buy/sell
    # transaction, even though "provide(d)" matches the sell-side verb
    # vocabulary on its face — the OBJECT being provided is data/
    # information/documentation/records, not a service or goods.
    object_lookahead = definition_body[match.end():match.end() + _LOOKAHEAD_OBJECT_CHARS]
    if _ADMINISTRATIVE_OBJECT_RE.search(object_lookahead):
        return True
    # A sell-side verb whose recipient ("to end-user subscribers"/"to
    # customers") is a generic, lowercase, unnamed downstream class of
    # third parties describes the role's own separate business model with
    # OTHER people, not its relationship to the document's actual named
    # counterparty — a reseller's downstream resale to its own customers
    # is a bystander fact here, distinct from "resells...to Acme Corp"
    # (a specific named party, which is NOT filtered by this check).
    if _DOWNSTREAM_GENERIC_RECIPIENT_RE.search(definition_body[match.end():match.end() + _LOOKAHEAD_OBJECT_CHARS + 20]):
        return True
    return False


def _classify_directional_evidence(definition_body: str) -> Optional[str]:
    """Returns "buy_side", "sell_side", "mixed", or None (no directional
    evidence at all) from a discovered definition body — pure
    interpretation, no discovery logic. "mixed" is returned, not
    resolved, when both vocabularies match: a definition using both
    purchasing and providing/selling language about the SAME role does
    not cleanly settle the question either way (see resolve_role_side)."""
    has_buy = any(
        not _is_bystander_verb_match(definition_body, m)
        for m in _DIRECTIONAL_BUY_EVIDENCE_RE.finditer(definition_body)
    )
    has_sell = any(
        not _is_bystander_verb_match(definition_body, m)
        for m in _DIRECTIONAL_SELL_EVIDENCE_RE.finditer(definition_body)
    )
    if has_buy and has_sell:
        return "mixed"
    if has_buy:
        return "buy_side"
    if has_sell:
        return "sell_side"
    return None


# A definition body that is a BARE cross-reference to another quoted
# defined term ("given to 'Purchaser' in Schedule A", "the meaning of
# 'Buyer'") carries no directional verb of its own — _classify_directional_
# evidence correctly returns None for it. Rather than treat that as
# non-directional ("means Acme Corp, a Delaware corporation" — UNKNOWN,
# safe to fall back), follow the ONE hop to the referenced term: if THAT
# term is itself defined elsewhere in the document with real directional
# evidence, that evidence genuinely describes the original role (they are
# the same entity by definition) and is safe to use. If the referenced
# term isn't found or is itself non-directional, this returns None and the
# caller falls through to its existing UNKNOWN/escalation handling — no
# multi-hop chasing beyond one level.
_INDIRECT_DEFINITION_REF_RE = re.compile(
    r"(?:given\s+to|meaning\s+of|same\s+meaning\s+as)\s+"
    + _ROLE_DEFINITION_QUOTE + r"([A-Z][A-Za-z]{2,25})" + _ROLE_DEFINITION_QUOTE,
    re.I,
)


def _resolve_indirect_definition_side(definition_body: str, role: str, document_text: str) -> Optional[str]:
    im = _INDIRECT_DEFINITION_REF_RE.search(definition_body)
    if not im:
        return None
    ref_role = im.group(1)
    if ref_role.lower() == role.lower():
        return None
    ref_body = _find_role_definition_body(ref_role, document_text)
    if not ref_body:
        return None
    return _classify_directional_evidence(ref_body)


def resolve_role_side(role: str, document_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns (side, conflict_reason). `side` is None exactly when
    `conflict_reason` is not None — a caller must never use a non-None
    side alongside a non-None reason.

    Composes discovery (_find_role_definition_body) and interpretation
    (_classify_directional_evidence) into four conceptual outcomes:

      - NO_DEFINITION (no definitional sentence found for this role
        anywhere in the document): returns (generic_side, None).
      - CONSISTENT (a definition was found and its directional evidence
        agrees with the generic mapping): returns (generic_side, None).
      - UNKNOWN (a definition was found but carries no directional
        evidence at all — e.g. "'Vendor' means Acme Corp, a Delaware
        corporation"): returns (generic_side, None). A definition merely
        existing is not itself suspicious; the overwhelming majority of
        defined-terms sections define a role's legal NAME, not its
        transactional function, and must not become a source of
        unnecessary escalation.
      - CONFLICT (a definition was found whose directional evidence
        points EXCLUSIVELY to the side OPPOSITE the generic mapping, or
        whose evidence is "mixed" — matches both vocabularies and so
        does not cleanly settle the question either way): returns
        (None, reason) — the caller must not guess between the generic
        mapping and the document's own language; it must route to
        unresolved/REQUIRES_REVIEW instead.
    """
    generic_side = side_for_role(role)

    # Step 4A.5 — multiple, differently-scoped definitions: some drafting
    # defines the same role twice, once generally and once with a scope
    # qualifier ("'Grower' means X. 'Grower,' solely for purposes of
    # Section 14, means Y."). Looking at only the first definition would
    # silently miss that a later, differently-scoped definition points
    # the opposite transactional direction. If two or more definitions
    # exist with directional evidence and they disagree, this is a
    # genuine, deterministically-detectable conflict — never guess which
    # scope governs the clause being evaluated.
    all_bodies = _find_all_role_definition_bodies(role, document_text)
    if any(_PARTY_OTHER_THAN_RE.search(b) for b in all_bodies):
        return None, (
            f"the document's own definition of '{role}' makes its identity depend on which party is "
            f"NOT some other named party (\"the party other than ...\") — '{role}''s actual identity "
            f"cannot be determined from the text alone"
        )
    distinct_sides = {
        s for s in (_classify_directional_evidence(b) for b in all_bodies)
        if s is not None
    }
    if len(distinct_sides) > 1:
        return None, (
            f"the document contains multiple definitions of '{role}' with conflicting directional "
            f"evidence (one or more scoped to a specific section) — cannot determine which definition "
            f"governs the clause being evaluated"
        )

    definition_body = _find_role_definition_body(role, document_text)
    if not definition_body:
        if _has_broad_definition_signal(role, document_text):
            # DOCUMENT_DEFINITION_UNRESOLVED (Step 4A.3): document-specific
            # language about this role appears to exist, but not through a
            # predicate our interpretable pipeline recognizes — the generic
            # mapping must not be trusted silently.
            return None, (
                f"the document appears to define or recharacterize the role of '{role}' using "
                f"language this system does not confidently recognize — cannot safely confirm "
                f"whether '{role}''s conventional classification still applies"
            )
        return generic_side, None  # NO_DOCUMENT_OVERRIDE

    definition_side = _classify_directional_evidence(definition_body)
    if definition_side is None:
        indirect_side = _resolve_indirect_definition_side(definition_body, role, document_text)
        if indirect_side is not None:
            definition_side = indirect_side
    if definition_side is None:
        if _has_unrecognized_relational_content(definition_body, role):
            # DOCUMENT_DEFINITION_UNRESOLVED: a definition was found and IS
            # interpretable-in-principle, but its body relates '{role}' to
            # another named party through a verb outside the recognized
            # buy/sell vocabulary — do not assume this is safely
            # non-directional the way "means Acme Corp, a Delaware
            # corporation" is.
            return None, (
                f"the document's own definition of '{role}' relates it to another party through "
                f"language this system does not confidently classify as buy-side or sell-side — "
                f"cannot safely confirm whether '{role}''s conventional classification still applies"
            )
        return generic_side, None  # UNKNOWN — definition found, no directional evidence at all
    if definition_side == "mixed":
        return None, (
            f"the document's own definition of '{role}' uses both purchasing/receiving language "
            f"and providing/selling language — cannot determine which transactional side '{role}' "
            f"actually occupies"
        )
    if generic_side is not None and definition_side != generic_side:
        return None, (
            f"the document's own definition of '{role}' uses "
            f"{'purchasing/receiving' if definition_side == 'buy_side' else 'providing/selling'} language, "
            f"which conflicts with '{role}''s conventional "
            f"{'buy-side' if generic_side == 'buy_side' else 'sell-side'} classification"
        )
    return definition_side, None  # CONSISTENT


# ---------------------------------------------------------------------------
# Pure text utilities — no clause semantics, byte-identical across every
# adapter before promotion (see benchmarks/duplication_promotion_review.md,
# section 9a). Promoted because there was nothing adapter-specific left to
# parameterize: every adapter, including Governing Law (the negative
# control with no directionality and almost no windowing machinery at all),
# used the exact same implementation.
# ---------------------------------------------------------------------------

def excerpt(text: str, start: int, end: int, pad: int = 60) -> str:
    """Word-boundary-trimmed excerpt around [start, end), for human-readable
    evidence quotes — never cuts a word in half at the pad boundary."""
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    if lo > 0:
        space = text.rfind(" ", 0, lo)
        if space != -1:
            lo = space + 1
    if hi < len(text):
        space = text.find(" ", hi)
        if space != -1:
            hi = space
    return text[lo:hi].strip()


def section_label_before(text: str, anchor_start: int, lookback: int = 30) -> Optional[str]:
    """The last 1-3 digit (optionally decimal, e.g. "12.4") number found in
    the `lookback` characters before `anchor_start` — used to label
    "Section 12" from an anchor match's position. Returns None if no such
    number precedes the anchor within range."""
    look = text[max(0, anchor_start - lookback):anchor_start]
    nums = re.findall(r"\d{1,3}(?:\.\d{1,2})?", look)
    return nums[-1] if nums else None


# ---------------------------------------------------------------------------
# Step 4A.11 — Cross-Reference Resolution (SOURCE -> REFERENCE -> TARGET ->
# CONCEPT -> VALUE). Shared, adapter-agnostic infrastructure: locating a
# document DIVISION (Section/Schedule/Exhibit/Appendix/Annex/Article N) and
# extracting its body text once a reference to it is found. What the body
# means (is this actually a monetary cap? a liability limit? a payment
# term?) is adapter-specific and lives in each adapter's own module — this
# primitive only answers "where is the target division, and what text does
# it contain," never "what does that text establish." A cross-reference
# resolver built on this must still independently verify the CONCEPT and
# extract the VALUE from the returned body; finding a body is not itself
# evidence of anything material.
# ---------------------------------------------------------------------------

_DIVISION_KIND_ALTERNATION = r"Section|Schedule|Exhibit|Appendix|Annex|Article"
_DIVISION_IDENTIFIER_FRAGMENT = r"[0-9]+(?:\.[0-9]+)*|[A-Z]\b"
# A REFERENCE: some connector phrase (structural set, not exhaustive prose)
# followed, within a bounded span of non-sentence-ending characters, by a
# division label. The gap between connector and label is matched lazily and
# WITHOUT constraining what nouns may appear there ("the cap set forth in,"
# "the limitation of liability described in," "the applicable ceiling
# specified in," ...) — bounding the STRUCTURE (connector ... label, same
# sentence) generalizes across drafting styles without enumerating the
# possible intervening descriptive phrases, the same structural-over-
# lexical principle used throughout the Step 4A.10.x symmetry work.
CROSS_REFERENCE_RE = re.compile(
    r"(?:subject\s+to|as\s+set\s+forth\s+in|set\s+forth\s+in|pursuant\s+to|"
    r"except\s+as\s+provided\s+in|in\s+accordance\s+with|as\s+described\s+in|"
    r"as\s+specified\s+in|as\s+provided\s+in|as\s+limited\s+by)"
    r"(?:(?!\.)[^.]){0,60}?\b(" + _DIVISION_KIND_ALTERNATION + r")\s+(" + _DIVISION_IDENTIFIER_FRAGMENT + r")",
    re.I,
)
# A CROSS_REFERENCE_RE match only describes a genuine DELEGATION to the
# referenced provision — the two structural shapes that break that
# assumption, found by regression during Step 4A.11 development:
#
# 1. The connector itself is negated ("shall not be subject to the cap
#    set forth in Section 9") — this states the OPPOSITE of delegation,
#    an explicit carve-OUT from the referenced provision, not a
#    reference to its value.
# 2. The reference sits inside a "notwithstanding" clause ("Notwithstanding
#    the limitation of liability set forth in Section 9, ...") — this is an
#    OVERRIDE signal: the sentence goes on to state its own value despite
#    the referenced provision, not to adopt it.
#
# Both are grammatical scoping relationships (what governs the connector),
# not new connector phrases to enumerate — checking them keeps the
# connector list itself general while not mistaking negation/override
# prose for delegation prose.
_CROSS_REFERENCE_NEGATION_RE = re.compile(
    r"\b(?:not|no\s+longer|shall\s+not|will\s+not|does\s+not|is\s+not|are\s+not)\s+"
    r"(?:otherwise\s+)?(?:be\s+)?$",
    re.I,
)
_CROSS_REFERENCE_OVERRIDE_RE = re.compile(r"\bnotwithstanding\b", re.I)


def cross_reference_is_delegation(text: str, match: "re.Match[str]") -> bool:
    """False when a CROSS_REFERENCE_RE match is negated or sits inside a
    "notwithstanding" override clause — see the comment above. Callers
    should treat a non-delegating match the same as no match at all."""
    preceding = text[max(0, match.start() - 40):match.start()]
    if _CROSS_REFERENCE_NEGATION_RE.search(preceding):
        return False
    clause_start = max(
        text.rfind(".", 0, match.start()),
        text.rfind(";", 0, match.start()),
        text.rfind("\n", 0, match.start()),
    )
    clause = text[clause_start + 1:match.start()]
    if _CROSS_REFERENCE_OVERRIDE_RE.search(clause):
        return False
    return True


def find_delegating_cross_reference(text: str) -> Optional["re.Match[str]"]:
    """First CROSS_REFERENCE_RE match in `text` that actually describes a
    delegation (see `cross_reference_is_delegation`) — skips negated or
    "notwithstanding"-overridden matches rather than stopping at the first
    connector occurrence regardless of its grammatical scope."""
    for m in CROSS_REFERENCE_RE.finditer(text):
        if cross_reference_is_delegation(text, m):
            return m
    return None


# A HEADING occurrence of a division label — distinguished from a mere
# INLINE reference to it by requiring the label sit at a sentence/paragraph
# boundary (start of text, a newline, or immediately after ". "). This is
# what makes target-lookup structural rather than "find the number
# anywhere": an inline mention ("as capped by Section 9") must never be
# mistaken for Section 9's own heading. The kind word is OPTIONAL for a
# purely numeric identifier ("9. Indemnification Cap." is exactly as common
# in real drafting as "Section 9. Indemnification Cap.") — but required for
# a letter identifier, since a bare capital letter at a sentence boundary
# ("A. This is...") is an ordinary enumerated list item far more often than
# a genuine "Exhibit A"-style heading, and the kind word is what
# distinguishes the two structurally.
_DIVISION_HEADING_RE = re.compile(
    r"(?:\A|\n|\.\s{1,3})\s*(?:(" + _DIVISION_KIND_ALTERNATION + r")\s+([0-9]+(?:\.[0-9]+)*|[A-Z])"
    r"|([0-9]+(?:\.[0-9]+)*))\b\.?[:\-–—]?",
    re.I,
)


def _division_heading_kind_identifier(m: "re.Match[str]") -> Tuple[str, str]:
    """Normalizes a _DIVISION_HEADING_RE match into (kind, identifier),
    treating a bare numeric heading with no kind word as an implicit
    "Section" (see the regex comment above for why letter identifiers
    don't get the same treatment)."""
    if m.group(1):
        return m.group(1), m.group(2)
    return "Section", m.group(3)


@dataclass
class TargetLookupResult:
    status: str  # "FOUND" | "NOT_FOUND" | "AMBIGUOUS"
    body: Optional[str] = None
    match_start: Optional[int] = None
    note: str = ""


def locate_target_provision(full_text: str, kind: str, identifier: str, max_chars: int = 1500) -> TargetLookupResult:
    """Finds the HEADING occurrence of `<kind> <identifier>` (e.g. "Section
    9", "Schedule 3") in `full_text` and returns the body text that follows
    it, up to the next division-heading-shaped boundary (of ANY kind/
    identifier) or `max_chars`, whichever comes first — a structural
    boundary, not a lexical one (it doesn't need to know what the NEXT
    division is called, only that a new one starts).

    Fails closed on ambiguity: >=2 distinct heading occurrences of the same
    "<kind> <identifier>" is reported AMBIGUOUS, not resolved to the first
    one found — a genuine drafting defect (duplicate numbering) or a
    parsing false-positive both deserve human review, not a silent guess.
    """
    heading_positions = [
        m.start() for m in _DIVISION_HEADING_RE.finditer(full_text)
        if _division_heading_kind_identifier(m)[0].lower() == kind.lower()
        and _division_heading_kind_identifier(m)[1].upper() == identifier.upper()
    ]
    if not heading_positions:
        return TargetLookupResult(status="NOT_FOUND", note=f"no heading occurrence of {kind} {identifier} found in the document")
    if len(heading_positions) > 1:
        return TargetLookupResult(
            status="AMBIGUOUS",
            note=f"{len(heading_positions)} distinct heading occurrences of {kind} {identifier} found — cannot determine which governs",
        )
    start = heading_positions[0]
    heading_match = _DIVISION_HEADING_RE.search(full_text[start:start + 200])
    body_start = start + (heading_match.end() if heading_match else 0)
    hi = min(len(full_text), body_start + max_chars)
    next_boundary = _DIVISION_HEADING_RE.search(full_text[body_start:hi])
    if next_boundary:
        hi = body_start + next_boundary.start()
    return TargetLookupResult(status="FOUND", body=full_text[body_start:hi], match_start=start)


# ---------------------------------------------------------------------------
# Step 4A.11 Phase 2 — conditional applicability. Shared infrastructure for
# detecting whether a material fact's applicability is conditioned by
# contractual language, and — the central problem per the phase spec —
# whether that condition structurally ATTACHES to the specific fact in
# question rather than merely appearing somewhere nearby in the document.
#
# Three-state model (plus UNCONDITIONAL for "no condition at all"), no
# probabilistic authority:
#   UNCONDITIONAL   -- no material condition modifies this fact.
#   ESTABLISHED     -- a condition is present and its attachment is
#                      deterministically clear (same-sentence leading
#                      clause, same-sentence trailing proviso, a specific
#                      mid-clause modifier shape, or an explicit backward
#                      reference from the immediately following sentence).
#   NOT_ESTABLISHED -- condition-shaped language exists but scope/
#                      attachment cannot be confirmed.
#   CONFLICTING     -- two separately operative provisions impose
#                      incompatible conditions that cannot be
#                      deterministically reconciled.
#
# Attachment is scoped by SENTENCE, not by a fixed character window: a
# condition connector occurring in a different sentence than the fact
# (a different obligation, a different party's clause, a heading, a
# quoted/negated example separated by its own sentence boundary) is
# structurally out of scope by construction, without needing a
# hand-maintained list of "which phrases mean this belongs to someone
# else." This mirrors the structural-over-lexical principle used
# throughout the Step 4A.10.x symmetry work and the Phase 1 cross-
# reference mechanism above.
# ---------------------------------------------------------------------------

@dataclass
class ConditionEvidence:
    status: str  # "UNCONDITIONAL" | "ESTABLISHED" | "NOT_ESTABLISHED" | "CONFLICTING"
    condition_type: Optional[str] = None
    evidence_span: Optional[str] = None
    note: str = ""


def unconditional() -> ConditionEvidence:
    return ConditionEvidence(status="UNCONDITIONAL")


# Leading conditional clause: the fact's own SENTENCE opens with a
# connector clause, terminated by a comma, before the main clause begins
# ("If Customer breaches..., Vendor shall indemnify..."). Also matches a
# clause-initial "if/when/unless" that starts right after an EARLIER
# comma-separated clause in a compound sentence ("Notwithstanding X, if Y,
# Z shall apply.") -- still structurally "leading" relative to the main
# clause that follows its own comma, just not at the sentence's absolute
# start.
_LEADING_CONDITION_RE = re.compile(
    r"(?:\A|,\s*)(?:If|When|Unless|Only\s+if|But\s+only\s+if)\b(?:(?!,).){1,220}?,\s*",
    re.I,
)

# Trailing proviso: after the main clause, within the SAME sentence, a
# connector introduces a qualifying clause running toward the sentence's
# own end ("..., provided that...", "..., unless...", "..., to the extent...").
_TRAILING_PROVISO_RE = re.compile(
    r",?\s*(?:provided(?:,)?\s+(?:however,?\s+)?that|unless|except\s+(?:when|to\s+the\s+extent)|"
    r"only\s+if|but\s+only\s+if|to\s+the\s+extent|only\s+to\s+the\s+extent|"
    r"only\s+for|but\s+only\s+for|"
    r"so\s+long\s+as|as\s+long\s+as|where\s+applicable)\b",
    re.I,
)

# Mid-clause modifiers, each requiring a specific structural shape rather
# than a bare connector word, to avoid flooding on ordinary prose ("upon
# receipt of written notice" is a condition; "upon execution" is
# contract-effectiveness boilerplate and is deliberately not matched).
_MIDCLAUSE_SUBJECT_TO_CONDITIONS_RE = re.compile(
    r"\bsubject\s+to\s+(?:the\s+following\s+conditions|"
    r"(?:[A-Z][\w'-]*(?:'s)?\s+){1,4}(?:prior\s+)?(?:written\s+)?consent)\b",
    re.I,
)
# The role possessive ("Customer's", "the Vendor's") is optional before
# "receipt of"/"written notice of" -- Step 4A.11 Phase 4
# (fab-ind-af3-payment-triggered-by-event-01) found "Upon Customer's receipt
# of a signed change order, Customer shall pay..." went undetected because
# the pattern previously required "upon (the )?receipt of" with nothing
# between "upon" and "receipt", missing the ordinary case where the party
# receiving is named directly.
_MIDCLAUSE_UPON_RE = re.compile(
    r"\bupon\s+(?:the\s+)?(?:(?:[A-Z][\w'-]*(?:'s)?\s+){1,3})?(?:occurrence\s+of|receipt\s+of|written\s+notice\s+of|"
    r"a\s+final,?\s+non-appealable\s+judgment|[a-z]+'s\s+material\s+breach\s+of|termination\s+of)\b",
    re.I,
)
_MIDCLAUSE_CONTINGENT_RE = re.compile(r"\b(?:contingent|conditioned)\s+(?:up)?on\b", re.I)
_MIDCLAUSE_WHERE_APPLICABLE_RE = re.compile(r"\bwhere\s+applicable\b", re.I)
_MIDCLAUSE_EXCEPT_RE = re.compile(r"\bexcept\s+(?:when|to\s+the\s+extent|in|where)\b", re.I)
# "shall apply only if/when/to the extent" / "applies only if/when/to the
# extent" -- a direct (no leading comma) applicability restriction, as
# opposed to the temporal-only shape below.
_MIDCLAUSE_APPLIES_ONLY_RE = re.compile(
    r"\b(?:shall\s+apply|applies)\s+only\s+(?:if|when|to\s+the\s+extent)\b",
    re.I,
)

# Temporal applicability change: NOT ordinary duration language ("during
# the Term") but an explicit "does/shall not apply until/after" or "only
# applies until/after/before" shape that changes WHETHER the fact applies,
# not merely how long it lasts.
_TEMPORAL_APPLICABILITY_RE = re.compile(
    r"\b(?:shall\s+not\s+apply\s+until|does\s+not\s+apply\s+until|not\s+apply\s+until|"
    r"shall\s+apply\s+only\s+(?:until|after)|apply\s+only\s+(?:until|after))\b",
    re.I,
)

# Family N — condition located in the sentence immediately AFTER the
# fact's own sentence, explicitly naming the fact by a referential noun
# phrase ("This obligation", "The foregoing limitation", "Such cap")
# before stating a condition. A further qualifying trigger word (if/when/
# unless/until/after/before/arising-from/arising-out-of/arising-under, or a
# "within N days"-shaped procedural window) is REQUIRED after the noun-
# phrase scope -- this is what distinguishes a genuine attachment condition
# ("applies only to claims arising under this Agreement", "does not apply
# to invoices disputed in good faith within 10 days of receipt") from a
# bare category carve-out ("shall not apply to willful misconduct"), which
# is already handled separately by each adapter's own carve-out/category
# classification and must NOT be reinterpreted as a condition on the whole
# fact (Step 4A.11 Phase 4: multisupercap-05 regressed when this
# requirement was first relaxed to fully optional -- "This limitation
# shall not apply to willful misconduct" was wrongly treated as an
# unresolved condition on the entire cap instead of the plain uncapped
# carve-out it actually is).
_BACKREF_CONDITION_RE = re.compile(
    r"\A\s*(?:This|The\s+foregoing|Such)\s+(?:indemnification\s+)?"
    r"(?:obligation|limitation|cap|exception)\b(?:(?!\.).){1,120}?"
    r"\b(?:shall\s+not\s+apply\s+to|does\s+not\s+apply\s+to|shall\s+not\s+apply|does\s+not\s+apply|"
    r"applies\s+only\s+to|applies\s+only|shall\s+apply\s+only)\b"
    r"(?:(?!\.).){1,220}?\b(?:if|when|unless|to\s+the\s+extent|until|after|before|arising\s+from|"
    r"arising\s+out\s+of|arising\s+under|within\s+\d+)\b",
    re.I,
)

# An explicit denial that any condition exists at all ("is not subject to
# any condition precedent") — must not be mistaken for a condition just
# because a condition-shaped word appears in a sentence that DENIES one.
_CONDITION_DENIAL_RE = re.compile(
    r"\bis\s+not\s+subject\s+to\s+any\s+condition\b|\bwithout\s+condition\b|\bunconditionally\b",
    re.I,
)

# A vague forward/sideways pointer to an unnamed, unlocated condition
# ("certain conditions... may apply", "certain limitations... may
# further restrict") — signals a condition exists without identifying
# scope or target, so attachment cannot be established either way.
_VAGUE_CONDITION_POINTER_RE = re.compile(
    r"\bcertain\s+(?:conditions|limitations)\b(?:(?!\.).){0,120}?\bmay\s+(?:apply|further\s+restrict)\b",
    re.I,
)

# A backward-referencing conditional marker ("In that event, Seller shall
# indemnify...") points to a triggering circumstance stated in an EARLIER
# sentence — genuinely harder anaphora than the forward _BACKREF_CONDITION_RE
# family above (which only resolves the fact's own condition from the
# FOLLOWING sentence). Step 4A.11 Phase 4
# (fab-ind-af3-condition-prior-sentence-01) found this silently reported as
# UNCONDITIONAL — as if no condition existed at all — when the sentence
# itself plainly signals one exists that this engine does not resolve.
# Correct behavior is NOT_ESTABLISHED (condition-shaped language detected,
# attachment/trigger not confirmed), not UNCONDITIONAL.
_BACKWARD_VAGUE_CONDITION_RE = re.compile(
    r"\A\s*(?:In\s+(?:that|such)\s+event|In\s+such\s+(?:a\s+)?case|"
    r"Under\s+(?:those|such)\s+circumstances)\s*,",
    re.I,
)

_MIDCLAUSE_PATTERNS: Tuple[Tuple[Pattern, str], ...] = (
    (_MIDCLAUSE_SUBJECT_TO_CONDITIONS_RE, "subject_to_conditions"),
    (_MIDCLAUSE_UPON_RE, "upon"),
    (_MIDCLAUSE_CONTINGENT_RE, "contingent"),
    (_MIDCLAUSE_WHERE_APPLICABLE_RE, "where_applicable"),
    (_MIDCLAUSE_EXCEPT_RE, "except"),
    (_MIDCLAUSE_APPLIES_ONLY_RE, "only_if"),
    (_TEMPORAL_APPLICABILITY_RE, "temporal"),
)


def _leading_condition_type(head: str) -> str:
    head = head.strip().lstrip(",").strip().lower()
    if head.startswith("unless"):
        return "unless"
    if head.startswith("only if") or head.startswith("but only if"):
        return "only_if"
    return "if_when"


def _trailing_proviso_type(body: str) -> str:
    body = body.lower()
    if "provided" in body:
        return "provided_that"
    if "unless" in body:
        return "unless"
    if "except" in body:
        return "except"
    if "only if" in body:
        return "only_if"
    if "only for" in body:
        return "only_for"
    if "to the extent" in body:
        return "to_the_extent"
    if "so long as" in body or "as long as" in body:
        return "so_long_as"
    if "where applicable" in body:
        return "where_applicable"
    return "provided_that"


# Shared negative lookbehind for common abbreviation periods that are not
# real sentence/clause boundaries — "Inc.", "Corp.", "Co.", "Ltd.", "LLC."
# (all routinely embedded mid-sentence in a party's own name) alongside the
# pre-existing e.g./i.e./etc./vs./Mr./Dr./No. set. Shared between
# sentence_bounds (condition-attachment scoping) and _CLAUSE_BOUNDARY_RE
# below (is_operative_context's clause scoping) so a fix to one doesn't
# silently miss the other — Step 4A.11 Phase 4 found "...Northstar Data
# Systems Inc. within Net 30 days..., provided that..." was being split at
# "Inc." into two sentences, hiding the trailing proviso from
# detect_condition_in_span entirely (fab-pay-af10-multiword-plus-condition-01).
_ABBREVIATION_LOOKBEHIND = (
    r"(?<!e\.g)(?<!i\.e)(?<!\betc)(?<!\bvs)(?<!\bMr)(?<!\bDr)(?<!\bNo)"
    r"(?<!\bInc)(?<!\bCorp)(?<!\bCo)(?<!\bLtd)(?<!\bLLC)(?<!\bLLP)"
)
_SENTENCE_SPLIT_RE = re.compile(_ABBREVIATION_LOOKBEHIND + r"[.!?]\s+|\n\s*\n")
_SENTENCE_END_RE = re.compile(_ABBREVIATION_LOOKBEHIND + r"[.!?](?=\s|\Z)")


def sentence_bounds(text: str, pos: int) -> Tuple[int, int]:
    """Returns (start, end) of the sentence containing `pos`, bounded by a
    sentence-ending punctuation mark followed by whitespace/EOL, a blank
    line, or the text boundaries."""
    start = 0
    for m in _SENTENCE_SPLIT_RE.finditer(text[:pos]):
        start = m.end()
    end = len(text)
    m2 = _SENTENCE_END_RE.search(text[pos:])
    if m2:
        end = pos + m2.end()
    return start, end


def detect_condition_in_span(text: str, span_start: int, span_end: int) -> ConditionEvidence:
    """Looks for a condition connector structurally attached to the
    sentence spanning [span_start, span_end) in `text`: a leading clause
    at the sentence's own start, a trailing proviso later in the SAME
    sentence, a mid-clause modifier anywhere in the sentence, or an
    explicit backward reference from the sentence immediately after.
    Never searches beyond the fact's own sentence (plus exactly one
    sentence of backward-reference lookahead) — a condition elsewhere in
    the document, in a different obligation's sentence, or in a different
    party's sentence is structurally out of scope by construction."""
    sent_start, sent_end = sentence_bounds(text, span_start)
    sentence = text[sent_start:sent_end]

    if _CONDITION_DENIAL_RE.search(sentence):
        return unconditional()

    backward_vague = _BACKWARD_VAGUE_CONDITION_RE.match(sentence)
    if backward_vague and is_operative_context(text, sent_start + backward_vague.start(), sent_start + backward_vague.end()):
        return ConditionEvidence(
            status="NOT_ESTABLISHED", condition_type=None,
            evidence_span=backward_vague.group(0).strip().rstrip(","),
            note="a triggering condition is referenced from an earlier sentence but its specific "
            "attachment/trigger cannot be resolved",
        )

    leading = _LEADING_CONDITION_RE.search(sentence)
    if leading and is_operative_context(text, sent_start + leading.start(), sent_start + leading.end()):
        return ConditionEvidence(
            status="ESTABLISHED",
            condition_type=_leading_condition_type(leading.group(0)),
            evidence_span=leading.group(0).strip().lstrip(",").strip().rstrip(","),
        )

    trailing = _TRAILING_PROVISO_RE.search(sentence)
    if trailing and is_operative_context(text, sent_start + trailing.start(), sent_start + trailing.end()):
        return ConditionEvidence(
            status="ESTABLISHED",
            condition_type=_trailing_proviso_type(trailing.group(0)),
            evidence_span=sentence[trailing.start():].strip(),
        )

    for pattern, type_name in _MIDCLAUSE_PATTERNS:
        m = pattern.search(sentence)
        if m and is_operative_context(text, sent_start + m.start(), sent_start + m.end()):
            lo = max(0, m.start() - 40)
            hi = min(len(sentence), m.end() + 80)
            return ConditionEvidence(status="ESTABLISHED", condition_type=type_name, evidence_span=sentence[lo:hi].strip())

    # Family N — the sentence immediately after may explicitly reference
    # this fact by name and condition it there.
    if sent_end < len(text):
        next_start, next_end = sentence_bounds(text, sent_end + 1)
        next_sentence = text[next_start:next_end]
        backref = _BACKREF_CONDITION_RE.match(next_sentence)
        if backref and is_operative_context(text, next_start + backref.start(), next_start + backref.end()):
            return ConditionEvidence(status="ESTABLISHED", condition_type="backref", evidence_span=backref.group(0).strip())
        vague = _VAGUE_CONDITION_POINTER_RE.search(next_sentence)
        if vague:
            return ConditionEvidence(
                status="NOT_ESTABLISHED", condition_type=None,
                evidence_span=vague.group(0).strip(),
                note="a condition is referenced but not identified/located -- attachment cannot be established",
            )
    vague_same = _VAGUE_CONDITION_POINTER_RE.search(sentence)
    if vague_same:
        return ConditionEvidence(
            status="NOT_ESTABLISHED", condition_type=None,
            evidence_span=vague_same.group(0).strip(),
            note="a condition is referenced but not identified/located -- attachment cannot be established",
        )

    return unconditional()


def detect_condition_in_text(text: str) -> ConditionEvidence:
    """Same detection, scoped to the ENTIRE given text rather than one
    sentence around a specific offset -- used for a cross-reference
    TARGET division's own body, where the whole resolved body is already
    the correct scope (Section 7 of the phase-2 spec: SOURCE -> REFERENCE
    -> TARGET -> CONDITION -> MATERIAL FACT)."""
    if _CONDITION_DENIAL_RE.search(text):
        return unconditional()
    # Scan every sentence in the body for a leading or trailing marker,
    # or a mid-clause modifier.
    pos = 0
    while pos < len(text):
        sent_start, sent_end = sentence_bounds(text, pos)
        if sent_end <= pos:
            break
        sentence = text[sent_start:sent_end]
        leading = _LEADING_CONDITION_RE.search(sentence)
        if leading:
            return ConditionEvidence(status="ESTABLISHED", condition_type=_leading_condition_type(leading.group(0)),
                                      evidence_span=leading.group(0).strip().lstrip(",").strip().rstrip(","))
        trailing = _TRAILING_PROVISO_RE.search(sentence)
        if trailing:
            return ConditionEvidence(status="ESTABLISHED", condition_type=_trailing_proviso_type(trailing.group(0)),
                                      evidence_span=sentence[trailing.start():].strip())
        applies_only = re.search(r"\bapplies\s+only\s+to\b(?:(?!\.).){1,150}", sentence, re.I)
        if applies_only:
            return ConditionEvidence(status="ESTABLISHED", condition_type="to_the_extent",
                                      evidence_span=applies_only.group(0).strip())
        for pattern, type_name in _MIDCLAUSE_PATTERNS:
            m = pattern.search(sentence)
            if m:
                lo = max(0, m.start() - 40)
                hi = min(len(sentence), m.end() + 80)
                return ConditionEvidence(status="ESTABLISHED", condition_type=type_name, evidence_span=sentence[lo:hi].strip())
        pos = sent_end + 1
    return unconditional()


# Family CONFLICTING (bounded) — two separately operative provisions,
# elsewhere in the document, each backward-reference the SOURCE division
# by "under Section N" (or Schedule/Exhibit/etc.) and each impose a
# temporal condition on it. If two such conditions use directly opposite
# temporal markers (after/before, until/after) they cannot both be true
# for the same claim -- reported CONFLICTING rather than silently picking
# either. This is deliberately narrow (temporal antonyms only, the
# concrete shape actually observed) rather than a general incompatible-
# condition prover, which is out of scope for this phase.
_BACKWARD_CONDITION_ON_SECTION_RE = re.compile(
    r"\b(?:the\s+)?(?:indemnification\s+obligation|liability\s+cap|limitation\s+of\s+liability|cap)\b"
    r"(?:(?!\.).){0,40}?\b(?:under|in)\s+(" + _DIVISION_KIND_ALTERNATION + r")\s+(" + _DIVISION_IDENTIFIER_FRAGMENT + r")\b"
    r"(?:(?!\.).){1,220}?\b(?:shall\s+apply\s+only|applies\s+only|shall\s+not\s+apply)\b(?:(?!\.).){0,220}",
    re.I,
)
_TEMPORAL_ANTONYM_PAIRS = (("after", "before"), ("until", "after"))

# Candidate 2 root-cause fix (indemnification material-context silent
# loss): _BACKWARD_CONDITION_ON_SECTION_RE above requires the qualifying
# clause to open with "<the obligation> under/in Section N ...", i.e.
# the section reference comes BEFORE the "shall apply only" language.
# Real drafting very commonly inverts this with a leading "Notwithstanding
# Section N, ..." construct instead -- a materially different surface
# form of the exact same backward cross-reference concept, not covered
# by the existing pattern at all.
_NOTWITHSTANDING_SECTION_QUALIFIER_RE = re.compile(
    r"notwithstanding\s+(?:the\s+foregoing\s+in\s+|anything\s+(?:to\s+the\s+contrary\s+)?(?:contained\s+)?in\s+)?"
    r"(" + _DIVISION_KIND_ALTERNATION + r")\s+(" + _DIVISION_IDENTIFIER_FRAGMENT + r")\b"
    r"(?:(?!\.).){1,220}?\b(?:shall\s+apply\s+only|applies\s+only|shall\s+not\s+apply|shall\s+not\s+exceed"
    r"|is\s+limited\s+to|shall\s+be\s+limited\s+to)\b(?:(?!\.).){0,220}",
    re.I,
)


def detect_backward_referenced_qualifier(full_text: str, source_kind: str, source_identifier: str) -> Optional[ConditionEvidence]:
    """Generalizes `detect_conflicting_backward_conditions` (below) to the
    SINGLE-reference case. That function only ever returns non-None when
    TWO backward-references to the same division conflict -- a genuine,
    material qualifier stated via exactly ONE such reference ("Notwithstanding
    Section 12, Vendor's indemnification obligation applies only to
    claims filed within ninety days...") was previously invisible to
    both this codebase's regex vocabulary (the leading-"notwithstanding"
    surface form) AND the "needs 2+ to fire at all" gate -- silently
    discarding a real modifier rather than surfacing it. Returns
    ESTABLISHED (an unresolved, but real, qualifier exists) the first
    time ANY matching backward-reference is found, or CONFLICTING when
    2+ disagree (reusing the same temporal-antonym check the sibling
    function already trusts), never silently None once a qualifying
    reference exists."""
    matches = [
        m for m in _NOTWITHSTANDING_SECTION_QUALIFIER_RE.finditer(full_text)
        if m.group(1).lower() == source_kind.lower() and m.group(2).upper() == source_identifier.upper()
    ] + [
        m for m in _BACKWARD_CONDITION_ON_SECTION_RE.finditer(full_text)
        if m.group(1).lower() == source_kind.lower() and m.group(2).upper() == source_identifier.upper()
    ]
    if not matches:
        return None
    tails = [m.group(0).lower() for m in matches]
    for a, b in _TEMPORAL_ANTONYM_PAIRS:
        if any(a in t for t in tails) and any(b in t for t in tails):
            return ConditionEvidence(
                status="CONFLICTING", condition_type="temporal",
                evidence_span=" | ".join(m.group(0).strip() for m in matches),
                note=f"{len(matches)} separately operative provisions impose incompatible temporal "
                     f"conditions on {source_kind} {source_identifier} -- cannot be deterministically reconciled",
            )
    return ConditionEvidence(
        status="ESTABLISHED", condition_type="backward_reference",
        evidence_span=matches[0].group(0).strip(),
        note=f"a separately-stated provision imposes a qualifier on {source_kind} {source_identifier} via a "
             f"backward cross-reference -- this evaluation does not determine whether it applies or its full scope",
    )


def detect_conflicting_backward_conditions(full_text: str, source_kind: str, source_identifier: str) -> Optional[ConditionEvidence]:
    """Scans `full_text` for 2+ provisions that each backward-reference
    `<source_kind> <source_identifier>` (the fact's own division) with a
    temporal condition, and reports CONFLICTING when two of them use
    directly opposite temporal markers. Returns None when fewer than 2
    such backward-references exist (nothing to reconcile)."""
    matches = [
        m for m in _BACKWARD_CONDITION_ON_SECTION_RE.finditer(full_text)
        if m.group(1).lower() == source_kind.lower() and m.group(2).upper() == source_identifier.upper()
    ]
    if len(matches) < 2:
        return None
    tails = [m.group(0).lower() for m in matches]
    for a, b in _TEMPORAL_ANTONYM_PAIRS:
        has_a = any(a in t for t in tails)
        has_b = any(b in t for t in tails)
        if has_a and has_b:
            return ConditionEvidence(
                status="CONFLICTING", condition_type="temporal",
                evidence_span=" | ".join(m.group(0).strip() for m in matches),
                note=f"{len(matches)} separately operative provisions impose incompatible temporal "
                     f"conditions on {source_kind} {source_identifier} -- cannot be deterministically reconciled",
            )
    return None


# ---------------------------------------------------------------------------
# Formulaic REQUIRES_REVIEW explanation/action text — the string-formatting
# half of the "unresolved facts -> abstain" pattern used by every adapter
# with a directional or multi-fact structure (see benchmarks/duplication_
# promotion_review.md, section 5). Deliberately NOT a PolicyDecision
# builder: each adapter's REQUIRES_REVIEW PolicyDecision carries different
# fields (LoL includes category_treatments/our_position/reconciliation;
# the others pass empty/None for those) and forcing one shared constructor
# to cover every adapter's field set would either bloat every call site
# with mostly-unused parameters or silently drop fields an adapter actually
# needs. Only the two pure strings — which carry zero decision-shape
# information — are shared.
# ---------------------------------------------------------------------------

def requires_review_explanation(clause_description: str, contract_language: str, unresolved_facts: List[str]) -> str:
    """`clause_description` is the noun phrase naming what couldn't be
    evaluated, e.g. "indemnification structure", "termination structure",
    or plain "clause" (LoL's phrasing)."""
    return (
        f"Contract language: \"{contract_language}\". This {clause_description} could not be evaluated "
        f"deterministically — the following fact(s) required for a policy decision could not be reliably "
        f"established: {'; '.join(unresolved_facts)}. Result: {REQUIRES_REVIEW}."
    )


def requires_review_required_action(unresolved_facts: List[str]) -> str:
    return "Manual review required — " + "; ".join(unresolved_facts)


# ---------------------------------------------------------------------------
# Reciprocal-symmetry verification mechanics — the scan/window/compare
# skeleton independently implemented four times (Indemnification,
# Termination, Confidentiality, Assignment; see benchmarks/duplication_
# promotion_review.md, section 2). A mutual/reciprocal clause opener
# ("each party"/"either party"/"neither party"...) claims symmetric
# treatment; real drafting sometimes layers a differentiated, per-party-
# NAMED proviso on top of that opener. This scans a window for sub-clauses
# attributing terms to a SPECIFIC named role, snapshots each role's terms
# via an adapter-supplied function, and compares snapshots pairwise via an
# adapter-supplied comparison function — the attribution regex, the
# generic-role-word stoplist, what a "snapshot" contains, and how two
# snapshots disagree are all clause-specific and stay adapter-owned.
#
# The local window for each role's own attribution is bounded at the START
# of the NEXT role attribution (not just the next sentence period) — a
# role's own classification window bleeding into the next role's clause,
# when two attributions are joined by ", and" inside one semicolon-joined
# sentence rather than separated by a period, was found and fixed
# independently in Assignment and Confidentiality before being centralized
# here, and confirmed (via regression tests written and shown failing
# before this promotion) to reproduce identically in Indemnification and
# Termination's pre-promotion implementations.
# ---------------------------------------------------------------------------

# Step 4A.5 — a multi-word role-name capture ("[A-Z]\w+(?:\s+[A-Z]\w+){0,2}")
# is necessary to stop truncating real multi-word entity/role names ("Host
# Facility", "Home Health Agency"), but in ALL-CAPS text (a formatting
# mutation both frozen corpora exercise) every word is capitalized, so the
# same fragment can over-capture trailing connector words ("CUSTOMER FROM
# AND"). This trims common non-role connector words a capitalized role
# name would never legitimately end with, from the right end only —
# it does not change what counts as a valid role name, only strips
# grammatical filler a greedy multi-word match pulled in by accident.
_ROLE_NAME_TRAILING_STOPWORDS = frozenset({
    "from", "and", "or", "the", "this", "that", "which", "who", "shall",
    "will", "to", "of", "for", "under", "against", "in", "on", "at", "by",
    "with", "its", "their",
})


def trim_role_name(raw: str) -> str:
    """Strips trailing connector words a greedy multi-word role-name
    capture pulled in (see _ROLE_NAME_TRAILING_STOPWORDS) — used
    wherever a role/entity name is captured via a multi-word capitalized
    fragment, so ordinary text following the real name (especially in
    ALL-CAPS formatting mutations) doesn't get treated as part of it."""
    words = raw.split()
    while len(words) > 1 and words[-1].lower() in _ROLE_NAME_TRAILING_STOPWORDS:
        words.pop()
    return " ".join(words)


# Step 4A.7.1 (A6-RB-07), generalized in Step 4A.7.3 — a numeric/defined
# value can be cleanly extracted while its own source is delegated through a
# chain of cross-references ending in a document not included in this
# excerpt ("...set forth in Section 4, which Section 4 itself cross-
# references Schedule B...not included in this excerpt"). Originally built
# and scoped to liability's cap-basis shape only; Step 4A.7.3's fresh
# battery (F3-D-06, F3-P-15) found the identical pattern reachable from
# indemnification's monetary/scope delegation and payment_terms' rate
# delegation, and no adapter but liability had any detector for it at all.
# Shared here so every adapter gets the same, single detection rule rather
# than three independently-drifting copies. Matches the general SHAPE (a
# relative "which X itself/in turn <delegates>" clause resolving to an
# excluded/external document), not one adapter's own vocabulary.
CHAINED_DELEGATION_RE = re.compile(
    # Step 4A.9 (S48-L-T3-I-01) — "in turn DEFERS TO" is the same
    # second-hop delegation as "in turn cross-references/references", one
    # more ordinary verb for the same concept.
    r"which\s+[A-Z][\w .]{0,40}?\s+(?:itself|in\s+turn)\s+"
    r"(?:cross-references|references|incorporates(?:\s+by\s+reference)?|defers\s+to)\s+"
    r"[^.]{0,120}?"
    r"(?:not\s+included\b|external,?\s+not\s+part\s+of\s+this\s+Agreement|not\s+part\s+of\s+this\s+Agreement)",
    re.I,
)


# Step 4A.7.4 — a stated value (a cap, a payment period) can be governed by
# a "PROVIDED THAT" proviso whose OWN triggering condition is explicitly
# marked as still unresolved ("a condition not yet verified as of this
# excerpt" / "it not yet being determined which shipments qualify"). Unlike
# an ordinary conditional clause (which resolves deterministically once the
# underlying fact is known), this shape signals the drafter themselves
# doesn't yet know whether the condition is met — so the stated value's
# applicability is itself an open question, not merely a business term to
# read literally. Shared because the shape isn't specific to what kind of
# value the proviso conditions (liability cap multiplier, payment period,
# ...) — see fresh-battery F3-L-09 and F3-P-09.
# Step 4A.9 — Step 4A.8 found this only tolerated two closing verbs
# ("verified"/"determined") in two tenses. The underlying concept — a
# PROVIDED THAT proviso whose own triggering condition the document admits
# isn't settled yet — is expressed with plenty of other, equally ordinary
# closing verbs ("confirmed", "made" an election, "elected", "fixed" a
# date) and tenses ("not yet HAVING BEEN determined", not just "not yet
# been"/"not yet being"), and can carry an adverb before the verb ("not yet
# been INDEPENDENTLY confirmed").
CONDITIONAL_UNVERIFIED_PRECONDITION_RE = re.compile(
    # Step 4A.9 (S48-P-F-02) — the same conditional-value-depends-on-an-
    # unresolved-precondition shape is also drafted as "unless X ... in
    # which case Y" rather than only "PROVIDED THAT" — the anchor is
    # widened to either.
    # Non-period-or-decimal-point-in-a-section-number ((?:[^.]|\.\d)): a
    # bare [^.] stops the lookahead dead at "Section 6.7"'s own decimal
    # point, well short of the actual unresolved-precondition phrase later
    # in the same sentence (S48-P-F-02).
    r"(?:provided\s+that|unless\b)(?:[^.]|\.\d){0,200}?"
    r"(?:has\s+|have\s+)?not\s+yet\s+(?:been\s+|being\s+|having\s+been\s+)?(?:[a-z]+ly\s+)?"
    r"(?:verified|determined|confirmed|made|elected|established|resolved|fixed|settled)\b",
    re.I,
)


# Step 4A.9 — Step 4A.8 found the self-flagged-unresolved family
# independently maintained per adapter (liability's _SELF_FLAGGED_
# AMBIGUITY_RE, payment_terms' _SELF_FLAGGED_PAYMENT_UNRESOLVED_RE,
# indemnification's _SELF_FLAGGED_INDEMNIFICATION_UNRESOLVED_RE) had drifted
# apart: a phrase added to liability in Step 4A.7.4
# ("determination having yet been made") was never propagated to
# payment_terms despite the identical concept applying there too
# (S48-P-N-03), and fresh Step 4A.8 paraphrases of the SAME underlying
# concept ("have not yet agreed whether", "remains unresolved" without
# "under negotiation", "determination has yet been reached") were missing
# from every adapter's copy. This is the shared, adapter-agnostic core of
# that family — "the document itself states a material fact is not yet
# settled" has no adapter-specific semantics — kept separate from each
# adapter's own genuinely adapter-specific extras (payment's "no invoice
# shall issue until", liability's "no such [X] currently exists").
SELF_FLAGGED_UNRESOLVED_RE = re.compile(
    r"\b(?:it\s+being\s+)?unclear\s+whether\b"
    r"|not\s+yet\s+(?:finally\s+)?resolved\b"
    r"|remains?\s+unresolved\b"
    r"|not\s+yet\s+(?:been\s+)?determined\b"
    r"|determination\s+not\s+yet\s+made\b"
    r"|(?:no\s+such\s+)?determination\s+having\s+(?:yet\s+)?been\s+made\b"
    r"|determination\s+has\s+yet\s+been\s+reached\b"
    r"|not\s+yet\s+reached\s+agreement\b"
    r"|have\s+not\s+yet\s+reached\s+agreement\b"
    r"|(?:have|has)\s+not\s+yet\s+agreed\s+whether\b"
    r"|remain(?:s|ing)?\s+under\s+negotiation\b",
    re.I,
)


# Step 4A.10.1 — a structuring-regex match is currently trusted as
# document-owned/operative with zero check of its enclosing structural
# context. Step 4A.10 found 3 S4 cases (all indemnification) where text
# quoted as a hypothetical example inside a prompt-injection payload, then
# explicitly negated ("this sentence does not actually appear anywhere
# below"), was extracted as if the parties had actually agreed to it.
# Root-caused (artifacts/step4a10_1/s4_root_cause.md) as a compound of:
# quoted-example text being treated as operative, AND negation/meta-
# language of that quoted material (whether before OR after it) being
# ignored entirely. A pre-fix benchmark (artifacts/step4a10_1/
# s4_benchmark_PRE_output.txt) found this generalizes across 5 distinct
# non-operative structural families (quoted examples, drafting
# instructions, descriptive-about-clause statements, prompt injection,
# explicit negation) at an 18/50 (36%) false-operative-extraction rate —
# confirming this is a general property of the pipeline, not limited to
# the 3 originally-found sentences, and not specific to one phrase family.
#
# This is deliberately adapter-agnostic (any structuring regex in any
# adapter has the identical blind spot) and lives here rather than in
# indemnification_policy_engine.py so a future liability/payment_terms
# fix, if evidence ever justifies one, reuses this rather than
# re-deriving it.
_QUOTATION_INTRODUCING_RE = re.compile(
    r"\bplease\s+quote\b"
    r"|\bquote\s+the\s+following\b"
    r"|\bread(?:s|ing)?\s+as\s+follows\b"
    r"|\bstate[sd]?\s+as\s+follows\b"
    r"|\bfor\s+example\b"
    r"|\bfor\s+instance\b"
    r"|\bsuch\s+as\b"
    r"|\be\.g\."
    r"|\bhypothetically\b"
    r"|\bsample\s+(?:language|provision)\b"
    r"|\billustrative\s+(?:language|clause)\b"
    r"|\bdraft\s+language\s+reading\b"
    r"|\bconsider\s+language\s+(?:like|such\s+as)\b"
    r"|\ba\s+clause\s+(?:such\s+as|reading)\b"
    r"|\blanguage\s+(?:such\s+as|reading)\b"
    # Step 4A.11 Phase 4 — "A typical [limitation] clause reads:" (colon,
    # no "as follows") wasn't covered by the "reads as follows" phrase
    # above; found via a genuine false structural establishment
    # (fab-lia-af6-quoted-example-01).
    r"|\breads?\s*:\s*$"
    r"|\btypical\s+\w+\s+clause\b",
    re.I,
)

_NEGATED_OR_REJECTED_MATERIAL_RE = re.compile(
    r"\bdoes\s+not\s+actually\s+appear\b"
    r"|\bdoes\s+not\s+appear\b"
    r"|\bis\s+not\s+included\b"
    r"|\bwas\s+not\s+included\b"
    r"|\bdoes\s+not\s+contain\b"
    r"|\bdo\s+not\s+contain\b"
    r"|\bwas\s+rejected\b"
    r"|\bwere\s+rejected\b"
    r"|\brejected\s+language\b"
    r"|\bwould\s+have\s+(?:stated|read|provided|required)\b"
    r"|\bthis\s+(?:sentence|language|clause|provision)\s+does\s+not\b"
    r"|\bno\s+such\s+(?:language|clause|provision|sentence)"
    r"(?:\s+currently)?\s+(?:appears|exists|is\s+included)\b"
    r"|\bdoes\s+not\s+contain\s+a\s+provision\b"
    r"|\bcontains?\s+no\s+(?:such\s+)?(?:\w+[\s-]){0,3}(?:provision|clause|language|term)\b"
    r"|\bomits?\s+any\s+requirement\b"
    r"|\bwas\s+withdrawn\b"
    r"|\bwas\s+deleted\b"
    r"|\bexplicitly\s+declined\b"
    r"|\bdeclined\s+to\s+(?:agree|include)\b"
    # Step 4A.11 Phase 4 — direct safety-defect evidence: a provision
    # marked "(no longer in effect)" and later stated to have been
    # "replaced... in its entirety" by an amendment was still being
    # established as if currently operative (fab-ind-af6-superseded-01),
    # because no existing check covered this specific superseded-
    # provision language family.
    r"|\bno\s+longer\s+in\s+(?:effect|force)\b"
    r"|\breplaced\b(?:(?!\.).){0,40}?\bin\s+its\s+entirety\b"
    r"|\bsuperseded\b"
    # A schedule/exhibit/clause explicitly marked as illustrative/
    # informational only, or explicitly stated not to be part of the
    # Agreement -- a sample clause shown "for reference purposes only"
    # (fab-ind-af6-nonoperative-schedule-01) states real-looking
    # obligation text without actually adopting it.
    r"|\binformational\s+only\b"
    r"|\bnot\s+part\s+of\s+the\s+Agreement\b"
    r"|\bfor\s+reference\s+purposes\s+only\b"
    r"|\bprovided\s+for\s+reference\s+only\b"
    r"|\b(?:shown|provided|given|included|listed|attached)\s+(?:here\s+)?for\s+reference(?:\s+only)?\b"
    r"|\bnot\s+incorporated\b"
    # A hypothetical/unfinalized-draft marker: the surrounding text
    # explicitly states nothing has been agreed/finalized yet.
    r"|\bhave\s+not\s+been\s+finalized\b"
    r"|\bhas\s+not\s+been\s+finalized\b"
    r"|\bnot\s+yet\s+finalized\b"
    r"|\bno\b(?:(?!\.).){0,40}?\bhave\s+been\s+finalized\b"
    # A description of a PRIOR, terminated/different agreement's terms --
    # explicitly not this Agreement's own operative term.
    r"|\bprior,?\s+now[\s-]terminated\s+agreement\b"
    r"|\bunder\s+the\s+parties'?\s+prior\s+agreement\b",
    re.I,
)

# Recital/intent language ("WHEREAS the parties intend to...") states an
# aspiration the operative sections below may or may not adopt verbatim
# -- it is not itself the operative term. Separate from
# _NEGATED_OR_REJECTED_MATERIAL_RE because nothing is being negated or
# rejected here; it simply was never asserted as current fact.
_RECITAL_INTENT_RE = re.compile(
    r"\bWHEREAS\b(?:(?!\.).){0,120}?\bintend(?:s|ed)?\s+to\b",
    re.I,
)

_META_INSTRUCTIONAL_RE = re.compile(
    r"\bplease\s+(?:quote|revise|output|respond|insert|add)\b"
    r"|\bignore\s+(?:all\s+)?previous\s+instructions\b"
    r"|\bsystem\s*(?:override)?\s*:"
    r"|\bnote\s+to\s+(?:reviewer|ai|model|drafter)\b"
    r"|\bdrafting\s+note\s*:"
    r"|\bcomment\s*:"
    r"|\breviewer\s+instruction\b"
    r"|\byou\s+(?:are|must|should)\s+(?:now\s+)?(?:output|respond|treat|report)\b"
    r"|\battention\s+model\b"
    r"|\btest\s+instruction\b"
    r"|\bfor\s+debugging\s+purposes\b"
    r"|\bfor\s+testing\s+purposes\b"
    r"|\[(?:drafting\s+note|redline\s+instruction|comment\s+bubble|system\s+instruction)\]",
    re.I,
)

# Candidate 2 root-cause fix (shared primitive gap): the existing
# structural cue families above catch a quoted example, a drafting
# instruction, a narrow set of "language stating that..." descriptive
# phrasings, and WHEREAS-recital intent -- but NOT the extremely common
# real-world pattern of industry-norm commentary ("It is common practice
# for a vendor to carry X", "SaaS agreements typically commit to Y")
# combined with an explicit statement that THIS agreement's own terms
# are not yet settled ("remains to be negotiated", "have not yet agreed").
# Found via two independent adapters (insurance, sla) both extracting an
# "established" fact from exactly this shape of sentence -- reported as
# a shared-primitive defect, not two adapter-local bugs, and fixed once
# here so every caller of is_operative_context benefits.
_INDUSTRY_NORM_DESCRIPTIVE_RE = re.compile(
    r"\bit\s+is\s+(?:common|typical|standard)\s+(?:practice\s+)?(?:for\b|to\b)"
    r"|\b(?:commonly|typically|usually|generally)\s+(?:commits?\s+to|requires?|includes?|provides?|"
    r"carr(?:y|ies)|specif(?:y|ies)|states?|caps?)\b"
    r"|\bagreements?\s+of\s+this\s+(?:type|kind)\s+(?:typically|commonly|usually|generally)\b"
    r"|\bin\s+(?:this\s+)?(?:industry|line\s+of\s+business)\b.{0,40}?\b(?:typically|commonly|usually)\b",
    re.I,
)
_NOT_YET_AGREED_RE = re.compile(
    r"remains?\s+to\s+be\s+(?:negotiated|agreed|finalized|determined|settled)"
    r"|(?:have|has)\s+not\s+(?:yet\s+)?(?:been\s+)?(?:agreed|negotiated|finalized|settled\s+on|addressed|decided)"
    r"|(?:is|are)\s+(?:yet\s+)?to\s+be\s+(?:agreed|negotiated|finalized|determined)"
    r"|subject\s+to\s+(?:future|further)\s+negotiation"
    r"|not\s+(?:yet\s+)?(?:finalized|final(?:i[sz]ed)?)\b",
    re.I,
)

# Candidate 3 final gap-closure fix (Root Cause A) — a structural signal
# that a named contract party is itself the subject of a modal-obligation
# construction anchored in the local window ("Vendor shall maintain...",
# "Customer will pay..."). Used to REBUT the industry-norm-descriptive
# signal below: a clause that opens with a benign industry-context lead-in
# but then states a real, party-specific obligation ("As is standard in
# the industry, Vendor shall maintain 99.9% uptime...") must not be
# suppressed just because it also contains industry-norm framing. Kept
# deliberately generic (any of the common party-role nouns, not a
# blacklist of specific sentences) so it generalizes across adapters.
_PARTY_OBLIGATION_ANCHOR_RE = re.compile(
    r"\b(?:Vendor|Customer|Supplier|Contractor|Licensee|Licensor|Client|"
    r"Company|Provider|Recipient|Disclosing\s+Party|Receiving\s+Party|"
    r"Party|Parties)\b(?:(?!\.).){0,40}?\b(?:shall|will|must|agrees?\s+to|"
    r"is\s+required\s+to|are\s+required\s+to)\b",
    re.I,
)

# Candidate 3 final gap-closure fix (Root Cause A) — the matched clause
# directly negates the very obligation/commitment it describes ("Vendor
# shall have NO obligation to notify...", "makes no uptime commitment").
# Distinct from _NEGATED_OR_REJECTED_MATERIAL_RE above, which covers
# meta-textual negation of a QUOTED example ("this sentence does not
# actually appear..."); this covers direct grammatical negation of the
# duty itself, present in the operative sentence with no quoting involved
# (found via data_security-130 / sla-210 -- a real "Vendor shall have no
# obligation to notify Customer of any personal data breach" clause was
# being extracted as if it established an affirmative notification duty).
_DIRECT_OBLIGATION_NEGATION_RE = re.compile(
    r"\b(?:shall|will)\s+have\s+no\s+(?:obligation|duty|requirement)\s+to\b"
    r"|\bis\s+not\s+(?:obligated|required)\s+to\b"
    r"|\bare\s+not\s+(?:obligated|required)\s+to\b"
    r"|\bmakes?\s+no\s+(?:\w+\s+){0,2}(?:commitment|guarantee|warranty)\b"
    r"|\bno\s+(?:\w+\s+){0,2}commitment\s+of\s+any\s+kind\b"
    r"|\bshall\s+not\s+be\s+(?:obligated|required)\s+to\b",
    re.I,
)

# Candidate 3 zero-silent-loss mission (Phase 3, shared reconciliation
# primitive) -- a DIFFERENT, SEPARATE statement elsewhere in the SAME
# document can broadly negate or supersede a value already established
# elsewhere ("Vendor shall maintain CGL insurance with a $2,000,000
# limit... For clarity, no specific insurance limits are required under
# this Agreement..."). This is distinct from _DIRECT_OBLIGATION_NEGATION_RE
# (which negates the obligation AT the matched span itself) -- here the
# negation is a genuinely separate, later clause about the SAME concept,
# and from _NEGATED_OR_REJECTED_MATERIAL_RE (which covers meta-textual
# negation of a QUOTED example). Deliberately general structural
# vocabulary -- "no specific X (is/are) required", "does not guarantee
# any specific X", "retains all ownership rights ... grants only a
# license" -- not a blacklist of the specific burned-corpus sentences;
# these are standard contract-drafting negation/override patterns that
# recur across liability, insurance, SLA, and IP-ownership domains alike.
DOCUMENT_WIDE_NEGATION_RE = re.compile(
    r"\bno\s+specific\s+\w+(?:\s+\w+){0,2}\s+(?:is|are)\s+required\b"
    r"|\bdoes\s+not\s+guarantee\s+any\s+specific\b"
    r"|\bis\s+not\s+required\s+under\s+this\s+Agreement\b"
    r"|\bretains?\s+all\s+ownership\s+rights\b(?:(?!\.).){0,60}?\bgrants?\s+(?:[A-Z][\w']*\s+)?(?:only\s+)?a\s+license\b"
    # Scoped narrowly to "Section N shall not apply" (nullifying an ENTIRE
    # cross-referenced section wholesale) -- NOT a bare "the limitation
    # shall not apply to claims arising from X," which is a legitimate,
    # already-handled, category-scoped carve-out (see category_treatments'
    # "uncapped" treatment), not a document-wide contradiction.
    r"|\bSection\s+\d+[A-Za-z]?\s+shall\s+not\s+apply\b"
    # A later statement affirmatively grants unrestricted freedom to do
    # the very thing an earlier statement required consent/restriction
    # for ("may freely assign ... without consent or notice") -- a direct
    # reversal of a consent/restriction requirement, general across any
    # adapter that structures a consent-gated right.
    r"|\bmay\s+freely\s+\w+\b(?:(?!\.).){0,60}?\bwithout\s+consent\b",
    re.I,
)

# Candidate 3 zero-silent-loss mission (Phase 3) -- an explicit textual
# marker that the DOCUMENT ITSELF states two provisions are unreconciled
# ("without indicating which governs", "without reconciling the two",
# "without reconciling which controls", "without resolving which
# applies") is a standard drafting-review convention for flagging real
# ambiguity, not vocabulary invented for one test corpus -- a document
# containing this marker is asserting its own internal inconsistency.
UNRECONCILED_AMBIGUITY_MARKER_RE = re.compile(
    r"\bwithout\s+(?:indicating|reconciling|resolving|specifying)\s+which\s+(?:governs|controls|applies)\b"
    r"|\bwithout\s+reconciling\s+the\s+two\b",
    re.I,
)


def document_wide_conflict_detected(document_text: str, established_start: int = 0, established_end: int = 0) -> bool:
    """Returns True when the document contains a DOCUMENT_WIDE_NEGATION_RE
    match anywhere. No exclusion window is needed: this regex's vocabulary
    (broad negation phrasing -- "no specific X is required", "does not
    guarantee any specific X") is structurally incompatible with the
    affirmative value-establishing phrasing every adapter's own primary-
    value regex requires (e.g. "shall maintain ... with a $X limit"), so
    a match can only ever come from a genuinely SEPARATE clause, never
    the same one that established the value. established_start/end are
    accepted for call-site compatibility but not currently used."""
    return bool(DOCUMENT_WIDE_NEGATION_RE.search(document_text))


def unreconciled_ambiguity_marker_present(document_text: str) -> bool:
    """Returns True when the document contains an explicit self-declared
    unreconciled-ambiguity marker (see UNRECONCILED_AMBIGUITY_MARKER_RE)."""
    return bool(UNRECONCILED_AMBIGUITY_MARKER_RE.search(document_text))


# Candidate 3 zero-silent-loss mission (Phase 3) -- a cross-section
# carve-out that EXPLICITLY NAMES the section number of an already-
# established value ("Notwithstanding Section 14, the uptime commitment
# described therein does not apply during the first thirty days...",
# "For clarity, the 99.9% uptime commitment in Section 14 excludes any
# beta or preview features...") is a general, section-number-driven
# structural pattern -- not specific vocabulary for any one adapter's
# domain concept, since it works for any material dimension a document
# might scope-limit by explicit section cross-reference. Deliberately
# parameterized by the established value's own section_label (already
# tracked by every adapter's facts object) rather than hardcoding a
# clause-type keyword.
def cross_section_carveout_referencing(document_text: str, section_label: Optional[str]) -> bool:
    """Returns True when the document contains a carve-out/exception/
    exclusion/additional-requirement statement that explicitly cross-
    references section_label (the section number that established the
    adapter's primary value) -- either narrowing it (an exclusion) or
    supplementing it (an additional condition), since both shapes mean
    the primary value alone no longer fully describes the document's
    actual position. No-ops (returns False) when section_label is falsy."""
    if not section_label:
        return False
    label = re.escape(str(section_label))
    pattern = re.compile(
        rf"\bNotwithstanding\s+Section\s+{label}\b(?:(?!\.).){{0,200}}?"
        rf"(?:does\s+not\s+apply|shall\s+not\s+apply|is\s+excluded|are\s+excluded)"
        rf"|\b(?:in|under|referenced\s+in)\s+Section\s+{label}\b(?:(?!\.).){{0,120}}?"
        rf"\b(?:excludes?|does\s+not\s+include|is\s+measured\s+from)\b"
        rf"|\bSection\s+{label}\b(?:(?!\.).){{0,120}}?\bdoes\s+not\s+apply\b"
        rf"|\brequired\s+by\s+Section\s+{label}\b(?:(?!\.).){{0,120}}?\b(?:must|shall)\b"
        rf"|\bcoverage\s+required\s+by\s+Section\s+{label}\b(?:(?!\.).){{0,120}}?\b(?:must|shall)\b"
        rf"|\bSubject\s+to\s+Section\s+{label}\.\d+\b"
        rf"|\bpermitted\s+under\s+Section\s+{label}\b(?:(?!\.).){{0,120}}?\b(?:does\s+not\s+relieve|remains?\s+liable|shall\s+not\s+relieve)\b",
        re.I,
    )
    return bool(pattern.search(document_text))

# Candidate 3 final gap-closure fix (Root Cause A) — a hypothetical/
# illustrative framing that does not rely on quote marks at all
# ("For example, if Vendor were required to carry Cyber Liability
# insurance, a $1,000,000 limit would be typical...") and so is invisible
# to the existing _QUOTATION_INTRODUCING_RE check (which only fires when
# a quote-mark span is found). Requires an explicit hypothetical
# conditional marker ("for example, if" / "if ... were ...") co-occurring
# with an illustrative-typicality claim ("would be typical", "illustrating
# common ..."), so a genuine "For example, Vendor shall..." cross-
# reference to a real defined example elsewhere is not falsely caught
# (that shape lacks the subjunctive "were"/"would be typical" pairing).
_HYPOTHETICAL_ILLUSTRATIVE_RE = re.compile(
    r"\bfor\s+example\b(?:(?!\.).){0,80}?\bif\b(?:(?!\.).){0,80}?\bwere\b"
    r"|\bif\s+a\s+\w+\s+(?:committed|agreed|were)\b(?:(?!\.).){0,80}?"
    r"\bwould\s+be\s+(?:typical|common|standard)\b"
    r"|\bwould\s+be\s+(?:typical|common|standard)\s+for\s+an?\b"
    r"|\billustrating\s+common\b",
    re.I,
)

# Candidate 3 final gap-closure fix (Root Cause B) -- a defined term whose
# definition is delegated to an external document that the text itself
# states is not attached ("as defined in the Data Processing Addendum,
# which is not attached here") must be flagged as an unresolved
# dependency, not silently treated as a self-contained defined term.
# Deliberately shared here (not re-derived per adapter) -- insurance,
# data_security, and ip_ownership all showed the identical gap
# (UNRESOLVED_DEFINITION_TO_CLEAN) via three independently-phrased but
# structurally identical cases. General, not phrase-specific -- matches
# any external-document name, and the "not attached" clause independent
# of exact wording. Separates DETECTION (a defined term delegates to an
# external document -- this regex) from TARGET RESOLUTION (whether that
# document's content is actually available -- it never is, once "not
# attached" is stated, so no further resolution step is needed here).
EXTERNAL_DEFINITION_NOT_ATTACHED_RE = re.compile(
    r"(?:as\s+)?defined\s+in\s+(?:the\s+)?[^,.;]{1,80},?\s+which\s+is\s+not\s+attached"
    r"|is\s+defined\s+in\s+(?:the\s+)?[^,.;]{1,80}\s*[,.]?\s*(?:that\s+document\s+is\s+)?not\s+attached",
    re.I,
)

_DESCRIPTIVE_ABOUT_CLAUSE_RE = re.compile(
    r"\ba\s+(?:supplier|vendor|party|contractor|licensee|licensor|customer|"
    r"client)\s+(?:might|could|may|would)\s+agree\s+that\b"
    r"|\b(?:language|provision|clause|term)\s+(?:stating|providing|saying)\s+that\b"
    r"|\ba\s+(?:clause|provision)\s+(?:providing|stating)\s+that\b"
    r"|\bdescribing\s+a\s+provision\b"
    r"|\bthis\s+(?:memorandum|memo|summary|article|alert|case\s+study|"
    r"training|glossary|faq)\b",
    re.I,
)

_QUOTE_CHARS = "'‘’\"“”"

# A negation/instruction/descriptive cue must not bleed across a clause
# boundary into a SEPARATE, genuinely operative statement elsewhere in the
# same document (e.g. "...does not actually appear anywhere below.
# Separately, X shall indemnify Y for..." — the second clause is a real,
# distinct, operative term and must not be suppressed just because an
# earlier decoy nearby was negated). Found via this step's own MIXED-case
# test family (artifacts/step4a10_1/s4_benchmark_POST_output.txt showed a
# false suppression here before this boundary was added). Clause
# boundaries are period/semicolon/em-dash followed by whitespace — a
# coarse but general and robust proxy for "a new independent statement is
# starting," which naturally scopes the negation/quotation/meta/
# descriptive checks to the SAME clause as the match (plus one clause of
# lookback/lookahead for the "quote introduced, then negated in the very
# next clause" shape the original 3 S4 cases used) without requiring an
# enumerated list of transition words.
#
# Step 4A.11 Phase 4 — direct safety-defect evidence found via the fresh
# adversarial battery: a common abbreviation period ("e.g.", "i.e.",
# "etc.") followed by whitespace was itself being treated as a clause
# boundary, so "[DRAFTING NOTE: insert standard language here, e.g.
# 'Vendor shall indemnify Customer...']" scoped window_before to AFTER
# "e.g. ", making the earlier "[DRAFTING NOTE:" meta-instructional
# marker invisible to is_operative_context and allowing the bracketed
# example to be falsely established as a real obligation (fab-ind-af6-
# drafting-instruction-01). The negative lookbehind below excludes the
# small, closed set of abbreviation periods that commonly appear
# mid-sentence; it does not touch genuine sentence-ending periods.
_CLAUSE_BOUNDARY_RE = re.compile(_ABBREVIATION_LOOKBEHIND + r"[.;]\s+|--\s*|—\s*")


def _same_or_adjacent_clause(full_window: str, from_end: bool) -> str:
    """Deliberately asymmetric, matching the two demonstrated shapes:
    - BACKWARD (from_end=True, looking before the match): restricted to
      the CURRENT clause only (from the last clause boundary to the
      match) — a "Separately,"/new-clause transition immediately behind
      the match means whatever an EARLIER clause said (e.g. a negated
      decoy quote) must not reach forward into this, a separate, genuinely
      operative statement.
    - FORWARD (from_end=False, looking after the match): the current
      clause PLUS one clause of lookahead — negation of a just-quoted
      example characteristically follows it in the very next clause
      ("...'X shall indemnify Y.' This sentence does not actually
      appear..."), so that one clause of lookahead must still be visible."""
    boundaries = list(_CLAUSE_BOUNDARY_RE.finditer(full_window))
    if from_end:
        if boundaries:
            return full_window[boundaries[-1].end():]
        return full_window
    else:
        if len(boundaries) >= 2:
            return full_window[:boundaries[1].start()]
        return full_window


# Candidate 3 final gap-closure fix (Root Cause A) -- the four states
# distinguishing WHY a structuring-regex match is or isn't the document's
# own operative term, replacing the previous plain boolean. Deliberately
# not a fifth "just return False more often" tweak: OPERATIVE_UNRESOLVED
# and CONFLICTING_CONTEXT let a caller (or a future caller) distinguish
# "structurally confirmed operative"/"structurally confirmed
# non-operative" from "structural cues are ambiguous/contradictory" --
# which the old boolean silently collapsed into a coin-flip between the
# two confirmed states.
OPERATIVE_CONFIRMED = "OPERATIVE_CONFIRMED"
NON_OPERATIVE_CONFIRMED = "NON_OPERATIVE_CONFIRMED"
OPERATIVE_UNRESOLVED = "OPERATIVE_UNRESOLVED"
CONFLICTING_CONTEXT = "CONFLICTING_CONTEXT"


def classify_operative_context(text: str, match_start: int, match_end: int,
                                before_window: int = 220, after_window: int = 220) -> str:
    """Classifies a structuring-regex match's surrounding context as one
    of OPERATIVE_CONFIRMED / NON_OPERATIVE_CONFIRMED / OPERATIVE_UNRESOLVED
    / CONFLICTING_CONTEXT, using STRUCTURAL cue families (quoted
    hypothetical examples, drafting instructions/comments, descriptive
    statements about the general concept, meta-instructional text
    including prompt-injection payloads, direct or meta-textual negation,
    hypothetical/illustrative framing, and industry-norm commentary) --
    never a blacklist of specific sentences. See the module comment above
    this function and artifacts/step4a10_1/s4_root_cause.md for the
    original design, and artifacts/candidate3_final_gap_closure/
    OPERATIVE_CONTEXT_DESIGN.md for this revision's rationale.
    """
    lo, hi = max(0, match_start - before_window), min(len(text), match_end + after_window)
    window_before_full = text[lo:match_start]
    window_after_full = text[match_end:hi]

    # Scope negation/quotation/meta/descriptive checks to the clause
    # touching the match plus one clause of lookback/lookahead (see
    # _same_or_adjacent_clause) so an unrelated, separately-introduced
    # clause elsewhere in the document can't falsely suppress a genuine
    # operative statement.
    window_before = _same_or_adjacent_clause(window_before_full, from_end=True)
    window_after = _same_or_adjacent_clause(window_after_full, from_end=False)
    local_window = window_before + text[match_start:match_end] + window_after

    confirmed_non_operative = False

    # Enclosed in quote marks whose most recent opening quote is itself
    # preceded (nearby) by quotation-introducing framing.
    quote_positions = [window_before.rfind(ch) for ch in _QUOTE_CHARS]
    quote_open = max(quote_positions)
    if quote_open != -1:
        pre_quote_context = window_before[max(0, quote_open - 120):quote_open]
        if _QUOTATION_INTRODUCING_RE.search(pre_quote_context):
            confirmed_non_operative = True

    if _NEGATED_OR_REJECTED_MATERIAL_RE.search(local_window):
        confirmed_non_operative = True
    if _META_INSTRUCTIONAL_RE.search(window_before) or _META_INSTRUCTIONAL_RE.search(local_window[:before_window]):
        confirmed_non_operative = True
    if _DESCRIPTIVE_ABOUT_CLAUSE_RE.search(window_before):
        confirmed_non_operative = True
    if _RECITAL_INTENT_RE.search(window_before):
        confirmed_non_operative = True
    # A direct grammatical negation of the very obligation/commitment the
    # match is about ("Vendor shall have no obligation to notify...") is
    # a confirmed non-operative signal by itself -- no rebuttal applies,
    # because the match IS the negation, not a mere lead-in.
    if _DIRECT_OBLIGATION_NEGATION_RE.search(local_window):
        confirmed_non_operative = True
    # A hypothetical/hedged illustrative framing not anchored in quote
    # marks ("For example, if Vendor were required to carry..., a
    # $1,000,000 limit would be typical").
    if _HYPOTHETICAL_ILLUSTRATIVE_RE.search(local_window):
        confirmed_non_operative = True

    # Candidate 2's original design: industry-norm descriptive framing
    # ("It is common practice for...", "SaaS agreements typically...")
    # combined with an explicit statement that THIS agreement's own terms
    # are not yet settled ("remains to be negotiated") is a reliable,
    # structural signal of non-operative commentary.
    #
    # Candidate 3 final gap-closure fix: requiring BOTH signals left a
    # gap -- plain descriptive/generic-subject commentary ("SaaS
    # agreements typically commit to 99.9% uptime...") that never states
    # anything about being "not yet agreed" (because nothing has been
    # proposed to agree to) was passing through as OPERATIVE_CONFIRMED.
    # The general, non-phrase-specific distinguishing signal is whether a
    # NAMED CONTRACT PARTY is itself the subject of a modal-obligation
    # construction near the match (_PARTY_OBLIGATION_ANCHOR_RE) -- real
    # operative clauses that merely open with a benign industry-context
    # lead-in ("As is standard in the industry, Vendor shall maintain
    # 99.9% uptime...") have this; pure background commentary about what
    # "agreements of this type" or "vendors" typically do does not.
    industry_norm = bool(_INDUSTRY_NORM_DESCRIPTIVE_RE.search(local_window))
    not_yet_agreed = bool(_NOT_YET_AGREED_RE.search(local_window))
    party_anchor = bool(_PARTY_OBLIGATION_ANCHOR_RE.search(local_window))
    if industry_norm and not party_anchor:
        confirmed_non_operative = True
    elif not_yet_agreed:
        confirmed_non_operative = True
    elif industry_norm and party_anchor:
        # Industry-norm framing IS present, and so is a real party
        # obligation -- these two signals point in opposite directions
        # for the same match. Neither the original AND-gate nor a naive
        # OR-gate resolves this correctly; it is a genuine structural
        # ambiguity, not a case either confirmed state fits, so it must
        # not be silently folded into OPERATIVE_CONFIRMED (the pre-
        # Candidate-3 behavior) or into NON_OPERATIVE_CONFIRMED (which
        # would risk suppressing a real obligation with a norm-
        # referencing lead-in).
        return CONFLICTING_CONTEXT

    if confirmed_non_operative:
        return NON_OPERATIVE_CONFIRMED
    return OPERATIVE_CONFIRMED


def is_operative_context(text: str, match_start: int, match_end: int,
                          before_window: int = 220, after_window: int = 220) -> bool:
    """Boolean convenience wrapper over classify_operative_context(), kept
    for every existing call site's `if is_operative_context(...):` gate.
    OPERATIVE_CONFIRMED -> True (establish the match). NON_OPERATIVE_
    CONFIRMED -> False (suppress it). OPERATIVE_UNRESOLVED (reserved for
    future structural-ambiguity signals that aren't yet in play) -> True,
    since suppressing on mere uncertainty here would re-create the
    over-suppression risk Candidate 2's dual-signal design was built to
    avoid; the fact-admission pipeline downstream (verification, dependency
    grounding, absence-state routing) is where genuine ambiguity in an
    established candidate gets escalated to REQUIRES_REVIEW, not here.
    CONFLICTING_CONTEXT -> False: a genuinely contradictory structural
    signal set must not be silently treated as a confirmed clean
    establishment; each adapter's own absence-state / PRESENT_BUT_
    UNRESOLVED safety net (Candidate 3 remediation, Root Cause 1) is what
    keeps this from silently reaching a clean ACCEPT.
    """
    state = classify_operative_context(text, match_start, match_end, before_window, after_window)
    return state in (OPERATIVE_CONFIRMED, OPERATIVE_UNRESOLVED)


def chained_delegation_excerpt(window: str, before: int = 60, after: int = 40) -> Optional[str]:
    """Returns the excerpt around a CHAINED_DELEGATION_RE match in `window`,
    or None if the pattern doesn't fire. Each adapter builds its own
    unresolved-fact message around this excerpt (the underlying fact this
    blocks — a cap, a monetary scope, a rate — differs per adapter)."""
    m = CHAINED_DELEGATION_RE.search(window)
    if not m:
        return None
    lo = max(0, m.start() - before)
    hi = min(len(window), m.end() + after)
    return window[lo:hi].strip()


# Step 4A.10.1 — structural markers that a clause is singling out,
# limiting, or conditioning ONE named party's treatment differently from
# another, independent of which of the 12 required comparison dimensions
# (monetary/scope/defense-control/causation/trigger/temporal/etc.) it
# falls under. Used only as a SAFETY NET (see detect_role_attributed_
# asymmetry below) when the specific-dimension classifiers found no
# provable difference — never as the sole/first-line asymmetry signal.
_DIFFERENTIATING_QUALIFIER_RE = re.compile(
    r"\bonly\b|\bsolely\b|\bexclusively\b|\bexclusive\b|\bdoes\s+not\s+apply\b|"
    r"\bdo\s+not\s+apply\b|\bno\s+(?:\w+\s+)?right\s+to\b|\buncapped\b|\bcapped\s+at\b|"
    r"\bregardless\s+of\b|\bconditioned\s+on\b|\bextends?\s+to\b|"
    r"\bdifferent\b|\bdiffering\b|\bunlike\b|\ba\s+carve[- ]?out\b",
    re.I,
)


# Step 4A.10.6 — the per-role local span is bounded by the NEXT role
# mention (see the callers building local_texts), so the first role
# mentioned in a list is almost always cut off mid-sentence with a
# trailing connector ("Founder Holdings, " / "...against it, and ") the
# LAST-mentioned role's span never has (it runs to the sentence's real
# end instead). That is a window-slicing artifact, not real drafted
# content, and comparing it literally manufactures a "difference" out
# of pure position-in-sentence. Stripped before comparison so the
# structural check reflects actual stated content, not where the
# clause happened to end this particular role's turn.
_TRAILING_CONNECTOR_NOISE_RE = re.compile(
    r"[,;]?\s*(?:and|but|or|while|whereas|as\s+well)?\s*[.,;]?\s*$", re.I,
)
_LEADING_CONNECTOR_NOISE_RE = re.compile(
    r"^\s*(?:likewise|similarly|correspondingly|in\s+turn)\s*,?\s*", re.I,
)


def _normalize_role_text_for_structural_compare(text: str, self_role: str, other_roles: List[str]) -> str:
    t = text
    for r in sorted((o for o in other_roles if o), key=len, reverse=True):
        t = re.sub(re.escape(r) + r"(?:'s|’s)?", " <OTHER> ", t, flags=re.I)
    if self_role:
        t = re.sub(re.escape(self_role) + r"(?:'s|’s)?", " <SELF> ", t, flags=re.I)
    t = _LEADING_CONNECTOR_NOISE_RE.sub("", t)
    t = _TRAILING_CONNECTOR_NOISE_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def role_texts_structurally_equivalent(local_texts: Dict[str, str]) -> bool:
    """Step 4A.10.4 — general, non-lexical differentiation check. Two (or
    more) named roles' own local text spans are 'structurally equivalent'
    only if, after substituting every role name with a generic <SELF>/
    <OTHER> placeholder, the resulting normalized strings are IDENTICAL —
    i.e. the drafter used the exact same mirrored language for each named
    role, modulo which role is which. This replaces the Step 4A.10.1/
    4A.10.3 approach of scanning for a recognized "differentiating
    qualifier" cue WORD (see _DIFFERENTIATING_QUALIFIER_RE, now retired
    from this safety-boundary role): that approach put the burden of
    proof on detecting a difference, which is itself a closed vocabulary
    problem — every fresh corpus finds a new phrase that differentiates
    treatment without using any recognized cue word (Step 4A.10.3's
    independent 182-case corpus found six such families: defense
    control, monetary treatment, first/third-party, geographic scope,
    cross-reference/schedule, temporal/survival — see
    artifacts/step4a10_3/step4a10_3_final_report.md). This function
    inverts the burden: symmetry requires POSITIVE structural proof the
    two spans say the same thing, not merely the absence of a recognized
    difference. A single role, or no local text, is vacuously equivalent
    (nothing to compare) — this is a comparison primitive only; callers
    remain responsible for deciding whether >=2 comparable roles exist at
    all."""
    roles = list(local_texts.keys())
    if len(roles) < 2:
        return True
    normalized = {
        r: _normalize_role_text_for_structural_compare(local_texts[r], r, [o for o in roles if o != r])
        for r in roles
    }
    base = normalized[roles[0]]
    return all(normalized[r] == base for r in roles[1:])


def detect_role_attributed_asymmetry(
    window: str,
    attribution_re: Pattern[str],
    generic_role_words: Any,
    snapshot_fn: Callable[[str], Dict[str, Any]],
    compare_fn: Callable[[str, Dict[str, Any], str, Dict[str, Any]], List[str]],
    max_chars: int = 220,
    established_equal_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], bool]] = None,
) -> List[str]:
    """Returns a list of human-readable disagreement reasons; empty means
    either fewer than two distinct named-role attributions were found
    (nothing to compare — not itself evidence of asymmetry) or every
    attributed role's snapshot agrees per `compare_fn`.

    `attribution_re` must have exactly one capturing group (the role name).
    `generic_role_words` is checked against the captured role, lowercased.
    `snapshot_fn(local_text) -> dict` builds one role's fact snapshot from
    its own bounded local window. `compare_fn(base_role, base_snapshot,
    other_role, other_snapshot) -> List[str]` compares the first-seen
    role's snapshot against every other role's snapshot pairwise and
    returns zero or more reason strings for that pair. `established_equal_fn(base_snapshot,
    other_snapshot) -> bool`, if given, lets the caller declare that some
    dimension was positively established equal for both roles (real proof
    of sameness despite differing surface wording) — when true for every
    pair, it stands down the structural fail-closed check below, same as
    an explicit equal-treatment cue.
    """
    matches = [m for m in attribution_re.finditer(window) if trim_role_name(m.group(1)).lower() not in generic_role_words]
    if len(matches) < 2:
        return []

    snapshots: Dict[str, Dict[str, Any]] = {}
    local_texts: Dict[str, str] = {}
    for i, m in enumerate(matches):
        role = trim_role_name(m.group(1))
        if role in snapshots:
            continue  # first mention of a role governs
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(window)
        hi = min(len(window), m.end() + max_chars, next_start)
        boundary = re.search(r"\.\s", window[m.end():hi])
        if boundary:
            hi = m.end() + boundary.start() + 1
        local_texts[role] = window[m.end():hi]
        snapshots[role] = snapshot_fn(local_texts[role])

    roles = list(snapshots.keys())
    if len(roles) < 2:
        return []

    reasons: List[str] = []
    base_role = roles[0]
    base_snapshot = snapshots[base_role]
    for role in roles[1:]:
        reasons.extend(compare_fn(base_role, base_snapshot, role, snapshots[role]))
    if reasons:
        return reasons

    # Step 4A.10.4 — general safety net (artifacts/step4a10_4/design.md),
    # superseding the Step 4A.10.1 lexical-cue version. The per-dimension
    # `compare_fn` classifiers are a closed vocabulary and can silently
    # find "nothing to compare" even when the drafter plainly attached
    # DIFFERENT, role-specific language to each named role. The prior
    # version treated an explicit "differentiating qualifier" cue WORD as
    # the trigger for escalation — itself a closed vocabulary that a
    # fresh corpus repeatedly found new phrasing to evade. This version
    # requires POSITIVE structural proof of sameness instead: symmetry is
    # declared only if every attributed role's own local text, once role
    # names are normalized out, is IDENTICAL to every other's. Absence of
    # a recognized difference cue is never itself evidence of symmetry.
    if established_equal_fn is not None and all(
        established_equal_fn(base_snapshot, snapshots[role]) for role in roles[1:]
    ):
        return reasons  # a real dimension was established equal for every pair -- positive proof, safe
    if not role_texts_structurally_equivalent(local_texts):
        return [
            f"{base_role} and {' and '.join(roles[1:])} each have separately-stated "
            f"language attached to their respective obligations that is not structurally "
            f"identical once each role's own name is normalized out — the specific "
            f"comparison checks could not establish these as equivalent, and symmetry "
            f"cannot be assumed"
        ]
    return reasons


class BasePolicyRuleLike(Protocol):
    """The minimum any clause-specific PolicyRule-like object must expose
    for the shared core to route escalation and fallback language. Clause
    adapters define their own richer Protocol (thresholds, required
    exceptions, whatever else the clause needs) that structurally includes
    these three fields — see liability_policy_engine.PolicyRuleLike."""
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]


# ---------------------------------------------------------------------------
# Negotiation ladder
# ---------------------------------------------------------------------------

@dataclass
class LadderStep:
    label: str
    description: str
    status: str  # "passed" | "current" | "not_reached"


def build_ladder(state: str, step_specs: List[Tuple[str, str]]) -> List[LadderStep]:
    """step_specs is a list of (label, description) pairs already in
    LADDER_ORDER sequence (5 entries: ACCEPT/ACCEPT_WITH_NOTE/NEGOTIATE/
    ESCALATE/PROHIBITED positions) — the adapter builds the descriptions
    (which reference clause-specific language like "annual fees"), this
    function only marks passed/current/not_reached from `state`. A state
    outside LADDER_ORDER (REQUIRES_REVIEW, NOT_APPLICABLE) marks nothing
    as current — those states mean no ladder position was reached."""
    steps = [LadderStep(label, description, "not_reached") for label, description in step_specs]
    if state not in LADDER_ORDER:
        return steps
    idx = LADDER_ORDER.index(state)
    for i, step in enumerate(steps):
        step.status = "passed" if i < idx else ("current" if i == idx else "not_reached")
    return steps


# ---------------------------------------------------------------------------
# Threshold classification — the common "three-tier band" pattern behind
# any policy expressed as preferred / acceptable-max / negotiate-max.
# ---------------------------------------------------------------------------

def classify_by_threshold(
    value: float,
    preferred_max: Optional[float],
    acceptable_max: Optional[float],
    negotiate_max: Optional[float],
) -> str:
    """value <= preferred_max -> ACCEPT; <= acceptable_max -> ACCEPT_WITH_NOTE;
    <= negotiate_max -> NEGOTIATE; otherwise ESCALATE. Any threshold left
    None is treated as "not set" (that band is skipped, not treated as
    unlimited) — mirrors the original inline LoL state machine exactly."""
    if preferred_max is not None and value <= preferred_max:
        return ACCEPT
    if acceptable_max is not None and value <= acceptable_max:
        return ACCEPT_WITH_NOTE
    if negotiate_max is not None and value <= negotiate_max:
        return NEGOTIATE
    return ESCALATE


def escalate_to_for_state(state: str, escalation_authority: Optional[str]) -> Optional[str]:
    """Which states carry a named escalation contact — ESCALATE and
    PROHIBITED route to approval; everything else has no escalation target."""
    return escalation_authority if state in (ESCALATE, PROHIBITED) else None


def fallback_text_for_state(state: str, fallback_text: Optional[str], applicable_states: Tuple[str, ...]) -> Optional[str]:
    """Fallback/redline language is only offered for states the adapter
    designates as redline-eligible (e.g. LoL uses MUST_REDLINE, PROHIBITED,
    NEGOTIATE) — passed in by the adapter since which states warrant a
    redline is a clause-specific policy decision, not a core one."""
    return fallback_text if state in applicable_states else None


# ---------------------------------------------------------------------------
# Directional (asymmetric) position resolution
# ---------------------------------------------------------------------------

@dataclass
class PositionCandidate:
    """One named party's position on a clause, reduced to whatever the
    adapter considers comparable. `dedup_key` must be a hashable value two
    equal positions share (e.g. (kind, numeric value) for a cap) — None
    means "no comparable value was extracted for this role" and the
    candidate participates in role-counting but not in the distinctness
    check, mirroring how an unparsed role is still counted but can't prove
    asymmetry on its own."""
    role: str
    side: Optional[str]  # e.g. "buy_side" | "sell_side" | None if unmapped
    dedup_key: Optional[Hashable]
    summary: str


def resolve_directional_position(
    candidates: List[PositionCandidate], contract_side: str,
    *, position_label: str = "asymmetric positions", value_label: str = "position",
) -> Tuple[Optional[PositionCandidate], Optional[Dict[str, str]], Optional[Dict[str, str]], Optional[str]]:
    """Given every named-role position found in a provision, determines
    which one is "ours" per the playbook's configured contract_side.
    Returns (our_candidate, our_position_dict, counterparty_position_dict,
    unresolved_reason).

    `position_label`/`value_label` let an adapter phrase the abstention
    reason in clause-specific terms (e.g. LoL passes position_label=
    "asymmetric liability positions", value_label="cap") without the core
    algorithm knowing anything about liability, indemnification, or any
    other clause concept.

    Never silently returns only the recognized side: fewer than two
    distinct positions means there's no asymmetry to resolve (not an
    error — returns all-None, caller proceeds with the clause's plain
    general position); a mutual policy facing genuine asymmetry, or an
    unmappable role pair under a directional policy, both return a
    specific reason instead of guessing."""
    if len(candidates) < 2:
        return None, None, None, None

    distinct_values = {c.dedup_key for c in candidates if c.dedup_key is not None}
    if len(distinct_values) <= 1:
        return None, None, None, None  # all sides state the same position — not asymmetric

    if contract_side == "mutual":
        return None, None, None, (
            f"contract defines {position_label} by party, but this playbook is configured "
            f"for a mutual position — cannot determine which {value_label} applies to us"
        )

    ours = [c for c in candidates if c.side == contract_side]
    theirs = [c for c in candidates if c.side is not None and c.side != contract_side]
    if len(ours) != 1 or len(theirs) != 1:
        return None, None, None, (
            f"contract defines {position_label} but the named parties "
            "(" + ", ".join(c.role for c in candidates) + ") could not be confidently mapped "
            f"to our configured contract side ({contract_side})"
        )

    our_c, their_c = ours[0], theirs[0]
    our_dict = {"role": our_c.role, "summary": our_c.summary}
    their_dict = {"role": their_c.role, "summary": their_c.summary}
    return our_c, our_dict, their_dict, None


# ---------------------------------------------------------------------------
# Decision + evidence
# ---------------------------------------------------------------------------

@dataclass
class PolicyDecision:
    rule_id: str
    clause_type: str
    state: str
    contract_language: str
    extracted_summary: str
    policy_limit_summary: str
    required_action: str
    explanation: str
    negotiation_ladder: List[LadderStep]
    category_treatments: List[Dict[str, str]]  # clause-agnostic list of sub-treatments (carve-outs, etc.)
    unresolved_facts: List[str]
    start_index: Optional[int]
    end_index: Optional[int]
    escalate_to: Optional[str] = None
    fallback_text: Optional[str] = None
    source: Optional[str] = None
    controlling_provision: Optional[Dict[str, str]] = None
    our_position: Optional[Dict[str, str]] = None
    counterparty_position: Optional[Dict[str, str]] = None
    reconciliation: Optional[str] = None
    # Evidence-report labels — default values reproduce the original LoL
    # wording exactly; other adapters override these rather than the core
    # ever guessing what to call a clause-specific concept ("liability",
    # "exposure", "cap", ...).
    summary_label: str = "General cap"
    our_position_label: str = "Our liability"
    counterparty_position_label: str = "Counterparty cap"
    # A small, explicitly-registered set of already-computed *Facts values
    # that have no natural home in category_treatments/controlling_provision/
    # our_position/counterparty_position but a downstream consumer (the
    # Interaction Engine — see interaction_engine_core.py) needs at the
    # decision level, without re-deriving anything from raw text. This is
    # NOT a general-purpose dumping ground: only the keys listed in
    # INTERACTION_FACT_REGISTRY below may appear here, only for the clause
    # types that register them, and only adapters explicitly documented as
    # populating it do so — every other adapter leaves this at its default
    # {} and is unaffected. Every value is either an already-computed
    # *Facts attribute passed through unchanged, or None — never inferred,
    # never re-parsed, never computed from anything the adapter's own
    # extract_*_facts function didn't already establish.
    interaction_facts: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "clause_type": self.clause_type,
            "state": self.state,
            "contract_language": self.contract_language,
            "extracted_summary": self.extracted_summary,
            "policy_limit_summary": self.policy_limit_summary,
            "required_action": self.required_action,
            "explanation": self.explanation,
            "negotiation_ladder": [
                {"label": s.label, "description": s.description, "status": s.status}
                for s in self.negotiation_ladder
            ],
            "category_treatments": self.category_treatments,
            "unresolved_facts": self.unresolved_facts,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "escalate_to": self.escalate_to,
            "fallback_text": self.fallback_text,
            "source": self.source,
            "controlling_provision": self.controlling_provision,
            "our_position": self.our_position,
            "counterparty_position": self.counterparty_position,
            "reconciliation": self.reconciliation,
            "interaction_facts": self.interaction_facts,
        }

    def render_evidence_report(self) -> str:
        """Human-readable provenance block — the format a lawyer can point
        to as the basis for the decision, e.g.:

            PROHIBITED
            Controlling provision: Section 12.4 — Limitation of Liability
            General cap: 2x fees paid in preceding 12 months
            ...
            Result: PROHIBITED
            Evidence: "<exact contract language>"
        """
        lines = [self.state]
        if self.controlling_provision:
            lines.append(f"Controlling provision: {self.controlling_provision['label']}")
        lines.append(f"{self.summary_label}: {self.extracted_summary}")
        for ct in self.category_treatments:
            if ct["treatment"] not in ("not_addressed",):
                lines.append(f"{ct['category'].replace('_', ' ').title()}: {ct['treatment'].replace('_', ' ').title()}"
                              + (f" ({ct['cap_summary']})" if ct.get("cap_summary") else ""))
        if self.counterparty_position:
            lines.append(f"{self.counterparty_position_label}: {self.counterparty_position['summary']}")
        if self.our_position:
            lines.append(f"{self.our_position_label}: {self.our_position['summary']}")
        if self.source:
            lines.append(f"Playbook: {self.source}")
        lines.append(f"Policy: {self.policy_limit_summary}")
        lines.append(f"Result: {self.state}")
        lines.append(f'Evidence: "{self.contract_language}"')
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# interaction_facts registry — the exhaustive, reviewed list of every key
# any adapter is permitted to populate on PolicyDecision.interaction_facts,
# added for the Interaction Engine (see docs/architecture/
# interaction_engine_v1_design.md and interaction_engine_core.py). A key
# not listed here is a bug, not a convenience — this module never grows an
# open-ended fact bag; every entry was added because a specific, approved
# interaction rule needs a specific, already-computed *Facts value that has
# no natural home in category_treatments/controlling_provision/our_position/
# counterparty_position. Each entry documents its exact type and semantics,
# in particular that None is a distinct, meaningful value ("the contract
# never addressed this") and must never be conflated with False.
INTERACTION_FACT_REGISTRY: Dict[str, Dict[str, str]] = {
    "payment_terms": {
        "disputed_amounts_withholdable": (
            "Optional[bool] — mirrors PaymentFacts.disputed_amounts_withholdable "
            "unchanged: True if the clause affirmatively establishes a right to "
            "withhold disputed amounts, False if it affirmatively denies one, "
            "None if the clause never addresses it."
        ),
        "service_credit_present": (
            "Optional[bool] — mirrors PaymentFacts.service_credit_present "
            "unchanged: presence-only signal that payment terms reference a "
            "service credit mechanism; carries no percentage/basis/cap detail "
            "by design (see sla_policy_engine.py's module docstring — SLA owns "
            "the service-credit mechanism, payment_terms only notices it)."
        ),
    },
    "sla": {
        "service_credit_present": (
            "Optional[bool] — mirrors SLAFacts.service_credit_present "
            "unchanged: presence-only signal that the SLA clause references a "
            "service credit remedy."
        ),
    },
}


def validate_interaction_facts(clause_type: str, interaction_facts: Dict[str, Any]) -> None:
    """Fails loudly (AssertionError) if an adapter populates a key not in
    INTERACTION_FACT_REGISTRY for its own clause type — the enforcement
    half of the registry-is-exhaustive contract described above. Adapter
    benchmark/unit test suites call this on every decision they produce;
    it is deliberately not called inside PolicyDecision itself (evaluate_*_
    policy stays a pure function with no import-time dependency surprises)."""
    allowed = set(INTERACTION_FACT_REGISTRY.get(clause_type, {}))
    unexpected = set(interaction_facts) - allowed
    if unexpected:
        raise AssertionError(
            f"{clause_type!r} PolicyDecision.interaction_facts contains unregistered "
            f"key(s) {sorted(unexpected)} — add them to INTERACTION_FACT_REGISTRY "
            f"in policy_engine_core.py first, with documented type/semantics."
        )


# ---------------------------------------------------------------------------
# Benchmark safety metrics — shared by every clause adapter's benchmark
# harness (see benchmarks/run_liability_benchmark.py for the first use).
# ---------------------------------------------------------------------------

FALSE_SAFE_EXPECTED_STATES = {NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE, REQUIRES_REVIEW}
FALSE_SAFE_ACTUAL_STATES = {ACCEPT, ACCEPT_WITH_NOTE}


def is_false_safe(expected_state: str, actual_state: str) -> bool:
    """The catastrophic failure mode: the correct answer required attorney
    attention but the engine returned ACCEPT/ACCEPT_WITH_NOTE."""
    return expected_state in FALSE_SAFE_EXPECTED_STATES and actual_state in FALSE_SAFE_ACTUAL_STATES


def is_false_escalation(expected_state: str, actual_state: str) -> bool:
    """The "annoying automation" failure mode: the correct answer was
    clear-cut but the engine sent it to REQUIRES_REVIEW anyway. A system
    that hits zero false-safe by refusing to ever decide isn't safe, it's
    just unhelpful — this is the metric that would catch that."""
    return expected_state != REQUIRES_REVIEW and actual_state == REQUIRES_REVIEW


def decision_hash(decision: PolicyDecision) -> str:
    """Stable hash of a decision's full output — used to verify the
    reproducibility guarantee (same input -> byte-identical output)."""
    return hashlib.sha256(json.dumps(decision.as_dict(), sort_keys=True).encode()).hexdigest()


def check_deterministic(evaluate_once: Callable[[], PolicyDecision], repeats: int = 5) -> bool:
    """Calls `evaluate_once` `repeats` times and confirms every call
    produces a byte-identical decision (via decision_hash)."""
    hashes = {decision_hash(evaluate_once()) for _ in range(repeats)}
    return len(hashes) == 1
