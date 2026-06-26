"""
Playbook Comparison Engine.

Compares an incoming contract's analysis against a pre-analyzed "standard" template
to surface deviations — clauses that are in the incoming contract but NOT in the
template (new risks), and clauses in the template but NOT in the incoming contract
(missing protections).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from rules_engine import RuleEngine, Finding


@dataclass
class Deviation:
    rule_id: str
    title: str
    severity: str
    deviation_type: str  # "added_risk" or "missing_protection"
    description: str
    incoming_excerpt: Optional[str] = None
    template_excerpt: Optional[str] = None


class PlaybookEngine:
    def __init__(self):
        self.rule_engine = RuleEngine()

    def compare(
        self,
        incoming_findings: List[Dict],
        template_findings: List[Dict],
    ) -> Dict:
        """
        Compare incoming contract findings against template findings.

        Returns:
        - added_risks: rules triggered in incoming but NOT in template
        - missing_protections: rules triggered in template but NOT in incoming
        - shared_findings: rules triggered in both
        - deviation_count: total deviations
        - deviation_summary: human-readable summary
        """
        incoming_rules = {f["rule_id"]: f for f in incoming_findings}
        template_rules = {f["rule_id"]: f for f in template_findings}

        incoming_ids = set(incoming_rules.keys())
        template_ids = set(template_rules.keys())

        added_risk_ids = incoming_ids - template_ids
        missing_protection_ids = template_ids - incoming_ids
        shared_ids = incoming_ids & template_ids

        deviations: List[Deviation] = []

        for rid in sorted(added_risk_ids):
            f = incoming_rules[rid]
            deviations.append(Deviation(
                rule_id=rid,
                title=f.get("title", rid),
                severity=f.get("severity", "medium"),
                deviation_type="added_risk",
                description=f"This contract triggers '{f.get('title', rid)}' which is NOT present in your standard template. This may represent additional risk beyond your baseline.",
                incoming_excerpt=f.get("matched_excerpt"),
            ))

        for rid in sorted(missing_protection_ids):
            f = template_rules[rid]
            deviations.append(Deviation(
                rule_id=rid,
                title=f.get("title", rid),
                severity=f.get("severity", "medium"),
                deviation_type="missing_protection",
                description=f"Your standard template triggers '{f.get('title', rid)}' but this contract does NOT. A protection or clause from your standard terms may be missing.",
                template_excerpt=f.get("matched_excerpt"),
            ))

        severity_order = {"high": 0, "medium": 1, "low": 2}
        deviations.sort(key=lambda d: (severity_order.get(d.severity, 9), d.deviation_type))

        shared = []
        for rid in sorted(shared_ids):
            inc = incoming_rules[rid]
            tmpl = template_rules[rid]
            severity_changed = inc.get("severity") != tmpl.get("severity")
            shared.append({
                "rule_id": rid,
                "title": inc.get("title", rid),
                "severity": inc.get("severity"),
                "template_severity": tmpl.get("severity"),
                "severity_changed": severity_changed,
            })

        return {
            "deviations": [
                {
                    "rule_id": d.rule_id,
                    "title": d.title,
                    "severity": d.severity,
                    "deviation_type": d.deviation_type,
                    "description": d.description,
                    "incoming_excerpt": d.incoming_excerpt,
                    "template_excerpt": d.template_excerpt,
                }
                for d in deviations
            ],
            "added_risks": [d for d in deviations if d.deviation_type == "added_risk"],
            "missing_protections": [d for d in deviations if d.deviation_type == "missing_protection"],
            "shared_findings": shared,
            "deviation_count": len(deviations),
            "added_risk_count": len(added_risk_ids),
            "missing_protection_count": len(missing_protection_ids),
        }
