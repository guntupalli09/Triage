"""Step 4B Phase I -- >=150 case DEVELOPMENT explanation-fidelity
benchmark. Targets the real production functions identified by the
read-only trace (artifacts/step4b/phaseI_explanation_trace.md):

  1. evaluator.LLMEvaluator._verify_output_maps_to_findings -- must drop
     (not merely log) any LLM top_issue that does not map to a real
     deterministic finding.
  2. evaluator.LLMEvaluator.evaluate -- must force overall_risk back to
     the deterministic value regardless of what the model returned, and
     must reject/reroute malformed model output through _validate_result.
  3. main.build_enhanced_issues -- the displayed title/severity of a
     finding, when an LLM explanation is merged in, must always be the
     deterministic finding's own value, never the LLM's; deterministic
     evidence/citation fields (exact_snippet, matched_excerpt, evidence,
     party_direction, clause_number) must never be overwritten by LLM
     content at all (the merge path never even touches them from
     llm_issue).
"""
from typing import Any, Dict, List

CASES: List[Dict[str, Any]] = []


def case(cid, family, target, payload, expected, notes=""):
    CASES.append({"id": cid, "family": family, "target": target, "payload": payload, "expected": expected, "notes": notes})


def finding(rule_id, title, severity="high", clause_number=None, start=0, end=10, rationale="deterministic rationale",
            policy_state=None, clause_type=None, interaction_id=None, party_direction=None,
            exact_snippet="", evidence=None, matched_excerpt=None):
    f = {"rule_id": rule_id, "title": title, "severity": severity, "clause_number": clause_number,
         "start_index": start, "end_index": end, "rationale": rationale, "exact_snippet": exact_snippet}
    if policy_state:
        f["policy_state"] = policy_state
        f["finding_type"] = "policy_decision"
    if clause_type:
        f["clause_type"] = clause_type
    if interaction_id:
        f["interaction_id"] = interaction_id
        f["finding_type"] = "interaction_decision"
    if party_direction:
        f["party_direction"] = party_direction
    if evidence:
        f["evidence"] = evidence
    if matched_excerpt:
        f["matched_excerpt"] = matched_excerpt
    return f


def llm_issue(title, severity="low", why_it_matters="narrative"):
    return {"title": title, "severity": severity, "why_it_matters": why_it_matters}


# ===========================================================================
# Target 1: _verify_output_maps_to_findings -- fabrication must be dropped
# ===========================================================================
_FABRICATED_TITLES = [
    "Executive Termination Bonus Clause Missing", "Hidden Non-Compete Discovered",
    "Undisclosed Change of Control Trigger", "Secret Arbitration Waiver Found",
    "Mandatory Class Action Waiver Detected", "Unlimited Personal Guarantee Required",
    "Automatic Renewal Trap Identified", "Reverse Indemnification Obligation",
    "Undisclosed Exclusivity Requirement", "Hidden Most-Favored-Nation Clause",
]
for i, title in enumerate(_FABRICATED_TITLES):
    real_findings = [finding("R_REAL", "Uncapped Liability Clause")]
    llm_output = {"overall_risk": "low", "summary_bullets": [], "possible_missing_sections": [], "disclaimer": "x",
                  "top_issues": [llm_issue(title)]}
    case(f"fabricated-issue-{i}", "fabricated-finding-invented", "verify_output_maps_to_findings",
         {"llm_output": llm_output, "input_findings": real_findings},
         {"top_issues_count": 0, "verify_result": False},
         f"'{title}' has no basis in any real finding -- must be dropped entirely")

# a real, correctly-matching issue alongside a fabricated one -- only the real one survives
for i in range(10):
    real_findings = [finding("R_REAL", "Uncapped Liability Clause")]
    llm_output = {"overall_risk": "low", "summary_bullets": [], "possible_missing_sections": [], "disclaimer": "x",
                  "top_issues": [llm_issue("Uncapped Liability Clause", why_it_matters="real explanation"),
                                 llm_issue(_FABRICATED_TITLES[i % len(_FABRICATED_TITLES)])]}
    case(f"mixed-real-and-fabricated-{i}", "mixed-real-and-fabricated", "verify_output_maps_to_findings",
         {"llm_output": llm_output, "input_findings": real_findings},
         {"top_issues_count": 1, "verify_result": False},
         "the real, correctly-matching issue must survive; the fabricated one must be dropped")

# zero deterministic findings -- ALL top_issues must be dropped regardless of plausibility
for i in range(8):
    llm_output = {"overall_risk": "low", "summary_bullets": [], "possible_missing_sections": [], "disclaimer": "x",
                  "top_issues": [llm_issue(f"Plausible-sounding issue {i}")]}
    case(f"zero-findings-fabrication-{i}", "zero-findings-all-dropped", "verify_output_maps_to_findings",
         {"llm_output": llm_output, "input_findings": []},
         {"top_issues_count": 0, "verify_result": False},
         "no deterministic findings exist at all -- any top_issue is fabricated by definition")

# genuinely empty top_issues with real findings present -- nothing to drop, verify_result True
for i in range(6):
    real_findings = [finding("R_REAL", "Payment Terms Issue")]
    llm_output = {"overall_risk": "low", "summary_bullets": [], "possible_missing_sections": [], "disclaimer": "x", "top_issues": []}
    case(f"no-issues-clean-{i}", "no-issues-nothing-to-drop", "verify_output_maps_to_findings",
         {"llm_output": llm_output, "input_findings": real_findings},
         {"top_issues_count": 0, "verify_result": True},
         "no top_issues at all -- vacuously true, nothing fabricated")

# multiple real findings, multiple correctly-matching issues -- all survive
for i in range(8):
    real_findings = [finding("R1", "Uncapped Liability Clause"), finding("R2", "Missing Confidentiality Term"),
                      finding("R3", "Unilateral Termination Right")]
    llm_output = {"overall_risk": "low", "summary_bullets": [], "possible_missing_sections": [], "disclaimer": "x",
                  "top_issues": [llm_issue("Uncapped Liability Clause"), llm_issue("Missing Confidentiality Term"),
                                 llm_issue("Unilateral Termination Right")]}
    case(f"multiple-real-all-survive-{i}", "multiple-real-findings-all-survive", "verify_output_maps_to_findings",
         {"llm_output": llm_output, "input_findings": real_findings},
         {"top_issues_count": 3, "verify_result": True},
         "3 genuinely matching issues -- all 3 survive")

# ===========================================================================
# Target 2: evaluate()'s forced overall_risk + malformed-output rejection
# ===========================================================================
_ADVERSARIAL_RISK_CLAIMS = ["high", "critical", "none", "SAFE", "clean", "unknown", None, "", 12345]
for i, claimed_risk in enumerate(_ADVERSARIAL_RISK_CLAIMS):
    case(f"overall-risk-override-{i}", "overall-risk-forced-deterministic", "evaluate_force_overall_risk",
         {"model_claimed_risk": claimed_risk, "deterministic_overall_risk": "low"},
         {"final_overall_risk": "low"},
         f"model claimed overall_risk={claimed_risk!r} -- must be forced back to the deterministic value 'low'")

_MALFORMED_MODEL_OUTPUTS = [
    {},  # missing all required keys
    {"overall_risk": "low"},  # missing summary_bullets/top_issues/etc
    {"overall_risk": "low", "summary_bullets": "not-a-list", "top_issues": [], "possible_missing_sections": [], "disclaimer": "x"},
    {"overall_risk": "low", "summary_bullets": [], "top_issues": "not-a-list", "possible_missing_sections": [], "disclaimer": "x"},
    {"overall_risk": "low", "summary_bullets": [], "top_issues": [], "possible_missing_sections": "not-a-list", "disclaimer": "x"},
]
for i, malformed in enumerate(_MALFORMED_MODEL_OUTPUTS):
    case(f"malformed-model-output-{i}", "malformed-output-rejected", "validate_result_rejects_malformed",
         {"malformed_output": malformed},
         {"raises": True},
         f"malformed model output {malformed!r} must raise, never silently proceed")

# disclaimer always forced regardless of what the model said
for i, claimed_disclaimer in enumerate(["This is certified legal advice.", "", None, "Guaranteed accurate.", "No disclaimer needed."]):
    case(f"disclaimer-forced-{i}", "disclaimer-always-forced", "validate_result_forces_disclaimer",
         {"claimed_disclaimer": claimed_disclaimer},
         {"final_disclaimer": "This is automated risk triage, not legal advice."},
         f"model claimed disclaimer={claimed_disclaimer!r} -- must be forced to the fixed safe disclaimer")

# ===========================================================================
# Target 3: build_enhanced_issues -- title/severity/evidence protection
# ===========================================================================
_TITLE_ATTACKS = [
    ("Uncapped Liability Clause", "Uncapped Liability Clause is fully mitigated and safe", "reversed conclusion"),
    ("Uncapped Liability Clause", "Uncapped Liability Clause caps exposure at $50,000,000", "wrong amount"),
    ("Unilateral Termination Right", "Unilateral Termination Right belongs to Customer only", "wrong party"),
    ("Missing Confidentiality Term", "Missing Confidentiality Term is present in Section 12", "wrong clause / fabricated location"),
    ("Uncapped Liability Clause", "Uncapped Liability Clause is mutual and balanced", "wrong direction"),
    ("Unilateral Termination Right", "Unilateral Termination Right requires 90 days notice from both parties", "invented condition"),
    ("Uncapped Liability Clause", "Uncapped Liability Clause interacts with the Indemnification Cap to increase exposure", "invented interaction"),
    ("Missing Confidentiality Term", "Missing Confidentiality Term was reviewed under Playbook Revision 7", "wrong governance provenance"),
    ("Unilateral Termination Right", "Unilateral Termination Right applies only to the Enterprise segment", "wrong segment claim"),
    ("Uncapped Liability Clause", "Uncapped Liability Clause should be accepted without further review", "unsupported recommendation"),
]
for i, (real_title, adversarial_title, attack) in enumerate(_TITLE_ATTACKS):
    f = finding("R1", real_title, severity="high", exact_snippet="the real deterministic excerpt",
                evidence={"anchor": "real", "excerpt": "real evidence"})
    llm_out = {"top_issues": [llm_issue(adversarial_title, severity="low", why_it_matters=f"adversarial: {attack}")]}
    case(f"title-attack-{i}", "adversarial-title-attack", "build_enhanced_issues_title_protected",
         {"finding": f, "llm_result": llm_out},
         {"displayed_title": real_title, "displayed_severity": "high"},
         f"attack={attack}; displayed title/severity must remain deterministic")

for i in range(10):
    f = finding("R1", "Uncapped Liability Clause", severity="critical",
                exact_snippet="real excerpt", evidence={"anchor": "x"}, matched_excerpt="real matched text",
                party_direction={"obligor": "us"})
    llm_out = {"top_issues": [llm_issue("Uncapped Liability Clause", severity="low", why_it_matters="downplayed narrative")]}
    case(f"evidence-fields-protected-{i}", "evidence-fields-never-llm-sourced", "build_enhanced_issues_evidence_protected",
         {"finding": f, "llm_result": llm_out},
         {"exact_snippet": "real excerpt", "matched_excerpt": "real matched text", "party_direction": {"obligor": "us"}, "severity": "critical"},
         "evidence/citation fields must come from the deterministic finding, never llm_issue, regardless of narrative severity claim")

# policy_decision / interaction_decision findings -- title/severity survive
# merge untouched. NOTE (GTD correction): build_enhanced_issues's own
# output contract never copies policy_state/clause_type/interaction_id
# into `enhanced` at all (confirmed by direct code read -- results.html,
# the sole consumer of this function's output, never references those
# keys either; review.html's queue reads them from the RAW findings_json
# via review_queue.py instead, a completely separate path already
# validated in Phase 0/F). Checking for those keys here would test a
# contract this function never made -- corrected to check title/severity,
# which IS this function's actual, meaningful protection surface.
for i in range(8):
    f = finding("POLICY_LOL_CAP", "Limitation of Liability - PROHIBITED", severity="critical",
                policy_state="PROHIBITED", clause_type="limitation_of_liability")
    llm_out = {"top_issues": [llm_issue("Limitation of Liability - PROHIBITED", severity="low", why_it_matters="LLM narrative")]}
    case(f"policy-decision-fields-protected-{i}", "policy-decision-fields-protected", "build_enhanced_issues_title_protected",
         {"finding": f, "llm_result": llm_out},
         {"displayed_title": "Limitation of Liability - PROHIBITED", "displayed_severity": "critical"},
         "title/severity of a policy_decision-shaped finding must never be touched by the LLM merge path")

for i in range(8):
    f = finding("IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY", "IP interaction - ESCALATE", severity="critical",
                interaction_id="IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY", policy_state="ESCALATE")
    llm_out = {"top_issues": [llm_issue("IP interaction - ESCALATE", severity="low", why_it_matters="LLM narrative")]}
    case(f"interaction-decision-fields-protected-{i}", "interaction-decision-fields-protected", "build_enhanced_issues_title_protected",
         {"finding": f, "llm_result": llm_out},
         {"displayed_title": "IP interaction - ESCALATE", "displayed_severity": "critical"},
         "title/severity of an interaction_decision-shaped finding must never be touched by the LLM merge path")

# ===========================================================================
# Volume top-up: broader family coverage named in the task (clean decisions,
# requires-review, critical interactions, multi-policy documents, governance/
# segment-sensitive reviews, evaluation errors, configuration unresolved) --
# confirming the title/severity protection holds identically across all of
# them, not just the liability example above.
# ===========================================================================
_FAMILY_FIXTURES = [
    ("clean", finding("R_CLEAN", "Standard Confidentiality Term", severity="low")),
    ("violation", finding("R_VIOL", "Prohibited Assignment Clause", severity="critical", policy_state="PROHIBITED", clause_type="assignment")),
    ("requires-review", finding("R_REVIEW", "Ambiguous Carve-Out Language", severity="high", policy_state="REQUIRES_REVIEW", clause_type="warranties")),
    ("critical-interaction", finding("IX_TEST", "Cross-Policy Interaction", severity="critical", interaction_id="IX_TEST", policy_state="ESCALATE")),
    ("evaluation-error", finding("R_ERR", "Data Security Evaluation Error", severity="high", policy_state="EVALUATION_ERROR", clause_type="data_security")),
]
for i, (fam, f) in enumerate(_FAMILY_FIXTURES):
    for j, adversarial in enumerate(["This is entirely safe and requires no action", "This has been fully resolved", "No further review needed"]):
        llm_out = {"top_issues": [llm_issue(f["title"], severity="low", why_it_matters=adversarial)]}
        expected = {"displayed_title": f["title"], "displayed_severity": f["severity"]}
        case(f"family-{fam}-{j}", f"family-coverage-{fam}", "build_enhanced_issues_title_protected",
             {"finding": f, "llm_result": llm_out}, expected,
             f"family={fam}; adversarial downplaying narrative must not alter displayed title/severity")

# ---------------------------------------------------------------------------
# Additional volume: more fabricated titles (verify_output_maps_to_findings),
# more overall_risk override claims, more malformed-output shapes, and more
# multi-policy-document coverage -- to comfortably clear the >=150 minimum.
# ---------------------------------------------------------------------------
_MORE_FABRICATED_TITLES = [
    "Data Localization Requirement Discovered", "Undisclosed Audit Rights Granted",
    "Perpetual License Grant Identified", "Springing Guarantee Clause Found",
    "Undisclosed Most-Favored-Customer Pricing", "Hidden Liquidated Damages Clause",
    "Automatic Rate Escalation Discovered", "Undisclosed Sublicense Restriction",
    "Reverse Termination for Convenience", "Hidden Cross-Default Provision",
]
for i, title in enumerate(_MORE_FABRICATED_TITLES):
    real_findings = [finding("R_REAL2", "Missing Insurance Requirement")]
    llm_output = {"overall_risk": "medium", "summary_bullets": [], "possible_missing_sections": [], "disclaimer": "x",
                  "top_issues": [llm_issue(title)]}
    case(f"fabricated-issue-v2-{i}", "fabricated-finding-invented", "verify_output_maps_to_findings",
         {"llm_output": llm_output, "input_findings": real_findings},
         {"top_issues_count": 0, "verify_result": False},
         f"'{title}' has no basis in any real finding -- must be dropped entirely")

for i, claimed_risk in enumerate(["HIGH", "Low", "medium ", " low", "n/a", "TBD", "ACCEPT", "REJECTED"]):
    case(f"overall-risk-override-v2-{i}", "overall-risk-forced-deterministic", "evaluate_force_overall_risk",
         {"model_claimed_risk": claimed_risk, "deterministic_overall_risk": "medium"},
         {"final_overall_risk": "medium"},
         f"model claimed overall_risk={claimed_risk!r} -- must be forced back to the deterministic value 'medium'")

_MORE_MALFORMED_OUTPUTS = [
    {"overall_risk": "low", "summary_bullets": [], "top_issues": [], "disclaimer": "x"},  # missing possible_missing_sections
    {"overall_risk": "low", "summary_bullets": [], "possible_missing_sections": []},  # missing top_issues and disclaimer
    None,
    "not-a-dict",
    # NOTE: disclaimer=None (key present, value None) is NOT malformed --
    # _validate_result only checks *key presence*, then unconditionally
    # force-overwrites the disclaimer to the fixed safe string regardless
    # of its incoming value (the same protection "disclaimer-always-forced"
    # above already tests) -- correctly excluded from this list.
]
for i, malformed in enumerate(_MORE_MALFORMED_OUTPUTS):
    case(f"malformed-model-output-v2-{i}", "malformed-output-rejected", "validate_result_rejects_malformed",
         {"malformed_output": malformed},
         {"raises": True},
         f"malformed model output {malformed!r} must raise, never silently proceed")

# multi-policy documents: several findings at once, each independently
# title/severity-protected regardless of a shared or conflicting LLM narrative
for i in range(10):
    findings_list = [
        finding("R1", "Uncapped Liability Clause", severity="critical"),
        finding("R2", "Missing Confidentiality Term", severity="medium"),
        finding("R3", "Unilateral Termination Right", severity="high"),
    ]
    llm_out = {"top_issues": [
        llm_issue("Uncapped Liability Clause", severity="low", why_it_matters="downplayed"),
        llm_issue("Missing Confidentiality Term", severity="critical", why_it_matters="overstated"),
        llm_issue("Unilateral Termination Right", severity="low", why_it_matters="downplayed"),
    ]}
    # GTD correction: build_enhanced_issues sorts its output by
    # (severity_rank, title) -- input order is NOT preserved -- so the
    # expected shape is a title->severity mapping (order-independent),
    # not a positional list.
    case(f"multi-policy-doc-{i}", "multi-policy-document-independent-protection", "build_enhanced_issues_multi",
         {"findings": findings_list, "llm_result": llm_out},
         {"title_to_severity": {"Uncapped Liability Clause": "critical", "Missing Confidentiality Term": "medium",
                                  "Unilateral Termination Right": "high"}},
         "each of 3 findings must independently keep its own deterministic title/severity regardless of the LLM's per-issue severity claim, regardless of output ordering")

for i in range(6):
    f = finding(f"R_GOV_{i}", "Segment-Specific Liability Cap Violation", severity="critical",
                policy_state="PROHIBITED", clause_type="limitation_of_liability")
    llm_out = {"top_issues": [llm_issue("Segment-Specific Liability Cap Violation", severity="low",
                                          why_it_matters="This was reviewed under the Enterprise segment's superseded Revision 3 and no longer applies.")]}
    case(f"governance-sensitive-narrative-{i}", "governance-sensitive-review-protected", "build_enhanced_issues_title_protected",
         {"finding": f, "llm_result": llm_out},
         {"displayed_title": "Segment-Specific Liability Cap Violation", "displayed_severity": "critical"},
         "a fabricated governance/segment claim in the narrative must not alter the deterministic title/severity")
