"""
Negotiation Reasoning Chain.

Product roadmap Feature 6 (see the product memo, Rev. 2): "why this
wording" matters more than "here's better wording." A redline with no
reasoning is an edit; a redline with a reasoning chain is a negotiation
position — Clause -> Issue -> Legal Risk -> Business Risk -> Market
Standard -> Suggested Revision -> Suggested Redline -> Expected
Counterparty Objection -> Fallback Position.

Scope, stated honestly: authoring a reasoning chain is legal-drafting
content, not pattern-matching — the same category of real, justified,
per-item analytical work severity_factor_data.py's own docstring
describes for severity scoring ("real analytical work a human has to do
and justify in text... not analogy-based"). It does not scale by
mass-producing shallow text across every deficiency the Clause Quality
Engine can detect.

This module currently covers ONE full module end-to-end — Arbitration,
the roadmap's flagship — as a complete, working demonstration of the
pattern: all 7 of its deficiency elements have a fully authored chain.
Liability, Confidentiality, Indemnification, Termination, and IP are NOT
yet covered here; extending this module to them (and eventually to the
189 detection rules directly) is a scoped follow-up requiring the same
per-item authoring discipline, not something to rush.

A chain is only meaningful for a DEFICIENCY (an element that is absent) —
there is nothing to negotiate about an element that's already present, so
callers should only look up a chain when clause_quality.ClauseElement.present
is False.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class ReasoningChain:
    issue: str
    legal_risk: str
    business_risk: str
    market_standard: str
    suggested_revision: str
    suggested_redline: str
    expected_counterparty_objection: str
    fallback_position: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "issue": self.issue,
            "legal_risk": self.legal_risk,
            "business_risk": self.business_risk,
            "market_standard": self.market_standard,
            "suggested_revision": self.suggested_revision,
            "suggested_redline": self.suggested_redline,
            "expected_counterparty_objection": self.expected_counterparty_objection,
            "fallback_position": self.fallback_position,
        }


# (module, element_key) -> ReasoningChain. Only ARBITRATION is complete —
# see module docstring.
_CHAINS: Dict[Tuple[str, str], ReasoningChain] = {}


def _add(module: str, element_key: str, chain: ReasoningChain) -> None:
    _CHAINS[(module, element_key)] = chain


_add("arbitration", "institution", ReasoningChain(
    issue="The arbitration clause does not name an administering institution.",
    legal_risk="Without a named institution, there is no body responsible for appointing "
               "arbitrators if the parties can't agree, administering the case procedurally, "
               "or providing a fallback set of rules — an ad hoc arbitration can stall entirely "
               "at the outset over exactly these questions, sometimes requiring a separate court "
               "petition just to get the tribunal constituted.",
    business_risk="A stalled or contested tribunal-formation process delays resolution of "
                  "the underlying dispute — every additional month of delay compounds legal "
                  "spend and prolongs unresolved commercial exposure.",
    market_standard="Commercial contracts of this type typically name AAA (domestic, "
                     "commercial) or ICC/SIAC/LCIA (cross-border) as the administering "
                     "institution, paired with that institution's own rules.",
    suggested_revision="Name a specific, recognized arbitral institution to administer the "
                        "proceedings.",
    suggested_redline="Any dispute arising out of or relating to this Agreement shall be "
                       "finally resolved by arbitration administered by the American "
                       "Arbitration Association (\"AAA\") in accordance with its Commercial "
                       "Arbitration Rules.",
    expected_counterparty_objection="Counterparty may prefer a different institution (e.g. "
                                     "JAMS) it has existing panel relationships or familiarity "
                                     "with, or may push for ad hoc (UNCITRAL Rules, no "
                                     "administering institution) to reduce administrative fees.",
    fallback_position="Accept JAMS or another recognized institution the counterparty already "
                       "uses regularly; if counterparty insists on ad hoc, require UNCITRAL "
                       "Arbitration Rules specifically (not a bespoke procedure) so a known, "
                       "tested rule set still governs even without an administering body.",
))

_add("arbitration", "seat", ReasoningChain(
    issue="The arbitration clause does not specify a legal seat (place) of arbitration.",
    legal_risk="The seat determines which country's arbitration law governs the proceeding "
               "and which national courts have supervisory jurisdiction (e.g. to hear a "
               "challenge to the tribunal's jurisdiction, or to enforce/set aside the eventual "
               "award). Without a stated seat, this is left to be argued after a dispute has "
               "already arisen — exactly when the parties can least agree on anything.",
    business_risk="A fight over the seat before the merits are even reached adds a preliminary "
                  "procedural dispute, delaying resolution and adding legal cost before the "
                  "substantive case begins.",
    market_standard="A specific city and country (e.g. \"New York, New York, USA\" or "
                     "\"London, England\") is standard; the seat need not be where hearings "
                     "physically occur (see \"virtual/physical hearing location\" as a "
                     "separate, non-legal logistics question).",
    suggested_revision="State a specific city and country as the legal seat of arbitration.",
    suggested_redline="The seat of arbitration shall be New York, New York, USA.",
    expected_counterparty_objection="Counterparty may push for its own home jurisdiction as "
                                     "the seat, for the practical advantage of more familiar "
                                     "local counsel and courts.",
    fallback_position="Propose a neutral third jurisdiction with well-developed, arbitration-"
                       "friendly law (e.g. Delaware, England, Singapore, or Switzerland) rather "
                       "than conceding the counterparty's home forum outright.",
))

_add("arbitration", "rules", ReasoningChain(
    issue="The arbitration clause does not reference a specific set of governing arbitration rules.",
    legal_risk="Without named rules, procedural questions (how arbitrators are appointed, "
               "briefing schedules, discovery/disclosure scope, whether interim relief is "
               "available) have no default framework — parties may need to negotiate basic "
               "procedure from scratch after a dispute has already arisen.",
    business_risk="Ad hoc procedural negotiation after a dispute arises adds delay and legal "
                  "cost to what should be a resolution phase, not another round of negotiation.",
    market_standard="Rules are typically tied to the named institution — AAA Commercial "
                     "Arbitration Rules, ICC Rules of Arbitration, SIAC Rules, LCIA Rules, or "
                     "UNCITRAL Arbitration Rules for ad hoc proceedings.",
    suggested_revision="Reference the procedural rules of the named administering institution.",
    suggested_redline="...in accordance with the Commercial Arbitration Rules of the American "
                       "Arbitration Association then in effect.",
    expected_counterparty_objection="Generally low resistance — this is typically a "
                                     "housekeeping addition once an institution is agreed, not "
                                     "a substantive point of negotiation.",
    fallback_position="If the parties can't agree on an institution, adopt the UNCITRAL "
                       "Arbitration Rules as a neutral, institution-independent default.",
))

_add("arbitration", "arbitrator_count", ReasoningChain(
    issue="The arbitration clause does not specify the number of arbitrators.",
    legal_risk="Absent an agreed number, this becomes a threshold dispute in itself — under "
               "most institutional rules the default is a sole arbitrator unless the parties "
               "specify otherwise (or three, if the rules or amount in controversy trigger it "
               "automatically), which may not match what either party actually intended for "
               "a dispute of this contract's size.",
    business_risk="A three-arbitrator panel roughly triples arbitrator fees and lengthens the "
                  "process versus a sole arbitrator — for a lower-value contract, an unstated "
                  "default to three multiplies dispute-resolution cost relative to the amount "
                  "actually at stake.",
    market_standard="One arbitrator for disputes under roughly $1-5M in controversy (faster, "
                     "materially cheaper); three arbitrators for higher-value or technically "
                     "complex disputes, or where either party wants a party-appointed "
                     "arbitrator on the panel.",
    suggested_revision="State the number of arbitrators explicitly, sized to the realistic "
                        "value of disputes under this Agreement.",
    suggested_redline="The arbitration shall be conducted by a sole arbitrator appointed in "
                       "accordance with the [Institution] Rules.",
    expected_counterparty_objection="A counterparty facing significant potential exposure "
                                     "under the contract may prefer three arbitrators (a "
                                     "party-appointed seat on the panel, not just an "
                                     "institution-selected sole arbitrator) despite the added "
                                     "cost.",
    fallback_position="Tie the arbitrator count to a dollar threshold: sole arbitrator below a "
                       "stated amount in controversy, three-arbitrator panel above it.",
))

_add("arbitration", "language", ReasoningChain(
    issue="The arbitration clause does not specify the language of the proceedings.",
    legal_risk="For a cross-border relationship, the language of arbitration is not obviously "
               "implied by the seat or the contract's own drafting language — leaving this "
               "unstated risks a dispute conducted (and evidence translated) in a language "
               "neither party specifically agreed to, adding cost and interpretive risk to "
               "every submission.",
    business_risk="Translation of pleadings, evidence, and hearing transcripts into an "
                  "unplanned-for language is a real, avoidable cost that falls on both sides "
                  "and can meaningfully slow the proceeding.",
    market_standard="English is the default choice in the large majority of international "
                     "commercial arbitrations regardless of the parties' home languages, given "
                     "arbitrator and counsel availability.",
    suggested_revision="State the language of the arbitration explicitly.",
    suggested_redline="The language of the arbitration shall be English.",
    expected_counterparty_objection="A counterparty operating primarily in another language "
                                     "may prefer that language, or request bilingual "
                                     "proceedings (which meaningfully increases cost for both "
                                     "sides via dual translation/interpretation).",
    fallback_position="Agree to English for the arbitration itself, while allowing documentary "
                       "evidence originally created in another language to be submitted with "
                       "a certified translation rather than requiring bilingual proceedings "
                       "throughout.",
))

_add("arbitration", "emergency_relief", ReasoningChain(
    issue="The arbitration clause does not address emergency arbitrator procedures or interim/"
          "provisional relief pending constitution of the tribunal.",
    legal_risk="A standard tribunal typically takes weeks to months to constitute. Without an "
               "emergency-relief mechanism, a party facing genuinely urgent harm (e.g. an "
               "imminent confidentiality breach or irreversible IP misuse) may have no fast "
               "avenue for interim protection during that gap — and if the arbitration clause "
               "is drafted as fully exclusive, may even be blocked from seeking that relief in "
               "court instead.",
    business_risk="Real, time-sensitive harm (leaking trade secrets, ongoing infringement) can "
                  "become irreversible during the weeks it takes to constitute a standard "
                  "tribunal, with no contractual mechanism to stop it sooner.",
    market_standard="Most major institutional rules (AAA, ICC, SIAC, LCIA) already include "
                     "emergency arbitrator provisions by default; well-drafted clauses "
                     "additionally carve out an express right to seek interim injunctive "
                     "relief from a court in parallel, notwithstanding the arbitration "
                     "agreement, for genuinely urgent matters.",
    suggested_revision="Add an express carve-out preserving the right to seek emergency/"
                        "interim relief, whether via the institution's emergency arbitrator "
                        "process or in a court of competent jurisdiction.",
    suggested_redline="Notwithstanding the foregoing, either party may seek emergency or "
                       "interim injunctive relief from a court of competent jurisdiction, or "
                       "via an emergency arbitrator under the [Institution] Rules, without "
                       "waiving its right to arbitrate the underlying dispute.",
    expected_counterparty_objection="A counterparty concerned about forum-shopping may want "
                                     "the emergency-relief carve-out narrowly limited to "
                                     "specific clause types (e.g. confidentiality, IP) rather "
                                     "than available for any dispute.",
    fallback_position="Narrow the carve-out to confidentiality and IP-infringement claims "
                       "specifically, rather than a general emergency-relief right for any "
                       "type of dispute under the Agreement.",
))

_add("arbitration", "no_litigation_conflict", ReasoningChain(
    issue="This document also contains an exclusive court-jurisdiction clause elsewhere, "
          "which conflicts with the arbitration clause.",
    legal_risk="Two dispute-resolution mechanisms that each claim exclusivity create a real "
               "ambiguity about which one actually governs — a party could plausibly argue for "
               "either forum depending on which is more favorable at the time a dispute arises, "
               "and a court may need to resolve the conflict itself before the underlying "
               "dispute can even be addressed.",
    business_risk="A forum fight is a real, billable dispute in its own right, layered on top "
                  "of (and delaying) the actual commercial dispute the parties need resolved.",
    market_standard="A single, internally consistent dispute-resolution clause — either "
                     "arbitration exclusively (with a narrow, express carve-out for interim "
                     "court relief, see the emergency-relief element above) or litigation "
                     "exclusively, never a bare, competing pair of full clauses.",
    suggested_revision="Remove the competing exclusive-jurisdiction clause, or, if the intent "
                        "is genuinely both forums for different purposes, make each clause's "
                        "scope narrow and mutually exclusive on its face.",
    suggested_redline="Except as expressly provided in Section [emergency relief], the "
                       "arbitration provisions of Section [X] shall be the parties' sole and "
                       "exclusive means of resolving any dispute arising out of or relating to "
                       "this Agreement.",
    expected_counterparty_objection="The competing clause may have been inherited from a "
                                     "template and nobody currently disputes removing it, but "
                                     "counterparty's counsel may want to confirm which clause "
                                     "was actually intended before agreeing to strike either.",
    fallback_position="If neither party will concede which clause governs, expressly carve "
                       "out one narrow category (e.g. only IP-infringement claims proceed in "
                       "court, everything else arbitrates) so the scope conflict is resolved "
                       "rather than left ambiguous.",
))


def get_reasoning_chain(module: str, element_key: str) -> Optional[ReasoningChain]:
    """Returns the authored reasoning chain for a deficient
    (present=False) clause_quality element, or None if this specific
    (module, element_key) pair hasn't been authored yet — callers should
    treat None as "not yet covered," never fabricate a chain on the fly."""
    return _CHAINS.get((module, element_key))


def covered_modules() -> Tuple[str, ...]:
    """Which clause_quality modules currently have ANY authored chains —
    for callers/UI that want to say plainly what's covered vs. roadmap."""
    return tuple(sorted({module for module, _ in _CHAINS}))
