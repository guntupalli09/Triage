"""
Limitation-of-Liability clause adapter, over policy_engine_core.

This module owns everything specific to liability caps: finding LoL-
anchored provisions in a document and reconciling multiple ones, the typed
CapExpression model (simple/greater-of/lesser-of/per-claim-and-aggregate),
category carve-out classification, consequential-damages detection,
cross-reference resolution, and named-party position extraction. It owns
no part of the decision model, evidence structure, ladder mechanics, or
directional-resolution algorithm — those live in policy_engine_core.py and
are shared with every other clause adapter.

Three architectural commitments distinguish this from a naive "find a
number, compare it" extractor, each driven by a real failure the benchmark
corpus surfaced (see benchmarks/liability_benchmark_report.md):

1. DOCUMENT-WIDE PROVISION DISCOVERY. A contract can contain more than one
   Limitation of Liability provision — a later exhibit, schedule, or an
   amendment that explicitly restates the clause. Scanning only a fixed
   window from the first occurrence is not a simplification, it is a blind
   spot: a superseding cap placed past that window is invisible, and the
   engine will confidently accept a stale, superseded number. This module
   finds every LoL-anchored provision in the full document and reconciles
   them deterministically (an explicit amendment/restatement supersedes;
   consistent duplicates agree; anything else is unreconciled) rather than
   ever silently preferring the first one found.

2. TYPED CAP REPRESENTATION. A liability cap is not always one number.
   "The greater of $1M or 2x fees," "1x per claim, 3x in the aggregate,"
   and a plain "2x annual fees" are different structures, and collapsing
   the first two into a single extracted multiplier produces a
   deterministic but wrong answer — worse than admitted uncertainty,
   because the product presents it as authoritative. CapExpression
   represents simple, greater-of, lesser-of, and per-claim/aggregate
   structures explicitly; only a structure that reduces to one comparable
   value under the policy's basis is evaluated, everything else is
   REQUIRES_REVIEW with the specific reason recorded.

3. DIRECTIONAL (ASYMMETRIC) POSITIONS. When a contract states different
   caps — or an uncapped position — for each named party, there is no
   single "the cap" to extract. PartyPosition tracks each side
   independently; policy_engine_core.resolve_directional_position maps
   "us" from the playbook's configured contract_side and never silently
   evaluates whichever side's language happened to be easier to parse
   while ignoring the other.

Every decision states, deterministically, no confidence score at any
branch: ACCEPT / ACCEPT_WITH_NOTE / NEGOTIATE / MUST_REDLINE / PROHIBITED /
ESCALATE / REQUIRES_REVIEW / NOT_APPLICABLE — and carries the evidence that
produced it: which provision controls, what was extracted, and why.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE, LADDER_ORDER,
    LadderStep, PolicyDecision, PositionCandidate,
    build_ladder as _core_build_ladder,
    classify_by_threshold, escalate_to_for_state, fallback_text_for_state,
    resolve_directional_position as _core_resolve_directional_position,
    resolve_role_side as _core_resolve_role_side,
    side_for_role as _core_side_for_role,
    excerpt as _excerpt, section_label_before as _section_label_before,
    requires_review_explanation, requires_review_required_action,
    trim_role_name,
    CHAINED_DELEGATION_RE as _core_chained_delegation_re,
    CONDITIONAL_UNVERIFIED_PRECONDITION_RE as _core_conditional_unverified_precondition_re,
    WORD_NUMBERS as _core_word_numbers,
    SELF_FLAGGED_UNRESOLVED_RE as _core_self_flagged_unresolved_re,
    ConditionEvidence,
    detect_condition_in_span as _core_detect_condition_in_span,
    detect_condition_in_text as _core_detect_condition_in_text,
    detect_conflicting_backward_conditions as _core_detect_conflicting_backward_conditions,
    is_operative_context as _core_is_operative_context,
    document_wide_conflict_detected as _document_wide_conflict_detected,
    unreconciled_ambiguity_marker_present as _unreconciled_ambiguity_marker_present,
)

RULE_ID = "POLICY_LOL_CAP"

# Typed cap basis — what a multiplier cap is a multiple OF. Only BASIS_FEES
# is comparable to a policy threshold (defined as "Nx annual fees"); every
# other basis is preserved with its exact source language but routed to
# REQUIRES_REVIEW rather than silently compared as if it were fee-based.
BASIS_FEES = "FEES"
BASIS_PURCHASE_PRICE = "PURCHASE_PRICE"
BASIS_CONTRACT_VALUE = "CONTRACT_VALUE"
BASIS_FIXED_AMOUNT = "FIXED_AMOUNT"
BASIS_OTHER = "OTHER"
BASIS_UNRESOLVED = "UNRESOLVED"
# Step 4A.5 Priority 4 — a recurring PERIODIC payment stream under the
# agreement (royalties, premium, rent, service charges) plays the exact
# same structural role as "fees" wherever it is the contract's own sole
# periodic payment basis: "2x annual royalties" in a franchise agreement
# and "2x annual fees" in a services agreement are the same policy
# concept expressed with the domain's own vocabulary for that payment.
# This is NOT the same as BASIS_PURCHASE_PRICE/BASIS_CONTRACT_VALUE,
# which are one-time/aggregate transaction values, not a recurring
# per-period payment — those remain genuinely non-comparable. See
# evaluate_liability_policy's basis gate for the negative control this
# is gated on (a document that ALSO separately states a distinct "fees"
# quantity stays non-comparable — two different payment streams cannot
# be silently treated as the same one).
BASIS_RECURRING_PAYMENT = "RECURRING_PAYMENT"

CATEGORIES = [
    "data_breach", "ip_infringement", "confidentiality",
    "indemnification", "fraud", "gross_negligence", "willful_misconduct",
]
EXCEPTION_TYPES = list(CATEGORIES)

_CATEGORY_KEYWORD_RE = {
    "data_breach": re.compile(r"\bdata breach(?:es)?\b|\bsecurity breach(?:es)?\b", re.I),
    "ip_infringement": re.compile(
        r"\bintellectual property\b.{0,40}\binfringement\b|\bIP infringement\b|\binfringement of\b.{0,40}\bintellectual property\b",
        re.I,
    ),
    "confidentiality": re.compile(r"\bconfidentiality\b|\bconfidential information\b", re.I),
    "indemnification": re.compile(r"\bindemnif\w*\b", re.I),
    "fraud": re.compile(r"\bfraud(?:ulent)?\b", re.I),
    "gross_negligence": re.compile(r"\bgross negligence\b", re.I),
    "willful_misconduct": re.compile(r"\bwil[l]?ful misconduct\b", re.I),
}

# Step 4A.9 — moved to policy_engine_core.py as the shared, adapter-
# agnostic number-parsing primitive (WORD_NUMBERS); aliased here so every
# existing call site in this file is unchanged. See that module's comment
# for why number parsing is shared while basis-noun vocabulary stays
# adapter-local.
_WORD_NUMBERS = _core_word_numbers

# Provision discovery, in the same two-layer style the other five engines
# use (a broad anchor pattern + local disqualifiers — cf.
# termination_policy_engine._ANCHOR_RE / indemnification_policy_engine's
# "\bno\s+$" lookback filter).
#
# Layer 1 — the labelled anchor: a heading or self-reference that names the
# provision outright.
_ANCHOR_RE = re.compile(r"limitation\s+of\s+liability|liability\s+cap|^liability\s+terms\s*$", re.I | re.M)

# Layer 2 — drafting anchors: the operative sentence patterns commercial
# liability caps are actually written in, for the (very common) case where
# the clause carries no heading at all — a pasted redline excerpt, an email
# thread, an order-form rider. Before this existed, extract_liability_facts
# returned None for any liability limitation that didn't literally contain
# the words "limitation of liability" or "liability cap", producing a
# confident, false "this contract does not address liability caps" on
# genuinely adverse language (UX walkthrough P0-3).
#
# Every alternative requires the word "liability" adjacent to a cap/exclusion
# verb phrase — never "liability" alone — so provisions that merely mention
# liability in passing (indemnities, insurance covenants, joint-and-several
# allocations, governing-law sentences) are not misclassified as
# limitation-of-liability provisions. See _SECONDARY_DISQUALIFIER_RE for the
# local-context guard on top of that.
_SECONDARY_ANCHOR_RE = re.compile(
    # "<Party>'s aggregate/total/maximum/cumulative/overall liability ..."
    r"\b(?:aggregate|total|maximum|cumulative|overall|entire)\s+liability\b"
    # "... liability shall not exceed / is capped at / is limited to ..."
    r"|\bliability\b(?:\s+[\w'’]+){0,8}?\s+(?:shall\s+not\s+exceed|shall\s+in\s+no\s+event\s+exceed"
    r"|(?:is|are|shall\s+be)\s+(?:capped|limited)\s+(?:at|to)|(?:is|are|shall\s+be)\s+capped\b)"
    # "in no event shall <Party> be liable ... in excess of / exceed ..."
    r"|in\s+no\s+event\s+shall(?:\s+[\w'’]+){0,6}?\s+liability\s+exceed"
    # "liability shall be unlimited" / "unlimited liability" / "uncapped liability"
    r"|\bunlimited\s+liability\b|\bliability\s+shall\s+be\s+unlimited\b"
    r"|\buncapped\s+liability\b|\bliability\s+(?:shall\s+be|is|remains?)\s+uncapped\b"
    # "no cap/limit on liability"
    r"|\bno\s+(?:cap|limit(?:ation)?)\s+(?:on|of)\s+liability\b"
    # Step 4A.5 Priority 3 — the same concept (a financial responsibility
    # ceiling for claims) stated using "exposure" or "recovery against" in
    # place of "liability": "<Party>'s (maximum/aggregate) exposure ...
    # shall be restricted to/is fixed at ...", "any recovery against
    # <Party> ... is limited to a sum not to exceed ...". Each alternative
    # still requires the SAME cap-verb-phrase structure as the
    # liability-worded alternatives above (never a bare "exposure" or
    # "recovery" alone), so this does not make the anchor fire on
    # unrelated uses of those common words (e.g. "market exposure",
    # "recovery of costs").
    r"|\b(?:aggregate|total|maximum|cumulative|overall|entire)?\s*exposure\b.{0,150}?"
    r"(?:shall\s+be\s+restricted\s+to|is\s+restricted\s+to|shall\s+not\s+exceed|is\s+fixed\s+at)"
    r"|\bany\s+recovery\s+against\b.{0,200}?\bis\s+limited\s+to\s+a\s+sum\s+not\s+to\s+exceed\b",
    re.I,
)

# Local-context disqualifiers for a LAYER-2 anchor only (never applied to an
# explicitly labelled provision): contexts where cap-shaped language around
# the word "liability" belongs to a different kind of provision. Insurance
# covenants are the important one — "commercial general liability insurance
# with limits of not less than $2,000,000" is a coverage requirement, not a
# limitation of the counterparty's liability to us.
_SECONDARY_DISQUALIFIER_RE = re.compile(
    r"\binsurance\b|\binsurer\b|\bcoverage\s+limits?\b|\bpolicy\s+of\s+insurance\b",
    re.I,
)
_SECONDARY_LOCAL_WINDOW = 200
# How far back a layer-2 anchor's provision window is extended so the
# operative sentence isn't truncated mid-clause (the anchor typically lands
# on the cap phrase itself, several words into the sentence).
_SECONDARY_LOOKBACK = 400
_UNLIMITED_RE = re.compile(
    r"unlimited liability|no limit(?:ation)?\s+(?:on|of)\s+liability"
    r"|liability shall not be limited|without limitation as to (?:the )?amount"
    r"|shall have unlimited liability"
    r"|remains?\s+uncapped|shall\s+(?:be|remain)\s+uncapped"
    r"|not subject to any (?:cap|limit)(?:ation)?"
    r"|there (?:is|shall be) no (?:cap|limit)(?:ation)?",
    re.I,
)
# Step 4A.7 — "amounts paid or payable" added to the closed basis-word
# family: the same recurring/aggregate-payment concept as "fees"/"charges"
# already in this list, just a more generic noun for it. Still a closed
# enumeration, not an open vocabulary net.
_BASIS_WORD_FRAGMENT = r"(fees?|purchase price|contract value|order form value|rent|royalt(?:y|ies)|premiums?|charges?|amounts?\s+paid\s+or\s+payable)"
# Step 4A.7 — Priority 3 remediation (Step 4A.6 Section F.1 / the single
# largest repeated WC mechanism found: ~32 cases across Tiers 1-3). The
# basis-word match previously required the basis noun (fees/rent/royalty/
# premiums/charges) to appear IMMEDIATELY after "annual"/"total"/
# "aggregate" — real commercial drafting routinely qualifies that noun with
# a domain-specific modifier ("annual DISTRIBUTION fees", "annual
# INSTALLATION fees", "annual FRANCHISE ROYALTY fees", "annual STORAGE
# fees"), and the modifier's mere presence caused the entire cap to
# disappear (general_cap_expression.components stayed empty, and the
# adapter then reported "no numeric general cap stated" — a confident,
# wrong MUST_REDLINE on a contract that has a clean, quantified cap).
# The general invariant (per the governing remediation instructions):
# modifiers INSIDE the quantum must not cause the whole cap to vanish.
# Tolerating 0-2 additional capitalized-or-lowercase words between the
# temporal qualifier and the basis noun is a bounded capacity increase —
# not an enumeration of specific modifier nouns — and does not touch
# candidate OWNERSHIP/association at all (a separate, already-tested
# mechanism — see run_liability_ownership_benchmark.py, unaffected by
# this change and re-run clean in Step 4A.7 Phase 7). See
# benchmarks/step4a7_liability_basis_benchmark.py (60+ cases: ordinary
# qualified bases, negative controls, false-association checks).
# Step 4A.7.1: hyphenated modifiers ("crop-purchase price") tolerated —
# [\w-]+ instead of \w+ — same bounded capacity increase, not a new
# vocabulary entry.
_BASIS_MODIFIER_FRAGMENT = r"(?:[\w-]+\s+){0,2}"
_MULTIPLIER_NUM_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:the\s+)?(?:total\s+|aggregate\s+)?(?:annual\s+)?"
    + _BASIS_MODIFIER_FRAGMENT + _BASIS_WORD_FRAGMENT
    + r"(?:\s+paid)?(?:\s+(?:in|during)\s+the\s+(?:twelve|12)\s*\(?12\)?\s*months?)?",
    re.I,
)
_MULTIPLIER_WORD_RE = re.compile(
    r"\b(" + "|".join(_WORD_NUMBERS) + r")\s*(?:\(\d+\))?\s*times?\s*(?:the\s+)?(?:total\s+|aggregate\s+)?"
    r"(?:annual\s+)?" + _BASIS_MODIFIER_FRAGMENT + _BASIS_WORD_FRAGMENT,
    re.I,
)


_RECURRING_PAYMENT_BASIS_WORDS_RE = re.compile(r"royalt|premium|\brent\b|charges?", re.I)


def _classify_basis(basis_word: str) -> str:
    w = basis_word.lower()
    if "fee" in w:
        return BASIS_FEES
    if "purchase price" in w:
        return BASIS_PURCHASE_PRICE
    if "contract value" in w:
        return BASIS_CONTRACT_VALUE
    if _RECURRING_PAYMENT_BASIS_WORDS_RE.search(w):
        return BASIS_RECURRING_PAYMENT
    return BASIS_OTHER
# Fee-period caps ("six (6) months of fees", "fees paid or payable ... twelve
# months") are first-class CapValue.kind == "fee_period". They must be found
# here — not recovered later by re-parsing a truncated provision excerpt —
# so symbolic months survive into LoL v2 without converting to money.
_FEE_PERIOD_WORD_ALT = "|".join(sorted(_WORD_NUMBERS.keys(), key=len, reverse=True))
_FEE_PERIOD_DURATION_RE = re.compile(
    rf"\b(\d+(?:\.\d+)?|{_FEE_PERIOD_WORD_ALT})\s*(?:\(\d+\))?\s*[-\s']*(years?|months?)'?\s*"
    r"(?:of\s+)?(?:worth\s+of\s+)?fees?\b",
    re.I,
)
_FEE_PERIOD_TRAILING_RE = re.compile(
    rf"fees?\s+(?:paid(?:\s+or\s+payable)?|payable).{{0,120}}?"
    rf"(\d+(?:\.\d+)?|{_FEE_PERIOD_WORD_ALT})\s*(?:\(\d+\))?\s*months?\b"
    r"|"
    rf"(?:twelve|12|\d+(?:\.\d+)?|{_FEE_PERIOD_WORD_ALT})\s*(?:\(\d+\))?\s*months?\s+"
    rf"(?:preceding|prior|before|immediately\s+preceding).{{0,60}}?fees?",
    re.I,
)


def _parse_fee_period_number_token(token: str) -> Optional[float]:
    try:
        return float(token)
    except ValueError:
        key = token.lower()
        return float(_WORD_NUMBERS[key]) if key in _WORD_NUMBERS else None


def _parse_fee_period_months_from_duration(match: re.Match) -> Optional[float]:
    n = _parse_fee_period_number_token(match.group(1))
    if n is None:
        return None
    unit = match.group(2).lower().rstrip("s")
    return n * 12.0 if unit == "year" else float(n)


def _parse_fee_period_months_from_trailing(match: re.Match) -> Optional[float]:
    token = match.group(1) if match.lastindex else None
    if token:
        return _parse_fee_period_number_token(token)
    # Second alternative may omit a capture; recover twelve/12 from the span.
    span = match.group(0)
    if re.search(r"\b(?:twelve|12)\b", span, re.I):
        return 12.0
    return None


_FIXED_AMOUNT_RE = re.compile(
    r"(?:maximum(?:\s+aggregate)?\s+liability(?:\s+of\s+(?:either\s+party)?)?\s*(?:shall\s+not\s+exceed|shall\s+exceed|exceed|of|:)?"
    r"|liable\s+for\s+(?:an\s+amount\s+)?(?:in\s+excess\s+of|more\s+than)"
    # Step 4A.7.1 (Step 4A.6/4A.7 A6-L-04): "shall not be liable TO
    # [Party] FOR [damages-noun] EXCEEDING $X" — the object-phrasing
    # variant of the same fixed-cap concept, distinguished from the
    # existing "liable for...in excess of/more than $X" alternative only
    # by which preposition/participle introduces the amount ("exceeding"
    # vs. "in excess of"/"more than") and by an optional intervening
    # "to [Party]" clause. Same bounded concept, not a new trigger family.
    r"|liable\s+(?:to\s+(?:\w+\s+){1,4})?for\s+(?:\w+\s+){0,3}exceeding"
    r"|limited\s+to"
    r"|(?:is\s+)?capped\s+at"
    r"|is\s+fixed\s+at"
    r"|(?:a\s+)?cap(?:\s+\w+){0,4}\s+(?:of|is)"
    r"|(?:greater|lesser)\s+of"
    r"|in\s+no\s+event\s+shall(?:\s+[\w']+){0,8}\s+exceed"
    r"|shall(?:\s+in\s+the\s+aggregate)?\s+not\s+exceed"
    # A self-defined term ("the Liability Cap Amount") whose value is
    # stated in a trailing clause rather than inline at the cap sentence
    # itself: "...limited to the Liability Cap Amount, which the parties
    # agree is $1,500,000." Step 4A.7.1 (A6-L-43): tolerate a short
    # interposed clause ("...which the parties agree, for purposes of
    # this Agreement, is $X") between "agree" and "is" — the same
    # bounded defined-term-delegation shape, just with an ordinary
    # parenthetical aside inserted, a general grammatical relaxation
    # (any short interposed clause) not a specific-phrase patch.
    r"|(?:cap|amount|limit)\b[^.$]{0,40}?,\s*which(?:\s+the\s+parties)?(?:\s+agree)?(?:,\s*[^,.$]{0,50},)?\s+is)"
    r"\s*\$\s*([\d,]+(?:\.\d{2})?)",
    re.I,
)
_BARE_OR_FIXED_AMOUNT_RE = re.compile(r"\bor\s*\$\s*([\d,]+(?:\.\d{2})?)", re.I,
)
_EXCLUSION_SIGNAL_RE = re.compile(
    r"shall not apply to|does not apply to"
    r"|excluded from (?:this|the foregoing|such) limitation"
    r"|shall not be subject to (?:the foregoing|such|this) limitation"
    r"|there shall be no limitation"
    r"|not subject to the (?:cap|limitation)s?(?:\s+set forth| described)?(?:\s+above|\s+herein|\s+in this section)?"
    r"|except for (?:breaches? of )?|other than|excluding (?:breaches? of )?|with the exception of",
    re.I,
)
_CAP_TRIGGER_RE = re.compile(
    r"shall not exceed|is capped at|shall be capped|limited to|shall not be liable for", re.I,
)
_AMBIGUITY_SIGNAL_RE = re.compile(
    r"notwithstanding|provided,?\s+however|except as otherwise (?:set forth|provided)|subject to the foregoing",
    re.I,
)
_MUTUAL_PHRASE_RE = re.compile(r"\beither party\b|\bboth parties\b|\bneither party\b", re.I)
_ROLE_POSITION_RE = re.compile(
    # No blanket re.I: [A-Z] must stay case-SENSITIVE, or Python's
    # IGNORECASE (which applies to character classes, not just literals)
    # lets it match lowercase too — e.g. "maximum" in "Supplier's maximum
    # aggregate liability shall not exceed..." or "occurrence"/"annual" in
    # "per-occurrence liability is capped at... annual liability is capped
    # at..." get captured as if they were party role names, producing
    # spurious PartyPositions and a misleading "asymmetric positions by
    # party" reason for clauses that have nothing to do with two parties.
    # See tests/test_liability_policy_engine.py::TestRolePositionRegexCaseSensitivity
    # and benchmarks/liability_benchmark_report.md for the specific
    # corpus case this changes. The verb-phrase literals alone are scoped
    # case-insensitive via (?i:...) so "Shall"/"SHALL"/"shall" still match.
    r"([A-Z][A-Za-z]{2,20})(?:'s)?\s+(?i:aggregate\s+|maximum\s+)?liability\s+(?i:under this Agreement\s+)?"
    r"(?i:shall not exceed|is (?:capped|limited) (?:at|to)|shall be (?:capped|limited) (?:at|to)"
    r"|is not subject to|shall not be liable for)"
)
_CONSEQUENTIAL_RE = re.compile(r"\b(consequential|indirect|special|incidental|punitive)\b[^.]{0,60}\bdamages\b", re.I)
_EXCLUDE_PHRASE_RE = re.compile(
    r"shall not be liable for"
    r"|no party shall be liable"
    r"|neither party shall be liable"
    r"|in no event shall\s+(?:\w+\s+){0,3}be liable"
    r"|(?:are|is|shall be) excluded"
    r"|excludes? (?:any|all)?\s*(?:consequential|indirect|special|incidental|punitive)",
    re.I,
)
_CARVEOUT_PHRASE_RE = re.compile(r"except for|other than|excluding breaches of|with respect to", re.I)
_AMENDMENT_SIGNAL_RE = re.compile(
    r"hereby amended|amended and restated|amends and restates|is amended to read|is hereby amended"
    r"|supersed(?:e|ing|ed)s?|shall supersede",
    re.I,
)

# Cross-reference detection: the LoL provision delegates or modifies its cap
# through another named provision instead of stating one directly. Each
# pattern with a capture group names the referenced location so it can be
# located and, if unambiguous, resolved deterministically — never guessed
# at when multiple candidate targets exist (see _resolve_cross_reference).
_CROSS_REF_TARGET_PATTERNS = [
    re.compile(r"(?:as\s+)?set\s+forth\s+in\s+(Schedule\s+[A-Z0-9]+|Exhibit\s+[A-Z0-9]+|Appendix\s+[A-Z0-9]+|Section\s+\d+(?:\.\d+)?)", re.I),
    re.compile(r"(?:as\s+)?set\s+forth\s+in\s+(the\s+(?:applicable\s+)?Order\s+Form)", re.I),
    re.compile(r"(?:as\s+)?set\s+forth\s+in\s+(the\s+DPA|the\s+Data\s+Processing\s+Addendum)", re.I),
    re.compile(r"governed\s+(?:exclusively\s+)?by\s+(Schedule\s+[A-Z0-9]+|Exhibit\s+[A-Z0-9]+)", re.I),
    re.compile(r"\bsee\s+(Schedule\s+[A-Z0-9]+|Exhibit\s+[A-Z0-9]+|Appendix\s+[A-Z0-9]+)", re.I),
    re.compile(r"incorporated(?:\s+herein)?\s+by\s+reference", re.I),  # no target name captured
]
_CROSS_REF_RESOLUTION_WINDOW = 2000

_PROVISION_WINDOW_CHARS = 3000
_LOCAL_WINDOW_CHARS = 180
# Step 4A: exclusion-coverage boundary search range and its bounded
# fallback — see _compute_exclusion_coverage. _EXCLUSION_COVERAGE_SEARCH_CHARS
# is how far to look for an actual sentence/clause boundary before giving
# up; _EXCLUSION_COVERAGE_FALLBACK_CHARS is the old fixed-width behavior,
# used only when no boundary exists at all within the search range.
_EXCLUSION_COVERAGE_SEARCH_CHARS = 600
_EXCLUSION_COVERAGE_FALLBACK_CHARS = 100
_ANCHOR_DEDUP_GAP = 300  # a second anchor this close to a prior one is the same clause, not a new provision
_GREATER_LESSER_RE = re.compile(
    # Step 4A.9 (S48-L-T2-07) — "whichever AMOUNT/FIGURE/VALUE is greater"
    # tolerates a single interposed noun between "whichever" and "is",
    # which the original "whichever is (the) greater" phrasing didn't.
    r"(?P<greater>greater of|whichever\s+(?:\w+\s+)?is\s+(?:the\s+)?(?:greater|higher))"
    r"|(?P<lesser>lesser of|whichever\s+(?:\w+\s+)?is\s+(?:the\s+)?(?:lesser|lower))",
    re.I,
)
_PER_CLAIM_RE = re.compile(r"per[\s-]claim|per[\s-]occurrence|(?:individual|single|each) claim", re.I)
_AGGREGATE_SCOPE_RE = re.compile(r"\baggregate\b|in the aggregate|across all claims|total liability", re.I)

# Step 4A.5 — the multiplier itself can be unambiguous (e.g. "1 times the
# annual fees paid") while the VALUE it multiplies is stated ambiguously
# elsewhere in the same provision ("...'the annual fees paid' may refer to
# fees paid under the current Order Form or, if greater, the cumulative
# fees paid across all Order Forms..."). This is a different structure
# than _GREATER_LESSER_RE's "greater of $X or $Y" (which compares two
# already-computed cap VALUES) — here the ambiguity is in what the BASIS
# quantity even is, so the multiplier cannot be applied to a single known
# number at all.
_BASIS_VALUE_AMBIGUITY_RE = re.compile(
    r"may\s+(?:refer\s+to|mean)\s+.{0,100}?\bor,?\s+if\s+(?:greater|lesser|higher|lower),?\s+",
    re.I,
)

# Step 4A.7.1 remediation (A6-L-52) — a single-provision cap sentence can
# name BOTH the obligor and the beneficiary directly ("Grantee's aggregate
# liability to Grantor shall not exceed..."). Unlike indemnification, this
# adapter's cap-resolution path has no role-attribution awareness at all
# for a bare single-cap sentence — the cap VALUE is trusted regardless of
# whether either named role can actually be identified. When NEITHER role
# resolves to a side via the generic vocabulary NOR via a document-specific
# definition (resolve_role_side returns (None, None) for both — genuinely
# unmapped, not merely a detected conflict, which is a separate, already-
# escalated case), role identity cannot be confirmed, and if it could
# matter for interpreting the clause, the cap must not resolve silently.
# See benchmarks/step4a7_2_role_attribution_benchmark.py for the positive
# controls (ordinary Buyer/Seller/Vendor/Client/Licensor/Licensee names,
# and names with a document-specific but resolvable definition) this must
# NOT fire on.
_CAP_SENTENCE_ROLE_PAIR_RE = re.compile(
    r"(?-i:([A-Z][A-Za-z]{2,25}))(?:'s)?\s+(?i:aggregate\s+|maximum\s+)?liability\s+to\s+"
    r"(?-i:([A-Z][A-Za-z]{2,25}))\s+"
    r"(?i:shall\s+not\s+exceed|is\s+(?:capped|limited)\s+(?:at|to)|shall\s+be\s+(?:capped|limited)\s+(?:at|to))",
)


def _unmapped_cap_role_pair_reason(window: str, document_text: str) -> Optional[str]:
    m = _CAP_SENTENCE_ROLE_PAIR_RE.search(window)
    if not m:
        return None
    role1, role2 = trim_role_name(m.group(1)), trim_role_name(m.group(2))
    if role1.lower() in _GENERIC_ROLE_STOPWORDS or role2.lower() in _GENERIC_ROLE_STOPWORDS:
        return None
    # Deliberately checks ONLY the bare generic-vocabulary mapping
    # (side_for_role), not the fuller resolve_role_side (which also
    # inspects the document's own definition text for directional
    # evidence). Validation found that document-definition-based conflict
    # detection, while correct for indemnification's bidirectional
    # architecture, produces false positives here on elaborate-but-
    # harmless entity descriptions (cooperative/d/b/a boilerplate,
    # successor-entity language) that were never meant to carry
    # directional evidence in the first place — see A6-L-59 in
    # benchmarks/step4a7_2_role_attribution_benchmark.py, a permanent
    # regression case for exactly this. The narrower, bare-vocabulary
    # check still catches A6-L-52 (neither "Grantee" nor "Grantor" has
    # ANY generic mapping at all) without that false-positive path.
    side1 = _core_side_for_role(role1)
    side2 = _core_side_for_role(role2)
    if side1 is None and side2 is None:
        return (
            f"neither '{role1}' nor '{role2}' maps to recognized buy-side/sell-side vocabulary — "
            f"cannot confirm whose liability this cap actually governs"
        )
    return None


_GENERIC_ROLE_STOPWORDS = {"each", "the", "any", "such", "this", "that", "both", "either", "all", "party", "parties"}

# Step 4A.7.1 (A6-RB-07), generalized and moved to policy_engine_core.py in
# Step 4A.7.3 as CHAINED_DELEGATION_RE — a multiplier can be cleanly
# extracted while its BASIS (what the multiplier applies to) is itself
# delegated through a chain of cross-references ending in a document not
# included in this excerpt. This is a TWO-level delegation, harder than the
# single-level "see Schedule B" cross-reference the existing
# _CROSS_REFERENCE_RES family already handles safely — the cap SENTENCE
# looks self-contained, which is exactly why it's dangerous: nothing else
# flags the basis itself as unresolved. Kept as a local alias so every
# existing call site below is unchanged; indemnification and payment_terms
# now import the same core regex directly (see step4a7_3 fresh-battery
# findings F3-D-06/F3-P-15 — this shape isn't liability-specific).
_CHAINED_BASIS_DELEGATION_RE = _core_chained_delegation_re

# Step 4A.5 — some drafting explicitly flags its own ambiguity ("it being
# unclear whether these are the same cap stated twice or two independent
# caps that would stack"). A document's own hedge about whether it means
# one thing or another is about as safe and general a review-trigger as
# exists — no interpretation is required, the text says so itself.
# Step 4A.7.1 — widened from "unclear whether" alone to the general
# closed family of phrases a drafter uses to explicitly flag that a
# value/scope is not yet finally settled (Step 4A.6 A6-L-23, A6-RB-01,
# A6-RB-09: "remains a matter...not yet finally resolved", "no such
# written agreement currently exists", "a determination not yet made").
# Each alternative is a specific, closed phrase describing the drafter's
# OWN acknowledgment of unresolved status — not a generic uncertainty
# word — so this does not open a vague-language net that would escalate
# ordinary hedged-but-resolved drafting.
_SELF_FLAGGED_AMBIGUITY_RE = re.compile(
    _core_self_flagged_unresolved_re.pattern
    + r"|no\s+such\s+[\w\s]{0,30}\s+currently\s+exists\b",
    re.I,
)

# Step 4A.5 Priority 4 (anti-false-safe): a self-defined cap TERM ("the
# Royalty Cap Amount") given two DIFFERENT values in two different
# sections of the same document is a genuine conflict discovered by
# Step 4A.5's earlier BASIS_RECURRING_PAYMENT fix having removed the
# (accidental, unrelated) basis-mismatch escalation that had been masking
# this real gap. General, deterministic construction: "'X' is defined in
# Section N ... as VALUE, and separately in Section M ... as VALUE2" —
# regardless of which specific values are involved, stating a term is
# defined twice with an explicit "and separately ... as" contrast is
# itself sufficient evidence of conflict, never resolved by picking
# either value.
_CONFLICTING_DEFINED_TERM_RE = re.compile(
    # Step 4A.9 (S48-L-T3-H-01) — "and IS SEPARATELY DEFINED in Section" is
    # the same restatement as "and separately in Section", with "is...
    # defined" spelled out instead of elided.
    r"is\s+defined\s+in\s+Section\s+\d+(?:\.\d+)?(?:\s*\([^)]*\))?\s+as\s+[^,]+,?\s+and\s+(?:is\s+)?separately(?:\s+defined)?"
    r"\s+in\s+Section\s+\d+(?:\.\d+)?(?:\s*\([^)]*\))?\s+as\b"
    # Step 4A.7.1 (A6-L-22): the SAME defined-term-conflict concept, a
    # different surface construction — "'[Term]' means, for purposes of
    # Section X, ..., and means, for purposes of Section Y, ..." — the
    # general shape is a defined term whose OWN definition is repeated,
    # each repetition scoped to a different named section, rather than
    # the specific "is defined...as...and separately...as" wording. Not
    # widened to catch every possible defined-term restatement — still
    # requires the explicit per-section scoping ("for purposes of Section
    # N") that signals the drafter intends genuinely different meanings
    # in different places, as opposed to one definition simply being
    # restated for readability.
    r"|means,?\s+for\s+purposes\s+of\s+Section\s+\d+(?:\.\d+)?(?:\s*\([^)]*\))?,\s+[^,]+,?\s+and\s+means,?"
    r"\s+for\s+purposes\s+of\s+Section\s+\d+(?:\.\d+)?(?:\s*\([^)]*\))?,",
    re.I,
)


# ---------------------------------------------------------------------------
# Typed cap representation (Priority 2)
# ---------------------------------------------------------------------------

@dataclass
class CapValue:
    kind: str  # "fee_multiplier" | "fixed_amount" | "unlimited" | "fee_period"
    # Typed cap basis — what the multiplier is OF. A multiplier is only
    # comparable to a policy threshold (defined as "Nx annual fees") when
    # basis == BASIS_FEES; any other basis is preserved verbatim but must
    # never be silently evaluated as if it were fee-based (see
    # evaluate_liability_policy's basis gate).
    # For fee_period, basis is BASIS_FEES (the period is of fees); the
    # finer FeeBasis / FeeScope enums are inferred at the v2 bridge from
    # raw_excerpt so months stay symbolic rather than converting to money.
    basis: str = BASIS_UNRESOLVED
    multiplier: Optional[float] = None
    fixed_amount: Optional[float] = None
    months: Optional[float] = None  # fee_period only — symbolic duration
    raw_excerpt: str = ""
    start_index: int = 0
    end_index: int = 0

    def summary(self) -> str:
        if self.kind == "unlimited":
            return "Unlimited"
        if self.kind == "fee_period":
            return f"{self.months:g} months' fees"
        if self.kind == "fee_multiplier":
            if self.basis == BASIS_FEES:
                return f"{self.multiplier:g}x annual fees"
            basis_label = self.basis.replace("_", " ").title() if self.basis else "unspecified basis"
            return f"{self.multiplier:g}x {basis_label}"
        if self.kind == "fixed_amount":
            return f"${self.fixed_amount:,.2f} fixed"
        return "unspecified"

    def compare_key(self) -> float:
        if self.kind == "unlimited":
            return float("inf")
        if self.kind == "fee_multiplier":
            return self.multiplier
        if self.kind == "fee_period":
            return self.months
        return self.fixed_amount


@dataclass
class CapExpression:
    """A typed, possibly-compound liability cap position.

    structure is one of:
      "simple"                 — one unambiguous value
      "greater_of"             — max() of components governs
      "lesser_of"               — min() of components governs
      "per_claim_and_aggregate" — two different-scope values, both stated
      "unresolved"              — could not be reliably classified
    """
    structure: str
    components: List[CapValue] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)  # parallel to components, only for per_claim_and_aggregate
    unresolved_reason: str = ""
    raw_excerpt: str = ""
    start_index: int = 0
    end_index: int = 0
    # Step 4A.7.1 remediation (A6-L-52) — populated at EXTRACTION time
    # (policy-independent, since extraction must not depend on policy
    # config) whenever the cap sentence names both an obligor and a
    # beneficiary role ("[Role1]'s liability to [Role2] shall not
    # exceed...") and at least one of them cannot be confirmed to either
    # side. Only CONSUMED at policy-evaluation time, and only when
    # policy.contract_side != "mutual" — a single-provision cap whose
    # value doesn't depend on which named party is "us" (contract_side
    # mutual) has no reason to escalate over an unresolved role pair, and
    # doing so anyway was found, during validation, to introduce new
    # false escalations on ordinary role-definition drafting (elaborate
    # but harmless corporate-family/successor definitions using role
    # nouns like "Processor"/"Merchant"/"Operator"/"Tenant" that are
    # legitimate business terms simply absent from the generic buy/sell
    # vocabulary, not evidence of anything unresolved).
    unmapped_role_pair_reason: Optional[str] = None

    def effective_cap(self) -> Tuple[Optional[CapValue], Optional[str]]:
        """Returns (CapValue to compare against a policy threshold, reason)
        — reason is set (and the CapValue is None) whenever the structure
        cannot be reduced to one comparable value without information the
        engine doesn't have."""
        if self.structure == "simple":
            return (self.components[0] if self.components else None), None

        if self.structure in ("greater_of", "lesser_of"):
            if not self.components:
                return None, "compound cap structure detected but no component values could be extracted"
            kinds = {c.kind for c in self.components}
            non_unlimited = [c for c in self.components if c.kind != "unlimited"]
            if "unlimited" in kinds:
                if self.structure == "greater_of":
                    return CapValue(kind="unlimited", raw_excerpt=self.raw_excerpt,
                                     start_index=self.start_index, end_index=self.end_index), None
                # lesser_of: the non-unlimited option governs, if there's exactly one
                if len(non_unlimited) == 1:
                    return non_unlimited[0], None
                return None, "lesser-of structure could not be reduced to one value"
            if len({c.kind for c in non_unlimited}) > 1:
                return None, (
                    f"cannot resolve a {self.structure.replace('_', ' ')} structure mixing "
                    f"incomparable cap kinds ({', '.join(sorted({c.kind for c in non_unlimited}))}) "
                    f"without additional deal context"
                )
            reducer = max if self.structure == "greater_of" else min
            return reducer(self.components, key=lambda c: c.compare_key()), None

        if self.structure == "per_claim_and_aggregate":
            if len(self.components) != 2:
                return None, "per-claim/aggregate structure detected but could not extract both values"
            a, b = self.components
            if a.kind == b.kind and a.compare_key() == b.compare_key():
                return a, None
            return None, (
                "clause distinguishes per-claim and aggregate caps with different values; "
                "policy threshold scope (per-claim vs. aggregate) is not specified"
            )

        return None, self.unresolved_reason or "cap structure could not be reliably classified"

    def summary(self) -> str:
        if self.structure == "simple":
            return self.components[0].summary() if self.components else "unspecified"
        if self.structure in ("greater_of", "lesser_of"):
            label = "greater of" if self.structure == "greater_of" else "lesser of"
            return f"{label} " + " or ".join(c.summary() for c in self.components)
        if self.structure == "per_claim_and_aggregate":
            parts = [f"{role}: {c.summary()}" for role, c in zip(self.roles, self.components)]
            return "; ".join(parts)
        return f"unresolved ({self.unresolved_reason})" if self.unresolved_reason else "unresolved"


def _simple(cap: Optional[CapValue]) -> CapExpression:
    if cap is None:
        return CapExpression(structure="simple", components=[])
    return CapExpression(structure="simple", components=[cap], raw_excerpt=cap.raw_excerpt,
                          start_index=cap.start_index, end_index=cap.end_index)


def _unresolved(reason: str, raw_excerpt: str = "", start_index: int = 0, end_index: int = 0) -> CapExpression:
    return CapExpression(structure="unresolved", unresolved_reason=reason, raw_excerpt=raw_excerpt,
                          start_index=start_index, end_index=end_index)


@dataclass
class CategoryTreatment:
    category: str
    # "uncapped" | "super_cap" | "within_general_cap" | "not_addressed" | "unresolved"
    treatment: str
    cap: Optional[CapValue] = None
    raw_excerpt: str = ""
    established: bool = True


@dataclass
class PartyPosition:
    role: str  # raw role word as it appears in the text, e.g. "Customer"
    side: Optional[str]  # "buy_side" | "sell_side" | None if unrecognized OR in conflict
    cap_expression: CapExpression
    # Set (Step 4A) when resolve_role_side() found the document's own
    # definition of `role` conflicts with the generic buy/sell vocabulary
    # — side is None whenever this is not None. Distinct from an
    # unrecognized role name (side is also None there, but this stays
    # None too) so evaluate_liability_policy can surface a specific,
    # useful reason instead of the generic "could not be mapped" text.
    side_conflict_reason: Optional[str] = None


@dataclass
class Provision:
    """One discovered Limitation-of-Liability-anchored clause in the
    document. A document may contain several (see reconciliation logic in
    extract_liability_facts)."""
    index: int
    section_label: Optional[str]
    is_amendment: bool
    start_index: int
    end_index: int
    raw_excerpt: str
    general_cap_expression: CapExpression
    category_treatments: Dict[str, CategoryTreatment]
    party_positions: Dict[str, PartyPosition]
    consequential_damages_excluded: Optional[bool]
    consequential_damages_established: bool
    consequential_damages_carveouts: List[str]
    cross_reference: Optional[Dict[str, Any]] = None  # {"label", "resolved", "reason"} — see _resolve_cross_reference
    # Step 4A.11 Phase 2 — whether this provision's own applicability is
    # conditioned (see policy_engine_core.ConditionEvidence).
    condition: Optional[ConditionEvidence] = None
    # Full provision window text used for mutuality / framing facts. Distinct
    # from raw_excerpt, which may be narrowed to the cap-value token (e.g. a
    # fee-period span) for condition anchoring — mutual openers like
    # "EACH PARTY'S TOTAL AGGREGATE LIABILITY" live in the window, not the
    # value excerpt.
    operative_window_excerpt: str = ""

    def provision_label(self) -> str:
        if self.section_label:
            return f"Section {self.section_label} — Limitation of Liability"
        return f"the Limitation of Liability provision at character {self.start_index}"


@dataclass
class LiabilityFacts:
    clause_found: bool
    provisions: List[Provision] = field(default_factory=list)
    controlling_provision: Optional[Provision] = None
    reconciliation: str = "single"  # "single" | "amendment_resolved" | "consistent_duplicate" | "unreconciled"
    reconciliation_explanation: str = ""
    # Fact-admission architecture (see fact_admission.py and
    # indemnification_policy_engine.py's absence_state, which this mirrors).
    # Diagnostic by default — evaluate_liability_policy branches on
    # clause_found/absence_state together (see the NOT_APPLICABLE branch),
    # never on this string alone, matching indemnification's own discipline.
    # CONFIRMED_ABSENT: regex found nothing AND semantic discovery ran
    #   successfully and also found/admitted nothing.
    # RECOGNITION_UNCERTAIN: regex found nothing AND semantic discovery was
    #   unavailable/errored — must never collapse into CONFIRMED_ABSENT.
    absence_state: str = "CONFIRMED_ABSENT"
    semantic_discovery_error: Optional[str] = None
    document_wide_conflict: bool = False
    # Zero-silent-loss follow-up (data_security-139 general failure class)
    # — a candidate was discovered but rejected by its OWN semantic
    # verification (uncertain, not a disproven claim), and a deterministic
    # anchor also exists elsewhere in the document. Previously discarded
    # once accepted_anchors was non-empty; see extract_liability_facts.
    ai_identified_unresolved_dependency: Optional[str] = None


class PolicyRuleLike(Protocol):
    """Structural type for whatever ORM row (or test double) is passed to
    evaluate() — deliberately not importing models.PolicyRule, so this
    engine has no database dependency and stays independently testable.
    Structurally includes policy_engine_core.BasePolicyRuleLike's fields
    (contract_side, escalation_approval_authority, fallback_text) plus
    everything specific to a liability-cap policy."""
    preferred_multiplier: Optional[float]
    acceptable_max_multiplier: Optional[float]
    negotiate_max_multiplier: Optional[float]
    prohibit_unlimited: bool
    required_exceptions_json: Optional[List[str]]
    fallback_text: Optional[str]
    escalation_approval_authority: Optional[str]
    contract_side: str
    require_consequential_damages_exclusion: bool
    required_consequential_carveouts_json: Optional[List[str]]


# LadderStep and PolicyDecision are clause-agnostic — imported from
# policy_engine_core above, not redefined here.

# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

# _excerpt / _section_label_before are imported from policy_engine_core
# (promoted — see policy_engine_core.excerpt / section_label_before).

def _find_cap_values(window: str) -> List[CapValue]:
    """All cap-value mentions in the window, in document order. Overlapping
    matches from different patterns are deduped by keeping the first."""
    matches: List[Tuple[int, int, CapValue]] = []
    for m in _UNLIMITED_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="unlimited", raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _MULTIPLIER_NUM_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="fee_multiplier", basis=_classify_basis(m.group(2)), multiplier=float(m.group(1)),
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _MULTIPLIER_WORD_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="fee_multiplier", basis=_classify_basis(m.group(2)), multiplier=float(_WORD_NUMBERS[m.group(1).lower()]),
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _FIXED_AMOUNT_RE.finditer(window):
        matches.append((m.start(), m.end(), CapValue(
            kind="fixed_amount", basis=BASIS_FIXED_AMOUNT, fixed_amount=float(m.group(1).replace(",", "")),
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _FEE_PERIOD_DURATION_RE.finditer(window):
        months = _parse_fee_period_months_from_duration(m)
        if months is None:
            continue
        matches.append((m.start(), m.end(), CapValue(
            kind="fee_period", basis=BASIS_FEES, months=months,
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))
    for m in _FEE_PERIOD_TRAILING_RE.finditer(window):
        months = _parse_fee_period_months_from_trailing(m)
        if months is None:
            continue
        matches.append((m.start(), m.end(), CapValue(
            kind="fee_period", basis=BASIS_FEES, months=months,
            raw_excerpt=window[m.start():m.end()], start_index=m.start(), end_index=m.end(),
        )))

    matches.sort(key=lambda t: t[0])
    deduped: List[Tuple[int, int, CapValue]] = []
    for start, end, cap in matches:
        if deduped and start < deduped[-1][1]:
            continue  # overlaps a match already kept
        deduped.append((start, end, cap))
    return [cap for _, _, cap in deduped]


def _all_category_keyword_positions(window: str) -> List[Tuple[int, str]]:
    positions = []
    for cat, kw_re in _CATEGORY_KEYWORD_RE.items():
        for m in kw_re.finditer(window):
            positions.append((m.start(), cat))
    return positions


def _compute_exclusion_coverage(window: str, all_category_positions: List[Tuple[int, str]]) -> Dict[str, str]:
    """For each exclusion-signal occurrence, credits every category keyword
    found in its forward coverage span — from the signal to the next
    sentence/clause boundary, or ~100 characters, whichever is first — as
    "uncapped". A signal covering a coordinated list ("...shall not apply
    to claims arising from fraud or gross negligence.") correctly credits
    every category named in that list, not just the nearest one. Forward-
    only and boundary-limited so a LATER, unrelated exclusion signal for a
    different category elsewhere in the clause cannot bleed backward onto
    an earlier category's own super-cap language (see the multisupercap-01/
    -05 regression tests, both same-sentence, comma-joined clauses where
    backward attribution previously mis-credited the wrong category)."""
    covered: Dict[str, str] = {}
    for sig in _EXCLUSION_SIGNAL_RE.finditer(window):
        # Step 4A: find the actual sentence/clause boundary FIRST, over a
        # generously bounded search range, rather than truncating to a
        # fixed 100 chars before ever looking for one. A short, fixed cap
        # here (searched-then-truncated, as before) meant an exception
        # list naming several categories in one run-on sentence ("fraud,
        # willful misconduct, ..., or infringement of IP rights, in no
        # event shall liability exceed 1x fees") had its real boundary —
        # the period after the general cap — invisible past 100 chars, so
        # only the first category or two ever got credited as excluded;
        # the rest fell through to the same-sentence super-cap check and
        # wrongly claimed the general cap as their own. Only fall back to
        # the original fixed-width cutoff when no boundary exists at all
        # within the larger search range (an exception list that runs on
        # even longer than this should still get SOME bounded coverage,
        # not scan indefinitely).
        search_end = min(len(window), sig.end() + _EXCLUSION_COVERAGE_SEARCH_CHARS)
        search_text = window[sig.end():search_end]
        # `\.$` (end of string/window, no trailing character after the
        # final period) matters here specifically: a clause's final
        # sentence routinely has nothing after its closing period, so a
        # boundary regex that only recognizes "period + whitespace" would
        # never find it and would silently fall back to the fixed-width
        # cutoff on exactly the cases this fix targets.
        # A bare semicolon is deliberately NOT treated as a hard boundary
        # here — semicolon-separated drafting of an exception list itself
        # ("fraud; willful misconduct; ... ; or infringement...") is
        # common and must not truncate coverage after the first item. A
        # semicolon that genuinely introduces a new independent clause
        # (with its own cap language) is instead caught by the same
        # cap-trigger-gated scan used for "and" below.
        boundary = re.search(r"\.\s|\.$", search_text)
        span_end = min(len(window), sig.end() + (boundary.start() if boundary else _EXCLUSION_COVERAGE_FALLBACK_CHARS))
        coverage_text = window[sig.end():span_end]
        boundary = re.search(r"\.\s|\.$", coverage_text)
        boundary_pos = boundary.start() if boundary else None
        # "...X, AND liability for Y shall not exceed..." (or "...X;
        # liability for Y shall not exceed...") introduces a new
        # independent clause with its own cap, not a continuation of the
        # excluded-category list — truncate coverage at that connector so
        # Y's keyword (here in the new clause's subject) isn't swept in
        # too. Semicolons are included here (not as an unconditional
        # boundary above) precisely so a semicolon that DOES introduce a
        # new cap-bearing clause is still caught, while one that's just a
        # list-item separator within the exception enumeration is not.
        for conn_m in re.finditer(r"\band\b|;", coverage_text, re.I):
            if _CAP_TRIGGER_RE.search(coverage_text[conn_m.end():conn_m.end() + 60]):
                if boundary_pos is None or conn_m.start() < boundary_pos:
                    boundary_pos = conn_m.start()
                break
        if boundary_pos is not None:
            coverage_text = coverage_text[:boundary_pos]
        coverage_end = sig.end() + len(coverage_text)
        for pos, cat in all_category_positions:
            if sig.end() <= pos < coverage_end and cat not in covered:
                covered[cat] = _excerpt(window, sig.start(), coverage_end)
    return covered


def _classify_category(
    window: str, category: str, all_category_positions: List[Tuple[int, str]],
    exclusion_coverage: Dict[str, str],
) -> CategoryTreatment:
    keyword_re = _CATEGORY_KEYWORD_RE[category]
    occurrences = list(keyword_re.finditer(window))
    if not occurrences:
        return CategoryTreatment(category=category, treatment="not_addressed", established=True)

    m = occurrences[0]
    local_start = max(0, m.start() - _LOCAL_WINDOW_CHARS)
    local_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    local = window[local_start:local_end]
    excerpt = _excerpt(window, m.start(), m.end())

    if category in exclusion_coverage:
        return CategoryTreatment(category=category, treatment="uncapped", raw_excerpt=excerpt, established=True)

    # A category-specific cap must be stated FORWARD of the category
    # keyword, in the SAME sentence — searching backward would let a nearby
    # but unrelated general cap get misattributed to this category as a
    # phantom super-cap, and searching past a sentence boundary ("...breaches
    # of willful misconduct. Aggregate liability shall not exceed 1x...")
    # would credit the *next* sentence's unrelated general cap the same way.
    forward_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    forward_text = window[m.end():forward_end]
    # A semicolon joins independent clauses just as a period joins
    # sentences ("...basket shall be $25,000; separately, aggregate
    # liability shall not exceed 2x...") — without this, a category
    # keyword on one side of a semicolon can reach across it and claim an
    # unrelated cap value stated in the other, independent clause.
    boundary = re.search(r"\.\s|;\s", forward_text)
    same_sentence_text = forward_text[:boundary.start()] if boundary else forward_text
    forward_caps = _find_cap_values(same_sentence_text)
    if forward_caps:
        cap = forward_caps[0]
        cap.start_index += m.end()
        cap.end_index += m.end()
        return CategoryTreatment(category=category, treatment="super_cap", cap=cap, raw_excerpt=excerpt, established=True)

    if _AMBIGUITY_SIGNAL_RE.search(local):
        return CategoryTreatment(category=category, treatment="unresolved", raw_excerpt=excerpt, established=False)

    return CategoryTreatment(category=category, treatment="within_general_cap", raw_excerpt=excerpt, established=True)


def _classify_general_cap_expression(
    window: str, category_treatments: Dict[str, CategoryTreatment],
) -> CapExpression:
    claims = [
        (cat, t.cap.start_index, t.cap.end_index) for cat, t in category_treatments.items()
        if t.treatment == "super_cap" and t.cap is not None
    ]
    claimed_spans = [(lo, hi) for _, lo, hi in claims]

    def _is_claimed(cap: CapValue) -> bool:
        return any(cap.start_index >= lo - 5 and cap.end_index <= hi + 5 for lo, hi in claimed_spans)

    # Step 4A candidate-ownership check: the SAME exact span cannot
    # legitimately be a category-specific super_cap for more than one
    # category at once — a span can be a general aggregate cap OR belong
    # to one carve-out's own specific treatment, never both/several
    # simultaneously. When the same-sentence forward-scan in
    # _classify_category independently credits 2+ categories with the
    # identical cap span (Step 2B's LOL-D-01: five carve-outs in one
    # run-on sentence all reaching the same trailing "1x fees" cap),
    # that is itself a signal something is wrong with how the categories
    # were attributed — not a license to silently drop the span from the
    # general-cap pool and proceed as if no cap were stated at all.
    span_claimants: Dict[Tuple[int, int], List[str]] = {}
    for cat, lo, hi in claims:
        span_claimants.setdefault((lo, hi), []).append(cat)
    multiply_claimed = [(span, cats) for span, cats in span_claimants.items() if len(cats) > 1]
    if multiply_claimed:
        (lo, hi), cats = multiply_claimed[0]
        return _unresolved(
            f"the same cap language was attributed to multiple carve-out categories "
            f"({', '.join(sorted(cats))}) — cannot determine whether this is the general "
            f"aggregate cap or a category-specific cap without attorney review",
            raw_excerpt=_excerpt(window, lo, hi), start_index=lo, end_index=hi,
        )

    conflicting_term = _CONFLICTING_DEFINED_TERM_RE.search(window)
    if conflicting_term:
        lo = max(0, conflicting_term.start() - 60)
        hi = min(len(window), conflicting_term.end() + 60)
        return _unresolved(
            "a self-defined cap term is given two different values in two different sections of this document",
            raw_excerpt=window[lo:hi].strip(), start_index=lo, end_index=hi,
        )

    self_flagged = _SELF_FLAGGED_AMBIGUITY_RE.search(window)
    if self_flagged:
        lo = max(0, self_flagged.start() - 40)
        hi = min(len(window), self_flagged.end() + 150)
        return _unresolved(
            "the document explicitly flags its own ambiguity about how this cap should be interpreted",
            raw_excerpt=window[lo:hi].strip(), start_index=lo, end_index=hi,
        )

    chained_delegation = _CHAINED_BASIS_DELEGATION_RE.search(window)
    if chained_delegation:
        lo = max(0, chained_delegation.start() - 60)
        hi = min(len(window), chained_delegation.end() + 40)
        return _unresolved(
            "the cap's basis is delegated through a chain of cross-references ending in a document not "
            "included — the multiplier itself is clean but what it applies to cannot be verified",
            raw_excerpt=window[lo:hi].strip(), start_index=lo, end_index=hi,
        )

    conditional_unverified = _core_conditional_unverified_precondition_re.search(window)
    if conditional_unverified:
        lo = max(0, conditional_unverified.start() - 20)
        hi = min(len(window), conditional_unverified.end() + 20)
        return _unresolved(
            "the stated multiplier's applicability is conditioned on a precondition the document itself "
            "marks as not yet verified — cannot confirm this cap actually governs",
            raw_excerpt=window[lo:hi].strip(), start_index=lo, end_index=hi,
        )

    basis_ambiguity = _BASIS_VALUE_AMBIGUITY_RE.search(window)
    if basis_ambiguity:
        lo = max(0, basis_ambiguity.start() - 60)
        hi = min(len(window), basis_ambiguity.end() + 100)
        return _unresolved(
            "the multiplier's basis value itself is stated ambiguously (may refer to more than one "
            "figure) — cannot determine which figure the multiplier applies to without additional information",
            raw_excerpt=window[lo:hi].strip(), start_index=lo, end_index=hi,
        )

    # Greater-of / lesser-of: look for the signal, then extract the
    # component values from a window immediately around it.
    gl = _GREATER_LESSER_RE.search(window)
    if gl:
        structure = "greater_of" if gl.group("greater") else "lesser_of"
        local_end = min(len(window), gl.end() + 250)
        local_start = max(0, gl.start() - 40)
        components = [c for c in _find_cap_values(window[local_start:local_end]) if not _is_claimed(c)]
        for c in components:
            c.start_index += local_start
            c.end_index += local_start
        # Step 4A.5 Priority 4: within a "greater of A or B"/"lesser of A
        # or B" structure, the SECOND operand often carries no lead-in
        # verb of its own ("...the greater of 2 times the annual fees
        # paid or $1,000,000") — the governing verb applies to the whole
        # compound expression, not to each operand individually. Scoped
        # strictly to this local greater/lesser-of window (never applied
        # to a bare dollar figure elsewhere in the document), a bare
        # "or $N" is safe to treat as the second operand only when
        # exactly one component was already found by the general path.
        if len(components) == 1:
            local_text = window[local_start:local_end]
            bare_or_m = _BARE_OR_FIXED_AMOUNT_RE.search(local_text)
            if bare_or_m and not any(abs(bare_or_m.start(1) - (c.start_index - local_start)) < 3 for c in components):
                components.append(CapValue(
                    kind="fixed_amount", basis=BASIS_FIXED_AMOUNT,
                    fixed_amount=float(bare_or_m.group(1).replace(",", "")),
                    raw_excerpt=bare_or_m.group(0),
                    start_index=local_start + bare_or_m.start(), end_index=local_start + bare_or_m.end(),
                ))
        if len(components) >= 2:
            return CapExpression(
                structure=structure, components=components[:2],
                raw_excerpt=_excerpt(window, gl.start(), local_end - local_start + local_start, pad=0) or window[local_start:local_end].strip(),
                start_index=local_start, end_index=local_end,
            )
        # Signal present but couldn't extract both operands — don't guess.
        return _unresolved(
            f"a '{structure.replace('_', ' ')}' structure was signaled but its component values could not both be extracted",
            raw_excerpt=window[local_start:local_end].strip(), start_index=local_start, end_index=local_end,
        )

    # Per-claim vs. aggregate: two distinct scopes each with their own cap.
    per_claim_m = _PER_CLAIM_RE.search(window)
    aggregate_m = _AGGREGATE_SCOPE_RE.search(window)
    if per_claim_m and aggregate_m:
        pc_window = window[per_claim_m.start():min(len(window), per_claim_m.start() + 150)]
        ag_window = window[aggregate_m.start():min(len(window), aggregate_m.start() + 150)]
        pc_caps = [c for c in _find_cap_values(pc_window) if not _is_claimed(c)]
        ag_caps = [c for c in _find_cap_values(ag_window) if not _is_claimed(c)]
        if pc_caps and ag_caps:
            pc, ag = pc_caps[0], ag_caps[0]
            pc.start_index += per_claim_m.start()
            pc.end_index += per_claim_m.start()
            ag.start_index += aggregate_m.start()
            ag.end_index += aggregate_m.start()
            return CapExpression(
                structure="per_claim_and_aggregate", components=[pc, ag], roles=["per_claim", "aggregate"],
                raw_excerpt=_excerpt(window, min(pc.start_index, ag.start_index), max(pc.end_index, ag.end_index)),
                start_index=min(pc.start_index, ag.start_index), end_index=max(pc.end_index, ag.end_index),
            )

    # Fall back to the simple/conflict model: gather unclaimed cap values.
    all_caps = _find_cap_values(window)
    unclaimed = [c for c in all_caps if not _is_claimed(c)]
    if not unclaimed:
        return _simple(None)

    # Step 4A / 4A.1: when the clause's OWN operative language delegates
    # to a cross-referenced provision ("...liability shall be as set
    # forth in Schedule C...") rather than stating a cap directly, the
    # document-wide provision window (_PROVISION_WINDOW_CHARS) can still
    # reach far enough to pick up unrelated cap-shaped numbers from that
    # referenced material (Step 2B's LOL-B-01: an SLA service-credit cap
    # inside "Schedule C" was adopted as the liability cap purely because
    # it was the only cap-shaped match in the window). Filter to
    # concept-verified candidates BEFORE the has_unlimited/distinct-value
    # conflict logic below — 4A.1 fix: filtering AFTER that logic (as
    # Step 4A originally did, checking only the sole survivor when
    # exactly one candidate remained) meant a genuine liability cap
    # sitting alongside an unrelated disqualified number (e.g. an SLA
    # service-credit figure in the same referenced schedule) was wrongly
    # treated as "multiple distinct cap values, cannot determine which
    # governs" instead of correctly recognizing that only one candidate
    # was ever a real liability-concept candidate to begin with. Mirrors
    # the same concept-anchor requirement _resolve_cross_reference already
    # enforces for its own candidates — reused here, not reinvented,
    # because this is the SAME failure mode reached via a different code
    # path. Ordinary clauses that state their cap directly (the
    # overwhelming majority) never contain cross-reference delegation
    # language at all, so this filter is a no-op for them — it only
    # engages when the clause itself points elsewhere.
    has_delegation = _detect_cross_reference(window) is not None
    # Step 4A.3 — Failure Family 3 hardening: concept+limit verification
    # is no longer conditional on cross-reference delegation. Step 4A.2's
    # LOL-H2-04 demonstrated the gap directly — a service-credit figure
    # sitting in the SAME sentence as a genuine liability cap, with NO
    # cross-reference involved at all, was adopted as the cap purely
    # because it was structurally reachable, since this "plain" path
    # (no delegation, no category claim) applied no verification
    # whatsoever. The invariant is now: whenever there is more than one
    # surviving candidate, EVERY candidate must independently pass
    # concept+limit(+disqualifier) verification before being admitted to
    # the distinct-value comparison — a candidate that isn't concept-
    # verified is simply not a competing candidate, not "the only
    # option so it must be right." The single-candidate, no-delegation
    # case (the overwhelming majority of ordinary contracts, where one
    # cap-shaped value is stated directly and unambiguously) is left
    # unconditionally trusted, exactly as before — this only engages
    # when there is genuine multiplicity to adjudicate, so ordinary
    # drafting is unaffected.
    if has_delegation or len(unclaimed) > 1:
        concept_verified = [c for c in unclaimed if c.kind == "unlimited" or _has_liability_concept_nearby(window, c)]
        if not concept_verified:
            cap = unclaimed[0]
            return _unresolved(
                "this clause delegates to a cross-referenced provision, and no cap-shaped "
                "value found in the document has any limitation-of-liability language near "
                "it — cannot establish that any of them is actually the liability cap "
                "without attorney review",
                raw_excerpt=_excerpt(window, cap.start_index, cap.end_index),
                start_index=cap.start_index, end_index=cap.end_index,
            )
        unclaimed = concept_verified

    # Step 4A.5 Priority 4: investigated a fix here (excluding "unlimited"
    # matches scoped to a named carve-out exception from the general-cap
    # conflict check) to resolve A4-D-07/A4-D-08 automatically. Reverted
    # after it regressed two pre-existing, more heavily-vetted benchmark
    # cases (asym-05: an "uncapped" carve-out on a DIFFERENT scope
    # ("payment obligations", not liability) that is a genuine conflict;
    # unheaded-10: a compound general-cap-plus-many-category-carve-out
    # statement the existing suite deliberately treats as ambiguous
    # enough to escalate) — the boundary between "safely automatable
    # single/dual-category carve-out" and "genuinely ambiguous compound
    # statement" could not be drawn narrowly enough to fix one without
    # breaking the other in the time available. A4-D-07/A4-D-08 remain
    # correctly-safe REQUIRES_REVIEW outcomes (documented FE limitation)
    # rather than risk a false-safe on the existing corpus.
    has_unlimited = any(c.kind == "unlimited" for c in unclaimed)
    numeric = [c for c in unclaimed if c.kind != "unlimited"]
    distinct_numeric_values = {
        (c.kind, c.basis, c.multiplier, c.fixed_amount, c.months) for c in numeric
    }

    if has_unlimited and numeric:
        return _unresolved(
            "conflicting unlimited and numeric cap language for the general cap",
            raw_excerpt=_excerpt(window, unclaimed[0].start_index, unclaimed[0].end_index),
            start_index=unclaimed[0].start_index, end_index=unclaimed[0].end_index,
        )
    if has_unlimited:
        return _simple(unclaimed[0])
    if len(distinct_numeric_values) > 1:
        return _unresolved(
            "multiple distinct cap values found for the general clause; cannot determine which governs",
            raw_excerpt=_excerpt(window, numeric[0].start_index, numeric[0].end_index),
            start_index=numeric[0].start_index, end_index=numeric[0].end_index,
        )
    return _simple(numeric[0])


def _classify_consequential_damages(window: str) -> Tuple[Optional[bool], bool, List[str]]:
    m = _CONSEQUENTIAL_RE.search(window)
    if not m:
        return None, True, []  # not addressed at all — confidently "no exclusion found"
    local_start = max(0, m.start() - _LOCAL_WINDOW_CHARS)
    local_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
    local = window[local_start:local_end]
    carveouts = []
    if _CARVEOUT_PHRASE_RE.search(local):
        cv_local = local[max(0, m.start() - local_start):]
        for cat, kw_re in _CATEGORY_KEYWORD_RE.items():
            if kw_re.search(cv_local):
                carveouts.append(cat)
    if _EXCLUDE_PHRASE_RE.search(local):
        return True, True, carveouts
    return None, False, carveouts


def _find_party_positions(window: str, document_text: Optional[str] = None) -> Dict[str, PartyPosition]:
    """Detects distinct named-role liability statements ('Customer's
    liability shall not exceed...', 'Vendor's liability is not subject
    to...') and their cap values. Two or more distinct roles with distinct
    cap expressions is the signal for a directional/asymmetric structure —
    see evaluate_liability_policy for how "ours" vs. "counterparty" is
    resolved from this.

    `document_text` (Step 4A) is the FULL document, not just `window` — a
    role's own defined-terms sentence is routinely far from the operative
    liability clause. When not given (e.g. legacy/test callers), falls
    back to `window` alone, so this stays backward compatible."""
    positions: Dict[str, PartyPosition] = {}
    scan_text = document_text if document_text is not None else window
    for m in _ROLE_POSITION_RE.finditer(window):
        role = m.group(1)
        role_key = role.lower()
        if role_key in positions:
            continue
        segment_end = min(len(window), m.end() + 150)
        segment = window[m.end():segment_end]
        # The role-position match already consumed the lead-in phrase
        # ("...is capped at"), so a bare "$1,000,000" left in the segment
        # won't match _FIXED_AMOUNT_RE's own required lead-in — restore a
        # synthetic one so the same tested cap-value patterns still apply.
        padding = "shall not exceed "
        caps = _find_cap_values(padding + segment)
        if not caps:
            continue
        cap = caps[0]
        cap.start_index += m.end() - len(padding)
        cap.end_index += m.end() - len(padding)
        side, conflict_reason = _core_resolve_role_side(role, scan_text)
        positions[role_key] = PartyPosition(
            role=role, side=side, cap_expression=_simple(cap), side_conflict_reason=conflict_reason,
        )
    return positions


def _detect_cross_reference(window: str) -> Optional[Tuple[str, int, int]]:
    """Returns (label, start, end) for the first cross-reference signal
    found — label is "" for a generic "incorporated by reference" with no
    named target. None if no cross-reference language is present at all."""
    for pat in _CROSS_REF_TARGET_PATTERNS:
        m = pat.search(window)
        if m:
            label = m.group(1) if m.groups() else ""
            return label, m.start(), m.end()
    return None


# Step 4A.1 — liability-concept ownership, restructured. Step 4A's
# _has_liability_concept_nearby (a fixed 250-char window checked against
# _ANCHOR_RE/_SECONDARY_ANCHOR_RE, the SAME narrow patterns used for
# primary clause recognition) rejected a genuine cap phrased "liability
# arising under this Agreement ... exceed ..." because
# _SECONDARY_ANCHOR_RE's "in no event shall ... liability exceed" pattern
# requires those two words adjacent, with no intervening relative clause
# (XR-4). Root cause: one regex was being asked to prove three different
# things at once (this is about liability AND this imposes a limit AND
# this specific number is the value) — any single narrow pattern that
# happens to satisfy all three simultaneously is inherently brittle to
# ordinary drafting variation. 4A.1 splits this into three independently
# testable questions, each answered over the SENTENCE containing the
# candidate (a structural boundary — not a fixed character window):
#
#   1. CONCEPT — does the sentence concern liability at all?
#   2. LIMIT   — does the sentence impose a maximum/limitation?
#   3. VALUE   — the numeric candidate itself (already established by
#      the caller via _find_cap_values before this function runs).
#
# All three together (not one giant regex) are required before a
# candidate is treated as an established liability cap. A DISQUALIFYING
# check additionally rejects a sentence whose dominant subject is a
# different, commonly-confused concept (service credits, insurance,
# deductibles, purchase price, etc.) even if the word "liability" or a
# limit predicate happens to also appear in it — see Step 4A.1's negative
# cross-reference test suite for the concrete confusions this guards.
_LIABILITY_CONCEPT_RE = re.compile(r"\bliabilit(?:y|ies)\b|\bliable\b", re.I)
_LIABILITY_LIMIT_PREDICATE_RE = re.compile(
    r"shall\s+not\s+exceed|is\s+capped\s+at|shall\s+be\s+capped|\blimited\s+to\b"
    r"|shall\s+not\s+be\s+liable\s+for|\bmaximum\b|in\s+no\s+event.{0,120}?exceed"
    r"|\baggregate\b|\bcumulative\b|\bceiling\b|\buncapped\b|\bunlimited\b"
    r"|\bcap(?:s|ped)?\b",
    re.I,
)
# Concepts that commonly co-occur with cap-shaped numbers but are NOT
# limitation-of-liability — each one is a real drafting pattern that
# produced a wrong candidate somewhere in Step 2B/4A/4A.1 testing or is a
# realistic analog of one (SLA service credits; insurance policy limits;
# a deal's purchase price; late/termination fees; security deposits;
# indemnification baskets/deductibles).
_LIABILITY_DISQUALIFYING_CONCEPT_RE = re.compile(
    r"service\s+credit|\bSLA\b|service\s+level|\binsurance\b|\bdeductible\b|\bpurchase\s+price\b"
    r"|indemnification\s+basket|\bbasket\b|\btermination\s+fee\b|\bsecurity\s+deposit\b"
    r"|\blate\s+fee\b|\bpenalty\b",
    re.I,
)
# How far to search, in EITHER direction, for the sentence boundary
# around a candidate — a bounded fallback only, structural boundaries
# (period+space, period+end-of-text) are always preferred when found
# within this range. Generous enough for realistic multi-clause
# sentences without scanning unboundedly.
_LIABILITY_SENTENCE_SEARCH_CHARS = 500


def _sentence_containing_with_offset(text: str, start: int, end: int) -> Tuple[str, int]:
    """Returns (sentence, sentence_start_offset_in_text) for the sentence
    containing text[start:end], found via structural boundaries (". ", or
    start/end of text) rather than a fixed character window — falls back
    to a bounded window only when no boundary exists within
    _LIABILITY_SENTENCE_SEARCH_CHARS."""
    back_lo = max(0, start - _LIABILITY_SENTENCE_SEARCH_CHARS)
    back_text = text[back_lo:start]
    back_boundary = back_text.rfind(". ")
    sentence_start = back_lo + back_boundary + 2 if back_boundary != -1 else back_lo

    fwd_hi = min(len(text), end + _LIABILITY_SENTENCE_SEARCH_CHARS)
    fwd_text = text[end:fwd_hi]
    fwd_m = re.search(r"\.\s|\.$", fwd_text)
    sentence_end = end + fwd_m.end() if fwd_m else fwd_hi

    return text[sentence_start:sentence_end], sentence_start


def _sentence_containing(text: str, start: int, end: int) -> str:
    """Returns the sentence containing text[start:end] — see
    _sentence_containing_with_offset for the offset-returning variant used
    when a caller needs to map indices back into sentence-relative
    coordinates."""
    sentence, _ = _sentence_containing_with_offset(text, start, end)
    return sentence


# Step 4A.3: a disqualifying-concept mention that is itself being
# EXCLUDED/DISCLAIMED ("separate from any insurance requirement",
# "independent of insurance proceeds", "insurance proceeds do not limit
# Provider's contractual liability") must not disqualify the candidate —
# the sentence is explicitly saying the disqualifying concept does NOT
# govern here. Scoped narrowly around the disqualifier match itself
# (not the whole sentence) so this doesn't accidentally neutralize a
# genuine disqualifier elsewhere in a longer sentence.
_DISQUALIFIER_NEGATION_RE = re.compile(
    r"separate\s+from|independent\s+of|exclusive\s+of|regardless\s+of|notwithstanding"
    r"|in\s+addition\s+to|(?:shall\s+not|does\s+not|do\s+not)\s+limit|not\s+a\s+limitation\s+on",
    re.I,
)
_DISQUALIFIER_NEGATION_WINDOW = 60


def _comma_delimited_span(sentence: str, start: int, end: int) -> Tuple[int, int]:
    """The comma-to-comma (or sentence-boundary) sub-clause containing
    sentence[start:end] — the structural unit a parenthetical/appositive
    disqualifier concept ("including without limitation any service
    credits...") actually applies to, as opposed to the whole sentence."""
    seg_start = sentence.rfind(",", 0, start)
    seg_start = seg_start + 1 if seg_start != -1 else 0
    seg_end = sentence.find(",", end)
    seg_end = seg_end if seg_end != -1 else len(sentence)
    return seg_start, seg_end


def _has_liability_concept_nearby(text: str, cap: CapValue) -> bool:
    """CONCEPT + LIMIT (+ disqualifier) verification for one candidate
    value, scoped to its containing sentence. Does NOT re-verify VALUE —
    the caller already established the candidate via _find_cap_values.

    A disqualifying concept (e.g. "service credit", "insurance") only
    disqualifies THIS candidate when it appears in the SAME comma-
    delimited sub-clause as the candidate — a sentence can legitimately
    contain an unrelated disqualifying sub-clause (an SLA service-credit
    parenthetical, an insurance carve-out) alongside a genuine liability
    cap elsewhere in the same sentence, and that sub-clause must not
    poison the whole sentence for every candidate in it."""
    sentence, sentence_offset = _sentence_containing_with_offset(text, cap.start_index, cap.end_index)
    cap_lo = cap.start_index - sentence_offset
    cap_hi = cap.end_index - sentence_offset
    cap_seg_start, cap_seg_end = _comma_delimited_span(sentence, cap_lo, cap_hi)
    for dm in _LIABILITY_DISQUALIFYING_CONCEPT_RE.finditer(sentence):
        if dm.start() >= cap_seg_end or dm.end() <= cap_seg_start:
            continue  # disqualifying concept sits in a different sub-clause — not about THIS candidate
        lo = max(0, dm.start() - _DISQUALIFIER_NEGATION_WINDOW)
        hi = min(len(sentence), dm.end() + _DISQUALIFIER_NEGATION_WINDOW)
        if not _DISQUALIFIER_NEGATION_RE.search(sentence[lo:hi]):
            return False
    return bool(_LIABILITY_CONCEPT_RE.search(sentence) and _LIABILITY_LIMIT_PREDICATE_RE.search(sentence))


def _resolve_cross_reference(
    text: str, provision_start: int, provision_end: int, label: str,
) -> Tuple[Optional[CapValue], str]:
    """Searches the full document for the named reference target (e.g.
    "Schedule C") outside the current provision and attempts to locate a
    cap value stated near it. Resolves deterministically only when exactly
    one candidate location yields a value THAT IS ALSO INDEPENDENTLY
    ANCHORED to the liability concept (or every such candidate agrees) —
    otherwise returns (None, reason) naming why it couldn't, never a guess
    among multiple candidates, and never a numeric value whose surrounding
    text gives no indication it is even about liability."""
    occurrences = [
        m for m in re.finditer(re.escape(label), text, re.I)
        if not (provision_start <= m.start() <= provision_end)
    ]
    if not occurrences:
        return None, f"referenced provision \"{label}\" was not found elsewhere in the extracted document text"

    all_candidates: List[Tuple[re.Match, CapValue]] = []
    for m in occurrences:
        if not _core_is_operative_context(text, m.start(), m.end()):
            # The reference label itself sits in non-operative context near
            # this occurrence (e.g. "(informational only)", "for reference
            # only", a superseded/negated summary) — a candidate value found
            # near it is not a binding cap and must not compete with a
            # genuinely operative occurrence found elsewhere in the document.
            continue
        forward = text[m.end():min(len(text), m.end() + _CROSS_REF_RESOLUTION_WINDOW)]
        caps = _find_cap_values(forward)
        if caps:
            cap = caps[0]
            cap.start_index += m.end()
            cap.end_index += m.end()
            if not _core_is_operative_context(text, cap.start_index, cap.end_index):
                continue
            all_candidates.append((m, cap))

    if not all_candidates:
        return None, (
            f"referenced provision \"{label}\" was found but no cap value could be located near it"
        )

    resolved = [(m, cap) for m, cap in all_candidates if _has_liability_concept_nearby(text, cap)]
    if not resolved:
        return None, (
            f"referenced provision \"{label}\" was found and states a numeric value, but the "
            f"surrounding text does not state a limitation-of-liability concept — cannot establish "
            f"that this value is actually the liability cap without attorney review"
        )

    distinct_values = {(c.kind, c.basis, c.multiplier, c.fixed_amount, c.months) for _, c in resolved}
    if len(distinct_values) > 1:
        return None, (
            f"multiple mentions of \"{label}\" were found with different, liability-concept-anchored "
            f"cap values; cannot determine which governs without attorney review"
        )
    return resolved[0][1], ""


def _extract_provision(text: str, anchor_start: int, index: int) -> Provision:
    window_start = anchor_start
    window_end = min(len(text), window_start + _PROVISION_WINDOW_CHARS)
    window = text[window_start:window_end]

    all_cat_positions = _all_category_keyword_positions(window)
    exclusion_coverage = _compute_exclusion_coverage(window, all_cat_positions)
    category_treatments = {
        cat: _classify_category(window, cat, all_cat_positions, exclusion_coverage) for cat in CATEGORIES
    }
    general_cap_expr = _classify_general_cap_expression(window, category_treatments)
    if general_cap_expr.structure != "unresolved" and general_cap_expr.components:
        general_cap_expr.unmapped_role_pair_reason = _unmapped_cap_role_pair_reason(window, text)
    consequential_excluded, consequential_established, carveouts = _classify_consequential_damages(window)
    party_positions = _find_party_positions(window, document_text=text)

    lookback_start = max(0, window_start - 300)
    is_amendment = bool(_AMENDMENT_SIGNAL_RE.search(text[lookback_start:window_end]))

    # Cross-reference: the provision states no cap of its own and instead
    # delegates to another named section/schedule/exhibit/order form/DPA.
    # Prefer resolving it deterministically when the referenced provision
    # exists in the document and is unambiguous; otherwise this becomes
    # REQUIRES_REVIEW (naming the reference) rather than the misleading
    # MUST_REDLINE ("insert cap language") — a delegated cap isn't missing,
    # it's just not stated here.
    cross_reference_info = None
    if not general_cap_expr.components and general_cap_expr.structure == "simple":
        cross_ref = _detect_cross_reference(window)
        if cross_ref:
            label, sig_start, sig_end = cross_ref
            if label:
                resolved_cap, reason = _resolve_cross_reference(text, window_start, window_end, label)
                if resolved_cap is not None:
                    # _resolve_cross_reference searched the full document, so
                    # its offsets are already absolute — convert back to
                    # window-relative here so the generic re-anchor pass
                    # below (which adds window_start once) stays uniform
                    # across every code path instead of needing a special case.
                    resolved_cap.start_index -= window_start
                    resolved_cap.end_index -= window_start
                    general_cap_expr = CapExpression(
                        structure="simple", components=[resolved_cap],
                        raw_excerpt=resolved_cap.raw_excerpt,
                        start_index=resolved_cap.start_index, end_index=resolved_cap.end_index,
                    )
                    cross_reference_info = {"label": label, "resolved": True, "reason": ""}
                else:
                    general_cap_expr = _unresolved(
                        f"delegates to \"{label}\" — {reason}",
                        raw_excerpt=_excerpt(window, sig_start, sig_end), start_index=sig_start, end_index=sig_end,
                    )
                    cross_reference_info = {"label": label, "resolved": False, "reason": reason}
            else:
                general_cap_expr = _unresolved(
                    "delegates to a cross-referenced provision that could not be identified by name",
                    raw_excerpt=_excerpt(window, sig_start, sig_end), start_index=sig_start, end_index=sig_end,
                )
                cross_reference_info = {"label": "", "resolved": False, "reason": "no named reference target"}

    cap, _ = general_cap_expr.effective_cap() if general_cap_expr.structure != "unresolved" else (None, None)
    if general_cap_expr.components or general_cap_expr.structure == "unresolved":
        raw_excerpt = general_cap_expr.raw_excerpt or _excerpt(text, window_start, min(window_end, window_start + 300))
        start_index = window_start + general_cap_expr.start_index if general_cap_expr.raw_excerpt else window_start
        end_index = window_start + general_cap_expr.end_index if general_cap_expr.raw_excerpt else min(window_end, window_start + 300)
    else:
        raw_excerpt = _excerpt(text, window_start, min(window_end, window_start + 200))
        start_index = window_start
        end_index = min(window_end, window_start + 200)

    # Re-anchor every window-relative span to absolute document offsets.
    for c in general_cap_expr.components:
        c.start_index += window_start
        c.end_index += window_start
    for t in category_treatments.values():
        if t.cap is not None:
            t.cap.start_index += window_start
            t.cap.end_index += window_start
    for pp in party_positions.values():
        for c in pp.cap_expression.components:
            c.start_index += window_start
            c.end_index += window_start

    # Step 4A.11 Phase 4 — direct safety-defect evidence: this module
    # never checked is_operative_context anywhere, so a quoted example
    # explicitly negated afterward ("A typical clause reads: 'Aggregate
    # liability shall not exceed $1,000,000.' This Agreement does not
    # include such a clause.") was established as a real cap
    # (fab-lia-af6-quoted-example-01). If EVERY component of the
    # resolved cap expression fails the shared operative-context check,
    # the expression is downgraded to unresolved rather than trusted --
    # mirrors how a cross-reference failure already downgrades to
    # unresolved elsewhere in this function.
    if general_cap_expr.components and general_cap_expr.structure != "unresolved":
        if all(not _core_is_operative_context(text, c.start_index, c.end_index) for c in general_cap_expr.components):
            general_cap_expr = _unresolved(
                "the only candidate cap value found sits in quoted/negated/non-operative "
                "context (e.g. a rejected example, a heading, or explicitly negated text), "
                "not the document's own operative term",
                raw_excerpt=general_cap_expr.raw_excerpt,
                start_index=general_cap_expr.start_index, end_index=general_cap_expr.end_index,
            )
            cap = None

    section_label = _section_label_before(text, window_start)
    # Step 4A.11 Phase 2 — when a cap VALUE was actually found, start_index/
    # end_index above are already anchored at that value's own position
    # (not the clause heading), so a sentence-scoped scan there correctly
    # attaches a condition stated in the same sentence, or the sentence
    # immediately after (the backref family), to THIS value rather than a
    # different party's separately-stated figure elsewhere in the window.
    # When no value was found at all, start_index/end_index fall back to
    # the heading's own position, which is the wrong anchor for a
    # condition that only appears later in the clause — the whole
    # provision window is scanned instead in that case.
    if general_cap_expr.components:
        condition = _core_detect_condition_in_span(text, start_index, end_index)
    else:
        condition = _core_detect_condition_in_text(text[window_start:window_end])
    if section_label:
        conflict = _core_detect_conflicting_backward_conditions(text, "Section", section_label)
        if conflict is not None:
            priority = {"CONFLICTING": 3, "ESTABLISHED": 2, "NOT_ESTABLISHED": 1, "UNCONDITIONAL": 0}
            condition = max((condition, conflict), key=lambda e: priority.get(e.status, 0))

    return Provision(
        index=index, section_label=section_label, is_amendment=is_amendment,
        start_index=start_index, end_index=end_index, raw_excerpt=raw_excerpt,
        general_cap_expression=general_cap_expr, category_treatments=category_treatments,
        party_positions=party_positions, consequential_damages_excluded=consequential_excluded,
        consequential_damages_established=consequential_established, consequential_damages_carveouts=carveouts,
        cross_reference=cross_reference_info, condition=condition,
        operative_window_excerpt=(window[:800] if window else ""),
    )


def _sentence_start_before(text: str, index: int) -> int:
    """Start of the sentence/paragraph containing `index`, bounded by
    _SECONDARY_LOOKBACK. Deterministic and purely positional — no
    heuristics about content."""
    lower_bound = max(0, index - _SECONDARY_LOOKBACK)
    segment = text[lower_bound:index]
    best = 0
    for boundary in (". ", ".\n", "\n\n", "; "):
        pos = segment.rfind(boundary)
        if pos != -1:
            best = max(best, pos + len(boundary))
    return lower_bound + best


def _discover_anchors(text: str) -> List[Tuple[int, bool]]:
    """Every provision anchor in the document as (window_start, is_labelled),
    in document order, deduplicated.

    Layer 1 (labelled) anchors are taken as-is. Layer 2 (drafting) anchors
    are only accepted when they are NOT already inside/near a labelled
    provision — a cap sentence sitting under a "Limitation of Liability"
    heading is the same provision, not a second one — and when their local
    context doesn't disqualify them (see _SECONDARY_DISQUALIFIER_RE)."""
    primary = [(m.start(), True) for m in _ANCHOR_RE.finditer(text)]

    secondary: List[Tuple[int, bool]] = []
    for m in _SECONDARY_ANCHOR_RE.finditer(text):
        local = text[max(0, m.start() - _SECONDARY_LOCAL_WINDOW): m.end() + _SECONDARY_LOCAL_WINDOW]
        if _SECONDARY_DISQUALIFIER_RE.search(local):
            continue
        # Suppressed when a labelled provision already covers this text —
        # its own window (_PROVISION_WINDOW_CHARS) will read this sentence.
        if any(p_start <= m.start() < p_start + _PROVISION_WINDOW_CHARS for p_start, _ in primary):
            continue
        secondary.append((_sentence_start_before(text, m.start()), False))

    candidates = sorted(primary + secondary, key=lambda a: a[0])

    accepted: List[Tuple[int, bool]] = []
    for start, is_labelled in candidates:
        if accepted and start - accepted[-1][0] < _ANCHOR_DEDUP_GAP:
            continue  # same clause mentioning itself again, not a new provision
        accepted.append((start, is_labelled))
    return accepted


# Off by default — mirrors indemnification_policy_engine.HYBRID_DISCOVERY_
# ENABLED's rollout discipline (a module-level switch a deployer/test flips
# explicitly, never inferred from whether OPENAI_API_KEY happens to be
# set). With this off, extract_liability_facts behaves byte-identically to
# before this integration: regex-only discovery, CONFIRMED_ABSENT ->
# NOT_APPLICABLE when nothing is found. This keeps the existing 78-case
# regression suite (see tests/test_liability_policy_engine.py) passing
# unchanged in any environment without a configured provider, and lets
# Step 1's single-adapter rollout be enabled independently of whether a
# provider key exists in a given deployment/test environment.
LIABILITY_SEMANTIC_DISCOVERY_ENABLED = False  # module-load-time default; immediately overridden below
import fact_admission as _fact_admission_env_check
LIABILITY_SEMANTIC_DISCOVERY_ENABLED = _fact_admission_env_check.semantic_discovery_enabled("LIABILITY_SEMANTIC_DISCOVERY_ENABLED")
del _fact_admission_env_check

_LIABILITY_SEMANTIC_FOCUS = (
    "one party's exposure to damages, losses, or claims under this agreement being "
    "limited, capped, excluded, or expressly stated to be unlimited — a limitation-"
    "of-liability concept — even if the wording is unusual or does not use standard "
    "terms like 'limitation of liability' or 'cap'"
)
_LIABILITY_SEMANTIC_PROPOSITION = (
    "This sentence or clause is operative language of this agreement that limits, "
    "caps, excludes, or expressly leaves unlimited a party's liability, damages, or "
    "losses arising under this agreement."
)


def _run_semantic_discovery(text: str) -> Tuple[List, Optional[str], bool, Optional[str]]:
    """Additive semantic discovery for liability-cap language the
    deterministic anchors above did not recognize. Mirrors
    indemnification_policy_engine._run_semantic_discovery exactly, using
    the shared fact_admission framework instead of a bespoke
    implementation. Returns (admitted_candidates, unresolved_dependency_
    note, note_is_unconditional, error); error is None when discovery ran
    successfully (even if it found nothing — see absence_state in
    extract_liability_facts).

    unresolved_dependency_note (final trust architecture, Step B/H) —
    when a candidate's proposition depended on a cross-reference/
    definition fact_admission.verify_and_ground could NOT resolve, the
    candidate is correctly NOT_ADMITTED and never becomes a provision —
    but that failure is preserved here rather than disappearing, so the
    caller can force REQUIRES_REVIEW instead of falling back to
    CONFIRMED_ABSENT.

    note_is_unconditional (Blocker 2, final pre-freeze blocker
    remediation) — True when unresolved_dependency_note came from a
    specific, always-material mechanism (definition/cross-reference
    dependency, competing readings) that the caller's own materiality
    gate (_any_provision_established, below) must NEVER suppress,
    regardless of what else was established elsewhere in the document.
    False means the note is the generic uncertain-verification catch-all
    (content-uncertain status, or a pure infrastructure failure), the
    only category the caller may legitimately suppress, and only when it
    can prove the same material fact was already genuinely established."""
    if not LIABILITY_SEMANTIC_DISCOVERY_ENABLED:
        return [], None, False, None
    import fact_admission as _fa
    try:
        raw_candidates = _fa.discover_candidate_spans(text, "limitation_of_liability", _LIABILITY_SEMANTIC_FOCUS)
    except Exception as exc:  # noqa: BLE001 — provider unavailable, never "confirmed absent"
        return [], None, False, f"{type(exc).__name__}: {exc}"

    verified_candidates = [
        _fa.verify_and_ground(candidate, text, _LIABILITY_SEMANTIC_PROPOSITION) for candidate in raw_candidates
    ]
    admitted = [c for c in verified_candidates if c.admission_status == _fa.ADMITTED]
    # Uses the shared helper (not a hand-rolled duplicate) so this adapter
    # automatically picks up every unresolved-dependency case the shared
    # framework knows about -- including competing readings, added after
    # an adapter-level test here first exposed that a hand-rolled
    # duplicate of this check (the prior version of this function) never
    # covered that case at all.
    unresolved_dependency_note = _fa.first_unresolved_dependency_note(verified_candidates)
    note_is_unconditional = _fa.first_unresolved_dependency_note_is_unconditional(verified_candidates)
    return admitted, unresolved_dependency_note, note_is_unconditional, None


def extract_liability_facts(text: str) -> Optional[LiabilityFacts]:
    """Thin wrapper over _extract_liability_facts_inner that additionally
    flags a document-wide contradiction/unreconciled-ambiguity marker
    (Candidate 3 zero-silent-loss mission, Phase 3) -- kept as a wrapper
    rather than threading the flag through every one of the inner
    function's several return points."""
    facts = _extract_liability_facts_inner(text)
    if facts is not None and (
        _document_wide_conflict_detected(text) or _unreconciled_ambiguity_marker_present(text)
    ):
        facts.document_wide_conflict = True
    return facts


def _extract_liability_facts_inner(text: str) -> Optional[LiabilityFacts]:
    """Discovers every liability-limitation provision in the full document
    (not just the first) and reconciles them. Returns None only when no such
    provision exists at all anywhere in the document AND semantic discovery
    (see _run_semantic_discovery) also ran successfully and found nothing —
    a semantic-discovery provider outage/error never collapses into "no
    clause," it becomes RECOGNITION_UNCERTAIN instead (see absence_state).

    Discovery is two-layered — an explicitly labelled provision, or ordinary
    commercial cap drafting with no heading at all. See _ANCHOR_RE /
    _SECONDARY_ANCHOR_RE. A third, additive layer (semantic discovery) runs
    only when the first two find nothing, proposing candidate spans that
    must independently pass adversarial semantic verification AND
    deterministic grounding before they can seed a provision window — see
    fact_admission.py. A semantically-admitted candidate is treated exactly
    like any other anchor: it still has to survive the same deterministic
    _extract_provision structuring any regex-found anchor does, so it can
    reach PRESENT_AND_VERIFIED-equivalent status but never bypasses
    structural verification the way a raw LLM classification would."""
    accepted_anchors = _discover_anchors(text)
    semantic_error: Optional[str] = None
    semantic_qualifiers_by_start: Dict[int, Any] = {}
    unresolved_dependency_note: Optional[str] = None
    # Candidate 3 remediation (Root Cause 2): contextual discovery is no
    # longer gated behind "deterministic anchor discovery found zero
    # matches" -- see confidentiality_policy_engine.py's identical fix.
    # Root Cause 1 does not apply to this adapter: an admitted-but-
    # unparseable candidate already becomes a Provision with
    # general_cap=None, which evaluate_liability_policy already routes to
    # MUST_REDLINE ("clause present but no numeric general cap stated") —
    # never a silent ACCEPT/NOT_APPLICABLE. See PRE_IMPLEMENTATION_MAP.md.
    admitted_semantic, unresolved_dependency_note, note_is_unconditional, semantic_error = _run_semantic_discovery(text)
    if not accepted_anchors:
        if admitted_semantic:
            accepted_anchors = [(c.start_offset, False) for c in admitted_semantic]
            # Final trust architecture (Phase 5) — keep each admitted
            # candidate's own grounded condition/exception (see
            # fact_admission.evaluate_admission's qualifier-grounding gate)
            # so it can be forced into review below if the deterministic
            # structuring below doesn't independently already capture it.
            # A candidate reaching here already passed grounding for any
            # qualifier it claimed, so .condition/.exception are either
            # None or a real, grounded quote — never a dropped/fabricated one.
            semantic_qualifiers_by_start = {c.start_offset: c for c in admitted_semantic}
        elif semantic_error is not None:
            return LiabilityFacts(
                clause_found=True, provisions=[], absence_state="RECOGNITION_UNCERTAIN",
                semantic_discovery_error=semantic_error,
                reconciliation="single", reconciliation_explanation="",
            )
        elif unresolved_dependency_note is not None:
            # Final trust architecture (Step B/H, zero-silent-loss) — a
            # candidate was found and its proposition depended on a
            # cross-reference/definition that could not be
            # deterministically resolved. It never became a provision,
            # but it must not silently collapse into CONFIRMED_ABSENT
            # either — see evaluate_liability_policy's DEPENDENCY_
            # UNRESOLVED branch.
            return LiabilityFacts(
                clause_found=True, provisions=[], absence_state="DEPENDENCY_UNRESOLVED",
                semantic_discovery_error=unresolved_dependency_note,
                reconciliation="single", reconciliation_explanation="",
            )
        else:
            return None
    # Note: when accepted_anchors is already non-empty (deterministic
    # anchors exist), any ADDITIONALLY admitted semantic candidate is
    # currently not merged into the provisions list -- this adapter's
    # qualifier-composition loop below matches admitted candidates to
    # provisions strictly by shared anchor offset (accepted_anchors), and
    # a corroborating-but-not-identical AI candidate's own offset would
    # not line up with a provision it didn't seed. This is a known,
    # narrower scope than the other 11 adapters' "always add AI's
    # qualifiers regardless of which channel found the anchor" behavior;
    # recorded as a residual risk rather than silently left unstated.

    provisions = [_extract_provision(text, start, i) for i, (start, _) in enumerate(accepted_anchors)]

    # Final trust architecture (Phase 5) — the AI/context layer may notice
    # a material condition or exception that the deterministic regex-based
    # condition detector (_core_detect_condition_in_span, run inside
    # _extract_provision above) missed entirely, since it only recognizes
    # a finite set of conditional-clause patterns. If the AI found and
    # GROUNDED one, and the deterministic pass found none, this is
    # EXACTLY the "AI notices what regex misses" case the shared
    # discovery layer already exists for elsewhere — it must not be
    # silently dropped merely because it arrived from the semantic path.
    # Composing it into the SAME provision.condition field
    # evaluate_liability_policy already reads (see the `if provision.
    # condition is not None` block there) means no new decision branch is
    # needed: any non-None condition, regardless of source, already
    # forces this provision into REQUIRES_REVIEW rather than a clean
    # decision -- the mission's Phase 4 fail-closed rule for an
    # unresolved qualifier is satisfied by construction, not by a new
    # special case.
    # Matched by POSITION in accepted_anchors, not by provision.start_index
    # -- _extract_provision may re-anchor start_index to the cap
    # expression's own offset within the window (see its two branches
    # above), which can differ from the original anchor offset the
    # candidate was keyed by. List order is preserved 1:1 by the
    # comprehension that built `provisions` from `accepted_anchors` above.
    for provision, (anchor_start, _) in zip(provisions, accepted_anchors):
        candidate = semantic_qualifiers_by_start.get(anchor_start)
        if candidate is None:
            continue
        # The deterministic detector's "nothing found" sentinel is a real
        # ConditionEvidence(status="UNCONDITIONAL"), not None — only skip
        # when the deterministic pass already independently established,
        # rejected, or flagged a conflicting condition of its own.
        if provision.condition is not None and provision.condition.status != "UNCONDITIONAL":
            continue
        qualifier_text = candidate.condition or candidate.exception
        dependency_note = None
        if qualifier_text is None:
            dr, xr = candidate.definition_resolution, candidate.cross_reference_resolution
            # Both are guaranteed RESOLVED here — a candidate with an
            # unresolved definition/cross-reference is NOT_ADMITTED and
            # so never appears in semantic_qualifiers_by_start at all
            # (see fact_admission.evaluate_admission's zero-silent-loss
            # gate); the unresolved case is handled separately above via
            # unresolved_dependency_note, since there is no provision to
            # attach it to when accepted_anchors was empty.
            if dr is not None:
                dependency_note = f'depends on the defined term "{dr.term}": {dr.definition_evidence}'
            elif xr is not None:
                dependency_note = f'depends on the cross-referenced "{xr.label}": {xr.target_evidence}'
        qualifier_text = qualifier_text or dependency_note
        if qualifier_text is None:
            continue
        provision.condition = ConditionEvidence(
            status="ESTABLISHED", condition_type="ai_identified",
            evidence_span=qualifier_text,
            note="identified by contextual AI analysis and independently grounded against the source document",
        )

    # Zero-silent-loss mission follow-up, second-order fix -- an
    # unresolved_dependency_note sourced from a candidate whose OWN
    # semantic verification was merely uncertain (never a disproven claim)
    # must only be suppressed when a deterministic anchor already exists
    # and GENUINELY, POSITIVELY resolved something material for this same
    # clause (a real numeric cap, an actually-triggered category carve-out,
    # a real condition) -- never merely because SOME dimension defaulted
    # to its confident-negative sentinel.
    #
    # Candidate 3 final pre-freeze blocker remediation (Blocker 2) -- the
    # ORIGINAL version of this gate checked `any(t.established for t in
    # p.category_treatments.values())`, but category_treatments always
    # contains one CategoryTreatment per CATEGORIES entry, and a category
    # nobody mentioned in the text still comes back `treatment=
    # "not_addressed", established=True` (a legitimate, confident
    # deterministic finding that the category is silent -- just not
    # evidence that a DIFFERENT, uncertain AI candidate is redundant).
    # Since every real provision has at least one such "not_addressed"
    # category, the original gate was ALWAYS true regardless of whether
    # the cap itself, or anything else material, was ever established --
    # confirmed by direct reproduction: a bare "This Section addresses
    # liability matters generally." provision (nothing established at
    # all) still satisfied the old gate. Fixed by requiring the category
    # signal to be an actual, positive determination (treatment not in
    # {"not_addressed", "unresolved"}), not merely "established" in the
    # confident-negative sense. Re-verified against both the
    # nothing-established shape (gate now correctly False) and the
    # limitation_of_liability-006 shape (gate still correctly True, since
    # that case's gross_negligence/willful_misconduct carve-outs are
    # genuinely, positively triggered as "uncapped", not merely silent).
    _any_provision_established = any(
        p.general_cap_expression.effective_cap()[0] is not None
        or any(
            t.established and t.treatment not in ("not_addressed", "unresolved")
            for t in p.category_treatments.values()
        )
        or (p.condition is not None and p.condition.status == "ESTABLISHED")
        for p in provisions
    )
    surfaced_unresolved_dependency_note = (
        unresolved_dependency_note if (note_is_unconditional or not _any_provision_established) else None
    )

    if len(provisions) == 1:
        return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=provisions[0],
                               reconciliation="single", reconciliation_explanation="Single provision found.",
                               ai_identified_unresolved_dependency=surfaced_unresolved_dependency_note)

    # Reconciliation: prefer an explicit amendment/restatement over the
    # provisions it supersedes. If multiple provisions carry an amendment
    # signal, the last one in document order is the most recent.
    amendment_provisions = [p for p in provisions if p.is_amendment]
    if amendment_provisions:
        controlling = amendment_provisions[-1]
        others = [p for p in provisions if p is not controlling]
        explanation = (
            f"{len(provisions)} Limitation of Liability provisions found; "
            f"{controlling.provision_label()} contains explicit amendment/restatement language "
            f"and supersedes {', '.join(p.provision_label() for p in others)}."
        )
        return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=controlling,
                               reconciliation="amendment_resolved", reconciliation_explanation=explanation,
                               ai_identified_unresolved_dependency=surfaced_unresolved_dependency_note)

    # No amendment signal — if every provision's effective general cap
    # agrees, they're consistent (e.g. a clause quoted or cross-referenced
    # more than once); otherwise this is a genuine unreconciled conflict.
    effective_values = []
    all_resolved = True
    for p in provisions:
        cap, reason = p.general_cap_expression.effective_cap()
        if cap is None:
            all_resolved = False
            break
        effective_values.append((cap.kind, cap.multiplier, cap.fixed_amount, cap.months))

    if all_resolved and len(set(effective_values)) == 1:
        explanation = f"{len(provisions)} Limitation of Liability provisions found, all stating the same cap."
        return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=provisions[0],
                               reconciliation="consistent_duplicate", reconciliation_explanation=explanation,
                               ai_identified_unresolved_dependency=surfaced_unresolved_dependency_note)

    explanation = (
        f"{len(provisions)} Limitation of Liability provisions found with no explicit amendment/restatement "
        f"language tying them together, and their terms do not agree: "
        + "; ".join(f"{p.provision_label()}: {p.general_cap_expression.summary()}" for p in provisions)
        + ". Cannot determine which provision controls without attorney review."
    )
    return LiabilityFacts(clause_found=True, provisions=provisions, controlling_provision=None,
                           reconciliation="unreconciled", reconciliation_explanation=explanation,
                           ai_identified_unresolved_dependency=surfaced_unresolved_dependency_note)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _fmt_multiplier(value: Optional[float]) -> str:
    if value is None:
        return "unspecified"
    return f"{value:g}x annual fees"


def _build_ladder(policy: PolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", f"Preferred position: {_fmt_multiplier(policy.preferred_multiplier)}"),
        ("ACCEPTABLE", f"Auto-accept up to {_fmt_multiplier(policy.acceptable_max_multiplier)}"),
        ("FALLBACK", f"Negotiate up to {_fmt_multiplier(policy.negotiate_max_multiplier)}"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Unlimited liability — prohibited by policy" if policy.prohibit_unlimited else "Unlimited liability"),
    ]
    return _core_build_ladder(state, step_specs)


def _category_treatments_dict(provision: Provision) -> List[Dict[str, str]]:
    return [
        {
            "category": t.category, "treatment": t.treatment,
            "cap_summary": t.cap.summary() if t.cap else None,
            "raw_excerpt": t.raw_excerpt, "established": t.established,
        }
        for t in provision.category_treatments.values()
    ]


def _resolve_directional_position(
    provision: Provision, policy: PolicyRuleLike,
) -> Tuple[Optional[CapExpression], Optional[Dict[str, str]], Optional[Dict[str, str]], Optional[str]]:
    """When a provision states 2+ distinct named-role positions with
    different cap expressions, determines which is "ours" per
    policy.contract_side. Returns (our_cap_expression, our_position_dict,
    counterparty_position_dict, unresolved_reason). Thin LoL-specific
    wrapper over policy_engine_core.resolve_directional_position: builds
    PositionCandidates from CapExpressions, delegates the actual
    ours-vs-theirs algorithm to the shared core, then maps the chosen
    candidate back to its CapExpression."""
    positions = list(provision.party_positions.values())
    candidates = [
        PositionCandidate(
            role=pp.role, side=pp.side,
            dedup_key=(
                (pp.cap_expression.components[0].kind, pp.cap_expression.components[0].compare_key())
                if pp.cap_expression.components else None
            ),
            summary=pp.cap_expression.summary(),
        )
        for pp in positions
    ]
    chosen, our_dict, their_dict, reason = _core_resolve_directional_position(
        candidates, policy.contract_side,
        position_label="asymmetric liability positions", value_label="cap",
    )
    if chosen is None:
        # Step 4A: if any position's side is unresolved specifically
        # because the document's own definition of that role conflicts
        # with the generic vocabulary (not merely because the role name
        # was unrecognized), surface that specific reason instead of the
        # generic "could not be confidently mapped" text — a lawyer
        # reading unresolved_facts should see WHY, not just THAT.
        conflict_reasons = [pp.side_conflict_reason for pp in positions if pp.side_conflict_reason]
        if conflict_reasons:
            reason = "; ".join(conflict_reasons) + (f" ({reason})" if reason else "")
        return None, our_dict, their_dict, reason
    matching_pp = next(pp for pp in positions if pp.role == chosen.role)
    return matching_pp.cap_expression, our_dict, their_dict, reason


def evaluate_liability_policy(
    facts: Optional[LiabilityFacts],
    policy: PolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    """Deterministic state machine: structured contract facts x PolicyRule
    thresholds -> one authoritative PolicyDecision, or REQUIRES_REVIEW when
    a fact the decision depends on cannot be reliably established
    (unreconciled provisions, a compound cap that doesn't reduce to one
    comparable value, an unmappable directional structure, ambiguous
    category carve-out language). No confidence score at any branch."""
    if facts is not None and not facts.provisions and facts.absence_state == "RECOGNITION_UNCERTAIN":
        # Fact-admission architecture (Step 5/6): a semantic-discovery
        # provider outage/error must never be reported as "this contract
        # does not address liability caps" (NOT_APPLICABLE, which
        # document_aggregation.py and interaction_engine_core.py both
        # treat as safely excludable). It must escalate instead — see
        # fact_admission.py and _run_semantic_discovery above.
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Could not determine whether a limitation-of-liability clause is present",
            policy_limit_summary=_fmt_multiplier(policy.preferred_multiplier),
            required_action="Manual review required — automated recognition was unavailable for this document.",
            explanation=(
                "Deterministic pattern matching found no limitation-of-liability clause, and semantic "
                f"verification could not confirm its absence ({facts.semantic_discovery_error or 'unavailable'}). "
                "This is not the same as confirming the contract has no such clause."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source,
        )

    if facts is not None and not facts.provisions and facts.absence_state == "DEPENDENCY_UNRESOLVED":
        # Final trust architecture (Step B/H, zero-silent-loss) — a
        # candidate liability provision was identified by contextual
        # analysis, but its meaning depended on a cross-reference or
        # defined term this document does not deterministically resolve.
        # Never dropped so the document can fall through to "no clause
        # found" — forced to review instead.
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="A candidate liability limitation was identified but a material dependency could not be resolved",
            policy_limit_summary=_fmt_multiplier(policy.preferred_multiplier),
            required_action="Manual review required — a cross-reference or defined term this provision depends on could not be located in this document.",
            explanation=(
                f"Contextual analysis identified language that may limit liability, but {facts.semantic_discovery_error}. "
                "This evaluation does not determine what the provision actually means without that dependency resolved."
            ),
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source,
        )

    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No limitation-of-liability clause found",
            policy_limit_summary=_fmt_multiplier(policy.preferred_multiplier),
            required_action="None — this contract does not address liability caps",
            explanation="No limitation-of-liability clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source,
        )

    if facts.reconciliation == "unreconciled":
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=REQUIRES_REVIEW,
            contract_language=facts.reconciliation_explanation,
            extracted_summary="Multiple unreconciled provisions",
            policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
            required_action="Manual review required — " + facts.reconciliation_explanation,
            explanation=facts.reconciliation_explanation,
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=["controlling provision could not be determined among multiple candidates"],
            start_index=facts.provisions[0].start_index, end_index=facts.provisions[0].end_index,
            source=source, reconciliation=facts.reconciliation,
        )

    provision = facts.controlling_provision
    controlling_provision_dict = {
        "label": provision.provision_label(), "excerpt": provision.raw_excerpt,
        "start_index": provision.start_index, "end_index": provision.end_index,
    }
    required_exceptions = list(policy.required_exceptions_json or [])
    unresolved_facts: List[str] = []

    # Candidate 3 zero-silent-loss mission — a document-wide contradiction
    # or self-declared unreconciled ambiguity must block clean regardless
    # of what the local provision otherwise established.
    if facts.document_wide_conflict:
        unresolved_facts.append(
            "a separate statement elsewhere in the document appears to contradict, negate, or leave unreconciled "
            "the liability cap established in this clause"
        )

    if facts.ai_identified_unresolved_dependency:
        unresolved_facts.append(
            f"a material dependency was identified by contextual analysis but could not be confidently "
            f"confirmed ({facts.ai_identified_unresolved_dependency})"
        )

    # Step 4A.7.1 remediation (A6-L-52) — only relevant when the policy
    # actually needs to know which named party is "us" (see the
    # CapExpression.unmapped_role_pair_reason docstring for why this is
    # gated on contract_side rather than firing unconditionally).
    if policy.contract_side != "mutual" and provision.general_cap_expression.unmapped_role_pair_reason:
        unresolved_facts.append(
            f"role attribution ({provision.general_cap_expression.unmapped_role_pair_reason})"
        )

    # Directional resolution — only engages when 2+ distinct role positions exist.
    directional_cap_expr, our_position, counterparty_position, directional_reason = _resolve_directional_position(
        provision, policy,
    )
    if directional_reason:
        unresolved_facts.append(f"directional liability position ({directional_reason})")
    general_cap_expr = directional_cap_expr if directional_cap_expr is not None else provision.general_cap_expression

    general_cap, general_cap_reason = general_cap_expr.effective_cap()
    if general_cap_reason:
        unresolved_facts.append(f"general liability cap ({general_cap_reason})")
    elif (
        general_cap is not None and general_cap.kind == "fee_multiplier"
        and general_cap.basis == BASIS_RECURRING_PAYMENT
        and "fee" in provision.raw_excerpt.lower()
    ):
        # Step 4A.5 Priority 4 negative control: this clause ALSO
        # separately mentions "fee(s)" as a distinct quantity alongside
        # its own royalties/premium/rent/charges basis — two different
        # payment streams may exist, so this basis must not be silently
        # treated as interchangeable with the policy's fees-defined
        # threshold.
        general_cap_reason = (
            "cap is expressed as a multiplier of a recurring payment basis that is not 'fees', and this "
            "document separately mentions fees as well — cannot confirm they are the same quantity"
        )
        unresolved_facts.append(f"general liability cap ({general_cap_reason})")
        general_cap = None
    elif general_cap is not None and general_cap.kind == "fee_multiplier" and general_cap.basis not in (BASIS_FEES, BASIS_RECURRING_PAYMENT):
        # A multiplier of purchase price / contract value / some other
        # basis is not comparable to a policy threshold defined as "Nx
        # annual fees" — preserve the exact source language, don't force
        # it into fee-multiplier semantics by comparing it anyway.
        basis_label = (general_cap.basis or BASIS_OTHER).replace("_", " ").title()
        general_cap_reason = (
            f"cap is expressed as a multiplier of {basis_label}, not fees — policy thresholds are "
            f"defined as a multiplier of annual fees and this cannot be compared without additional information"
        )
        unresolved_facts.append(f"general liability cap ({general_cap_reason})")
        general_cap = None
    elif general_cap is not None and general_cap.kind == "fee_period":
        # v1 thresholds are multipliers of annual fees. A symbolic fee-period
        # cap (e.g. 6 months' fees) must not be silently converted to money
        # or to months/12. Fail closed; LoL v2 compares fee periods symbolically.
        general_cap_reason = (
            "cap is expressed as a fee-period duration rather than a fees multiplier — "
            "v1 thresholds cannot compare this symbolically; use a v2 LoL position"
        )
        unresolved_facts.append(f"general liability cap ({general_cap_reason})")
        general_cap = None
    # Step 4A.5 Priority 4: BASIS_RECURRING_PAYMENT with no competing "fee"
    # mention falls through here with general_cap intact — a recurring
    # per-period payment stream (royalties/premium/rent/charges) that is
    # the clause's own sole payment basis is functionally the same policy
    # concept as "fees" and is compared against the threshold exactly like
    # a BASIS_FEES multiplier below.

    for cat in required_exceptions:
        treatment = provision.category_treatments.get(cat)
        if treatment is not None and treatment.treatment == "unresolved":
            unresolved_facts.append(f"{cat} treatment (ambiguous carve-out language)")

    if policy.require_consequential_damages_exclusion and not provision.consequential_damages_established:
        unresolved_facts.append("consequential damages exclusion (ambiguous language)")

    # Step 4A.11 Phase 2 — a conditional fact may become authoritative only
    # WITH its condition preserved; this engine does not evaluate whether a
    # condition's real-world trigger is satisfied.
    if provision.condition is not None and provision.condition.status == "ESTABLISHED":
        unresolved_facts.append(
            f"liability cap is conditionally applicable ({provision.condition.condition_type}: "
            f"\"{provision.condition.evidence_span}\") — this evaluation does not determine whether "
            f"the stated condition is satisfied"
        )
    elif provision.condition is not None and provision.condition.status == "NOT_ESTABLISHED":
        unresolved_facts.append(
            f"liability cap's applicability (condition-shaped language present but its scope/"
            f"attachment cannot be established: \"{provision.condition.evidence_span}\")"
        )
    elif provision.condition is not None and provision.condition.status == "CONFLICTING":
        unresolved_facts.append(f"liability cap's applicability ({provision.condition.note})")

    if unresolved_facts:
        state = REQUIRES_REVIEW
        explanation = requires_review_explanation("clause", provision.raw_excerpt, unresolved_facts)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="limitation_of_liability", state=state,
            contract_language=provision.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
            required_action=requires_review_required_action(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=_category_treatments_dict(provision), unresolved_facts=unresolved_facts,
            start_index=provision.start_index, end_index=provision.end_index, source=source,
            controlling_provision=controlling_provision_dict, our_position=our_position,
            counterparty_position=counterparty_position, reconciliation=facts.reconciliation,
        )

    missing_exceptions = [
        cat for cat in required_exceptions
        if provision.category_treatments.get(cat) is not None
        and provision.category_treatments[cat].treatment not in ("uncapped", "super_cap")
    ]
    # Candidate 3 final gap-closure fix (Section 9, zero-silent-loss): a
    # deterministically-established carve-out (uncapped/super_cap
    # treatment) for a category the CURRENT policy doesn't happen to name
    # in required_exceptions_json was previously completely invisible in
    # the final decision -- present in provision.category_treatments
    # internally, but never surfaced in the explanation/notes, and never
    # distinguished a plain ACCEPT from an ACCEPT with a carve-out
    # present. This is exactly the "grounded + preserved internally, but
    # silently dropped from the decision surface" gap the burned corpus's
    # YES_BUT_EXCEPTION family exposed (e.g. limitation_of_liability-006,
    # -015). A carve-out for gross negligence/willful misconduct/
    # indemnification etc. is not inherently a policy violation (many
    # playbooks expect exactly such a carve-out), so this does not force
    # an escalation -- it surfaces as ACCEPT_WITH_NOTE rather than a bare
    # ACCEPT whenever the cap itself is otherwise compliant, so the fact
    # remains visible to a reviewer instead of disappearing into an
    # undifferentiated clean decision.
    # Only "uncapped" (a genuinely unlimited exposure for that category) is
    # treated as a silently-lost material fact -- "super_cap" is already a
    # fully quantified, distinct value that surfaces via category_treatments
    # in the decision output regardless (see
    # test_data_breach_super_cap_is_captured_distinctly_from_general_cap),
    # so nothing is actually lost for that treatment kind.
    other_established_exceptions = [
        cat for cat, t in provision.category_treatments.items()
        if t.established and t.treatment == "uncapped" and cat not in required_exceptions
    ]
    missing_consequential = (
        policy.require_consequential_damages_exclusion
        and provision.consequential_damages_excluded is not True
    )
    missing_consequential_carveouts = []
    if policy.require_consequential_damages_exclusion and provision.consequential_damages_excluded is True:
        missing_consequential_carveouts = [
            c for c in (policy.required_consequential_carveouts_json or [])
            if c not in provision.consequential_damages_carveouts
        ]

    if general_cap is None:
        state = MUST_REDLINE
        extracted_summary = "Limitation-of-liability clause present but no numeric general cap stated"
        required_action = "Redline — insert the approved cap language"
        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". A limitation-of-liability clause exists but "
            f"states no enforceable numeric general cap. Company policy requires a stated cap. Result: {state}."
        )
    elif general_cap.kind == "unlimited":
        state = PROHIBITED if policy.prohibit_unlimited else ESCALATE
        extracted_summary = "Unlimited liability"
        required_action = "Replace clause — apply the approved fallback cap" if state == PROHIBITED else "Escalate for approval — unlimited liability exceeds policy"
        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". Extracted value: Unlimited. "
            f"Company policy: unlimited liability is {'prohibited' if policy.prohibit_unlimited else 'permitted only with escalation'}. "
            f"Result: {state}."
        )
    elif general_cap.kind == "fixed_amount":
        state = ESCALATE
        extracted_summary = general_cap.summary()
        required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — cap is a fixed dollar amount, not a fees multiplier; compare manually against policy"
        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". Extracted value: {general_cap.summary()}. "
            f"Policy is defined as a multiplier of annual fees, so this cannot be compared automatically. Result: {state}."
        )
    else:  # fee_multiplier
        value = general_cap.multiplier
        extracted_summary = general_cap.summary()
        state = classify_by_threshold(
            value, policy.preferred_multiplier, policy.acceptable_max_multiplier, policy.negotiate_max_multiplier,
        )

        if state in (ACCEPT, ACCEPT_WITH_NOTE) and (missing_exceptions or missing_consequential or missing_consequential_carveouts):
            state = NEGOTIATE
        elif state == ACCEPT and other_established_exceptions:
            state = ACCEPT_WITH_NOTE

        notes = []
        if missing_exceptions:
            notes.append(f"missing required exception(s): {', '.join(missing_exceptions)}")
        if missing_consequential:
            notes.append("policy requires a consequential-damages exclusion, which was not found")
        if missing_consequential_carveouts:
            notes.append(f"consequential-damages exclusion missing required carve-out(s): {', '.join(missing_consequential_carveouts)}")
        if other_established_exceptions:
            notes.append(f"cap does not apply to: {', '.join(other_established_exceptions)}")

        if state == ACCEPT:
            required_action = "None — clause meets preferred position"
        elif state == ACCEPT_WITH_NOTE:
            required_action = "None — within acceptable range, note for the file"
        elif state == NEGOTIATE:
            required_action = "Negotiate down to preferred position" + (f"; {'; '.join(notes)}" if notes else "")
        else:
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — exceeds negotiable range"

        explanation = (
            f"Contract language: \"{provision.raw_excerpt}\". Extracted value: {general_cap.summary()}. "
            f"Policy — preferred: {_fmt_multiplier(policy.preferred_multiplier)}, "
            f"acceptable up to: {_fmt_multiplier(policy.acceptable_max_multiplier)}, "
            f"negotiable up to: {_fmt_multiplier(policy.negotiate_max_multiplier)}. "
            f"Result: {state}."
        )
        if notes and state in (NEGOTIATE, ACCEPT_WITH_NOTE):
            explanation += " " + "; ".join(notes).capitalize() + "."

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="limitation_of_liability", state=state,
        contract_language=provision.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=_fmt_multiplier(policy.negotiate_max_multiplier),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, state),
        category_treatments=_category_treatments_dict(provision), unresolved_facts=unresolved_facts,
        start_index=provision.start_index, end_index=provision.end_index,
        escalate_to=escalate_to_for_state(state, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(state, policy.fallback_text, (MUST_REDLINE, PROHIBITED, NEGOTIATE)),
        source=source, controlling_provision=controlling_provision_dict,
        our_position=our_position, counterparty_position=counterparty_position,
        reconciliation=facts.reconciliation,
    )


# Backward-compatible alias for the pre-hardening single-fact API name.
extract_liability_cap = extract_liability_facts
