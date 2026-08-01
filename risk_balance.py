"""
Risk Allocation & Clause Balance Score.

Product roadmap Feature 5 (see the product memo, Rev. 2): "is this
contract one-sided, and in whose favor" is the first question a negotiator
asks before a redline session. rules_engine.py already computes this
per-finding (see _build_perspective — every ONE_WAY_RULE_IDS/IP-assignment
finding gets a favorable/unfavorable/neutral/unclear label relative to the
reviewing party), it just never gets aggregated into a single number. This
module is that aggregation — no new detection, a different lens on data
the engine already produced, same posture as risk_dashboard.py.

Method: of the findings the engine could classify directionally
(favorable or unfavorable to the reviewing party — neutral/mutual and
unclear findings are excluded from the ratio itself, since they don't
represent a one-sided allocation either way, but their counts are still
reported for transparency), what fraction are unfavorable? 0 = every
directional clause favors the reviewing party; 50 = evenly split; 100 =
every directional clause favors the counterparty.

Applicability gate: if the engine could not classify ANY finding
directionally (no ONE_WAY_RULE_IDS findings fired, or all came back
"unclear"), there is nothing to aggregate — applicable=False, not a
misleading 0 or 50.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

_SEVERITY_RANK: Dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _severity_of(finding: Any) -> str:
    sev = getattr(finding, "severity", None)
    if sev is None:
        return "low"
    return sev.value if hasattr(sev, "value") else str(sev)


@dataclass(frozen=True)
class RiskBalanceReport:
    applicable: bool
    balance_score: Optional[int]  # 0-100: 0=entirely favors reviewer, 100=entirely favors counterparty
    favorable_count: int
    unfavorable_count: int
    neutral_count: int
    unclear_count: int
    top_unfavorable_contributors: List[Dict[str, str]]
    methodology_note: str = (
        "Aggregates the reviewing-party favorability already computed per finding (see "
        "rules_engine.py's _build_perspective) — no new detection. balance_score is the percentage "
        "of DIRECTIONAL findings (favorable + unfavorable to the reviewing party, default: customer) "
        "that are unfavorable; mutual/neutral and unclear findings are excluded from the ratio itself "
        "since they don't represent a one-sided allocation either way, but their counts are reported "
        "separately. Only covers rule families the engine already classifies directionally "
        "(ONE_WAY_RULE_IDS and IP-assignment clauses) — a contract with no directional findings shows "
        "applicable=False, not a misleading 0 or 50."
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "applicable": self.applicable,
            "balance_score": self.balance_score,
            "favorable_count": self.favorable_count,
            "unfavorable_count": self.unfavorable_count,
            "neutral_count": self.neutral_count,
            "unclear_count": self.unclear_count,
            "top_unfavorable_contributors": self.top_unfavorable_contributors,
            "methodology_note": self.methodology_note,
        }


def compute_risk_balance(findings: Sequence[Any]) -> RiskBalanceReport:
    """Pure function: List[Finding] -> RiskBalanceReport. Reads only the
    `perspective` attribute rules_engine.py already attaches to directional
    findings — computes nothing new."""
    favorable = unfavorable = neutral = unclear = 0
    unfavorable_findings: List[Any] = []

    for f in findings:
        perspective = getattr(f, "perspective", None)
        if not perspective:
            continue
        favorability = perspective.get("favorability")
        if favorability == "favorable":
            favorable += 1
        elif favorability == "unfavorable":
            unfavorable += 1
            unfavorable_findings.append(f)
        elif favorability == "neutral":
            neutral += 1
        elif favorability == "unclear":
            unclear += 1

    directional_total = favorable + unfavorable
    if directional_total == 0:
        return RiskBalanceReport(
            applicable=False, balance_score=None,
            favorable_count=favorable, unfavorable_count=unfavorable,
            neutral_count=neutral, unclear_count=unclear,
            top_unfavorable_contributors=[],
        )

    balance_score = round(100 * unfavorable / directional_total)

    top_sorted = sorted(
        unfavorable_findings, key=lambda f: (_SEVERITY_RANK.get(_severity_of(f), 9), f.rule_id)
    )
    top_contributors = [
        {"rule_id": f.rule_id, "title": getattr(f, "title", f.rule_id), "severity": _severity_of(f)}
        for f in top_sorted[:5]
    ]

    return RiskBalanceReport(
        applicable=True, balance_score=balance_score,
        favorable_count=favorable, unfavorable_count=unfavorable,
        neutral_count=neutral, unclear_count=unclear,
        top_unfavorable_contributors=top_contributors,
    )
