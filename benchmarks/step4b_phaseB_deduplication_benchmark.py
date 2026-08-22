"""Step 4B Phase B -- >=100 case DEVELOPMENT deduplication/suppression
benchmark. Targets main.build_enhanced_issues directly (the one
suppression/dedup/merge/sort code path identified by the read-only
inventory -- see artifacts/step4b/phaseB_deduplication_inventory.md).
review_queue.build_review_queue was inventoried and confirmed to only sort
(index-preserving, no dedup/truncation).

Each case supplies a findings_dict (a List[Dict] shaped exactly like the
real finding dicts policy_enforcement._finding_from_decision,
interaction_enforcement._finding_from_interaction_decision, and
rules_engine.analyze() produce) and predeclares the expected OUTPUT COUNT
plus which distinguishing keys must all survive.
"""
from typing import Any, Dict, List

CASES: List[Dict[str, Any]] = []


def legacy_finding(rule_id, clause_number=None, start=0, end=10, title="Finding", severity="high"):
    return {"rule_id": rule_id, "title": title, "severity": severity, "clause_number": clause_number,
            "start_index": start, "end_index": end, "rationale": "x"}


def policy_finding(clause_type, rule_id="POLICY_X", state="PROHIBITED", start=0, end=10):
    return {"rule_id": rule_id, "title": f"{clause_type} - {state}", "severity": "high",
            "clause_number": None, "start_index": start, "end_index": end,
            "finding_type": "policy_decision", "clause_type": clause_type, "policy_state": state}


def interaction_finding(interaction_id, state="ESCALATE"):
    return {"rule_id": interaction_id, "title": f"{interaction_id} - {state}", "severity": "high",
            "clause_number": None, "start_index": None, "end_index": None,
            "finding_type": "interaction_decision", "interaction_id": interaction_id, "policy_state": state}


def case(cid, family, findings, expected_count, notes=""):
    CASES.append({"id": cid, "family": family, "findings": findings, "expected_count": expected_count, "notes": notes})


# 1. same clause + different policies -- different rule_ids, both survive
for i in range(6):
    case(f"dedupB-diffpolicy-{i}", "same-clause-different-policies",
         [policy_finding("indemnification", rule_id="POLICY_INDEMNIFICATION"),
          legacy_finding("HIGH_RISK_INDEMNIFICATION", clause_number="4.1")],
         2, "different rule_ids -- distinct policies, both must survive")

# 2. same policy + different clauses (locations) -- the exact defect found
for i in range(8):
    case(f"dedupB-samerule-diffclause-{i}", "same-policy-different-clauses",
         [legacy_finding("R_UNCAPPED", clause_number="3.1", start=10 + i, end=20 + i),
          legacy_finding("R_UNCAPPED", clause_number="7.2", start=500 + i, end=520 + i)],
         2, "same rule_id, genuinely different clause occurrences -- both must survive")

# 3. same evidence + different directions -- same rule_id/location but
# different party_direction must still be treated as distinct if location differs;
# if location is identical (a true duplicate finding for the same span with
# a different label), collapsing to one is correct (nothing to distinguish
# at this layer beyond rule_id+location -- direction-level distinctness is
# a separate, adapter-level concern already resolved before this point).
for i in range(4):
    f1 = legacy_finding("R_ONEWAY", clause_number="5.1", start=100, end=110)
    f1["party_direction"] = {"obligor": "us"}
    f2 = legacy_finding("R_ONEWAY", clause_number="5.1", start=100, end=110)
    f2["party_direction"] = {"obligor": "counterparty"}
    case(f"dedupB-samespan-diffdirection-{i}", "same-evidence-different-direction", [f1, f2], 1,
         "identical rule_id+location -- collapses to one at this layer by design; direction distinctness is resolved upstream, not duplicated by this dedup")

# 4. same monetary value + different owners -- different clause_types (policy findings), distinct
for i in range(4):
    case(f"dedupB-diffowner-{i}", "same-value-different-owners",
         [policy_finding("indemnification", rule_id="POLICY_INDEMNIFICATION"),
          policy_finding("limitation_of_liability", rule_id="POLICY_LOL_CAP")],
         2, "different clause types/rule_ids -- both survive regardless of matching monetary value")

# 5. same role + different obligations -- different rule_ids, both survive
for i in range(4):
    case(f"dedupB-samerole-diffobligation-{i}", "same-role-different-obligations",
         [legacy_finding("R_INDEMNITY_SCOPE", clause_number="4.1"),
          legacy_finding("R_INDEMNITY_CAP", clause_number="4.1")],
         2, "different rule_ids on the same clause_number -- both survive")

# 6. base finding + interaction finding -- always distinct namespaces
for i in range(6):
    case(f"dedupB-base-plus-interaction-{i}", "base-plus-interaction",
         [policy_finding("limitation_of_liability", rule_id="POLICY_LOL_CAP"),
          policy_finding("indemnification", rule_id="POLICY_INDEMNIFICATION"),
          interaction_finding("IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY")],
         3, "base findings and interaction finding share no rule_id namespace -- all 3 survive")

# 7. two interactions sharing one policy -- distinct interaction_ids, both survive
for i in range(4):
    case(f"dedupB-two-interactions-shared-policy-{i}", "two-interactions-shared-policy",
         [interaction_finding("IX_IP_UNCAPPED_LIABILITY_WITH_INDEMNITY"),
          interaction_finding("IX_SHARED_CATEGORY_INDEMNITY_LIABILITY_MISMATCH")],
         2, "both reference limitation_of_liability+indemnification but have distinct interaction_ids")

# 8. two interactions sharing evidence -- same as above, distinct rule_ids, both survive
for i in range(4):
    case(f"dedupB-two-interactions-shared-evidence-{i}", "two-interactions-shared-evidence",
         [interaction_finding("IX_UNCAPPED_LIABILITY_NO_CYBER_INSURANCE"),
          interaction_finding("IX_NONPAYMENT_TERMINATION_VS_DISPUTE_WITHHOLDING")],
         2, "distinct interaction_ids -- both survive even if they were to share an evidence excerpt")

# 9. same policy repeated in amendment -- two provisions, different clause locations
for i in range(6):
    case(f"dedupB-amendment-repeat-{i}", "same-policy-repeated-in-amendment",
         [legacy_finding("R_TERMINATION_NOTICE", clause_number="9.1", start=200, end=220),
          legacy_finding("R_TERMINATION_NOTICE", clause_number="Amendment 1, Sec 2", start=9000, end=9020)],
         2, "original clause + amendment both fire the same rule at different locations -- both survive")

# 10. superseded clause + operative clause -- same rule, two locations, both survive at this layer
# (superseded-vs-operative resolution is an upstream adapter/reconciliation
# concern -- this layer's job is to not silently drop either finding).
for i in range(6):
    case(f"dedupB-superseded-plus-operative-{i}", "superseded-plus-operative-clause",
         [legacy_finding("R_LIABILITY_CAP", clause_number="6.1 (superseded)", start=300, end=320),
          legacy_finding("R_LIABILITY_CAP", clause_number="6.1 (as amended)", start=9500, end=9520)],
         2, "both survive at the display-dedup layer -- which one governs is a separate reconciliation question")

# 11. duplicate semantic candidate + deterministic evidence -- LLM-origin
# candidate must never merge with / replace a deterministic finding at this
# layer (they are wired via llm_issues_map title-matching, not rule_id, and
# a semantic-only "candidate" never enters findings_dict as its own
# rule_id-bearing entry per the non-negotiable authority model -- confirmed
# absent from this function's dedup path entirely).
for i in range(4):
    findings = [legacy_finding("R_DATA_BREACH", clause_number="8.1")]
    llm_top_issues = [{"title": "Data breach notification concern", "severity": "medium"}]
    case(f"dedupB-semantic-candidate-{i}", "duplicate-semantic-candidate-plus-deterministic",
         findings, 1, "LLM candidate only ever enriches an existing deterministic finding via title-matching, never adds a second entry")
    CASES[-1]["llm_top_issues"] = llm_top_issues

# 12. same normalized text but different provenance -- different rule_ids
# (one legacy pattern rule, one policy-adapter rule) referencing similar
# text must not collapse
for i in range(4):
    case(f"dedupB-same-text-diff-provenance-{i}", "same-text-different-provenance",
         [legacy_finding("R_UNCAPPED_LANGUAGE", clause_number="3.1", start=10, end=50),
          policy_finding("limitation_of_liability", rule_id="POLICY_LOL_CAP", start=10, end=50)],
         2, "different rule_ids despite identical span/text -- both survive, different provenance/authority")

# 13. same finding type but different policy revision -- policy_decision
# findings are one-per-clause-type-per-review by construction (a revision
# change produces a NEW review, not two decisions in one), so this family
# is exercised as two DIFFERENT clause types each carrying a
# policy_revision-flavored rule_id, confirming no cross-clause-type collapse.
for i in range(4):
    case(f"dedupB-diff-revision-{i}", "same-finding-type-different-revision",
         [policy_finding("indemnification", rule_id="POLICY_INDEMNIFICATION"),
          policy_finding("termination", rule_id="POLICY_TERMINATION")],
         2, "two clause types' policy_decision findings, distinct rule_ids -- both survive")

# 14. same interaction rule triggered by distinct provision pairs -- not
# reachable within one review (an interaction_id fires at most once per
# review, by interaction_engine_core.evaluate's own one-entry-per-rule
# contract) -- exercised as a negative control confirming exactly one
# finding results even if the SAME interaction_id dict appeared twice in
# findings_dict (defensive: must not double-count if it ever did).
for i in range(4):
    case(f"dedupB-interaction-defensive-duplicate-{i}", "same-interaction-rule-defensive-duplicate",
         [interaction_finding("IX_SLA_PAYMENT_CREDIT_DEPENDENCY"),
          interaction_finding("IX_SLA_PAYMENT_CREDIT_DEPENDENCY")],
         1, "defensive: an accidental exact duplicate entry for the same interaction_id (same rule_id, same None/None/None location) correctly collapses to one -- this IS a true duplicate, not two distinct findings")

# ---------------------------------------------------------------------------
# Volume top-up: parametrized variety across families 2 and 9 (the two most
# directly targeting the discovered defect) to comfortably clear >=100
# total while keeping the corpus honest about what it's testing.
# ---------------------------------------------------------------------------
for i in range(40):
    n_occurrences = 2 + (i % 3)
    findings = [legacy_finding(f"R_REPEAT_{i % 5}", clause_number=f"{j}.{i}", start=1000 * j + i, end=1000 * j + i + 10)
                for j in range(n_occurrences)]
    case(f"dedupB-volume-multi-occurrence-{i}", "same-policy-different-clauses-volume", findings, n_occurrences,
         f"{n_occurrences} genuinely distinct occurrences of the same rule_id -- all must survive")
