"""
Indemnification clause adapter, over policy_engine_core.

This is the second clause adapter — built specifically to test whether
policy_engine_core.py's boundary (extracted from Limitation of Liability
alone) is genuinely reusable or was accidentally shaped around LoL's
specifics. See the "Architecture findings" section at the bottom of this
docstring for what that test found.

SEMANTIC MODEL. Indemnification's hard problem is not a number to compare
against a threshold — that's secondary, and plugs into the shared
threshold machinery once everything else is settled. The hard problem is
topology:

    who -> indemnifies whom -> for what (triggering conduct/claims)
        -> subject to what scope (third-party only vs. also first-party)
        -> subject to what procedure (defense control, notice, cooperation)
        -> subject to what exclusions
        -> subject to what monetary treatment

A single document can state this topology more than once: a reciprocal
clause states it TWICE, once in each direction, and both directions are
simultaneously valid — this is fundamentally different from Limitation of
Liability, where multiple provisions describing the same single "general
cap" concept are competing candidates to be reconciled into one. Two
indemnification obligations pointing in different directions are not in
conflict; they are two different facts about two different promises. This
adapter tracks each directional IndemnityObligation independently rather
than trying to reconcile them into one controlling provision.

Because a lawyer's actual question is directional ("is the counterparty's
promise to us adequate," "is our promise to them excessive"), evaluation
resolves TWO roles from the document — our exposure obligation (we
indemnify them) and our protection obligation (they indemnify us) — and
evaluates each independently against the policy, using the same
REQUIRES_REVIEW-first abstention discipline as Limitation of Liability:
an unmappable role, an ambiguous trigger, or an unresolved monetary
structure always routes to REQUIRES_REVIEW rather than a guessed ACCEPT.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Protocol, Tuple

from policy_engine_core import (
    ACCEPT, ACCEPT_WITH_NOTE, NEGOTIATE, MUST_REDLINE, PROHIBITED, ESCALATE,
    REQUIRES_REVIEW, NOT_APPLICABLE,
    LadderStep, PolicyDecision,
    resolve_role_side,
    build_ladder as _core_build_ladder,
    classify_by_threshold, escalate_to_for_state, fallback_text_for_state,
    excerpt as _excerpt, section_label_before as _section_label_before,
    requires_review_explanation, requires_review_required_action,
    detect_role_attributed_asymmetry,
    trim_role_name,
)

RULE_ID = "POLICY_INDEMNIFICATION"

TRIGGERS = [
    "ip_infringement", "data_breach", "confidentiality",
    "negligence", "gross_negligence", "willful_misconduct",
]

_TRIGGER_KEYWORD_RE = {
    "ip_infringement": re.compile(
        r"\bintellectual property\b.{0,40}\binfringement\b|\bIP infringement\b|\binfringement of\b.{0,40}\bintellectual property\b",
        re.I,
    ),
    "data_breach": re.compile(r"\bdata breach(?:es)?\b|\bsecurity breach(?:es)?\b", re.I),
    "confidentiality": re.compile(r"\bconfidentiality\b|\bconfidential information\b", re.I),
    "gross_negligence": re.compile(r"\bgross negligence\b", re.I),
    "willful_misconduct": re.compile(r"\bwil[l]?ful misconduct\b", re.I),
    # Step 4A.7.1 (A6-C-15): "fraud" was a missing trigger category —
    # a standard indemnification carve-out/exclusion category alongside
    # the six already tracked, not an open-ended addition.
    "fraud": re.compile(r"\bfraud(?:ulent)?\b", re.I),
    # Checked after gross_negligence so "gross negligence" doesn't also
    # register as a bare "negligence" match at a different span.
    "negligence": re.compile(r"\bnegligence\b(?!\s*(?:,|and|or)?\s*gross)", re.I),
}

# Step 4A.5 — multi-word role/entity names ("Host Facility", "Home Health
# Agency", "Underwriting Agent", "Import Broker") were being truncated to
# their LAST word by every role-name capturing group in this file, which
# only ever captured a single capitalized token. This shared fragment
# captures 1-3 consecutive capitalized words (bounded to avoid swallowing
# an entire capitalized sentence-opening run) — the same structural
# pattern already used for single-word roles, generalized. A generic verb
# ("Shall", "The", "This"...) beginning the NEXT clause is lowercase in
# real drafting text and won't extend the match; this is not tied to any
# specific role name.
#
# Step 4A.7 — the 1-3 word cap above was itself too narrow: ordinary
# commercial entity names routinely run 4-5 words ("Pacific Rim Freight
# Brokers", "Continental Data Center Colocation Services"), and capping at
# 3 caused the SAME entity to be captured as two DIFFERENT truncated
# substrings depending on where each obligation match anchored (e.g.
# "Rim Freight Brokers" in one obligation, "Pacific Rim Freight" in the
# other), which then fails role-name equality checks that assume both
# mentions of one real party produce the identical string. Widening to
# 1-5 words is the same bounded-run rationale as the original fix, just
# recalibrated to the length of names actually seen; it is a capacity
# increase, not a new vocabulary entry, and remains far short of
# "arbitrary run of capitalized words" (still stops at the first
# lowercase word).
_MULTIWORD_ROLE_NAME_FRAGMENT = (
    r"[A-Z][A-Za-z]{1,25}(?:\s+[A-Z][A-Za-z]{1,25}){0,4}"
    # Step 4A.5 Priority 4: a role name occasionally has one lowercase
    # connector word inside it ("Importer of Record") — a small, closed
    # set of common connectors (of/the/for), never an arbitrary word,
    # optionally followed by one more capitalized word.
    r"(?:\s+(?:of|the|for)\s+[A-Z][A-Za-z]{1,25})?"
)

_ANCHOR_RE = re.compile(r"indemnif\w*", re.I)

# Step 4A.5 Priority 3 — Recognition-miss family: the SAME legal concept
# (one party makes another financially whole against third-party claims,
# and takes on defense of them) stated WITHOUT the word "indemnif*" at
# all, using a small closed family of known compound synonym idioms
# ("hold X harmless from and defend X against", "protect, defend, and
# reimburse", "undertakes to make X whole for, and to assume the defense
# of", "shall bear full responsibility for defending and satisfying such
# claim on X's behalf"). Each alternative is a full, specific multi-word
# phrase — never a single generic verb like "protect" or "defend" alone —
# precisely so this does not make the adapter engage on unrelated clauses
# that merely mention protection/defense in some other sense (e.g. IP
# "defend," data "protection"). A document containing NONE of these and
# no "indemnif*" anchor is correctly left as NOT_APPLICABLE — this closes
# a documented vocabulary gap, it does not open a generic-word net.
_SYNONYM_OBLIGATION_HOLD_HARMLESS_RE = re.compile(
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\s+(?i:agrees\s+to\s+|shall\s+)?"
    r"(?i:hold)\s+(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\s+(?i:harmless\s+from\s+and\s+defend)\s+\2\s+(?i:against)"
)
_SYNONYM_OBLIGATION_PROTECT_REIMBURSE_RE = re.compile(
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\s+(?i:shall\s+)?"
    r"(?i:protect,?\s*defend,?\s*(?:and\s+)?reimburse)\s+(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\b"
)
_SYNONYM_OBLIGATION_MAKE_WHOLE_RE = re.compile(
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\s+(?i:undertakes\s+to\s+make|shall\s+make)\s+"
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\s+(?i:whole\s+for,?\s+and\s+to\s+assume\s+the\s+defense\s+of)\b"
)
_SYNONYM_OBLIGATION_BEAR_RESPONSIBILITY_RE = re.compile(
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\s+(?i:shall\s+bear\s+(?:full\s+)?responsibility\s+for\s+defending\s+and\s+satisfying\s+(?:such|any)\s+claims?\s+on)\s+"
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")(?:'s)?\s+(?i:behalf)\b"
)
_SYNONYM_OBLIGATION_RES = (
    _SYNONYM_OBLIGATION_HOLD_HARMLESS_RE,
    _SYNONYM_OBLIGATION_PROTECT_REIMBURSE_RE,
    _SYNONYM_OBLIGATION_MAKE_WHOLE_RE,
    _SYNONYM_OBLIGATION_BEAR_RESPONSIBILITY_RE,
)
# An explicit, document-wide statement that no indemnification obligation
# exists at all. Distinct from the anchor-negation guard below (which only
# filters an anchor match immediately preceded by "no " — i.e. the SAME
# mention being negated): this catches the common drafting pattern where
# the word "indemnification" is used once in passing (e.g. acknowledging
# the concept exists) and a SEPARATE sentence elsewhere unambiguously
# states no obligation was created. Only used when no directional
# obligation could otherwise be parsed — it never overrides a real,
# parsed obligation.
_EXPLICIT_NO_OBLIGATION_RE = re.compile(
    r"no\s+part(?:y|ies)\s+shall\s+have\s+any\s+indemnification\s+obligation"
    r"|no\s+indemnification\s+obligation\s+(?:is|shall\s+be|exists|is\s+created|shall\s+arise)"
    r"|shall\s+not\s+have\s+any\s+indemnification\s+obligation",
    re.I,
)
_OBLIGATION_RE = re.compile(
    # No blanket re.I: [A-Z] must stay case-SENSITIVE, or it silently
    # matches lowercase too (Python re applies IGNORECASE to character
    # classes, not just literals) and captures garbage role names like
    # "party"/"the" out of "Each party shall indemnify ... the other
    # party." The verb phrase alone is wrapped in a scoped (?i:...) so
    # "Shall"/"SHALL"/"shall" all still match.
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")(?:\s*\([^)]{0,65}\))?\s+(?i:shall|will|agrees to)\s+"
    r"(?i:defend,?\s*(?:and\s+)?indemnify|indemnify,?\s*(?:and\s+)?defend|indemnify)"
    r"(?i:,?\s*(?:and\s+)?(?:defend\s+and\s+)?hold\s+harmless)?\s+"
    r"(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r")\b"
)
_MUTUAL_RECIPROCAL_RE = re.compile(
    # Step 4A.5 Priority 4: an optional parenthetical defined-term aside
    # ("Each party (the 'Indemnifying Party') shall indemnify the other
    # party (the 'Indemnified Party') ...") is common shorthand-defining
    # drafting layered on top of an otherwise plain reciprocal opener —
    # it must not break recognition of the reciprocal structure itself.
    r"each\s+party(?:\s*\([^)]{0,60}\))?\s+shall\s+indemnify(?:,?\s*defend,?)?(?:\s+and\s+hold\s+harmless)?"
    r"\s+the\s+other(?:\s+party)?(?:\s*\([^)]{0,60}\))?"
    r"|the\s+parties\s+shall\s+(?:mutually\s+)?indemnify\s+each\s+other"
    r"|mutual\s+indemnification",
    re.I,
)

_THIRD_PARTY_ONLY_RE = re.compile(r"third[\s-]part(?:y|ies)\s+claims?", re.I)
_FIRST_PARTY_SIGNAL_RE = re.compile(
    r"first[\s-]part(?:y|ies)\s+claims?|whether\s+or\s+not\s+(?:asserted\s+by\s+)?a\s+third\s+party"
    r"|regardless\s+of\s+whether\s+.{0,30}third\s+party|direct\s+claims?\s+between\s+the\s+parties"
    r"|whether\s+direct\s+or\s+third[\s-]part(?:y|ies)"
    # [A-Z] deliberately kept case-sensitive within the overall re.I
    # compile via (?-i:...) — role names in contracts are capitalized
    # defined terms, and this is the same re.I-over-[A-Z] hazard already
    # fixed elsewhere in this file's _OBLIGATION_RE.
    r"|(?i:claims?\s+by\s+)(?-i:[A-Z][A-Za-z]{2,25})(?i:\s+against\s+)(?-i:[A-Z][A-Za-z]{2,25})",
    re.I,
)

_EXCLUSION_SIGNAL_RE = re.compile(
    r"shall not apply to|does not apply to|excluded from (?:this|the foregoing|such) indemn\w*"
    r"|except for (?:claims? )?(?:arising from |related to )?|other than|excluding|with the exception of",
    re.I,
)
_CAP_TRIGGER_RE = re.compile(r"shall not exceed|is capped at|shall be capped|limited to", re.I)

_DEFENSE_INDEMNIFYING_RE = re.compile(
    r"indemnifying\s+part(?:y|ies)?\s+shall\s+(?:have\s+the\s+right\s+to\s+)?control(?:\s+the)?\s+(?:the\s+)?defense"
    r"|shall\s+(?:have\s+the\s+right\s+to\s+)?(?:assume\s+and\s+)?control\s+(?:the\s+)?defense.{0,60}?at\s+its\s+(?:own\s+)?(?:sole\s+)?(?:cost|expense)",
    re.I,
)
_DEFENSE_INDEMNIFIED_RE = re.compile(
    r"indemnified\s+part(?:y|ies)?\s+(?:may|shall\s+have\s+the\s+right\s+to)\s+control(?:\s+the)?\s+(?:the\s+)?defense"
    r"|indemnified\s+part(?:y|ies)?\s+shall\s+control\s+its\s+own\s+defense",
    re.I,
)
_DEFENSE_SHARED_RE = re.compile(r"jointly\s+control|participate\s+in\s+(?:the\s+)?defense\s+with", re.I)
_NAMED_DEFENSE_CONTROL_RE = re.compile(
    r"(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))\s+(?i:shall\s+(?:have\s+the\s+right\s+to\s+)?control(?:ling)?|controlling|shall\s+assume\s+and\s+control)\s+(?:the\s+)?defense",
    re.I,
)

_NOTICE_RE = re.compile(r"prompt(?:ly)?\s+(?:written\s+)?notice|notify\s+.{0,20}\s+in\s+writing|written\s+notice\s+of\s+(?:any\s+)?claim", re.I)
_COOPERATION_RE = re.compile(r"reasonable\s+cooperation|shall\s+cooperate|cooperate\s+(?:fully\s+)?with", re.I)

_MONETARY_UNLIMITED_RE = re.compile(
    r"shall\s+not\s+be\s+(?:subject\s+to\s+)?(?:any\s+)?(?:cap|limit)(?:ation)?"
    r"|shall\s+be\s+uncapped|uncapped\s+(?:obligation|indemnification)"
    r"|no\s+(?:cap|limit)(?:ation)?\s+shall\s+apply",
    re.I,
)
# Step 4A.7 — same fix, same rationale, as liability_policy_engine.py's
# _BASIS_MODIFIER_FRAGMENT (Step 4A.6 A6-I-04, A6-I-25, A6-I-39, A6-I-40:
# "annual distribution fees"/"annual storage fees"/"annual management
# fees"/"annual referral fees" all previously vanished the same way here).
# This is a separate, independent regex from liability's — not shared code
# — so it needed the identical, bounded modifier-tolerance fix applied a
# second time, not a shared-constant refactor (the two adapters' monetary
# grammars are similar but not identical, e.g. indemnification has no
# purchase-price/contract-value/order-form-value basis words).
_MONETARY_MULTIPLIER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:the\s+)?(?:total\s+|aggregate\s+)?(?:annual\s+)?(?:\w+\s+){0,2}"
    r"(?:fees?|rent|royalt(?:y|ies)|premiums?|charges?)",
    re.I,
)
_MONETARY_FIXED_RE = re.compile(
    r"(?:shall\s+not\s+exceed|(?:is\s+)?capped\s+at|limited\s+to)\s*\$\s*([\d,]+(?:\.\d{2})?)",
    re.I,
)
_MONETARY_CROSS_REF_RE = re.compile(
    r"subject\s+to\s+the\s+(?:limitation\s+of\s+liability|liability\s+cap)\s+(?:set\s+forth\s+)?in\s+(Section\s+\d+(?:\.\d+)?)",
    re.I,
)
# Step 4A.3 — Failure Family 3-analogue for indemnification: a multiplier/
# fixed-amount figure that is explicitly attributed to the SEPARATE
# limitation-of-liability clause ("the general liability cap of 2 times
# the fees paid described in Section 9") must not be silently adopted as
# THIS obligation's own indemnification monetary term just because a
# number-shaped pattern happens to appear nearby — that number belongs to
# a different clause type entirely, even when _MONETARY_CROSS_REF_RE's
# narrower phrasing doesn't happen to match it.
_MONETARY_OTHER_CLAUSE_DISQUALIFIER_RE = re.compile(
    r"(?:general\s+)?liability\s+cap|limitation\s+of\s+liability",
    re.I,
)
_MONETARY_DISQUALIFIER_PROXIMITY = 40
_SECTION_REF_NEAR_RE = re.compile(r"Section\s+\d+(?:\.\d+)?", re.I)

# A restatement elsewhere in the document ("Vendor's indemnification
# obligations shall not exceed 2 times the fees paid") that doesn't use
# the "shall indemnify, defend, and hold harmless" phrasing _OBLIGATION_RE
# requires is invisible to the main obligation scan entirely — a second,
# conflicting monetary term for the SAME named role would silently never
# challenge the first-found value. This mirrors _PARTY_SPECIFIC_EXCEPTION_RE
# structurally but targets a monetary-only restatement rather than a
# proviso, and is fed into the SAME existing "different monetary terms"
# conflict check named obligations already go through — no new decision
# state, no new mechanism, just visibility for an obligation that was
# already there in the text.
_RESTATEMENT_MONETARY_RE = re.compile(
    r"(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))(?:'s)?\s+indemnification\s+obligations?\s+shall\s+not\s+exceed\s*"
    r"(?:(\d+(?:\.\d+)?)\s*(?:x|times)\s*(?:the\s+)?(?:total\s+|aggregate\s+)?(?:annual\s+)?fees?"
    r"|\$\s*([\d,]+(?:\.\d{2})?))",
    re.I,
)

# A mutual/reciprocal ("each party"/"the parties shall mutually indemnify")
# match claims symmetric treatment. This finds sub-clauses that attribute
# terms to one SPECIFIC named party within that same window ("Vendor's
# indemnification obligations...", "Customer's obligations under this
# Section...") so those per-party terms can be compared against each other
# — see _detect_reciprocal_asymmetry. [A-Z] is deliberately kept case-
# sensitive within the overall re.I compile via (?-i:...), the same
# re.I-over-[A-Z] hazard already fixed elsewhere in this file.
_ROLE_ATTRIBUTION_RE = re.compile(
    r"(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))(?:'s)?\s+(?i:indemnification\s+)?(?i:obligations?)\s+"
    r"(?i:under\s+this\s+(?:Section|Agreement)\s+)?",
    re.I,
)
_GENERIC_ROLE_WORDS = {
    "each", "the", "any", "such", "this", "that", "both", "either", "all",
    "party", "parties", "indemnifying", "indemnified", "other",
}
# Step 4A.3 — Failure Family 4: a reciprocal opener ("each party shall
# indemnify... up to a cap of 2x fees") can be immediately qualified by an
# "except that/provided that" proviso naming ONE specific party and giving
# it different terms ("except that Vendor's cap for IP infringement claims
# shall be 4x fees"). _ROLE_ATTRIBUTION_RE / detect_role_attributed_asymmetry
# only fires when TWO distinct named-role attributions appear in the same
# window to compare against each other — this proviso pattern names only
# ONE role, comparing against the window's own general (reciprocal) terms
# rather than a second named party, so it needs its own narrow detector.
_PARTY_SPECIFIC_EXCEPTION_RE = re.compile(
    r"(?:except|provided)\s+that\s+(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))(?:'s)?\s+"
    r"(?i:cap|liability|indemnification|obligations?|responsibility)\b"
    # Step 4A.5 Priority 4 (anti-false-safe): the same one-named-party
    # exception shape, but naming the party as the OBJECT of "claims
    # against ROLE" rather than as the possessive SUBJECT of "ROLE's
    # cap/obligations/..." — "except that claims against Underwriting
    # Agent arising from regulatory fines shall not be subject to this
    # cap".
    r"|(?:except|provided)\s+that\s+claims?\s+against\s+(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))\b",
    re.I,
)
_BROAD_BENEFICIARY_RE = re.compile(r"affiliates|officers|directors|employees|agents", re.I)

# Step 4A.7 — S4 remediation (Step 4A.6 A6-I-23): a reciprocal opener can
# state an EXPLICITLY named/quoted causation standard separately for two
# named parties ("...is subject to a causation standard of 'sole and
# proximate cause,' whereas [Other Party]'s...is subject to a broader
# 'contributing cause' standard"). This is deliberately narrow — it only
# recognizes a causation standard the drafter has explicitly singled out
# by name/quotation, not the ordinary causation-LINK phrase ("caused by",
# "arising from", "arising out of", "resulting from") that appears in
# nearly every indemnification sentence as connective tissue rather than
# as a distinguishing legal standard. Treating every such connective
# phrase as a comparable "standard" would risk manufacturing false
# escalations out of pure stylistic variation between two mentions of the
# SAME shared clause; requiring an explicit "causation standard of"/
# "subject to a ... standard" cue bounds the concept to drafting that is
# itself asserting a standard is being fixed, which is the only shape
# this fix is meant to catch. See
# benchmarks/step4a7_reciprocal_semantic_benchmark.py for the positive/
# negative boundary tests establishing this scope.
_CAUSATION_STANDARD_RE = re.compile(
    r"causation\s+standard\s+of\s+['‘]([^'’]{3,60})['’]"
    r"|subject\s+to\s+a\s+(?:broader\s+|narrower\s+|different\s+)?['‘]([^'’]{3,60})['’]\s+standard",
    re.I,
)


def _classify_causation_standard(local: str) -> Optional[str]:
    m = _CAUSATION_STANDARD_RE.search(local)
    if not m:
        return None
    phrase = (m.group(1) or m.group(2) or "").strip().lower()
    return phrase or None

# Step 4A.5 — Failure Family: a reciprocal opener can be qualified by
# PROCEDURAL (not monetary/trigger/scope) terms stated separately for two
# different named parties — a survival period, a notice precondition, a
# defense-control grant, or a temporal carve-out — none of which
# _snapshot_indemnity_attribution's monetary/trigger/scope/defense-control/
# beneficiary comparison tracks, and none of which _PARTY_SPECIFIC_
# EXCEPTION_RE's single-named-party-vs-general-terms shape catches when
# BOTH sides are named individually rather than one side being compared to
# an unnamed "general" baseline. The general invariant: when a clause
# names two or more DISTINCT parties (not the "each party"/"the other
# party" reciprocal placeholders) each attached to their OWN procedural
# grant/exclusion, the opener's claim of symmetry cannot be verified —
# regardless of which specific procedural concept (survival, notice,
# defense control, temporal scope) is used, since new procedural concepts
# will keep appearing and must not each need their own dedicated pattern.
_PROCEDURAL_ROLE_CUE_RE = re.compile(
    r"(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))(?:'s)?\s+(?:indemnification\s+)?obligations?\s+"
    r"(?:under\s+this\s+(?:Section|Agreement)\s+)?shall\s+"
    r"(?i:not\s+apply|survive|additionally\s+require)"
    r"|(?i:the\s+)?(?i:indemnification\s+)?obligations?\s+of\s+(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))\s+"
    r"(?:under\s+this\s+(?:Section|Agreement)\s+)?shall\s+(?i:not\s+apply|survive|additionally\s+require)"
    r"|(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))\s+shall\s+(?i:control\s+the\s+defense)",
    re.I,
)
_PROCEDURAL_EXCLUDED_ROLE_RE = re.compile(
    # Step 4A.7 — S4 remediation (Step 4A.6 A6-I-12): "(but not any
    # individual Franchisee)" was previously missed because the role name
    # is not the word immediately after "not" — an ordinary English
    # qualifier ("any", "any individual", "each particular", ...)
    # intervenes. Tolerating a small, unenumerated run of lowercase filler
    # words before the capitalized role name is a general grammatical
    # relaxation (any lowercase qualifier), not a specific-phrase patch.
    r"\(\s*but\s+not\s+(?:[a-z]+\s+){0,2}(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))\s*\)"
    r"|does\s+not\s+apply\s+to\s+claims?\s+(?:asserted\s+against|against)\s+(?-i:(" + _MULTIWORD_ROLE_NAME_FRAGMENT + r"))",
    re.I,
)
# Step 4A.7 — S4 remediation (Step 4A.6 A6-I-35 and, defense-in-depth,
# A6-I-18): a reciprocal ("each party"/mutual) opener can be qualified by
# an "except that"/"provided that" proviso that names ONE specific party
# in a shape none of the above cue regexes anticipate (e.g. "PROVIDED
# THAT if the claim arises from a defect in Products manufactured by
# [Party] specifically... the cap ... shall instead be..."). Rather than
# add a fifth dedicated cue pattern for this construction (and a sixth,
# seventh, ... for the next one), this generalizes: ANY named role
# (multi-word — see the >=2-word requirement below, which is what keeps
# this from matching ordinary capitalized document nouns like "Section"
# or "Products") appearing anywhere inside an except/provided-that clause
# is itself sufficient signal that the reciprocal opener's symmetry claim
# needs verification, regardless of which specific verb or condition
# follows the name. A genuinely symmetric proviso has no reason to name
# one specific party rather than restating "each party"/"either party" —
# see benchmarks/step4a7_reciprocal_semantic_benchmark.py for the
# positive (must NOT fire) controls that establish this boundary.
_EXCEPTION_PROVISO_MARKER_RE = re.compile(r"(?:except|provided)[\s,]+(?:however[\s,]+)?that\b", re.I)
# Step 4A.7 — widened during post-fix verification (Step 4A.6 A6-I-16:
# "except that Sublicensee's obligation does not extend to claims arising
# from patent infringement") to also match a SINGLE capitalized word, not
# just 2+-word names — single-word role names ("Sublicensee", "Vendor",
# "Landlord") are common and this exact reciprocal-scope-exclusion shape
# is one of the two Step 4A.5-disclosed residual weaknesses this step is
# specifically meant to close. The false-positive risk a 2+-word minimum
# was originally guarding against (matching "Section"/"Products"/
# "Agreement" as if they were role names) is instead handled by the
# explicit stopword list below, extended to cover the common single-word
# capitalized nouns that appear in this drafting style outside of role
# names — see benchmarks/step4a7_reciprocal_semantic_benchmark.py for the
# negative controls this must continue to pass.
_EXCEPTION_CLAUSE_ROLE_RE = re.compile(
    r"(?-i:[A-Z][A-Za-z]{1,25}(?:\s+[A-Z][A-Za-z]{1,25}){0,3})", re.I,
)
_EXCEPTION_CLAUSE_ROLE_STOPWORDS = {
    "products", "product", "provided", "except", "section", "agreement",
    "exhibit", "schedule", "article", "party", "parties",
    "notwithstanding", "this", "that", "such", "any", "all", "each",
    "either", "neither", "both", "the", "claims", "claim", "if", "unless",
}
# A proviso can use the exact "except that"/"provided that" trigger phrase
# while explicitly disclaiming that it changes anything substantive (a
# bystander factual aside, not a genuine differentiation) — e.g. "...a fact
# that does not affect either party's indemnification obligations under
# this Section." Skipping a clause that self-negates this way is a general
# linguistic check (any self-disclaiming phrase of this shape), not a
# one-off exclusion for a single known adversarial case; see A6-I-37 in
# benchmarks/step4a6_corpus_indemnification_direction.py, preserved as a
# permanent regression case in
# benchmarks/step4a7_reciprocal_semantic_benchmark.py.
_EXCEPTION_CLAUSE_SELF_NEGATION_RE = re.compile(
    r"does\s+not\s+affect|shall\s+not\s+affect|does\s+not\s+(?:modify|change|impact)"
    r"|shall\s+not\s+(?:modify|change|impact)|no\s+effect\s+on",
    re.I,
)


def _find_exception_clause_named_roles(window: str, allow_multi_role_clauses: bool = False) -> List[str]:
    """Only ever returns roles from a clause naming EXACTLY ONE distinct
    party (the A6-I-12/18/35/I-16 shape: one named party singled out
    against an implicit "both/everyone else" baseline). A clause naming
    TWO OR MORE distinct parties (e.g. "provided that Licensor's
    obligations...2x...and Licensee's obligations...2x...") is a
    comparison _ROLE_ATTRIBUTION_RE/detect_role_attributed_asymmetry
    already performs correctly (including confirming IDENTICAL stated
    terms are not a differentiation) — flagging it here too, without that
    value comparison, would produce a false positive whenever two named
    roles happen to state the same terms in the same proviso. See
    benchmarks/indemnification_asymmetry_benchmark.py asym-19 (a
    permanent regression case for exactly this).

    allow_multi_role_clauses=True (Step 4A.7.1) relaxes that restriction
    for the ONE caller (the compound cross-mechanism check) that already
    independently confirmed there is only a single _ROLE_ATTRIBUTION_RE
    attribution in the whole window — in that specific context a 2-role
    exception clause can't be the asym-19 shape (which requires 2
    attribution matches to even reach the comparison), so returning both
    roles found is safe there without reintroducing that false positive."""
    roles: List[str] = []
    seen_lower = set()
    for marker in _EXCEPTION_PROVISO_MARKER_RE.finditer(window):
        hi = min(len(window), marker.end() + 300)
        boundary = re.search(r"\.\s|\.$", window[marker.end():hi])
        if boundary:
            hi = marker.end() + boundary.end()
        clause = window[marker.end():hi]
        if _EXCEPTION_CLAUSE_SELF_NEGATION_RE.search(clause):
            continue
        _scan_exception_sub_clause(clause, roles, seen_lower, allow_multi_role_clauses)
    return roles


def _scan_exception_sub_clause(clause: str, roles: List[str], seen_lower: set, allow_multi_role_clauses: bool = False) -> None:
        clause_roles: List[str] = []
        clause_seen_lower = set()
        last_end = None
        for m in _EXCEPTION_CLAUSE_ROLE_RE.finditer(clause):
            # A hyphenated/digit-led connector word inside an entity name
            # ("Zenith 3D-Printing Manufacturing Corp") breaks this regex
            # into two adjacent matches ("Zenith", "Printing Manufacturing
            # Corp") rather than one — treat two matches separated by only
            # a short gap as fragments of the SAME name, not two distinct
            # parties, so this doesn't get misread as a Licensor/Licensee-
            # style two-party clause. See benchmarks/
            # step4a7_reciprocal_semantic_benchmark.py S4B-EXC-* cases.
            if last_end is not None and m.start() - last_end <= 15:
                last_end = m.end()
                continue
            last_end = m.end()
            role = trim_role_name(m.group(0))
            first_word = role.split()[0].lower() if role else ""
            # A short (<=3-char) standalone ALL-CAPS token ("IP", "SLA",
            # "API") is a legal/technical abbreviation, not a role name —
            # role names in this drafting style are always longer,
            # title-cased words. General shape check, not an enumerated
            # abbreviation list.
            is_short_abbreviation = len(role) <= 3 and role.isupper()
            if (
                not role
                or role.lower() in _GENERIC_ROLE_WORDS
                or first_word in _EXCEPTION_CLAUSE_ROLE_STOPWORDS
                or role.lower() in clause_seen_lower
                or is_short_abbreviation
            ):
                continue
            clause_seen_lower.add(role.lower())
            clause_roles.append(role)
        if len(clause_roles) != 1 and not allow_multi_role_clauses:
            return
        for role in clause_roles:
            if role.lower() in seen_lower:
                continue
            seen_lower.add(role.lower())
            roles.append(role)


_SURVIVAL_PERIOD_RE = re.compile(r"(?:for\s+)?(\w+)\s*\(?\d*\)?\s+(years?|months?)\b", re.I)
_SURVIVAL_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _survival_period_value(local: str) -> Optional[Tuple[float, str]]:
    m = _SURVIVAL_PERIOD_RE.search(local)
    if not m:
        return None
    word = m.group(1).lower()
    n = _SURVIVAL_WORD_NUMBERS.get(word)
    if n is None and word.isdigit():
        n = float(word)
    if n is None:
        return None
    return (float(n), m.group(2).lower().rstrip("s"))


def _find_procedural_differentiation_roles(window: str) -> List[str]:
    roles: List[str] = []
    seen_lower = set()

    def _add(role: Optional[str]) -> None:
        if not role:
            return
        role = trim_role_name(role)
        if role.lower() in _GENERIC_ROLE_WORDS or role.lower() in seen_lower:
            return
        seen_lower.add(role.lower())
        roles.append(role)

    survival_matches: List[Tuple[str, str]] = []  # (role, local text after match)
    for m in _PROCEDURAL_ROLE_CUE_RE.finditer(window):
        role = m.group(1) or m.group(2) or m.group(3)
        if role is None:
            continue
        if "survive" in m.group(0).lower():
            local = window[m.end():min(len(window), m.end() + 40)]
            survival_matches.append((trim_role_name(role), local))
        else:
            _add(role)
    for m in _PROCEDURAL_EXCLUDED_ROLE_RE.finditer(window):
        _add(m.group(1) or m.group(2))

    # Survival-period matches only count as differentiation if two
    # DIFFERENT roles are named AND their extracted period values
    # actually differ — two named parties both getting the identical
    # period restated per-role is not asymmetry, and must not become one
    # (avoids a new source of false escalation from purely stylistic
    # per-party restatement of the same term).
    if len(survival_matches) >= 2:
        values = [(_survival_period_value(local), role) for role, local in survival_matches]
        distinct_values = {v for v, _ in values if v is not None}
        if len(distinct_values) > 1:
            for role, _ in survival_matches:
                _add(role)

    return roles

_PROVISION_WINDOW_CHARS = 2000
_LOCAL_WINDOW_CHARS = 160
_ROLE_ATTRIBUTION_LOCAL_CHARS = 220


# ---------------------------------------------------------------------------
# Structured facts
# ---------------------------------------------------------------------------

@dataclass
class MonetaryTreatment:
    kind: str  # "multiplier" | "fixed" | "unlimited" | "cross_reference" | "not_stated"
    multiplier: Optional[float] = None
    fixed_amount: Optional[float] = None
    cross_reference_label: Optional[str] = None
    raw_excerpt: str = ""

    def summary(self) -> str:
        if self.kind == "unlimited":
            return "Uncapped"
        if self.kind == "multiplier":
            return f"{self.multiplier:g}x annual fees"
        if self.kind == "fixed":
            return f"${self.fixed_amount:,.2f} fixed"
        if self.kind == "cross_reference":
            return f"per {self.cross_reference_label}"
        return "unspecified"


@dataclass
class TriggerTreatment:
    trigger: str
    treatment: str  # "covered" | "excluded" | "not_addressed" | "unresolved"
    raw_excerpt: str = ""
    established: bool = True


@dataclass
class IndemnityObligation:
    """One directional promise: indemnifying_role indemnifies indemnified_role."""
    indemnifying_role: str
    indemnifying_side: Optional[str]
    indemnified_role: str
    indemnified_side: Optional[str]
    trigger_treatments: Dict[str, TriggerTreatment]
    scope: str  # "third_party_only" | "includes_first_party" | "not_addressed" | "unresolved"
    defense_control: str  # "indemnifying_party" | "indemnified_party" | "shared" | "not_addressed" | "unresolved"
    notice_required: Optional[bool]
    cooperation_required: Optional[bool]
    monetary: MonetaryTreatment
    raw_excerpt: str
    start_index: int
    end_index: int
    section_label: Optional[str]
    # Step 4A: set whenever resolve_role_side() found the document's own
    # definition of indemnifying_role/indemnified_role conflicts with the
    # generic buy/sell vocabulary — the corresponding *_side is None
    # whenever its reason is present here. Kept separate from an
    # unrecognized-role-name None so _resolve_obligations_for_side can
    # surface a specific, useful reason rather than generic "unrecognized
    # party name(s)" text.
    role_side_conflict_reasons: List[str] = field(default_factory=list)
    is_mutual_reciprocal: bool = False
    # Step 4A.7: populated for EVERY obligation (reciprocal or named) — see
    # _detect_reciprocal_asymmetry. A non-empty list means the shared
    # window this obligation was extracted from contains a signal that a
    # claimed or apparent symmetry between two directions (an "each
    # party"/"mutual" opener, or two strictly-named obligations pointing
    # at each other) cannot be trusted: materially different terms stated
    # per named party, a named causation standard that differs by party,
    # or an except/provided-that proviso singling out one named party.
    asymmetry_reasons: List[str] = field(default_factory=list)

    def label(self) -> str:
        prefix = f"Section {self.section_label} — " if self.section_label else ""
        return f"{prefix}{self.indemnifying_role} indemnifies {self.indemnified_role}"


@dataclass
class IndemnificationFacts:
    clause_found: bool
    obligations: List[IndemnityObligation] = field(default_factory=list)


class IndemnificationPolicyRuleLike(Protocol):
    contract_side: str
    escalation_approval_authority: Optional[str]
    fallback_text: Optional[str]
    required_protection_triggers_json: Optional[List[str]]
    prohibited_exposure_triggers_json: Optional[List[str]]
    require_exposure_third_party_only: bool
    require_defense_control_for_exposure: bool
    require_notice_and_cooperation_for_exposure: bool
    prohibit_uncapped_exposure: bool
    exposure_preferred_multiplier: Optional[float]
    exposure_acceptable_max_multiplier: Optional[float]
    exposure_negotiate_max_multiplier: Optional[float]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

# _excerpt / _section_label_before are imported from policy_engine_core
# (promoted — see policy_engine_core.excerpt / section_label_before).

def _classify_triggers(window: str) -> Dict[str, TriggerTreatment]:
    """Mirrors liability_policy_engine's forward-coverage-span exclusion
    model (same class of bug it was built to avoid: an exclusion signal
    for one trigger bleeding onto an unrelated nearby trigger). Deliberately
    reimplemented here rather than imported — the category *vocabulary* is
    clause-specific (indemnification triggers are conduct that CREATES an
    obligation; LoL categories are carve-outs FROM a cap — opposite
    polarity, not the same concept wearing a different name)."""
    positions = []
    for trig, kw_re in _TRIGGER_KEYWORD_RE.items():
        for m in kw_re.finditer(window):
            positions.append((m.start(), trig))

    covered_by_exclusion: Dict[str, str] = {}
    for sig in _EXCLUSION_SIGNAL_RE.finditer(window):
        span_end = min(len(window), sig.end() + 100)
        coverage_text = window[sig.end():span_end]
        boundary = re.search(r"\.\s|;", coverage_text)
        boundary_pos = boundary.start() if boundary else None
        for and_m in re.finditer(r"\band\b", coverage_text, re.I):
            if _CAP_TRIGGER_RE.search(coverage_text[and_m.end():and_m.end() + 60]):
                if boundary_pos is None or and_m.start() < boundary_pos:
                    boundary_pos = and_m.start()
                break
        if boundary_pos is not None:
            coverage_text = coverage_text[:boundary_pos]
        coverage_end = sig.end() + len(coverage_text)
        for pos, trig in positions:
            if sig.end() <= pos < coverage_end and trig not in covered_by_exclusion:
                covered_by_exclusion[trig] = _excerpt(window, sig.start(), coverage_end)

    treatments = {}
    for trig, kw_re in _TRIGGER_KEYWORD_RE.items():
        occurrences = list(kw_re.finditer(window))
        if not occurrences:
            treatments[trig] = TriggerTreatment(trigger=trig, treatment="not_addressed")
            continue
        m = occurrences[0]
        excerpt = _excerpt(window, m.start(), m.end())
        if trig in covered_by_exclusion:
            treatments[trig] = TriggerTreatment(trigger=trig, treatment="excluded", raw_excerpt=excerpt)
            continue
        local_start = max(0, m.start() - _LOCAL_WINDOW_CHARS)
        local_end = min(len(window), m.end() + _LOCAL_WINDOW_CHARS)
        local = window[local_start:local_end]
        if re.search(r"notwithstanding|provided,?\s+however|except as otherwise", local, re.I):
            treatments[trig] = TriggerTreatment(trigger=trig, treatment="unresolved", raw_excerpt=excerpt, established=False)
            continue
        treatments[trig] = TriggerTreatment(trigger=trig, treatment="covered", raw_excerpt=excerpt)
    return treatments


def _classify_scope(window: str) -> str:
    has_third = bool(_THIRD_PARTY_ONLY_RE.search(window))
    has_first = bool(_FIRST_PARTY_SIGNAL_RE.search(window))
    if has_first:
        return "includes_first_party"
    if has_third:
        return "third_party_only"
    return "not_addressed"


def _classify_defense_control(
    window: str, indemnifying_role: Optional[str] = None, indemnified_role: Optional[str] = None,
) -> str:
    has_indemnifying = bool(_DEFENSE_INDEMNIFYING_RE.search(window))
    has_indemnified = bool(_DEFENSE_INDEMNIFIED_RE.search(window))
    has_shared = bool(_DEFENSE_SHARED_RE.search(window))
    # Step 4A.5 Priority 4 (anti-false-safe): the same defense-control
    # concept stated using the ACTUAL NAMED party ("with Ceding Reinsurer
    # controlling the defense of any such claim") rather than the generic
    # "the indemnifying party"/"the indemnified party" shorthand the
    # patterns above require. Only checked when the caller supplies the
    # obligation's own role names, and only credited to whichever named
    # role the match is FOR — never guessed when the role names aren't
    # known at this call site.
    named_defense = _NAMED_DEFENSE_CONTROL_RE.search(window)
    if named_defense:
        named_role = trim_role_name(named_defense.group(1)).lower()
        if indemnifying_role is not None and named_role == indemnifying_role.lower():
            has_indemnifying = True
        elif indemnified_role is not None and named_role == indemnified_role.lower():
            has_indemnified = True
    signals = sum([has_indemnifying, has_indemnified, has_shared])
    if signals > 1:
        return "shared"
    if has_shared:
        return "shared"
    if has_indemnifying:
        return "indemnifying_party"
    if has_indemnified:
        return "indemnified_party"
    return "not_addressed"


def _classify_monetary(window: str, obligation_start: int) -> MonetaryTreatment:
    xref = _MONETARY_CROSS_REF_RE.search(window)
    unlimited = _MONETARY_UNLIMITED_RE.search(window)
    mult = _MONETARY_MULTIPLIER_RE.search(window)
    fixed = _MONETARY_FIXED_RE.search(window)

    def _other_clause_label(m: "re.Match[str]") -> Optional[str]:
        lo = max(0, m.start() - _MONETARY_DISQUALIFIER_PROXIMITY)
        if not _MONETARY_OTHER_CLAUSE_DISQUALIFIER_RE.search(window[lo:m.start()]):
            return None
        sec = _SECTION_REF_NEAR_RE.search(window[m.start():m.end() + 60])
        return sec.group(0) if sec else "a different clause elsewhere in the document"

    mult_disq_label = _other_clause_label(mult) if mult is not None else None
    fixed_disq_label = _other_clause_label(fixed) if fixed is not None else None
    if mult_disq_label is not None:
        mult = None
    if fixed_disq_label is not None:
        fixed = None

    candidates = [c for c in (xref, unlimited, mult, fixed) if c is not None]
    if not candidates:
        # A figure that looked like this obligation's own monetary term but
        # was disqualified as belonging to a different clause (e.g. "subject
        # to the aggregate liability cap of 2x... set forth in Section 9")
        # is not the same fact as no monetary term being stated at all —
        # it's a delegation to another clause, same as an explicit
        # cross-reference, and must not be silently treated as "not
        # addressed" (which downstream checks do not escalate on).
        disq_label = mult_disq_label or fixed_disq_label
        if disq_label is not None:
            return MonetaryTreatment(kind="cross_reference", cross_reference_label=disq_label, raw_excerpt="")
        return MonetaryTreatment(kind="not_stated")
    # Earliest mention in the obligation's own window governs — consistent
    # with "closest stated position wins" used throughout the LoL adapter.
    first = min(candidates, key=lambda m: m.start())
    if first is xref:
        return MonetaryTreatment(kind="cross_reference", cross_reference_label=xref.group(1), raw_excerpt=_excerpt(window, xref.start(), xref.end()))
    if first is unlimited:
        return MonetaryTreatment(kind="unlimited", raw_excerpt=_excerpt(window, unlimited.start(), unlimited.end()))
    if first is mult:
        return MonetaryTreatment(kind="multiplier", multiplier=float(mult.group(1)), raw_excerpt=_excerpt(window, mult.start(), mult.end()))
    return MonetaryTreatment(kind="fixed", fixed_amount=float(fixed.group(1).replace(",", "")), raw_excerpt=_excerpt(window, fixed.start(), fixed.end()))


def _monetary_key(m: MonetaryTreatment) -> Tuple[str, Optional[float], Optional[float]]:
    return (m.kind, m.multiplier, m.fixed_amount)


def _trigger_treatment_key(trigger_treatments: Dict[str, TriggerTreatment]) -> FrozenSet[Tuple[str, str]]:
    """Comparable summary of which trigger categories are covered/excluded
    — ignores raw_excerpt/established (provenance, not substance) so two
    directions stating the SAME coverage in different words still compare
    equal, while two directions covering DIFFERENT categories (or
    differing on covered vs. excluded for the same category) do not."""
    return frozenset((trig, tt.treatment) for trig, tt in trigger_treatments.items())


def _snapshot_indemnity_attribution(local: str) -> Dict[str, Any]:
    return {
        "monetary": _classify_monetary(local, 0),
        "scope": _classify_scope(local),
        "defense_control": _classify_defense_control(local),
        "triggers": frozenset(
            trig for trig, kw_re in _TRIGGER_KEYWORD_RE.items() if kw_re.search(local)
        ),
        "broad_beneficiary": bool(_BROAD_BENEFICIARY_RE.search(local)),
        "causation_standard": _classify_causation_standard(local),
    }


def _compare_indemnity_attribution(base_role: str, base: Dict[str, Any], role: str, snap: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if (
        base["monetary"].kind != "not_stated" and snap["monetary"].kind != "not_stated"
        and _monetary_key(base["monetary"]) != _monetary_key(snap["monetary"])
    ):
        reasons.append(
            f"{base_role} and {role} state different monetary terms "
            f"({base['monetary'].summary()} vs {snap['monetary'].summary()})"
        )
    if base["triggers"] and snap["triggers"] and base["triggers"] != snap["triggers"]:
        reasons.append(f"{base_role} and {role} cover different trigger sets")
    if (
        base["scope"] not in ("not_addressed", "unresolved")
        and snap["scope"] not in ("not_addressed", "unresolved")
        and base["scope"] != snap["scope"]
    ):
        reasons.append(f"{base_role} and {role} state different claim scope")
    if (
        base["defense_control"] not in ("not_addressed", "unresolved")
        and snap["defense_control"] not in ("not_addressed", "unresolved")
        and base["defense_control"] != snap["defense_control"]
    ):
        reasons.append(f"{base_role} and {role} state different defense-control terms")
    if base["broad_beneficiary"] != snap["broad_beneficiary"]:
        reasons.append(f"{base_role} and {role} name different indemnified-party groups")
    # Step 4A.7 — S4 remediation (causation-standard differentiation, e.g.
    # "sole and proximate cause" vs. "contributing cause" stated separately
    # per named role). Deliberately narrow: only fires when BOTH roles
    # state an EXPLICITLY named/quoted causation standard (see
    # _CAUSATION_STANDARD_RE) that differs — ordinary stylistic causation-
    # link variation ("caused by" vs. "arising from") used in a single
    # shared reciprocal clause never reaches this comparison at all (there
    # is only one snapshot, not two, in that case) and is not itself
    # treated as a differentiation signal, to avoid manufacturing false
    # escalations out of ordinary drafting synonymy. See
    # benchmarks/step4a7_reciprocal_semantic_benchmark.py for the positive/
    # negative boundary tests.
    if base["causation_standard"] and snap["causation_standard"] and base["causation_standard"] != snap["causation_standard"]:
        reasons.append(
            f"{base_role} and {role} are subject to different named causation standards "
            f"({base['causation_standard']!r} vs {snap['causation_standard']!r})"
        )
    return reasons


def _detect_reciprocal_asymmetry(window: str) -> List[str]:
    """A mutual/reciprocal match ("each party shall indemnify... the other
    party" / "the parties shall mutually indemnify each other") claims
    symmetric treatment. Real drafting sometimes layers differentiated,
    per-party-NAMED terms on top of that symmetric opener — a proviso that
    states different monetary caps, different covered triggers, different
    claim scope, different defense-control terms, or a different
    indemnified-party group for one named role than another. A genuinely
    reciprocal clause never does this; when it happens, the opener's
    symmetry claim cannot be trusted and must not be treated as
    established fact.

    The scan/window/compare mechanics are shared (see policy_engine_core.
    detect_role_attributed_asymmetry) — only the attribution regex, the
    generic-role stoplist, and what a "snapshot" contains/how two
    snapshots disagree stay adapter-owned, via
    _snapshot_indemnity_attribution / _compare_indemnity_attribution.
    """
    # Step 4A.7.1 (Step 4A.6 A6-I-43): "the parties acknowledge ongoing
    # discussions regarding a mutual indemnification framework but have
    # not yet reached agreement on its terms" mentions "mutual
    # indemnification" descriptively — discussing whether to have one —
    # which incorrectly satisfies _MUTUAL_RECIPROCAL_RE's match and
    # creates a phantom "Each Party indemnifies the Other Party"
    # obligation with no actual terms. This self-flagged-not-yet-agreed
    # signal must block that obligation from being trusted as
    # established, exactly like the liability/payment-terms counterparts
    # of the same phrase family.
    if re.search(r"have\s+not\s+yet\s+reached\s+agreement\b|not\s+yet\s+reached\s+agreement\b", window, re.I):
        return ["the document explicitly states the parties have not yet reached agreement on this clause's terms"]

    reasons = detect_role_attributed_asymmetry(
        window, _ROLE_ATTRIBUTION_RE, _GENERIC_ROLE_WORDS,
        _snapshot_indemnity_attribution, _compare_indemnity_attribution,
        max_chars=_ROLE_ATTRIBUTION_LOCAL_CHARS,
    )
    if reasons:
        return reasons

    # One-named-party-vs-general-terms check (see _PARTY_SPECIFIC_EXCEPTION_RE).
    em = _PARTY_SPECIFIC_EXCEPTION_RE.search(window)
    em_role = em.group(1) or em.group(2) if em else None
    if em and trim_role_name(em_role).lower() not in _GENERIC_ROLE_WORDS:
        role = trim_role_name(em_role)
        general_snapshot = _snapshot_indemnity_attribution(window[:em.start()])
        hi = min(len(window), em.end() + _ROLE_ATTRIBUTION_LOCAL_CHARS)
        boundary = re.search(r"\.\s|\.$", window[em.end():hi])
        if boundary:
            hi = em.end() + boundary.end()
        exception_snapshot = _snapshot_indemnity_attribution(window[em.end():hi])
        reasons = _compare_indemnity_attribution("the general terms", general_snapshot, role, exception_snapshot)
    if reasons:
        return reasons

    # Step 4A.5 — differentiated PROCEDURAL terms (survival period, notice
    # precondition, defense control, temporal carve-out) named separately
    # for two or more distinct parties; see _find_procedural_differentiation_roles.
    procedural_roles = _find_procedural_differentiation_roles(window)
    if len(procedural_roles) >= 2:
        reasons.append(
            f"the clause states differentiated procedural terms (survival period, notice precondition, "
            f"defense control, or a temporal carve-out) separately for {' and '.join(procedural_roles)} "
            f"rather than one shared symmetric term"
        )
    elif len(procedural_roles) == 1:
        # A single named party with a "(but not X)"-style exclusive grant,
        # or a "shall not apply"/"shall additionally require" clause that
        # names only itself with no counterpart named — still asymmetric:
        # a grant or carve-out attached to exactly one named party (not
        # "each party") is inherently not the reciprocal opener's claimed
        # symmetric treatment.
        reasons.append(
            f"the clause attaches a party-specific procedural grant or carve-out to {procedural_roles[0]} "
            f"alone, rather than applying it to both parties symmetrically"
        )
    if reasons:
        return reasons

    # Step 4A.7 — general except/provided-that named-role check (see
    # _find_exception_clause_named_roles above for the rationale).
    exception_roles = _find_exception_clause_named_roles(window)
    if exception_roles:
        reasons.append(
            "the clause contains an 'except that'/'provided that' proviso naming "
            + " and ".join(exception_roles) +
            " specifically, rather than stating the condition for both parties uniformly — "
            "the reciprocal opener's symmetry claim cannot be verified from this proviso"
        )
        return reasons

    # Step 4A.7.1 — compound differentiation (Step 4A.7's own stress
    # benchmark S4B-COMP-05/07): a single sentence can differentiate TWO
    # DIFFERENT named parties through TWO DIFFERENT mechanisms at once —
    # one via an except/provided-that proviso, the other via a "[Role]'s
    # ... obligation is subject to a '...' standard" attribution. Neither
    # mechanism alone has enough signal (the exception-clause scan defers
    # when it sees 2 roles in one clause, per asym-19's fix; the
    # attribution comparator needs 2 comparable attributions, and only
    # gets 1). If _ROLE_ATTRIBUTION_RE finds exactly ONE attribution and
    # a DIFFERENT role is independently named in an exception clause
    # (checked without the single-role restriction here, since the
    # cross-mechanism combination itself is the signal), that is still
    # evidence two parties are each carrying their own, independently
    # stated differentiation — even though neither one alone could be
    # compared against a matching attribution for the other.
    attribution_matches = [
        m for m in _ROLE_ATTRIBUTION_RE.finditer(window)
        if trim_role_name(m.group(1)).lower() not in _GENERIC_ROLE_WORDS
    ]
    if len(attribution_matches) == 1:
        attributed_role = trim_role_name(attribution_matches[0].group(1)).lower()
        other_named_roles = _find_exception_clause_named_roles(window, allow_multi_role_clauses=True)
        distinct_other = [r for r in other_named_roles if r.lower() != attributed_role]
        if distinct_other:
            reasons.append(
                f"the clause states a '{attribution_matches[0].group(1)}'s...obligation is subject to a "
                f"named standard' differentiation for one party, AND a separate except/provided-that "
                f"proviso naming {distinct_other[0]} — two independently differentiated parties in one "
                f"sentence, neither comparable to a matching statement for the other"
            )
    return reasons


def _extract_obligation_window(text: str, start: int, end: int) -> str:
    return text[start:min(len(text), start + _PROVISION_WINDOW_CHARS)]


def extract_indemnification_facts(text: str) -> Optional[IndemnificationFacts]:
    """Finds every directional indemnification obligation stated in the
    full document. Unlike Limitation of Liability's single controlling
    provision, obligations are NOT reconciled into one — a reciprocal
    clause legitimately states two simultaneously valid obligations, one
    per direction, and both are evaluated independently."""
    # "No indemnification provision is included..." mentions the word but
    # explicitly negates it — a bare substring search would treat that
    # sentence as evidence a clause exists. Require at least one anchor
    # occurrence NOT immediately preceded by a negation cue.
    anchors = [m for m in _ANCHOR_RE.finditer(text) if not re.search(r"\bno\s+$", text[max(0, m.start() - 15):m.start()], re.I)]
    # Step 4A.5 Priority 3: a document that never uses "indemnif*" at all
    # can still state the same concept using one of the closed synonym
    # idioms above — check those before giving up on document engagement.
    if not anchors and not any(r.search(text) for r in _SYNONYM_OBLIGATION_RES):
        return None

    obligations: List[IndemnityObligation] = []
    seen_spans: List[Tuple[int, int]] = []
    # Step 4A.5: a genuinely reciprocal-but-NAMED pattern ("Landlord
    # shall indemnify Tenant, and Tenant shall indemnify Landlord...")
    # states two DIFFERENT obligations only ~30 chars apart — close
    # enough that the proximity-only dedup below would wrongly discard
    # the second one as a duplicate match of the first. Only treat a
    # close match as a duplicate when it names the SAME role pair (in
    # either direction) as an already-seen obligation; a different pair
    # that close together is a real second obligation, not a re-match.
    seen_role_pairs: List[Tuple[int, Tuple[str, str]]] = []

    for m in _OBLIGATION_RE.finditer(text):
        indemnifying_role, indemnified_role = trim_role_name(m.group(1)), trim_role_name(m.group(2))
        if indemnifying_role.lower() == indemnified_role.lower():
            continue  # regex false-positive guard, e.g. matched the same word twice
        # Ordered (not unordered) pair: "Landlord indemnifies Tenant" and
        # "Tenant indemnifies Landlord" are different obligations despite
        # sharing the same two parties — only an EXACT repeat of the same
        # direction is a duplicate match.
        pair = (indemnifying_role.lower(), indemnified_role.lower())
        if any(abs(m.start() - s) < 50 and p == pair for s, p in seen_role_pairs):
            continue
        window = _extract_obligation_window(text, m.start(), min(len(text), m.start() + _PROVISION_WINDOW_CHARS))
        indemnifying_side, indemnifying_conflict = resolve_role_side(indemnifying_role, text)
        indemnified_side, indemnified_conflict = resolve_role_side(indemnified_role, text)
        conflict_reasons = [r for r in (indemnifying_conflict, indemnified_conflict) if r]
        obligations.append(IndemnityObligation(
            indemnifying_role=indemnifying_role, indemnifying_side=indemnifying_side,
            indemnified_role=indemnified_role, indemnified_side=indemnified_side,
            trigger_treatments=_classify_triggers(window),
            scope=_classify_scope(window),
            defense_control=_classify_defense_control(window, indemnifying_role, indemnified_role),
            notice_required=True if _NOTICE_RE.search(window) else None,
            cooperation_required=True if _COOPERATION_RE.search(window) else None,
            monetary=_classify_monetary(window, m.start()),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
            role_side_conflict_reasons=conflict_reasons,
            # Step 4A.7 — S4 remediation: previously only populated for
            # is_mutual_reciprocal=True obligations. A strictly-named
            # two-party pair ("Timberline shall indemnify Member, and
            # Member shall indemnify Timberline...") can be qualified by
            # the exact same kind of per-party differentiation (a named
            # causation standard, an except/provided-that proviso naming
            # one party) that a reciprocal "each party" opener can — the
            # window-scanning checks in _detect_reciprocal_asymmetry don't
            # actually depend on "each party" phrasing, so reusing them
            # here (rather than duplicating the logic) closes that gap.
            # See _resolve_obligations_for_side's same_pair check.
            asymmetry_reasons=_detect_reciprocal_asymmetry(window),
        ))
        seen_spans.append((m.start(), m.end()))
        seen_role_pairs.append((m.start(), pair))

    # Step 4A.5 Priority 3: same extraction shape as the main loop above,
    # driven by the closed synonym-idiom patterns instead of _OBLIGATION_RE.
    # A synonym match at a span already covered by a canonical
    # _OBLIGATION_RE match is skipped as the same obligation restated, not
    # a second one.
    for synonym_re in _SYNONYM_OBLIGATION_RES:
        for m in synonym_re.finditer(text):
            if any(lo - 30 <= m.start() <= hi + 30 for lo, hi in seen_spans):
                continue
            indemnifying_role, indemnified_role = trim_role_name(m.group(1)), trim_role_name(m.group(2))
            if indemnifying_role.lower() == indemnified_role.lower():
                continue
            pair = (indemnifying_role.lower(), indemnified_role.lower())
            if any(abs(m.start() - s) < 50 and p == pair for s, p in seen_role_pairs):
                continue
            window = _extract_obligation_window(text, m.start(), min(len(text), m.start() + _PROVISION_WINDOW_CHARS))
            indemnifying_side, indemnifying_conflict = resolve_role_side(indemnifying_role, text)
            indemnified_side, indemnified_conflict = resolve_role_side(indemnified_role, text)
            conflict_reasons = [r for r in (indemnifying_conflict, indemnified_conflict) if r]
            obligations.append(IndemnityObligation(
                indemnifying_role=indemnifying_role, indemnifying_side=indemnifying_side,
                indemnified_role=indemnified_role, indemnified_side=indemnified_side,
                trigger_treatments=_classify_triggers(window),
                scope=_classify_scope(window),
                defense_control=_classify_defense_control(window, indemnifying_role, indemnified_role),
                notice_required=True if _NOTICE_RE.search(window) else None,
                cooperation_required=True if _COOPERATION_RE.search(window) else None,
                monetary=_classify_monetary(window, m.start()),
                raw_excerpt=_excerpt(text, m.start(), m.end()),
                start_index=m.start(), end_index=m.end(),
                section_label=_section_label_before(text, m.start()),
                role_side_conflict_reasons=conflict_reasons,
                asymmetry_reasons=_detect_reciprocal_asymmetry(window),  # Step 4A.7 — see main loop above
            ))
            seen_spans.append((m.start(), m.end()))
            seen_role_pairs.append((m.start(), pair))

    # See _RESTATEMENT_MONETARY_RE: a same-role restatement using
    # different phrasing than _OBLIGATION_RE requires. Only fires when it
    # names a role already seen as a named obligation's indemnifying_role
    # (never fabricates a new obligation direction from nothing) and
    # states a genuinely different value — feeds into the existing
    # multi-obligation conflict check via a synthetic same-direction
    # obligation clone.
    base_by_role = {o.indemnifying_role.lower(): o for o in obligations}
    for rm in _RESTATEMENT_MONETARY_RE.finditer(text):
        if any(abs(rm.start() - s) < 50 for s, _ in seen_spans):
            continue
        role = trim_role_name(rm.group(1))
        base = base_by_role.get(role.lower())
        if base is None:
            continue
        if rm.group(2):
            restated = MonetaryTreatment(kind="multiplier", multiplier=float(rm.group(2)), raw_excerpt=_excerpt(text, rm.start(), rm.end()))
        else:
            restated = MonetaryTreatment(kind="fixed", fixed_amount=float(rm.group(3).replace(",", "")), raw_excerpt=_excerpt(text, rm.start(), rm.end()))
        if _monetary_key(restated) == _monetary_key(base.monetary):
            continue  # same value restated — not a conflict, nothing to surface
        obligations.append(IndemnityObligation(
            indemnifying_role=base.indemnifying_role, indemnifying_side=base.indemnifying_side,
            indemnified_role=base.indemnified_role, indemnified_side=base.indemnified_side,
            trigger_treatments=base.trigger_treatments, scope=base.scope,
            defense_control=base.defense_control, notice_required=base.notice_required,
            cooperation_required=base.cooperation_required, monetary=restated,
            raw_excerpt=_excerpt(text, rm.start(), rm.end()),
            start_index=rm.start(), end_index=rm.end(),
            section_label=_section_label_before(text, rm.start()),
            role_side_conflict_reasons=base.role_side_conflict_reasons,
        ))
        seen_spans.append((rm.start(), rm.end()))

    for m in _MUTUAL_RECIPROCAL_RE.finditer(text):
        if any(abs(m.start() - s) < 50 for s, _ in seen_spans):
            continue
        window = _extract_obligation_window(text, m.start(), min(len(text), m.start() + _PROVISION_WINDOW_CHARS))
        # A mutual/reciprocal clause names no specific roles — represented
        # as a single symmetric obligation; the evaluator applies its terms
        # to both directions rather than picking one.
        obligations.append(IndemnityObligation(
            indemnifying_role="Each Party", indemnifying_side=None,
            indemnified_role="the Other Party", indemnified_side=None,
            trigger_treatments=_classify_triggers(window),
            scope=_classify_scope(window),
            defense_control=_classify_defense_control(window, "Each Party", "the Other Party"),
            notice_required=True if _NOTICE_RE.search(window) else None,
            cooperation_required=True if _COOPERATION_RE.search(window) else None,
            monetary=_classify_monetary(window, m.start()),
            raw_excerpt=_excerpt(text, m.start(), m.end()),
            start_index=m.start(), end_index=m.end(),
            section_label=_section_label_before(text, m.start()),
            is_mutual_reciprocal=True,
            asymmetry_reasons=_detect_reciprocal_asymmetry(window),
        ))
        seen_spans.append((m.start(), m.end()))

    if not obligations:
        if _EXPLICIT_NO_OBLIGATION_RE.search(text):
            # No directional promise was parsed, AND the document contains
            # an unambiguous statement that no obligation exists — treat
            # this the same as no clause being present at all, rather than
            # an unparseable-but-present clause. Deliberately narrow (fixed
            # phrases only): this must not fire on an ordinary "indemnif..."
            # mention that simply failed to parse for an unrelated reason.
            return None
        # "indemnif..." appears somewhere (e.g. a heading or a cross-
        # reference to an indemnification section elsewhere) but no
        # directional promise could be parsed from it.
        return IndemnificationFacts(clause_found=True, obligations=[])

    obligations.sort(key=lambda o: o.start_index)
    return IndemnificationFacts(clause_found=True, obligations=obligations)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _fmt_multiplier(value: Optional[float]) -> str:
    if value is None:
        return "unspecified"
    return f"{value:g}x annual fees"


def _build_ladder(policy: IndemnificationPolicyRuleLike, state: str) -> List[LadderStep]:
    step_specs = [
        ("IDEAL", f"Preferred exposure cap: {_fmt_multiplier(policy.exposure_preferred_multiplier)}"),
        ("ACCEPTABLE", f"Auto-accept exposure up to {_fmt_multiplier(policy.exposure_acceptable_max_multiplier)}"),
        ("FALLBACK", f"Negotiate exposure up to {_fmt_multiplier(policy.exposure_negotiate_max_multiplier)}"),
        ("ESCALATE", f"Beyond negotiable range — route to {policy.escalation_approval_authority or 'Legal Director'}"),
        ("WALK-AWAY", "Uncapped exposure — prohibited by policy" if policy.prohibit_uncapped_exposure else "Uncapped exposure"),
    ]
    return _core_build_ladder(state, step_specs)


def _resolve_obligations_for_side(
    obligations: List[IndemnityObligation], contract_side: str,
) -> Tuple[Optional[IndemnityObligation], Optional[IndemnityObligation], List[str]]:
    """Resolves which obligation (if any) is our EXPOSURE (we indemnify
    them) and which is our PROTECTION (they indemnify us). Returns
    (exposure_obligation, protection_obligation, unresolved_reasons).
    Never guesses: an obligation whose roles can't be mapped to our
    configured contract_side contributes a reason instead of being
    silently treated as exposure or protection."""
    reasons: List[str] = []
    exposure, protection = None, None

    reciprocal = [o for o in obligations if o.is_mutual_reciprocal]
    named = [o for o in obligations if not o.is_mutual_reciprocal]

    if reciprocal and not named:
        obligation = reciprocal[0]
        if obligation.asymmetry_reasons:
            # The clause opens with symmetric ("each party"/"mutual")
            # language, but states materially different terms for at
            # least one named party elsewhere in the same provision — the
            # opener's symmetry claim could not be verified, so it must
            # not be trusted as both our exposure AND our protection.
            # Never guess which named party's terms are actually ours;
            # route to REQUIRES_REVIEW instead of ACCEPT. See
            # tests/test_indemnification_policy_engine.py::
            # TestReciprocalSymmetryVerification and
            # benchmarks/indemnification_benchmark_report.md.
            reasons.append(
                "clause opens with reciprocal ('each party'/'mutual') language, but states "
                "materially different terms per named party (" + "; ".join(obligation.asymmetry_reasons) +
                ") — cannot confirm the clause is actually symmetric, so which named party's terms "
                "are ours cannot be determined from this opener alone"
            )
            return None, None, reasons
        # A symmetric mutual clause applies the same terms in both
        # directions — usable as both exposure and protection regardless
        # of contract_side, since the terms don't differ by party.
        return obligation, obligation, reasons

    # Step 4A.5 — direction invariance for a NAMED (not "each party") pair:
    # some drafting states two directional obligations explicitly by name
    # ("Landlord shall indemnify Tenant, and Tenant shall indemnify
    # Landlord...") instead of using reciprocal language, with IDENTICAL
    # terms in both directions. If the two roles are each other's
    # counterparty in exactly two obligations, and the monetary/scope/
    # defense_control terms match, the policy RESULT is invariant to
    # which one is "us" — so, exactly like the reciprocal-opener case
    # above, this can be used as both exposure and protection without
    # ever having to decide which named role we are. This does NOT
    # assign an unknown role a side, and does NOT apply when the two
    # directions differ in ANY tracked term (that is a genuine asymmetry,
    # left to escalate below as usual).
    if len(named) == 2:
        o1, o2 = named
        same_pair = (
            o1.indemnifying_role.lower() == o2.indemnified_role.lower()
            and o1.indemnified_role.lower() == o2.indemnifying_role.lower()
        )
        # Step 4A.7 — S4 remediation (Step 4A.6 A6-I-18, A6-I-23): this
        # equality check previously compared only monetary/scope/
        # defense_control, so a genuine per-direction difference in WHICH
        # claims are covered (trigger_treatments — e.g. a data-breach
        # carve-out with a longer survival period stated for only one
        # named party) or in procedural preconditions (notice/cooperation)
        # could pass as "the same pair, safe to treat as symmetric" even
        # though the two directions are not actually equivalent. The
        # required invariant is that ALL policy-relevant attributes must
        # match after direction normalization, not just the three that
        # happened to be checked already.
        # Step 4A.7 — S4 remediation (Step 4A.6 A6-I-18, A6-I-23): the
        # per-obligation fields above only capture what's true of the
        # SHARED window both obligations were extracted from (which is why
        # trigger_treatments alone doesn't distinguish them — a later
        # differentiating sentence naming just one party is visible to
        # both obligations' window equally). asymmetry_reasons is where
        # that window-level "does an except/provided-that clause, or a
        # named causation standard, single out one specific party" signal
        # now lives (see the two obligation-creation sites above) — if
        # EITHER obligation's window carries such a signal, the pair must
        # not be trusted as symmetric even though their own individual
        # fields happen to match.
        # Step 4A.7 — bugfix during Phase 7 verification: the fields
        # compared below (monetary/scope/defense_control/triggers/notice/
        # cooperation) can ALREADY, correctly, differ between two named
        # directions — e.g. benchmarks/indemnification_corpus.py's
        # split-reciprocal-02, where Vendor's exposure is explicitly
        # capped at 1x and Customer's protection to us is explicitly
        # uncapped. That is a real, intended, already-safely-handled
        # asymmetry (each direction resolves independently below via its
        # own clear role/monetary terms) — NOT the "opener claims
        # symmetry but a proviso quietly differentiates it" situation
        # asymmetry_reasons exists to catch. So asymmetry_reasons must
        # only ever BLOCK the fast invariance path (the case where every
        # other field already matched and the ONLY reason to distrust
        # treating the two as equivalent is a signal the other fields
        # don't capture — e.g. A6-I-18/A6-I-23) — it must never, by
        # itself, override an already-differentiated pair that the
        # ordinary per-obligation loop below is fully equipped to
        # resolve correctly.
        fields_match = (
            same_pair and _monetary_key(o1.monetary) == _monetary_key(o2.monetary)
            and o1.scope == o2.scope and o1.defense_control == o2.defense_control
            and _trigger_treatment_key(o1.trigger_treatments) == _trigger_treatment_key(o2.trigger_treatments)
            and o1.notice_required == o2.notice_required
            and o1.cooperation_required == o2.cooperation_required
        )
        if fields_match and not o1.asymmetry_reasons and not o2.asymmetry_reasons:
            return o1, o1, reasons
        if fields_match and (o1.asymmetry_reasons or o2.asymmetry_reasons):
            combined = list(dict.fromkeys(o1.asymmetry_reasons + o2.asymmetry_reasons))
            reasons.append(
                "the document states this obligation in both directions by name, but a per-party "
                "differentiation was found (" + "; ".join(combined) + ") — cannot confirm the two "
                "directions are actually equivalent"
            )
            return None, None, reasons

    if contract_side == "mutual":
        if named:
            reasons.append(
                "contract states directional (non-mutual) indemnification obligations, but this playbook "
                "is configured for a mutual position — cannot determine which obligation is ours"
            )
        return None, None, reasons

    for o in named:
        # Step 4A.5 — direction invariance: a strictly two-named-party,
        # non-reciprocal obligation has exactly one indemnifying role and
        # one indemnified role. If EITHER role's side is confidently
        # resolved (no role_side_conflict_reasons) and matches or
        # contradicts contract_side, the OTHER role's identity (us vs.
        # counterparty) follows by elimination — it does not need its
        # OWN generic-vocabulary classification, only its OWN definition
        # not to conflict. This is deliberately narrow: it does NOT
        # guess a side for an unmapped role in isolation, and it never
        # overrides a role that has its own conflict reason (a genuine
        # reversal/ambiguity always still blocks resolution).
        indemnifying_unmapped_clean = o.indemnifying_side is None and not any(
            r for r in o.role_side_conflict_reasons if o.indemnifying_role.lower() in r.lower()
        )
        indemnified_unmapped_clean = o.indemnified_side is None and not any(
            r for r in o.role_side_conflict_reasons if o.indemnified_role.lower() in r.lower()
        )
        effective_indemnifying_is_us = o.indemnifying_side == contract_side
        effective_indemnified_is_us = o.indemnified_side == contract_side
        if not effective_indemnifying_is_us and not effective_indemnified_is_us:
            # Neither side is confidently known to be us directly — check
            # whether the OTHER side is confidently known to be NOT us,
            # which (in a strictly two-party obligation) still identifies
            # this role as us by elimination.
            if o.indemnified_side is not None and o.indemnified_side != contract_side and indemnifying_unmapped_clean:
                effective_indemnifying_is_us = True
            elif o.indemnifying_side is not None and o.indemnifying_side != contract_side and indemnified_unmapped_clean:
                effective_indemnified_is_us = True

        if effective_indemnifying_is_us and (o.indemnified_side is not None and o.indemnified_side != contract_side or indemnified_unmapped_clean):
            if exposure is not None and _monetary_key(exposure.monetary) != _monetary_key(o.monetary):
                reasons.append("multiple obligations found where we are the indemnifying party, with different monetary terms — cannot determine which governs")
            elif exposure is None:
                exposure = o
        elif effective_indemnified_is_us and (o.indemnifying_side is not None and o.indemnifying_side != contract_side or indemnifying_unmapped_clean):
            if protection is not None and _monetary_key(protection.monetary) != _monetary_key(o.monetary):
                reasons.append("multiple obligations found where we are the indemnified party, with different monetary terms — cannot determine which governs")
            elif protection is None:
                protection = o
        elif o.indemnifying_side is None or o.indemnified_side is None:
            if o.role_side_conflict_reasons:
                # Step 4A: a specific, useful reason — the role WAS
                # recognized, but the document's own definition conflicts
                # with the generic vocabulary — rather than the generic
                # "unrecognized party name(s)" text below, which would be
                # misleading here.
                reasons.extend(o.role_side_conflict_reasons)
            else:
                reasons.append(
                    f"obligation \"{o.indemnifying_role} indemnifies {o.indemnified_role}\" could not be mapped "
                    f"to our configured contract side ({contract_side}) — unrecognized party name(s)"
                )

    return exposure, protection, reasons


def evaluate_indemnification_policy(
    facts: Optional[IndemnificationFacts],
    policy: IndemnificationPolicyRuleLike,
    source: Optional[str] = None,
) -> PolicyDecision:
    """Deterministic state machine over indemnification topology. Evaluates
    our EXPOSURE obligation (do we promise too much) and our PROTECTION
    obligation (does the counterparty promise us enough) independently,
    then combines them — REQUIRES_REVIEW wins if either side has an
    unresolved fact, otherwise the more severe of the two resolved states
    governs (ESCALATE/PROHIBITED > NEGOTIATE > ACCEPT_WITH_NOTE > ACCEPT)."""
    if facts is None or not facts.clause_found:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="indemnification", state=NOT_APPLICABLE,
            contract_language="", extracted_summary="No indemnification clause found",
            policy_limit_summary=_fmt_multiplier(policy.exposure_preferred_multiplier),
            required_action="None — this contract does not address indemnification",
            explanation="No indemnification clause was found in this contract, so the policy has nothing to evaluate against.",
            negotiation_ladder=_build_ladder(policy, NOT_APPLICABLE), category_treatments=[], unresolved_facts=[],
            start_index=None, end_index=None, source=source, summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
        )

    if not facts.obligations:
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="indemnification", state=REQUIRES_REVIEW,
            contract_language="", extracted_summary="Indemnification referenced but no directional obligation could be parsed",
            policy_limit_summary=_fmt_multiplier(policy.exposure_preferred_multiplier),
            required_action="Manual review required — indemnification language present but structure unclear",
            explanation="The document references indemnification but no parseable 'X shall indemnify Y' or mutual "
                        "reciprocal structure was found — the clause may be malformed, cross-referenced elsewhere, "
                        "or drafted in a form this extractor doesn't recognize.",
            negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW), category_treatments=[],
            unresolved_facts=["indemnification obligation structure could not be parsed"],
            start_index=None, end_index=None, source=source, summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
        )

    exposure, protection, resolution_reasons = _resolve_obligations_for_side(facts.obligations, policy.contract_side)
    unresolved_facts = list(resolution_reasons)

    required_protection = list(policy.required_protection_triggers_json or [])
    prohibited_exposure = list(policy.prohibited_exposure_triggers_json or [])

    # --- Protection-side unresolved facts ---
    # A missing protection obligation (protection is None with no
    # resolution_reason) is NOT treated as unresolved here — that's a
    # confidently-observed gap, handled below as a NEGOTIATE finding, not
    # an ambiguity requiring review.
    if protection is not None:
        for trig in required_protection:
            t = protection.trigger_treatments.get(trig)
            if t is not None and t.treatment == "unresolved":
                unresolved_facts.append(f"protection coverage for {trig} (ambiguous carve-out language)")
        if protection.monetary.kind == "cross_reference":
            unresolved_facts.append(
                f"protection monetary treatment (delegates to {protection.monetary.cross_reference_label}, not resolved by this evaluation)"
            )

    # --- Exposure-side unresolved facts ---
    exposure_monetary_value = None
    if exposure is not None:
        for trig in prohibited_exposure:
            t = exposure.trigger_treatments.get(trig)
            if t is not None and t.treatment == "unresolved":
                unresolved_facts.append(f"exposure coverage for {trig} (ambiguous carve-out language)")
        if policy.require_exposure_third_party_only and exposure.scope == "unresolved":
            unresolved_facts.append("exposure scope (third-party vs. first-party ambiguous)")
        if exposure.monetary.kind == "cross_reference":
            unresolved_facts.append(
                f"exposure monetary treatment (delegates to {exposure.monetary.cross_reference_label}, not resolved by this evaluation)"
            )

    if unresolved_facts:
        controlling = exposure or protection or facts.obligations[0]
        explanation = requires_review_explanation("indemnification structure", controlling.raw_excerpt, unresolved_facts)
        return PolicyDecision(
            rule_id=RULE_ID, clause_type="indemnification", state=REQUIRES_REVIEW,
            contract_language=controlling.raw_excerpt, extracted_summary="Could not be reliably established",
            policy_limit_summary=_fmt_multiplier(policy.exposure_negotiate_max_multiplier),
            required_action=requires_review_required_action(unresolved_facts),
            explanation=explanation, negotiation_ladder=_build_ladder(policy, REQUIRES_REVIEW),
            category_treatments=[], unresolved_facts=unresolved_facts,
            start_index=controlling.start_index, end_index=controlling.end_index, source=source,
            controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                    "start_index": controlling.start_index, "end_index": controlling.end_index},
            summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
        )

    # --- Resolved: determine severity-ranked findings from each side ---
    notes: List[str] = []
    worst_state = ACCEPT

    def _worse(a: str, b: str) -> str:
        order = {ACCEPT: 0, ACCEPT_WITH_NOTE: 1, NEGOTIATE: 2, MUST_REDLINE: 3, ESCALATE: 4, PROHIBITED: 5}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    if required_protection:
        if protection is None:
            notes.append(f"no protection obligation found covering required trigger(s): {', '.join(required_protection)}")
            worst_state = _worse(worst_state, NEGOTIATE)
        else:
            missing = [
                t for t in required_protection
                if protection.trigger_treatments.get(t) is None
                or protection.trigger_treatments[t].treatment != "covered"
            ]
            if missing:
                notes.append(f"protection missing required trigger(s): {', '.join(missing)}")
                worst_state = _worse(worst_state, NEGOTIATE)

    if exposure is not None:
        prohibited_hit = [
            t for t in prohibited_exposure
            if exposure.trigger_treatments.get(t) is not None
            and exposure.trigger_treatments[t].treatment == "covered"
        ]
        if prohibited_hit:
            notes.append(f"exposure covers prohibited trigger(s): {', '.join(prohibited_hit)}")
            worst_state = _worse(worst_state, NEGOTIATE)

        # A scope that was never affirmatively confirmed as third-party-only
        # ("not_addressed" — the text simply never said "third-party
        # claims") is not the same fact as a confirmed third-party-only
        # limitation, and must not be silently treated as satisfying a
        # policy that specifically requires that limitation to be stated.
        # See tests/test_indemnification_policy_engine.py::
        # TestThirdPartyOnlyScopeSilence and benchmarks/
        # indemnification_benchmark_report.md's scope-05 finding.
        if policy.require_exposure_third_party_only and exposure.scope != "third_party_only":
            notes.append("exposure is not affirmatively limited to third-party claims")
            worst_state = _worse(worst_state, NEGOTIATE)

        if policy.require_defense_control_for_exposure and exposure.defense_control not in ("indemnifying_party", "shared"):
            notes.append("we do not control (or share control of) the defense of claims we must indemnify")
            worst_state = _worse(worst_state, NEGOTIATE)

        if policy.require_notice_and_cooperation_for_exposure and not (exposure.notice_required and exposure.cooperation_required):
            notes.append("exposure obligation lacks a notice-and-cooperation precondition")
            worst_state = _worse(worst_state, NEGOTIATE)

        if exposure.monetary.kind == "unlimited":
            if policy.prohibit_uncapped_exposure:
                notes.append("exposure is uncapped, prohibited by policy")
                worst_state = _worse(worst_state, PROHIBITED)
            else:
                notes.append("exposure is uncapped")
                worst_state = _worse(worst_state, ESCALATE)
        elif exposure.monetary.kind == "fixed":
            notes.append(f"exposure cap is a fixed dollar amount ({exposure.monetary.summary()}), not a fees multiplier — compare manually")
            worst_state = _worse(worst_state, ESCALATE)
        elif exposure.monetary.kind == "multiplier":
            threshold_state = classify_by_threshold(
                exposure.monetary.multiplier, policy.exposure_preferred_multiplier,
                policy.exposure_acceptable_max_multiplier, policy.exposure_negotiate_max_multiplier,
            )
            if threshold_state != ACCEPT:
                notes.append(f"exposure cap {exposure.monetary.summary()} exceeds preferred position")
            worst_state = _worse(worst_state, threshold_state)
        elif exposure.monetary.kind == "not_stated":
            notes.append("exposure obligation states no monetary treatment at all")
            worst_state = _worse(worst_state, MUST_REDLINE)

    controlling = exposure or protection or facts.obligations[0]
    extracted_summary = (
        f"Exposure: {exposure.monetary.summary() if exposure else 'n/a'}; "
        f"Protection: {'present' if protection else 'not found'}"
    )
    if worst_state == ACCEPT and not notes:
        required_action = "None — indemnification terms meet policy"
        explanation = f"Contract language: \"{controlling.raw_excerpt}\". No policy gaps found. Result: {ACCEPT}."
    else:
        if worst_state in (ESCALATE, PROHIBITED):
            required_action = f"Escalate to {policy.escalation_approval_authority or 'Legal Director'} — " + "; ".join(notes)
        elif worst_state == NEGOTIATE:
            required_action = "Negotiate — " + "; ".join(notes)
        else:
            required_action = "None — within acceptable range, note for the file: " + "; ".join(notes)
        explanation = (
            f"Contract language: \"{controlling.raw_excerpt}\". {'; '.join(notes)}. Result: {worst_state}."
        )

    return PolicyDecision(
        rule_id=RULE_ID, clause_type="indemnification", state=worst_state,
        contract_language=controlling.raw_excerpt, extracted_summary=extracted_summary,
        policy_limit_summary=_fmt_multiplier(policy.exposure_negotiate_max_multiplier),
        required_action=required_action, explanation=explanation,
        negotiation_ladder=_build_ladder(policy, worst_state),
        category_treatments=[
            {"category": t.trigger, "treatment": t.treatment, "cap_summary": None,
             "raw_excerpt": t.raw_excerpt, "established": t.established}
            for t in (exposure.trigger_treatments.values() if exposure else [])
        ],
        unresolved_facts=[], start_index=controlling.start_index, end_index=controlling.end_index,
        escalate_to=escalate_to_for_state(worst_state, policy.escalation_approval_authority),
        fallback_text=fallback_text_for_state(worst_state, policy.fallback_text, (NEGOTIATE, ESCALATE, PROHIBITED)),
        source=source,
        controlling_provision={"label": controlling.label(), "excerpt": controlling.raw_excerpt,
                                "start_index": controlling.start_index, "end_index": controlling.end_index},
        our_position={"role": exposure.indemnifying_role, "summary": exposure.monetary.summary()} if exposure else None,
        counterparty_position={"role": protection.indemnifying_role, "summary": protection.monetary.summary()} if protection else None,
        summary_label="Indemnification treatment", our_position_label="Our exposure",
        counterparty_position_label="Counterparty protection",
    )
