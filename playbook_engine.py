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

    def to_dict(self) -> Dict[str, Optional[str]]:
        """The one explicit JSON representation of a Deviation.

        compare()'s result crosses a persistence boundary (it is written
        straight into Contract.deviations_json, an encrypted JSON column)
        and a template-rendering boundary. Before this existed, compare()
        returned raw dataclass instances under "added_risks"/
        "missing_protections", so any Playbook whose own template produced
        findings crashed the upload with
        `TypeError: Object of type Deviation is not JSON serializable`
        (UX walkthrough P0-4). Every field is listed explicitly — not
        `asdict()` and not `default=str` — so adding a field to the
        dataclass is a deliberate decision about what gets persisted and
        rendered, and nothing is silently stringified."""
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity,
            "deviation_type": self.deviation_type,
            "description": self.description,
            "incoming_excerpt": self.incoming_excerpt,
            "template_excerpt": self.template_excerpt,
        }


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

        # Every value below is JSON-serializable by construction: this dict
        # is persisted verbatim into Contract.deviations_json. Deviation
        # objects never leave this method (P0-4).
        return {
            "deviations": [d.to_dict() for d in deviations],
            "added_risks": [d.to_dict() for d in deviations if d.deviation_type == "added_risk"],
            "missing_protections": [d.to_dict() for d in deviations if d.deviation_type == "missing_protection"],
            "shared_findings": shared,
            "deviation_count": len(deviations),
            "added_risk_count": len(added_risk_ids),
            "missing_protection_count": len(missing_protection_ids),
        }
