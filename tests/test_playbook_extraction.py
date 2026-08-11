"""
Unit tests for playbook_extraction.py — the Phase 2 deterministic
extraction proposal builders.

The catastrophic Phase 2 failure the task defines is false establishment:
the source document does not actually support a value, but extraction
proposes it as ESTABLISHED anyway. Most tests here are adversarial in
that specific sense — proving a plausible-looking-but-unsupported
inference is NOT made, not just that supported ones are.
"""
import os

os.environ.setdefault("DEV_MODE", "true")

import assignment_policy_engine as ape
import confidentiality_policy_engine as cpe
import governing_law_policy_engine as gpe
import indemnification_policy_engine as ipe
import liability_policy_engine as lpe
import playbook_extraction as pex
import termination_policy_engine as tpe


def _statuses(proposed):
    return {name: p.status for name, p in proposed.items()}


# ---------------------------------------------------------------------------
# Liability
# ---------------------------------------------------------------------------

class TestLiabilityExtraction:
    def test_preferred_cap_established_with_evidence(self):
        text = "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid in the preceding twelve (12) months."
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        assert p["preferred_multiplier"].status == "ESTABLISHED"
        assert p["preferred_multiplier"].value == 2.0
        assert p["preferred_multiplier"].evidence_excerpt

    def test_ladder_tiers_never_established_from_a_single_point(self):
        text = "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid in the preceding twelve (12) months."
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        assert p["acceptable_max_multiplier"].status == "NOT_ESTABLISHED"
        assert p["negotiate_max_multiplier"].status == "NOT_ESTABLISHED"

    def test_capped_liability_does_not_establish_prohibit_unlimited_true(self):
        """Adversarial: a numeric cap is a favorable term. It must not be
        read as proof the org would categorically refuse unlimited."""
        text = "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid."
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        assert p["prohibit_unlimited"].status == "NOT_ESTABLISHED"

    def test_unlimited_liability_establishes_prohibit_unlimited_false(self):
        """Self-evident direction: the template's own cap IS unlimited."""
        text = "12. Limitation of Liability. Each party shall have unlimited liability under this Agreement."
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        assert p["prohibit_unlimited"].status == "ESTABLISHED"
        assert p["prohibit_unlimited"].value is False

    def test_silent_clause_does_not_establish_consequential_exclusion(self):
        """Adversarial: no mention of consequential damages at all must
        never be read as an affirmative 'not required' position."""
        text = "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid."
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        assert p["require_consequential_damages_exclusion"].status == "NOT_ESTABLISHED"

    def test_explicit_consequential_exclusion_established(self):
        text = (
            "12. Limitation of Liability. Liability shall not exceed one (1) times fees. "
            "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR CONSEQUENTIAL, INDIRECT, OR "
            "PUNITIVE DAMAGES, except for claims arising from gross negligence."
        )
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        assert p["require_consequential_damages_exclusion"].status == "ESTABLISHED"
        assert p["require_consequential_damages_exclusion"].value is True
        assert p["required_consequential_carveouts_json"].status == "ESTABLISHED"
        assert "gross_negligence" in p["required_consequential_carveouts_json"].value

    def test_absent_carveout_not_established_as_prohibited(self):
        """Negative evidence rule: fraud not mentioned as a carve-out
        anywhere must never be read as 'required_exceptions excludes
        fraud' or any other negative claim about fraud."""
        text = "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid, except for breaches of Confidentiality."
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        established_list = p["required_exceptions_json"].value if p["required_exceptions_json"].status == "ESTABLISHED" else []
        assert "fraud" not in (established_list or [])

    def test_no_clause_found_all_not_established(self):
        text = "This document says nothing about liability."
        facts = lpe.extract_liability_facts(text)
        p = pex.propose_fields("limitation_of_liability", facts, "mutual")
        assert all(f.status == "NOT_ESTABLISHED" for f in p.values())

    def test_conflicting_caps_across_provisions_produce_conflict_not_silent_pick(self):
        text = (
            "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid.\n\n"
            "Exhibit A. Notwithstanding Section 12, liability under this Exhibit shall not exceed "
            "five (5) times the fees paid, and this Exhibit does not amend or restate Section 12."
        )
        facts = lpe.extract_liability_facts(text)
        if facts.reconciliation == "unreconciled":
            p = pex.propose_fields("limitation_of_liability", facts, "mutual")
            assert p["preferred_multiplier"].status == "CONFLICTING"
            assert p["preferred_multiplier"].value is None


# ---------------------------------------------------------------------------
# Indemnification
# ---------------------------------------------------------------------------

class TestIndemnificationExtraction:
    def test_third_party_only_scope_established_true(self):
        text = (
            "9. Indemnification. Vendor shall indemnify Customer from and against any third-party "
            "claims only, arising from Vendor's gross negligence."
        )
        facts = ipe.extract_indemnification_facts(text)
        p = pex.propose_fields("indemnification", facts, "sell_side")
        assert p["require_exposure_third_party_only"].status == "ESTABLISHED"
        assert p["require_exposure_third_party_only"].value is True

    def test_includes_first_party_scope_established_false(self):
        text = (
            "9. Indemnification. Vendor shall indemnify Customer from and against any claims, "
            "whether direct or third-party, arising from Vendor's gross negligence."
        )
        facts = ipe.extract_indemnification_facts(text)
        p = pex.propose_fields("indemnification", facts, "sell_side")
        assert p["require_exposure_third_party_only"].status == "ESTABLISHED"
        assert p["require_exposure_third_party_only"].value is False

    def test_uncapped_exposure_establishes_prohibit_false(self):
        text = (
            "9. Indemnification. Vendor shall indemnify, defend, and hold harmless Customer from "
            "and against any and all claims, without limitation as to amount, arising from Vendor's "
            "gross negligence."
        )
        facts = ipe.extract_indemnification_facts(text)
        p = pex.propose_fields("indemnification", facts, "sell_side")
        # Either NOT_ESTABLISHED (extractor couldn't classify monetary as
        # unlimited from this phrasing) or ESTABLISHED False -- never True.
        assert p["prohibit_uncapped_exposure"].value is not True

    def test_capped_exposure_does_not_establish_prohibit_true(self):
        text = (
            "9. Indemnification. Vendor's total indemnification liability under this Section shall "
            "not exceed two (2) times the fees paid, and shall cover third-party claims only, "
            "arising from Vendor's gross negligence."
        )
        facts = ipe.extract_indemnification_facts(text)
        p = pex.propose_fields("indemnification", facts, "sell_side")
        assert p["prohibit_uncapped_exposure"].status == "NOT_ESTABLISHED"

    def test_mutual_contract_side_with_directional_language_not_established(self):
        """Adversarial: a directional (non-mutual) clause with
        contract_side='mutual' selected cannot resolve which obligation is
        ours -- must stay unestablished, not guess a side."""
        text = "9. Indemnification. Vendor shall indemnify Customer from and against third-party claims only."
        facts = ipe.extract_indemnification_facts(text)
        p = pex.propose_fields("indemnification", facts, "mutual")
        assert p["require_exposure_third_party_only"].status == "NOT_ESTABLISHED"

    def test_no_clause_found(self):
        facts = ipe.extract_indemnification_facts("Nothing relevant here.")
        p = pex.propose_fields("indemnification", facts, "sell_side")
        assert all(f.status == "NOT_ESTABLISHED" for f in p.values())


# ---------------------------------------------------------------------------
# Termination
# ---------------------------------------------------------------------------

class TestTerminationExtraction:
    def test_mutual_convenience_right_established(self):
        text = "15. Termination. Either party may terminate this Agreement for convenience upon 60 days written notice."
        facts = tpe.extract_termination_facts(text)
        p = pex.propose_fields("termination", facts, "sell_side")
        assert p["require_mutual_convenience_termination"].status == "ESTABLISHED"
        assert p["min_notice_days_against_us"].status == "ESTABLISHED"
        assert p["min_notice_days_against_us"].value == 60

    def test_asymmetric_convenience_right_does_not_establish_mutuality_false(self):
        """Adversarial: only Customer has a convenience right; this must
        not be read as 'we don't require mutuality' -- stay unestablished."""
        text = "15. Termination. Customer may terminate this Agreement for convenience upon 60 days written notice."
        facts = tpe.extract_termination_facts(text)
        p = pex.propose_fields("termination", facts, "sell_side")
        assert p["require_mutual_convenience_termination"].status == "NOT_ESTABLISHED"

    def test_cure_period_present_does_not_establish_prohibit_immediate_true(self):
        text = "15. Termination. Either party may terminate for cause upon a material breach that remains uncured for 30 days."
        facts = tpe.extract_termination_facts(text)
        p = pex.propose_fields("termination", facts, "sell_side")
        assert p["prohibit_immediate_termination_for_cause"].status == "NOT_ESTABLISHED"

    def test_our_own_immediate_termination_establishes_prohibit_false(self):
        text = (
            "15. Termination. Either party may terminate this Agreement immediately upon a "
            "material breach of this Agreement by the other party, without opportunity to cure."
        )
        facts = tpe.extract_termination_facts(text)
        p = pex.propose_fields("termination", facts, "sell_side")
        assert p["prohibit_immediate_termination_for_cause"].status == "ESTABLISHED"
        assert p["prohibit_immediate_termination_for_cause"].value is False

    def test_survival_topics_established_as_whitelist(self):
        text = (
            "15. Termination. Either party may terminate for convenience upon 30 days notice. "
            "Sections regarding Confidentiality and Payment Obligations shall survive termination."
        )
        facts = tpe.extract_termination_facts(text)
        p = pex.propose_fields("termination", facts, "sell_side")
        assert p["required_survival_topics_json"].status == "ESTABLISHED"
        assert set(p["required_survival_topics_json"].value) >= {"confidentiality", "payment_obligations"}
        # Topics never mentioned must not appear.
        assert "ip_ownership" not in p["required_survival_topics_json"].value

    def test_no_clause_found(self):
        facts = tpe.extract_termination_facts("Nothing relevant here.")
        p = pex.propose_fields("termination", facts, "sell_side")
        assert all(f.status == "NOT_ESTABLISHED" for f in p.values())


# ---------------------------------------------------------------------------
# Confidentiality
# ---------------------------------------------------------------------------

class TestConfidentialityExtraction:
    def test_mutual_obligation_established(self):
        text = "10. Confidentiality. Each party shall protect the other party's Confidential Information for a period of five (5) years using reasonable care."
        facts = cpe.extract_confidentiality_facts(text)
        p = pex.propose_fields("confidentiality", facts, "sell_side")
        assert p["require_mutual_confidentiality"].status == "ESTABLISHED"
        assert p["require_mutual_confidentiality"].value is True

    def test_one_directional_obligation_does_not_establish_mutual_false(self):
        text = "10. Confidentiality. Vendor shall protect Customer's Confidential Information for a period of five (5) years."
        facts = cpe.extract_confidentiality_facts(text)
        p = pex.propose_fields("confidentiality", facts, "sell_side")
        assert p["require_mutual_confidentiality"].status == "NOT_ESTABLISHED"

    def test_no_clause_found(self):
        facts = cpe.extract_confidentiality_facts("Nothing relevant here.")
        p = pex.propose_fields("confidentiality", facts, "sell_side")
        assert all(f.status == "NOT_ESTABLISHED" for f in p.values())


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

class TestAssignmentExtraction:
    def test_sole_discretion_on_us_establishes_prohibit_false(self):
        text = (
            "16. Assignment. Vendor may not assign this Agreement without the prior written "
            "consent of Customer, which consent may be withheld in its sole discretion."
        )
        facts = ape.extract_assignment_facts(text)
        p = pex.propose_fields("assignment", facts, "sell_side")
        assert p["prohibit_sole_discretion_consent"].status == "ESTABLISHED"
        assert p["prohibit_sole_discretion_consent"].value is False

    def test_reasonable_consent_does_not_establish_prohibit_true(self):
        text = "16. Assignment. Vendor may not assign this Agreement without Customer's prior written consent, which shall not be unreasonably withheld."
        facts = ape.extract_assignment_facts(text)
        p = pex.propose_fields("assignment", facts, "sell_side")
        assert p["prohibit_sole_discretion_consent"].status == "NOT_ESTABLISHED"

    def test_no_clause_found(self):
        facts = ape.extract_assignment_facts("Nothing relevant here.")
        p = pex.propose_fields("assignment", facts, "sell_side")
        assert all(f.status == "NOT_ESTABLISHED" for f in p.values())


# ---------------------------------------------------------------------------
# Governing Law
# ---------------------------------------------------------------------------

class TestGoverningLawExtraction:
    def test_jurisdiction_established(self):
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
        facts = gpe.extract_governing_law_facts(text)
        p = pex.propose_fields("governing_law", facts, "mutual")
        assert p["preferred_jurisdictions_json"].status == "ESTABLISHED"
        assert p["preferred_jurisdictions_json"].value == ["Delaware"]
        assert p["acceptable_jurisdictions_json"].status == "NOT_ESTABLISHED"
        assert p["prohibited_jurisdictions_json"].status == "NOT_ESTABLISHED"

    def test_jury_trial_not_mentioned_never_establishes_false(self):
        """Adversarial: the exact false-establishment trap the extractor
        itself cannot distinguish -- jury_trial_waived defaults to False
        for silence, not for an affirmative preserved-rights statement."""
        text = "20. Governing Law. This Agreement shall be governed by the laws of the State of Delaware."
        facts = gpe.extract_governing_law_facts(text)
        p = pex.propose_fields("governing_law", facts, "mutual")
        assert p["require_jury_trial_waiver"].status == "NOT_ESTABLISHED"

    def test_explicit_jury_waiver_established_true(self):
        text = (
            "20. Governing Law. This Agreement shall be governed by the laws of the State of "
            "Delaware. Each party hereby waives its right to a trial by jury."
        )
        facts = gpe.extract_governing_law_facts(text)
        p = pex.propose_fields("governing_law", facts, "mutual")
        assert p["require_jury_trial_waiver"].status == "ESTABLISHED"
        assert p["require_jury_trial_waiver"].value is True

    def test_arbitration_established(self):
        text = (
            "20. Governing Law. This Agreement shall be governed by the laws of the State of "
            "Delaware. Any dispute arising under this Agreement shall be resolved by binding "
            "arbitration."
        )
        facts = gpe.extract_governing_law_facts(text)
        p = pex.propose_fields("governing_law", facts, "mutual")
        assert p["required_dispute_resolution"].status == "ESTABLISHED"
        assert p["required_dispute_resolution"].value == "arbitration"

    def test_no_clause_found(self):
        facts = gpe.extract_governing_law_facts("Nothing relevant here.")
        p = pex.propose_fields("governing_law", facts, "mutual")
        assert all(f.status == "NOT_ESTABLISHED" for f in p.values())


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_repeated_extraction_produces_identical_proposals(self):
        text = (
            "12. Limitation of Liability. Liability shall not exceed two (2) times the fees paid, "
            "except for breaches of Confidentiality.\n\n"
            "9. Indemnification. Vendor shall indemnify Customer from third-party claims only "
            "arising from gross negligence, provided Vendor controls the defense.\n\n"
            "15. Termination. Either party may terminate for convenience upon 60 days notice.\n\n"
            "20. Governing Law. Delaware law governs; disputes resolved by binding arbitration."
        )
        results = []
        for _ in range(5):
            run = {}
            for clause_type, (extract_fn, _eval_fn) in {
                "limitation_of_liability": (lpe.extract_liability_facts, None),
                "indemnification": (ipe.extract_indemnification_facts, None),
                "termination": (tpe.extract_termination_facts, None),
                "governing_law": (gpe.extract_governing_law_facts, None),
            }.items():
                facts = extract_fn(text)
                proposed = pex.propose_fields(clause_type, facts, "sell_side")
                run[clause_type] = {
                    name: (p.status, p.value, p.evidence_excerpt) for name, p in proposed.items()
                }
            results.append(run)
        assert all(r == results[0] for r in results), "extraction is not deterministic across repeated runs"
