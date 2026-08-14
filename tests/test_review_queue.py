"""
Unit tests for review_queue.py — the exception-queue view-model (P0
remediation of docs/architecture/contract_review_exception_ux.md).

Pure-function tests against fixture findings/policy_decisions dicts; no
DB, no HTTP. The critical correctness property under test throughout:
"passed" is NEVER derived from the absence of a finding — only from an
explicit ACCEPT/ACCEPT_WITH_NOTE state recorded in policy_decisions.
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import review_queue as rq


def _policy_finding(clause_type, state, escalate_to=None, extra=None):
    f = {
        "finding_type": "policy_decision", "clause_type": clause_type, "policy_state": state,
        "title": f"{clause_type} — {state}", "rule_id": f"POLICY_{clause_type.upper()}",
        "escalate_to": escalate_to, "redline": None, "rationale": "because reasons",
    }
    if extra:
        f.update(extra)
    return f


def _rule_finding(rule_id="R1", severity="medium"):
    return {"finding_type": "pattern_match", "rule_id": rule_id, "policy_state": None,
            "title": f"Rule {rule_id}", "severity": severity}


def _decision(state, extracted_summary="found this", policy_limit_summary="policy allows this"):
    return {"state": state, "extracted_summary": extracted_summary, "policy_limit_summary": policy_limit_summary}


# ---------------------------------------------------------------------------
# Ordering (regression tests 1 & 2 from the task spec)
# ---------------------------------------------------------------------------

class TestOrdering:
    def test_prohibited_appears_before_negotiate_regardless_of_document_position(self):
        # NEGOTIATE finding placed FIRST in the array (i.e. earlier in the
        # document) — the queue must still rank PROHIBITED ahead of it.
        findings = [
            _policy_finding("termination", "NEGOTIATE"),
            _policy_finding("limitation_of_liability", "PROHIBITED"),
        ]
        queue = rq.build_review_queue(findings, {})
        assert queue.policy_exception_indices == [1, 0]

    def test_must_redline_in_highest_action_tier(self):
        assert rq.tier_rank("MUST_REDLINE") == rq.tier_rank("PROHIBITED") == rq.tier_rank("ESCALATE") == 0

    def test_negotiate_ranks_below_top_tier(self):
        assert rq.tier_rank("NEGOTIATE") > rq.tier_rank("PROHIBITED")

    def test_requires_review_ranks_below_negotiate(self):
        assert rq.tier_rank("REQUIRES_REVIEW") > rq.tier_rank("NEGOTIATE")

    def test_ties_within_a_tier_broken_by_original_index(self):
        findings = [
            _policy_finding("governing_law", "ESCALATE"),
            _policy_finding("indemnification", "PROHIBITED"),
            _policy_finding("assignment", "MUST_REDLINE"),
        ]
        queue = rq.build_review_queue(findings, {})
        # All three are tier 0 — order must be stable (original index order).
        assert queue.policy_exception_indices == [0, 1, 2]

    def test_other_findings_keep_original_array_order_unchanged(self):
        findings = [_rule_finding("R3"), _rule_finding("R1"), _rule_finding("R2")]
        queue = rq.build_review_queue(findings, {})
        assert queue.other_finding_indices == [0, 1, 2]

    def test_ordering_is_a_pure_deterministic_function_of_input(self):
        findings = [
            _policy_finding("termination", "NEGOTIATE"),
            _policy_finding("limitation_of_liability", "PROHIBITED"),
            _policy_finding("confidentiality", "REQUIRES_REVIEW"),
            _rule_finding("R1"),
        ]
        a = rq.build_review_queue(findings, {})
        b = rq.build_review_queue(findings, {})
        assert a.policy_exception_indices == b.policy_exception_indices
        assert a.other_finding_indices == b.other_finding_indices


# ---------------------------------------------------------------------------
# Passed-check correctness (regression tests 3-7)
# ---------------------------------------------------------------------------

class TestPassedCorrectness:
    def test_requires_review_never_displayed_as_a_pass(self):
        findings = [_policy_finding("indemnification", "REQUIRES_REVIEW")]
        policy_decisions = {"indemnification": _decision("REQUIRES_REVIEW")}
        queue = rq.build_review_queue(findings, policy_decisions)
        assert queue.summary.passed == 0
        assert "indemnification" not in [c.clause_type for c in queue.passed_checks]
        assert queue.summary.requires_review == 1

    def test_not_applicable_never_counted_as_passed(self):
        findings = []
        policy_decisions = {"governing_law": _decision("NOT_APPLICABLE")}
        queue = rq.build_review_queue(findings, policy_decisions)
        assert queue.summary.passed == 0
        assert queue.summary.not_applicable == 1
        assert queue.not_applicable_checks[0].clause_type == "governing_law"

    def test_evaluation_error_never_counted_as_passed(self):
        findings = [_policy_finding("confidentiality", "EVALUATION_ERROR")]
        # An EVALUATION_ERROR clause is never written into policy_decisions
        # at all (policy_enforcement.apply_active_policies omits it) — the
        # only signal is the finding itself.
        queue = rq.build_review_queue(findings, {})
        assert queue.summary.passed == 0
        assert queue.summary.evaluation_error == 1
        assert "confidentiality" not in [c.clause_type for c in queue.passed_checks]

    def test_missing_or_no_active_policy_never_counted_as_passed(self):
        """A clause type with NO entry in policy_decisions at all (no
        ACTIVE policy covers it) must never appear as passed — it was
        simply never evaluated, which review_queue must not manufacture
        certainty about."""
        findings = []
        policy_decisions = {"limitation_of_liability": _decision("ACCEPT")}
        queue = rq.build_review_queue(findings, policy_decisions)
        # Only the ONE evaluated clause counts as passed; the other five
        # clause types (never in policy_decisions) contribute nothing.
        assert queue.summary.passed == 1
        assert len(queue.passed_checks) == 1
        assert queue.passed_checks[0].clause_type == "limitation_of_liability"

    def test_explicit_acceptable_decision_is_counted_as_passed(self):
        findings = []
        policy_decisions = {
            "limitation_of_liability": _decision("ACCEPT"),
            "confidentiality": _decision("ACCEPT_WITH_NOTE"),
        }
        queue = rq.build_review_queue(findings, policy_decisions)
        assert queue.summary.passed == 2
        clause_types = {c.clause_type for c in queue.passed_checks}
        assert clause_types == {"limitation_of_liability", "confidentiality"}

    def test_evaluation_error_clause_excluded_from_passed_even_if_stale_decision_present(self):
        """Defense in depth: even if policy_decisions somehow retained a
        stale entry for a clause that also has an EVALUATION_ERROR
        finding, the error must win — never silently reported as passed."""
        findings = [_policy_finding("assignment", "EVALUATION_ERROR")]
        policy_decisions = {"assignment": _decision("ACCEPT")}
        queue = rq.build_review_queue(findings, policy_decisions)
        assert queue.summary.passed == 0
        assert queue.summary.evaluation_error == 1

    def test_passed_check_carries_real_engine_summaries_not_invented_text(self):
        findings = []
        policy_decisions = {"limitation_of_liability": _decision(
            "ACCEPT", extracted_summary="Cap is 1x fees", policy_limit_summary="policy allows up to 2x fees",
        )}
        queue = rq.build_review_queue(findings, policy_decisions)
        check = queue.passed_checks[0]
        assert check.extracted_summary == "Cap is 1x fees"
        assert check.policy_limit_summary == "policy allows up to 2x fees"


# ---------------------------------------------------------------------------
# Summary counts
# ---------------------------------------------------------------------------

class TestSummaryCounts:
    def test_needs_attention_includes_evaluation_error(self):
        findings = [
            _policy_finding("limitation_of_liability", "PROHIBITED"),
            _policy_finding("confidentiality", "EVALUATION_ERROR"),
        ]
        queue = rq.build_review_queue(findings, {})
        assert queue.summary.needs_attention == 2
        assert queue.summary.top_tier == 1
        assert queue.summary.evaluation_error == 1

    def test_empty_findings_and_no_policy_decisions_is_all_zero(self):
        queue = rq.build_review_queue([], {})
        assert queue.summary.as_dict() == {
            "needs_attention": 0, "top_tier": 0, "negotiate": 0, "requires_review": 0,
            "evaluation_error": 0, "passed": 0, "not_applicable": 0,
            "interactions_needing_attention": 0,
        }

    def test_none_policy_decisions_handled_like_empty_dict(self):
        queue = rq.build_review_queue([], None)
        assert queue.summary.passed == 0
        assert queue.passed_checks == []


# ---------------------------------------------------------------------------
# Clause label lookup
# ---------------------------------------------------------------------------

class TestClauseLabel:
    def test_known_clause_type_gets_human_label(self):
        assert rq._clause_label("limitation_of_liability") == "Limitation of Liability"

    def test_unknown_clause_type_falls_back_to_title_case(self):
        assert rq._clause_label("some_future_clause") == "Some Future Clause"


# ---------------------------------------------------------------------------
# Interaction Engine V1 — interaction_decision findings must be bucketed
# distinctly from policy_decision exceptions, never merged.
# ---------------------------------------------------------------------------

def _interaction_finding(interaction_id, state, escalate_to=None):
    return {
        "finding_type": "interaction_decision", "interaction_id": interaction_id, "policy_state": state,
        "title": f"{interaction_id} — {state}", "rule_id": interaction_id,
        "escalate_to": escalate_to, "redline": None, "rationale": "because it interacts",
        "clause_type": None, "participating_clause_types": ["limitation_of_liability", "indemnification"],
    }


class TestInteractionBucketing:
    def test_interaction_finding_never_lands_in_policy_or_other_bucket(self):
        findings = [_interaction_finding("IX_TEST", "ESCALATE")]
        queue = rq.build_review_queue(findings, {})
        assert queue.policy_exception_indices == []
        assert queue.other_finding_indices == []
        assert queue.interaction_exception_indices == [0]

    def test_interaction_count_feeds_summary(self):
        findings = [
            _interaction_finding("IX_A", "ESCALATE"),
            _interaction_finding("IX_B", "REQUIRES_REVIEW"),
            _policy_finding("limitation_of_liability", "NEGOTIATE"),
        ]
        queue = rq.build_review_queue(findings, {})
        assert queue.summary.interactions_needing_attention == 2
        assert len(queue.policy_exception_indices) == 1
        assert len(queue.interaction_exception_indices) == 2
        # interaction count must never bleed into the clause-exception headline.
        assert queue.summary.needs_attention == 1

    def test_interaction_bucket_sorted_by_tier_same_as_policy(self):
        findings = [
            _interaction_finding("IX_LOW", "NEGOTIATE"),
            _interaction_finding("IX_HIGH", "ESCALATE"),
            _interaction_finding("IX_MID", "REQUIRES_REVIEW"),
        ]
        queue = rq.build_review_queue(findings, {})
        ordered_ids = [findings[i]["interaction_id"] for i in queue.interaction_exception_indices]
        assert ordered_ids == ["IX_HIGH", "IX_LOW", "IX_MID"]

    def test_mixed_findings_all_three_buckets_are_disjoint(self):
        findings = [
            _rule_finding("R1"),
            _policy_finding("termination", "ESCALATE"),
            _interaction_finding("IX_A", "ESCALATE"),
        ]
        queue = rq.build_review_queue(findings, {})
        assert queue.other_finding_indices == [0]
        assert queue.policy_exception_indices == [1]
        assert queue.interaction_exception_indices == [2]
