"""
Deterministic Legal Work Product — Rule-ID-to-Redline mapping.

This is NOT an LLM generating legal language. Every rule_id maps to
exactly ONE reviewed default redline. The same rule always produces the
same suggested language — only contract-specific variables (defined party
names, section references) are substituted deterministically at render
time (see _substitute_variables). An LLM may explain a redline; it must
never author the redline text itself. If a future caller is tempted to
have an LLM fill in `suggested_redline`, that is a violation of this
module's entire purpose.

Ten drafting principles every template here follows (why each field looks
the way it does):

1. Minimum viable edit — a template targets ONE sentence or phrase, never
   "rewrite the whole clause." Lawyers negotiate; they don't redraft.
2. One issue, one solution — "add a liability cap," not "fix liability."
3. Preserve commercial intent — never touches price, deliverables, or
   scope; only reduces unnecessary legal risk.
4. Explain why — every template carries the full reasoning chain, never
   just replacement text.
5. Market-standard wording — conservative, commonly-used drafting, not
   creative/novel language. The goal is opposing counsel accepting it on
   sight, not admiring it.
6. Minimize negotiation friction — where two legally equivalent edits
   exist, prefer the one more likely to be accepted without a fight.
7. Preserve drafting style — templates use "shall," the formal register
   most commercial contracts already use; this module does not adapt
   per-contract style (a real limitation, stated honestly — see
   render_redline's docstring).
8. No new obligations unless necessary — prefer clarifying/capping an
   existing obligation over inventing a new one.
9. No over-negotiation — the redline is the smallest change that fixes
   the specific problem, not a maximalist rewrite.
10. Honest confidence — High (industry-standard wording), Medium (several
    acceptable alternatives exist), or Low (jurisdiction-specific, manual
    review recommended).

Scope, stated honestly: this covers a curated set of the highest-
frequency, highest-severity rules — not all 189. Each entry here is
genuinely reviewed, single-issue, attorney-quality content; extending
coverage is the same per-rule authoring discipline applied to more rules,
not something to mass-produce. See COVERED_RULE_IDS.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RedlineTemplate:
    issue: str  # short label, e.g. "Unlimited Liability"
    clause_category: str  # e.g. "Limitation of Liability"
    problem: str
    legal_rationale: str
    business_impact: str
    recommended_change: str
    suggested_redline: str  # may contain {party_a}/{party_b} placeholders
    why_this_wording: str
    expected_counterparty_position: str
    negotiation_difficulty: str  # "Low" | "Medium" | "High"
    fallback_position: str
    confidence: str  # "High" | "Medium" | "Low"


_TEMPLATES: Dict[str, RedlineTemplate] = {}


def _add(rule_id: str, template: RedlineTemplate) -> None:
    _TEMPLATES[rule_id] = template


_add("H_LOL_01", RedlineTemplate(
    issue="Unlimited Liability",
    clause_category="Limitation of Liability",
    problem="Liability is not capped, or the cap is weakened by carve-out/exclusion language that "
            "removes its practical effect.",
    legal_rationale="Without a cap, downside exposure under this Agreement is not bounded by the "
                     "value of the deal — a single claim can exceed the total fees ever paid, "
                     "regardless of the parties' relative bargaining positions or the contract's "
                     "actual size.",
    business_impact="Uncapped exposure is difficult to price, insure against, or reserve for — it "
                     "turns an otherwise-ordinary commercial relationship into an open-ended "
                     "financial risk.",
    recommended_change="Add a liability cap tied to fees paid under the Agreement, with standard "
                        "carve-outs for fraud, willful misconduct, confidentiality, and "
                        "indemnification.",
    suggested_redline="Except for liability arising from fraud, willful misconduct, confidentiality "
                       "obligations, or indemnification obligations expressly provided under this "
                       "Agreement, each party's aggregate liability shall not exceed the total fees "
                       "paid under this Agreement during the twelve (12) months preceding the event "
                       "giving rise to the claim.",
    why_this_wording="This is the single most common liability-cap formulation in commercial "
                      "contracts — a trailing-twelve-months fee-based cap with the four standard "
                      "carve-outs. It is instantly recognizable to opposing counsel and rarely "
                      "requires explanation.",
    expected_counterparty_position="Counterparty may propose a lower cap (e.g. a fixed dollar amount "
                                    "instead of fees paid) or push to narrow the carve-out list.",
    negotiation_difficulty="Low",
    fallback_position="Accept a fixed-dollar cap in place of the trailing-twelve-months formula if "
                       "the fixed amount is not materially lower than expected fees; do not concede "
                       "the fraud/willful-misconduct/confidentiality/indemnification carve-outs.",
    confidence="High",
))

_add("H_ASYMMETRIC_LIABILITY_01", RedlineTemplate(
    issue="Asymmetric Liability Cap",
    clause_category="Limitation of Liability",
    problem="The liability cap applies to one party only, leaving the other party's liability "
            "uncapped.",
    legal_rationale="A one-sided cap does not eliminate risk — it reallocates it entirely onto the "
                     "uncapped party, who now bears unbounded exposure while the counterparty's "
                     "downside is fixed.",
    business_impact="The uncapped party is effectively insuring the deal for both sides without "
                     "being compensated for that risk.",
    recommended_change="Make the existing cap mutual — apply the same cap language to both parties "
                        "rather than adding a new mechanism.",
    suggested_redline="Each party's aggregate liability under this Agreement shall be subject to the "
                       "limitation set forth in this Section, applied equally to both parties.",
    why_this_wording="A one-line mutuality fix that reuses the cap the drafting party already wrote "
                      "for itself — this is the smallest possible edit that solves the actual "
                      "problem (asymmetry), not a request for a new cap structure.",
    expected_counterparty_position="Counterparty (usually the drafting party) may argue its own risk "
                                    "profile under the contract is inherently different and does not "
                                    "warrant symmetry.",
    negotiation_difficulty="Medium",
    fallback_position="If full mutuality is refused, request a cap for the other party at a higher "
                       "multiple (e.g. 2-3x fees paid) rather than leaving it fully uncapped.",
    confidence="High",
))

_add("H_LOL_NO_CARVEOUT_01", RedlineTemplate(
    issue="Liability Cap Missing High-Severity Carve-Outs",
    clause_category="Limitation of Liability",
    problem="The liability cap has no carve-outs, meaning it applies even to fraud, willful "
            "misconduct, confidentiality breaches, and IP infringement claims.",
    legal_rationale="A cap without carve-outs effectively pre-authorizes bad-faith conduct up to the "
                     "cap amount — there is no way to recover more than the cap even for the most "
                     "egregious breaches.",
    business_impact="The most severe, reputationally damaging claims (a data breach, IP theft, "
                     "intentional fraud) are capped at the same low ceiling as an ordinary "
                     "performance dispute.",
    recommended_change="Add standard carve-outs to the existing cap for fraud, willful misconduct, "
                        "confidentiality breaches, and indemnification obligations.",
    suggested_redline="The foregoing limitation shall not apply to liability arising from a party's "
                       "fraud, willful misconduct, breach of confidentiality obligations, or "
                       "indemnification obligations under this Agreement.",
    why_this_wording="A single carve-out sentence appended to the existing cap — it does not "
                      "restructure the cap itself, only excludes the categories of claim that "
                      "commercial practice already treats as uncappable.",
    expected_counterparty_position="Counterparty may push to narrow the carve-out list (e.g. drop "
                                    "confidentiality or indemnification) to keep more claim types "
                                    "within the cap.",
    negotiation_difficulty="Medium",
    fallback_position="If the full four-item list is contested, hold firm on fraud and willful "
                       "misconduct (near-universally accepted as uncappable) and treat "
                       "confidentiality/indemnification as the negotiable items.",
    confidence="High",
))

_add("H_CONSEQUENTIAL_01", RedlineTemplate(
    issue="One-Sided Consequential Damages Waiver",
    clause_category="Limitation of Liability",
    problem="The waiver of consequential, indirect, or special damages applies to only one party.",
    legal_rationale="A one-sided waiver removes a real remedy category for one side while preserving "
                     "it for the other — in a dispute, the party without the waiver can recover "
                     "damage types the other side already gave up.",
    business_impact="The burdened party carries a materially larger tail-risk than its counterparty "
                     "for the same category of harm.",
    recommended_change="Make the existing consequential-damages waiver mutual.",
    suggested_redline="In no event shall either party be liable to the other for any consequential, "
                       "indirect, incidental, special, or punitive damages arising out of or "
                       "relating to this Agreement.",
    why_this_wording="Mutual consequential-damages waivers using this exact formulation are the "
                      "market default in commercial contracts — reusing it (rather than the "
                      "one-sided version already in the draft) is the smallest edit that fixes the "
                      "asymmetry.",
    expected_counterparty_position="Low resistance is typical — a one-sided version is often an "
                                    "oversight from a template rather than a deliberate position, "
                                    "and mutual waivers are the norm.",
    negotiation_difficulty="Low",
    fallback_position="If resisted, request the same waiver scoped narrowly to the categories of "
                       "damages most likely to actually arise under this Agreement's subject "
                       "matter.",
    confidence="High",
))

_add("H_INDEM_01", RedlineTemplate(
    issue="Unlimited Indemnification",
    clause_category="Indemnification",
    problem="The indemnification obligation is not capped and can exceed the value of the contract.",
    legal_rationale="Indemnification is a distinct exposure from the general limitation-of-liability "
                     "clause; if it is not itself capped or tied to the liability cap, it can bypass "
                     "that cap entirely.",
    business_impact="A single third-party claim triggering indemnification can create liability far "
                     "exceeding the deal's actual value.",
    recommended_change="Tie the indemnification obligation to the Agreement's existing liability "
                        "cap, or add a standalone cap if none exists.",
    suggested_redline="Each indemnifying party's aggregate liability under this indemnification "
                       "obligation shall be subject to the limitation of liability set forth in "
                       "Section [X] of this Agreement.",
    why_this_wording="Cross-referencing the existing cap (rather than drafting a new, separate cap "
                      "amount) is the smallest edit and avoids creating two different liability "
                      "ceilings in the same contract.",
    expected_counterparty_position="Counterparty may want indemnification carved OUT of the general "
                                    "cap specifically for IP-infringement or third-party claims.",
    negotiation_difficulty="Medium",
    fallback_position="Accept a separate, higher cap specifically for indemnification (e.g. 2x the "
                       "general liability cap) rather than leaving it fully uncapped.",
    confidence="High",
))

_add("H_INDEM_ONEWAY_01", RedlineTemplate(
    issue="One-Way Indemnification",
    clause_category="Indemnification",
    problem="Only one party has an indemnification obligation to the other.",
    legal_rationale="One-way indemnification allocates all third-party-claim risk to a single party, "
                     "regardless of which party's conduct actually caused the claim.",
    business_impact="The indemnifying party bears the full cost of third-party claims even those "
                     "arising from the other party's own acts or omissions.",
    recommended_change="Make the indemnification obligation mutual, each party indemnifying the "
                        "other for claims arising from its own acts.",
    suggested_redline="Each party shall indemnify, defend, and hold harmless the other party from "
                       "and against any third-party claims arising from the indemnifying party's "
                       "breach of this Agreement, negligence, or willful misconduct.",
    why_this_wording="A standard mutual indemnity tied to each party's own conduct — this is the "
                      "market default and does not expand what either party is indemnifying "
                      "against, only who owes the obligation.",
    expected_counterparty_position="The drafting party may argue its role in the relationship "
                                    "(e.g. pure service recipient) does not create indemnifiable "
                                    "risk on its side.",
    negotiation_difficulty="Medium",
    fallback_position="If full mutuality is refused, scope the counterparty's indemnity narrowly to "
                       "claims arising from its own breach of confidentiality or IP representations, "
                       "rather than conceding one-way indemnification entirely.",
    confidence="Medium",
))

_add("H_TERM_CONVENIENCE_01", RedlineTemplate(
    issue="One-Sided Termination for Convenience",
    clause_category="Termination",
    problem="Only one party may terminate the Agreement for convenience (without cause).",
    legal_rationale="A one-sided convenience-termination right lets one party exit the deal at will "
                     "while the other remains bound for the full term, regardless of that party's "
                     "own performance.",
    business_impact="The bound party cannot exit even a deteriorating relationship without cause, "
                     "while the other side can walk away at any time.",
    recommended_change="Make the existing termination-for-convenience right mutual, with the same "
                        "notice period for both parties.",
    suggested_redline="Either party may terminate this Agreement for convenience upon [30] days' "
                       "prior written notice to the other party.",
    why_this_wording="Reuses the exact notice period already in the one-sided version — the only "
                      "change is which party may exercise the right, which is the smallest edit "
                      "that fixes the asymmetry.",
    expected_counterparty_position="The drafting party may resist giving up its unilateral exit "
                                    "right, particularly if the contract secures revenue it wants "
                                    "locked in.",
    negotiation_difficulty="Medium",
    fallback_position="If mutuality is refused, request a longer minimum notice period or a "
                       "wind-down/transition-assistance obligation triggered by the other party's "
                       "convenience termination, to offset the asymmetry commercially.",
    confidence="High",
))

_add("H_ATTFEE_01", RedlineTemplate(
    issue="One-Way Attorneys' Fees",
    clause_category="Dispute Resolution",
    problem="Only one party can recover attorneys' fees if it prevails in a dispute.",
    legal_rationale="A one-sided fee-shifting clause changes the economics of a dispute — the party "
                     "without fee-recovery rights bears its own legal costs even if it wins, while "
                     "the other side does not.",
    business_impact="One-sided fee-shifting can discourage the disadvantaged party from pursuing "
                     "even meritorious claims, since litigation cost is not recoverable regardless "
                     "of outcome.",
    recommended_change="Make the attorneys'-fees provision mutual — the prevailing party, whichever "
                        "party that is, recovers its fees.",
    suggested_redline="In any action to enforce this Agreement, the prevailing party shall be "
                       "entitled to recover its reasonable attorneys' fees and costs from the "
                       "non-prevailing party.",
    why_this_wording="Standard \"prevailing party\" fee-shifting language — this is the most common "
                      "mutual formulation in commercial contracts and requires no further "
                      "negotiation over mechanics.",
    expected_counterparty_position="Generally low resistance — a one-sided version is often "
                                    "template drafting rather than a considered position.",
    negotiation_difficulty="Low",
    fallback_position="If resisted, propose deleting the fee-shifting provision entirely (each party "
                       "bears its own costs) rather than leaving the one-sided version in place.",
    confidence="High",
))

_add("M_ARBITRATION_01", RedlineTemplate(
    issue="Mandatory Arbitration / Class Action Waiver",
    clause_category="Dispute Resolution",
    problem="The Agreement requires mandatory, binding arbitration and/or waives the right to bring "
            "or participate in a class action, removing access to court and collective remedies.",
    legal_rationale="Mandatory arbitration and class-action waivers are generally enforceable in "
                     "commercial contracts, but they materially change the venue, cost, and "
                     "available remedies for any future dispute — this is a deliberate choice to "
                     "flag, not a defect to eliminate outright.",
    business_impact="Arbitration can be faster and more private than litigation, but also limits "
                     "discovery, appeal rights, and (with a class-action waiver) the ability to "
                     "aggregate small claims — evaluate against the realistic dispute profile for "
                     "this relationship.",
    recommended_change="If arbitration is acceptable in principle, ensure the clause specifies "
                        "institution, seat, rules, arbitrator count, and language (see the "
                        "Arbitration Clause Inspector); if arbitration is not acceptable, negotiate "
                        "removal in favor of litigation with an agreed venue.",
    suggested_redline="Any dispute arising out of or relating to this Agreement shall be resolved "
                       "exclusively in the state or federal courts located in [Venue], and each "
                       "party consents to the personal jurisdiction of such courts.",
    why_this_wording="This redline is offered only as the litigation ALTERNATIVE to arbitration, for "
                      "when arbitration itself (not just an incomplete arbitration clause) is the "
                      "point of negotiation — standard exclusive-venue litigation language, the "
                      "most common alternative structure.",
    expected_counterparty_position="A counterparty that specifically wants arbitration (e.g. for "
                                    "confidentiality or to avoid jury trials) will likely resist "
                                    "removing it outright.",
    negotiation_difficulty="High",
    fallback_position="Rather than removing arbitration entirely, negotiate carve-outs allowing "
                       "either party to seek injunctive relief in court, and ensure the arbitration "
                       "clause itself is complete (see the Arbitration Clause Inspector's element "
                       "checklist) even if arbitration itself is retained.",
    confidence="Medium",
))

_add("M_CONF_01", RedlineTemplate(
    issue="Perpetual / Indefinite Confidentiality",
    clause_category="Confidentiality",
    problem="The confidentiality obligation has no stated end date — it is perpetual or indefinite.",
    legal_rationale="An indefinite confidentiality obligation creates a permanent, unbounded "
                     "compliance burden with no clear point at which the obligation can be treated "
                     "as discharged.",
    business_impact="Perpetual obligations are difficult to track and audit over time, and create "
                     "long-tail risk with no natural expiration for record-retention and disclosure "
                     "controls.",
    recommended_change="Add a specific survival period for the confidentiality obligation following "
                        "termination or expiration of the Agreement.",
    suggested_redline="The obligations of confidentiality set forth in this Section shall survive "
                       "termination or expiration of this Agreement for a period of five (5) years.",
    why_this_wording="A five-year survival period is the most common term for general business "
                      "confidential information in commercial contracts — long enough to be "
                      "meaningful, short enough to be administrable.",
    expected_counterparty_position="Counterparty may want a shorter period (e.g. 2-3 years) or, for "
                                    "trade secrets specifically, may want no time limit at all "
                                    "carved back in.",
    negotiation_difficulty="Low",
    fallback_position="Accept a shorter period (2-3 years) for general Confidential Information "
                       "while carving out trade secrets for indefinite protection for as long as "
                       "they remain trade secrets under applicable law.",
    confidence="High",
))


# rule_ids with a reviewed template — the authoritative list callers should
# check before assuming a rule is covered.
COVERED_RULE_IDS = frozenset(_TEMPLATES.keys())

_PARTY_PLACEHOLDER_RE = re.compile(r"\{party_a\}|\{party_b\}")


def _substitute_variables(redline_text: str, metadata: Optional[Dict[str, Any]]) -> str:
    """Deterministic variable substitution ONLY — never LLM-generated
    text. Currently a no-op unless a template actually contains
    {party_a}/{party_b} placeholders (none of the initial COVERED_RULE_IDS
    templates do, since generic "each party"/"either party" phrasing is
    itself market-standard and safer than guessing which extracted name is
    even correct); this hook exists for future templates that do need
    named-party substitution, using metadata_extractor.py's already-
    extracted party names — never a guess invented at render time."""
    if not _PARTY_PLACEHOLDER_RE.search(redline_text):
        return redline_text
    parties = (metadata or {}).get("parties") or []
    party_a = parties[0]["short_name"] if len(parties) > 0 else "each party"
    party_b = parties[1]["short_name"] if len(parties) > 1 else "the other party"
    return redline_text.replace("{party_a}", party_a).replace("{party_b}", party_b)


def render_redline(finding: Any, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Combines a reviewed RedlineTemplate with an actual finding's
    dynamic data (severity, matched text, clause reference) into the full
    structured output. Returns None if this finding's rule_id has no
    reviewed template yet — callers must never fall back to generating
    one on the fly.

    `finding` is anything exposing rule_id, severity, exact_snippet (or
    matched_excerpt), clause_number — same attributes rules_engine.Finding
    already carries, or its dict serialization.
    """
    def _get(key: str, default: Any = None) -> Any:
        if isinstance(finding, dict):
            return finding.get(key, default)
        return getattr(finding, key, default)

    rule_id = _get("rule_id", "")
    template = _TEMPLATES.get(rule_id)
    if template is None:
        return None

    # Fact-aware gate: do not emit a one-sided consequential redline when
    # party-direction (or a reconciled Mutual title) already establishes mutuality.
    if rule_id == "H_CONSEQUENTIAL_01":
        pd = _get("party_direction") or {}
        mutuality = pd.get("mutuality_status") if isinstance(pd, dict) else None
        title = str(_get("title") or "")
        if mutuality == "mutual" or title.lower().startswith("mutual"):
            return None

    severity = _get("severity")
    severity_value = severity.value if hasattr(severity, "value") else str(severity)
    current_language = _get("exact_snippet") or _get("matched_excerpt") or ""

    return {
        "issue": template.issue,
        "clause": _get("clause_number") or "Not specified",
        "severity": severity_value,
        "current_language": current_language,
        "problem": template.problem,
        "legal_rationale": template.legal_rationale,
        "business_impact": template.business_impact,
        "recommended_change": template.recommended_change,
        "suggested_redline": _substitute_variables(template.suggested_redline, metadata),
        "why_this_wording": template.why_this_wording,
        "expected_counterparty_position": template.expected_counterparty_position,
        "negotiation_difficulty": template.negotiation_difficulty,
        "fallback_position": template.fallback_position,
        "confidence": template.confidence,
        "supporting_deterministic_rules": [rule_id],
    }
