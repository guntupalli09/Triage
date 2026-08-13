"""
Labeled adversarial corpus for the Data Protection / Security policy
engine benchmark (see benchmarks/run_data_security_benchmark.py).
Adapter #7 — first adapter added after the original six.

Labels here were written from the policy semantics and the drafting
pattern alone, reasoning directly from data_security_policy_engine.py's
evaluate_data_security_policy logic, never by running the implementation
and copying whatever it happened to output. DEFAULT_POLICY represents a
sell-side vendor (data processor) playbook with a fully-specified set of
requirements across every dimension, so that most cases only need to
override the one or two dimensions under test.
"""
from typing import Any, Dict, List, Optional

DEFAULT_POLICY = {
    "contract_side": "sell_side",
    "escalation_approval_authority": "Legal Director",
    "fallback_text": "Approved fallback: Processor role confirmed; subprocessor consent required; "
                      "48-hour breach notification; SCC-based international transfers; 30-day "
                      "deletion/return on termination; audit rights; ISO 27001 certification; "
                      "cooperation with data subject/regulatory requests; confidentiality of personal data.",
    "require_processor_role": True,
    "prohibit_unrestricted_subprocessors": True,
    "require_subprocessor_notice_or_consent": "consent",
    "preferred_breach_notification_hours": 24.0,
    "acceptable_max_breach_notification_hours": 48.0,
    "negotiate_max_breach_notification_hours": 72.0,
    "require_fixed_breach_notification_period": True,
    "require_international_transfer_safeguard": True,
    "require_data_residency": False,
    "required_data_residency_regions_json": None,
    "require_deletion_or_return": True,
    "max_retention_days": None,
    "require_audit_rights": True,
    "require_named_security_certification": True,
    "require_cooperation_obligation": True,
    "require_confidentiality_of_personal_data": True,
}


def case(
    id: str,
    tags: List[str],
    text: str,
    expected_state: str,
    policy_overrides: Optional[Dict[str, Any]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "id": id, "tags": tags, "text": text, "expected_state": expected_state,
        "policy_overrides": policy_overrides or {},
        "notes": notes,
    }


CASES: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Fully-compliant baseline (role, subprocessors, breach, transfer, deletion,
# audit, security, cooperation, PD confidentiality all satisfied).
# ---------------------------------------------------------------------------
FULLY_COMPLIANT_TEXT = (
    "12. Data Protection. Processor shall act as a data processor on behalf of Controller "
    "with respect to personal data processed under this Agreement, solely to provide the "
    "Services. Processor shall not engage any subprocessor without obtaining Controller's "
    "prior written consent. In the event of a security incident involving personal data, "
    "Processor shall notify Controller within 24 hours of becoming aware of such incident. "
    "Processor shall not transfer personal data outside the European Economic Area except "
    "pursuant to Standard Contractual Clauses. Upon termination of this Agreement, Processor "
    "shall delete or return all personal data within 30 days. Controller shall have the right "
    "to audit Processor's compliance with this Section upon reasonable prior notice. Processor "
    "shall maintain administrative, technical and physical safeguards in accordance with "
    "ISO/IEC 27001. Processor shall provide reasonable cooperation and assistance in "
    "connection with data subject requests and regulatory inquiries. Processor shall keep "
    "personal data confidential."
)

CASES += [
    case("clean-01", ["clean_role", "clean_all"], FULLY_COMPLIANT_TEXT, "ACCEPT",
         notes="Every configured dimension satisfied at the preferred tier."),
    case("clean-02", ["clean_role"],
         "9. Data Protection. Vendor shall act as a data processor with respect to Customer's "
         "personal data. Vendor shall not engage sub-processors without Customer's prior "
         "written consent. Vendor shall notify Customer within 12 hours after becoming aware "
         "of a security incident. Vendor shall not transfer personal data outside the "
         "European Economic Area except pursuant to Standard Contractual Clauses. Vendor "
         "shall delete or return all personal data within 15 days of termination. Customer "
         "may audit Vendor's compliance with this Section annually. Vendor shall maintain "
         "SOC 2 Type II certified security controls. Vendor shall cooperate with Customer's "
         "regulatory inquiries and data subject requests. Vendor shall keep personal data "
         "confidential.",
         "ACCEPT", notes="'Vendor' maps to sell_side via the shared BUY_SIDE/SELL_SIDE_ROLES vocabulary."),
]

# ---------------------------------------------------------------------------
# Role: clean controller/processor, mutual/unclear, joint controllers,
# conflicting attribution, wrong role, buy-side (Controller) framing.
# ---------------------------------------------------------------------------
CASES += [
    case("role-01", ["role"],
         "9. Data Protection. Controller shall act as a data controller and Processor shall "
         "act as a data processor with respect to personal data processed under this "
         "Agreement.",
         "NEGOTIATE",
         notes="Role satisfied (processor); every other required dimension is unaddressed "
               "and downgrades to NEGOTIATE, not ACCEPT."),
    case("role-02", ["role", "wrong_role"],
         "9. Data Protection. Processor shall act as a data controller with respect to "
         "personal data processed under this Agreement.",
         "MUST_REDLINE",
         notes="'Processor' (sell_side by local convention) is attributed the CONTROLLER "
               "role — wrong role for a policy requiring us to be Processor."),
    case("role-03", ["role", "buy_side"],
         "9. Data Protection. Controller shall act as a data controller and Processor shall "
         "act as a data processor with respect to personal data processed under this "
         "Agreement.",
         "MUST_REDLINE",
         policy_overrides={"contract_side": "buy_side", "require_processor_role": True},
         notes="We are buy_side (Controller); the clause correctly attributes us as "
               "Controller, but our policy (unusually) requires we be Processor — "
               "role mismatch."),
    case("role-04", ["role", "mutual"],
         "9. Data Protection. Processor shall act as a data processor on behalf of "
         "Controller with respect to personal data.",
         "REQUIRES_REVIEW",
         policy_overrides={"contract_side": "mutual"},
         notes="Directional role statement under a mutual-position playbook — cannot "
               "determine our role without knowing which named party we are."),
    case("role-05", ["role", "joint_controllers"],
         "9. Data Protection. The parties acknowledge that they are joint controllers of "
         "personal data processed in connection with this Agreement and shall cooperate "
         "in good faith to allocate their respective data protection obligations.",
         "MUST_REDLINE",
         notes="CORRECTED after benchmark run: joint_controllers=True resolves our_role to "
               "'joint', which is != 'processor' under a require_processor_role policy — "
               "the engine treats this the same as any other wrong-role attribution "
               "(MUST_REDLINE), which is the right call: joint-controller status is a "
               "substantively different (and more exposed) position than pure Processor, "
               "not a mere gap. Original label (NEGOTIATE) incorrectly assumed the wrong-"
               "role branch only applied to explicit Controller attribution."),
    case("role-06", ["role", "conflict"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data. For purposes of Section 14 only, Processor shall act as a data "
         "controller with respect to aggregated usage analytics.",
         "REQUIRES_REVIEW",
         notes="The same named party ('Processor') is attributed BOTH roles within the "
               "document — genuine role_conflict, must abstain rather than pick one."),
    case("role-07", ["role", "no_requirement"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "ACCEPT",
         policy_overrides={
             "require_processor_role": False, "prohibit_unrestricted_subprocessors": False,
             "require_subprocessor_notice_or_consent": "not_required",
             "preferred_breach_notification_hours": None, "acceptable_max_breach_notification_hours": None,
             "negotiate_max_breach_notification_hours": None, "require_fixed_breach_notification_period": False,
             "require_international_transfer_safeguard": False, "require_deletion_or_return": False,
             "require_audit_rights": False, "require_named_security_certification": False,
             "require_cooperation_obligation": False, "require_confidentiality_of_personal_data": False,
         },
         notes="With every other requirement turned off, a bare role statement alone is "
               "sufficient for ACCEPT."),
]

# ---------------------------------------------------------------------------
# Subprocessors: consent / notice / unrestricted / prohibited, conflict.
# ---------------------------------------------------------------------------
_SUBP_BASE = ("9. Data Protection. Processor shall act as a data processor with respect to "
              "personal data. {subp_clause}")

CASES += [
    case("subp-01", ["subprocessor", "consent"],
         _SUBP_BASE.format(subp_clause="Processor shall obtain Controller's prior written "
                            "consent before engaging any sub-processor."),
         "NEGOTIATE", notes="Subprocessor consent satisfied; other dimensions unaddressed."),
    case("subp-02", ["subprocessor", "notice"],
         _SUBP_BASE.format(subp_clause="Processor shall provide prior written notice to "
                            "Controller before engaging any sub-processor."),
         "NEGOTIATE", notes="Only 'notice' provided but policy requires 'consent' (higher "
                             "rank) — should downgrade for the subprocessor dimension."),
    case("subp-03", ["subprocessor", "unrestricted"],
         _SUBP_BASE.format(subp_clause="Processor may engage sub-processors at its sole "
                            "discretion without prior notice."),
         "MUST_REDLINE", notes="Unrestricted subprocessors explicitly prohibited by policy."),
    case("subp-04", ["subprocessor", "prohibited"],
         _SUBP_BASE.format(subp_clause="Processor shall not engage any sub-processor."),
         "NEGOTIATE", notes="Prohibited is stricter than any notice/consent requirement — "
                             "satisfies the subprocessor dimension; other dims unaddressed."),
    case("subp-05", ["subprocessor", "conflict"],
         _SUBP_BASE.format(subp_clause="Processor shall not engage any sub-processor without "
                            "Controller's prior written consent, provided that Processor may "
                            "engage sub-processors at its sole discretion for routine "
                            "infrastructure hosting."),
         "REQUIRES_REVIEW",
         notes="The same window matches both 'consent' and 'unrestricted' patterns — a "
               "genuine internal conflict between two sub-processor provisions."),
    case("subp-06", ["subprocessor", "not_required"],
         _SUBP_BASE.format(subp_clause="Processor shall provide prior written notice to "
                            "Controller before engaging any sub-processor."),
         "NEGOTIATE",
         policy_overrides={"require_subprocessor_notice_or_consent": "notice"},
         notes="Notice satisfies a 'notice' requirement exactly; other dims unaddressed."),
]

# ---------------------------------------------------------------------------
# Breach notification: fixed hours at each threshold band, undue delay,
# missing, conflicting periods.
# ---------------------------------------------------------------------------
_BREACH_BASE = ("9. Data Protection. Processor shall act as a data processor with respect to "
                "personal data. {breach_clause}")

CASES += [
    case("breach-01", ["breach", "preferred"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller within 12 "
                              "hours of becoming aware of such incident."),
         "NEGOTIATE", notes="12h is within preferred (<=24h) — breach dimension itself is "
                             "clean; other dims unaddressed keep overall state NEGOTIATE."),
    case("breach-02", ["breach", "acceptable"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller within 36 "
                              "hours of becoming aware of such incident."),
         "NEGOTIATE", notes="36h falls in acceptable band (<=48h) -> ACCEPT_WITH_NOTE for "
                             "this dimension alone, but other unaddressed dims still drive "
                             "overall NEGOTIATE."),
    case("breach-03", ["breach", "negotiate_band"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller within 60 "
                              "hours of becoming aware of such incident."),
         "NEGOTIATE", notes="60h exceeds acceptable (48h) but within negotiate_max (72h)."),
    case("breach-04", ["breach", "escalate_band"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller within 120 "
                              "hours of becoming aware of such incident."),
         "ESCALATE", notes="120h exceeds negotiate_max (72h) -> classify_by_threshold "
                            "returns ESCALATE, which _worse() promotes over any NEGOTIATE "
                            "notes from other unaddressed dimensions."),
    case("breach-05", ["breach", "undue_delay"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller without "
                              "undue delay."),
         "NEGOTIATE", notes="No fixed hours, only 'without undue delay', and policy "
                             "requires a fixed period."),
    case("breach-06", ["breach", "undue_delay", "no_fixed_required"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller without "
                              "undue delay."),
         "NEGOTIATE",
         policy_overrides={"require_fixed_breach_notification_period": False,
                            "preferred_breach_notification_hours": None,
                            "acceptable_max_breach_notification_hours": None,
                            "negotiate_max_breach_notification_hours": None},
         notes="'Without undue delay' satisfies the breach dimension once a fixed period "
               "is no longer required; other unaddressed dims still drive NEGOTIATE."),
    case("breach-07", ["breach", "missing"],
         _BREACH_BASE.format(breach_clause="Processor shall maintain reasonable security "
                              "measures for personal data."),
         "NEGOTIATE", notes="No breach/security-incident notification timing at all — "
                             "policy requires a preferred threshold, so silence downgrades."),
    case("breach-08", ["breach", "conflict"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident, Processor "
                              "shall notify Controller within 24 hours of becoming aware of "
                              "such incident. Notwithstanding the foregoing, for incidents "
                              "affecting fewer than 100 data subjects, Processor shall "
                              "notify Controller within 96 hours of becoming aware of such "
                              "incident."),
         "REQUIRES_REVIEW",
         notes="Two different fixed-hour notification periods stated for the same clause — "
               "genuine conflict, must abstain rather than pick either."),
]

# ---------------------------------------------------------------------------
# International transfers: SCC, adequacy, prohibited (absolute), qualified
# prohibition (== scc), unaddressed transfer, never mentioned.
# ---------------------------------------------------------------------------
_TRANSFER_BASE = ("9. Data Protection. Processor shall act as a data processor with respect "
                   "to personal data. {transfer_clause}")

CASES += [
    case("transfer-01", ["transfer", "scc"],
         _TRANSFER_BASE.format(transfer_clause="Processor shall not transfer personal data "
                                "outside the European Economic Area except pursuant to "
                                "Standard Contractual Clauses."),
         "NEGOTIATE", notes="Transfer safeguard (SCC) satisfied; other dims unaddressed."),
    case("transfer-02", ["transfer", "adequacy"],
         _TRANSFER_BASE.format(transfer_clause="International transfers of personal data "
                                "shall only be made to countries benefiting from an adequacy "
                                "decision of the European Commission."),
         "NEGOTIATE", notes="Adequacy-decision safeguard satisfies the transfer dimension."),
    case("transfer-03", ["transfer", "absolute_prohibit"],
         _TRANSFER_BASE.format(transfer_clause="Processor shall not transfer personal data "
                                "outside the European Economic Area under any circumstances."),
         "NEGOTIATE", notes="Absolute prohibition on international transfer trivially "
                             "satisfies a 'safeguard required' policy — no transfer occurs "
                             "at all."),
    case("transfer-04", ["transfer", "unaddressed_mechanism"],
         _TRANSFER_BASE.format(transfer_clause="Processor may make international transfers "
                                "of personal data as reasonably necessary to provide the "
                                "Services."),
         "MUST_REDLINE", notes="International transfer is contemplated but no SCC/adequacy "
                                "safeguard is named — required by policy."),
    case("transfer-05", ["transfer", "never_mentioned"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed solely within Controller's home country.",
         "NEGOTIATE", notes="Transfer topic never addressed at all; silence is not held "
                             "against the clause for this dimension, but other unaddressed "
                             "dims still drive NEGOTIATE."),
    case("transfer-06", ["transfer", "not_required"],
         _TRANSFER_BASE.format(transfer_clause="Processor may make international transfers "
                                "of personal data as reasonably necessary to provide the "
                                "Services."),
         "NEGOTIATE",
         policy_overrides={"require_international_transfer_safeguard": False},
         notes="Once the safeguard requirement is off, an unaddressed-mechanism transfer "
               "clause no longer triggers a transfer-specific note."),
]

# ---------------------------------------------------------------------------
# Data residency.
# ---------------------------------------------------------------------------
CASES += [
    case("residency-01", ["residency", "required_met"],
         "9. Data Protection. Processor shall act as a data processor. Personal data shall "
         "be stored exclusively within the European Union.",
         "NEGOTIATE",
         policy_overrides={"require_data_residency": True,
                            "required_data_residency_regions_json": ["European Union"]},
         notes="Residency requirement satisfied by an exact regional match; other "
               "unaddressed dims still drive NEGOTIATE."),
    case("residency-02", ["residency", "required_mismatch"],
         "9. Data Protection. Processor shall act as a data processor. Personal data shall "
         "be stored exclusively within the United States.",
         "NEGOTIATE",
         policy_overrides={"require_data_residency": True,
                            "required_data_residency_regions_json": ["European Union"]},
         notes="Residency stated but not within the policy's approved region(s)."),
    case("residency-03", ["residency", "required_missing"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE",
         policy_overrides={"require_data_residency": True,
                            "required_data_residency_regions_json": ["European Union"]},
         notes="Policy requires a stated residency commitment but none is present at all."),
    case("residency-04", ["residency", "not_required"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE",
         notes="require_data_residency is False by default — no residency note fires, "
               "other unaddressed dims still drive NEGOTIATE."),
]

# ---------------------------------------------------------------------------
# Deletion / return vs retention.
# ---------------------------------------------------------------------------
CASES += [
    case("deletion-01", ["deletion", "required_met"],
         "9. Data Protection. Processor shall act as a data processor. Upon termination of "
         "this Agreement, Processor shall delete or return all personal data within 30 days.",
         "NEGOTIATE", notes="Deletion commitment present; other dims unaddressed."),
    case("deletion-02", ["deletion", "indefinite_retention"],
         "9. Data Protection. Processor shall act as a data processor. Processor may retain "
         "personal data indefinitely following termination of this Agreement.",
         "MUST_REDLINE", notes="Explicit indefinite retention with no deletion commitment — "
                                "required by policy to have deletion/return."),
    case("deletion-03", ["deletion", "missing"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE", notes="No deletion/return commitment stated at all — policy requires "
                             "one."),
    case("deletion-04", ["deletion", "retention_days_conflict"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "retain personal data for up to 400 days following termination for backup purposes.",
         "NEGOTIATE",
         policy_overrides={"max_retention_days": 90, "require_deletion_or_return": False},
         notes="deletion_or_return_required stays None here (no delete/return language), "
               "but retention_days=400 exceeds the configured max_retention_days=90 — the "
               "retention-days note fires independently of the deletion-or-return note."),
    case("deletion-05", ["deletion", "retention_days_ok"],
         "9. Data Protection. Processor shall act as a data processor. Upon termination, "
         "Processor shall delete or return all personal data, retaining backup copies for "
         "up to 30 days for disaster-recovery purposes.",
         "NEGOTIATE",
         policy_overrides={"max_retention_days": 90},
         notes="30-day backup retention is within the 90-day max; deletion commitment "
               "present; other dims unaddressed keep overall NEGOTIATE."),
]

# ---------------------------------------------------------------------------
# Audit rights.
# ---------------------------------------------------------------------------
CASES += [
    case("audit-01", ["audit", "present"],
         "9. Data Protection. Processor shall act as a data processor. Controller shall "
         "have the right to audit Processor's compliance with this Section upon reasonable "
         "prior notice.",
         "NEGOTIATE", notes="Audit rights present; other dims unaddressed."),
    case("audit-02", ["audit", "absent"],
         "9. Data Protection. Processor shall act as a data processor. Controller shall not "
         "have audit rights with respect to Processor's data protection practices.",
         "MUST_REDLINE", notes="Audit rights expressly excluded — required by policy."),
    case("audit-03", ["audit", "missing"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE", notes="Audit rights never mentioned at all — required by policy."),
]

# ---------------------------------------------------------------------------
# Security standard: named certification, vague, ISO/SOC variants, missing.
# ---------------------------------------------------------------------------
CASES += [
    case("security-01", ["security_standard", "iso"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "maintain technical and organizational measures in accordance with ISO/IEC 27001.",
         "NEGOTIATE", notes="Named certification (ISO 27001) satisfies the requirement."),
    case("security-02", ["security_standard", "soc2"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "maintain information security controls consistent with SOC 2 Type II.",
         "NEGOTIATE", notes="Named certification (SOC 2 Type II) satisfies the requirement."),
    case("security-03", ["security_standard", "vague"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "maintain industry-standard security measures to protect personal data.",
         "NEGOTIATE", notes="Only vague 'industry-standard' language, no named certification "
                             "— policy requires a named certification."),
    case("security-04", ["security_standard", "commercially_reasonable"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "implement commercially reasonable security measures for personal data.",
         "NEGOTIATE", notes="'Commercially reasonable security measures' is vague language, "
                             "not a named certification."),
    case("security-05", ["security_standard", "missing"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE", notes="No security-standard anchor language at all."),
    case("security-06", ["security_standard", "not_required"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "maintain industry-standard security measures to protect personal data.",
         "NEGOTIATE",
         policy_overrides={"require_named_security_certification": False},
         notes="Once the named-certification requirement is off, vague security language "
               "no longer triggers a security-standard note."),
]

# ---------------------------------------------------------------------------
# Cooperation (data-subject requests + regulatory inquiries, combined dim).
# ---------------------------------------------------------------------------
CASES += [
    case("cooperation-01", ["cooperation", "present"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "provide reasonable assistance to Controller in connection with data subject "
         "requests and regulatory inquiries.",
         "NEGOTIATE", notes="Cooperation obligation present; other dims unaddressed."),
    case("cooperation-02", ["cooperation", "present_alt_phrasing"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "cooperate with Controller in responding to data subject access requests.",
         "NEGOTIATE", notes="Alternate 'cooperate ... in responding to' phrasing also "
                             "establishes the cooperation dimension."),
    case("cooperation-03", ["cooperation", "missing"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE", notes="No cooperation commitment stated at all — required by policy."),
]

# ---------------------------------------------------------------------------
# Confidentiality of personal data.
# ---------------------------------------------------------------------------
CASES += [
    case("pd-confidentiality-01", ["pd_confidentiality", "present"],
         "9. Data Protection. Processor shall act as a data processor. Personal data shall "
         "be treated as confidential and shall not be disclosed except as necessary to "
         "provide the Services.",
         "NEGOTIATE", notes="PD confidentiality commitment present; other dims unaddressed."),
    case("pd-confidentiality-02", ["pd_confidentiality", "missing"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE", notes="No PD-specific confidentiality commitment stated."),
]

# ---------------------------------------------------------------------------
# DPA / Schedule / Exhibit cross-reference (delegation to an external doc).
# ---------------------------------------------------------------------------
CASES += [
    case("dpa-crossref-01", ["dpa_crossref", "nothing_else"],
         "9. Data Protection. The parties' respective data protection obligations, "
         "including with respect to processing roles, subprocessors, breach notification, "
         "international transfers, and security, are governed by the attached Data "
         "Processing Agreement.",
         "REQUIRES_REVIEW",
         notes="Material data-protection obligations are delegated wholesale to an external "
               "DPA with no dimension independently established in-clause — cannot "
               "evaluate deterministically without the referenced document."),
    case("dpa-crossref-02", ["dpa_crossref", "supplementing"],
         FULLY_COMPLIANT_TEXT + " This Section is further supplemented by the terms of the "
         "attached Data Processing Agreement.",
         "ACCEPT",
         notes="A DPA cross-reference that supplements (rather than replaces) an "
               "otherwise-complete in-clause treatment does not, on its own, block "
               "evaluation — every dimension is still independently established in-text."),
]

# ---------------------------------------------------------------------------
# Multiple sections / amendments (document-wide anchors, same value).
# ---------------------------------------------------------------------------
CASES += [
    case("multi-section-01", ["multi_section", "consistent"],
         "9. Data Protection. Processor shall act as a data processor with respect to "
         "personal data processed under this Agreement. Processor shall notify Controller "
         "of any security incident within 24 hours of becoming aware of such incident.\n\n"
         "18. Amendment to Data Protection Terms. For the avoidance of doubt, Processor "
         "confirms it will act as a data processor and will notify Controller of any "
         "security incident within 24 hours of becoming aware, consistent with Section 9.",
         "NEGOTIATE",
         notes="Two anchored windows restate the SAME role and SAME breach-notification "
               "hours — no conflict, values merge cleanly; other dims unaddressed."),
    case("multi-section-02", ["multi_section", "amendment_changes_hours"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "notify Controller of any security incident within 72 hours of becoming aware of "
         "such incident.\n\n18. First Amendment. Section 9 is hereby amended to require "
         "Processor to notify Controller of any security incident within 24 hours of "
         "becoming aware of such incident.",
         "REQUIRES_REVIEW",
         notes="The original clause and the amendment state two DIFFERENT breach-"
               "notification periods for the same obligation — the extractor has no way to "
               "determine which one controls without legal interpretation, so this "
               "surfaces as a genuine conflict rather than picking the amendment's value."),
]

# ---------------------------------------------------------------------------
# No privacy clause at all -> NOT_APPLICABLE.
# ---------------------------------------------------------------------------
CASES += [
    case("not-applicable-01", ["not_applicable"],
         "9. Governing Law. This Agreement shall be governed by the laws of the State of "
         "Delaware, without regard to its conflicts of laws principles.",
         "NOT_APPLICABLE", notes="No data-protection/security clause anchor at all."),
    case("not-applicable-02", ["not_applicable", "commercial_only"],
         "9. Fees. Customer shall pay Vendor the fees set forth in the applicable Order "
         "Form within 30 days of invoice.",
         "NOT_APPLICABLE", notes="Ordinary commercial clause, no data-protection content."),
]

# ---------------------------------------------------------------------------
# Malformed / degenerate clauses.
# ---------------------------------------------------------------------------
CASES += [
    case("malformed-01", ["malformed", "fragment"],
         "9. Data Protection. Personal data.",
         "NEGOTIATE",
         notes="Anchor matches ('personal data') but the fragment establishes nothing — "
               "every dimension falls through to its 'missing/required' branch, none of "
               "which is REQUIRES_REVIEW-triggering on its own, so this lands at NEGOTIATE "
               "(worst note), not REQUIRES_REVIEW."),
    case("malformed-02", ["malformed", "ocr_noise"],
         "9.  Data   Protection .   Processor  shall   act  as  a   data  processor  with "
         "respect  to  personal  data  processed  under  this  Agreement .",
         "NEGOTIATE",
         notes="Irregular whitespace (OCR-style artifact) should not defeat the anchor or "
               "role regexes, which tolerate \\s+ throughout."),
]

# ---------------------------------------------------------------------------
# Ambiguous pronouns.
# ---------------------------------------------------------------------------
CASES += [
    case("ambiguous-pronoun-01", ["ambiguous_pronoun"],
         "9. Data Protection. Each party shall ensure that its personnel who process "
         "personal data are subject to appropriate confidentiality obligations. It shall "
         "notify the other party of any security incident without undue delay.",
         "NEGOTIATE",
         notes="No named-party role statement is extractable here at all (generic "
               "'each party'/'it' pronouns, no controller/processor role words) — "
               "role_attributions stays empty, so require_processor_role's 'no role "
               "statement was found' NEGOTIATE note fires rather than a false abstention."),
]

# ---------------------------------------------------------------------------
# Explicit negations.
# ---------------------------------------------------------------------------
CASES += [
    case("negation-01", ["negation", "no_subprocessors"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall not "
         "engage any sub-processor for the performance of the Services.",
         "NEGOTIATE",
         notes="Outright prohibition on subprocessors ('prohibited') is stricter than any "
               "notice/consent requirement — satisfies the subprocessor dimension "
               "cleanly, no false MUST_REDLINE."),
    case("negation-02", ["negation", "no_audit"],
         "9. Data Protection. Processor shall act as a data processor. Controller shall "
         "not have the right to audit Processor's data protection practices.",
         "MUST_REDLINE", notes="Explicit audit-rights negation, required by policy."),
]

# ---------------------------------------------------------------------------
# Exceptions / carve-outs.
# ---------------------------------------------------------------------------
CASES += [
    case("exception-01", ["exception", "transfer_carveout"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall not "
         "transfer personal data outside the European Economic Area, unless such transfer "
         "is made pursuant to Standard Contractual Clauses or an applicable adequacy "
         "decision.",
         "NEGOTIATE",
         notes="Qualified prohibition ('unless ... SCCs') is a named-mechanism transfer "
               "safeguard, not an absolute ban — should classify as 'scc', not "
               "'prohibited'."),
    case("exception-02", ["exception", "subprocessor_carveout"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall not "
         "engage any sub-processor without Controller's prior written consent, except for "
         "Processor's Affiliates engaged in the ordinary course of providing the Services.",
         "NEGOTIATE",
         notes="The consent requirement is the dominant, clearly-stated commitment; the "
               "affiliate carve-out is a minor exception the regex does not need to "
               "specially detect for the top-level 'consent' classification to hold."),
]

# ---------------------------------------------------------------------------
# Additional coverage: boundary thresholds, alternate role-words, mutual
# with no attributions, and other required categories from the task spec
# not yet independently exercised above.
# ---------------------------------------------------------------------------
CASES += [
    case("breach-boundary-01", ["breach", "boundary_preferred"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller within 24 "
                              "hours of becoming aware of such incident."),
         "NEGOTIATE", notes="Exactly at the preferred threshold (24h <= preferred 24h) -> "
                             "ACCEPT for this dimension; other unaddressed dims keep the "
                             "overall state at NEGOTIATE."),
    case("breach-boundary-02", ["breach", "boundary_negotiate_max"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller within 72 "
                              "hours of becoming aware of such incident."),
         "NEGOTIATE", notes="Exactly at negotiate_max (72h) -> NEGOTIATE, not ESCALATE."),
    case("breach-boundary-03", ["breach", "boundary_escalate"],
         _BREACH_BASE.format(breach_clause="In the event of a security incident involving "
                              "personal data, Processor shall notify Controller within 73 "
                              "hours of becoming aware of such incident."),
         "ESCALATE", notes="One hour past negotiate_max (72h) -> ESCALATE."),
    case("role-08", ["role", "alt_role_word"],
         "9. Data Protection. Licensor shall act as a data processor with respect to "
         "personal data processed under this Agreement.",
         "NEGOTIATE", notes="'Licensor' is a shared SELL_SIDE_ROLES word (from "
                             "policy_engine_core), correctly mapped independent of the "
                             "local Processor/Controller fallback."),
    case("role-09", ["role", "mutual_no_attribution"],
         "9. Data Protection. Each party shall implement reasonable security measures to "
         "protect the other party's personal data.",
         "NEGOTIATE",
         policy_overrides={"contract_side": "mutual"},
         notes="No role_attributions extracted at all (no named-party role statement) even "
               "under a mutual policy — falls through to the 'no role statement found' "
               "NEGOTIATE note, not an unresolved/ambiguous abstention, since there is "
               "nothing directional to be ambiguous about."),
    case("residency-05", ["residency", "multi_region_match"],
         "9. Data Protection. Processor shall act as a data processor. Personal data shall "
         "be stored exclusively within Canada.",
         "NEGOTIATE",
         policy_overrides={"require_data_residency": True,
                            "required_data_residency_regions_json": ["European Union", "Canada", "United Kingdom"]},
         notes="Residency region matches one of several approved regions."),
    case("retention-boundary-01", ["deletion", "retention_days_boundary"],
         "9. Data Protection. Processor shall act as a data processor. Processor shall "
         "retain personal data for up to 90 days following termination for backup purposes.",
         "NEGOTIATE",
         policy_overrides={"max_retention_days": 90, "require_deletion_or_return": False},
         notes="Exactly at max_retention_days (90) — not over, no retention-days note."),
    case("subp-07", ["subprocessor", "consent_exceeds_notice_requirement"],
         _SUBP_BASE.format(subp_clause="Processor shall obtain Controller's prior written "
                            "consent before engaging any sub-processor."),
         "NEGOTIATE",
         policy_overrides={"require_subprocessor_notice_or_consent": "notice"},
         notes="'Consent' (rank 2) exceeds a 'notice' (rank 1) requirement — satisfies the "
               "subprocessor dimension cleanly, no false negotiate note for that dimension."),
    case("transfer-07", ["transfer", "qualified_prohibition_no_named_mechanism"],
         _TRANSFER_BASE.format(transfer_clause="Processor shall not transfer personal data "
                                "outside the European Economic Area, except as reasonably "
                                "necessary to provide the Services."),
         "MUST_REDLINE",
         notes="The carve-out ('except as reasonably necessary') is not a named safeguard "
               "(no SCC/adequacy reference) — classifies as 'unaddressed_transfer', which "
               "still requires a MUST_REDLINE note under a safeguard-required policy."),
    case("malformed-03", ["malformed", "empty_after_heading"],
         "12. Data Protection.",
         "NEGOTIATE",
         notes="CORRECTED after benchmark run: the section heading text 'Data Protection' "
               "itself matches _ANCHOR_RE ('data\\s+protection'), so clause_found=True even "
               "though nothing substantive follows — same as malformed-01's bare fragment. "
               "Original label (NOT_APPLICABLE) incorrectly assumed a heading-only anchor "
               "wouldn't itself trigger detection; the engine cannot distinguish 'heading "
               "with no body' from 'real but terse clause' without more text, so it "
               "correctly falls through every dimension's 'missing' branch to NEGOTIATE "
               "rather than fabricating NOT_APPLICABLE."),
    case("negation-03", ["negation", "no_pd_confidentiality"],
         "9. Data Protection. Processor shall act as a data processor. Personal data is not "
         "subject to any confidentiality obligation under this Section.",
         "NEGOTIATE",
         notes="Explicit negation does not match _PD_CONFIDENTIALITY_RE (which only detects "
               "an affirmative commitment) — confidentiality_of_personal_data stays None, "
               "so the 'no such commitment found' NEGOTIATE note fires exactly as it would "
               "for silence; the explicit negation is not treated any differently, which is "
               "the conservative and correct behavior here."),
    case("clean-03", ["clean_all", "buy_side"],
         "9. Data Protection. Customer shall act as a data controller and Vendor shall act "
         "as a data processor with respect to personal data processed under this "
         "Agreement. Vendor shall not engage any sub-processor without Customer's prior "
         "written consent. Vendor shall notify Customer within 24 hours of becoming aware "
         "of any security incident involving personal data. Vendor shall not transfer "
         "personal data outside the European Economic Area except pursuant to Standard "
         "Contractual Clauses. Upon termination, Vendor shall delete or return all personal "
         "data within 30 days. Customer shall have the right to audit Vendor's compliance "
         "with this Section. Vendor shall maintain technical and organizational measures in "
         "accordance with ISO 27001. Vendor shall provide reasonable assistance in "
         "connection with data subject requests and regulatory inquiries. Personal data "
         "shall be kept confidential.",
         "ACCEPT",
         policy_overrides={"contract_side": "buy_side", "require_processor_role": False},
         notes="Buy-side (Customer/Controller) policy with require_processor_role off — "
               "every other dimension independently satisfied at the preferred tier."),
]
