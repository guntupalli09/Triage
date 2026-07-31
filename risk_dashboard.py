"""
Three-Score Risk Dashboard — Legal Risk / Business Risk / Negotiation
Difficulty. Product roadmap Feature 3 (see the TriageCounsel product memo,
Rev. 2): replaces a single blended "health score" with three independent
0-100 readings, because a contract can be legally low-risk but commercially
painful to renegotiate (or the reverse) — collapsing that distinction into
one number hides exactly the judgment call a reviewing partner needs to
make.

Deterministic and purely additive: this module adds no new detection. It is
a different aggregation of findings rules_engine.py already produced, in the
same spirit as rules_engine._compute_workflow_decision (signature_readiness)
— a second lens on the same underlying findings, not a replacement for
overall_risk/severity.

Method (documented here so a score is always traceable, never "the model
said so"):

1. Each finding's rule_id is tested against three keyword sets — LEGAL_RISK,
   BUSINESS_RISK, NEGOTIATION_DIFFICULTY (below). The same rule_id-substring
   approach main.py's _get_rule_category() already uses for the per-category
   pass/fail badges; this reuses that signal, aggregated differently. A
   finding can match zero, one, or more than one bucket (e.g. an uncapped
   personal-guaranty finding is naturally both a business-risk and a
   negotiation-difficulty signal).
2. Each matching finding contributes severity_weight points to that bucket:
   critical=25, high=12, medium=4, low=1.
3. A bucket's score is the sum of its matched findings' weights, capped at
   100.

A score of 0 means no matching findings were detected by this ruleset — it
is not by itself a certification that the clause is market-standard, only
that nothing in this category tripped a rule. This mirrors the same honesty
convention severity_scoring.py's _practical_max() documents about its own
known limitations: state the method plainly, including what it does not
claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

# Severity -> point weight when a finding matches a bucket's keyword set.
# Same tier ordering as rules_engine.Severity; not the severity_scoring.py
# WAS/factor framework (deliberately — that framework is frozen and scores a
# single finding in isolation, not a whole-document aggregate).
_SEVERITY_WEIGHT: Dict[str, int] = {"critical": 25, "high": 12, "medium": 4, "low": 1}
_SEVERITY_RANK: Dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# "Would this hold up, and is the contract enforceable as written" —
# governing law/venue conflicts, arbitration structure, regulatory and
# statutory exposure, missing required legal protections/representations.
LEGAL_RISK_KEYWORDS: Tuple[str, ...] = (
    "GOVLAW", "ARBITRATION", "JURISDICTION", "VENUE", "DATA_PRIVACY", "EXPORT_CTRL",
    "COMPLIANCE", "WAIVER", "INJUNCT", "EQUIT", "DPA_MISSING", "BAA_MISSING",
    "BREACH_NOTIFY", "CLASSIFICATION", "AUTHORITY_REP", "WARRANTY_DISCLAIM",
    "AI_TRAINING", "STARK_KICKBACK", "DCAA", "OCI_TERMINATION", "FLOWDOWN",
    "SANCTION", "CROSS_BORDER", "LICENSURE", "COUNTERPARTS_ESIGN",
    "EFFECTIVE_DATE_MISSING", "SIGNATURE", "EXHIBIT_MISSING",
)

# "How much money is actually at stake" — uncapped/asymmetric liability,
# indemnification, insurance, fees, pricing, billing, damages.
BUSINESS_RISK_KEYWORDS: Tuple[str, ...] = (
    "LOL", "LIAB", "CONSEQUENTIAL", "INDEM", "INSURANCE", "FEE", "PRICE",
    "PAYMENT", "BILLING", "INVOICE", "UNCAPPED", "DEDUCTIBLE", "ROYALTY",
    "GUARANTY", "RETAINAGE", "COMMIT", "DISCOUNT", "TAX", "CURRENCY",
    "EXPENSE", "DAMAGES", "PERSONAL", "CANCEL_FEE", "ESCROW", "SUBROGATION",
)

# "How hard is this to walk back across the table" — one-sided/unilateral
# rights, exclusivity, audit leverage, non-compete/non-solicit scope.
NEGOTIATION_DIFFICULTY_KEYWORDS: Tuple[str, ...] = (
    "UNILATERAL", "ONEWAY", "ONE_SIDED", "ASYMMETRIC", "NONCOMP", "NONSOLICIT",
    "CONVENIENCE", "EXCLUSIVE", "MFN", "AUDIT", "ENCROACHMENT", "TERRITORY",
    "NO_ACCOUNTING", "FORCED", "MANDATORY", "RESTRICT", "MIN_COMMIT",
    "CLASS_WAIVER", "ATWILL",
)


def _severity_of(finding: Any) -> str:
    sev = finding.severity
    return sev.value if hasattr(sev, "value") else str(sev)


def _rule_id_matches(rule_id: str, keywords: Tuple[str, ...]) -> bool:
    return any(kw in rule_id for kw in keywords)


@dataclass(frozen=True)
class ScoreBreakdown:
    score: int  # 0-100, capped
    matched_finding_count: int
    top_contributors: List[Dict[str, str]]  # most-severe-first, max 5: rule_id/title/severity


@dataclass(frozen=True)
class RiskDashboard:
    legal_risk: ScoreBreakdown
    business_risk: ScoreBreakdown
    negotiation_difficulty: ScoreBreakdown
    methodology_note: str = (
        "Each score is an independent 0-100 reading of THIS document's own findings, not a "
        "prediction or a comparison against other contracts. A finding counts toward a score "
        "when its rule matches that score's keyword set (a finding can count toward more than "
        "one score); severity weights critical=25/high=12/medium=4/low=1 are summed per score "
        "and capped at 100. A score of 0 means no matching findings were detected in this "
        "category — it does not by itself certify the clause is market-standard."
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "legal_risk_score": self.legal_risk.score,
            "business_risk_score": self.business_risk.score,
            "negotiation_difficulty_score": self.negotiation_difficulty.score,
            "legal_risk_contributors": self.legal_risk.top_contributors,
            "business_risk_contributors": self.business_risk.top_contributors,
            "negotiation_difficulty_contributors": self.negotiation_difficulty.top_contributors,
            "methodology_note": self.methodology_note,
        }


def _score_bucket(findings: Sequence[Any], keywords: Tuple[str, ...]) -> ScoreBreakdown:
    matched = [f for f in findings if _rule_id_matches(f.rule_id, keywords)]
    raw_points = sum(_SEVERITY_WEIGHT.get(_severity_of(f), 0) for f in matched)
    score = min(100, raw_points)

    matched_sorted = sorted(
        matched, key=lambda f: (_SEVERITY_RANK.get(_severity_of(f), 9), f.rule_id)
    )
    top_contributors = [
        {
            "rule_id": f.rule_id,
            "title": getattr(f, "title", f.rule_id),
            "severity": _severity_of(f),
        }
        for f in matched_sorted[:5]
    ]
    return ScoreBreakdown(score=score, matched_finding_count=len(matched), top_contributors=top_contributors)


def compute_risk_dashboard(findings: Sequence[Any]) -> RiskDashboard:
    """Pure function: List[Finding] -> RiskDashboard. Same input always
    produces the same output — no I/O, no randomness, nothing beyond
    arithmetic over attributes the findings already carry."""
    return RiskDashboard(
        legal_risk=_score_bucket(findings, LEGAL_RISK_KEYWORDS),
        business_risk=_score_bucket(findings, BUSINESS_RISK_KEYWORDS),
        negotiation_difficulty=_score_bucket(findings, NEGOTIATION_DIFFICULTY_KEYWORDS),
    )
